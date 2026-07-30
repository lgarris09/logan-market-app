from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class Dimensions(BaseModel):
    personal_relevance: float = Field(ge=0.0, le=1.0)
    global_importance: float = Field(ge=0.0, le=1.0)
    community_momentum: float = Field(ge=0.0, le=1.0)
    urgency: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    novelty: float = Field(ge=0.0, le=1.0)
    opportunity_magnitude: float = Field(ge=0.0, le=1.0)
    risk: float = Field(ge=0.0, le=1.0)
    actionability: float = Field(ge=0.0, le=1.0)
    connection_strength: float = Field(ge=0.0, le=1.0)


class AttentionRecommendation(BaseModel):
    schema_version: str = "1.0"
    event_id: UUID
    recommend: bool
    dimensions: Dimensions
    priority_score: float = Field(ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list)
    competing_items: list[UUID] = Field(default_factory=list)
    recommended_at: datetime
    decision_trace: list = Field(default_factory=list)
