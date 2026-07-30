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
    prior_signal_links: list[UUID] = Field(default_factory=list)
    stance: Literal["confirms", "contradicts", "complicates", "new"]
    actionability: Literal["actionable", "informational", "ambiguous"]
    explanation: str
    supporting_links: list[Reference] = Field(default_factory=list)
    reasoned_at: datetime
    decision_trace: list = Field(default_factory=list)
