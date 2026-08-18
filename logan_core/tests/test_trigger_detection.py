"""Sprint 3.6.6 — deterministic trigger detection unit tests (Phase 8).

Covers evaluate_earnings_beat_condition's pure fire condition directly (every
edge case explicitly, per the sprint's Phase 8 checklist) and
StocksTriggerEvaluator's TriggerEvent construction on top of it.
"""

from datetime import datetime

from logan_core.contracts import NormalizedSignal, RawSignal
from logan_core.normalization import Normalizer
from logan_core.trigger_detection import (
    StocksTriggerEvaluator,
    evaluate_earnings_beat_condition,
    evaluate_earnings_in_line_condition,
    evaluate_earnings_miss_condition,
)
from logan_core.trigger_detection.stocks import (
    STOCK_EARNINGS_BEAT,
    STOCK_EARNINGS_IN_LINE,
    STOCK_EARNINGS_MISS,
)


def test_beat_above_threshold_fires():
    fired, beat_pct, reason = evaluate_earnings_beat_condition(1.05, 0.98)
    assert fired is True
    assert beat_pct is not None and round(beat_pct, 2) == 7.14
    assert "fired" in reason


def test_beat_below_threshold_does_not_fire():
    # actual > consensus but well under the 5.0 beat_pct threshold
    fired, beat_pct, reason = evaluate_earnings_beat_condition(1.00, 0.99)
    assert fired is False
    assert beat_pct is not None and beat_pct < 5.0
    assert "below the" in reason


def test_actual_below_consensus_does_not_fire():
    fired, beat_pct, reason = evaluate_earnings_beat_condition(0.90, 0.98)
    assert fired is False
    assert beat_pct is None
    assert "does not exceed" in reason


def test_actual_equal_consensus_does_not_fire():
    fired, beat_pct, reason = evaluate_earnings_beat_condition(0.98, 0.98)
    assert fired is False
    assert beat_pct is None


def test_zero_consensus_handled_safely():
    fired, beat_pct, reason = evaluate_earnings_beat_condition(0.10, 0.0)
    assert fired is False
    assert beat_pct is None
    assert "zero" in reason


def test_missing_actual_eps_does_not_fire():
    fired, beat_pct, reason = evaluate_earnings_beat_condition(None, 0.98)
    assert fired is False
    assert beat_pct is None
    assert "actual_eps missing" in reason


def test_missing_consensus_eps_does_not_fire():
    fired, beat_pct, reason = evaluate_earnings_beat_condition(1.05, None)
    assert fired is False
    assert beat_pct is None
    assert "consensus_eps missing" in reason


def test_negative_consensus_uses_absolute_value_denominator():
    # A real (if unusual) case: consensus was a loss, actual beat it materially.
    fired, beat_pct, _ = evaluate_earnings_beat_condition(0.10, -0.20)
    assert fired is True
    assert beat_pct is not None and round(beat_pct, 6) == 150.0


def test_miss_above_threshold_fires():
    fired, miss_pct, reason = evaluate_earnings_miss_condition(0.52, 0.68)
    assert fired is True
    assert miss_pct is not None and round(miss_pct, 2) == 23.53
    assert "fired" in reason


def test_miss_below_threshold_does_not_fire():
    # actual < consensus but well under the 5.0 miss_pct threshold
    fired, miss_pct, reason = evaluate_earnings_miss_condition(0.97, 1.00)
    assert fired is False
    assert miss_pct is not None and miss_pct < 5.0
    assert "below the" in reason


def test_actual_above_consensus_does_not_miss():
    fired, miss_pct, reason = evaluate_earnings_miss_condition(1.05, 0.98)
    assert fired is False
    assert miss_pct is None
    assert "does not fall below" in reason


def test_miss_missing_fields_and_zero_consensus_handled_safely():
    assert evaluate_earnings_miss_condition(None, 0.98)[:2] == (False, None)
    assert evaluate_earnings_miss_condition(0.52, None)[:2] == (False, None)
    fired, miss_pct, reason = evaluate_earnings_miss_condition(0.10, 0.0)
    assert fired is False
    assert miss_pct is None
    assert "zero" in reason


def test_in_line_within_two_percent_fires_neutral():
    fired, pct, reason = evaluate_earnings_in_line_condition(0.71, 0.70)
    assert fired is True
    assert pct is not None and round(pct, 2) == 1.43
    assert "fired" in reason


def test_in_line_fires_on_small_downside_too():
    # abs(beat_pct) < 2.0 regardless of direction.
    fired, pct, reason = evaluate_earnings_in_line_condition(0.99, 1.00)
    assert fired is True
    assert pct is not None and pct < 0
    assert "fired" in reason


def test_in_line_does_not_fire_at_or_above_two_percent():
    fired, pct, reason = evaluate_earnings_in_line_condition(0.714, 0.70)
    assert fired is False
    assert pct is not None
    assert "at or above" in reason


def test_dead_zone_between_two_and_five_percent_fires_nothing():
    # 4.08% beat: below BEAT's 5.0 threshold, at/above IN_LINE's 2.0 threshold.
    # Deliberate registry-defined gap -- neither trigger fires here.
    beat_fired, _, _ = evaluate_earnings_beat_condition(1.02, 0.98)
    in_line_fired, _, _ = evaluate_earnings_in_line_condition(1.02, 0.98)
    miss_fired, _, _ = evaluate_earnings_miss_condition(1.02, 0.98)
    assert beat_fired is False
    assert miss_fired is False
    assert in_line_fired is False


