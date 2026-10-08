"""ADR-079 -- the Beta 1 EPS-safe fallback.

With the gate on, an earnings-surprise trigger (beat, miss or in-line) fires
only when the provider proved the reported and the consensus EPS comparable.
Unknown is never treated as valid, and a blocked comparison produces no
trigger, no confidence contribution and no magnitude. Other signal families
are unaffected.
"""

from datetime import datetime, timedelta, timezone

import pytest

from logan_core.contracts import RawSignal
from logan_core.normalization import Normalizer
from logan_core.trigger_detection.stocks import (
    STOCK_ANALYST_UPGRADE,
    STOCK_EARNINGS_BEAT,
    STOCK_EARNINGS_IN_LINE,
    STOCK_EARNINGS_MISS,
    STOCK_PRICE_MOVE_SIGNIFICANT,
    StocksTriggerEvaluator,
    assess_eps_comparability,
    eps_surprise_is_comparable,
)

NOW = datetime(2026, 10, 5, 21, 0, tzinfo=timezone.utc)


def _proof(**overrides) -> dict:
    proof = {
        "actual_eps_basis": "adjusted",
        "consensus_eps_basis": "adjusted",
        "actual_eps_share_basis": "diluted",
        "consensus_eps_share_basis": "diluted",
        "fiscal_quarter": "2026-Q3",
        "consensus_fiscal_quarter": "2026-Q3",
        "consensus_as_of": (NOW - timedelta(days=2)).isoformat(),
        "actual_eps_currency": "USD",
        "consensus_eps_currency": "USD",
        "split_between_estimate_and_actual": False,
        "restated": False,
    }
    proof.update(overrides)
    return {k: v for k, v in proof.items() if v is not None}


def _earnings(actual: float, consensus: float, **fields) -> RawSignal:
    return RawSignal(
        domain="stocks",
        source_id="fixture_earnings_provider",
        source_name="STRATUS Test Fixture (not live data)",
        raw_value={
            "entity_id": "NVDA",
            "entity_type": "ticker",
            "signal_type": "earnings_signal",
            "value": "NVDA reported quarterly results",
            "actual_eps": actual,
            "consensus_eps": consensus,
            **fields,
        },
        captured_at=NOW,
    )


def _evaluate(raw: RawSignal, *, gate: bool = True):
    evaluator = StocksTriggerEvaluator(eps_comparability_gate=gate)
    return evaluator, evaluator.evaluate(raw, Normalizer().normalize(raw))


# --- valid comparable EPS ------------------------------------------------------


def test_proven_comparable_beat_fires():
    _, trigger = _evaluate(_earnings(1.20, 1.00, **_proof()))
    assert trigger is not None and trigger.trigger_code == STOCK_EARNINGS_BEAT


def test_proven_comparable_miss_fires():
    _, trigger = _evaluate(_earnings(0.80, 1.00, **_proof()))
    assert trigger is not None and trigger.trigger_code == STOCK_EARNINGS_MISS


def test_proven_comparable_in_line_fires():
    _, trigger = _evaluate(_earnings(1.01, 1.00, **_proof()))
    assert trigger is not None and trigger.trigger_code == STOCK_EARNINGS_IN_LINE


# --- blocked comparisons -------------------------------------------------------

BLOCKED_CASES = [
    # (label, proof overrides, expected reason code, expected state)
    (
        "basis unknown",
        {"actual_eps_basis": None, "consensus_eps_basis": None},
        "eps_basis_unknown",
        "blocked_incomparable_basis",
    ),
    (
        "basis mismatch",
        {"actual_eps_basis": "gaap"},
        "eps_basis_mismatch",
        "blocked_incomparable_basis",
    ),
    (
        "share basis unknown",
        {"consensus_eps_share_basis": None},
        "eps_share_basis_unknown",
        "blocked_incomparable_basis",
    ),
    (
        "fiscal period mismatch",
        {"consensus_fiscal_quarter": "2026-Q2"},
        "fiscal_period_mismatch",
        None,
    ),
    (
        "fiscal period unverified",
        {"consensus_fiscal_quarter": None},
        "fiscal_period_unverified",
        None,
    ),
    (
        "no pre-release estimate timestamp",
        {"consensus_as_of": None},
        "estimate_timestamp_unverified",
        None,
    ),
    (
        "estimate captured after the release",
        {"consensus_as_of": (NOW + timedelta(hours=1)).isoformat()},
        "estimate_not_pre_release",
        None,
    ),
    (
        "split status unknown",
        {"split_between_estimate_and_actual": None},
        "split_status_unverified",
        None,
    ),
    (
        "unadjusted split",
        {"split_between_estimate_and_actual": True},
        "unadjusted_split_between_estimate_and_actual",
        None,
    ),
    ("restatement unresolved", {"restated": None}, "restatement_unresolved", None),
    ("restated", {"restated": True}, "restatement_unresolved", None),
    ("currency unknown", {"actual_eps_currency": None}, "currency_unverified", None),
]


