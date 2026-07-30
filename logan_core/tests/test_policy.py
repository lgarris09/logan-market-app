from datetime import datetime, timezone
from uuid import uuid4

from logan_core.contracts import AttentionRecommendation, CommunitySignal, Dimensions
from logan_core.policy import ANALYSIS_DISCLAIMER, GAMBLING_DISCLAIMER, PolicyEngine


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
        priority_score=0.6,
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
