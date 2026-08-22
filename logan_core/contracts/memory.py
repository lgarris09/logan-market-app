from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from .common import Domain

RecordType = Literal[
    "user_statement",
    "behavior_record",
    "feedback_record",
    "outcome_record",
    "source_reliability",
    "prior_analysis",
    "preference_signal",
    "correction_record",
    # Sprint 3.6.7 Block 3: a deterministic exposure/impression fact -- "this
    # opportunity was shown to the user" -- not ambiguous behavior needing
    # FeedbackEngine's intent interpretation. Deliberately its own
    # record_type, not "feedback_record": UserModelBuilder's existing
    # behavioral-evidence folding (_fold_behavioral_evidence) filters on
    # record_type == "feedback_record" specifically, so exposure_records are
    # structurally excluded from ever being read as positive "interested"
    # evidence by that function -- impressions alone can never manufacture
    # relevance. See docs/DECISIONS.md's Sprint 3.6.7 Block 3 ADR.
    "exposure_record",
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
    domain: Optional[Domain] = None
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
            raise ValueError(
                "user_id must be a non-empty, stable identifier (ADR-033) — never empty or anonymous"
            )
        return value
