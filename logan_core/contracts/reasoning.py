from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from .common import Reference


class ReasoningResult(BaseModel):
    schema_version: str = "1.0"
    event_id: UUID
    significance: str
    # Renamed from `personal_relevance` per ADR-021 — do not confuse with the
    # float-typed Dimensions.personal_relevance used by the Opportunity Engine.
    personal_relevance_narrative: str
    connected_entities: list[str] = Field(default_factory=list)
    # Explicit/inferred split of connected_entities above (union of the two,
    # unchanged) -- lets the Opportunity Engine bound an inferred-only
    # connection's relevance contribution below an explicit one (holdings or
    # Interest(source="explicit")) rather than treating them identically.
    # Additive fields, both default empty -- existing callers that only read
    # connected_entities are unaffected.
    connected_entities_explicit: list[str] = Field(default_factory=list)
    connected_entities_inferred: list[str] = Field(default_factory=list)
    prior_signal_links: list[UUID] = Field(default_factory=list)
    stance: Literal["confirms", "contradicts", "complicates", "new"]
    actionability: Literal["actionable", "informational", "ambiguous"]
    explanation: str
    supporting_links: list[Reference] = Field(default_factory=list)
    reasoned_at: datetime
    decision_trace: list = Field(default_factory=list)
