from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from .common import (
    EvaluationHorizon,
    InvalidationStatus,
    Resolvability,
    VerificationQuality,
)

InteractionType = Literal[
    "view", "click", "dismiss", "save", "act", "share", "watch", "remind"
]
InferredIntent = Literal[
    "interested",
    "curious",
    "dismissing",
    "confused",
    "accidental",
    "researching",
    "unknown",
]


class FeedbackSignal(BaseModel):
    schema_version: str = "1.0"
    event_id: UUID
    interaction_type: InteractionType
    inferred_intent: InferredIntent
    intent_confidence: float = Field(ge=0.0, le=1.0)
    duration_ms: Optional[int] = None
    raw_interaction: str
    observed_at: datetime
    decision_trace: list = Field(default_factory=list)

    @model_validator(mode="after")
    def _low_confidence_is_unknown(self):
        if self.intent_confidence < 0.50 and self.inferred_intent != "unknown":
            raise ValueError(
                "inferred_intent must be 'unknown' when intent_confidence < 0.50"
            )
        return self


class OutcomeRecord(BaseModel):
    """Redesigned in v3.1.3 per ADR-036: outcomes are not reduced to a win/loss
    field. `result`/`expected`/`accuracy` are retained only as deprecated
    compatibility fields — no code in this repository constructs them; new code
    must use `observed_result`/`raw_predicted_value` instead. See
    OUTCOME_EVALUATION.md, which is authoritative on the full shape and must be
    read together with this contract.
    """

    schema_version: str = "2.0"
    outcome_id: UUID
    event_id: UUID
    # opportunity_id/prediction_id: no Opportunity Lifecycle layer with its own
    # stable ID exists in the running code yet (see 23_CURRENT_IMPLEMENTATION_STATE.md)
    # — both are kept optional here rather than required as in 07_DATA_CONTRACTS.md's
    # documentation-level table, since nothing in this codebase can supply
    # opportunity_id today. Flagged as a compatibility deviation, not silently done.
    opportunity_id: Optional[UUID] = None
    prediction_id: Optional[UUID] = None
    user_id: str
    entity_id: str
    trigger_event_ids: list[UUID] = Field(default_factory=list)
    evidence_ids: list[UUID] = Field(default_factory=list)
    outcome_type: Literal[
        "signal_accuracy",
        "source_reliability",
        "user_value",
        "market_resolution",
        "event_resolution",
    ]
    prediction_or_claim_type: str
    # The full predicted claim (domain-specific shape) — not just a direction/
    # magnitude pair. See OUTCOME_EVALUATION.md's worked example.
    raw_predicted_value: object
    created_at: datetime
    evaluation_horizon: EvaluationHorizon
    resolvability: Resolvability
    # Populated only when resolvability == "resolved" — enforced below. Never
    # fabricated: a caller must not set resolvability="resolved" without a real
    # observed_result, and must not attach one otherwise.
    observed_result: Optional[object] = None
    invalidation_status: InvalidationStatus = "none"
    invalidation_conditions: list[str] = Field(default_factory=list)
    verification_quality: VerificationQuality
    # Per-trigger contribution records, not a win/loss tally. Shape intentionally
    # left generic — TriggerEvent isn't implemented in code yet (see
    # 23_CURRENT_IMPLEMENTATION_STATE.md), so nothing here assumes its structure.
    source_contribution: list = Field(default_factory=list)
    decision_trace_ref: Optional[str] = None

    # --- Deprecated v1 compatibility fields — superseded, not deleted (ADR-036) ---
    result: Optional[object] = None  # deprecated — use observed_result
    expected: Optional[object] = None  # deprecated — use raw_predicted_value
    accuracy: Optional[float] = Field(default=None, ge=0.0, le=1.0)  # retained

    resolved_at: datetime
    delay_window: Literal["immediate", "hours", "days", "months"]  # retained
    learning_applied: bool = False

    @model_validator(mode="after")
    def _observed_result_matches_resolvability(self):
        if self.resolvability == "resolved" and self.observed_result is None:
            raise ValueError(
                "observed_result must be populated when resolvability is 'resolved'"
            )
        if self.resolvability != "resolved" and self.observed_result is not None:
            raise ValueError(
                "observed_result must be null unless resolvability is 'resolved' (no fabricated outcomes)"
            )
        return self
