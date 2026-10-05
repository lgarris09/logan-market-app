from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

from logan_core.contracts import (
    DecisionTraceEntry,
    Delta,
    Domain,
    EnrichedEvent,
    Entity,
    EntityType,
    NormalizedSignal,
    TriggerEvent,
)

DEDUP_WINDOW = timedelta(hours=1)

# STRATUS reliability correction (OOM root-cause fix, 2026-10-04 production
# incident): the smallest, deterministic fixed-size recent-history policy
# that bounds `EnrichedEvent.signal_ids`/`decision_trace` growth for a
# single, continuously-corroborated dedup_key. Confirmed root cause: the
# live stock feed polls every ~60s (notification poller + mobile foreground
# poll, independently, both hitting this same shared WorldModel instance),
# and a ticker's earnings/quote report can stay "current" -- and therefore
# continuously corroborating within DEDUP_WINDOW -- for days to a full
# quarter. Before this fix, every corroborating poll unconditionally
# appended one entry to both lists with no upper bound, which measured as
# literal, unbounded process-lifetime growth in production (confirmed via
# live Fly SSH inspection: ~2.7M durable freshness-observation rows
# recorded at this same per-poll rate over one month).
#
# 50 is chosen, not tuned: at the historically observed and currently
# duplicated poll rate (roughly 1-3 full pipeline runs/minute across the
# notification poller and the mobile app's own foreground poll), 50 entries
# comfortably spans several minutes to tens of minutes of the MOST RECENT
# real corroboration history for one (entity, signal_type) -- enough for any
# debugging/audit use of decision_trace/signal_ids -- while keeping the
# worst-case memory for this structure negligible regardless of how many
# hours/days a signal stays continuously current (at most ~90 concurrently
# tracked dedup_keys in the current 30-ticker x 3-signal-family universe,
# each capped at 50 small entries). This never touches `supporting`, which
# EvidenceTrustEngine's corroboration/confidence math reads directly --
# `supporting`'s own existing duplicate-detection semantics (see process()
# below) are completely unchanged by this bound.
MAX_RECENT_EVENT_HISTORY = 50


def _bounded_history(history: list) -> list:
    """Deterministic fixed-size recent-history policy: keeps only the
    newest `MAX_RECENT_EVENT_HISTORY` entries (oldest dropped first),
    mirroring this codebase's existing bounded-history precedent
    (logan_core/diagnostics/fault_codes.py's `_MAX_RECENT_OCCURRENCES` ring
    buffer; backend/app/logan_feed.py's `_trim_ask_history`). Applied only
    to pure provenance/audit-trail fields (`signal_ids`, `decision_trace`)
    -- never to `supporting`, which confidence math reads directly and
    which this fix does not touch."""
    if len(history) <= MAX_RECENT_EVENT_HISTORY:
        return history
    return history[-MAX_RECENT_EVENT_HISTORY:]


# V1 downstream-effect mapping — a small static relationship graph that lets the
# ripple concept (one event affecting related entities) show up even before real
# causal-link inference exists. Extension point per Layer 3 spec. Deliberately
# leaves some demo entities (AAPL, OIL, NFL, MUSIC, POLY) unconnected, the same way
# not every real opportunity ripples into every other one.
DOWNSTREAM_EFFECTS: dict[str, list[str]] = {
    "TSLA": ["NVDA", "MARKETS", "AI_SECTOR"],
    "NVDA": ["MARKETS", "AI_SECTOR", "TSLA"],
    "AI_SECTOR": ["TSLA", "NVDA"],
    "FED": ["MARKETS", "BTC"],
    "MARKETS": ["FED", "TSLA", "NVDA"],
    "BTC": ["FED"],
}

ENTITY_DISPLAY_NAMES: dict[str, str] = {
    "TSLA": "Tesla",
    "NVDA": "NVIDIA",
    "AAPL": "Apple",
    "MARKETS": "Markets",
    "OIL": "Oil",
    "BTC": "Bitcoin",
    "FED": "Federal Reserve",
    "NFL": "NFL",
    "MUSIC": "Music",
    "POLY": "Polymarket",
    "AI_SECTOR": "AI Sector",
}


