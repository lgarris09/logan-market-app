from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

MemoryType = Literal[
    "core",
    "strategic",
    "contextual",
    "behavioral_signal",
    "temporary",
    "noise",
]

MemoryStatus = Literal[
    "proposed",
    "observed",
    "reinforced",
    "confirmed",
    "core",
    "rejected",
]

MemoryAction = Literal["stored", "inbox", "ignored"]


class MemoryCreate(BaseModel):
    content: str = Field(min_length=2, max_length=2000)
    active_category: str = Field(default="user_profile")
    source: str = Field(default="user_statement")
    user_confirmed: bool = False


class MemoryRecord(BaseModel):
    id: str
    content: str
    primary_branch: str
    linked_branches: list[str]
    memory_type: MemoryType
    importance: int = Field(ge=0, le=100)
    confidence: int = Field(ge=0, le=100)
    status: MemoryStatus
    action: MemoryAction
    source: str
    reinforcement_count: int
    created_at: datetime
    updated_at: datetime


class MemoryDecision(BaseModel):
    memory: MemoryRecord
    explanation: str


class MemoryConfirm(BaseModel):
    confirmed: bool


class CategoryContext(BaseModel):
    active_category: str
    memories: list[MemoryRecord]
