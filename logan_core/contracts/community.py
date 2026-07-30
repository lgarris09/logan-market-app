from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CommunitySignal(BaseModel):
    schema_version: str = "1.0"
    event_id: UUID
    engagement_volume: int = Field(ge=0)
    engagement_velocity: float
    unique_users: int = Field(ge=0)
    saves_shares: int = Field(ge=0)
    questions: int = Field(ge=0)
    lifecycle_state: Literal["emerging", "peak", "fading", "dormant"]
    coordinated_risk: float = Field(ge=0.0, le=1.0)
    bot_risk: float = Field(ge=0.0, le=1.0)
    momentum_score: float = Field(ge=0.0, le=1.0)
    measured_at: datetime
    decision_trace: list = Field(default_factory=list)
