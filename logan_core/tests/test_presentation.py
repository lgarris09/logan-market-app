"""Layer 13 direct unit tests (V3.1.4 BATCH-2 -- previously uncovered)."""

from datetime import datetime, timezone
from uuid import uuid4

from logan_core.contracts import (
    ConclusionConfidence,
    PolicyResult,
    PrioritizedItem,
    ReasoningResult,
)
from logan_core.presentation import PresentationEngine

NOW = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)


def _reasoning(event_id):
    return ReasoningResult(
        event_id=event_id,
        significance="Tesla announces AI partnership",
        personal_relevance_narrative="Directly relevant to your NVDA holding.",
        connected_entities=["NVDA"],
        stance="new",
        actionability="actionable",
        explanation="Tesla announces AI partnership. Directly relevant.",
        reasoned_at=NOW,
    )


def _confidence(event_id, score=0.8):
    return ConclusionConfidence(
        event_id=event_id,
        confidence_score=score,
        classification="inference",
        evaluated_at=NOW,
    )


def _policy_result(event_id):
    return PolicyResult(
        event_id=event_id,
        permitted=True,
        communication_mode="analysis",
        required_disclaimers=["Logan provides analysis, not advice."],
        policy_rules_applied=["advice_boundary_v1"],
        evaluated_at=NOW,
    )


def _prioritized(event_id, visibility="primary", interruption="digest"):
    return PrioritizedItem(
        event_id=event_id,
        visibility=visibility,
        interruption=interruption,
        rank=1,
        changed_since_view=True,
        is_new_for_user=True,
        prioritized_at=NOW,
    )


def test_alert_interruption_produces_alert_surface():
    event_id = uuid4()
    item = _prioritized(event_id, interruption="alert")
    delivered = PresentationEngine().deliver(
        item, _reasoning(event_id), _confidence(event_id), _policy_result(event_id)
    )
    assert delivered.surface == "alert"


def test_primary_visibility_with_no_interruption_produces_wheel_surface():
    event_id = uuid4()
    item = _prioritized(event_id, visibility="primary", interruption="none")
    delivered = PresentationEngine().deliver(
        item, _reasoning(event_id), _confidence(event_id), _policy_result(event_id)
    )
    assert delivered.surface == "wheel"


def test_disclaimers_carried_verbatim_from_policy_result():
    event_id = uuid4()
    item = _prioritized(event_id)
    policy_result = _policy_result(event_id)
    delivered = PresentationEngine().deliver(
        item, _reasoning(event_id), _confidence(event_id), policy_result
    )
    assert delivered.required_disclaimers == policy_result.required_disclaimers


def test_headline_truncated_to_120_chars():
    event_id = uuid4()
    long_significance = "X" * 300
    reasoning = _reasoning(event_id).model_copy(
        update={"significance": long_significance}
    )
    item = _prioritized(event_id)
    delivered = PresentationEngine().deliver(
        item, reasoning, _confidence(event_id), _policy_result(event_id)
    )
    assert len(delivered.headline) <= 120


def test_decision_trace_populated():
    event_id = uuid4()
    item = _prioritized(event_id)
    delivered = PresentationEngine().deliver(
        item, _reasoning(event_id), _confidence(event_id), _policy_result(event_id)
    )
    assert len(delivered.decision_trace) == 1
    assert "surface=" in delivered.decision_trace[0].rule


# --- V2.3B Phase 2 Block 5: personal_relevance_result passthrough ----------


def test_personal_relevance_result_defaults_to_none():
    event_id = uuid4()
    item = _prioritized(event_id)
    delivered = PresentationEngine().deliver(
        item, _reasoning(event_id), _confidence(event_id), _policy_result(event_id)
    )
    assert delivered.personal_relevance_result is None


def test_personal_relevance_result_is_carried_through_verbatim():
    from logan_core.contracts import PersonalRelevanceResult

    event_id = uuid4()
    item = _prioritized(event_id)
    relevance = PersonalRelevanceResult(
        value=0.6,
        state="high",
        basis="watch",
        is_watched=True,
        strongest_signals=["You're actively watching this."],
        explicit=True,
        explanation="You're actively watching this.",
    )
    delivered = PresentationEngine().deliver(
        item,
        _reasoning(event_id),
        _confidence(event_id),
        _policy_result(event_id),
        personal_relevance_result=relevance,
    )
    assert delivered.personal_relevance_result == relevance
