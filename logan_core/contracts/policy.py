from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from .lifecycle import MeaningfulChangeType
from .personal_relevance import PersonalRelevanceResult


class PolicyResult(BaseModel):
    schema_version: str = "1.0"
    event_id: UUID
    permitted: bool
    communication_mode: Literal["analysis", "alert", "informational", "suppressed"]
    language_constraints: list[str] = Field(default_factory=list)
    required_disclaimers: list[str] = Field(default_factory=list)
    policy_rules_applied: list[str] = Field(default_factory=list)
    evaluated_at: datetime
    decision_trace: list = Field(default_factory=list)
    # STRATUS 3.6.12 (Notification Ledger V1): PolicyEngine.evaluate()
    # already computes this locally (_watch_route()) but, before this
    # field existed, only ever exposed it embedded in one decision_trace
    # rule string -- additive, defaults to "none" for any pre-existing
    # direct construction that doesn't supply it (there is no real
    # decision here to preserve byte-for-byte; "none" is also the correct,
    # honest value whenever communication_mode != "alert"). Lets a reader
    # (e.g. the notification ledger) distinguish the Personal vs
    # Exceptional Watch route without parsing a formatted string.
    watch_route: Literal["personal", "exceptional", "none"] = "none"

    @model_validator(mode="after")
    def _suppressed_when_not_permitted(self):
        if not self.permitted and self.communication_mode != "suppressed":
            raise ValueError(
                "communication_mode must be 'suppressed' when permitted is False"
            )
        return self


class LifecycleDeltaSummary(BaseModel):
    """The narrow slice of LifecycleDelta a future notification decision
    would actually need -- never the full delta (evidence/trajectory detail
    stays in LifecycleDelta itself; a notification-eligibility check has no
    business consuming raw EvidenceSnapshot fields)."""

    change_type: MeaningfulChangeType
    is_meaningful: bool
    is_notification_worthy: bool


class EarnedNotificationInputs(BaseModel):
    """Operational Beta Hardening Block 8 -- the typed input a future Full
    Earned Notifications pass would consume, mirroring SourceObservation's
    own precedent (contracts/trust.py): defined and populated from real,
    already-computed pipeline data, but not wired into PolicyEngine.evaluate()
    or notifications.py's dispatch_eligible_notifications() and must not be
    without a separate, explicit decision -- push eligibility today remains
    exactly `interruption == "alert"` via `_watch_route()`'s existing
    dims-only gate (ADR-049), byte-for-byte unaffected by this contract's
    existence.

    Every field here is a plain reference to (or narrow slice of) a contract
    this codebase already computes -- never a new score, never a new
    inference:
      material_delta            -- LifecycleDeltaSummary (Stock Opportunity
                                    Logic V2), None when lifecycle tracking
                                    isn't active for this entity/user.
      evidence_credibility       -- EvidenceTrust.trust_score (0.0-1.0),
                                    always present (evidence trust is
                                    computed for every event).
      personal_relevance_result  -- the same PersonalRelevanceResult already
                                    on AttentionRecommendation, unchanged.
      time_sensitivity           -- Dimensions.urgency (0.0-1.0), the
                                    existing "how time-sensitive" signal
                                    Opportunity Engine already computes --
                                    not a new time-sensitivity model.
      is_watched                 -- the same boolean PersonalRelevanceResult
                                    already carries.
    """

    schema_version: str = "1.0"
    event_id: UUID
    material_delta: Optional[LifecycleDeltaSummary] = None
    evidence_credibility: float = Field(ge=0.0, le=1.0)
    personal_relevance_result: Optional[PersonalRelevanceResult] = None
    time_sensitivity: float = Field(ge=0.0, le=1.0)
    is_watched: bool
    computed_at: datetime
