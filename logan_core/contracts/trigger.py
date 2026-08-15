from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from .common import DecisionTraceEntry, Domain

# Sprint 3.6.6 — minimal TriggerEvent, not the full canonical contract in
# TRIGGER_EVENT_FRAMEWORK.md. That document's ~60-field shape (revision
# model, dedup/identity, lifecycle_effect, seasonal_context,
# provider_disagreement_state, policy gates, notification_eligibility,
# causal_relationship, etc.) remains SPECIFIED — NOT IMPLEMENTED (OD-009);
# this only implements the subset the first live vertical slice
# (NVIDIA earnings -> STOCK_EARNINGS_BEAT) can truthfully populate. See
# docs/DECISIONS.md's Sprint 3.6.6 ADR and
# 23_CURRENT_IMPLEMENTATION_STATE.md for exactly what moved from
# SPECIFIED to BUILT.
#
# Deliberately excluded from this minimal contract (would require either
# fabricating data no provider supplies yet, or building revision/dedup
# machinery this one-trigger-code slice doesn't exercise):
# revision_number/supersedes_revision, expiration_timestamp, domain_impacts,
# verification_status, action_window_start/end, decay_profile,
# seasonal_context, causal_relationship, related/contradicting/invalidating
# trigger_ids, provider_disagreement_state, legal_or_policy_gate,
# notification_eligibility, recalculation_required, user_update_required.

TriggerClass = Literal["catalyst", "confirmation", "contradiction", "invalidation"]
TriggerStatus = Literal["detected", "confirmed"]
TriggerDirection = Literal["positive", "negative", "neutral"]


class TriggerEvent(BaseModel):
    schema_version: str = "1.0"
    trigger_id: UUID
    trigger_code: str
    trigger_class: TriggerClass
    trigger_type: str
    trigger_status: TriggerStatus
    domain: Domain
    affected_entity_id: str
    direction: TriggerDirection
    # Real, provider-derived magnitude (e.g. beat_pct for STOCK_EARNINGS_BEAT).
    # Never a placeholder/estimated value.
    raw_magnitude: float
    # Deterministic confidence contribution from the registry (e.g. +0.22 for
    # STOCK_EARNINGS_BEAT per TRIGGER_REGISTRY_STOCKS.md) -- a fixed constant
    # keyed to trigger_code, not computed/learned. See
    # evidence_trust/trust.py's trigger_confidence_bonus for how this is
    # consumed; this field only carries the value, it does not apply it.
    confidence_contribution: float = Field(ge=-1.0, le=1.0)
    # Real fields the provider actually supplied, using the registry's own
    # documented context shape (TRIGGER_REGISTRY_STOCKS.md) as the key
    # vocabulary -- absent/unknown fields are omitted, never fabricated. See
    # the provider mapping in receptors/stocks_earnings.py.
    context: dict = Field(default_factory=dict)
    originating_signal_ids: list[UUID] = Field(default_factory=list)
    source_id: str
    source_name: str
    event_timestamp: datetime
    detected_timestamp: datetime
    decision_trace: list[DecisionTraceEntry] = Field(default_factory=list)


__all__ = ["TriggerEvent", "TriggerClass", "TriggerStatus", "TriggerDirection"]
