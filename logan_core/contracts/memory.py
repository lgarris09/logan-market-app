from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

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
    # Required per-user isolation (ADR-033) — never empty/anonymous. The current
    # local/founder-only workflow uses LOCAL_FOUNDER_USER_ID (see contracts/common.py)
    # rather than a real multi-user identity. Independent of the ADR-006 database
    # decision — see ML_PRIVACY_AND_DATA_SEPARATION.md.
    user_id: str
    record_type: RecordType
    content: object
    domain: Optional[str] = None
    entities: list[str] = Field(default_factory=list)
    source_layer: Literal["learning_system"] = "learning_system"
    created_at: datetime
    last_accessed: Optional[datetime] = None
    decay_weight: float = Field(default=1.0, ge=0.0, le=1.0)
    operational_ref: Optional[UUID] = None

    @field_validator("user_id")
    @classmethod
    def _user_id_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("user_id must be a non-empty, stable identifier (ADR-033) — never empty or anonymous")
        return value
