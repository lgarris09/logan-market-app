"""Confidence semantics regression matrix.

A durable suite for *what the confidence score means*, run through the
real scoring layers (Normalizer -> StocksTriggerEvaluator -> WorldModel ->
EvidenceTrustEngine -> ConclusionConfidenceEngine). Two kinds of test:

1. INVARIANTS -- properties any future scoring change must keep (bounds,
   determinism, monotonicity, no confidence from missing data, a source
   cannot corroborate itself, ...). These should never need editing.

2. CURRENT VALUES -- the exact numbers today's formula produces for a
   named set of cases (`CURRENT_VALUES` below). They exist so that a
   scoring change shows up as an explicit, reviewable diff. Editing that
   table is expected when scoring semantics change -- and only then, with
   an ADR. See docs/CONFIDENCE_SEMANTICS.md.
"""

from datetime import datetime, timedelta, timezone

import pytest

from logan_core.conclusion_confidence import ConclusionConfidenceEngine
from logan_core.contracts import EvidenceTrust, ReasoningResult
from logan_core.contracts.presentation import confidence_label_for
from logan_core.evidence_trust import SOURCE_REPUTATION_REGISTRY, EvidenceTrustEngine
from logan_core.normalization import Normalizer
from logan_core.opportunity_lifecycle import (
    CONFIDENCE_DELTA_THRESHOLD,
    OpportunityLifecycleTracker,
)
from logan_core.receptors.providers.base import EarningsReport, GradeChange, Quote
from logan_core.receptors.providers.fmp import FMP_SOURCE_ID
from logan_core.receptors.stocks_earnings import earnings_report_to_raw_signal
from logan_core.receptors.stocks_market_data import (
    grade_change_to_raw_signal,
    quote_to_raw_signal,
)
from logan_core.trigger_detection import StocksTriggerEvaluator
from logan_core.world_model import WorldModel

NOW = datetime(2026, 10, 5, 16, 0, 0, tzinfo=timezone.utc)
AGED_HOURS = 30 * 24  # typical of the live feed: recency contributes nothing
FRESH_HOURS = 0.5

# Today's constants, restated so a change to any of them is a visible diff.
BASE_TRUST_SINGLE_UNKNOWN_SOURCE_AGED = 0.375  # 0.35*0.5 source + 0.20 completeness
BEAT, MISS, PRICE, ANALYST = 0.22, 0.20, 0.10, 0.08


# --- builders -----------------------------------------------------------------


def earnings(
    actual, consensus, *, age_hours=AGED_HOURS, source=FMP_SOURCE_ID, ticker="AAA"
):
    return earnings_report_to_raw_signal(
        EarningsReport(
            entity_id=ticker,
            actual_eps=actual,
            consensus_eps=consensus,
            fiscal_quarter="Q3 2026",
            report_timestamp=NOW - timedelta(hours=age_hours),
            source_id=source,
            source_name="test",
        )
    )


def beat(pct, **kwargs):
    return earnings(1.0 + pct / 100.0, 1.0, **kwargs)


def miss(pct, **kwargs):
    return earnings(1.0 - pct / 100.0, 1.0, **kwargs)


def price_move(pct, *, age_hours=AGED_HOURS, source=FMP_SOURCE_ID, ticker="AAA"):
    return quote_to_raw_signal(
        Quote(
            entity_id=ticker,
            price=100.0 * (1 + pct / 100.0),
            previous_close=100.0,
            change_pct=pct,
            quote_timestamp=NOW - timedelta(hours=age_hours),
            source_id=source,
            source_name="test",
        )
    )


def analyst(action, *, age_hours=AGED_HOURS, source=FMP_SOURCE_ID, ticker="AAA"):
    return grade_change_to_raw_signal(
        GradeChange(
            entity_id=ticker,
            grading_firm="Example Securities",
            previous_rating="Hold",
            new_rating="Buy" if action == "upgrade" else "Sell",
            action=action,
            action_date=NOW - timedelta(hours=age_hours),
            source_id=source,
            source_name="test",
        )
    )


