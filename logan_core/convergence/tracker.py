from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

from logan_core.contracts import DecisionTraceEntry, TriggerEvent

# TRIGGER_REGISTRY_STOCKS.md's STOCK_CONVERGENCE_MULTI_SOURCE: "3 or more
# independent signal sources fire on the same entity within a 30-minute
# window." Registered, fixed constants -- not computed/learned, per Sprint
# 3.6.6D's standing rule (reuse only registry-defined constants).
STOCK_CONVERGENCE_MULTI_SOURCE = "STOCK_CONVERGENCE_MULTI_SOURCE"
CONVERGENCE_WINDOW = timedelta(minutes=30)
_MIN_DISTINCT_SOURCE_TYPES = 3
_CONVERGENCE_CONFIDENCE_CONTRIBUTION = 0.20

_TRACKER_SOURCE_ID = "stratus_convergence_tracker"
_TRACKER_SOURCE_NAME = "STRATUS Convergence Tracker"


@dataclass(frozen=True)
class _Observation:
    """One qualifying TriggerEvent this tracker has been told about, reduced
    to only what convergence needs to remember about it."""

    signal_type: str
    trigger_code: str
    trigger_id: UUID
    originating_signal_ids: list[UUID]
    domain: str
    observed_at: datetime


@dataclass
class _Episode:
    """The currently-active convergence episode for one entity -- the exact
    set of distinct signal_types that most recently crossed the ≥3 threshold.
    Its `trigger_id`/`first_detected_at` stay fixed for as long as the same
    signature remains active, so repeated polls that keep observing the same
    already-converged signal types re-describe the same ongoing episode
    (stable identity, `event_timestamp` pinned to when it started) rather
    than minting a fresh "new" alert every poll."""

    signature: frozenset[str]
    trigger_id: UUID
    first_detected_at: datetime


