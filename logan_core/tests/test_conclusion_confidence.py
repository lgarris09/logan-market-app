"""Layer 9 direct unit tests. Includes the ADR-015 regression added in V3.1.4
BATCH-1 Stage 1: Mental Model must be pass-through/data-collection only and must
never influence ConclusionConfidence, Opportunity ranking, or the recommend/
suppress outcome.
"""

from datetime import datetime, timezone
from uuid import uuid4

from logan_core.conclusion_confidence import ConclusionConfidenceEngine
from logan_core.contracts import CommunitySignal, EvidenceTrust, MentalModel, ReasoningResult
from logan_core.opportunity import OpportunityEngine


def _trust(event_id, trust_score=0.8, contradiction_flag=False, now=None):
    now = now or datetime.now(timezone.utc)
    return EvidenceTrust(
        event_id=event_id,
        source_score=0.8,
        corroboration=2,
        recency_score=0.9,
        contradiction_flag=contradiction_flag,
        manipulation_risk="low",
        completeness=1.0,
        trust_score=trust_score,
        evaluated_at=now,
    )


def _reasoning(now=None):
    now = now or datetime.now(timezone.utc)
    return ReasoningResult(
        event_id=uuid4(),
        significance="Test event",
        personal_relevance_narrative="Directly relevant.",
        connected_entities=["NVDA"],
        stance="new",
        actionability="actionable",
        explanation="Test explanation.",
        reasoned_at=now,
    )


def _mental_model(confidence, now=None):
    now = now or datetime.now(timezone.utc)
    return MentalModel(
        model_id=uuid4(),
        domain="stocks",
        hypothesis="Test hypothesis",
        confidence=confidence,
        trend="new",
        created_at=now,
        last_updated=now,
    )


def _community(event_id, now=None):
    now = now or datetime.now(timezone.utc)
    return CommunitySignal(
        event_id=event_id,
        engagement_volume=50,
        engagement_velocity=10.0,
        unique_users=30,
        saves_shares=5,
        questions=2,
        lifecycle_state="emerging",
        coordinated_risk=0.0,
        bot_risk=0.0,
        momentum_score=0.5,
        measured_at=now,
    )


def test_confidence_score_derives_from_trust_only():
    engine = ConclusionConfidenceEngine()
    trust = _trust(uuid4())
    reasoning = _reasoning()
    confidence = engine.evaluate(reasoning, trust, mental_model=None)
    assert confidence.confidence_score == trust.trust_score


def test_decision_trace_populated():
    engine = ConclusionConfidenceEngine()
    trust = _trust(uuid4())
    reasoning = _reasoning()
    confidence = engine.evaluate(reasoning, trust, mental_model=None)
    assert len(confidence.decision_trace) == 1
    assert "classification" in confidence.decision_trace[0].rule


def test_mental_model_confidence_has_zero_effect_on_confidence_score():
    engine = ConclusionConfidenceEngine()
    reasoning = _reasoning()
    trust = _trust(reasoning.event_id)

    low = engine.evaluate(reasoning, trust, mental_model=_mental_model(0.02))
    high = engine.evaluate(reasoning, trust, mental_model=_mental_model(0.99))
    none = engine.evaluate(reasoning, trust, mental_model=None)

    assert low.confidence_score == high.confidence_score == none.confidence_score
    assert low.classification == high.classification == none.classification


def test_mental_model_confidence_has_zero_effect_on_opportunity_outcome():
    """End-to-end: two runs differing only in MentalModel.confidence must produce
    an identical AttentionRecommendation (ranking and recommend/suppress alike).
    """
    confidence_engine = ConclusionConfidenceEngine()
    opportunity_engine = OpportunityEngine()
    reasoning = _reasoning()
    trust = _trust(reasoning.event_id)
    community = _community(reasoning.event_id)

    confidence_low = confidence_engine.evaluate(reasoning, trust, mental_model=_mental_model(0.0))
    confidence_high = confidence_engine.evaluate(reasoning, trust, mental_model=_mental_model(1.0))

    rec_low = opportunity_engine.evaluate(reasoning, confidence_low, community)
    rec_high = opportunity_engine.evaluate(reasoning, confidence_high, community)

    assert rec_low.recommend == rec_high.recommend
    assert rec_low.internal_rank_score == rec_high.internal_rank_score
    assert rec_low.dimensions.model_dump() == rec_high.dimensions.model_dump()
