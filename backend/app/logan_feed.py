import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel

# Same local-dev sys.path bridge as logan_demo.py -- see ADR-022. Repeated here
# (rather than imported) so this module doesn't depend on logan_demo's import
# order having already run it.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from logan_core.community_intelligence import EngagementSample  # noqa: E402
from logan_core.contracts import (  # noqa: E402
    LOCAL_FOUNDER_USER_ID,
    DeliveredItem,
    Holding,
    Interest,
    RawSignal,
)
from logan_core.orchestrator import Orchestrator, PipelineDependencies  # noqa: E402
from logan_core.receptors import (  # noqa: E402
    earnings_report_to_raw_signal,
    simulated_fixtures,
    tesla_ai_partnership_corroboration,
)
from logan_core.receptors.providers import (  # noqa: E402
    FmpEarningsProvider,
    FmpProviderError,
)
from logan_core.trigger_detection import (  # noqa: E402
    StocksTriggerEvaluator,
    evaluate_earnings_beat_condition,
)
from logan_core.user_model import UserModelBuilder  # noqa: E402

from .config import live_nvda_earnings_enabled  # noqa: E402
from .entity_registry import resolve  # noqa: E402

# --- Process-lifetime pipeline state (notification/identity fix) ---
#
# Previously, `_run_feed_pipeline()` built a brand-new `Orchestrator()` on
# every single call -- which meant a brand-new World Model too, so its event
# dedup index (see world_model/model.py's `_recent`) never had anything to
# compare against and handed out a fresh random `event_id` for the same
# underlying opportunity on every request. This broke both event identity
# stability *and* Prioritization's AttentionState (surfaced/cooldowns/
# fatigue/notification-review), which the spec already designed for exactly
# this "is this new to the user" use case but nothing had ever wired up.
#
# The fix: one Orchestrator instance for the life of this process, not one
# per request. World Model's dedup and Prioritization's AttentionState can
# now actually do their jobs across repeated `/v1/opportunities` calls.
#
# IMPORTANT LIMITATION, by design for this stage (see the owner conversation
# this shipped from): this is in-memory, process-lifetime state only. A
# backend restart (including `uvicorn --reload` triggering on a file change)
# resets it completely -- every event_id and every notification-reviewed
# record is gone, and the next request re-establishes a fresh baseline. This
# is intentional: real durable per-user history needs actual persistence,
# which is an open, undecided question for this repo (ADR-006) and not
# something to back into as a side effect of this fix. A `threading.Lock`
# guards access since FastAPI runs sync `def` routes in a worker thread pool
# by default, so concurrent requests could otherwise race on the same
# in-memory dicts.
_state_lock = threading.Lock()
_orchestrator: Orchestrator | None = None
# user_ids whose very first `/v1/opportunities` request has already been
# processed -- lets that first response stay notification-silent (nothing is
# "new" relative to a user who's never seen anything yet) without treating
# every subsequent, genuinely-new event the same way.
_baseline_established: set[str] = set()


def _get_orchestrator() -> Orchestrator:
    global _orchestrator
    with _state_lock:
        if _orchestrator is None:
            # Sprint 3.6.6C: trigger_detector is gated behind
            # live_nvda_earnings_enabled(), not wired unconditionally.
            # Orchestrator.run() adds a "trigger_detection" ExecutionTrace
            # layer entry for *every* raw_signal whenever any detector is
            # configured at all (see orchestrator/pipeline.py's run()) --
            # unconditional wiring would therefore change the trace shape for
            # every simulated entity even with the live path disabled,
            # breaking the "disabled mode is byte-for-byte unchanged"
            # requirement. Gating construction on the flag keeps disabled
            # mode identical to pre-3.6.6C (no trigger_detector at all, same
            # as every other existing Orchestrator() caller) while still
            # giving the live NVDA path real trigger detection when enabled.
            # Read once at construction time, matching config.py's own
            # documented assumption that flipping this flag requires a clean
            # backend restart, not a mid-process toggle.
            deps = (
                PipelineDependencies(trigger_detector=StocksTriggerEvaluator())
                if live_nvda_earnings_enabled()
                else PipelineDependencies()
            )
            _orchestrator = Orchestrator(deps=deps)
        return _orchestrator


