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


# --- bounded retention (ADR-074) ----------------------------------------------


def test_trace_and_evidence_lists_stay_bounded_under_repeated_polling():
    from logan_core.mental_model.engine import MAX_RECENT_HYPOTHESIS_HISTORY

    assert MAX_RECENT_HYPOTHESIS_HISTORY == 50
    engine = MentalModelEngine()
    model = None
    for index in range(5_000):
        stance = "contradicts" if index % 3 == 0 else "confirms"
        _, model = engine.process(
            _reasoning(significance="Tesla: earnings signal", stance=stance),
            domain="stocks",
        )
        assert len(model.decision_trace) <= MAX_RECENT_HYPOTHESIS_HISTORY
        assert len(model.supporting) <= MAX_RECENT_HYPOTHESIS_HISTORY
        assert len(model.opposing) <= MAX_RECENT_HYPOTHESIS_HISTORY
    assert len(model.decision_trace) == MAX_RECENT_HYPOTHESIS_HISTORY
    assert len(model.supporting) == MAX_RECENT_HYPOTHESIS_HISTORY
    assert len(model.opposing) == MAX_RECENT_HYPOTHESIS_HISTORY
    assert len(engine._hypotheses) == 1


def test_the_most_recent_history_is_what_survives():
    engine = MentalModelEngine()
    event_ids = []
    model = None
    for _ in range(120):
        reasoning = _reasoning(significance="Tesla: earnings signal", stance="confirms")
        event_ids.append(str(reasoning.event_id))
        _, model = engine.process(reasoning, domain="stocks")
    # Oldest dropped first, newest kept, order preserved.
    assert model.supporting == event_ids[-50:]
    assert model.decision_trace[-1].rule.startswith("trend=")
    timestamps = [entry.timestamp for entry in model.decision_trace]
    assert timestamps == sorted(timestamps)


def test_history_below_the_bound_is_untouched():
    engine = MentalModelEngine()
    model = None
    for _ in range(10):
        _, model = engine.process(
            _reasoning(significance="Tesla: earnings signal", stance="confirms"),
            domain="stocks",
        )
    assert len(model.decision_trace) == 10
    assert len(model.supporting) == 10
    assert model.opposing == []


def test_bounding_history_does_not_change_confidence_or_trend():
    """Confidence is computed from the previous confidence, never from the
    lists -- so it must match plain arithmetic over the full stance
    sequence, well past the point where history starts being dropped."""
    stances = (["confirms"] * 3 + ["contradicts"] * 4 + ["complicates"]) * 40
    deltas = {"confirms": 0.10, "contradicts": -0.15, "complicates": -0.05}

    engine = MentalModelEngine()
    _, model = engine.process(
        _reasoning(significance="Tesla: earnings signal", stance="new"), domain="stocks"
    )
    expected = 0.5
    for stance in stances:
        previous = expected
        expected = max(0.0, min(1.0, expected + deltas[stance]))
        _, model = engine.process(
            _reasoning(significance="Tesla: earnings signal", stance=stance),
            domain="stocks",
        )
        assert model.confidence == expected
        assert model.trend == (
            "strengthening"
            if expected > previous
            else "weakening" if expected < previous else "stable"
        )
    assert len(stances) > 50  # history was being dropped throughout
