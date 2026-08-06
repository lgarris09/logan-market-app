from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from .common import Domain


class ActivityRecord(BaseModel):
    activity_type: str
    detail: str
    occurred_at: datetime


class ScheduledEvent(BaseModel):
    label: str
    scheduled_at: datetime


class LiveState(BaseModel):
    domain: Domain
    entity_id: str
    state: object


class ActiveContext(BaseModel):
    schema_version: str = "1.0"
    session_id: UUID
    # Required, non-empty (V3.1.4 BATCH-2) -- ActiveContext had no user
    # ownership at all before this; every other per-user contract
    # (MemoryRecord, UserModel, AttentionState, OutcomeRecord) already
    # required one. See docs/DECISIONS.md ADR-033 for the same requirement
    # on MemoryRecord; this extends the same discipline here.
    user_id: str
    current_question: Optional[str] = None
    time_of_day: Literal["morning", "midday", "afternoon", "evening", "night"]
    recent_activity: list[ActivityRecord] = Field(default_factory=list)
    temporary_intent: Optional[str] = None
    upcoming_events: list[ScheduledEvent] = Field(default_factory=list)
    live_context: list[LiveState] = Field(default_factory=list)
    created_at: datetime
    expires_at: datetime

    @field_validator("user_id")
    @classmethod
    def _user_id_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError(
                "user_id must be a non-empty, stable identifier — never empty or anonymous"
            )
        return value
