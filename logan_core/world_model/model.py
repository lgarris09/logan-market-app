from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from logan_core.contracts import DecisionTraceEntry, Delta, Domain, EnrichedEvent, Entity, NormalizedSignal

DEDUP_WINDOW = timedelta(hours=1)

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
        # Sliding window per (entity_id, signal_type): last signal's captured_at and
        # the event it belongs to. A fixed calendar-aligned bucket would let two
        # signals a few minutes apart land in different buckets purely by landing on
        # opposite sides of an hour boundary -- this tracks recency directly instead.
        self._recent: dict[tuple[str, str], tuple[datetime, UUID]] = {}
        self._prior_values: dict[tuple[str, str], object] = {}
        self._events: dict[UUID, EnrichedEvent] = {}

    def _get_or_create_entity(self, entity_id: str, entity_type: str, domain: Domain) -> Entity:
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

    def process(self, signal: NormalizedSignal) -> EnrichedEvent:
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
        """
        entity = self._get_or_create_entity(signal.entity_id, signal.entity_type, signal.domain)
        downstream = DOWNSTREAM_EFFECTS.get(signal.entity_id, [])
        for downstream_id in downstream:
            self._get_or_create_entity(downstream_id, "ticker", signal.domain)

        dedup_key = (signal.entity_id, signal.signal_type)
        recent = self._recent.get(dedup_key)
        within_window = recent is not None and (signal.captured_at - recent[0]) <= DEDUP_WINDOW
        prior_event_id = recent[1] if within_window else None

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
            event = existing.model_copy(
                update={
                    "is_new": False,
                    "prior_event_id": prior_event_id,
                    "signal_ids": existing.signal_ids + [signal.signal_id],
                    "supporting": existing.supporting + [signal.signal_id],
                    "enriched_at": datetime.now(timezone.utc),
                    "decision_trace": existing.decision_trace
                    + [
                        DecisionTraceEntry(
                            layer="world_model",
                            rule=f"corroboration: merged into existing event "
                            f"(within {DEDUP_WINDOW} dedup window)",
                            timestamp=datetime.now(timezone.utc),
                        )
                    ],
                }
            )

        self._recent[dedup_key] = (signal.captured_at, event.event_id)
        self._events[event.event_id] = event
        return event
