"""STRATUS 3.6.12 -- Notification Candidate + Decision Ledger V1. Pure unit
tests for logan_core/opportunity_lifecycle/notification_ledger.py. No
backend/SQLite/Orchestrator involved -- see
backend/tests/test_notification_ledger_integration.py for the
wired-through-backend tests, mirroring test_notification_gate.py's own
established split.
"""

from datetime import datetime, timezone
from uuid import uuid4

from logan_core.contracts import EarnedNotificationInputs, NotificationCandidate
from logan_core.opportunity_lifecycle import (
    NotificationDecision,
    UserOpportunityKnowledge,
    build_ledger_decision,
    build_notification_candidate,
    determine_ledger_outcome,
    evaluate_shadow,
)
from logan_core.policy.engine import (
    EXCEPTIONAL_CONFIDENCE_FLOOR,
    PERSONAL_INFERRED_URGENCY_FLOOR,
)

NOW = datetime(2026, 9, 10, 0, 0, 0, tzinfo=timezone.utc)
EVENT_ID = uuid4()


def _inputs(
    evidence_credibility=0.5, time_sensitivity=0.5, is_watched=False
) -> EarnedNotificationInputs:
    return EarnedNotificationInputs(
        event_id=EVENT_ID,
        material_delta=None,
        evidence_credibility=evidence_credibility,
        personal_relevance_result=None,
        time_sensitivity=time_sensitivity,
        is_watched=is_watched,
        computed_at=NOW,
    )


def _candidate(**overrides) -> NotificationCandidate:
    defaults = dict(
        candidate_id=uuid4(),
        event_id=EVENT_ID,
        user_id="user-a",
        entity_id="NVDA",
        ticker="NVDA",
        signal_family="earnings_signal",
        now=NOW,
        source_captured_at=NOW,
        is_watched=False,
        watch_route="none",
        communication_mode="analysis",
        personal_relevance=0.3,
        connection_strength=0.0,
        visibility="feed",
        interruption="digest",
        in_cooldown=False,
        domain_fatigued=False,
        thesis_revision=1,
        is_notification_worthy=True,
        change_type="confidence_increased",
        knowledge=None,
        confidence_score=0.6,
        classification="inference",
        provider_degraded=False,
        freshness_state="FRESH",
        market_evidence=None,
        earned_notification_inputs=_inputs(),
    )
    defaults.update(overrides)
    return build_notification_candidate(**defaults)  # type: ignore[arg-type]


# --- build_notification_candidate ------------------------------------------


def test_candidate_thesis_id_defaults_to_entity_id():
    candidate = _candidate(entity_id="AAPL")
    assert candidate.thesis_id == "AAPL"


def test_candidate_captures_watch_and_revision_snapshots():
    knowledge = UserOpportunityKnowledge(
        user_id="user-a",
        entity_id="NVDA",
        last_seen_revision=1,
        last_notified_revision=1,
        last_notified_at=NOW,
        last_notified_change_type="confidence_increased",
        updated_at=NOW,
    )
    candidate = _candidate(
        is_watched=True,
        watch_route="personal",
        knowledge=knowledge,
        thesis_revision=2,
    )
    assert candidate.watch.is_watched is True
    assert candidate.watch.watch_route == "personal"
    assert candidate.revision.thesis_revision == 2
    assert candidate.revision.last_notified_revision == 1
    assert candidate.revision.last_notified_at == NOW


def test_candidate_embeds_earned_notification_inputs_wholesale():
    inputs = _inputs(evidence_credibility=0.9, time_sensitivity=0.1, is_watched=True)
    candidate = _candidate(earned_notification_inputs=inputs)
    assert candidate.earned_notification_inputs.evidence_credibility == 0.9
    assert candidate.earned_notification_inputs.time_sensitivity == 0.1


# --- determine_ledger_outcome ------------------------------------------------


def test_policy_suppressed_when_not_permitted():
    outcome, reason = determine_ledger_outcome(
        policy_permitted=False,
        communication_mode="suppressed",
        interruption="none",
        in_cooldown=False,
        domain_fatigued=False,
        material_delta_decision=None,
    )
    assert (outcome, reason) == ("SUPPRESS", "policy_suppressed")


def test_view_cooldown_active_suppression():
    outcome, reason = determine_ledger_outcome(
        policy_permitted=True,
        communication_mode="analysis",
        interruption="none",
        in_cooldown=True,
        domain_fatigued=False,
        material_delta_decision=None,
    )
    assert (outcome, reason) == ("SUPPRESS", "view_cooldown_active")


def test_interruption_budget_exhausted_suppression():
    outcome, reason = determine_ledger_outcome(
        policy_permitted=True,
        communication_mode="analysis",
        interruption="none",
        in_cooldown=False,
        domain_fatigued=True,
        material_delta_decision=None,
    )
    assert (outcome, reason) == ("SUPPRESS", "interruption_budget_exhausted")


