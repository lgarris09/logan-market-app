from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .common import Delta, Domain, Entity
from .trigger import TriggerEvent


class EnrichedEvent(BaseModel):
    schema_version: str = "1.0"
    event_id: UUID
    signal_ids: list[UUID]
    domain: Domain
    is_new: bool
    prior_event_id: Optional[UUID] = None
    entities: list[Entity]
    change_delta: list[Delta] = Field(default_factory=list)
    supporting: list[UUID] = Field(default_factory=list)
    contradicting: list[UUID] = Field(default_factory=list)
    downstream: list[str] = Field(default_factory=list)
    summary: str
    occurred_at: datetime
    enriched_at: datetime
    decision_trace: list = Field(default_factory=list)
    # Sprint 3.6.6 — additive, default-empty: populated only when a
    # deterministic trigger (see trigger_detection/) fired for one of this
    # event's originating signals. Every existing caller/test that doesn't
    # pass a trigger_event to WorldModel.process() sees this stay []
    # exactly as before. See docs/DECISIONS.md's Sprint 3.6.6 ADR.
    trigger_events: list[TriggerEvent] = Field(default_factory=list)
