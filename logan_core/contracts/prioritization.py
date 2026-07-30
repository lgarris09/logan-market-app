from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PrioritizedItem(BaseModel):
    schema_version: str = "1.0"
    event_id: UUID
    visibility: Literal["primary", "feed", "background", "hidden"]
    interruption: Literal["alert", "digest", "none"]
    rank: int = Field(ge=1)
    cooldown_until: Optional[datetime] = None
    changed_since_view: bool
    prioritized_at: datetime
    decision_trace: list = Field(default_factory=list)


class SurfaceRecord(BaseModel):
    event_id: UUID
    surfaced_at: datetime


class DismissRecord(BaseModel):
    event_id: UUID
    dismissed_at: datetime


class AlertRecord(BaseModel):
    event_id: UUID
    alerted_at: datetime


class CooldownRecord(BaseModel):
    event_id: UUID
    until: datetime


class FatigueRecord(BaseModel):
    domain: str
    count: int = Field(ge=0)
    window: datetime


class AttentionState(BaseModel):
    schema_version: str = "1.0"
    user_id: str
    surfaced: list[SurfaceRecord] = Field(default_factory=list)
    dismissed: list[DismissRecord] = Field(default_factory=list)
    alerted: list[AlertRecord] = Field(default_factory=list)
    cooldowns: list[CooldownRecord] = Field(default_factory=list)
    fatigue: list[FatigueRecord] = Field(default_factory=list)
    last_updated: datetime