def _live_nvda_raw_signal(now: datetime) -> RawSignal | None:
    """Sprint 3.6.6C: attempts to replace the simulated NVDA fixture with a
    real FMP-driven earnings signal. Returns None on any failure -- FMP
    unreachable, auth failure, malformed response, or genuinely no reported
    earnings on file -- so the caller can fall back to the simulated
    fixture. Never raises: every FmpProviderError is caught here so a live-
    data hiccup can never take down /v1/opportunities (Phase "Honest
    failure behavior" instruction). Never silently presents simulated data
    as live either -- the caller only substitutes this return value in
    place of the simulated fixture when it is not None; when it is None,
    the simulated NVDA fixture already in `fixtures` is left untouched.

    Also returns None when a real report was fetched but does not satisfy
    STOCK_EARNINGS_BEAT. A valid provider response is not itself an
    opportunity -- this 3.6.6C slice's intended semantics are that the real
    NVDA opportunity surfaces only when the implemented TriggerEvent
    actually fires, not merely because FMP returned some usable data.
    Reuses evaluate_earnings_beat_condition (the same pure function
    StocksTriggerEvaluator.evaluate() calls) rather than re-deriving the
    fire condition, so this pre-check and the orchestrator's own later
    trigger_detection layer can never disagree.
    """
    try:
        provider = FmpEarningsProvider()
    except FmpProviderError as exc:
        print(f"[live-nvda] provider unavailable, using simulated NVDA: {exc}")
        return None

    try:
        report = provider.fetch_latest_earnings("NVDA")
    except FmpProviderError as exc:
        print(f"[live-nvda] FMP fetch failed, using simulated NVDA: {exc}")
        return None

    if report is None:
        print("[live-nvda] FMP has no reported NVDA earnings, using simulated NVDA")
        return None

    fired, beat_pct, reason = evaluate_earnings_beat_condition(
        report.actual_eps, report.consensus_eps
    )
    if not fired:
        print(
            f"[live-nvda] real report fetched but STOCK_EARNINGS_BEAT did not "
            f"fire ({reason}), using simulated NVDA"
        )
        return None

    print(
        f"[live-nvda] using real FMP earnings report dated "
        f"{report.report_timestamp.date()} for NVDA (source={report.source_id}, "
        f"beat_pct={beat_pct:.2f})"
    )
    return earnings_report_to_raw_signal(report)


def reset_pipeline_state() -> None:
    """Test-only (and general-purpose "start over") hook: drops the persistent
    Orchestrator and baseline tracking, so the next call behaves like a fresh
    process start. Tests that compare two pipeline runs and expect them to be
    independent (rather than exercising the new deliberate cross-request
    persistence) should call this between runs -- see
    backend/tests/test_opportunities_api.py and test_logan_feed.py.
    """
    global _orchestrator
    with _state_lock:
        _orchestrator = None
        _baseline_established.clear()


def mark_notifications_reviewed(event_ids: list[UUID]) -> None:
    """Called by the `/v1/notifications/review` route -- the only way an
    event_id's `is_new_for_user` clears (re-observing the same event again
    does not clear it; see PrioritizationEngine.prioritize()).
    """
    orchestrator = _get_orchestrator()
    with _state_lock:
        orchestrator.deps.prioritization_engine.mark_reviewed(
            LOCAL_FOUNDER_USER_ID, event_ids
        )
    # Sprint 3.6.6G: deferred import breaks the logan_feed<->notifications
    # circular dependency (notifications.py imports FeedItem/
    # get_alert_eligible_items from this module at load time; this module
    # cannot also import from notifications.py at load time without a
    # cycle) -- see notifications.py's own comment on
    # get_pending_push_event_ids. Reviewing through this one existing
    # endpoint now clears both the pre-existing is_new_for_user badge state
    # above and the new pending-push state together, coherently -- not two
    # separate review actions the client would have to know to call.
    from .notifications import mark_pushed_notifications_reviewed

    mark_pushed_notifications_reviewed(event_ids)


