from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from .personal_relevance import PersonalRelevanceResult


class DeliveredItem(BaseModel):
    schema_version: str = "1.0"
    event_id: UUID
    surface: Literal["wheel", "feed_card", "alert", "digest", "background"]
    headline: str
    what_happened: str
    why_it_matters: str
    why_it_matters_to_me: str
    why_now: str
    confidence_label: Literal["High", "Moderate", "Low", "Speculative"]
    confidence_score: float = Field(ge=0.0, le=1.0)
    # V2.3B Phase 2 (Learning-Driven STRATUS) Block 5 -- the structured
    # "why this matters to you" basis behind why_it_matters_to_me above.
    # Optional/None only for a pre-Phase-2 direct construction that doesn't
    # supply one; every real PresentationEngine.deliver() call populates it.
    personal_relevance_result: Optional[PersonalRelevanceResult] = None
    connected_items: list[UUID] = Field(default_factory=list)
    required_disclaimers: list[str] = Field(default_factory=list)
    decision_trace: list = Field(default_factory=list)
    delivered_at: datetime

    @field_validator("headline")
    @classmethod
    def _headline_length(cls, value: str) -> str:
        if len(value) > 120:
            raise ValueError("headline must be at most 120 characters")
        return value


ConfidenceLabel = Literal["High", "Moderate", "Low", "Speculative"]


def confidence_label_for(score: float) -> ConfidenceLabel:
    if score >= 0.80:
        return "High"
    if score >= 0.55:
        return "Moderate"
    if score >= 0.35:
        return "Low"
    return "Speculative"