def evaluate(raw_signals, *, now=NOW):
    """One entity's signals through the real layers, in pipeline order.
    Signals of different types are merged the way the Orchestrator merges
    co-qualified events: every attached trigger is kept on the primary."""
    normalizer, detector, world = Normalizer(), StocksTriggerEvaluator(), WorldModel()
    normalized, event = [], None
    for raw in raw_signals:
        signal = normalizer.normalize(raw)
        normalized.append(signal)
        signal_event = world.process(
            signal, trigger_event=detector.evaluate(raw, signal)
        )
        if event is None or signal_event.event_id == event.event_id:
            event = signal_event
        else:
            event = event.model_copy(
                update={
                    "trigger_events": event.trigger_events + signal_event.trigger_events
                }
            )
    trust = EvidenceTrustEngine().evaluate(event, normalized, now=now)
    reasoning = ReasoningResult(
        event_id=event.event_id,
        significance="x",
        personal_relevance_narrative="x",
        stance="new",
        actionability="actionable",
        explanation="x",
        reasoned_at=now,
    )
    confidence = ConclusionConfidenceEngine().evaluate(reasoning, trust)
    return event, trust, confidence


def score(raw_signals, **kwargs) -> float:
    return evaluate(raw_signals, **kwargs)[2].confidence_score


# --- the matrix ---------------------------------------------------------------

MATRIX = {
    # earnings: weak / medium / strong, aged
    "earnings_beat_weak_aged": lambda: [beat(5.1)],
    "earnings_beat_medium_aged": lambda: [beat(12)],
    "earnings_beat_strong_aged": lambda: [beat(40)],
    "earnings_beat_extreme_aged": lambda: [beat(215)],
    "earnings_miss_weak_aged": lambda: [miss(5.1)],
    "earnings_miss_strong_aged": lambda: [miss(40)],
    # earnings: fresh
    "earnings_beat_medium_fresh": lambda: [beat(12, age_hours=FRESH_HOURS)],
    # earnings: not qualifying / missing data
    "earnings_in_line": lambda: [beat(1)],
    "earnings_below_threshold": lambda: [beat(4.9)],
    "earnings_missing_consensus": lambda: [earnings(1.2, None)],
    "earnings_missing_actual": lambda: [earnings(None, 1.0)],
    "earnings_zero_consensus": lambda: [earnings(1.2, 0.0)],
    # price
    "price_move_weak_aged": lambda: [price_move(5.5)],
    "price_move_strong_aged": lambda: [price_move(30)],
    "price_move_down_strong_aged": lambda: [price_move(-30)],
    "price_move_weak_fresh": lambda: [price_move(5.5, age_hours=FRESH_HOURS)],
    "price_move_below_threshold": lambda: [price_move(2)],
    # analyst
    "analyst_upgrade_aged": lambda: [analyst("upgrade")],
    "analyst_downgrade_aged": lambda: [analyst("downgrade")],
    # mixed signals on one entity
    "mixed_earnings_plus_analyst": lambda: [beat(12), analyst("upgrade")],
    "mixed_earnings_analyst_price": lambda: [
        beat(12),
        analyst("upgrade"),
        price_move(12),
    ],
    "mixed_analyst_plus_price": lambda: [analyst("upgrade"), price_move(12)],
}

# CURRENT VALUES -- today's formula. Change only with a scoring ADR.
CURRENT_VALUES = {
    "earnings_beat_weak_aged": (0.595, "Moderate"),
    "earnings_beat_medium_aged": (0.595, "Moderate"),
    "earnings_beat_strong_aged": (0.595, "Moderate"),
    "earnings_beat_extreme_aged": (0.595, "Moderate"),
    "earnings_miss_weak_aged": (0.575, "Moderate"),
    "earnings_miss_strong_aged": (0.575, "Moderate"),
    "earnings_in_line": (0.375, "Low"),
    "earnings_below_threshold": (0.375, "Low"),
    "earnings_missing_consensus": (0.375, "Low"),
    "earnings_missing_actual": (0.375, "Low"),
    "earnings_zero_consensus": (0.375, "Low"),
    "price_move_weak_aged": (0.475, "Low"),
    "price_move_strong_aged": (0.475, "Low"),
    "price_move_down_strong_aged": (0.475, "Low"),
    "price_move_below_threshold": (0.375, "Low"),
    "analyst_upgrade_aged": (0.455, "Low"),
    "analyst_downgrade_aged": (0.455, "Low"),
    "mixed_earnings_plus_analyst": (0.595, "Moderate"),
    "mixed_earnings_analyst_price": (0.595, "Moderate"),
    "mixed_analyst_plus_price": (0.475, "Low"),
}


