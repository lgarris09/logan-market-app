"""ADR-083 -- evidence strength is derived from named conditions, never from
a score threshold or a population percentile, and a blocked observation
never receives a label.
"""

import ast
import itertools
import pathlib
from datetime import datetime, timezone
from typing import Any

import pytest

import logan_core.conclusion_confidence.evidence_strength as es
from logan_core.conclusion_confidence.evidence_strength import (
    CONDITIONS,
    EVIDENCE_LABELS,
    FRESHNESS_NOT_EVALUATED,
    assess_evidence_strength,
    evidence_label_for,
)
from logan_core.contracts import RawSignal
from logan_core.normalization import Normalizer
from logan_core.trigger_detection.stocks import StocksTriggerEvaluator


def _assess(**overrides):
    kwargs: dict[str, Any] = dict(
        corroboration=1,
        completeness=1.0,
        contradiction_flag=False,
        manipulation_risk="low",
        freshness_state="FRESH",
    )
    kwargs.update(overrides)
    return assess_evidence_strength(**kwargs)


# --- each state maps to named conditions ---------------------------------------


def test_strong_requires_independent_corroboration_and_established_freshness():
    result = _assess(corroboration=2)
    assert result.strength == "strong"
    assert {
        "qualified",
        "independent_corroboration",
        "details_complete",
        "no_conflict",
        "freshness_established",
    } <= set(result.conditions)
    assert result.limitations == () and result.critical == ()


def test_single_origin_with_no_conflict_is_supported():
    result = _assess(corroboration=1)
    assert result.strength == "supported"
    assert "single_origin" in result.conditions
    assert result.limitations == () and result.critical == ()


@pytest.mark.parametrize("freshness", ["FRESH", "RECENTLY_OBSERVED"])
def test_both_established_freshness_states_count(freshness):
    assert _assess(corroboration=2, freshness_state=freshness).strength == "strong"


def test_corroboration_without_evaluated_freshness_is_not_strong():
    """Strong is claimed only when every condition is actually met. With no
    freshness contract the freshness condition is not met, so the most that
    can be said is Supported."""
    result = _assess(corroboration=3, freshness_state=FRESHNESS_NOT_EVALUATED)
    assert result.strength == "supported"
    assert "freshness_not_evaluated" in result.conditions


LIMITED_CASES = [
    ({"completeness": 0.75}, "details_incomplete"),
    ({"manipulation_risk": "medium"}, "elevated_manipulation_risk"),
    ({"freshness_state": "STALE_WITHIN_GRACE"}, "freshness_within_grace"),
    ({"freshness_state": "UNAVAILABLE"}, "freshness_unconfirmed"),
    ({"freshness_state": None}, "freshness_unconfirmed"),
    ({"freshness_state": "A_STATE_FROM_THE_FUTURE"}, "freshness_unconfirmed"),
]


@pytest.mark.parametrize("overrides,code", LIMITED_CASES)
@pytest.mark.parametrize("corroboration", [1, 2, 5])
def test_each_defined_limitation_yields_limited(overrides, code, corroboration):
    result = _assess(corroboration=corroboration, **overrides)
    assert result.strength == "limited"
    assert code in result.limitations
    assert result.critical == ()


@pytest.mark.parametrize(
    "overrides,code",
    [
        ({"contradiction_flag": True}, "contradicting_evidence"),
        ({"manipulation_risk": "high"}, "high_manipulation_risk"),
    ],
)
def test_a_critical_condition_claims_no_strength_tier(overrides, code):
    result = _assess(corroboration=4, **overrides)
    assert result.strength == "conflicting"
    assert code in result.critical


