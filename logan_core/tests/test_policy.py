from datetime import datetime, timezone
from uuid import uuid4

from logan_core.contracts import AttentionRecommendation, CommunitySignal, Dimensions
from logan_core.policy import (
    ANALYSIS_DISCLAIMER,
    BOT_RISK_SUPPRESSION_THRESHOLD,
    GAMBLING_DISCLAIMER,
    PolicyEngine,
)


def _dimensions(**overrides):
    base = dict(
        personal_relevance=0.7,
        global_importance=0.6,
        community_momentum=0.5,
        urgency=0.5,
        confidence=0.7,
        novelty=0.6,
        opportunity_magnitude=0.6,
        risk=0.1,
        actionability=0.7,
        connection_strength=0.5,
    )
    base.update(overrides)
    return Dimensions(**base)


def _recommendation(event_id, recommend=True, **dim_overrides):
    now = datetime.now(timezone.utc)
    return AttentionRecommendation(
        event_id=event_id,
        recommend=recommend,
        dimensions=_dimensions(**dim_overrides),
        internal_rank_score=0.6,
        reasons=["test"],
        recommended_at=now,
    )


def _community(event_id, bot_risk=0.0):
    now = datetime.now(timezone.utc)
    return CommunitySignal(
        event_id=event_id,
        engagement_volume=20,
        engagement_velocity=2.0,
        unique_users=15,
        saves_shares=2,
        questions=1,
        lifecycle_state="peak",
        coordinated_risk=bot_risk,
        bot_risk=bot_risk,
        momentum_score=0.4,
        measured_at=now,
    )


def test_sports_domain_gets_objectivity_language_constraints():
    event_id = uuid4()
    recommendation = _recommendation(event_id)
    community = _community(event_id)

    result = PolicyEngine().evaluate(recommendation, community, domain="sports")

    assert "objective_data_forward_only" in result.language_constraints
    assert "no_urgency_framing" in result.language_constraints
    assert GAMBLING_DISCLAIMER in result.required_disclaimers
    assert ANALYSIS_DISCLAIMER in result.required_disclaimers


def test_stocks_domain_does_not_get_gambling_disclaimer():
    event_id = uuid4()
    recommendation = _recommendation(event_id)
    community = _community(event_id)

    result = PolicyEngine().evaluate(recommendation, community, domain="stocks")

    assert "objective_data_forward_only" not in result.language_constraints
    assert GAMBLING_DISCLAIMER not in result.required_disclaimers
    assert ANALYSIS_DISCLAIMER in result.required_disclaimers


def test_high_bot_risk_suppresses_communication():
    event_id = uuid4()
    recommendation = _recommendation(event_id)
    community = _community(event_id, bot_risk=0.9)

    result = PolicyEngine().evaluate(recommendation, community, domain="social")

    assert result.permitted is False
    assert result.communication_mode == "suppressed"


def test_advice_boundary_language_constraint_always_present():
    event_id = uuid4()
    recommendation = _recommendation(event_id)
    community = _community(event_id)

    for domain in ("stocks", "sports", "poly", "social", "news"):
        result = PolicyEngine().evaluate(recommendation, community, domain=domain)
        assert "no_directive_language" in result.language_constraints
        assert ANALYSIS_DISCLAIMER in result.required_disclaimers


def test_poly_domain_gets_objectivity_language_constraints():
    """ADR-013 applies equally to poly (prediction markets), not just sports --
    only sports had a dedicated assertion before V3.1.4 BATCH-2."""
    event_id = uuid4()
    recommendation = _recommendation(event_id)
    community = _community(event_id)

    result = PolicyEngine().evaluate(recommendation, community, domain="poly")

    assert "objective_data_forward_only" in result.language_constraints
    assert "no_urgency_framing" in result.language_constraints
    assert GAMBLING_DISCLAIMER in result.required_disclaimers


def test_bot_risk_just_below_threshold_does_not_suppress():
    event_id = uuid4()
    recommendation = _recommendation(event_id)
    community = _community(event_id, bot_risk=BOT_RISK_SUPPRESSION_THRESHOLD - 0.01)

    result = PolicyEngine().evaluate(recommendation, community, domain="social")

    assert result.permitted is True
    assert result.communication_mode != "suppressed"


def test_bot_risk_exactly_at_threshold_suppresses():
    event_id = uuid4()
    recommendation = _recommendation(event_id)
    community = _community(event_id, bot_risk=BOT_RISK_SUPPRESSION_THRESHOLD)

    result = PolicyEngine().evaluate(recommendation, community, domain="social")

    assert result.permitted is False
    assert result.communication_mode == "suppressed"


def test_bot_risk_above_threshold_suppresses():
    event_id = uuid4()
    recommendation = _recommendation(event_id)
    community = _community(
        event_id, bot_risk=min(BOT_RISK_SUPPRESSION_THRESHOLD + 0.1, 1.0)
    )

    result = PolicyEngine().evaluate(recommendation, community, domain="social")

    assert result.permitted is False
    assert result.communication_mode == "suppressed"


def test_bot_risk_suppression_applies_even_in_objective_only_domain():
    """Bot-risk suppression and the sports/poly objectivity rule are independent
    -- a suppressed result from an objective-only domain must still carry the
    domain's required disclaimers (they're appended before the suppression
    check runs), not silently drop them.
    """
    event_id = uuid4()
    recommendation = _recommendation(event_id)
    community = _community(event_id, bot_risk=0.95)

    result = PolicyEngine().evaluate(recommendation, community, domain="sports")

    assert result.permitted is False
    assert result.communication_mode == "suppressed"
    assert GAMBLING_DISCLAIMER in result.required_disclaimers


def test_decision_trace_populated_for_both_permitted_and_suppressed():
    event_id = uuid4()
    recommendation = _recommendation(event_id)

    permitted = PolicyEngine().evaluate(
        recommendation, _community(event_id, bot_risk=0.0), domain="stocks"
    )
    suppressed = PolicyEngine().evaluate(
        recommendation, _community(event_id, bot_risk=0.95), domain="stocks"
    )

    assert len(permitted.decision_trace) == 1
    assert len(suppressed.decision_trace) == 1
    assert "suppressed" in suppressed.decision_trace[0].rule
