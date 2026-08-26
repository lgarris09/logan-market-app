import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
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
    Domain,
    EvidenceSnapshot,
    FeedbackSignal,
    Holding,
    InteractionType,
    Interest,
    MarketEvidenceInput,
    OpportunityRevision,
    RawSignal,
    UserModel,
)
from logan_core.convergence import StockConvergenceTracker  # noqa: E402
from logan_core.memory import MemoryStore  # noqa: E402
from logan_core.opportunity_lifecycle import (  # noqa: E402
    OpportunityLifecycleTracker,
    UserOpportunityKnowledge,
    compute_user_sync_delta,
)
from logan_core.orchestrator import Orchestrator, PipelineDependencies  # noqa: E402
from logan_core.receptors import (  # noqa: E402
    earnings_report_to_raw_signal,
    grade_change_to_raw_signal,
    quote_to_raw_signal,
    simulated_fixtures,
    tesla_ai_partnership_corroboration,
)
from logan_core.receptors.providers import (  # noqa: E402
    FmpEarningsProvider,
    FmpMarketDataProvider,
    FmpProviderError,
)
from logan_core.trigger_detection import (  # noqa: E402
    StocksTriggerEvaluator,
    evaluate_analyst_grade_condition,
    evaluate_earnings_beat_condition,
    evaluate_price_move_condition,
)
from logan_core.user_model import UserModelBuilder  # noqa: E402

from .ask_context import (  # noqa: E402
    OpportunityContext,
    OpportunityContextCache,
    build_opportunity_context,
)
from .ask_llm_provider import ConversationTurn  # noqa: E402
from .config import (  # noqa: E402
    lifecycle_store_db_path,
    live_data_only_mode,
    live_stock_tickers,
    memory_persistence_enabled,
    memory_store_db_path,
    revision_store_db_path,
    user_knowledge_store_db_path,
)
from .entity_registry import resolve  # noqa: E402
from .lifecycle_store import LifecycleStore  # noqa: E402
from .revision_store import OpportunityRevisionStore  # noqa: E402
from .user_knowledge_store import UserKnowledgeStore  # noqa: E402

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
# Stock Opportunity Logic V2: the same process-lifetime instance wired into
# _orchestrator's PipelineDependencies below -- kept as its own module
# reference (not just reached through _orchestrator.deps) so
# _run_feed_pipeline() can export/persist an entity's updated snapshot right
# after each orchestrator.run() call without reaching into the Orchestrator's
# internals. _lifecycle_store is None unless memory_persistence_enabled() --
# disabled mode (the default, and every pre-Sprint-3.6.9 test) keeps
# lifecycle tracking purely in-memory, same discipline as memory_store.
_lifecycle_tracker: OpportunityLifecycleTracker | None = None
_lifecycle_store: LifecycleStore | None = None
# Stock Opportunity Logic V2.1 (User Sync Gap): durable global revision
# history (_revision_store) and per-user knowledge pointers
# (_user_knowledge_store / _user_knowledge_cache) -- same construction/
# gating discipline as _lifecycle_tracker/_lifecycle_store immediately
# above: both are None unless live_stock_tickers() is configured (revisions
# only exist once lifecycle tracking is active at all), and the durable
# stores are additionally None unless memory_persistence_enabled(). The
# cache is keyed by (user_id, entity_id) -- process-lifetime, write-through
# to the store on every mutation, exactly mirroring _lifecycle_tracker's own
# relationship to _lifecycle_store.
_revision_store: OpportunityRevisionStore | None = None
_user_knowledge_store: UserKnowledgeStore | None = None
_user_knowledge_cache: dict[tuple[str, str], UserOpportunityKnowledge] = {}
# user_ids whose very first `/v1/opportunities` request has already been
# processed -- lets that first response stay notification-silent (nothing is
# "new" relative to a user who's never seen anything yet) without treating
# every subsequent, genuinely-new event the same way. Already correctly
# per-user (a set of user_id strings) since it was introduced -- Sprint
# 3.6.8 Block 2 only changes what values ever get inserted into it.
_baseline_established: set[str] = set()
# Sprint 3.6.8 Block 2: per-user UserModel persistence -- was a single
# process-lifetime UserModel shared by every caller (see ADR-057). Same
# in-memory-only limitation as before -- a backend restart resets this too,
# same as `_orchestrator` and `_baseline_established`.
_user_models: dict[str, UserModel] = {}

# Sprint 3.6.8 Block 2: per-user opportunity-context cache for contextual Ask
# STRATUS (was one process-wide cache keyed only by event_id -- see ADR-057.
# OpportunityContext carries personalized fields, personal_relevance/
# connection_basis/is_new_for_user included; a shared cache would let one
# user's Ask STRATUS session read another user's personalization simply by
# knowing an event_id). Refreshed wholesale, per user, on every
# `_run_feed_pipeline(user_id)` call.
_opportunity_context_caches: dict[str, OpportunityContextCache] = {}

# Sprint 3.6.7 Block 4: bounded, process-lifetime Ask STRATUS session store.
# Deliberately not persisted to SQLite -- session continuity is a short-lived
# API/UI convenience (one Ask STRATUS conversation), not durable behavioral
# preference data, so it doesn't belong in the same persistence tier as
# UserModel evidence (see docs/DECISIONS.md's Sprint 3.6.7 Block 4 ADR for
# the full reasoning). Stores only the structured continuity anchor (which
# event_id this session is discussing, and which event_ids it has already
# recorded an ASK_FOLLOWUP for) -- never raw question/answer transcript text,
# which the deterministic ask_engine doesn't need to answer well anyway.
#
# Sprint 3.6.8 Block 2: keyed by (user_id, session_id), not session_id alone
# (see ADR-057) -- a session_id is client-generated and not itself a secret,
# so an unscoped store would let a guessed/predictable session_id from one
# user read or extend another user's Ask STRATUS session. One shared cap
# across all users (not per-user) -- this remains a lightweight UI
# convenience store, not a place to spend real per-user LRU machinery on.
_ASK_SESSION_LIMIT = 500

# Sprint 3.6.8 Block 3 -- bounded conversational history (ADR-058). Small,
# reasoned integers in this codebase's existing style (FATIGUE_LIMIT=5,
# MIN_REPEAT_EVIDENCE=2), not values tuned against real usage data:
# _MAX_ASK_HISTORY_TURNS caps retained (question, answer) pairs per session
# -- generous enough to cover a real "why? / why does that matter? / which
# signal? / what would weaken this?" chain (the acceptance examples run to
# ~10 questions across a session, well within 6 retained *pairs* = 12
# messages) without ever growing unbounded. _MAX_ASK_HISTORY_CHARS is a
# secondary defensive bound -- a handful of unusually long turns could still
# blow past a reasonable prompt-size budget before hitting the turn cap;
# both bounds evict the oldest full (user, assistant) pair at a time, never
# a partial pair, so the retained history always starts on a "user" turn
# and strictly alternates (required by Anthropic's Messages API shape, see
# ask_llm_anthropic.py's generate()).
_MAX_ASK_HISTORY_TURNS = 6
_MAX_ASK_HISTORY_CHARS = 4000


class _AskSession:
    __slots__ = (
        "event_id",
        "ask_followup_recorded_event_ids",
        "last_active_at",
        "history",
    )

    def __init__(self) -> None:
        self.event_id: UUID | None = None
        self.ask_followup_recorded_event_ids: set[UUID] = set()
        self.last_active_at: datetime = datetime.now(timezone.utc)
        # Sprint 3.6.8 Block 3: bounded conversational history, oldest first.
        # Never persisted to SQLite -- same short-lived-UI-convenience
        # reasoning as the rest of this session store (see the module
        # docstring above); real question/answer text was already
        # deliberately kept out of durable storage before this block, and
        # that boundary is unchanged, just extended to cover more than one
        # turn now.
        self.history: list[ConversationTurn] = []


_ask_sessions: dict[tuple[str, str], _AskSession] = {}