@pytest.mark.parametrize("case", sorted(CURRENT_VALUES))
def test_current_values(case):
    expected_score, expected_label = CURRENT_VALUES[case]
    actual = score(MATRIX[case]())
    assert actual == pytest.approx(expected_score, abs=1e-6)
    assert confidence_label_for(actual) == expected_label


# --- invariants: bounds, determinism -------------------------------------------


@pytest.mark.parametrize("case", sorted(MATRIX))
def test_score_is_always_within_bounds(case):
    assert 0.0 <= score(MATRIX[case]()) <= 1.0


@pytest.mark.parametrize("case", sorted(MATRIX))
def test_identical_inputs_give_identical_scores(case):
    first = evaluate(MATRIX[case]())
    second = evaluate(MATRIX[case]())
    assert first[2].confidence_score == second[2].confidence_score
    assert first[1].trust_score == second[1].trust_score
    assert first[2].classification == second[2].classification


# --- invariants: magnitude -----------------------------------------------------


@pytest.mark.parametrize(
    "weaker, stronger",
    [
        ("earnings_beat_weak_aged", "earnings_beat_medium_aged"),
        ("earnings_beat_medium_aged", "earnings_beat_strong_aged"),
        ("earnings_beat_strong_aged", "earnings_beat_extreme_aged"),
        ("earnings_miss_weak_aged", "earnings_miss_strong_aged"),
        ("price_move_weak_aged", "price_move_strong_aged"),
    ],
)
def test_stronger_evidence_never_scores_below_weaker_evidence(weaker, stronger):
    """Today these are equal (the trigger contribution ignores magnitude).
    Under any future scheme they may differ, but never in this direction."""
    assert score(MATRIX[stronger]()) >= score(MATRIX[weaker]())


@pytest.mark.parametrize(
    "case, cap",
    [
        ("earnings_beat_extreme_aged", BEAT),
        ("earnings_miss_strong_aged", MISS),
        ("price_move_strong_aged", PRICE),
        ("analyst_upgrade_aged", ANALYST),
    ],
)
def test_no_trigger_contributes_more_than_its_registry_constant(case, cap):
    _event, trust, confidence = evaluate(MATRIX[case]())
    assert trust.trigger_confidence_bonus <= cap + 1e-9
    assert confidence.confidence_score <= (
        BASE_TRUST_SINGLE_UNKNOWN_SOURCE_AGED + cap + 1e-9
    )


def test_direction_of_a_move_does_not_change_evidence_strength():
    assert score(MATRIX["price_move_strong_aged"]()) == pytest.approx(
        score(MATRIX["price_move_down_strong_aged"]())
    )


# --- invariants: missing or non-qualifying data --------------------------------


@pytest.mark.parametrize(
    "case",
    [
        "earnings_in_line",
        "earnings_below_threshold",
        "earnings_missing_consensus",
        "earnings_missing_actual",
        "earnings_zero_consensus",
        "price_move_below_threshold",
    ],
)
def test_missing_or_non_qualifying_evidence_earns_no_trigger_confidence(case):
    _event, trust, confidence = evaluate(MATRIX[case]())
    assert trust.trigger_confidence_bonus == 0.0
    assert confidence.confidence_score == pytest.approx(trust.trust_score)
    # ...and never outranks a genuinely qualifying signal of the same age.
    assert confidence.confidence_score < score(MATRIX["analyst_upgrade_aged"]())


def test_missing_data_never_reads_as_moderate_or_high():
    for case in ("earnings_missing_consensus", "earnings_missing_actual"):
        assert confidence_label_for(score(MATRIX[case]())) in ("Low", "Speculative")


# --- invariants: recency -------------------------------------------------------


@pytest.mark.parametrize(
    "fresh, aged",
    [
        ("earnings_beat_medium_fresh", "earnings_beat_medium_aged"),
        ("price_move_weak_fresh", "price_move_weak_aged"),
    ],
)
def test_fresh_evidence_never_scores_below_the_same_evidence_aged(fresh, aged):
    assert score(MATRIX[fresh]()) > score(MATRIX[aged]())


