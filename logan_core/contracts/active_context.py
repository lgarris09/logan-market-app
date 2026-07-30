from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ActivityRecord(BaseModel):
    activity_type: str
    detail: str
    occurred_at: datetime


class ScheduledEvent(BaseModel):
    label: str
    scheduled_at: datetime


class LiveState(BaseModel):
    domain: str
    entity_id: str
    state: object


class ActiveContext(BaseModel):
    schema_version: str = "1.0"
    session_id: UUID
    current_question: Optional[str] = None
    time_of_day: Literal["morning", "midday", "afternoon", "evening", "night"]
    recent_activity: list[ActivityRecord] = Field(default_factory=list)
    temporary_intent: Optional[str] = None
    upcoming_events: list[ScheduledEvent] = Field(default_factory=list)
    live_context: list[LiveState] = Field(default_factory=list)
    created_at: datetime
    expires_at: datetime
