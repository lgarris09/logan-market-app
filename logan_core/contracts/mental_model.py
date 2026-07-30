from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MentalModel(BaseModel):
    schema_version: str = "1.0"
    model_id: UUID
    domain: str
    hypothesis: str
    confidence: float = Field(ge=0.0, le=1.0)
    supporting: list[str] = Field(default_factory=list)
    opposing: list[str] = Field(default_factory=list)
    trend: Literal["strengthening", "weakening", "stable", "new", "retired"]
    created_at: datetime
    last_updated: datetime
    retired_at: Optional[datetime] = None
    decision_trace: list = Field(default_factory=list)


class MentalModelDelta(BaseModel):
    schema_version: str = "2.0"
    model_id: UUID
    prior_confidence: float = Field(ge=0.0, le=1.0)
    new_confidence: float = Field(ge=0.0, le=1.0)
    delta: float
    trigger_event_id: UUID
    delta_is_signal: bool
    delta_threshold: float = 0.10
    computed_at: datetime
