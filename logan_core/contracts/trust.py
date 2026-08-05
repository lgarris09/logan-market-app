from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from .common import EvaluationHorizon, InvalidationStatus, Resolvability, VerificationQuality


class EvidenceTrust(BaseModel):
    schema_version: str = "1.0"
    event_id: UUID
    source_score: float = Field(ge=0.0, le=1.0)
    corroboration: int = Field(ge=0)
    recency_score: float = Field(ge=0.0, le=1.0)
    contradiction_flag: bool
    manipulation_risk: Literal["low", "medium", "high"]
    completeness: float = Field(ge=0.0, le=1.0)
    trust_score: float = Field(ge=0.0, le=1.0)
    # Reserved, non-functional metadata (ADR-032, MODEL_CONTRACTS.md). No trained
    # model exists this release — source_score/trust_score above are computed
    # exactly as before by the deterministic SOURCE_REPUTATION_REGISTRY formula.
    # This field exists so a future calibrated source-reliability model has
    # somewhere to declare its version; it must never be set to anything other
    # than the deterministic-baseline default without a real model behind it.
    source_reliability_model_version: Optional[str] = "deterministic-baseline"
    evaluated_at: datetime
    decision_trace: list = Field(default_factory=list)


class SourceObservation(BaseModel):
    """Future-facing, source-centric sibling of OutcomeRecord — a per-source
    accuracy/reliability observation, structured the same non-win/loss way
    (ADR-036's shape applied to sources rather than opportunities). This is the
    typed input a future source-reliability calibration pass (ADR-032) would
    consume; it is not wired into EvidenceTrustEngine and must not be — nothing
    in this codebase reads or constructs SourceObservation yet, and
    EvidenceTrust.source_score/trust_score remain computed exactly as before by
    SOURCE_REPUTATION_REGISTRY, unaffected by anything here.
    """

    schema_version: str = "1.0"
    observation_id: UUID
    source_id: str
    # Either a trigger_id or a claim_id identifies what this source reported on —
    # TriggerEvent isn't implemented in code yet, so this stays a bare string
    # rather than a typed UUID reference into a contract that doesn't exist.
    trigger_or_claim_id: str
    evaluation_horizon: EvaluationHorizon
    resolvability: Resolvability
    observed_result: Optional[object] = None
    verification_quality: VerificationQuality
    invalidation_status: InvalidationStatus = "none"
    evidence_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime
    resolved_at: Optional[datetime] = None

    @model_validator(mode="after")
    def _observed_result_matches_resolvability(self):
        if self.resolvability == "resolved" and self.observed_result is None:
            raise ValueError("observed_result must be populated when resolvability is 'resolved'")
        if self.resolvability != "resolved" and self.observed_result is not None:
            raise ValueError("observed_result must be null unless resolvability is 'resolved' (no fabricated outcomes)")
        return self