def test_insufficient_personal_relevance_when_not_alert():
    outcome, reason = determine_ledger_outcome(
        policy_permitted=True,
        communication_mode="analysis",
        interruption="digest",
        in_cooldown=False,
        domain_fatigued=False,
        material_delta_decision=None,
    )
    assert (outcome, reason) == (
        "SUPPRESS",
        "insufficient_personal_relevance_or_urgency",
    )


def test_send_reuses_decide_notification_verdict_when_alert():
    decision = NotificationDecision(
        entity_id="NVDA",
        user_id="user-a",
        should_notify=True,
        reason="new_material_revision",
        evaluated_at=NOW,
    )
    outcome, reason = determine_ledger_outcome(
        policy_permitted=True,
        communication_mode="alert",
        interruption="alert",
        in_cooldown=False,
        domain_fatigued=False,
        material_delta_decision=decision,
    )
    assert (outcome, reason) == ("SEND", "new_material_revision")


def test_material_delta_suppression_reasons_pass_through_unchanged():
    for reason_value in (
        "same_revision_suppressed",
        "cooldown_suppressed",
        "provider_degraded_suppressed",
        "no_material_delta",
    ):
        decision = NotificationDecision(
            entity_id="NVDA",
            user_id="user-a",
            should_notify=False,
            reason=reason_value,
            evaluated_at=NOW,
        )
        outcome, reason = determine_ledger_outcome(
            policy_permitted=True,
            communication_mode="alert",
            interruption="alert",
            in_cooldown=False,
            domain_fatigued=False,
            material_delta_decision=decision,
        )
        assert (outcome, reason) == ("SUPPRESS", reason_value)


def test_alert_without_material_delta_decision_raises():
    """Production always calls decide_notification() once interruption ==
    'alert' -- a caller reaching this function without that verdict is a
    real wiring bug, not a state this function should silently paper over.
    """
    import pytest

    with pytest.raises(ValueError):
        determine_ledger_outcome(
            policy_permitted=True,
            communication_mode="alert",
            interruption="alert",
            in_cooldown=False,
            domain_fatigued=False,
            material_delta_decision=None,
        )


# --- evaluate_shadow ----------------------------------------------------------


def test_shadow_material_delta_not_evaluated_when_none():
    shadow = evaluate_shadow(
        is_notification_worthy=None,
        watch_route="none",
        domain_fatigued=False,
        in_cooldown=False,
        earned_notification_inputs=_inputs(),
    )
    assert shadow.material_delta.state == "NOT_EVALUATED"


def test_shadow_personal_relevance_mirrors_watch_route():
    favorable = evaluate_shadow(
        is_notification_worthy=True,
        watch_route="personal",
        domain_fatigued=False,
        in_cooldown=False,
        earned_notification_inputs=_inputs(),
    )
    unfavorable = evaluate_shadow(
        is_notification_worthy=True,
        watch_route="none",
        domain_fatigued=False,
        in_cooldown=False,
        earned_notification_inputs=_inputs(),
    )
    assert favorable.personal_relevance.state == "FAVORABLE"
    assert unfavorable.personal_relevance.state == "UNFAVORABLE"


def test_shadow_interruption_budget_unfavorable_on_either_veto():
    fatigued = evaluate_shadow(
        is_notification_worthy=True,
        watch_route="personal",
        domain_fatigued=True,
        in_cooldown=False,
        earned_notification_inputs=_inputs(),
    )
    cooling = evaluate_shadow(
        is_notification_worthy=True,
        watch_route="personal",
        domain_fatigued=False,
        in_cooldown=True,
        earned_notification_inputs=_inputs(),
    )
    assert fatigued.interruption_budget.state == "UNFAVORABLE"
    assert cooling.interruption_budget.state == "UNFAVORABLE"


def test_shadow_credible_evidence_uses_existing_exceptional_confidence_floor():
    just_below = evaluate_shadow(
        is_notification_worthy=True,
        watch_route="personal",
        domain_fatigued=False,
        in_cooldown=False,
        earned_notification_inputs=_inputs(
            evidence_credibility=EXCEPTIONAL_CONFIDENCE_FLOOR - 0.01
        ),
    )
    at_floor = evaluate_shadow(
        is_notification_worthy=True,
        watch_route="personal",
        domain_fatigued=False,
        in_cooldown=False,
        earned_notification_inputs=_inputs(
            evidence_credibility=EXCEPTIONAL_CONFIDENCE_FLOOR
        ),
    )
    assert just_below.credible_evidence.state == "UNFAVORABLE"
    assert at_floor.credible_evidence.state == "FAVORABLE"


