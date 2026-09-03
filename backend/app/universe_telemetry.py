"""Universe Manager V1a Operational + Supply Telemetry (V1a ITERATE block,
Phase 3) -- real-data recording and reporting for the metrics the Master
Plan's 14-consecutive-calendar-day expansion-gate proof needs.

Governance note, load-bearing: the actual governing document
(`STRATUS_Master_Implementation_Plan_2026-08-30_REV1.md`) is not present
anywhere in this repository (confirmed by a full-repo search this session)
-- everything wired here traces to a concept this codebase's *own* existing
code already defines and names (expansion_gates.py's seven opportunity-
quality gates, thesis/diversity.py's SuppressionRecord, exploration/'s
eligibility+placement, freshness.py's classification states, the Universe
Manager V1a scheduler-state store). Three specifically-requested metrics
have zero definition anywhere in this codebase or repo -- "signal yield,"
"Top-Five Competition Ratio," and "deterministic Thesis Novelty Rate" --
and are deliberately NOT implemented here. Inventing a definition for any
of them would be exactly the "invent a substitute definition" this block
was explicitly told not to do. See `BLOCKED_METRICS` below and this
session's own final report for the precise governance gap.

Telemetry observes; it never decides. Every function in this module is
read-only with respect to the pipeline it observes -- `record_pipeline_observation()`
is called after a feed response is already fully computed, wrapped in
try/except at its one call site (logan_feed.py), so a telemetry failure
can never affect a real request's output. Nothing here touches
qualification, ranking, polling cadence, or Personal Relevance.
"""