def test_recency_only_ever_decays():
    previous = None
    for hours in (0.1, 1, 3, 6, 12, 24, 72, 720):
        current = score([beat(12, age_hours=hours)])
        if previous is not None:
            assert current <= previous + 1e-12
        previous = current


def test_recency_contribution_is_bounded_by_its_weight():
    assert (
        score([beat(12, age_hours=0)]) - score(MATRIX["earnings_beat_medium_aged"]())
        <= 0.20 + 1e-9
    )


# --- invariants: corroboration and repeated evidence ---------------------------


def test_identical_repeats_from_one_source_do_not_raise_the_score():
    once = score([beat(12)])
    repeated = score([beat(12) for _ in range(25)])
    assert repeated == pytest.approx(once)


def test_changed_content_from_one_source_does_not_raise_the_score():
    """ADR-076: a source cannot corroborate itself."""
    once = score([price_move(12)])
    moving = score([price_move(12 + step / 10) for step in range(25)])
    assert moving == pytest.approx(once)
    _event, trust, _confidence = evaluate(
        [price_move(12 + step / 10) for step in range(25)]
    )
    assert trust.corroboration == 0


def test_an_independent_source_does_raise_the_score():
    alone = score([beat(12)])
    corroborated = score([beat(12), beat(12, source="reuters_wire")])
    assert corroborated > alone


def test_corroboration_saturates_at_three_independent_sources():
    def with_sources(count):
        sources = [
            "reuters_wire",
            "bloomberg_terminal",
            "sec_filing",
            "sportsbook_feed",
        ]
        return evaluate([beat(12)] + [beat(12, source=s) for s in sources[:count]])[1]

    assert with_sources(1).corroboration == 1
    assert with_sources(3).corroboration == 3
    three, four = with_sources(3), with_sources(4)
    # A fourth source cannot add more corroboration weight than the third.
    assert min(four.corroboration / 3, 1.0) == min(three.corroboration / 3, 1.0)


# --- invariants: source reputation ---------------------------------------------


def test_an_unregistered_source_gets_the_neutral_default():
    assert (
        FMP_SOURCE_ID not in SOURCE_REPUTATION_REGISTRY
    )  # true today; see the contract
    _event, trust, _confidence = evaluate([beat(12)])
    assert trust.source_score == 0.5


def test_a_more_reputable_source_scores_at_least_as_high():
    ordered = sorted(SOURCE_REPUTATION_REGISTRY, key=SOURCE_REPUTATION_REGISTRY.get)
    scores = [score([beat(12, source=source)]) for source in ordered]
    assert scores == sorted(scores)
    assert scores[-1] > scores[0]


# --- invariants: mixed signals -------------------------------------------------


@pytest.mark.parametrize(
    "mixed, parts",
    [
        (
            "mixed_earnings_plus_analyst",
            ["earnings_beat_medium_aged", "analyst_upgrade_aged"],
        ),
        (
            "mixed_earnings_analyst_price",
            [
                "earnings_beat_medium_aged",
                "analyst_upgrade_aged",
                "price_move_strong_aged",
            ],
        ),
        (
            "mixed_analyst_plus_price",
            ["analyst_upgrade_aged", "price_move_strong_aged"],
        ),
    ],
)
def test_mixed_signals_never_score_below_their_strongest_part_or_above_the_sum(
    mixed, parts
):
    """Today a mixed opportunity equals its strongest part (trigger
    contributions are not summed, and signal families are not counted as
    corroboration). Any future 'signal diversity' credit must stay within
    these bounds: at least the strongest part, never more than adding
    every part's trigger contribution."""
    mixed_score = score(MATRIX[mixed]())
    part_scores = [score(MATRIX[p]()) for p in parts]
    assert mixed_score >= max(part_scores) - 1e-9
    upper = BASE_TRUST_SINGLE_UNKNOWN_SOURCE_AGED + sum(
        s - BASE_TRUST_SINGLE_UNKNOWN_SOURCE_AGED for s in part_scores
    )
    assert mixed_score <= upper + 1e-9


def test_signal_families_are_not_counted_as_corroboration():
    _event, trust, _confidence = evaluate(MATRIX["mixed_earnings_analyst_price"]())
    assert trust.corroboration == 0