class StockConvergenceTracker:
    """Sprint 3.6.7 Block 2 -- 'Option 1: parallel convergence tracker'.

    Deliberately NOT a change to WorldModel's `(entity_id, signal_type)`
    dedup/corroboration semantics (world_model/model.py) -- those stay
    exactly as they are; this is a separate, persistent component that
    watches the same TriggerEvents WorldModel is handed and independently
    tracks, per entity, which *distinct* stock signal_types have produced a
    qualifying TriggerEvent within the registered 30-minute
    STOCK_CONVERGENCE_MULTI_SOURCE window. Not the canonical Hit-Detection-
    layer Convergence Detector from
    docs/specs/Logan_Documentation_v3.1.4/source_material/04_HIT_DETECTION.md
    either (that watches raw signal sources pre-trigger-detection, across
    domains) -- narrower, same discipline as convergence/detector.py's own
    docstring on why it isn't the canonical component: SPECIFIED-NOT-
    IMPLEMENTED (OD-009) is a separate, larger decision, not made here.

    Persistent, process-lifetime state (mirrors WorldModel's own `_recent`
    sliding-window index) -- a single instance must be reused across polls
    for its window to mean anything; a fresh instance per call would never
    see enough history to converge on anything (see PipelineDependencies'
    `convergence_tracker` field and backend/app/logan_feed.py's
    process-lifetime Orchestrator).

    Only ever called with TriggerEvents that already fired (see
    Orchestrator.run()'s wiring) -- a signal_type that was merely polled but
    produced no qualifying TriggerEvent this round contributes nothing, by
    construction. This is what "prevent repeated polling ... from falsely
    satisfying convergence" actually means here: an unrelated signal_type
    being checked every request (and finding nothing) can never itself count
    as one of the ≥3 distinct sources -- only a real qualifying detection
    does. And because distinct source types are tracked as a *set*, not a
    counter, re-observing the same signal_type on every subsequent poll
    (e.g. the same still-active price move re-confirmed each request) never
    inflates the count past 1 for that type either -- duplicate/repeated
    events cannot manufacture a third or fourth "distinct" source on their
    own.
    """

    def __init__(self) -> None:
        self._observations: dict[str, list[_Observation]] = {}
        self._active_episode: dict[str, _Episode] = {}

    def observe(
        self, trigger_event: TriggerEvent, signal_type: str
    ) -> Optional[TriggerEvent]:
        """Records one qualifying TriggerEvent for its entity/signal_type and
        returns a STOCK_CONVERGENCE_MULTI_SOURCE TriggerEvent iff ≥3 distinct
        signal_types are currently active (within the window, relative to
        this observation's own timestamp) for that entity -- else None.
        """
        entity_id = trigger_event.affected_entity_id
        # Windowed on `detected_timestamp` (when this trigger was actually
        # evaluated/detected -- effectively "now" at poll time, per
        # trigger_detection/stocks.py's `_build_trigger_event`), not
        # `event_timestamp` (when the underlying real-world event itself
        # occurred). Those two routinely diverge by far more than 30 minutes
        # for genuinely real data -- an earnings report's date, a quote's
        # real-time timestamp, and an analyst action's date are each
        # independently timestamped and can be days or weeks apart even when
        # all three are detected as live opportunities in the very same
        # poll. "3 or more independent signal sources fire ... within a
        # 30-minute window" (TRIGGER_REGISTRY_STOCKS.md) is naturally read as
        # "detected together," matching a live-polling system -- not as a
        # coincidence in the underlying events' own historical timestamps.
        now = trigger_event.detected_timestamp

        history = self._observations.setdefault(entity_id, [])
        history.append(
            _Observation(
                signal_type=signal_type,
                trigger_code=trigger_event.trigger_code,
                trigger_id=trigger_event.trigger_id,
                originating_signal_ids=list(trigger_event.originating_signal_ids),
                domain=trigger_event.domain,
                observed_at=now,
            )
        )

        # Sliding window relative to the most recent observation this entity
        # has produced -- same recency-based approach as WorldModel's own
        # DEDUP_WINDOW (world_model/model.py), not a fixed calendar bucket,
        # for the same reason: two signals a few minutes apart shouldn't land
        # on opposite sides of an arbitrary boundary.
        cutoff = now - CONVERGENCE_WINDOW
        history[:] = [o for o in history if o.observed_at >= cutoff]

        distinct_types = {o.signal_type for o in history}
        if len(distinct_types) < _MIN_DISTINCT_SOURCE_TYPES:
            # Window boundary case: this entity's active signal set just
            # fell (or never rose) past the threshold -- any previously
            # active episode has lapsed. The next time it re-crosses the
            # threshold is a genuinely new episode, not a continuation.
            self._active_episode.pop(entity_id, None)
            return None

        signature = frozenset(distinct_types)
        episode = self._active_episode.get(entity_id)
        if episode is None or episode.signature != signature:
            # First time this exact combination has converged (either the
            # very first time this entity reached 3, or the qualifying set
            # changed -- e.g. one signal_type aged out and a different one
            # took its place). A genuinely new episode, new identity.
            episode = _Episode(
                signature=signature, trigger_id=uuid4(), first_detected_at=now
            )
            self._active_episode[entity_id] = episode
        # else: same active episode, same signature already alerted on --
        # reuse its trigger_id/first_detected_at below so this describes the
        # *same* ongoing convergence, not a repeated new alert.

        latest_by_type: dict[str, _Observation] = {}
        for o in history:
            if o.signal_type in signature:
                latest_by_type[o.signal_type] = o  # history is time-ordered; last wins

        sources = sorted(latest_by_type)
        originating_signal_ids: list[UUID] = []
        for source in sources:
            originating_signal_ids.extend(latest_by_type[source].originating_signal_ids)

        context = {
            "source_count": len(sources),
            "sources": sources,
            "window_minutes": int(CONVERGENCE_WINDOW.total_seconds() // 60),
            "contributing_trigger_codes": [
                latest_by_type[s].trigger_code for s in sources
            ],
        }

        return TriggerEvent(
            trigger_id=episode.trigger_id,
            trigger_code=STOCK_CONVERGENCE_MULTI_SOURCE,
            trigger_class="catalyst",
            trigger_type="signal_convergence",
            trigger_status="confirmed",
            domain=trigger_event.domain,
            affected_entity_id=entity_id,
            direction="positive",
            # Real, computed magnitude -- how many distinct source types are
            # currently converged -- never a placeholder.
            raw_magnitude=float(len(sources)),
            confidence_contribution=_CONVERGENCE_CONFIDENCE_CONTRIBUTION,
            context=context,
            originating_signal_ids=originating_signal_ids,
            source_id=_TRACKER_SOURCE_ID,
            source_name=_TRACKER_SOURCE_NAME,
            # Pinned to when this episode first converged, not "now" on every
            # poll -- keeps recency scoring (EvidenceTrustEngine) and
            # "is this new" semantics stable across repeated polls of the
            # same ongoing convergence, mirroring WorldModel's own event_id
            # stability for corroborating signals.
            event_timestamp=episode.first_detected_at,
            detected_timestamp=now,
            decision_trace=[
                DecisionTraceEntry(
                    layer="convergence_tracker",
                    rule=(
                        f"{STOCK_CONVERGENCE_MULTI_SOURCE}: {len(sources)} distinct "
                        f"signal types ({', '.join(sources)}) converged for "
                        f"{entity_id} within the {CONVERGENCE_WINDOW} window"
                    ),
                    confidence=_CONVERGENCE_CONFIDENCE_CONTRIBUTION,
                    timestamp=now,
                )
            ],
        )