def _trim_ask_history(session: "_AskSession") -> None:
    """Evicts oldest-first, one full (user, assistant) pair at a time --
    never a partial pair, which would leave `history` starting on an
    "assistant" turn and break the alternating-role invariant every
    AskLlmProvider implementation (and Anthropic's own Messages API) relies
    on. Applies both bounds; either one alone would leave the other
    unenforced.
    """
    while len(session.history) > _MAX_ASK_HISTORY_TURNS * 2:
        del session.history[:2]
    while (
        session.history
        and sum(len(turn.text) for turn in session.history) > _MAX_ASK_HISTORY_CHARS
    ):
        del session.history[:2]


def _get_or_create_ask_session(user_id: str, session_id: str) -> _AskSession:
    key = (user_id, session_id)
    session = _ask_sessions.get(key)
    if session is None:
        # Bounded eviction: a simple oldest-first drop once the cap is hit --
        # this is a lightweight UI convenience store, not a place to spend
        # real LRU machinery on.
        if len(_ask_sessions) >= _ASK_SESSION_LIMIT:
            oldest_key = min(
                _ask_sessions, key=lambda k: _ask_sessions[k].last_active_at
            )
            del _ask_sessions[oldest_key]
        session = _AskSession()
        _ask_sessions[key] = session
    session.last_active_at = datetime.now(timezone.utc)
    return session


def get_opportunity_context(
    user_id: str, event_id: UUID
) -> Optional[OpportunityContext]:
    """Authoritative server-side rehydration for contextual Ask STRATUS --
    the only way `/v1/ask` (see main.py) ever learns about a specific
    opportunity's real content. Returns None when `event_id` isn't in this
    user's current cache (never seen by this user, or the backend restarted
    since) -- the caller must treat that as "no current context," never
    fabricate one. Scoped to `user_id`'s own cache (Sprint 3.6.8 Block 2) --
    an event_id from a different user's cache is never visible here, even if
    it happens to also be a real, currently-live event_id for someone else.
    """
    cache = _opportunity_context_caches.get(user_id)
    return cache.get(event_id) if cache is not None else None


def should_record_ask_followup(user_id: str, session_id: str, event_id: UUID) -> bool:
    """Sprint 3.6.7 Block 4 feedback-loop protection: at most one
    ASK_FOLLOWUP behavioral-evidence contribution per (session, opportunity)
    pair, regardless of how many follow-up questions that session asks about
    it -- "repeated questions in one session should not count as N
    independent preference confirmations." Marks the event_id as recorded on
    the same call that returns True, so this is safe to call exactly once per
    successfully-answered contextual question. Sprint 3.6.8 Block 2: scoped
    by (user_id, session_id) -- see `_ask_sessions`'s own comment.
    """
    session = _get_or_create_ask_session(user_id, session_id)
    if event_id in session.ask_followup_recorded_event_ids:
        return False
    session.ask_followup_recorded_event_ids.add(event_id)
    return True


def set_ask_session_event(user_id: str, session_id: str, event_id: UUID) -> None:
    """Records which opportunity a session is currently discussing, so a
    later follow-up question in the same session can omit `event_id` and
    still resolve against it (see main.py's ask_logan route).

    Sprint 3.6.8 Block 3: if this session was already anchored to a
    *different* opportunity, its retained conversation history is cleared
    here -- a deliberate, deterministic reset, not a silent carryover.
    Pronoun/reference resolution ("why?", "what about that?") must never
    accidentally resolve against a different opportunity's context just
    because a session_id happened to be reused. A no-op when the anchor is
    unchanged (the overwhelmingly common case -- every question in one
    real Ask STRATUS screen visit discusses the same opportunity) or when
    this is the session's first-ever anchor (`event_id is None` before).
    """
    session = _get_or_create_ask_session(user_id, session_id)
    if session.event_id is not None and session.event_id != event_id:
        session.history = []
    session.event_id = event_id


def get_ask_session_event(user_id: str, session_id: str) -> Optional[UUID]:
    session = _ask_sessions.get((user_id, session_id))
    return session.event_id if session is not None else None


def get_ask_history(user_id: str, session_id: str) -> list[ConversationTurn]:
    """Sprint 3.6.8 Block 3: this session's bounded prior turns, oldest
    first -- what main.py's ask_logan route passes to
    `generate_grounded_answer()` so the LLM path can resolve conversational
    follow-ups. Returns an empty list for a session that doesn't exist yet
    (this is its first turn) -- never fabricates continuity that was never
    established.
    """
    session = _ask_sessions.get((user_id, session_id))
    return list(session.history) if session is not None else []


def append_ask_turn(user_id: str, session_id: str, question: str, answer: str) -> None:
    """Sprint 3.6.8 Block 3: records one real, successfully-answered turn
    (whichever path -- LLM or deterministic fallback -- actually produced
    `answer`) into this session's bounded history. Only ever called after a
    real `OpportunityContext` resolved and a real answer was produced (see
    main.py's ask_logan) -- an invalid/stale event_id or an empty message
    never reaches here, so history can never contain a fabricated or
    ungrounded exchange. Deliberately does not distinguish LLM-produced vs.
    deterministic-fallback answers: both are real, true, grounded responses
    to the user's actual question, so both are legitimate conversational
    context for a later turn to reference.
    """
    session = _get_or_create_ask_session(user_id, session_id)
    session.history.append(ConversationTurn(role="user", text=question))
    session.history.append(ConversationTurn(role="assistant", text=answer))
    _trim_ask_history(session)


def _get_orchestrator() -> Orchestrator:
    global _orchestrator
    with _state_lock:
        if _orchestrator is None:
            # Sprint 3.6.6C: trigger_detector is gated behind whether any
            # live stock ticker is configured at all, not wired
            # unconditionally. Orchestrator.run() adds a "trigger_detection"
            # ExecutionTrace layer entry for *every* raw_signal whenever any
            # detector is configured at all (see orchestrator/pipeline.py's
            # run()) -- unconditional wiring would therefore change the
            # trace shape for every simulated entity even with the live path
            # disabled, breaking the "disabled mode is byte-for-byte
            # unchanged" requirement. Gating construction on the flag keeps
            # disabled mode identical to pre-3.6.6C (no trigger_detector at
            # all, same as every other existing Orchestrator() caller) while
            # still giving the live stock path real trigger detection when
            # enabled. Read once at construction time, matching config.py's
            # own documented assumption that flipping this flag requires a
            # clean backend restart, not a mid-process toggle.
            #
            # Sprint 3.6.8 Block 5: generalized from live_nvda_earnings_
            # enabled() to live_stock_tickers() being non-empty -- the same
            # gate, now covering any configured ticker (NVDA, TSLA, AAPL, or
            # more), not just NVDA specifically. live_stock_tickers() itself
            # falls back to the original single-ticker flag when the new one
            # isn't set (see config.py), so this is a strict generalization,
            # not a behavior change for existing STRATUS_LIVE_NVDA_EARNINGS
            # deployments/tests.
            #
            # Sprint 3.6.7 Block 2: convergence_tracker is gated behind the
            # same flag, for the same reason -- it must be constructed once
            # and reused for the life of this process (its 30-minute window
            # is meaningless across fresh instances), exactly like world_model
            # already is via the shared Orchestrator itself. Disabled mode
            # gets no convergence_tracker at all, same as no trigger_detector.
            #
            # Sprint 3.6.7 Block 3: memory_store is independently gated
            # behind memory_persistence_enabled() -- orthogonal to the live-
            # NVDA flag above (persistence is about durability across
            # restarts, not about live vs. simulated market data). Disabled
            # (the default) reconstructs the exact same in-memory
            # MemoryStore() every pre-Block-3 caller/test already gets, so
            # the entire existing backend test suite (which never sets
            # STRATUS_PERSIST_MEMORY) stays isolated to in-memory state.
            memory_store = (
                MemoryStore(db_path=memory_store_db_path())
                if memory_persistence_enabled()
                else MemoryStore()
            )

            # Stock Opportunity Logic V2: gated behind the same
            # live_stock_tickers() flag as trigger_detector/
            # convergence_tracker immediately above, for the identical
            # reason -- Orchestrator.run() adds an "opportunity_lifecycle"
            # ExecutionTrace layer entry whenever a lifecycle_tracker is
            # wired at all, so unconditional wiring would change the trace
            # shape (and, more importantly, start engaging
            # changed_since_view-driven cooldown) for every simulated
            # fixture too, not just the live stocks path this block is
            # actually about. Demo-mode (no live tickers configured) stays
            # byte-for-byte the pre-Sprint-3.6.9 behavior. Persisted the
            # same way memory_store is, independently of the live-data gate
            # -- see lifecycle_store.py.
            global _lifecycle_tracker, _lifecycle_store
            global _revision_store, _user_knowledge_store, _user_knowledge_cache
            _lifecycle_tracker = None
            _lifecycle_store = None
            _revision_store = None
            _user_knowledge_store = None
            _user_knowledge_cache = {}
            if live_stock_tickers():
                _lifecycle_tracker = OpportunityLifecycleTracker()
                if memory_persistence_enabled():
                    _lifecycle_store = LifecycleStore(lifecycle_store_db_path())
                    for snapshot in _lifecycle_store.load_all():
                        _lifecycle_tracker.load_snapshot(snapshot)
                    # Stock Opportunity Logic V2.1 (User Sync Gap): revision
                    # history and per-user knowledge pointers are persisted
                    # independently of the lifecycle snapshot table, but
                    # gated on the identical two conditions (lifecycle
                    # tracking active + persistence enabled) -- a revision
                    # number is meaningless without an active tracker to
                    # compare it against.
                    _revision_store = OpportunityRevisionStore(revision_store_db_path())
                    _user_knowledge_store = UserKnowledgeStore(
                        user_knowledge_store_db_path()
                    )
                    for knowledge in _user_knowledge_store.load_all():
                        _user_knowledge_cache[
                            (knowledge.user_id, knowledge.entity_id)
                        ] = knowledge

            deps = (
                PipelineDependencies(
                    trigger_detector=StocksTriggerEvaluator(),
                    convergence_tracker=StockConvergenceTracker(),
                    lifecycle_tracker=_lifecycle_tracker,
                    memory_store=memory_store,
                )
                if live_stock_tickers()
                else PipelineDependencies(memory_store=memory_store)
            )
            _orchestrator = Orchestrator(deps=deps)
        return _orchestrator


