"""STRATUS 3.6.12 -- Notification Candidate + Decision Ledger V1.

Shadow-mode foundation for future Earned Interruption (see docs/DECISIONS.md
for the full ADR). Answers, for every lifecycle-tracked entity STRATUS
evaluates for a user: "what could we have notified this user about, what
evidence existed, why did STRATUS send or suppress it, and was that decision
based on the actual state at that moment?"

This module owns the DECISION-PROVENANCE *shape* only -- mirrors
opportunity_lifecycle/notification_gate.py's own discipline exactly: every
field here is captured from an already-computed value handed in by the
caller (backend/app/logan_feed.py), never re-derived or re-scored here.
Nothing in this module decides anything (that stays PolicyEngine/
PrioritizationEngine/decide_notification's own authority) and nothing here
persists anything (backend/app/notification_ledger_store.py owns
durability).

Core principle (verbatim from the governing instruction): future earned
interruption is based on material delta AND credible evidence AND personal
relevance AND time sensitivity AND interruption budget. These five
dimensions are modeled independently below (never collapsed into one opaque
composite "notification score") in both the real decision
(`LedgerSuppressionReason` maps each production suppression directly onto
one of these dimensions, or "policy_suppressed" for the one existing gate
outside the five) and the shadow evaluation (`ShadowEvaluation`, one
`ShadowDimensionState` per dimension).

Shadow-mode guarantee: `ShadowEvaluation` is populated by reusing already-
computed real signals -- watch_route/domain_fatigued/in_cooldown for the
three dimensions with an existing real gate, and, for the two with no
production gate yet (credible_evidence, time_sensitivity), Operational Beta
Hardening Block 8's own `EarnedNotificationInputs` (backend/app/
earned_notification_inputs.py) -- `evidence_credibility` (EvidenceTrust.
trust_score) and `time_sensitivity` (Dimensions.urgency), the exact typed
snapshot that block built specifically to be a future notification pass's
input, never wired into any real decision. A single existing PolicyEngine
threshold constant is reused (never a new number invented) to turn each of
those two continuous values into a FAVORABLE/UNFAVORABLE verdict -- see
`evaluate_shadow()`'s own docstring for exactly which constant and why.
Written to the ledger only; nothing in this codebase's send/suppress path
ever reads it, so it structurally cannot alter, broaden, or narrow real
notification behavior.
"""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel

from .lifecycle import EvidenceSnapshot, MeaningfulChangeType
from .policy import EarnedNotificationInputs

# --- Real decision model ----------------------------------------------------

# Every value here is either reused verbatim from
# opportunity_lifecycle/notification_gate.py's own NotificationDecisionReason
# (new_material_revision, no_material_delta, same_revision_suppressed,
# cooldown_suppressed, provider_degraded_suppressed) -- the material-delta
# dimension, already-owned, real production policy -- or derived directly
# from an already-computed PolicyEngine/PrioritizationEngine boolean/field
# for the "never reached decide_notification at all" case (interruption !=
# "alert"): policy_suppressed (PolicyResult.permitted is False, e.g.
# bot-risk), view_cooldown_active/interruption_budget_exhausted
# (PrioritizationEngine's own in_cooldown/domain_fatigued -- the
# interruption-budget dimension), insufficient_personal_relevance_or_urgency
# (PolicyEngine's watch_route == "none" -- the personal-relevance dimension).
# None of these are invented thresholds; each names a real, already-computed
# fact this codebase's actual policy produced.
LedgerSuppressionReason = Literal[
    "policy_suppressed",
    "view_cooldown_active",
    "interruption_budget_exhausted",
    "insufficient_personal_relevance_or_urgency",
    "no_material_delta",
    "same_revision_suppressed",
    "cooldown_suppressed",
    "provider_degraded_suppressed",
    # ADR-080 fail-closed reasons, reused verbatim from notification_gate.
    "beta_notifications_paused",
    "freshness_unestablished_suppressed",
    "stale_evidence_suppressed",
    "revision_unattributable_suppressed",
]