# Per-entity simulated engagement, tuned for visual variety in the demo field --
# not meant to represent real-world volumes. Entities not listed fall back to a
# modest default.
_ENGAGEMENT_BY_ENTITY: dict[str, list[tuple[int, int, int, int]]] = {
    # (volume_at_point, unique_users, saves_shares, questions)
    "TSLA": [(10, 8, 1, 0), (40, 30, 6, 3)],
    "NVDA": [(15, 12, 2, 1), (35, 26, 5, 2)],
    "AAPL": [(6, 5, 1, 0), (12, 9, 2, 0)],
    "MARKETS": [(4, 4, 0, 0), (7, 5, 1, 0)],
    "OIL": [(3, 3, 0, 0), (5, 4, 0, 0)],
    "BTC": [(20, 15, 3, 1), (48, 34, 8, 3)],
    "FED": [(8, 6, 1, 0), (22, 16, 3, 1)],
    "NFL": [(5, 4, 0, 0), (9, 7, 1, 0)],
    "MUSIC": [(30, 20, 4, 2), (55, 38, 9, 4)],
    "POLY": [(3, 3, 0, 0), (4, 3, 0, 0)],
    "AI_SECTOR": [(30, 20, 4, 2), (55, 38, 9, 4)],
}


class FeedItem(BaseModel):
    event_id: UUID
    entity_id: str
    display_name: str
    category: str
    ticker: str | None
    domain: str
    delivered_item: DeliveredItem
    # 1-indexed position in this response's already-sorted order (1 = most
    # important). Deliberately an ordinal, not a raw score: logan_core's
    # internal_rank_score is internal-only and must never be returned via any
    # public API response (ADR-029) -- this field is the correct public-facing
    # substitute for "where does this belong in the field/list."
    rank: int
    confidence_score: float
    confidence_label: str
    connected_event_ids: list[UUID]
    # Whether this event_id is unread for the current user (see
    # PrioritizationEngine.prioritize()/mark_reviewed() -- deliberately not
    # the same concept as World Model's EnrichedEvent.is_new). False on a
    # user's very first-ever response (see _run_feed_pipeline's baseline
    # handling) and after an explicit POST /v1/notifications/review.
    is_new_for_user: bool
    # The real Normalization-layer signal_type behind this opportunity's
    # primary/first signal (e.g. "earnings_signal", "volatility_spike") --
    # exposed so the mobile field can show a short, honest reason tag on
    # each vessel instead of inventing one. Real data, not a polished
    # human-authored label -- see the owner conversation this shipped from
    # for why: no field for a hand-tuned short descriptor exists anywhere in
    # the pipeline, and fabricating one client-side would violate this
    # project's "don't fake capabilities" rule.
    signal_type: str


class DemoFeedResponse(BaseModel):
    items: list[FeedItem]
    generated_at: datetime


def _engagement_samples(entity_id: str, now: datetime) -> list[EngagementSample]:
    points = _ENGAGEMENT_BY_ENTITY.get(entity_id, [(5, 4, 0, 0), (8, 6, 1, 0)])
    return [
        EngagementSample(
            observed_at=now,
            volume_at_point=v,
            unique_users=u,
            saves_shares=s,
            questions=q,
        )
        for v, u, s, q in points
    ]