class WorldModel:
    """Layer 3 — owns the entity graph, relationship records, and dedup index.

    Forbidden per spec: reading User Model, applying personal relevance, scoring/ranking,
    sending notifications. Does not write Operational History — that's the Orchestrator's job (ADR-016).
    """

    def __init__(self) -> None:
        self._entity_graph: dict[str, Entity] = {}
        # Sliding window per (entity_id, signal_type): the last signal's own
        # captured_at, the real processing/observation time this dedup_key was
        # last touched, and the event it belongs to.
        #
        # STRATUS reliability correction (OOM root-cause fix): the window
        # check below now requires BOTH the provider-timestamp gap AND the
        # real processing-time gap to stay within DEDUP_WINDOW. Before this
        # fix, only the provider-timestamp gap was checked -- for a provider
        # report whose own captured_at never advances between polls (the
        # live case: FMP returns the identical earnings/quote report on
        # every ~60s poll), that gap is always exactly zero, so the window
        # never aged out no matter how much real wall-clock time had
        # actually passed; an unchanged report stayed "within the window"
        # permanently. Adding the processing-time axis means a genuinely
        # long real gap (the ticker stops being observed for longer than
        # DEDUP_WINDOW, e.g. an outage or a long process restart gap) is
        # correctly treated as outside the window again, while continuous,
        # real-time polling of the same unchanged report -- the correct,
        # intended, steady-state behavior -- is completely unaffected: both
        # axes stay well within DEDUP_WINDOW on every normal ~60s poll.
        self._recent: dict[tuple[str, str], tuple[datetime, datetime, UUID]] = {}
        self._prior_values: dict[tuple[str, str], object] = {}
        self._events: dict[UUID, EnrichedEvent] = {}
        # Sprint 3.6.6E: (source_id, value) of the most recently absorbed signal per
        # (entity_id, signal_type) -- independent of _prior_values, which only
        # updates when a genuinely new event starts. Lets process()'s corroboration
        # branch tell "the same source re-reporting identical content" (a duplicate
        # poll -- e.g. the live NVDA path re-fetching the same unchanged FMP report
        # on every /v1/opportunities request) apart from "a different source, or the
        # same source with genuinely changed content" (real corroboration).
        self._last_observed: dict[tuple[str, str], tuple[str, object]] = {}
        # Self-corroboration fix (ADR-076): the distinct source_ids that have
        # contributed to each event. `supporting` -- which
        # EvidenceTrustEngine reads as the corroboration count -- may only
        # grow when a source NOT already in this set reports. Before this,
        # one source re-reporting changed content (a quote that moved, a
        # corrected report) was appended to `supporting` and counted as
        # independent corroboration of itself.
        self._event_sources: dict[UUID, set[str]] = {}

    def _get_or_create_entity(
        self, entity_id: str, entity_type: EntityType, domain: Domain
    ) -> Entity:
        entity = self._entity_graph.get(entity_id)
        if entity is None:
            entity = Entity(
                entity_id=entity_id,
                entity_type=entity_type,
                display_name=ENTITY_DISPLAY_NAMES.get(entity_id, entity_id),
                domain=domain,
                attributes={},
            )
            self._entity_graph[entity_id] = entity
        return entity

    def get_event(self, event_id: UUID) -> Optional[EnrichedEvent]:
        """Read-only lookup into this instance's own event history, by
        event_id. Added alongside the OOM reliability correction so a
        dedup-window rollover (see process()) is verifiably additive --
        the prior event this entity/signal_type was tracking must still be
        retrievable, never silently dropped. Returns None for an event_id
        this WorldModel instance has never produced."""
        return self._events.get(event_id)

    def process(
        self,
        signal: NormalizedSignal,
        trigger_event: Optional[TriggerEvent] = None,
        *,
        observed_at: Optional[datetime] = None,
    ) -> EnrichedEvent:
        """V3.1.4 BATCH-2 note on `EnrichedEvent.contradicting`: reserved, not
        populated. A deterministic contradiction rule needs to compare two
        signals' `value` fields, but `NormalizedSignal.value` is untyped
        (`object`) -- comparing raw values for inequality would misclassify
        ordinary corroboration as contradiction (per
        `docs/IMPLEMENTATION_DECISIONS.md` #3, two sources paraphrasing the
        same event report different exact text/values without disagreeing),
        and any type-aware comparison would require inventing per-domain
        semantic contradiction logic this task's instructions explicitly
        prohibit. `contradicting` stays reserved on the contract; the
        downstream `ReasoningEngine` branch that reads it is documented as
        currently unreachable for the same reason, not silently dead.

        `observed_at` (STRATUS reliability correction): the real processing/
        observation time this call is happening at, used only for the
        dedup-window-aging check in `_recent` (see `__init__`'s own comment)
        -- never used for `EnrichedEvent.occurred_at` (still `signal.
        captured_at`, the real factual provider timestamp, completely
        unchanged) or for `change_delta`/`summary`/any user-visible thesis
        field. Defaults to `datetime.now(timezone.utc)` when omitted, so
        every existing production caller (the orchestrator never passes
        this) gets real wall-clock processing time automatically, with
        byte-identical behavior to before this fix in the steady-state,
        continuous-polling case. Tests pass it explicitly to simulate a
        real elapsed-time gap without needing to actually sleep.
        """
        if observed_at is None:
            observed_at = datetime.now(timezone.utc)

        entity = self._get_or_create_entity(
            signal.entity_id, signal.entity_type, signal.domain
        )
        downstream = DOWNSTREAM_EFFECTS.get(signal.entity_id, [])
        for downstream_id in downstream:
            self._get_or_create_entity(downstream_id, "ticker", signal.domain)

        dedup_key = (signal.entity_id, signal.signal_type)
        recent = self._recent.get(dedup_key)
        prior_event_id: UUID | None = None
        if recent is not None:
            prior_captured_at, prior_observed_at, recent_event_id = recent
            within_captured_window = (
                signal.captured_at - prior_captured_at
            ) <= DEDUP_WINDOW
            within_observed_window = (observed_at - prior_observed_at) <= DEDUP_WINDOW
            if within_captured_window and within_observed_window:
                prior_event_id = recent_event_id

        if prior_event_id is None:
            # First time this entity+signal_type has been seen in this time window —
            # a genuinely new event. Compute change_delta against the last known value
            # from a *previous* window, if any.
            change_delta: list[Delta] = []
            value_key = (signal.entity_id, signal.signal_type)
            prior_value = self._prior_values.get(value_key)
            if prior_value is not None and prior_value != signal.value:
                change_delta.append(
                    Delta(
                        field=signal.signal_type,
                        prior_value=prior_value,
                        new_value=signal.value,
                        unit=signal.unit,
                        changed_at=signal.captured_at,
                    )
                )
            self._prior_values[value_key] = signal.value

            event_id = uuid4()
            summary = f"{entity.display_name}: {signal.signal_type.replace('_', ' ')} ({signal.value})"
            event = EnrichedEvent(
                event_id=event_id,
                signal_ids=[signal.signal_id],
                domain=signal.domain,
                is_new=True,
                entities=[entity],
                change_delta=change_delta,
                supporting=[],
                # Deliberately always empty in V1 -- see the module-level note
                # below `process()` for why a deterministic contradiction rule
                # isn't implemented yet (V3.1.4 BATCH-2 review).
                contradicting=[],
                downstream=downstream,
                summary=summary,
                occurred_at=signal.captured_at,
                enriched_at=datetime.now(timezone.utc),
                # Sprint 3.6.6: attaches only when the orchestrator wired a
                # trigger_detector and it fired for this signal -- every
                # existing caller (trigger_event omitted) gets [] exactly as
                # before.
                trigger_events=[trigger_event] if trigger_event else [],
                decision_trace=[
                    DecisionTraceEntry(
                        layer="world_model",
                        rule=f"new event: no prior signal for {signal.entity_id}/{signal.signal_type} "
                        f"within the {DEDUP_WINDOW} dedup window",
                        timestamp=datetime.now(timezone.utc),
                    )
                ],
            )
        else:
            # A corroborating signal for an event already seen in this window — merge
            # it in as supporting evidence rather than treating it as a new event.
            existing = self._events[prior_event_id]
            # Sprint 3.6.6: replace-by-trigger_code, not append. A duplicate
            # poll of the same underlying report (Phase 5's "duplicate
            # polling results" edge case) would otherwise add a second,
            # near-identical TriggerEvent for the same trigger_code, and
            # EvidenceTrustEngine sums every attached trigger's
            # confidence_contribution -- silently double-counting the same
            # evidence. A genuinely corrected/revised report (different
            # raw_magnitude, same trigger_code -- Phase 5's "provider
            # corrections/revisions" case) replaces the prior entry rather
            # than stacking alongside it, so confidence reflects the latest
            # known numbers, not stale-plus-corrected added together. This
            # is deliberately simpler than TRIGGER_EVENT_FRAMEWORK.md's full
            # revision model (revision_number/supersedes_revision, out of
            # scope this sprint per OD-009) -- "one live TriggerEvent per
            # trigger_code per event," not a revision history.
            merged_triggers = list(existing.trigger_events)
            if trigger_event is not None:
                merged_triggers = [
                    t
                    for t in merged_triggers
                    if t.trigger_code != trigger_event.trigger_code
                ] + [trigger_event]

            # Sprint 3.6.6E: a duplicate poll of the same underlying evidence
            # (same source_id, same signal.value -- e.g. the live NVDA path
            # re-fetching an unchanged FMP report on every /v1/opportunities
            # request) is not new corroborating evidence and must not grow
            # `supporting`, which EvidenceTrustEngine's corroboration score
            # reads directly (len(event.supporting)) -- repeated reads of the
            # same observation were inflating confidence purely from being
            # polled repeatedly, never from anything genuinely new. `signal_ids`
            # still grows either way, preserving the honest provenance record
            # that this poll happened -- bounded by _bounded_history() below
            # (STRATUS reliability correction), same as `decision_trace`.
            # Only a source that has not yet contributed to this event is
            # real corroboration and grows `supporting` (ADR-076); the same
            # source reporting different content is absorbed without
            # counting (see `_event_sources` in __init__). `supporting` is
            # therefore bounded by the number of distinct sources.
            last_source_id, last_value = self._last_observed.get(
                dedup_key, (None, None)
            )
            is_duplicate_observation = (
                signal.source_id == last_source_id and signal.value == last_value
            )
            new_signal_ids = _bounded_history(existing.signal_ids + [signal.signal_id])
            contributing_sources = self._event_sources.setdefault(prior_event_id, set())
            if is_duplicate_observation:
                new_supporting = existing.supporting
                trace_rule = (
                    f"duplicate observation: same source ({signal.source_id}) and "
                    f"content re-polled within {DEDUP_WINDOW} -- not counted as new "
                    f"corroborating evidence"
                )
            elif signal.source_id in contributing_sources:
                # The same source reporting different content (a quote that
                # moved, a corrected/revised report). The new content is
                # absorbed -- trigger replacement above, signal_ids below --
                # but a source cannot corroborate itself.
                new_supporting = existing.supporting
                trace_rule = (
                    f"updated content from a source already counted "
                    f"({signal.source_id}) -- absorbed, not independent "
                    f"corroboration"
                )
            else:
                new_supporting = existing.supporting + [signal.signal_id]
                trace_rule = (
                    f"corroboration: merged into existing event "
                    f"(within {DEDUP_WINDOW} dedup window)"
                )
            contributing_sources.add(signal.source_id)

            event = existing.model_copy(
                update={
                    "is_new": False,
                    "prior_event_id": prior_event_id,
                    "signal_ids": new_signal_ids,
                    "supporting": new_supporting,
                    "enriched_at": datetime.now(timezone.utc),
                    "trigger_events": merged_triggers,
                    "decision_trace": _bounded_history(
                        existing.decision_trace
                        + [
                            DecisionTraceEntry(
                                layer="world_model",
                                rule=trace_rule,
                                timestamp=datetime.now(timezone.utc),
                            )
                        ]
                    ),
                }
            )

        if prior_event_id is None:
            self._event_sources[event.event_id] = {signal.source_id}
        self._recent[dedup_key] = (signal.captured_at, observed_at, event.event_id)
        self._last_observed[dedup_key] = (signal.source_id, signal.value)
        self._events[event.event_id] = event
        return event
