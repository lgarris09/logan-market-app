from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from logan_core.contracts import Delta, EnrichedEvent, Entity, NormalizedSignal

DEDUP_WINDOW = timedelta(hours=1)

# V1 downstream-effect mapping — a small static relationship graph that lets the
# "ripple" concept (one event affecting related entities) show up even before
# real causal-link inference exists. Extension point per Layer 3 spec.
DOWNSTREAM_EFFECTS: dict[str, list[str]] = {
    "TSLA": ["NVDA", "SMH", "AI_INFRA_ETF"],
    "NVDA": ["SMH", "AI_INFRA_ETF", "TSLA"],
}

ENTITY_DISPLAY_NAMES: dict[str, str] = {
    "TSLA": "Tesla",
    "NVDA": "NVIDIA",
    "SMH": "Semiconductor ETF (SMH)",
    "AI_INFRA_ETF": "AI Infrastructure ETF",
}


class WorldModel:
    """Layer 3 — owns the entity graph, relationship records, and dedup index.

    Forbidden per spec: reading User Model, applying personal relevance, scoring/ranking,
    sending notifications. Does not write Operational History — that's the Orchestrator's job (ADR-016).
    """

    def __init__(self) -> None:
        self._entity_graph: dict[str, Entity] = {}
        self._dedup_index: dict[tuple[str, str, int], UUID] = {}
        self._prior_values: dict[tuple[str, str], object] = {}
        self._events: dict[UUID, EnrichedEvent] = {}

    def _get_or_create_entity(self, entity_id: str, entity_type: str, domain: str) -> Entity:
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

    def _dedup_bucket(self, captured_at: datetime) -> int:
        return int(captured_at.timestamp() // DEDUP_WINDOW.total_seconds())

    def process(self, signal: NormalizedSignal) -> EnrichedEvent:
        entity = self._get_or_create_entity(signal.entity_id, signal.entity_type, signal.domain)
        downstream = DOWNSTREAM_EFFECTS.get(signal.entity_id, [])
        for downstream_id in downstream:
            self._get_or_create_entity(downstream_id, "ticker", signal.domain)

        dedup_key = (signal.entity_id, signal.signal_type, self._dedup_bucket(signal.captured_at))
        prior_event_id = self._dedup_index.get(dedup_key)

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
            self._dedup_index[dedup_key] = event_id
            summary = f"{entity.display_name}: {signal.signal_type.replace('_', ' ')} ({signal.value})"
            event = EnrichedEvent(
                event_id=event_id,
                signal_ids=[signal.signal_id],
                domain=signal.domain,
                is_new=True,
                entities=[entity],
                change_delta=change_delta,
                supporting=[],
                contradicting=[],
                downstream=downstream,
                summary=summary,
                occurred_at=signal.captured_at,
                enriched_at=datetime.now(timezone.utc),
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
                }
            )

        self._events[event.event_id] = event
        return event
