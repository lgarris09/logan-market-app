from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .common import Domain


class PrioritizedItem(BaseModel):
    schema_version: str = "1.0"
    event_id: UUID
    visibility: Literal["primary", "feed", "background", "hidden"]
    interruption: Literal["alert", "digest", "none"]
    rank: int = Field(ge=1)
    cooldown_until: Optional[datetime] = None
    changed_since_view: bool
    # Whether *this user* has acknowledged/reviewed this event_id before --
    # deliberately not derived from World Model event identity/dedup
    # (EnrichedEvent.is_new answers "is this the same underlying event," a
    # separate question). Computed from AttentionState.notifications_reviewed
    # in PrioritizationEngine.prioritize(); cleared only by an explicit
    # mark_reviewed() call, never by re-observing the same event again.
    is_new_for_user: bool
    prioritized_at: datetime
    decision_trace: list = Field(default_factory=list)
    # Operational Beta Hardening Block 2 (Controlled Exploration), extended
    # by Universe Manager V1a Blocks 11-14 -- set only when this codebase
    # has an honest, non-fabricated answer for "what actually drove this
    # item's visibility": one of the two per-item deterministic anti-echo-
    # chamber promotion reasons (exploration/engine.py), the batch-level
    # "at most one among the top five" placement reason
    # (exploration/placement.py's EXPLORATION_OBJECTIVE_STRENGTH), or
    # "personal_relevance" for the ordinary path when that dimension
    # genuinely dominated. None means either exploration wasn't wired in by
    # this caller, or the true driver is genuinely blended -- never a
    # fabricated single reason.
    attention_reason: Optional[
        Literal[
            "personal_relevance",
            "strong_world_signal",
            "unseen_material_change",
            "EXPLORATION_OBJECTIVE_STRENGTH",
        ]
    ] = None


class SurfaceRecord(BaseModel):
    event_id: UUID
    surfaced_at: datetime


# RESERVED, UNWIRED (V3.1.4 BATCH-2 review): part of AttentionState's contract
# shape, but nothing in PrioritizationEngine appends to AttentionState.dismissed
# or .alerted -- a "dismiss" interaction currently flows only through
# FeedbackEngine -> LearningEngine -> MemoryStore (see feedback/engine.py,
# learning/engine.py), never touching Prioritization/AttentionState at all.
# Not required by the current vertical slice; kept for when Prioritization
# itself needs to track per-item dismiss/alert history (e.g. to avoid
# re-surfacing a dismissed item), not removed as obsolete.
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
    domain: Domain
    count: int = Field(ge=0)
    window: datetime


# Deliberately a new, narrowly-named record rather than reusing DismissRecord:
# "reviewed the notification list" and "dismissed this opportunity" are
# different user actions with different implications (dismiss is documented
# as a future signal to stop *re-surfacing* an item at all; reviewing a
# notification only clears its unread badge, the opportunity itself stays
# fully visible/interactive in the field). Conflating the two would make a
# future real "dismiss" feature inherit unread-badge semantics it doesn't
# want, or vice versa.
class NotificationReviewRecord(BaseModel):
    event_id: UUID
    reviewed_at: datetime


class AttentionState(BaseModel):
    schema_version: str = "1.0"
    user_id: str
    surfaced: list[SurfaceRecord] = Field(default_factory=list)
    dismissed: list[DismissRecord] = Field(default_factory=list)
    alerted: list[AlertRecord] = Field(default_factory=list)
    cooldowns: list[CooldownRecord] = Field(default_factory=list)
    fatigue: list[FatigueRecord] = Field(default_factory=list)
    notifications_reviewed: list[NotificationReviewRecord] = Field(default_factory=list)
    last_updated: datetime
