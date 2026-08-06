from datetime import datetime, timezone
from uuid import uuid4

from logan_core.contracts import CommunitySignal, ConclusionConfidence, ReasoningResult
from logan_core.opportunity import RECOMMEND_THRESHOLD, OpportunityEngine


def _reasoning(stance="new", actionability="actionable", connected=None, now=None):
    now = now or datetime.now(timezone.utc)
    return ReasoningResult(
        event_id=uuid4(),
        significance="Test event",
        personal_relevance_narrative="Directly relevant.",
        connected_entities=connected or ["NVDA"],
        stance=stance,
        actionability=actionability,
        explanation="Test explanation.",
        reasoned_at=now,
    )


def _confidence(event_id, score=0.8, classification="inference", now=None):
    now = now or datetime.now(timezone.utc)
    return ConclusionConfidence(
        event_id=event_id,
        confidence_score=score,
        classification=classification,
        evaluated_at=now,
    )


def _community(event_id, momentum=0.6, lifecycle="emerging", bot_risk=0.0, now=None):
    now = now or datetime.now(timezone.utc)
    return CommunitySignal(
        event_id=event_id,
        engagement_volume=50,
        engagement_velocity=10.0,
        unique_users=30,
        saves_shares=5,
        questions=2,
        lifecycle_state=lifecycle,
        coordinated_risk=bot_risk,
        bot_risk=bot_risk,
        momentum_score=momentum,
        measured_at=now,
    )


def test_high_relevance_high_confidence_recommends():
    reasoning = _reasoning()
    confidence = _confidence(reasoning.event_id, score=0.85)
    community = _community(reasoning.event_id, momentum=0.7, lifecycle="emerging")

    engine = OpportunityEngine()
    recommendation = engine.evaluate(reasoning, confidence, community)

    assert recommendation.recommend is True
    assert recommendation.internal_rank_score >= RECOMMEND_THRESHOLD
    assert len(recommendation.reasons) >= 1
    assert (
        len(recommendation.decision_trace) == 7
    )  # validate..recommend, one entry per step


def test_low_relevance_low_confidence_does_not_recommend():
    reasoning = _reasoning(actionability="ambiguous", connected=[], stance="confirms")
    confidence = _confidence(
        reasoning.event_id, score=0.1, classification="speculation"
    )
    community = _community(reasoning.event_id, momentum=0.05, lifecycle="dormant")

    engine = OpportunityEngine()
    recommendation = engine.evaluate(reasoning, confidence, community)

    assert recommendation.recommend is False
    assert recommendation.internal_rank_score < RECOMMEND_THRESHOLD


def test_internal_rank_score_never_exceeds_bounds():
    reasoning = _reasoning()
    confidence = _confidence(reasoning.event_id, score=1.0)
    community = _community(reasoning.event_id, momentum=1.0, lifecycle="emerging")

    engine = OpportunityEngine()
    recommendation = engine.evaluate(reasoning, confidence, community)
    assert 0.0 <= recommendation.internal_rank_score <= 1.0
    for value in recommendation.dimensions.model_dump().values():
        assert 0.0 <= value <= 1.0


def test_community_momentum_has_zero_effect_on_ranking():
    """ADR-034 / V3.1.4 BATCH-1 Stage 2 regression: different momentum_score
    values must produce an identical internal_rank_score (and identical dimensions
    other than community_momentum itself) when every other input is equal.
    """
    reasoning = _reasoning()
    confidence = _confidence(reasoning.event_id, score=0.7)

    engine = OpportunityEngine()
    low = engine.evaluate(
        reasoning, confidence, _community(reasoning.event_id, momentum=0.0)
    )
    high = engine.evaluate(
        reasoning, confidence, _community(reasoning.event_id, momentum=1.0)
    )

    assert low.internal_rank_score == high.internal_rank_score
    assert low.recommend == high.recommend
    low_dims = low.dimensions.model_dump()
    high_dims = high.dimensions.model_dump()
    assert low_dims["community_momentum"] == 0.0
    assert high_dims["community_momentum"] == 1.0
    for key in low_dims:
        if key == "community_momentum":
            continue
        assert (
            low_dims[key] == high_dims[key]
        ), f"dimension {key!r} was affected by momentum"


def test_speculation_classification_increases_risk_dimension():
    reasoning = _reasoning()
    confidence_normal = _confidence(
        reasoning.event_id, score=0.6, classification="inference"
    )
    confidence_speculative = _confidence(
        reasoning.event_id, score=0.6, classification="speculation"
    )
    community = _community(reasoning.event_id, bot_risk=0.3)

    engine = OpportunityEngine()
    normal = engine.evaluate(reasoning, confidence_normal, community)
    speculative = engine.evaluate(reasoning, confidence_speculative, community)

    assert speculative.dimensions.risk > normal.dimensions.risk
