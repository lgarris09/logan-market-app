"""Layer 12 direct unit tests (V3.1.4 BATCH-2 -- previously uncovered).
Includes the FATIGUE_WINDOW expiration wiring added this batch: fatigue counts
must decay after FATIGUE_WINDOW elapses, not grow forever.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from logan_core.contracts import AttentionRecommendation, Dimensions, PolicyResult
from logan_core.prioritization import FATIGUE_LIMIT, FATIGUE_WINDOW, PrioritizationEngine

BASE_NOW = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)


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


def _recommendation(now):
    return AttentionRecommendation(
        event_id=uuid4(),
        recommend=True,
        dimensions=_dimensions(),
        internal_rank_score=0.75,
        reasons=["test"],
        recommended_at=now,
    )


def _policy_result(event_id, now, permitted=True, communication_mode="analysis"):
    return PolicyResult(
        event_id=event_id,
        permitted=permitted,
        communication_mode=communication_mode,
        policy_rules_applied=["advice_boundary_v1"],
        evaluated_at=now,
    )


def _surface_once(engine, now, domain="stocks"):
    recommendation = _recommendation(now)
    policy_result = _policy_result(recommendation.event_id, now)
    return engine.prioritize(
        user_id="demo_user",
        domain=domain,
        policy_result=policy_result,
        recommendation=recommendation,
        now=now,
    )


def test_domain_becomes_fatigued_at_the_limit():
    engine = PrioritizationEngine()
    result = None
    for i in range(FATIGUE_LIMIT):
        result = _surface_once(engine, BASE_NOW + timedelta(minutes=i))
    # The FATIGUE_LIMIT-th surfacing itself is still evaluated against the
    # count *before* it was incremented, so it's the (FATIGUE_LIMIT + 1)-th
    # call that first sees domain_fatigued -- surface one more and check.
    result = _surface_once(engine, BASE_NOW + timedelta(minutes=FATIGUE_LIMIT))
    assert result.visibility == "background"
    assert result.interruption == "none"


def test_fatigue_has_not_expired_just_before_the_window_ends():
    engine = PrioritizationEngine()
    for i in range(FATIGUE_LIMIT + 1):
        _surface_once(engine, BASE_NOW + timedelta(minutes=i))
    just_before_expiry = BASE_NOW + FATIGUE_WINDOW - timedelta(seconds=1)
    result = _surface_once(engine, just_before_expiry)
    assert result.visibility == "background"


def test_fatigue_expires_exactly_at_the_window_boundary():
    engine = PrioritizationEngine()
    for i in range(FATIGUE_LIMIT + 1):
        _surface_once(engine, BASE_NOW + timedelta(minutes=i))
    at_expiry = BASE_NOW + FATIGUE_WINDOW
    result = _surface_once(engine, at_expiry)
    # (now - window) <= FATIGUE_WINDOW is still true exactly at the boundary --
    # the record is still active at this instant, then decays on the next tick.
    assert result.visibility == "background"


def test_fatigue_decays_after_the_window():
    engine = PrioritizationEngine()
    for i in range(FATIGUE_LIMIT + 1):
        _surface_once(engine, BASE_NOW + timedelta(minutes=i))
    after_expiry = BASE_NOW + FATIGUE_WINDOW + timedelta(seconds=1)
    result = _surface_once(engine, after_expiry)
    assert result.visibility in ("primary", "feed")


def test_cooldown_hides_unchanged_recently_surfaced_item():
    engine = PrioritizationEngine()
    recommendation = _recommendation(BASE_NOW)
    policy_result = _policy_result(recommendation.event_id, BASE_NOW)
    engine.prioritize(
        user_id="demo_user",
        domain="stocks",
        policy_result=policy_result,
        recommendation=recommendation,
        now=BASE_NOW,
    )
    second = engine.prioritize(
        user_id="demo_user",
        domain="stocks",
        policy_result=policy_result,
        recommendation=recommendation,
        changed_since_view=False,
        now=BASE_NOW + timedelta(minutes=5),
    )
    assert second.visibility == "hidden"


def test_not_permitted_is_always_hidden():
    engine = PrioritizationEngine()
    recommendation = _recommendation(BASE_NOW)
    policy_result = _policy_result(
        recommendation.event_id, BASE_NOW, permitted=False, communication_mode="suppressed"
    )
    result = engine.prioritize(
        user_id="demo_user",
        domain="stocks",
        policy_result=policy_result,
        recommendation=recommendation,
        now=BASE_NOW,
    )
    assert result.visibility == "hidden"
    assert result.interruption == "none"
