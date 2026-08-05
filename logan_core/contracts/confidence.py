from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ConclusionConfidence(BaseModel):
    schema_version: str = "1.0"
    event_id: UUID
    confidence_score: float = Field(ge=0.0, le=1.0)
    classification: Literal["fact", "inference", "hypothesis", "speculation"]
    alternatives: list[str] = Field(default_factory=list)
    limiting_factors: list[str] = Field(default_factory=list)
    # Reserved, non-functional metadata (ADR-032, MODEL_CONTRACTS.md). No trained
    # model exists this release — confidence_score above is computed exactly as
    # before (trust_score/mental_model_weight blend). calibrated_at stays null
    # until a real calibration pass actually runs.
    confidence_model_version: Optional[str] = "deterministic-baseline"
    calibrated_at: Optional[datetime] = None
    evaluated_at: datetime
    decision_trace: list = Field(default_factory=list)
