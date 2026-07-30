from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class EvidenceTrust(BaseModel):
    schema_version: str = "1.0"
    event_id: UUID
    source_score: float = Field(ge=0.0, le=1.0)
    corroboration: int = Field(ge=0)
    recency_score: float = Field(ge=0.0, le=1.0)
    contradiction_flag: bool
    manipulation_risk: Literal["low", "medium", "high"]
    completeness: float = Field(ge=0.0, le=1.0)
    trust_score: float = Field(ge=0.0, le=1.0)
    evaluated_at: datetime
    decision_trace: list = Field(default_factory=list)