# The only real production "yes" path today -- reached exclusively through
# decide_notification() returning should_notify=True, itself only reachable
# once interruption=="alert" already cleared every gate above.
LedgerSendReason = Literal["new_material_revision"]

LedgerOutcome = Literal["SEND", "SUPPRESS"]


class WatchDecisionSnapshot(BaseModel):
    """Decision-time Watch/Policy-route facts, captured once -- never
    reconstructed later from a changed UserModel/Watch list."""

    schema_version: str = "1.0"
    is_watched: bool
    watch_route: Literal["personal", "exceptional", "none"]
    communication_mode: Literal["analysis", "alert", "informational", "suppressed"]
    personal_relevance: float
    connection_strength: float


class PrioritizationSnapshot(BaseModel):
    """Decision-time Prioritization facts -- visibility/interruption plus
    the two real interruption-budget vetoes (fatigue, view cooldown)."""

    schema_version: str = "1.0"
    visibility: Literal["primary", "feed", "background", "hidden"]
    interruption: Literal["alert", "digest", "none"]
    in_cooldown: bool
    domain_fatigued: bool


class RevisionSnapshot(BaseModel):
    """Thesis/revision identity and prior-notification provenance --
    entirely reused from LifecycleDelta/UserOpportunityKnowledge, never a
    parallel identity system. `thesis_revision` is the *global*, objective
    revision counter (OpportunityRevisionStore); `last_notified_revision`/
    `last_notified_at`/`last_notified_change_type` are this user's own
    durable high-water marks (UserOpportunityKnowledge) -- the same
    pointers notification_gate.decide_notification() itself reads.
    """

    schema_version: str = "1.0"
    thesis_revision: Optional[int] = None
    is_notification_worthy: Optional[bool] = None
    change_type: Optional[MeaningfulChangeType] = None
    last_seen_revision: Optional[int] = None
    last_notified_revision: Optional[int] = None
    last_notified_at: Optional[datetime] = None
    last_notified_change_type: Optional[MeaningfulChangeType] = None


class EvidenceCredibilitySnapshot(BaseModel):
    """Decision-time evidence/credibility facts not already carried by
    `EarnedNotificationInputs` below -- confidence_score/classification
    reused verbatim from ConclusionConfidence, provider_degraded from this
    poll's own real fetch outcome, freshness_state from the existing
    runtime freshness classification (None when no freshness contract is
    registered for this signal family, e.g. a demo/simulated entity --
    never a fabricated state).
    """

    schema_version: str = "1.0"
    confidence_score: float
    classification: Literal["fact", "inference", "hypothesis", "speculation"]
    provider_degraded: bool
    freshness_state: Optional[str] = None