def test_limited_is_only_ever_caused_by_a_defined_limitation():
    """Exhaustive over the input space: Limited appears exactly when one of
    the four defined non-critical limitations holds and nothing critical
    does; Strong exactly when all conditions are met."""
    for (
        corroboration,
        completeness,
        contradiction,
        risk,
        freshness,
    ) in itertools.product(
        [0, 1, 2, 3],
        [0.5, 1.0],
        [False, True],
        ["low", "medium", "high"],
        [
            "FRESH",
            "RECENTLY_OBSERVED",
            "STALE_WITHIN_GRACE",
            "UNAVAILABLE",
            None,
            FRESHNESS_NOT_EVALUATED,
        ],
    ):
        result = assess_evidence_strength(
            corroboration=corroboration,
            completeness=completeness,
            contradiction_flag=contradiction,
            manipulation_risk=risk,
            freshness_state=freshness,
        )
        critical = contradiction or risk == "high"
        limited = (
            completeness < 1.0
            or risk == "medium"
            or freshness in ("STALE_WITHIN_GRACE", "UNAVAILABLE", None)
        )
        if critical:
            expected = "conflicting"
        elif limited:
            expected = "limited"
        elif corroboration >= 2 and freshness in ("FRESH", "RECENTLY_OBSERVED"):
            expected = "strong"
        else:
            expected = "supported"
        assert result.strength == expected
        assert set(result.conditions) <= set(CONDITIONS)
        assert len(result.conditions) == len(set(result.conditions))


def test_assessment_is_deterministic():
    assert _assess(corroboration=2) == _assess(corroboration=2)


# --- what it is not ------------------------------------------------------------


def test_no_score_threshold_or_percentile_is_used():
    """Structural: the function takes no score and compares against no
    numeric threshold other than the two condition definitions."""
    import inspect

    params = set(inspect.signature(assess_evidence_strength).parameters)
    assert params == {
        "corroboration",
        "completeness",
        "contradiction_flag",
        "manipulation_risk",
        "freshness_state",
    }
    source = pathlib.Path(es.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    numbers = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
    }
    # ">= 2 independent origins" and "completeness >= 1.0" only.
    assert numbers == {2, 1.0}
    identifiers = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }
    for forbidden in ("confidence_score", "trust_score", "percentile", "quantile"):
        assert not any(forbidden in name for name in identifiers)


def test_strength_ignores_magnitude_and_personal_relevance():
    """Materiality and personal relevance are not inputs at all."""
    import inspect

    params = set(inspect.signature(assess_evidence_strength).parameters)
    for not_an_input in ("magnitude", "materiality", "relevance", "watched", "urgency"):
        assert not any(not_an_input in p for p in params)


def test_labels_make_no_probability_or_advice_claim():
    assert set(EVIDENCE_LABELS) == {"strong", "supported", "limited", "conflicting"}
    for label in EVIDENCE_LABELS.values():
        assert label.endswith(" evidence")
        assert not any(ch.isdigit() or ch == "%" for ch in label)
        for word in ("likely", "probab", "buy", "sell", "high", "low", "confidence"):
            assert word not in label.lower()
    for text in CONDITIONS.values():
        assert "%" not in text


def test_no_label_without_a_strength():
    assert evidence_label_for(None) is None
    assert evidence_label_for("blocked_incomparable_basis") is None
    assert evidence_label_for("something_else") is None
    assert evidence_label_for("supported") == "Supported evidence"


# --- a blocked observation never receives a label ------------------------------


def test_blocked_observation_never_reaches_a_strength_label():
    """End to end at the trigger boundary: a blocked EPS comparison emits no
    trigger, so no event, no confidence evaluation and no label exist for
    it. Its qualification state is not a strength and maps to no label."""
    raw = RawSignal(
        domain="stocks",
        source_id="fixture_earnings_provider",
        source_name="STRATUS Test Fixture (not live data)",
        raw_value={
            "entity_id": "NVDA",
            "entity_type": "ticker",
            "signal_type": "earnings_signal",
            "value": "NVDA reported quarterly results",
            "actual_eps": 1.20,
            "consensus_eps": 1.00,
        },
        captured_at=datetime(2026, 10, 5, tzinfo=timezone.utc),
    )
    evaluator = StocksTriggerEvaluator(eps_comparability_gate=True)
    assert evaluator.evaluate(raw, Normalizer().normalize(raw)) is None
    block = evaluator.last_eps_block
    assert block is not None and block.state.startswith("blocked_")
    assert evidence_label_for(block.state) is None
    assert block.state not in EVIDENCE_LABELS