import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from .config import memory_persistence_enabled, universe_daily_telemetry_db_path
from .universe_telemetry_store import (
    DailyObservationDelta,
    DailyUniverseTelemetry,
    UniverseDailyTelemetryStore,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from logan_core.contracts import ExplorationPlacementResult  # noqa: E402
from logan_core.diagnostics import recent_faults  # noqa: E402
from logan_core.receptors.providers import fmp_budget_snapshot  # noqa: E402
from logan_core.thesis.diversity import DiversityResult, ThesisCandidate  # noqa: E402

# Requested by name in the V1a ITERATE block but with no definition
# anywhere in this codebase, this repo's docs, or the (missing) governing
# plan file -- not implemented, not approximated, not silently redefined.
BLOCKED_METRICS = (
    "signal_yield",
    "top_five_competition_ratio",
    "deterministic_thesis_novelty_rate",
    # "evidence completeness" (MIN_COMPLETE_EVIDENCE_PAYLOAD_RATE) is also
    # blocked, distinctly: expansion_gates.py already names this gate, but
    # no field anywhere in this codebase's FeedItem/DeliveredItem/
    # ConclusionConfidence contracts marks an item's evidence payload as
    # "complete" -- computing this would mean inventing what "complete"
    # means, not observing an existing signal.
    "complete_evidence_payload_rate",
)

_store: Optional[UniverseDailyTelemetryStore] = None


def _get_store() -> Optional[UniverseDailyTelemetryStore]:
    global _store
    if not memory_persistence_enabled():
        return None
    if _store is None:
        _store = UniverseDailyTelemetryStore(universe_daily_telemetry_db_path())
    return _store


def reset_universe_telemetry_state() -> None:
    """Test-only (and general-purpose "start over") hook, mirroring every
    other store's identical reset_*_state() shape."""
    global _store
    if _store is not None:
        _store.close()
    _store = None


def _thesis_key(candidate: ThesisCandidate) -> str:
    """A "distinct thesis" is the same (entity, driver) identity
    thesis/diversity.py's own DRIVER_CAP already treats as one thesis --
    reusing that module's established concept, not inventing a second one."""
    return (
        f"{candidate.metadata.primary_entity_id}|{candidate.metadata.market_driver_tag}"
    )


def build_observation_delta(
    *,
    thesis_candidates: list[ThesisCandidate],
    diversity_result: DiversityResult,
    exploration_eligible_pool: list[ThesisCandidate],
    exploration_result: ExplorationPlacementResult,
    freshness_states: list[Optional[str]],
) -> DailyObservationDelta:
    """Pure transformation from one real `_run_feed_pipeline()` call's
    already-computed values into one day's observation delta -- no I/O, no
    provider calls, nothing invented. `qualified_opportunity_count` is
    `len(thesis_candidates)`: every thesis_candidates entry corresponds
    1:1 to a FeedItem this response actually delivered (an
    OBJECTIVELY_QUALIFIED opportunity, per contracts/universe.py's own
    four-state taxonomy), never a raw pre-qualification count.
    """
    entity_counts = Counter(c.metadata.primary_entity_id for c in thesis_candidates)
    sector_counts = Counter(c.metadata.sector or "UNKNOWN" for c in thesis_candidates)
    signal_family_counts = Counter(
        c.metadata.primary_signal_family for c in thesis_candidates
    )
    freshness_total = len(freshness_states)
    freshness_unavailable = sum(
        1 for state in freshness_states if state in (None, "UNAVAILABLE")
    )

    return DailyObservationDelta(
        qualified_opportunity_count=len(thesis_candidates),
        distinct_thesis_keys=[_thesis_key(c) for c in thesis_candidates],
        entity_impression_counts=dict(entity_counts),
        sector_impression_counts=dict(sector_counts),
        signal_family_impression_counts=dict(signal_family_counts),
        diversity_selected_count=len(diversity_result.selected),
        diversity_suppressed_count=len(diversity_result.suppressed),
        exploration_eligible_count=len(exploration_eligible_pool),
        exploration_placed_count=(
            1 if exploration_result.placed_event_id is not None else 0
        ),
        freshness_unavailable_count=freshness_unavailable,
        freshness_total_count=freshness_total,
        top_five_eligible_count=len(diversity_result.selected),
    )


def record_pipeline_observation(
    *,
    now: datetime,
    thesis_candidates: list[ThesisCandidate],
    diversity_result: DiversityResult,
    exploration_eligible_pool: list[ThesisCandidate],
    exploration_result: ExplorationPlacementResult,
    freshness_states: list[Optional[str]],
) -> None:
    """The single call site's entry point (logan_feed.py). Never raises --
    a telemetry failure must never affect a real request's response. A
    no-op, exactly like every other store in this codebase, when
    persistence is disabled."""
    try:
        store = _get_store()
        if store is None:
            return
        delta = build_observation_delta(
            thesis_candidates=thesis_candidates,
            diversity_result=diversity_result,
            exploration_eligible_pool=exploration_eligible_pool,
            exploration_result=exploration_result,
            freshness_states=freshness_states,
        )
        store.record(now.date(), delta)
    except Exception as exc:  # noqa: BLE001 -- telemetry must never break a request
        print(f"[universe-telemetry] observation recording failed, continuing: {exc}")


def daily_telemetry_range(start: date, end: date) -> list[DailyUniverseTelemetry]:
    """Real, persisted daily rows in [start, end] -- returns [] when
    persistence is disabled or no rows exist yet. A missing date inside the
    range is a real coverage gap, never backfilled or interpolated."""
    store = _get_store()
    if store is None:
        return []
    return store.range(start, end)


@dataclass(frozen=True)
class RealOperationalSignals:
    """Real, currently-observable operational signals -- explicitly
    process-lifetime/point-in-time where noted, never a genuine durable
    14-day rolling window (this codebase has no durable event log for
    per-call provider history; `recent_faults()` is an in-memory ring
    buffer capped at 200 entries, and `fmp_budget_snapshot()` is cumulative
    since process start). Callers must not present these as satisfying the
    Master Plan's literal 14-day requirement -- see `data_window` on each
    field's own docstring in `universe_report.py`'s Telemetry section.
    """

    fmp_rate_limit_responses: int
    real_call_failure_rate: Optional[float]
    peak_calls_per_minute_now: int
    unexplained_universe_changes: int


def collect_real_operational_signals(*, scheduler=None) -> RealOperationalSignals:
    """Every value here is real and currently observable -- none is a
    synthetic placeholder. `real_call_failure_rate` is None when zero real
    calls have been attempted yet (an honest "no data," not a fabricated
    0.0)."""
    faults = recent_faults(limit=200)
    fmp_rate_limit_responses = sum(1 for f in faults if f.code == "DATA-301")

    budget = fmp_budget_snapshot()
    total_real_calls = sum(c.real_calls for c in budget.by_endpoint.values())
    total_failures = sum(c.failures for c in budget.by_endpoint.values())
    real_call_failure_rate = (
        total_failures / total_real_calls if total_real_calls > 0 else None
    )

    peak_calls_per_minute_now = (
        scheduler.current_calls_per_minute() if scheduler is not None else 0
    )

    from .universe_manager import get_membership_store

    unexplained_universe_changes = 0
    membership_store = get_membership_store()
    if membership_store is not None:
        for record in membership_store.load_all():
            if not record.admission_reason_codes:
                unexplained_universe_changes += 1
            if record.effective_until is not None and not record.removal_reason:
                unexplained_universe_changes += 1

    return RealOperationalSignals(
        fmp_rate_limit_responses=fmp_rate_limit_responses,
        real_call_failure_rate=real_call_failure_rate,
        peak_calls_per_minute_now=peak_calls_per_minute_now,
        unexplained_universe_changes=unexplained_universe_changes,
    )


def real_meaningful_revision_count(start: date, end: date) -> int:
    """Real count of GLOBAL meaningful revisions in [start, end], sourced
    directly from the already-existing, already-durable
    OpportunityRevisionStore's own SQLite file (opportunity_revisions.db)
    -- no new instrumentation needed for the numerator, and no change to
    revision_store.py itself (a plain, read-only, schema-matching query
    against its file, not a private-attribute reach-in). There is
    currently no tracked denominator (total observation attempts,
    meaningful or not), so this is real evidence toward
    MIN_MEANINGFUL_REVISION_CONTENT_RATE's numerator only -- see this
    session's report for why the rate itself isn't computed.
    """
    import sqlite3

    from .config import revision_store_db_path

    if not memory_persistence_enabled():
        return 0
    path = revision_store_db_path()
    if not path.exists():
        return 0
    conn = sqlite3.connect(str(path))
    try:
        rows = conn.execute("SELECT created_at FROM opportunity_revisions").fetchall()
    finally:
        conn.close()
    count = 0
    for (created_at_text,) in rows:
        created_at = datetime.fromisoformat(created_at_text)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if start <= created_at.date() <= end:
            count += 1
    return count