def _get_user_model(
    orchestrator: Orchestrator, user_id: str, now: datetime
) -> UserModel:
    """Per-user, process-lifetime UserModel persistence (Sprint 3.6.8 Block
    2, ADR-057 -- was a single shared UserModel for every caller). Seeded
    once per user_id, then every later call rebuilds via
    UserModelBuilder.build() against that user's own accumulated
    `feedback_record` history in the shared Orchestrator's MemoryStore
    (written by `record_interaction()` below through the normal Feedback ->
    Learning path, and now correctly filtered by `memory_store.query(user_id=...)`
    -- see ADR-057 for the pre-Block-2 cross-user leak this closes). This is
    what lets repeated card-open/dwell/notification-tap evidence actually
    compound into established_behaviors/domain_preferences/
    Interest(source="inferred") *across* requests, not just within one.

    Seed data: `LOCAL_FOUNDER_USER_ID` alone gets the founder's real explicit
    holdings/interests (NVDA holding, AI_SECTOR interest) -- unchanged from
    every pre-Block-2 caller. Any other user_id gets UserModelBuilder.seed()'s
    own blank/unknown defaults (no holdings, no explicit interests,
    risk_tolerance="unknown") -- the founder's specific portfolio is
    founder-only demo data, never copied into another user's model.
    Explicit holdings/interests/risk_tolerance are preserved unchanged by
    `.build()` itself (see user_model/model.py) -- rebuilding here never
    weakens or overwrites them.
    """
    global _user_models
    with _state_lock:
        existing = _user_models.get(user_id)
        if existing is None:
            if user_id == LOCAL_FOUNDER_USER_ID:
                seeded = UserModelBuilder().seed(
                    user_id=user_id,
                    holdings=[
                        Holding(
                            domain="stocks",
                            entity_id="NVDA",
                            display_name="NVIDIA",
                            added_at=now,
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
            else:
                seeded = UserModelBuilder().seed(user_id=user_id)
            _user_models[user_id] = seeded
        else:
            memory_records = orchestrator.deps.memory_store.query(user_id=user_id)
            _user_models[user_id] = UserModelBuilder().build(
                user_id=user_id,
                memory_records=memory_records,
                base=existing,
            )
        return _user_models[user_id]


def _max_opt(a: Optional[int], b: Optional[int]) -> Optional[int]:
    """None-safe max -- used by `_advance_user_knowledge` so a pointer only
    ever moves forward, never regresses or gets clobbered by a stale/lower
    value from a racing caller.
    """
    if a is None:
        return b
    if b is None:
        return a
    return max(a, b)


def _get_user_knowledge(
    user_id: str, entity_id: str
) -> Optional[UserOpportunityKnowledge]:
    return _user_knowledge_cache.get((user_id, entity_id))


def _advance_user_knowledge(
    user_id: str,
    entity_id: str,
    now: datetime,
    *,
    seen_revision: Optional[int] = None,
    notified_revision: Optional[int] = None,
    opened_revision: Optional[int] = None,
) -> None:
    """The single UPSERT path for `UserOpportunityKnowledge` -- one row per
    (user_id, entity_id), pointers only ever advanced (via `_max_opt`), never
    one row per interaction (per the explicit product requirement). A no-op
    write (all three revisions None) still updates `updated_at`, which is
    harmless and keeps this the one code path every caller uses rather than
    special-casing "nothing to advance."
    """
    key = (user_id, entity_id)
    existing = _user_knowledge_cache.get(key)
    updated = UserOpportunityKnowledge(
        user_id=user_id,
        entity_id=entity_id,
        last_seen_revision=_max_opt(
            existing.last_seen_revision if existing else None, seen_revision
        ),
        last_notified_revision=_max_opt(
            existing.last_notified_revision if existing else None,
            notified_revision,
        ),
        last_opened_revision=_max_opt(
            existing.last_opened_revision if existing else None, opened_revision
        ),
        updated_at=now,
    )
    _user_knowledge_cache[key] = updated
    if _user_knowledge_store is not None:
        _user_knowledge_store.save(updated)


def mark_user_notified(
    user_id: str,
    entity_id: str,
    revision: Optional[int],
    now: Optional[datetime] = None,
) -> None:
    """Called by notifications.py immediately after a real Expo dispatch
    succeeds for one (user, item) pair -- the only place
    `last_notified_revision` ever advances. Deliberately distinct from
    "alert eligible" (PrioritizedItem.interruption == 'alert'): eligibility
    alone is not a real send, and only a real send should ever count as
    "this user was notified." A no-op when `revision` is None (lifecycle/
    revision tracking not active for this entity) -- there is nothing to
    advance a pointer against.
    """
    if revision is None:
        return
    with _state_lock:
        _advance_user_knowledge(
            user_id,
            entity_id,
            now or datetime.now(timezone.utc),
            notified_revision=revision,
        )


def _live_earnings_raw_signal(ticker: str, now: datetime) -> RawSignal | None:
    """Sprint 3.6.6C, generalized Sprint 3.6.8 Block 5 (was
    `_live_nvda_raw_signal`, hardcoded to "NVDA"): attempts to replace a
    configured ticker's simulated fixture with a real FMP-driven earnings
    signal. Returns None on any failure -- FMP unreachable, auth failure,
    malformed response, or genuinely no reported earnings on file -- so the
    caller can fall back to the simulated fixture (in demo mode -- see
    config.live_data_only_mode()) or leave the ticker honestly absent (in
    live-data-only mode). Never raises: every FmpProviderError is caught
    here so a live-data hiccup can never take down /v1/opportunities.
    Never silently presents simulated data as live either -- the caller
    only substitutes this return value in place of whatever it already had
    for `ticker` when it is not None.

    Also returns None when a real report was fetched but does not satisfy
    STOCK_EARNINGS_BEAT. A valid provider response is not itself an
    opportunity -- surfacing only happens when the implemented TriggerEvent
    actually fires, not merely because FMP returned some usable data.
    Reuses evaluate_earnings_beat_condition (the same pure function
    StocksTriggerEvaluator.evaluate() calls) rather than re-deriving the
    fire condition, so this pre-check and the orchestrator's own later
    trigger_detection layer can never disagree. Deliberately does not also
    check STOCK_EARNINGS_MISS/IN_LINE (both real, registered triggers as of
    ADR-045) -- preserving the exact pre-Block-5 substitution semantics
    rather than silently broadening them; see the Block 5 ADR's own
    deferred-items list.
    """
    try:
        provider = FmpEarningsProvider()
    except FmpProviderError as exc:
        print(f"[live-stocks] {ticker}: provider unavailable, source=fixture: {exc}")
        return None

    try:
        report = provider.fetch_latest_earnings(ticker)
    except FmpProviderError as exc:
        print(f"[live-stocks] {ticker}: FMP fetch failed, source=fixture: {exc}")
        return None

    if report is None:
        print(f"[live-stocks] {ticker}: FMP has no reported earnings, source=fixture")
        return None

    fired, beat_pct, reason = evaluate_earnings_beat_condition(
        report.actual_eps, report.consensus_eps
    )
    if not fired:
        print(
            f"[live-stocks] {ticker}: real report fetched but STOCK_EARNINGS_BEAT "
            f"did not fire ({reason}), source=fixture"
        )
        return None

    print(
        f"[live-stocks] {ticker}: using real FMP earnings report dated "
        f"{report.report_timestamp.date()} (source={report.source_id}, "
        f"beat_pct={beat_pct:.2f})"
    )
    return earnings_report_to_raw_signal(report)


def _live_price_move_raw_signal(ticker: str, now: datetime) -> RawSignal | None:
    """Sprint 3.6.7 Block 2, generalized Sprint 3.6.8 Block 5 (was
    `_live_nvda_price_move_raw_signal`): wires the live
    STOCK_PRICE_MOVE_SIGNIFICANT signal into the live equities path for a
    configured ticker -- an *additional* raw_signal alongside earnings, not
    a replacement. Returns None on any provider failure or when the fetched
    quote does not itself satisfy STOCK_PRICE_MOVE_SIGNIFICANT -- same "a
    valid response is not itself an opportunity" discipline as
    `_live_earnings_raw_signal`. An ordinary trading day contributes
    nothing extra, never a fabricated non-event.
    """
    try:
        provider = FmpMarketDataProvider()
    except FmpProviderError as exc:
        print(
            f"[live-stocks] {ticker}: market-data provider unavailable, "
            f"skipping price move: {exc}"
        )
        return None

    try:
        quote = provider.fetch_quote(ticker)
    except FmpProviderError as exc:
        print(
            f"[live-stocks] {ticker}: FMP quote fetch failed, skipping price move: {exc}"
        )
        return None

    if quote is None:
        print(f"[live-stocks] {ticker}: FMP has no quote, skipping price move")
        return None

    fired, change_pct, reason = evaluate_price_move_condition(quote.change_pct)
    if not fired:
        print(
            f"[live-stocks] {ticker}: real quote fetched but "
            f"STOCK_PRICE_MOVE_SIGNIFICANT did not fire ({reason}), skipping price move"
        )
        return None

    print(
        f"[live-stocks] {ticker}: using real FMP quote dated "
        f"{quote.quote_timestamp.date()} for price move "
        f"(source={quote.source_id}, change_pct={change_pct:.2f})"
    )
    return quote_to_raw_signal(quote)


def _live_analyst_grade_raw_signal(ticker: str, now: datetime) -> RawSignal | None:
    """Sprint 3.6.7 Block 2, generalized Sprint 3.6.8 Block 5 (was
    `_live_nvda_analyst_grade_raw_signal`): wires the live
    STOCK_ANALYST_UPGRADE/STOCK_ANALYST_DOWNGRADE signal into the live
    equities path for a configured ticker, on the same terms as
    `_live_price_move_raw_signal` above (additional signal, not a
    replacement; None on any failure or non-qualifying result).
    """
    try:
        provider = FmpMarketDataProvider()
    except FmpProviderError as exc:
        print(
            f"[live-stocks] {ticker}: market-data provider unavailable, "
            f"skipping analyst grade: {exc}"
        )
        return None

    try:
        grade = provider.fetch_latest_grade_change(ticker)
    except FmpProviderError as exc:
        print(
            f"[live-stocks] {ticker}: FMP grades fetch failed, skipping analyst grade: {exc}"
        )
        return None

    if grade is None:
        print(
            f"[live-stocks] {ticker}: FMP has no analyst grade, skipping analyst grade"
        )
        return None

    trigger_code, reason = evaluate_analyst_grade_condition(grade.action)
    if trigger_code is None:
        print(
            f"[live-stocks] {ticker}: real grade fetched but no analyst trigger "
            f"fired ({reason}), skipping analyst grade"
        )
        return None

    print(
        f"[live-stocks] {ticker}: using real FMP grade dated "
        f"{grade.action_date.date()} for analyst grade "
        f"(source={grade.source_id}, action={grade.action})"
    )
    return grade_change_to_raw_signal(grade)


# Stock Opportunity Logic V2.2 (Evidence + Trajectory Enrichment): the broad-
# market benchmark for "market-relative performance" -- SPY (the S&P 500
# ETF), a standard, widely-recognized proxy, fetched through the exact same
# FmpMarketDataProvider.fetch_quote() this file already calls for every live
# ticker. No new endpoint, no new vendor -- just one more symbol through an
# already-integrated call.
MARKET_BENCHMARK_SYMBOL = "SPY"

# Sector -> SPDR Select Sector ETF, for "sector-relative performance" --
# reasoned, industry-standard mappings (the same ETF family widely used for
# this exact purpose), not derived from any FMP field. A sector this table
# doesn't recognize simply gets no sector-relative evidence this poll (never
# a fabricated benchmark) -- see _fetch_market_evidence's own handling.
_SECTOR_BENCHMARK_SYMBOLS: dict[str, str] = {
    "Technology": "XLK",
    "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP",
    "Energy": "XLE",
    "Financial Services": "XLF",
    "Healthcare": "XLV",
    "Industrials": "XLI",
    "Communication Services": "XLC",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Basic Materials": "XLB",
}


def _fetch_market_evidence(ticker: str, now: datetime) -> MarketEvidenceInput | None:
    """Stock Opportunity Logic V2.2: assembles this poll's objective market
    evidence for one live-substituted ticker -- its own quote (price/
    change_pct/volume), the broad-market benchmark's quote, its sector
    benchmark's quote (when its profile resolves to a recognized sector),
    and its company profile (sector/average_volume/beta). Every fetch is
    independently best-effort: a failure fetching the profile or a benchmark
    quote degrades that specific field to None rather than failing the whole
    evidence attempt (an entity with a real quote but no recognized sector
    still gets trigger-price/market-relative evidence, just no sector-
    relative figure) -- matching this file's existing per-signal failure
    isolation discipline. Returns None only when the entity's own quote
    itself is unavailable, since without a real price there is nothing to
    build evidence from at all.
    """
    try:
        provider = FmpMarketDataProvider()
    except FmpProviderError as exc:
        print(
            f"[live-stocks] {ticker}: market-data provider unavailable, skipping evidence: {exc}"
        )
        return None

    try:
        quote = provider.fetch_quote(ticker)
    except FmpProviderError as exc:
        print(
            f"[live-stocks] {ticker}: FMP quote fetch failed, skipping evidence: {exc}"
        )
        return None
    if quote is None:
        print(f"[live-stocks] {ticker}: FMP has no quote, skipping evidence")
        return None

    market_change_pct: Optional[float] = None
    try:
        market_quote = provider.fetch_quote(MARKET_BENCHMARK_SYMBOL)
        if market_quote is not None:
            market_change_pct = market_quote.change_pct
    except FmpProviderError as exc:
        print(f"[live-stocks] {ticker}: market benchmark fetch failed: {exc}")

    sector: Optional[str] = None
    average_volume: Optional[float] = None
    beta: Optional[float] = None
    try:
        profile = provider.fetch_company_profile(ticker)
        if profile is not None:
            sector = profile.sector
            average_volume = profile.average_volume
            beta = profile.beta
    except FmpProviderError as exc:
        print(f"[live-stocks] {ticker}: profile fetch failed: {exc}")

    sector_benchmark_symbol = _SECTOR_BENCHMARK_SYMBOLS.get(sector) if sector else None
    sector_change_pct: Optional[float] = None
    if sector_benchmark_symbol is not None:
        try:
            sector_quote = provider.fetch_quote(sector_benchmark_symbol)
            if sector_quote is not None:
                sector_change_pct = sector_quote.change_pct
        except FmpProviderError as exc:
            print(f"[live-stocks] {ticker}: sector benchmark fetch failed: {exc}")

    return MarketEvidenceInput(
        price=quote.price,
        change_pct=quote.change_pct,
        market_change_pct=market_change_pct,
        sector=sector,
        sector_benchmark_symbol=sector_benchmark_symbol,
        sector_change_pct=sector_change_pct,
        volume=quote.volume,
        average_volume=average_volume,
        beta=beta,
    )


def reset_pipeline_state() -> None:
    """Test-only (and general-purpose "start over") hook: drops the persistent
    Orchestrator, baseline tracking, and persisted UserModel, so the next call
    behaves like a fresh process start. Tests that compare two pipeline runs
    and expect them to be independent (rather than exercising the new
    deliberate cross-request persistence) should call this between runs -- see
    backend/tests/test_opportunities_api.py and test_logan_feed.py.
    """
    global _orchestrator, _lifecycle_tracker, _lifecycle_store
    global _revision_store, _user_knowledge_store, _user_knowledge_cache
    with _state_lock:
        if _orchestrator is not None:
            # Sprint 3.6.7 Block 3: releases the SQLite connection cleanly
            # when persistence is enabled -- a no-op for the default
            # in-memory MemoryStore (close() only does anything when a
            # db_path was actually given). Without this, repeated resets
            # (every test in a persistence-focused suite) would leak one
            # open connection to the same file per reset.
            _orchestrator.deps.memory_store.close()
        if _lifecycle_store is not None:
            _lifecycle_store.close()
        if _revision_store is not None:
            _revision_store.close()
        if _user_knowledge_store is not None:
            _user_knowledge_store.close()
        _orchestrator = None
        _lifecycle_tracker = None
        _lifecycle_store = None
        _revision_store = None
        _user_knowledge_store = None
        _user_knowledge_cache = {}
        _baseline_established.clear()
        _user_models.clear()
        _opportunity_context_caches.clear()
        _ask_sessions.clear()


def purge_user(user_id: str) -> None:
    """V2.3A (Identity & Account Foundation) -- the logan_feed half of
    `purge_user_data()` (see backend/app/account_lifecycle.py, the central
    account-deletion primitive). Removes every piece of this user's state
    this module owns or holds a reference to: MemoryStore records,
    per-(user_id, entity_id) revision-knowledge rows, PrioritizationEngine's
    in-memory AttentionState, the process-lifetime UserModel/baseline/
    OpportunityContext-cache entries, and any Ask STRATUS session anchored
    to this user_id. Never touches objective/global opportunity state
    (LifecycleStore, RevisionStore, World Model) -- that data is not
    user-owned and must survive this user's deletion unchanged, per the
    explicit "objective intelligence remains global" boundary.
    """
    with _state_lock:
        if _orchestrator is not None:
            _orchestrator.deps.memory_store.delete_user(user_id)
            _orchestrator.deps.prioritization_engine.delete_user(user_id)
        if _user_knowledge_store is not None:
            _user_knowledge_store.delete_user(user_id)
        for key in [k for k in _user_knowledge_cache if k[0] == user_id]:
            del _user_knowledge_cache[key]
        _baseline_established.discard(user_id)
        _user_models.pop(user_id, None)
        _opportunity_context_caches.pop(user_id, None)
        for key in [k for k in _ask_sessions if k[0] == user_id]:
            del _ask_sessions[key]


def mark_notifications_reviewed(user_id: str, event_ids: list[UUID]) -> None:
    """Called by the `/v1/notifications/review` route -- the only way an
    event_id's `is_new_for_user` clears (re-observing the same event again
    does not clear it; see PrioritizationEngine.prioritize()). Scoped to
    `user_id` (Sprint 3.6.8 Block 2) -- PrioritizationEngine's AttentionState
    was already stored per-user internally (see prioritization/engine.py's
    `_states` dict); this was simply never called with any user_id besides
    the founder constant before this block.
    """
    orchestrator = _get_orchestrator()
    with _state_lock:
        orchestrator.deps.prioritization_engine.mark_reviewed(user_id, event_ids)
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

    mark_pushed_notifications_reviewed(user_id, event_ids)


def record_interaction(
    user_id: str,
    event_id: UUID,
    entity_id: str,
    domain: Domain,
    interaction_type: InteractionType,
    duration_ms: Optional[int] = None,
) -> None:
    """Behavioral-personalization foundation (Part A, ADR-047): reuses the
    existing, unmodified FeedbackSignal -> FeedbackEngine -> LearningEngine ->
    MemoryStore path, going through Orchestrator.run_feedback_loop() rather
    than building a parallel personalization system or reaching around it to
    call feedback_engine/learning_engine directly -- Orchestrator remains the
    sole owner of the interpret -> process_feedback sequencing (ADR-016/
    ADR-047's layer-ownership boundary).

    Passes a content-builder callable (behavioral-personalization pass) so
    `content` is built *after* FeedbackEngine.interpret() runs, from its own
    inferred_intent/intent_confidence -- still no free-form client text, but
    now enough for UserModelBuilder.build() to deterministically fold
    repeated behavioral evidence into the UserModel later without re-parsing
    prose or re-deriving an interpretation this layer already computed once.
    run_feedback_loop() interprets the interaction exactly once either way.

    Sprint 3.6.7 Block 3: `interaction_type == "impression"` is a
    deterministic exposure fact, not ambiguous user behavior -- it never
    reaches FeedbackEngine.interpret() at all, routed instead through
    Orchestrator.run_exposure_loop() -> LearningEngine.process_exposure()
    (see that method's own docstring for why this is a separate path, not a
    special case inside run_feedback_loop()).

    Sprint 3.6.8 Block 2 (ADR-057): `user_id` is now the caller's real
    resolved identity (see user_context.resolve_user_id), not a hardcoded
    constant -- every write this produces lands in MemoryStore under that
    user_id, and PrioritizationEngine's AttentionState/fatigue tracking is
    scoped to it.

    Stock Opportunity Logic V2.1 (User Sync Gap): this is the ONLY place
    `last_seen_revision`/`last_opened_revision` ever advance -- deliberately
    never inside `_run_feed_pipeline()`/the GET /v1/opportunities path, per
    the explicit "fetching a feed does not imply seen" product rule. Every
    real interaction_type reaching this function (impression included) is
    already defensible evidence the user encountered this specific
    opportunity in the app -- `useImpressionTracking.ts`'s own docstring is
    explicit that generation/serialization into an API response alone is
    NOT an impression, only becoming the field's focused card is -- so
    "seen" advances on any interaction_type; "opened" (a strictly stronger
    signal) advances only on "view", which mirrors the existing card-
    disclosure/dwell-tracking semantics exactly (useCardDwellTracking.ts
    submits "view" only for a real open->close span, never a mere render).
    A no-op when lifecycle/revision tracking isn't active for this entity
    (current_revision is None) -- there is nothing to advance a pointer
    against.
    """
    orchestrator = _get_orchestrator()
    snapshot = (
        _lifecycle_tracker.export_snapshot(entity_id)
        if _lifecycle_tracker is not None
        else None
    )
    current_revision = snapshot.revision if snapshot is not None else None
    if current_revision is not None:
        with _state_lock:
            _advance_user_knowledge(
                user_id,
                entity_id,
                datetime.now(timezone.utc),
                seen_revision=current_revision,
                opened_revision=(
                    current_revision if interaction_type == "view" else None
                ),
            )

    if interaction_type == "impression":
        with _state_lock:
            orchestrator.run_exposure_loop(
                event_id=event_id,
                user_id=user_id,
                domain=domain,
                entity_id=entity_id,
            )
        return

    def _build_content(feedback: FeedbackSignal) -> dict:
        return {
            "interaction_type": feedback.interaction_type,
            "entity_id": entity_id,
            "domain": domain,
            "inferred_intent": feedback.inferred_intent,
            "intent_confidence": feedback.intent_confidence,
            "duration_ms": feedback.duration_ms,
        }

    with _state_lock:
        orchestrator.run_feedback_loop(
            event_id=event_id,
            user_id=user_id,
            domain=domain,
            entities=[entity_id],
            interaction_type=interaction_type,
            content=_build_content,
            duration_ms=duration_ms,
        )


# Sprint 3.6.6I: the two points per entity below represent readings taken at
# the start and end of one observation window, not two readings both taken
# "now" -- see _engagement_samples' own comment for why that distinction
# matters (it was silently producing an artificially inflated
# engagement_velocity for nearly every entity). ENGAGEMENT_SAMPLE_WINDOW is
# that window's length. Chosen to reuse an existing, already-meaningful time
# constant in this system rather than invent a new arbitrary number:
# world_model/model.py's DEDUP_WINDOW (1 hour) is STRATUS's own established
# granularity for "how long an observation stays part of the same ongoing
# event" -- an engagement snapshot taken at the start vs. end of that same
# window is a defensible, in-universe-consistent choice for what these two
# fixture points represent. Not tuned to produce any particular downstream
# alert count -- see docs/DECISIONS.md's Sprint 3.6.6I ADR for the full
# reasoning and the before/after eligibility trace this produced.
ENGAGEMENT_SAMPLE_WINDOW = timedelta(hours=1)

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

    # Stock Opportunity Logic V2 (see docs/DECISIONS.md's Sprint 3.6.9 ADR).
    # All default to None/False and are additive -- an entity with no active
    # lifecycle tracking (demo mode, no live tickers configured) simply
    # reports lifecycle_state=None rather than a fabricated value; the
    # mobile layer treats absence as "lifecycle metadata not available for
    # this item," not an error.
    #
    # lifecycle_state: the current bounded state (new/developing/
    # high_attention/monitoring/cooling/stale/expired) -- see
    # logan_core/contracts/lifecycle.py's LifecycleState.
    lifecycle_state: str | None = None
    # is_updated: true iff this specific poll produced a *meaningful* change
    # (LifecycleDelta.is_meaningful) -- deliberately a different concept
    # from is_new_for_user above (that's about whether *this user* has
    # reviewed this event_id; this is about whether the underlying
    # opportunity itself has genuinely changed since STRATUS last evaluated
    # it, independent of whether any particular user has looked at it yet).
    is_updated: bool = False
    # meaningful_change_type: what kind of change this was (e.g.
    # "confidence_increased", "aged_to_cooling", "none") -- see
    # MeaningfulChangeType. Present even when is_updated is False (value
    # "none"), so the mobile layer never has to special-case its absence.
    meaningful_change_type: str | None = None
    # lifecycle_reason: one human-readable sentence explaining the current
    # lifecycle_state/meaningful_change_type -- serves both "why is this
    # still being shown" (a monitoring/cooling/stale explanation) and "why
    # does this deserve your attention now" (a strengthening/reactivation
    # explanation), whichever currently applies. One field, not two
    # separately-maintained ones, since exactly one of those framings is
    # ever true for a given poll.
    lifecycle_reason: str | None = None
    last_meaningful_change_at: datetime | None = None
    # Hours since STRATUS itself first surfaced this opportunity --
    # deliberately measured from first observation, not from the underlying
    # signal's own real-world event date (which, for something like an
    # earnings report, is frequently already old by the time it's first
    # detected and would misrepresent how long this has actually been
    # sitting in the user's Attention Field unchanged -- see the ADR).
    thesis_age_hours: float | None = None

    # Stock Opportunity Logic V2.1 (User Sync Gap, see docs/DECISIONS.md).
    # Both None whenever lifecycle/revision tracking isn't active for this
    # entity -- additive, same discipline as the V2 fields above.
    #
    # opportunity_revision: the entity's current *global* meaningful-
    # revision number (objective, identical for every user -- see
    # LifecycleSnapshot.revision). Not itself personalized; two users see
    # the same number for the same real-world opportunity.
    opportunity_revision: int | None = None
    # user_sync_status: THIS user's own knowledge state relative to
    # opportunity_revision -- "UP_TO_DATE" | "NEW_TO_USER" |
    # "UPDATED_SINCE_SEEN" | "NOTIFIED_BUT_UNSEEN". See
    # logan_core/opportunity_lifecycle/sync.py's SyncStatus for the exact,
    # deterministic decision rule. This is the field that answers "is this
    # change new to this specific user," distinct from is_updated above
    # (which is global/objective) and is_new_for_user (which is about badge/
    # review state, not revision knowledge).
    user_sync_status: str | None = None

    # Stock Opportunity Logic V2.2 (Evidence + Trajectory Enrichment, see
    # docs/DECISIONS.md). Both None/default whenever lifecycle tracking
    # isn't active OR no live market evidence was fetched this poll (a
    # provider failure, or the entity isn't a live-substituted ticker) --
    # additive, same discipline as every prior lifecycle_*/opportunity_*
    # field on this contract.
    #
    # trajectory: is the objective evidence strengthening/steady/weakening/
    # reversing -- a dimension deliberately separate from lifecycle_state
    # above (lifecycle_state answers "is this still active as a thesis";
    # trajectory answers "which way is the evidence moving").
    trajectory: str = "STEADY"
    previous_trajectory: str = "STEADY"
    trajectory_reason: str | None = None
    # evidence: typed/queryable core evidence (trigger price, price change
    # since trigger/since last revision, market- and sector-relative
    # performance, volume vs. average, beta-normalized move) -- a nested
    # structured object, not an opaque JSON blob, mirroring how
    # `delivered_item` is already a typed sub-object on this same contract.
    evidence: EvidenceSnapshot | None = None


class DemoFeedResponse(BaseModel):
    items: list[FeedItem]
    generated_at: datetime


def _spaced_timestamps(now: datetime, count: int, window: timedelta) -> list[datetime]:
    """Evenly spaces `count` timestamps across `window`, ending at `now` (the
    most recent reading) -- the same shape a real periodic poll would
    produce. A single timestamp has no interval to span, so it's just `now`.
    Pulled out of _engagement_samples as its own pure function specifically
    so this spacing behavior is testable independent of the entity fixture
    lookup below.
    """
    if count <= 1:
        return [now]
    step = window / (count - 1)
    return [now - window + step * i for i in range(count)]


def _engagement_samples(entity_id: str, now: datetime) -> list[EngagementSample]:
    """Sprint 3.6.6I fix: every sample previously shared the identical
    `observed_at=now` timestamp. CommunityIntelligenceEngine.measure() floors
    `hours_elapsed` at 0.25 when the elapsed time is zero (its own division-
    by-zero guard) and computes engagement_velocity as a raw point-delta
    divided by that floor -- with two same-timestamp samples, this silently
    multiplied every entity's real point-delta by 4, which pushed
    lifecycle_state to "emerging" for nearly every entity regardless of
    whether its underlying delta was actually a meaningful spike. Real-Case-
    Instrumented trace (2026-08-19, prior to this fix): 10 of 11 simulated
    entities computed "emerging" this way -- an artifact of fixture
    construction, not a real signal.

    Fixed by spreading each entity's points evenly across
    ENGAGEMENT_SAMPLE_WINDOW ending at `now` (first point = start of window,
    last point = now) -- the same shape a real periodic engagement poll
    would produce, and the same underlying (volume, unique_users,
    saves_shares, questions) fixture values as before (untouched -- this is
    a timing fix only, not a data/tuning change). CommunityIntelligenceEngine
    itself, its lifecycle thresholds, PolicyEngine, PrioritizationEngine, and
    STRATUS Watch's dispatch logic are all unmodified.
    """
    points = _ENGAGEMENT_BY_ENTITY.get(entity_id, [(5, 4, 0, 0), (8, 6, 1, 0)])
    timestamps = _spaced_timestamps(now, len(points), ENGAGEMENT_SAMPLE_WINDOW)
    return [
        EngagementSample(
            observed_at=t,
            volume_at_point=v,
            unique_users=u,
            saves_shares=s,
            questions=q,
        )
        for t, (v, u, s, q) in zip(timestamps, points, strict=True)
    ]


def _run_feed_pipeline(user_id: str) -> tuple[list[FeedItem], datetime, list[UUID]]:
    """Runs the simulated entity fixtures (Tesla, NVIDIA, Apple, Bitcoin, Federal
    Reserve, NFL, Music, Polymarket, Markets, Oil, AI) through one shared Orchestrator
    instance and builds the ranked, connected feed for `user_id`.

    Sharing one Orchestrator (and therefore one World Model and one Memory
    Store) across every caller lets genuinely overlapping entities (e.g.
    Tesla's downstream ripple touching NVIDIA and the AI sector, which have
    their own direct fixtures too) connect to each other, and lets two
    different users see the identical `event_id` for the identical
    real-world fact (World Model dedup is deliberately not user-scoped --
    "NVIDIA beat earnings" is one shared event, not N independent copies).
    What *is* user-scoped, per this call (Sprint 3.6.8 Block 2, ADR-057): the
    UserModel folded into `orchestrator.run()`, PrioritizationEngine's
    AttentionState (fatigue/cooldown/notification-review, via `user_id`
    passed straight through to `orchestrator.run()`), and the
    OpportunityContext cache and `is_new_for_user`/baseline bookkeeping built
    from this run's results, below.

    Single source of truth for both the versioned `/v1/opportunities` API
    (`opportunities.py`) and the legacy `/v1/demo/feed` route below -- neither
    duplicates this computation.

    The shared Orchestrator instance persists *across* calls to this
    function (see `_get_orchestrator()` above), not just within one -- this
    is what lets the same underlying opportunity keep a stable `event_id` and
    correct `is_new_for_user` across repeated requests, for the life of this
    process. Each user's own UserModel is likewise process-lifetime
    persistent (see `_get_user_model()`), not reseeded per call -- repeated
    card-open/dwell/notification-tap evidence recorded via
    `record_interaction()` between requests now actually compounds into that
    user's own inferred behavioral fields, never another user's.
    """
    now = datetime.now(timezone.utc)

    orchestrator = _get_orchestrator()
    user_model = _get_user_model(orchestrator, user_id, now)

    # Sprint 3.6.8 Block 5 (ADR-060): the production-vs-demo runtime
    # boundary. Demo/development mode (config.live_data_only_mode() ==
    # False, the default -- every pre-Block-5 caller/test) seeds `fixtures`
    # from the full simulated 11-entity set, exactly as before. Live-data-
    # only mode starts with nothing at all -- an entity only ever appears
    # this poll if a real live fetch below actually substitutes it. This is
    # what makes "unsupported domains do NOT quietly receive simulated
    # opportunities" and "provider failure does NOT substitute a fixture"
    # true in that mode: there is no simulated fallback sitting in `fixtures`
    # to fall back to in the first place.
    fixtures = {} if live_data_only_mode() else simulated_fixtures(now)

    # Sprint 3.6.6C, generalized Sprint 3.6.8 Block 5: replaces (never adds
    # alongside) each configured live ticker's fixture with a real
    # FMP-driven earnings signal when FMP actually returns usable, qualifying
    # data -- `fixtures` is keyed by entity_id, so this dict assignment is
    # what guarantees exactly one entry per ticker either way, never a
    # duplicate. Every other simulated entity (in demo mode) is untouched.
    # `live_substituted` tracks exactly which tickers got a genuine live
    # signal this poll -- the single source of truth the rest of this
    # function uses to guarantee an opportunity is either fully live-sourced
    # or fully simulated, never a blend of the two (see the guards below).
    live_tickers = live_stock_tickers()
    live_substituted: set[str] = set()
    for ticker in live_tickers:
        live_earnings_signal = _live_earnings_raw_signal(ticker, now)
        if live_earnings_signal is not None:
            fixtures[ticker] = live_earnings_signal
            live_substituted.add(ticker)
        # else: on failure/non-qualifying result, demo mode leaves whatever
        # simulated_fixtures() already put in `fixtures[ticker]` untouched
        # (the pre-Block-5 fallback behavior, unchanged); live-data-only
        # mode has nothing there to begin with, so the ticker is honestly
        # absent from this poll's results -- never a fabricated substitute.

    # One lock for the whole request's pipeline run, not just per-call: two
    # concurrent requests interleaving their individual entity.run() calls
    # against the same shared World Model/Prioritization state would produce
    # genuinely tangled results (e.g. one request's dedup window absorbing
    # signals from a different request), not just a data race.
    with _state_lock:
        results = []
        for entity_id, raw_signal in fixtures.items():
            raw_signals = [raw_signal]
            # Sprint 3.6.8 Block 5 fix: this simulated corroborating signal
            # must never be glued onto a *real* live TSLA earnings signal --
            # only ever added when TSLA's own primary signal this poll is
            # also simulated (entity_id not in live_substituted). Before
            # this guard existed, a live TSLA opportunity would have
            # silently gained a fabricated "Reuters confirms..." corroborating
            # signal alongside genuine live data -- exactly the kind of
            # simulated-into-live leak this block's governing rule forbids.
            if entity_id == "TSLA" and entity_id not in live_substituted:
                raw_signals.append(tesla_ai_partnership_corroboration(now))

            # Sprint 3.6.7 Block 2, generalized Sprint 3.6.8 Block 5: layers
            # live price-move/analyst-grade signals in alongside a ticker's
            # earnings signal now that Orchestrator.run() combines multiple
            # distinct-signal_type EnrichedEvents for one entity into one
            # coherent opportunity instead of the last one silently dropping
            # the others (ADR-051 finding 5). Each fetch is independently
            # gated on its own trigger actually firing -- see
            # _live_price_move_raw_signal/_live_analyst_grade_raw_signal's
            # own docstrings -- so a quiet trading day/no rating change
            # contributes nothing extra. StockConvergenceTracker only ever
            # emits STOCK_CONVERGENCE_MULTI_SOURCE once genuinely ≥3 distinct
            # signal_types have fired within its window, per entity (it is
            # never forced here, and one entity's observations can never
            # contribute to a different entity's convergence -- see
            # StockConvergenceTracker's own per-entity_id keying).
            #
            # Deliberately gated on `live_substituted`, not just
            # `live_tickers`: attempting these only after earnings has
            # already gone live for this ticker this poll guarantees the
            # same "fully live or fully simulated, never blended" property
            # as the TSLA guard above -- a ticker whose earnings fetch fell
            # back to simulated never gets a live price-move/grade signal
            # spliced onto that simulated primary signal either. A
            # price-move/grade-only live opportunity (earnings not firing)
            # is a real, deliberately deferred capability -- see the Block 5
            # ADR's own consequences.
            # Stock Opportunity Logic V2.2 (Evidence + Trajectory
            # Enrichment): market evidence is fetched under the identical
            # `live_substituted` gate as the price-move/grade signals above
            # -- a simulated demo entity never gets a live evidence fetch
            # spliced onto it, matching this file's own "fully live or
            # fully simulated, never blended" rule. A fetch failure (any
            # FMP hiccup) degrades to no evidence this poll, never a
            # fabricated one -- see _fetch_market_evidence's own docstring.
            market_evidence = None
            if entity_id in live_substituted:
                live_price_signal = _live_price_move_raw_signal(entity_id, now)
                if live_price_signal is not None:
                    raw_signals.append(live_price_signal)
                live_grade_signal = _live_analyst_grade_raw_signal(entity_id, now)
                if live_grade_signal is not None:
                    raw_signals.append(live_grade_signal)
                market_evidence = _fetch_market_evidence(entity_id, now)

            result = orchestrator.run(
                raw_signals=raw_signals,
                user_id=user_id,
                user_model=user_model,
                engagement_samples=_engagement_samples(entity_id, now),
                domain=raw_signal.domain,
                market_evidence=market_evidence,
            )
            results.append((entity_id, result))

            # Stock Opportunity Logic V2: write-through persistence -- if
            # this entity's lifecycle snapshot changed at all (it always has
            # a snapshot once lifecycle tracking is active; observe() always
            # updates last_evaluated_at even on a "none" change), persist it
            # immediately so a restart/redeploy right after this poll never
            # loses it. Mirrors notification_store.py's own write-through-
            # on-mutation discipline.
            if _lifecycle_store is not None and _lifecycle_tracker is not None:
                snapshot = _lifecycle_tracker.export_snapshot(entity_id)
                if snapshot is not None:
                    _lifecycle_store.save(snapshot)

            # Stock Opportunity Logic V2.1 (User Sync Gap): append one
            # durable revision row exactly when this poll produced a new
            # *global* revision (new_revision > previous_revision -- see
            # opportunity_lifecycle/tracker.py's is_global_meaningful gate,
            # which already excludes a personal-relevance-only change). Not
            # every poll -- the common "none" / personal-only case leaves
            # new_revision == previous_revision and writes nothing here.
            delta = result.lifecycle_delta
            if (
                _revision_store is not None
                and delta is not None
                and delta.new_revision != delta.previous_revision
            ):
                _revision_store.append(
                    OpportunityRevision(
                        entity_id=entity_id,
                        revision=delta.new_revision,
                        lifecycle_state=delta.new_state,
                        confidence_score=delta.new_confidence,
                        trigger_codes=delta.new_trigger_codes,
                        change_type=delta.change_type,
                        reason=delta.reason,
                        created_at=now,
                    )
                )

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
        is_first_load = user_id not in _baseline_established
        if is_first_load:
            _baseline_established.add(user_id)
            orchestrator.deps.prioritization_engine.mark_reviewed(
                user_id, [r.event.event_id for _, r in results]
            )

        # Sprint 3.6.6G: deferred import, see mark_notifications_reviewed's
        # own comment on the logan_feed<->notifications circular dependency.
        # A pushed-but-unopened notification must show in the in-app badge
        # even on this same first-load response -- the "first load is
        # notification-silent" rule above is about items that were never
        # pushed, not about hiding a real push the user already received.
        from .notifications import get_pending_push_event_ids

        pending_push_event_ids = get_pending_push_event_ids(user_id)

        items = []
        opportunity_contexts = []
        for position, (entity_id, r) in enumerate(results, start=1):
            entity = r.event.entities[0]
            canonical = resolve(entity_id, entity.display_name, r.event.domain)
            item_is_new_for_user = (
                False if is_first_load else r.prioritized_item.is_new_for_user
            ) or r.event.event_id in pending_push_event_ids

            # Stock Opportunity Logic V2.1 (User Sync Gap): a pure read/
            # comparison, never a write -- fetching this feed must never by
            # itself advance last_seen_revision (see record_interaction()'s
            # own docstring for the one place that pointer does move).
            current_revision = (
                r.lifecycle_delta.new_revision if r.lifecycle_delta else None
            )
            sync_delta = (
                compute_user_sync_delta(
                    entity_id=canonical.entity_id,
                    user_id=user_id,
                    current_revision=current_revision,
                    knowledge=_get_user_knowledge(user_id, canonical.entity_id),
                    now=now,
                )
                if current_revision is not None
                else None
            )
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
                    is_new_for_user=item_is_new_for_user,
                    # First signal drives the primary event for this entity
                    # (see world_model/model.py's process()) -- TSLA is the
                    # only fixture with a second, corroborating signal, and
                    # both share the same underlying signal_type.
                    signal_type=r.normalized_signals[0].signal_type,
                    # Stock Opportunity Logic V2 -- all None/False whenever
                    # r.lifecycle_delta is None (lifecycle tracking not
                    # active for this call; see _get_orchestrator()'s own
                    # live_stock_tickers() gate).
                    lifecycle_state=(
                        r.lifecycle_delta.new_state if r.lifecycle_delta else None
                    ),
                    is_updated=(
                        r.lifecycle_delta.is_meaningful if r.lifecycle_delta else False
                    ),
                    meaningful_change_type=(
                        r.lifecycle_delta.change_type if r.lifecycle_delta else None
                    ),
                    lifecycle_reason=(
                        r.lifecycle_delta.reason if r.lifecycle_delta else None
                    ),
                    last_meaningful_change_at=(
                        r.lifecycle_delta.last_meaningful_change_at
                        if r.lifecycle_delta
                        else None
                    ),
                    thesis_age_hours=(
                        r.lifecycle_delta.thesis_age_hours
                        if r.lifecycle_delta
                        else None
                    ),
                    opportunity_revision=current_revision,
                    user_sync_status=(
                        sync_delta.status if sync_delta is not None else None
                    ),
                    # Stock Opportunity Logic V2.2 -- all inert defaults
                    # whenever r.lifecycle_delta is None, identical
                    # discipline to the V2 fields above.
                    trajectory=(
                        r.lifecycle_delta.trajectory if r.lifecycle_delta else "STEADY"
                    ),
                    previous_trajectory=(
                        r.lifecycle_delta.previous_trajectory
                        if r.lifecycle_delta
                        else "STEADY"
                    ),
                    trajectory_reason=(
                        r.lifecycle_delta.trajectory_reason
                        if r.lifecycle_delta
                        else None
                    ),
                    evidence=(
                        r.lifecycle_delta.evidence if r.lifecycle_delta else None
                    ),
                )
            )
            # Sprint 3.6.7 Block 4: retains a richer slice of this same
            # PipelineResult for contextual Ask STRATUS -- see
            # ask_context.py's own docstring for why this isn't a second,
            # independent computation.
            opportunity_contexts.append(
                build_opportunity_context(
                    entity_id=canonical.entity_id,
                    display_name=canonical.display_name,
                    result=r,
                    is_new_for_user=item_is_new_for_user,
                    sync_delta=sync_delta,
                )
            )
        _opportunity_context_caches.setdefault(
            user_id, OpportunityContextCache()
        ).replace_all(opportunity_contexts)

        # Sprint 3.6.6F (STRATUS Watch): internal-only -- never added to the
        # public FeedItem contract (same discipline as internal_rank_score,
        # ADR-029). PrioritizedItem.interruption=="alert" is the existing,
        # already-computed bar for "urgent enough to interrupt" (Prioritization
        # Engine); reused here as the notification-eligibility gate rather than
        # inventing a second threshold. Independent of is_first_load's badge
        # silencing above -- a first-ever poll after a backend restart can
        # still be alert-eligible for push purposes even though the in-app
        # badge intentionally starts quiet.
        # Stock Opportunity Logic V2: "opportunity qualifies as alert" is no
        # longer, by itself, "send a notification" -- when lifecycle
        # tracking is active for this entity, a notification additionally
        # requires the poll's own LifecycleDelta to be notification-worthy
        # (a real, evidence-backed transition -- see
        # opportunity_lifecycle/tracker.py's own NOTIFICATION_WORTHY set).
        # r.lifecycle_delta is None whenever lifecycle tracking isn't active
        # for this call (demo mode, no live tickers configured) -- that case
        # keeps the exact pre-Sprint-3.6.9 behavior unchanged, matching the
        # gating precedent live_stock_tickers() already established for
        # trigger_detector/convergence_tracker above.
        alert_event_ids = [
            r.event.event_id
            for _, r in results
            if r.prioritized_item.interruption == "alert"
            and (r.lifecycle_delta is None or r.lifecycle_delta.is_notification_worthy)
        ]

    return items, now, alert_event_ids


def run_demo_feed(user_id: str = LOCAL_FOUNDER_USER_ID) -> DemoFeedResponse:
    """Deprecated in favor of `/v1/opportunities` (see `opportunities.py`), kept for
    existing callers during the V3.1.4 migration window -- see ADR-022 and the
    V3.1.4 BATCH-4 API work. Delegates to the same pipeline run as the versioned API;
    the two do not compute this independently. `user_id` defaults to the founder
    constant (Sprint 3.6.8 Block 2) -- this legacy route was never updated to accept
    the identity header, matching its own "kept only so existing callers don't
    break" scope.
    """
    items, now, _alert_event_ids = _run_feed_pipeline(user_id)
    return DemoFeedResponse(items=items, generated_at=now)


def get_alert_eligible_items(user_id: str) -> list[FeedItem]:
    """Sprint 3.6.6F (STRATUS Watch): `user_id`'s current pipeline run items
    whose PrioritizedItem.interruption == "alert" -- the existing "urgent
    enough to interrupt" bar, reused as the notification-eligibility gate.
    Runs the same shared, process-lifetime pipeline every other caller here
    uses, personalized for `user_id`; does not compute anything
    independently. Sprint 3.6.8 Block 2: `user_id` is now a required
    parameter -- see notifications.py's own per-user dispatch loop, which
    calls this once per user_id with a registered push token.
    """
    items, _now, alert_event_ids = _run_feed_pipeline(user_id)
    alert_ids = set(alert_event_ids)
    return [item for item in items if item.event_id in alert_ids]