def _run_feed_pipeline() -> tuple[list[FeedItem], datetime, list[UUID]]:
    """Runs the simulated entity fixtures (Tesla, NVIDIA, Apple, Bitcoin, Federal
    Reserve, NFL, Music, Polymarket, Markets, Oil, AI) through one shared Orchestrator
    instance and builds the ranked, connected feed shared by every route that exposes
    this data. Sharing one Orchestrator (and therefore one World Model, Memory Store,
    and Prioritization state) across all events lets genuinely overlapping entities
    (e.g. Tesla's downstream ripple touching NVIDIA and the AI sector, which have
    their own direct fixtures too) connect to each other, the same way related
    opportunities would in a real session -- not independent runs stitched together
    after the fact.

    Single source of truth for both the versioned `/v1/opportunities` API
    (`opportunities.py`) and the legacy `/v1/demo/feed` route below -- neither
    duplicates this computation.

    The shared Orchestrator instance now also persists *across* calls to this
    function (see `_get_orchestrator()` above), not just within one -- this
    is what lets the same underlying opportunity keep a stable `event_id` and
    correct `is_new_for_user` across repeated requests, for the life of this
    process.
    """
    now = datetime.now(timezone.utc)

    user_model = UserModelBuilder().seed(
        user_id=LOCAL_FOUNDER_USER_ID,
        holdings=[
            Holding(
                domain="stocks", entity_id="NVDA", display_name="NVIDIA", added_at=now
            )
        ],
        interests=[
            Interest(
                domain="social",
                topic="AI_SECTOR",
                weight=0.8,
                source="explicit",
                created_at=now,
                last_updated=now,
            )
        ],
        risk_tolerance="moderate",
    )

    orchestrator = _get_orchestrator()
    fixtures = simulated_fixtures(now)

    # Sprint 3.6.6C: replaces (never adds alongside) the simulated NVDA
    # fixture with a real FMP-driven one when explicitly enabled and FMP
    # actually returns usable data -- `fixtures` is keyed by entity_id, so
    # this dict assignment is what guarantees exactly one NVDA entry either
    # way, never a duplicate. Every other simulated entity is untouched.
    # Falls back to the simulated NVDA fixture already in `fixtures` (no
    # code path removes it) on any failure -- see _live_nvda_raw_signal's
    # own docstring for the exact failure modes this covers.
    if live_nvda_earnings_enabled():
        live_nvda_signal = _live_nvda_raw_signal(now)
        if live_nvda_signal is not None:
            fixtures["NVDA"] = live_nvda_signal

    # One lock for the whole request's pipeline run, not just per-call: two
    # concurrent requests interleaving their individual entity.run() calls
    # against the same shared World Model/Prioritization state would produce
    # genuinely tangled results (e.g. one request's dedup window absorbing
    # signals from a different request), not just a data race.
    with _state_lock:
        results = []
        for entity_id, raw_signal in fixtures.items():
            raw_signals = [raw_signal]
            if entity_id == "TSLA":
                raw_signals.append(tesla_ai_partnership_corroboration(now))

            result = orchestrator.run(
                raw_signals=raw_signals,
                user_id=LOCAL_FOUNDER_USER_ID,
                user_model=user_model,
                engagement_samples=_engagement_samples(entity_id, now),
                domain=raw_signal.domain,
            )
            results.append((entity_id, result))

        # Connections: two events are "rippled" to each other if the entities either one
        # touches (directly or via World Model's downstream mapping) overlap.
        touched: dict[UUID, set[str]] = {
            r.event.event_id: {e.entity_id for e in r.event.entities}
            | set(r.event.downstream)
            for _, r in results
        }
        connections: dict[UUID, list[UUID]] = {event_id: [] for event_id in touched}
        event_ids = list(touched.keys())
        for i, a in enumerate(event_ids):
            for b in event_ids[i + 1 :]:
                if touched[a] & touched[b]:
                    connections[a].append(b)
                    connections[b].append(a)

        # Sort by the internal-only ranking score before building the public
        # response -- the score itself is never serialized (ADR-029); only the
        # resulting order (as `rank`, below) is public-facing.
        results.sort(
            key=lambda pair: pair[1].recommendation.internal_rank_score, reverse=True
        )

        # First-ever request for this user: nothing is "new" relative to a
        # user who's never seen anything yet. Each item's is_new_for_user was
        # already computed True during its own orchestrator.run() above
        # (notifications_reviewed was empty going in) -- silence this specific
        # response by marking everything reviewed now, so both this response
        # and every future one reflect the same honest baseline.
        is_first_load = LOCAL_FOUNDER_USER_ID not in _baseline_established
        if is_first_load:
            _baseline_established.add(LOCAL_FOUNDER_USER_ID)
            orchestrator.deps.prioritization_engine.mark_reviewed(
                LOCAL_FOUNDER_USER_ID, [r.event.event_id for _, r in results]
            )

        # Sprint 3.6.6G: deferred import, see mark_notifications_reviewed's
        # own comment on the logan_feed<->notifications circular dependency.
        # A pushed-but-unopened notification must show in the in-app badge
        # even on this same first-load response -- the "first load is
        # notification-silent" rule above is about items that were never
        # pushed, not about hiding a real push the user already received.
        from .notifications import get_pending_push_event_ids

        pending_push_event_ids = get_pending_push_event_ids()

        items = []
        for position, (entity_id, r) in enumerate(results, start=1):
            entity = r.event.entities[0]
            canonical = resolve(entity_id, entity.display_name, r.event.domain)
            items.append(
                FeedItem(
                    event_id=r.event.event_id,
                    entity_id=canonical.entity_id,
                    display_name=canonical.display_name,
                    category=canonical.category,
                    ticker=canonical.ticker,
                    domain=r.event.domain,
                    delivered_item=r.delivered_item,
                    rank=position,
                    confidence_score=r.confidence.confidence_score,
                    confidence_label=r.delivered_item.confidence_label,
                    connected_event_ids=connections[r.event.event_id],
                    is_new_for_user=(
                        (False if is_first_load else r.prioritized_item.is_new_for_user)
                        or r.event.event_id in pending_push_event_ids
                    ),
                    # First signal drives the primary event for this entity
                    # (see world_model/model.py's process()) -- TSLA is the
                    # only fixture with a second, corroborating signal, and
                    # both share the same underlying signal_type.
                    signal_type=r.normalized_signals[0].signal_type,
                )
            )

        # Sprint 3.6.6F (STRATUS Watch): internal-only -- never added to the
        # public FeedItem contract (same discipline as internal_rank_score,
        # ADR-029). PrioritizedItem.interruption=="alert" is the existing,
        # already-computed bar for "urgent enough to interrupt" (Prioritization
        # Engine); reused here as the notification-eligibility gate rather than
        # inventing a second threshold. Independent of is_first_load's badge
        # silencing above -- a first-ever poll after a backend restart can
        # still be alert-eligible for push purposes even though the in-app
        # badge intentionally starts quiet.
        alert_event_ids = [
            r.event.event_id
            for _, r in results
            if r.prioritized_item.interruption == "alert"
        ]

    return items, now, alert_event_ids


def run_demo_feed() -> DemoFeedResponse:
    """Deprecated in favor of `/v1/opportunities` (see `opportunities.py`), kept for
    existing callers during the V3.1.4 migration window -- see ADR-022 and the
    V3.1.4 BATCH-4 API work. Delegates to the same pipeline run as the versioned API;
    the two do not compute this independently.
    """
    items, now, _alert_event_ids = _run_feed_pipeline()
    return DemoFeedResponse(items=items, generated_at=now)


def get_alert_eligible_items() -> list[FeedItem]:
    """Sprint 3.6.6F (STRATUS Watch): the current pipeline run's items whose
    PrioritizedItem.interruption == "alert" -- the existing "urgent enough to
    interrupt" bar, reused as the notification-eligibility gate. Runs the
    same shared, process-lifetime pipeline every other caller here uses; does
    not compute anything independently.
    """
    items, _now, alert_event_ids = _run_feed_pipeline()
    alert_ids = set(alert_event_ids)
    return [item for item in items if item.event_id in alert_ids]
