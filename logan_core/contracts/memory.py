from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

RecordType = Literal[
    "user_statement",
    "behavior_record",
    "feedback_record",
    "outcome_record",
    "source_reliability",
    "prior_analysis",
    "preference_signal",
    "correction_record",
]


class MemoryRecord(BaseModel):
    schema_version: str = "1.0"
    record_id: UUID
    record_type: RecordType
    content: object
    domain: Optional[str] = None
    entities: list[str] = Field(default_factory=list)
    source_layer: Literal["learning_system"] = "learning_system"
    created_at: datetime
    last_accessed: Optional[datetime] = None
    decay_weight: float = Field(default=1.0, ge=0.0, le=1.0)
    operational_ref: Optional[UUID] = None
