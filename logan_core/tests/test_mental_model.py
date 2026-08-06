"""Layer 8 direct unit tests (V3.1.4 BATCH-2 -- previously uncovered)."""

from datetime import datetime, timezone
from uuid import uuid4

from logan_core.contracts import ReasoningResult
from logan_core.mental_model import MentalModelEngine

NOW = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)


def _reasoning(significance="Tesla: earnings signal", stance="new"):
    return ReasoningResult(
        event_id=uuid4(),
        significance=significance,
        personal_relevance_narrative="Relevant.",
        stance=stance,
        actionability="actionable",
        explanation="Test explanation.",
        reasoned_at=NOW,
    )


def test_new_hypothesis_created_for_new_key():
    engine = MentalModelEngine()
    reasoning, model = engine.process(_reasoning(stance="new"), domain="stocks")
    assert model.trend == "new"
    assert model.domain == "stocks"
    assert model.decision_trace


def test_confirms_strengthens_existing_hypothesis():
    engine = MentalModelEngine()
    engine.process(
        _reasoning(significance="Tesla: earnings signal", stance="new"), domain="stocks"
    )
    _, second = engine.process(
        _reasoning(significance="Tesla: earnings signal", stance="confirms"),
        domain="stocks",
    )
    assert second.trend == "strengthening"
    assert len(second.decision_trace) == 2


def test_contradicts_weakens_existing_hypothesis():
    engine = MentalModelEngine()
    engine.process(
        _reasoning(significance="Tesla: earnings signal", stance="new"), domain="stocks"
    )
    _, second = engine.process(
        _reasoning(significance="Tesla: earnings signal", stance="contradicts"),
        domain="stocks",
    )
    assert second.trend == "weakening"


def test_reasoning_result_passes_through_unchanged():
    engine = MentalModelEngine()
    original = _reasoning()
    passed_through, _ = engine.process(original, domain="stocks")
    assert passed_through is original


def test_different_domains_do_not_share_hypotheses():
    engine = MentalModelEngine()
    _, stocks_model = engine.process(
        _reasoning(significance="AI: rally", stance="new"), domain="stocks"
    )
    _, social_model = engine.process(
        _reasoning(significance="AI: rally", stance="new"), domain="social"
    )
    assert stocks_model.model_id != social_model.model_id
