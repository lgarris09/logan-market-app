from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


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


def confidence_label_for(score: float) -> str:
    if score >= 0.80:
        return "High"
    if score >= 0.55:
        return "Moderate"
    if score >= 0.35:
        return "Low"
    return "Speculative"
