"""STRATUS 3.6.12 -- Notification Candidate + Decision Ledger V1: pure
assembly/decision functions.

Mirrors notification_gate.py's own discipline exactly: every function here
is pure, deterministic, and takes every fact it needs as an explicit
parameter -- nothing is re-derived, re-scored, or looked up from durable
storage directly (that stays backend/app/logan_feed.py's job, same as
notification_gate.decide_notification()'s own established boundary).
Nothing here persists anything (backend/app/notification_ledger_store.py
owns durability) and nothing here is read by any real send/suppress code
path -- see logan_core/contracts/notification_ledger.py's own top-of-file
docstring for the full shadow-mode guarantee this depends on.
"""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from logan_core.contracts import (
    EarnedNotificationInputs,
    EvidenceCredibilitySnapshot,
    EvidenceSnapshot,
    LedgerDecision,
    MeaningfulChangeType,
    NotificationCandidate,
    PrioritizationSnapshot,
    RevisionSnapshot,
    ShadowDimensionState,
    ShadowEvaluation,
    WatchDecisionSnapshot,
)
from logan_core.policy.engine import (
    EXCEPTIONAL_CONFIDENCE_FLOOR,
    PERSONAL_INFERRED_URGENCY_FLOOR,
)

from .notification_gate import NotificationDecision
from .sync import UserOpportunityKnowledge


def build_notification_candidate(
    *,
    candidate_id: UUID,
    event_id: UUID,
    user_id: str,
    entity_id: str,
    ticker: Optional[str],
    signal_family: Optional[str],
    now: datetime,
    source_captured_at: Optional[datetime],
    is_watched: bool,
    watch_route: Literal["personal", "exceptional", "none"],
    communication_mode: Literal["analysis", "alert", "informational", "suppressed"],
    personal_relevance: float,
    connection_strength: float,
    visibility: Literal["primary", "feed", "background", "hidden"],
    interruption: Literal["alert", "digest", "none"],
    in_cooldown: bool,
    domain_fatigued: bool,
    thesis_revision: Optional[int],
    is_notification_worthy: Optional[bool],
    change_type: Optional[MeaningfulChangeType],
    knowledge: Optional[UserOpportunityKnowledge],
    confidence_score: float,
    classification: Literal["fact", "inference", "hypothesis", "speculation"],
    provider_degraded: bool,
    freshness_state: Optional[str],
    market_evidence: Optional[EvidenceSnapshot],
    earned_notification_inputs: EarnedNotificationInputs,
    model_version: Optional[str] = None,
    trigger_codes: Optional[list[str]] = None,
    first_detected_at: Optional[datetime] = None,
) -> NotificationCandidate:
    """Assembles a NotificationCandidate from already-computed inputs only.
    `candidate_id` is supplied by the caller (deterministic, derived from
    (user_id, event_id, thesis_revision) -- see notification_ledger_store.py)
    so this stays a pure function with no ID-generation policy of its own.
    """
    return NotificationCandidate(
        candidate_id=candidate_id,
        event_id=event_id,
        user_id=user_id,
        entity_id=entity_id,
        ticker=ticker,
        signal_family=signal_family,
        thesis_id=entity_id,
        created_at=now,
        source_captured_at=source_captured_at,
        model_version=model_version,
        qualification_state="qualified" if trigger_codes else None,
        trigger_codes=trigger_codes,
        first_detected_at=first_detected_at,
        watch=WatchDecisionSnapshot(
            is_watched=is_watched,
            watch_route=watch_route,
            communication_mode=communication_mode,
            personal_relevance=personal_relevance,
            connection_strength=connection_strength,
        ),
        prioritization=PrioritizationSnapshot(
            visibility=visibility,
            interruption=interruption,
            in_cooldown=in_cooldown,
            domain_fatigued=domain_fatigued,
        ),
        revision=RevisionSnapshot(
            thesis_revision=thesis_revision,
            is_notification_worthy=is_notification_worthy,
            change_type=change_type,
            last_seen_revision=knowledge.last_seen_revision if knowledge else None,
            last_notified_revision=(
                knowledge.last_notified_revision if knowledge else None
            ),
            last_notified_at=knowledge.last_notified_at if knowledge else None,
            last_notified_change_type=(
                knowledge.last_notified_change_type if knowledge else None
            ),
        ),
        evidence=EvidenceCredibilitySnapshot(
            confidence_score=confidence_score,
            classification=classification,
            provider_degraded=provider_degraded,
            freshness_state=freshness_state,
        ),
        market_evidence=market_evidence,
        earned_notification_inputs=earned_notification_inputs,
    )


