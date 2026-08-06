from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

Domain = Literal["stocks", "sports", "poly", "social", "news", "crypto"]
EntityType = Literal["ticker", "team", "contract", "topic", "person"]

# The current single-operator local workflow's explicit, stable user identifier
# (ADR-033, ML_PRIVACY_AND_DATA_SEPARATION.md). Not an anonymous/empty placeholder —
# used wherever a caller doesn't yet have a real per-user identity to thread through.
# Does not imply multi-tenancy or a database decision (ADR-006 remains open).
LOCAL_FOUNDER_USER_ID = "demo_user"


class DecisionTraceEntry(BaseModel):
    layer: str
    rule: str
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    timestamp: datetime


class ExecutionMetrics(BaseModel):
    schema_version: str = "1.0"
    layer: str
    pipeline_run_id: UUID
    event_id: Optional[UUID] = None
    latency_ms: int = Field(ge=0)
    success: bool
    warnings: list[str] = Field(default_factory=list)
    retries: int = 0
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    recorded_at: datetime


class ExecutionTrace(BaseModel):
    schema_version: str = "1.0"
    pipeline_run_id: UUID
    event_id: Optional[UUID] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: Literal["running", "complete", "failed", "partial"] = "running"
    layers: list[ExecutionMetrics] = Field(default_factory=list)
    final_output: Optional[UUID] = None
    error: Optional[str] = None


class Entity(BaseModel):
    entity_id: str
    entity_type: EntityType
    display_name: str
    domain: Domain
    attributes: dict = Field(default_factory=dict)


class Delta(BaseModel):
    field: str
    prior_value: Optional[object] = None
    new_value: object
    unit: Optional[str] = None
    changed_at: datetime


class Reference(BaseModel):
    ref_type: Literal["signal", "event", "memory", "entity"]
    ref_id: UUID
    description: Optional[str] = None


# --- Shared outcome/observation-evaluation types (ADR-036) ---
# Used by both OutcomeRecord (contracts/feedback.py) and SourceObservation
# (contracts/trust.py) — kept here rather than duplicated so the two stay
# structurally consistent. See OUTCOME_EVALUATION.md.

Resolvability = Literal[
    "resolved",
    "unresolved_pending",
    "unresolvable_data_unavailable",
    "unresolvable_ambiguous",
]
InvalidationStatus = Literal[
    "none", "invalidated_before_resolution", "invalidated_at_resolution"
]
VerificationLevel = Literal[
    "verified", "partially_verified", "self_reported", "unverifiable"
]


class EvaluationHorizon(BaseModel):
    """When an outcome/observation is expected to become resolvable — {value, unit},
    plus an optional pointer to where the domain-specific timing came from. See
    OUTCOME_EVALUATION.md's timeline table.
    """

    value: float
    unit: str
    domain_source: Optional[str] = None


class VerificationQuality(BaseModel):
    """How an observed result was confirmed, and how much that confirmation itself
    should be trusted. `level` gates whether a record may ever influence any future
    accuracy rate — see OUTCOME_EVALUATION.md.
    """

    level: VerificationLevel
    method: str
    confidence_in_verification: float = Field(ge=0.0, le=1.0)