@pytest.mark.parametrize(
    "label,overrides,code,state", BLOCKED_CASES, ids=[c[0] for c in BLOCKED_CASES]
)
@pytest.mark.parametrize("actual", [1.20, 0.80, 1.01], ids=["beat", "miss", "in-line"])
def test_unproven_comparison_emits_no_earnings_trigger(
    label, overrides, code, state, actual
):
    raw = _earnings(actual, 1.00, **_proof(**overrides))
    evaluator, trigger = _evaluate(raw)
    assert trigger is None
    block = evaluator.last_eps_block
    assert block is not None
    assert code in block.reason_codes
    assert block.state.startswith("blocked_")
    if state is not None:
        assert block.state == state
    # A blocked observation carries no magnitude, band or direction.
    assert block.magnitude_pct is None
    assert block.materiality is None
    assert block.direction is None


@pytest.mark.parametrize("consensus", [0.0, 0.05, -0.40])
def test_negative_or_near_zero_denominator_is_blocked(consensus):
    evaluator, trigger = _evaluate(_earnings(0.60, consensus, **_proof()))
    assert trigger is None
    assert evaluator.last_eps_block is not None
    assert "estimate_denominator_ineligible" in evaluator.last_eps_block.reason_codes


def test_current_provider_shape_is_blocked():
    """What the live provider supplies today: two numbers and a quarter,
    with no statement of basis. That must not produce a beat."""
    raw = _earnings(1.20, 1.00, fiscal_quarter="2026-Q3")
    evaluator, trigger = _evaluate(raw)
    assert trigger is None
    assert evaluator.last_eps_block is not None
    assert evaluator.last_eps_block.state == "blocked_incomparable_basis"
    assert "earnings_eps_comparability_unresolved" in (
        evaluator.last_eps_block.reason_codes
    )


def test_unknown_never_becomes_valid():
    """Removing any single proof field blocks the comparison."""
    full = _proof()
    for field in full:
        partial = {k: v for k, v in full.items() if k != field}
        assessment = assess_eps_comparability(_earnings(1.20, 1.00, **partial), "NVDA")
        assert not eps_surprise_is_comparable(assessment), field


def test_reason_codes_are_stable_and_ordered():
    raw = _earnings(1.20, 1.00, fiscal_quarter="2026-Q3")
    first = assess_eps_comparability(raw, "NVDA").reason_codes
    second = assess_eps_comparability(raw, "NVDA").reason_codes
    assert first == second
    assert len(first) == len(set(first))


# --- nothing else is affected --------------------------------------------------


def test_gate_off_reproduces_prior_behavior():
    _, trigger = _evaluate(_earnings(1.20, 1.00, fiscal_quarter="2026-Q3"), gate=False)
    assert trigger is not None and trigger.trigger_code == STOCK_EARNINGS_BEAT


def test_blocked_eps_does_not_block_other_signal_families():
    """An otherwise valid event for the same company still qualifies on its
    own evidence when the EPS comparison is blocked."""
    evaluator = StocksTriggerEvaluator(eps_comparability_gate=True)
    earnings = _earnings(1.20, 1.00, fiscal_quarter="2026-Q3")
    assert evaluator.evaluate(earnings, Normalizer().normalize(earnings)) is None

    price = RawSignal(
        domain="stocks",
        source_id="fixture_quote_provider",
        source_name="STRATUS Test Fixture (not live data)",
        raw_value={
            "entity_id": "NVDA",
            "entity_type": "ticker",
            "signal_type": "price_change",
            "value": "NVDA moved",
            "change_pct": 6.4,
            "price": 106.4,
            "previous_close": 100.0,
        },
        captured_at=NOW,
    )
    price_trigger = evaluator.evaluate(price, Normalizer().normalize(price))
    assert price_trigger is not None
    assert price_trigger.trigger_code == STOCK_PRICE_MOVE_SIGNIFICANT

    grade = RawSignal(
        domain="stocks",
        source_id="fixture_grade_provider",
        source_name="STRATUS Test Fixture (not live data)",
        raw_value={
            "entity_id": "NVDA",
            "entity_type": "ticker",
            "signal_type": "analyst_change",
            "value": "NVDA upgraded",
            "action": "upgrade",
            "grading_firm": "Example Research",
        },
        captured_at=NOW,
    )
    grade_trigger = evaluator.evaluate(grade, Normalizer().normalize(grade))
    assert grade_trigger is not None
    assert grade_trigger.trigger_code == STOCK_ANALYST_UPGRADE