def test_shadow_time_sensitivity_uses_existing_personal_inferred_urgency_floor():
    just_below = evaluate_shadow(
        is_notification_worthy=True,
        watch_route="personal",
        domain_fatigued=False,
        in_cooldown=False,
        earned_notification_inputs=_inputs(
            time_sensitivity=PERSONAL_INFERRED_URGENCY_FLOOR - 0.01
        ),
    )
    at_floor = evaluate_shadow(
        is_notification_worthy=True,
        watch_route="personal",
        domain_fatigued=False,
        in_cooldown=False,
        earned_notification_inputs=_inputs(
            time_sensitivity=PERSONAL_INFERRED_URGENCY_FLOOR
        ),
    )
    assert just_below.time_sensitivity.state == "UNFAVORABLE"
    assert at_floor.time_sensitivity.state == "FAVORABLE"


def test_shadow_would_earn_interruption_favorable_only_when_all_five_favorable():
    shadow = evaluate_shadow(
        is_notification_worthy=True,
        watch_route="personal",
        domain_fatigued=False,
        in_cooldown=False,
        earned_notification_inputs=_inputs(
            evidence_credibility=EXCEPTIONAL_CONFIDENCE_FLOOR,
            time_sensitivity=PERSONAL_INFERRED_URGENCY_FLOOR,
        ),
    )
    assert shadow.would_earn_interruption == "FAVORABLE"


def test_shadow_would_earn_interruption_unfavorable_beats_not_evaluated():
    """Any UNFAVORABLE dimension makes the whole evaluation UNFAVORABLE even
    when another dimension (material_delta here) could not be evaluated --
    never collapsed into a fabricated FAVORABLE/NOT_EVALUATED."""
    shadow = evaluate_shadow(
        is_notification_worthy=None,  # NOT_EVALUATED
        watch_route="none",  # UNFAVORABLE
        domain_fatigued=False,
        in_cooldown=False,
        earned_notification_inputs=_inputs(
            evidence_credibility=EXCEPTIONAL_CONFIDENCE_FLOOR,
            time_sensitivity=PERSONAL_INFERRED_URGENCY_FLOOR,
        ),
    )
    assert shadow.would_earn_interruption == "UNFAVORABLE"


def test_shadow_would_earn_interruption_not_evaluated_when_no_unfavorable_present():
    shadow = evaluate_shadow(
        is_notification_worthy=None,  # NOT_EVALUATED
        watch_route="personal",  # FAVORABLE
        domain_fatigued=False,
        in_cooldown=False,
        earned_notification_inputs=_inputs(
            evidence_credibility=EXCEPTIONAL_CONFIDENCE_FLOOR,
            time_sensitivity=PERSONAL_INFERRED_URGENCY_FLOOR,
        ),
    )
    assert shadow.would_earn_interruption == "NOT_EVALUATED"


# --- build_ledger_decision ----------------------------------------------------


def test_build_ledger_decision_assembles_outcome_and_shadow():
    candidate = _candidate(
        watch_route="personal",
        communication_mode="alert",
        interruption="alert",
    )
    decision = NotificationDecision(
        entity_id="NVDA",
        user_id="user-a",
        should_notify=True,
        reason="new_material_revision",
        evaluated_at=NOW,
    )
    ledger_decision = build_ledger_decision(
        decision_id=uuid4(),
        candidate=candidate,
        policy_permitted=True,
        now=NOW,
        material_delta_decision=decision,
    )
    assert ledger_decision.outcome == "SEND"
    assert ledger_decision.reason == "new_material_revision"
    assert ledger_decision.candidate_id == candidate.candidate_id
    assert ledger_decision.user_id == "user-a"
    assert ledger_decision.shadow.personal_relevance.state == "FAVORABLE"


def test_build_ledger_decision_never_lets_shadow_override_real_outcome():
    """Real production has no evidence-credibility gate at all today, so a
    real SEND can happen even when the shadow evaluation's own
    credible_evidence dimension is UNFAVORABLE (low EvidenceTrust.
    trust_score) -- a genuine divergence between the two, proving the
    shadow evaluation is captured for comparison only and never applied to
    `outcome`."""
    candidate = _candidate(
        watch_route="personal",
        communication_mode="alert",
        interruption="alert",
        earned_notification_inputs=_inputs(
            evidence_credibility=0.1,  # far below the shadow's own floor
            time_sensitivity=PERSONAL_INFERRED_URGENCY_FLOOR,
        ),
    )
    decision = NotificationDecision(
        entity_id="NVDA",
        user_id="user-a",
        should_notify=True,
        reason="new_material_revision",
        evaluated_at=NOW,
    )
    ledger_decision = build_ledger_decision(
        decision_id=uuid4(),
        candidate=candidate,
        policy_permitted=True,
        now=NOW,
        material_delta_decision=decision,
    )
    assert ledger_decision.outcome == "SEND"
    assert ledger_decision.shadow.credible_evidence.state == "UNFAVORABLE"
    assert ledger_decision.shadow.would_earn_interruption == "UNFAVORABLE"
