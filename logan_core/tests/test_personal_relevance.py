"""V2.3B Phase 2 (Learning-Driven STRATUS) -- Personal Relevance V2.
compute_personal_relevance() (logan_core/opportunity/personal_relevance.py)
and its integration into OpportunityEngine.evaluate()."""

from datetime import datetime, timezone
from uuid import uuid4

from logan_core.contracts import CommunitySignal, ConclusionConfidence, ReasoningResult
from logan_core.opportunity import OpportunityEngine
from logan_core.opportunity.personal_relevance import (
    EXPLICIT_RELEVANCE,
    WATCH_RELEVANCE,
    compute_personal_relevance,
)

# --- compute_personal_relevance(): pure unit tests -------------------------


def test_watch_wins_over_no_connection():
    result = compute_personal_relevance(
        connected_entities_explicit=[],
        connected_entities_inferred=[],
        inferred_relevance_strength=0.0,
        inferred_evidence_count=0,
        is_watched=True,
        actionability_floor=0.2,
    )
    assert result.basis == "watch"
    assert result.is_watched is True
    assert result.state == "high"
    assert result.value == WATCH_RELEVANCE
    assert "watching" in result.explanation.lower()


def test_watch_and_explicit_both_present_watch_still_wins_the_basis():
    result = compute_personal_relevance(
        connected_entities_explicit=["NVDA"],
        connected_entities_inferred=[],
        inferred_relevance_strength=0.0,
        inferred_evidence_count=0,
        is_watched=True,
        actionability_floor=0.2,
    )
    assert result.basis == "watch"
    assert any("declared interest" in s.lower() for s in result.strongest_signals)


def test_watch_value_never_exceeds_explicit_relevance():
    """2026-08-30 finding: PolicyEngine's ADR-049 notification-eligibility
    gate keys directly off personal_relevance at the same 0.6 floor explicit
    connections already reach -- Watch must never introduce a *new*, higher
    ceiling than explicit already provides (see
    test_notification_hygiene.py's test_watch_alone_does_not_force_a_
    notification, which enforces this at the policy layer)."""
    assert WATCH_RELEVANCE == EXPLICIT_RELEVANCE


def test_explicit_without_watch():
    result = compute_personal_relevance(
        connected_entities_explicit=["NVDA"],
        connected_entities_inferred=[],
        inferred_relevance_strength=0.0,
        inferred_evidence_count=0,
        is_watched=False,
        actionability_floor=0.2,
    )
    assert result.basis == "explicit"
    assert result.value == EXPLICIT_RELEVANCE
    assert result.state == "high"
    assert any("not currently watching" in s.lower() for s in result.not_contributing)


def test_inferred_with_high_evidence_count_cites_repeated_return():
    result = compute_personal_relevance(
        connected_entities_explicit=[],
        connected_entities_inferred=["NVDA"],
        inferred_relevance_strength=0.85,
        inferred_evidence_count=4,
        is_watched=False,
        actionability_floor=0.2,
    )
    assert result.basis == "inferred"
    assert result.evidence_count == 4
    assert "4 times" in result.explanation


def test_inferred_with_thin_evidence_does_not_overclaim():
    result = compute_personal_relevance(
        connected_entities_explicit=[],
        connected_entities_inferred=["NVDA"],
        inferred_relevance_strength=0.75,
        inferred_evidence_count=2,
        is_watched=False,
        actionability_floor=0.2,
    )
    assert "early repeated interest" in result.explanation.lower()
    assert "4 times" not in result.explanation


def test_inferred_relevance_stays_bounded_below_explicit():
    result = compute_personal_relevance(
        connected_entities_explicit=[],
        connected_entities_inferred=["NVDA"],
        inferred_relevance_strength=1.0,
        inferred_evidence_count=10,
        is_watched=False,
        actionability_floor=0.2,
    )
    assert result.value < EXPLICIT_RELEVANCE


def test_no_connection_is_honestly_unknown_regardless_of_the_numeric_floor():
    result = compute_personal_relevance(
        connected_entities_explicit=[],
        connected_entities_inferred=[],
        inferred_relevance_strength=0.0,
        inferred_evidence_count=0,
        is_watched=False,
        actionability_floor=0.5,  # the "informational, nothing connected" floor
    )
    assert result.basis == "none"
    assert result.state == "unknown"
    assert result.value == 0.5  # numeric floor preserved for Dimensions/ranking
    assert "limited evidence" in result.explanation.lower()
    assert result.strongest_signals == []


def test_suppressed_entity_presents_as_none_not_a_special_case():
    """A corrected/suppressed inferred interest is simply absent from
    connected_entities_inferred by the time this function ever sees it (see
    _apply_corrections, user_model/model.py) -- this function needs no
    correction-specific branch at all, proven here by passing empty
    connections exactly as any other "nothing learned yet" case would."""
    result = compute_personal_relevance(
        connected_entities_explicit=[],
        connected_entities_inferred=[],
        inferred_relevance_strength=0.0,
        inferred_evidence_count=0,
        is_watched=False,
        actionability_floor=0.2,
    )
    assert result.basis == "none"


# --- OpportunityEngine integration -----------------------------------------


def _reasoning(**overrides) -> ReasoningResult:
    now = datetime.now(timezone.utc)
    defaults = dict(
        event_id=uuid4(),
        significance="Test event",
        personal_relevance_narrative="Test narrative.",
        connected_entities=[],
        connected_entities_explicit=[],
        connected_entities_inferred=[],
        stance="new",
        actionability="informational",
        explanation="Test explanation.",
        reasoned_at=now,
    )
    defaults.update(overrides)
    return ReasoningResult(**defaults)


def _confidence(event_id, score=0.5) -> ConclusionConfidence:
    return ConclusionConfidence(
        event_id=event_id,
        confidence_score=score,
        classification="inference",
        evaluated_at=datetime.now(timezone.utc),
    )


def _community(event_id) -> CommunitySignal:
    return CommunitySignal(
        event_id=event_id,
        engagement_volume=10,
        engagement_velocity=1.0,
        unique_users=5,
        saves_shares=0,
        questions=0,
        lifecycle_state="emerging",
        coordinated_risk=0.0,
        bot_risk=0.0,
        momentum_score=0.1,
        measured_at=datetime.now(timezone.utc),
    )


def test_recommendation_carries_a_populated_personal_relevance_result():
    reasoning = _reasoning(is_watched=True)
    confidence = _confidence(reasoning.event_id)
    community = _community(reasoning.event_id)

    recommendation = OpportunityEngine().evaluate(reasoning, confidence, community)
    assert recommendation.personal_relevance_result is not None
    assert recommendation.personal_relevance_result.basis == "watch"
    assert recommendation.dimensions.personal_relevance == WATCH_RELEVANCE


def test_actionable_holding_case_unchanged_by_phase_2():
    """The pre-existing actionable/holds_directly short-circuit (ceiling
    personal_relevance) must remain exactly as before -- Phase 2 only
    changes the non-actionable explicit/watch/inferred/none paths."""
    reasoning = _reasoning(actionability="actionable")
    confidence = _confidence(reasoning.event_id)
    community = _community(reasoning.event_id)

    recommendation = OpportunityEngine().evaluate(reasoning, confidence, community)
    assert recommendation.dimensions.personal_relevance == 1.0
    assert recommendation.personal_relevance_result is not None
    assert recommendation.personal_relevance_result.state == "high"