class NotificationCandidate(BaseModel):
    """One user-scoped notification candidate: everything STRATUS actually
    knew at the moment it decided whether to interrupt this user about this
    entity. Scope (a deliberate, documented boundary -- see
    backend/app/logan_feed.py's own wiring comment): recorded only for
    entities with active lifecycle tracking this poll (the exact same set
    notification_gate.decide_notification() already evaluates in
    production) -- not every simulated/demo entity, since those have no
    real revision concept to evaluate a notification decision against.
    """

    schema_version: str = "1.0"
    candidate_id: UUID
    event_id: UUID
    user_id: str
    entity_id: str
    ticker: Optional[str] = None
    signal_family: Optional[str] = None
    # Stock Opportunity Logic V2.1 (ADR-067): this codebase currently has
    # exactly one thesis per entity_id (no distinct thesis-clustering
    # concept exists yet -- see this repo's own standing "do not create
    # semantic clustering" instruction), so thesis_id == entity_id today.
    # Kept as its own named field (not silently aliased) so a future
    # multi-thesis-per-entity model only needs to change how this value is
    # populated, never every caller/reader of this contract.
    thesis_id: str
    created_at: datetime
    source_captured_at: Optional[datetime] = None
    # ADR-081 attribution. `model_version` names the evidence / qualification
    # rules in force when this candidate was evaluated
    # (logan_core.contracts.model_version.EVIDENCE_MODEL_VERSION).
    # `trigger_codes` are the qualifying triggers behind the opportunity; an
    # opportunity only exists because at least one trigger qualified, so
    # `qualification_state` is "qualified" by construction here -- blocked
    # observations never become candidates. All optional so rows written
    # before these fields existed still parse.
    model_version: Optional[str] = None
    qualification_state: Optional[str] = None
    trigger_codes: Optional[list[str]] = None
    # When the opportunity was first detected (lifecycle first_seen_at).
    first_detected_at: Optional[datetime] = None
    watch: WatchDecisionSnapshot
    prioritization: PrioritizationSnapshot
    revision: RevisionSnapshot
    evidence: EvidenceCredibilitySnapshot
    market_evidence: Optional[EvidenceSnapshot] = None
    # Operational Beta Hardening Block 8's own typed shadow-notification
    # snapshot (backend/app/earned_notification_inputs.py), embedded
    # wholesale rather than re-derived -- this is exactly the "richer
    # future notification dimensions" input that block was built to
    # prepare, so the ledger reuses it as-is for evidence_credibility
    # (EvidenceTrust.trust_score) and time_sensitivity (Dimensions.urgency).
    earned_notification_inputs: EarnedNotificationInputs


# --- Shadow-mode evaluation --------------------------------------------------


class ShadowDimensionState(BaseModel):
    """One independently-recorded shadow dimension. NOT_EVALUATED, never a
    fabricated FAVORABLE/UNFAVORABLE, whenever the underlying already-
    computed fact this dimension reuses is itself absent (e.g. no
    freshness contract registered for this signal family)."""

    schema_version: str = "1.0"
    state: Literal["FAVORABLE", "UNFAVORABLE", "NOT_EVALUATED"]
    basis: str


class ShadowEvaluation(BaseModel):
    """Shadow-only, additive evaluation of the five Earned-Interruption
    dimensions -- reused verbatim from real policy where a real gate
    already exists (material_delta, personal_relevance, interruption_
    budget), a simple, explicitly-provisional threshold over an existing
    computed fact where none exists yet (credible_evidence,
    time_sensitivity). Never read by any send/suppress code path; written
    to the ledger for later comparison only. `would_earn_interruption` is
    a transparent three-valued combination (never a numeric blend): any
    UNFAVORABLE dimension makes the whole evaluation UNFAVORABLE
    regardless of others' NOT_EVALUATED status; NOT_EVALUATED only when no
    dimension is UNFAVORABLE but at least one could not be evaluated;
    FAVORABLE only when every dimension is FAVORABLE.
    """

    schema_version: str = "1.0"
    material_delta: ShadowDimensionState
    credible_evidence: ShadowDimensionState
    personal_relevance: ShadowDimensionState
    time_sensitivity: ShadowDimensionState
    interruption_budget: ShadowDimensionState
    would_earn_interruption: Literal["FAVORABLE", "UNFAVORABLE", "NOT_EVALUATED"]


class LedgerDecision(BaseModel):
    """The final, explicit SEND/SUPPRESS verdict for one NotificationCandidate,
    plus its shadow-only companion evaluation. `reason` is always exactly
    the real production reason (LedgerSendReason for SEND,
    LedgerSuppressionReason for SUPPRESS) -- never invented, never blended
    into `shadow`.
    """

    schema_version: str = "1.0"
    decision_id: UUID
    candidate_id: UUID
    user_id: str
    event_id: UUID
    outcome: LedgerOutcome
    reason: str
    decided_at: datetime
    shadow: ShadowEvaluation