def determine_ledger_outcome(
    *,
    policy_permitted: bool,
    communication_mode: str,
    interruption: str,
    in_cooldown: bool,
    domain_fatigued: bool,
    material_delta_decision: Optional[NotificationDecision],
) -> tuple[Literal["SEND", "SUPPRESS"], str]:
    """The real SEND/SUPPRESS outcome + reason, derived entirely from
    already-computed PolicyEngine/PrioritizationEngine facts and (when
    production actually reached it) notification_gate.decide_notification()'s
    own verdict -- never a second material-delta/revision/cooldown
    evaluation. Matches PrioritizationEngine.prioritize()'s own precedence
    exactly (not policy_permitted, then in_cooldown, then domain_fatigued,
    then communication_mode) so a suppression reason here is never anything
    other than the actual, already-computed cause.
    """
    if interruption == "alert":
        # decide_notification() is only ever called in production once
        # interruption=="alert" already holds (backend/app/logan_feed.py's
        # own per-entity loop) -- reuse its exact verdict here, never
        # re-derive material-delta/revision/cooldown logic.
        if material_delta_decision is None:
            raise ValueError(
                "material_delta_decision is required when interruption == 'alert' "
                "-- production always calls decide_notification() in this case"
            )
        if material_delta_decision.should_notify:
            return "SEND", "new_material_revision"
        return "SUPPRESS", material_delta_decision.reason

    # decide_notification() was never reached in production for this poll --
    # the real reason is whichever of these already-computed facts is the
    # one that actually kept interruption from becoming "alert".
    if not policy_permitted:
        return "SUPPRESS", "policy_suppressed"
    if in_cooldown:
        return "SUPPRESS", "view_cooldown_active"
    if domain_fatigued:
        return "SUPPRESS", "interruption_budget_exhausted"
    return "SUPPRESS", "insufficient_personal_relevance_or_urgency"


def _bool_dimension(value: Optional[bool], basis: str) -> ShadowDimensionState:
    if value is None:
        return ShadowDimensionState(state="NOT_EVALUATED", basis=basis)
    return ShadowDimensionState(
        state="FAVORABLE" if value else "UNFAVORABLE", basis=basis
    )