# --- invariants: contradiction, classification, labels -------------------------


def _trust(**overrides) -> EvidenceTrust:
    values = dict(
        event_id="00000000-0000-0000-0000-000000000001",
        source_score=0.5,
        corroboration=0,
        recency_score=0.0,
        contradiction_flag=False,
        manipulation_risk="low",
        completeness=1.0,
        trust_score=0.375,
        trigger_confidence_bonus=0.22,
        evaluated_at=NOW,
    )
    values.update(overrides)
    return EvidenceTrust(**values)


def _confidence_from(trust: EvidenceTrust):
    reasoning = ReasoningResult(
        event_id=trust.event_id,
        significance="x",
        personal_relevance_narrative="x",
        stance="new",
        actionability="actionable",
        explanation="x",
        reasoned_at=NOW,
    )
    return ConclusionConfidenceEngine().evaluate(reasoning, trust)


def test_contradiction_always_lowers_the_score():
    plain = _confidence_from(_trust()).confidence_score
    contradicted = _confidence_from(_trust(contradiction_flag=True)).confidence_score
    assert contradicted == pytest.approx(plain * 0.7)
    assert contradicted < plain


def test_the_score_is_clamped_to_one():
    assert (
        _confidence_from(
            _trust(trust_score=0.95, trigger_confidence_bonus=0.22)
        ).confidence_score
        == 1.0
    )


def test_uncertainty_is_stated_for_single_source_evidence():
    _event, _trust_result, confidence = evaluate(MATRIX["earnings_beat_strong_aged"]())
    assert any(
        "one independent source" in factor for factor in confidence.limiting_factors
    )


@pytest.mark.parametrize(
    "value, label",
    [
        (1.0, "High"),
        (0.80, "High"),
        (0.7999, "Moderate"),
        (0.55, "Moderate"),
        (0.5499, "Low"),
        (0.35, "Low"),
        (0.3499, "Speculative"),
        (0.0, "Speculative"),
    ],
)
def test_label_boundaries(value, label):
    assert confidence_label_for(value) == label


def test_high_is_not_reachable_from_one_unregistered_source_today():
    """A documented property of the current formula, not a goal: the best
    case for single-provider evidence is the instant an earnings report
    lands. If this starts failing, the label thresholds need review."""
    best = score([beat(40, age_hours=0)])
    assert best < 0.80
    assert confidence_label_for(best) == "Moderate"


# --- lifecycle / revision behaviour --------------------------------------------


def _observe(tracker, value, when):
    return tracker.observe(
        entity_id="AAA",
        confidence_score=value,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.2,
        now=when,
    )


def test_an_unchanged_score_never_creates_a_revision():
    tracker = OpportunityLifecycleTracker()
    first = _observe(tracker, 0.595, NOW)
    for minute in range(1, 30):
        delta = _observe(tracker, 0.595, NOW + timedelta(minutes=minute))
        assert delta.is_meaningful is False
        assert delta.new_revision == first.new_revision


def test_a_change_below_the_threshold_is_not_a_revision():
    tracker = OpportunityLifecycleTracker()
    first = _observe(tracker, 0.595, NOW)
    delta = _observe(
        tracker, 0.595 + CONFIDENCE_DELTA_THRESHOLD - 0.01, NOW + timedelta(minutes=1)
    )
    assert delta.is_meaningful is False
    assert delta.new_revision == first.new_revision


@pytest.mark.parametrize(
    "new_value, change_type",
    [(0.70, "confidence_increased"), (0.487, "confidence_decreased")],
)
def test_a_change_past_the_threshold_is_a_revision_with_plain_wording(
    new_value, change_type
):
    """A step of this size IS a revision under today's tracker, whatever
    caused it. That is why a model or scoring change needs a neutral
    transition (ADR-078): recalculation must not reach this path as if the
    evidence itself had moved."""
    tracker = OpportunityLifecycleTracker()
    first = _observe(tracker, 0.595, NOW)
    delta = _observe(tracker, new_value, NOW + timedelta(minutes=1))
    assert delta.change_type == change_type
    assert delta.new_revision == first.new_revision + 1
    # ADR-077: the explanation never exposes the raw score or a percentage.
    assert not any(character.isdigit() for character in delta.reason)
    assert "%" not in delta.reason
