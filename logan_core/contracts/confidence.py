from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ConclusionConfidence(BaseModel):
    schema_version: str = "1.0"
    event_id: UUID
    confidence_score: float = Field(ge=0.0, le=1.0)
    classification: Literal["fact", "inference", "hypothesis", "speculation"]
    alternatives: list[str] = Field(default_factory=list)
    limiting_factors: list[str] = Field(default_factory=list)
    evaluated_at: datetime
    decision_trace: list = Field(default_factory=list)