def evaluate_shadow(
    *,
    is_notification_worthy: Optional[bool],
    watch_route: Literal["personal", "exceptional", "none"],
    domain_fatigued: bool,
    in_cooldown: bool,
    earned_notification_inputs: EarnedNotificationInputs,
) -> ShadowEvaluation:
    """Shadow-only evaluation of the five Earned-Interruption dimensions --
    see logan_core/contracts/notification_ledger.py's own docstring for the
    full shadow-mode guarantee. Three dimensions reuse a real, already-
    computed production gate outright (material_delta, personal_relevance,
    interruption_budget); the remaining two (credible_evidence,
    time_sensitivity) have no dedicated production threshold yet, so this
    reuses PolicyEngine's own existing Exceptional-route anchors
    (EXCEPTIONAL_CONFIDENCE_FLOOR, PERSONAL_INFERRED_URGENCY_FLOOR) applied
    to EarnedNotificationInputs' own evidence_credibility/time_sensitivity
    fields -- reused numbers, never invented ones, explicitly labeled
    provisional in each dimension's own `basis` string.
    """
    material_delta = _bool_dimension(
        is_notification_worthy,
        "LifecycleDelta.is_notification_worthy (real production material-delta gate)",
    )
    personal_relevance = ShadowDimensionState(
        state="FAVORABLE" if watch_route != "none" else "UNFAVORABLE",
        basis=(
            f"PolicyEngine watch_route={watch_route} "
            "(real production Personal/Exceptional Watch gate)"
        ),
    )
    interruption_budget = ShadowDimensionState(
        state="FAVORABLE" if not (domain_fatigued or in_cooldown) else "UNFAVORABLE",
        basis=(
            f"PrioritizationEngine domain_fatigued={domain_fatigued}, "
            f"in_cooldown={in_cooldown} (real production interruption-budget gate)"
        ),
    )
    credible_evidence = ShadowDimensionState(
        state=(
            "FAVORABLE"
            if earned_notification_inputs.evidence_credibility
            >= EXCEPTIONAL_CONFIDENCE_FLOOR
            else "UNFAVORABLE"
        ),
        basis=(
            f"EvidenceTrust.trust_score={earned_notification_inputs.evidence_credibility:.2f} "
            f">= {EXCEPTIONAL_CONFIDENCE_FLOOR} (PolicyEngine's existing Exceptional-route "
            "confidence anchor, reused provisionally here -- no dedicated evidence-"
            "credibility threshold exists in production notification policy yet)"
        ),
    )
    time_sensitivity = ShadowDimensionState(
        state=(
            "FAVORABLE"
            if earned_notification_inputs.time_sensitivity
            >= PERSONAL_INFERRED_URGENCY_FLOOR
            else "UNFAVORABLE"
        ),
        basis=(
            f"Dimensions.urgency={earned_notification_inputs.time_sensitivity:.2f} "
            f">= {PERSONAL_INFERRED_URGENCY_FLOOR} (PolicyEngine's existing Personal-route "
            "inferred-tier urgency anchor, reused provisionally here -- no dedicated "
            "time-sensitivity threshold exists in production notification policy yet)"
        ),
    )

    states = [
        material_delta.state,
        credible_evidence.state,
        personal_relevance.state,
        time_sensitivity.state,
        interruption_budget.state,
    ]
    if "UNFAVORABLE" in states:
        overall: Literal["FAVORABLE", "UNFAVORABLE", "NOT_EVALUATED"] = "UNFAVORABLE"
    elif "NOT_EVALUATED" in states:
        overall = "NOT_EVALUATED"
    else:
        overall = "FAVORABLE"

    return ShadowEvaluation(
        material_delta=material_delta,
        credible_evidence=credible_evidence,
        personal_relevance=personal_relevance,
        time_sensitivity=time_sensitivity,
        interruption_budget=interruption_budget,
        would_earn_interruption=overall,
    )


def build_ledger_decision(
    *,
    decision_id: UUID,
    candidate: NotificationCandidate,
    policy_permitted: bool,
    now: datetime,
    material_delta_decision: Optional[NotificationDecision],
) -> LedgerDecision:
    """Assembles the final LedgerDecision (real outcome/reason + shadow
    companion) for one already-built NotificationCandidate."""
    outcome, reason = determine_ledger_outcome(
        policy_permitted=policy_permitted,
        communication_mode=candidate.watch.communication_mode,
        interruption=candidate.prioritization.interruption,
        in_cooldown=candidate.prioritization.in_cooldown,
        domain_fatigued=candidate.prioritization.domain_fatigued,
        material_delta_decision=material_delta_decision,
    )
    shadow = evaluate_shadow(
        is_notification_worthy=candidate.revision.is_notification_worthy,
        watch_route=candidate.watch.watch_route,
        domain_fatigued=candidate.prioritization.domain_fatigued,
        in_cooldown=candidate.prioritization.in_cooldown,
        earned_notification_inputs=candidate.earned_notification_inputs,
    )
    return LedgerDecision(
        decision_id=decision_id,
        candidate_id=candidate.candidate_id,
        user_id=candidate.user_id,
        event_id=candidate.event_id,
        outcome=outcome,
        reason=reason,
        decided_at=now,
        shadow=shadow,
    )
