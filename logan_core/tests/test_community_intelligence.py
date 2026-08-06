"""Layer 4b direct unit tests (V3.1.4 BATCH-2 -- previously uncovered)."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from logan_core.community_intelligence import CommunityIntelligenceEngine, EngagementSample
from logan_core.contracts import EnrichedEvent, Entity

NOW = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)


def _event():
    entity = Entity(entity_id="TSLA", entity_type="ticker", display_name="Tesla", domain="stocks")
    return EnrichedEvent(
        event_id=uuid4(),
        signal_ids=[uuid4()],
        domain="stocks",
        is_new=True,
        entities=[entity],
        summary="Tesla test event",
        occurred_at=NOW,
        enriched_at=NOW,
    )


def test_no_samples_returns_dormant_zero_signal():
    engine = CommunityIntelligenceEngine()
    signal = engine.measure(_event(), samples=[], now=NOW)
    assert signal.lifecycle_state == "dormant"
    assert signal.engagement_volume == 0
    assert signal.momentum_score == 0.0
    assert signal.decision_trace


def test_rising_velocity_is_emerging():
    engine = CommunityIntelligenceEngine()
    samples = [
        EngagementSample(observed_at=NOW, volume_at_point=10, unique_users=8, saves_shares=1, questions=0),
        EngagementSample(
            observed_at=NOW + timedelta(hours=1), volume_at_point=40, unique_users=30, saves_shares=6, questions=3
        ),
    ]
    signal = engine.measure(_event(), samples, now=NOW)
    assert signal.lifecycle_state == "emerging"
    assert signal.engagement_velocity > 5
    assert signal.decision_trace


def test_falling_velocity_is_dormant():
    engine = CommunityIntelligenceEngine()
    samples = [
        EngagementSample(observed_at=NOW, volume_at_point=100, unique_users=50, saves_shares=10, questions=5),
        EngagementSample(
            observed_at=NOW + timedelta(hours=1), volume_at_point=10, unique_users=8, saves_shares=1, questions=0
        ),
    ]
    signal = engine.measure(_event(), samples, now=NOW)
    assert signal.lifecycle_state == "dormant"


def test_bot_risk_equals_coordinated_risk():
    """Documents current behavior (V3.1.4 gap review finding, not fixed this
    batch): bot_risk and coordinated_risk are derived from the same formula
    and are therefore always numerically identical. If this ever changes to
    two independently-derived signals, this test should be the first to fail
    and prompt an intentional review, not a silent drift.
    """
    engine = CommunityIntelligenceEngine()
    samples = [
        EngagementSample(observed_at=NOW, volume_at_point=200, unique_users=5, saves_shares=1, questions=0),
        EngagementSample(
            observed_at=NOW + timedelta(hours=1), volume_at_point=210, unique_users=5, saves_shares=1, questions=0
        ),
    ]
    signal = engine.measure(_event(), samples, now=NOW)
    assert signal.bot_risk == signal.coordinated_risk


def test_momentum_score_bounded_zero_to_one():
    engine = CommunityIntelligenceEngine()
    samples = [
        EngagementSample(observed_at=NOW, volume_at_point=1000, unique_users=900, saves_shares=500, questions=50),
        EngagementSample(
            observed_at=NOW + timedelta(hours=1),
            volume_at_point=5000,
            unique_users=4000,
            saves_shares=2000,
            questions=200,
        ),
    ]
    signal = engine.measure(_event(), samples, now=NOW)
    assert 0.0 <= signal.momentum_score <= 1.0
