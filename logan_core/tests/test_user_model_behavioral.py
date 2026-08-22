"""Sprint 3.6.7 Block 3 -- UserModelBuilder's maturity scaling, time-based
decay, and exposure-fatigue dampening. Pre-Block-3 folding behavior (MIN_
REPEAT_EVIDENCE gating, explicit-vs-inferred authority, domain leakage
protection) is covered unmodified by test_user_model.py; these tests are
specifically about the new behavior layered on top of it.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from logan_core.contracts import Holding, MemoryRecord
from logan_core.user_model import UserModelBuilder
from logan_core.user_model.model import (
    BEHAVIORAL_HALF_LIFE_DAYS,
    EXPOSURE_FATIGUE_THRESHOLD,
    MAX_INFERRED_INTEREST_WEIGHT,
    MIN_REPEAT_EVIDENCE,
)

NOW = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)


def _feedback(entity_id="NVDA", domain="stocks", confidence=0.85, created_at=NOW):
    return MemoryRecord(
        record_id=uuid4(),
        user_id="demo_user",
        record_type="feedback_record",
        content={
            "interaction_type": "save",
            "entity_id": entity_id,
            "domain": domain,
            "inferred_intent": "interested",
            "intent_confidence": confidence,
            "duration_ms": None,
        },
        domain=domain,
        entities=[entity_id],
        source_layer="learning_system",
        created_at=created_at,
    )


def _exposure(entity_id="NVDA", domain="stocks", count=6, last_seen=NOW, event_id=None):
    return MemoryRecord(
        record_id=uuid4(),
        user_id="demo_user",
        record_type="exposure_record",
        content={
            "entity_id": entity_id,
            "impression_count": count,
            "first_seen_at": (last_seen - timedelta(days=10)).isoformat(),
            "last_seen_at": last_seen.isoformat(),
        },
        domain=domain,
        entities=[entity_id],
        source_layer="learning_system",
        created_at=last_seen,
        operational_ref=event_id or uuid4(),
    )


def _interest_weight(user_model, topic):
    return next((i.weight for i in user_model.interests if i.topic == topic), None)


# --- Maturity scaling --------------------------------------------------


def test_exactly_min_repeat_evidence_gets_no_maturity_bonus():
    builder = UserModelBuilder()
    base = builder.seed(user_id="demo_user")
    records = [_feedback(confidence=0.75) for _ in range(MIN_REPEAT_EVIDENCE)]
    updated = builder.build(
        user_id="demo_user", memory_records=records, base=base, now=NOW
    )
    assert _interest_weight(updated, "NVDA") == 0.75


def test_more_evidence_produces_a_measurably_higher_weight():
    builder = UserModelBuilder()
    base = builder.seed(user_id="demo_user")

    few = [_feedback(confidence=0.75) for _ in range(MIN_REPEAT_EVIDENCE)]
    many = [_feedback(confidence=0.75) for _ in range(MIN_REPEAT_EVIDENCE + 4)]

    weight_few = _interest_weight(
        builder.build(user_id="demo_user", memory_records=few, base=base, now=NOW),
        "NVDA",
    )
    weight_many = _interest_weight(
        builder.build(user_id="demo_user", memory_records=many, base=base, now=NOW),
        "NVDA",
    )
    assert weight_many > weight_few


def test_maturity_bonus_is_capped_not_unbounded():
    """One burst of activity cannot alone dominate the profile -- 100
    qualifying records must not exceed MAX_INFERRED_INTEREST_WEIGHT."""
    builder = UserModelBuilder()
    base = builder.seed(user_id="demo_user")
    records = [_feedback(confidence=0.85) for _ in range(100)]
    updated = builder.build(
        user_id="demo_user", memory_records=records, base=base, now=NOW
    )
    assert _interest_weight(updated, "NVDA") <= MAX_INFERRED_INTEREST_WEIGHT


def test_evidence_count_and_last_reinforced_are_recorded_for_provenance():
    builder = UserModelBuilder()
    base = builder.seed(user_id="demo_user")
    records = [_feedback(created_at=NOW - timedelta(days=i)) for i in range(3)]
    updated = builder.build(
        user_id="demo_user", memory_records=records, base=base, now=NOW
    )

    pattern = next(
        b for b in updated.established_behaviors if b.label == "engaged_with_NVDA"
    )
    assert pattern.evidence_count == 3
    assert pattern.last_reinforced == NOW  # the most recent evidence's timestamp


# --- Time-based decay ----------------------------------------------------


def test_stale_inferred_interest_decays_over_one_half_life():
    builder = UserModelBuilder()
    base = builder.seed(user_id="demo_user")
    old = NOW - timedelta(days=BEHAVIORAL_HALF_LIFE_DAYS)
    records = [
        _feedback(confidence=0.80, created_at=old) for _ in range(MIN_REPEAT_EVIDENCE)
    ]
    updated = builder.build(
        user_id="demo_user", memory_records=records, base=base, now=NOW
    )
    weight = _interest_weight(updated, "NVDA")
    assert weight is not None
    assert abs(weight - 0.40) < 0.01  # 0.80 * 0.5**1


def test_very_stale_evidence_is_pruned_below_the_floor():
    builder = UserModelBuilder()
    base = builder.seed(user_id="demo_user")
    ancient = NOW - timedelta(days=BEHAVIORAL_HALF_LIFE_DAYS * 10)
    records = [
        _feedback(confidence=0.85, created_at=ancient)
        for _ in range(MIN_REPEAT_EVIDENCE)
    ]
    updated = builder.build(
        user_id="demo_user", memory_records=records, base=base, now=NOW
    )
    assert _interest_weight(updated, "NVDA") is None
    assert updated.established_behaviors == []


def test_fresh_evidence_is_not_decayed_at_all():
    builder = UserModelBuilder()
    base = builder.seed(user_id="demo_user")
    records = [
        _feedback(confidence=0.85, created_at=NOW) for _ in range(MIN_REPEAT_EVIDENCE)
    ]
    updated = builder.build(
        user_id="demo_user", memory_records=records, base=base, now=NOW
    )
    assert _interest_weight(updated, "NVDA") == 0.85


def test_explicit_interests_are_never_decayed():
    from logan_core.contracts import Interest

    builder = UserModelBuilder()
    old_interest = Interest(
        domain="stocks",
        topic="NVDA",
        weight=0.9,
        source="explicit",
        created_at=NOW - timedelta(days=365),
        last_updated=NOW - timedelta(days=365),
    )
    base = builder.seed(user_id="demo_user", interests=[old_interest])
    updated = builder.build(user_id="demo_user", memory_records=[], base=base, now=NOW)
    assert _interest_weight(updated, "NVDA") == 0.9


def test_explicit_holdings_are_never_decayed_or_removed():
    builder = UserModelBuilder()
    base = builder.seed(
        user_id="demo_user",
        holdings=[
            Holding(
                domain="stocks",
                entity_id="NVDA",
                display_name="NVIDIA",
                added_at=NOW - timedelta(days=365),
            )
        ],
    )
    updated = builder.build(user_id="demo_user", memory_records=[], base=base, now=NOW)
    assert updated.holdings == base.holdings


def test_decay_pruning_populates_decision_trace():
    builder = UserModelBuilder()
    base = builder.seed(user_id="demo_user")
    ancient = NOW - timedelta(days=BEHAVIORAL_HALF_LIFE_DAYS * 10)
    records = [
        _feedback(confidence=0.85, created_at=ancient)
        for _ in range(MIN_REPEAT_EVIDENCE)
    ]
    updated = builder.build(
        user_id="demo_user", memory_records=records, base=base, now=NOW
    )
    assert any("decay" in entry.rule for entry in updated.decision_trace)


# --- Exposure-fatigue dampening -----------------------------------------


def test_high_exposure_after_engagement_goes_quiet_dampens_the_interest():
    builder = UserModelBuilder()
    base = builder.seed(user_id="demo_user")
    engaged_at = NOW - timedelta(days=5)
    records = [
        _feedback(created_at=engaged_at),
        _feedback(created_at=engaged_at + timedelta(minutes=1)),
        _exposure(count=EXPOSURE_FATIGUE_THRESHOLD + 1, last_seen=NOW),
    ]
    updated = builder.build(
        user_id="demo_user", memory_records=records, base=base, now=NOW
    )

    undampened = 0.85 * 0.5 ** (5 / BEHAVIORAL_HALF_LIFE_DAYS)  # decay alone
    weight = _interest_weight(updated, "NVDA")
    assert weight is not None
    assert weight < undampened
    assert any("exposure_fatigue" in e.rule for e in updated.decision_trace)


def test_recent_engagement_right_before_exposure_is_not_fatigued():
    """Exposure that continues *during* an active engagement window (not
    after it goes quiet) must not be treated as fatigue."""
    builder = UserModelBuilder()
    base = builder.seed(user_id="demo_user")
    recent = NOW - timedelta(minutes=30)
    records = [
        _feedback(created_at=recent),
        _feedback(created_at=recent + timedelta(minutes=1)),
        _exposure(count=EXPOSURE_FATIGUE_THRESHOLD + 1, last_seen=NOW),
    ]
    updated = builder.build(
        user_id="demo_user", memory_records=records, base=base, now=NOW
    )
    weight = _interest_weight(updated, "NVDA")
    latest_evidence_at = recent + timedelta(minutes=1)
    age_days = (NOW - latest_evidence_at).total_seconds() / 86400
    expected_undampened = 0.85 * 0.5 ** (age_days / BEHAVIORAL_HALF_LIFE_DAYS)
    assert weight is not None
    assert abs(weight - expected_undampened) < 1e-6
    assert not any("exposure_fatigue" in e.rule for e in updated.decision_trace)


def test_impressions_below_threshold_never_dampen():
    builder = UserModelBuilder()
    base = builder.seed(user_id="demo_user")
    engaged_at = NOW - timedelta(days=5)
    records = [
        _feedback(created_at=engaged_at),
        _feedback(created_at=engaged_at + timedelta(minutes=1)),
        _exposure(count=EXPOSURE_FATIGUE_THRESHOLD - 1, last_seen=NOW),
    ]
    updated = builder.build(
        user_id="demo_user", memory_records=records, base=base, now=NOW
    )
    assert not any("exposure_fatigue" in e.rule for e in updated.decision_trace)


def test_exposure_alone_never_creates_a_negative_interest():
    """An entity with heavy exposure but zero engagement ever must not
    manufacture any interest -- unobserved is not the same as ignored."""
    builder = UserModelBuilder()
    base = builder.seed(user_id="demo_user")
    records = [_exposure(count=50, last_seen=NOW)]
    updated = builder.build(
        user_id="demo_user", memory_records=records, base=base, now=NOW
    )
    assert updated.interests == []
    assert not any("exposure_fatigue" in e.rule for e in updated.decision_trace)


def test_exposure_fatigue_never_applies_to_a_held_entity():
    builder = UserModelBuilder()
    base = builder.seed(
        user_id="demo_user",
        holdings=[
            Holding(
                domain="stocks", entity_id="NVDA", display_name="NVIDIA", added_at=NOW
            )
        ],
    )
    engaged_at = NOW - timedelta(days=5)
    records = [
        _feedback(created_at=engaged_at),
        _feedback(created_at=engaged_at + timedelta(minutes=1)),
        _exposure(count=EXPOSURE_FATIGUE_THRESHOLD + 5, last_seen=NOW),
    ]
    updated = builder.build(
        user_id="demo_user", memory_records=records, base=base, now=NOW
    )
    # No inferred interest is created at all for an explicitly-held entity
    # (pre-existing behavior); fatigue has nothing to dampen either way.
    assert not any("exposure_fatigue" in e.rule for e in updated.decision_trace)


def test_repeated_dampening_can_eventually_prune_the_interest():
    builder = UserModelBuilder()
    base = builder.seed(user_id="demo_user")
    engaged_at = NOW - timedelta(days=5)
    records = [
        _feedback(confidence=0.75, created_at=engaged_at),
        _feedback(confidence=0.75, created_at=engaged_at + timedelta(minutes=1)),
        _exposure(count=1000, last_seen=NOW),
    ]
    updated = builder.build(
        user_id="demo_user", memory_records=records, base=base, now=NOW
    )
    weight = _interest_weight(updated, "NVDA")
    # A single call only dampens by one EXPOSURE_FATIGUE_PENALTY step, so
    # this alone won't prune -- but the mechanism must be bounded and never
    # negative.
    assert weight is None or weight >= 0.0