def _raw_signal(raw_value: dict, now: datetime) -> RawSignal:
    return RawSignal(
        domain="stocks",
        source_id="fixture_earnings_provider",
        source_name="STRATUS Test Fixture (not live data)",
        raw_value=raw_value,
        captured_at=now,
    )


def _normalized(raw: RawSignal, now: datetime) -> NormalizedSignal:
    # Reuses the real Normalizer rather than hand-building NormalizedSignal --
    # exactly what the real pipeline does, and avoids duplicating its
    # extraction logic here.
    return Normalizer().normalize(raw)


def test_evaluator_fires_and_returns_populated_trigger_event(now):
    raw = _raw_signal(
        {
            "entity_id": "NVDA",
            "entity_type": "ticker",
            "signal_type": "earnings_signal",
            "value": "NVDA reported EPS of 1.05 vs. consensus 0.98",
            "unit": None,
            "actual_eps": 1.05,
            "consensus_eps": 0.98,
            "fiscal_quarter": "Q2 2026",
            "guidance_revised": True,
            "guidance_delta_pct": 6.7,
        },
        now,
    )
    normalized = _normalized(raw, now)

    trigger = StocksTriggerEvaluator().evaluate(raw, normalized)

    assert trigger is not None
    assert trigger.trigger_code == STOCK_EARNINGS_BEAT
    assert trigger.trigger_class == "catalyst"
    assert trigger.direction == "positive"
    assert trigger.affected_entity_id == "NVDA"
    assert trigger.confidence_contribution == 0.22
    assert trigger.originating_signal_ids == [normalized.signal_id]
    assert trigger.source_id == "fixture_earnings_provider"
    assert trigger.context["actual_eps"] == 1.05
    assert trigger.context["consensus_eps"] == 0.98
    assert trigger.context["fiscal_quarter"] == "Q2 2026"
    assert trigger.context["guidance_revised"] is True
    assert round(trigger.context["beat_pct"], 2) == 7.14
    assert trigger.decision_trace
    assert "fired" in trigger.decision_trace[0].rule


def test_evaluator_no_fire_returns_none_in_dead_zone(now):
    # 4.08% beat: below BEAT's 5.0 threshold, at/above IN_LINE's 2.0 threshold.
    raw = _raw_signal(
        {
            "entity_id": "NVDA",
            "entity_type": "ticker",
            "signal_type": "earnings_signal",
            "value": "NVDA reported EPS of 1.02 vs. consensus 0.98",
            "unit": None,
            "actual_eps": 1.02,
            "consensus_eps": 0.98,
        },
        now,
    )
    normalized = _normalized(raw, now)
    assert StocksTriggerEvaluator().evaluate(raw, normalized) is None


def test_evaluator_fires_miss_and_returns_populated_trigger_event(now):
    raw = _raw_signal(
        {
            "entity_id": "NVDA",
            "entity_type": "ticker",
            "signal_type": "earnings_signal",
            "value": "NVDA reported EPS of 0.52 vs. consensus 0.68",
            "unit": None,
            "actual_eps": 0.52,
            "consensus_eps": 0.68,
        },
        now,
    )
    normalized = _normalized(raw, now)

    trigger = StocksTriggerEvaluator().evaluate(raw, normalized)

    assert trigger is not None
    assert trigger.trigger_code == STOCK_EARNINGS_MISS
    assert trigger.trigger_class == "catalyst"
    assert trigger.direction == "negative"
    assert trigger.confidence_contribution == 0.20
    assert round(trigger.context["miss_pct"], 2) == 23.53
    assert "beat_pct" not in trigger.context
    assert "fired" in trigger.decision_trace[0].rule


def test_evaluator_fires_in_line_with_zero_confidence_contribution(now):
    raw = _raw_signal(
        {
            "entity_id": "NVDA",
            "entity_type": "ticker",
            "signal_type": "earnings_signal",
            "value": "NVDA reported EPS of 0.99 vs. consensus 0.98",
            "unit": None,
            "actual_eps": 0.99,
            "consensus_eps": 0.98,
        },
        now,
    )
    normalized = _normalized(raw, now)

    trigger = StocksTriggerEvaluator().evaluate(raw, normalized)

    assert trigger is not None
    assert trigger.trigger_code == STOCK_EARNINGS_IN_LINE
    assert trigger.trigger_class == "confirmation"
    assert trigger.direction == "neutral"
    assert trigger.confidence_contribution == 0.0
    assert round(trigger.context["beat_pct"], 2) == 1.02


def test_evaluator_ignores_non_earnings_signal_types(now):
    raw = _raw_signal(
        {
            "entity_id": "NVDA",
            "entity_type": "ticker",
            "signal_type": "technical_breakout",
            "value": "Broad market breadth turns bullish",
            "unit": None,
        },
        now,
    )
    normalized = _normalized(raw, now)
    assert StocksTriggerEvaluator().evaluate(raw, normalized) is None


def test_evaluator_does_not_fabricate_missing_context_fields(now):
    # No fiscal_quarter/guidance fields supplied -- must not appear in
    # context at all, per Phase 1/7's "never fabricate an absent field."
    raw = _raw_signal(
        {
            "entity_id": "NVDA",
            "entity_type": "ticker",
            "signal_type": "earnings_signal",
            "value": "NVDA reported EPS of 1.05 vs. consensus 0.98",
            "unit": None,
            "actual_eps": 1.05,
            "consensus_eps": 0.98,
        },
        now,
    )
    normalized = _normalized(raw, now)
    trigger = StocksTriggerEvaluator().evaluate(raw, normalized)
    assert trigger is not None
    assert "fiscal_quarter" not in trigger.context
    assert "guidance_revised" not in trigger.context
    assert "guidance_delta_pct" not in trigger.context
