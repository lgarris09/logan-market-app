"""V2.3C Telemetry -- core recording logic and internal read/diagnostic API.

Owns exactly one thing: turning a client-submitted TelemetryEventRequest
into a durable, authoritative TelemetryEvent. Never infers preference,
never computes affinity, never scores relevance -- see telemetry_models.py's
own module docstring for why this is a deliberately separate concern from
FeedbackSignal/MemoryStore's existing Learning pipeline.

Same lazy-store / in-memory-index pattern as notifications.py's
_get_store(): an in-memory dict is always present (byte-for-byte in-memory
behavior when persistence is disabled, matching every pre-V2.3C test's
posture); a durable SQLite-backed mirror is layered on top only when
config.memory_persistence_enabled() is true. reset_telemetry_state() is
this module's own independent reset hook, wired into conftest.py's autouse
fixture exactly like reset_notification_state()/reset_fmp_cache() already
are -- not threaded through logan_feed.py's reset_pipeline_state(), since
telemetry has no relationship to the pipeline's own Orchestrator/lifecycle
state at all.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from .config import memory_persistence_enabled, telemetry_store_db_path
from .logan_feed import _get_user_knowledge, get_opportunity_context
from .telemetry_models import (
    TelemetryBatchRejection,
    TelemetryContext,
    TelemetryEvent,
    TelemetryEventBatchRequest,
    TelemetryEventBatchResponse,
    TelemetryEventRequest,
)
from .telemetry_store import TelemetryStore

# Insertion-ordered (Python dict semantics) -- doubles as both the
# idempotency index (a duplicate event_id is a no-op, see record_event) and
# the in-memory read path every diagnostic function below scans.
_events: dict[UUID, TelemetryEvent] = {}
_store: Optional[TelemetryStore] = None

_OPPORTUNITY_SCOPED_EVENT_NAMES = frozenset(
    {"opportunity_opened", "opportunity_returned_to", "watch_created", "watch_removed"}
)


def _get_store() -> Optional[TelemetryStore]:
    global _store
    if not memory_persistence_enabled():
        return None
    if _store is None:
        _store = TelemetryStore(telemetry_store_db_path())
        _events.clear()
        for event in _store.load_all():
            _events[event.event_id] = event
    return _store


def _resolve_opportunity_promotion(
    user_id: str, request: TelemetryEventRequest
) -> tuple[str, Optional[int], Optional[TelemetryContext]]:
    """Returns the (possibly-promoted) event_name, the validated
    opportunity_revision to persist, and the (possibly-enriched) context.

    The one piece of real business logic in this module: an
    `opportunity_opened` submission is promoted to `opportunity_returned_to`
    when this user's own durable, existing view-history
    (UserOpportunityKnowledge.last_opened_revision -- see
    opportunity_lifecycle/sync.py; advanced by record_interaction()'s
    "view" path, the SAME mechanism useCardDwellTracking.ts already submits
    on a real open->close span) shows a genuine prior completed open of this
    entity. This reuses existing durable state rather than inventing new
    view-tracking state (V2.3C Block H) -- no new store, no client-supplied
    "is this a return" flag ever trusted.

    A client-submitted `opportunity_revision` is cross-checked against the
    entity's current known revision when the opportunity_id resolves (never
    trusted blindly); when it doesn't resolve (a stale/expired event_id --
    honest, not fabricated), the event is still recorded exactly as
    submitted, with no promotion and no revision cross-check, since there is
    nothing authoritative to validate against.
    """
    if request.event_name not in _OPPORTUNITY_SCOPED_EVENT_NAMES:
        return request.event_name, request.opportunity_revision, request.context

    context = get_opportunity_context(user_id, request.opportunity_id)
    if context is None:
        return request.event_name, request.opportunity_revision, request.context

    if (
        request.opportunity_revision is not None
        and context.current_revision is not None
        and request.opportunity_revision > context.current_revision
    ):
        raise ValueError(
            "opportunity_revision exceeds this entity's current known revision"
        )

    if request.event_name != "opportunity_opened":
        return request.event_name, request.opportunity_revision, request.context

    knowledge = _get_user_knowledge(user_id, context.entity_id)
    previous_opened = knowledge.last_opened_revision if knowledge else None
    if previous_opened is None:
        # A genuine first-ever open -- never promoted.
        return request.event_name, request.opportunity_revision, request.context

    enriched_context = TelemetryContext(
        ask_session_id=request.context.ask_session_id if request.context else None,
        useful=request.context.useful if request.context else None,
        previous_opened_revision=previous_opened,
    )
    return (
        "opportunity_returned_to",
        context.current_revision or request.opportunity_revision,
        enriched_context,
    )


def record_event(user_id: str, request: TelemetryEventRequest) -> TelemetryEvent:
    """The single entry point every route (single and batch) uses.
    Idempotent on event_id -- a resubmission of an event_id already
    recorded returns the original, stored event unchanged, never a
    duplicate and never an overwrite (Block C's explicit "do not silently
    overwrite historical telemetry")."""
    # _get_store() must run before the idempotency check below: on a fresh
    # process, _events starts empty until the durable store's load_all()
    # rehydrates it (lazily, on first call) -- checking _events first would
    # miss a resubmission of an event_id that was durably persisted by a
    # *previous* process, on exactly the first call after a restart.
    store = _get_store()
    existing = _events.get(request.event_id)
    if existing is not None:
        return existing

    event_name, opportunity_revision, context = _resolve_opportunity_promotion(
        user_id, request
    )
    event = TelemetryEvent(
        event_id=request.event_id,
        event_name=event_name,
        occurred_at=request.occurred_at,
        recorded_at=datetime.now(timezone.utc),
        user_id=user_id,
        opportunity_id=request.opportunity_id,
        opportunity_revision=opportunity_revision,
        source_surface=request.source_surface,
        context=context,
    )
    _events[event.event_id] = event
    if store is not None:
        store.append(event)
    return event


def record_batch(
    user_id: str, batch: TelemetryEventBatchRequest
) -> TelemetryEventBatchResponse:
    accepted = 0
    rejected: list[TelemetryBatchRejection] = []
    for request in batch.events:
        try:
            record_event(user_id, request)
            accepted += 1
        except ValueError as exc:
            rejected.append(
                TelemetryBatchRejection(event_id=request.event_id, reason=str(exc))
            )
    return TelemetryEventBatchResponse(accepted_count=accepted, rejected=rejected)


def reset_telemetry_state() -> None:
    """Test-only (and general-purpose "start over") hook, mirroring
    reset_notification_state()'s identical shape. Releases the durable
    store's SQLite connection when persistence is enabled; the file itself
    is left untouched (simulates a real restart, not a data wipe)."""
    global _store
    if _store is not None:
        _store.close()
    _store = None
    _events.clear()


# --- V2.3C Block E: internal read/diagnostic API -----------------------
#
# Deliberately not exposed as a public mobile endpoint (see main.py -- no
# GET route wraps any of these). Enough for a future Personal Learning
# engine to query raw history cleanly; this module itself never infers
# preference or computes affinity from what it returns.


def recent_events_for_user(user_id: str, limit: int = 50) -> list[TelemetryEvent]:
    _get_store()  # ensures _events is hydrated from disk even if this is
    # the first call since a restart, with no write in between
    matches = [e for e in _events.values() if e.user_id == user_id]
    matches.sort(key=lambda e: e.occurred_at, reverse=True)
    return matches[:limit]


def events_for_user_and_opportunity(
    user_id: str, opportunity_id: UUID
) -> list[TelemetryEvent]:
    _get_store()
    matches = [
        e
        for e in _events.values()
        if e.user_id == user_id and e.opportunity_id == opportunity_id
    ]
    matches.sort(key=lambda e: e.occurred_at)
    return matches


def events_by_type(
    event_name: str, user_id: Optional[str] = None, limit: int = 100
) -> list[TelemetryEvent]:
    _get_store()
    matches = [
        e
        for e in _events.values()
        if e.event_name == event_name and (user_id is None or e.user_id == user_id)
    ]
    matches.sort(key=lambda e: e.occurred_at, reverse=True)
    return matches[:limit]


def latest_event_for_user_and_type(
    user_id: str, event_name: str
) -> Optional[TelemetryEvent]:
    matches = events_by_type(event_name, user_id=user_id, limit=1)
    return matches[0] if matches else None
