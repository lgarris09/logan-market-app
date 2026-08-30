"""Universe Manager V1a Block 9 -- deterministic market-driver tagging
(logan_core/thesis/market_driver.py). Every case is a pure function of
real, existing trigger-code constants -- no LLM, no semantic inference.
"""

from logan_core.convergence.tracker import STOCK_CONVERGENCE_MULTI_SOURCE
from logan_core.thesis.market_driver import (
    classify_market_driver,
    primary_signal_family,
    secondary_signal_families,
)
from logan_core.trigger_detection.stocks import (
    STOCK_ANALYST_DOWNGRADE,
    STOCK_ANALYST_UPGRADE,
    STOCK_EARNINGS_BEAT,
    STOCK_EARNINGS_MISS,
    STOCK_PRICE_MOVE_SIGNIFICANT,
)


def test_empty_trigger_codes_is_unclassified():
    assert classify_market_driver([]) == "UNCLASSIFIED"


def test_only_convergence_marker_is_unclassified():
    assert classify_market_driver([STOCK_CONVERGENCE_MULTI_SOURCE]) == "UNCLASSIFIED"


def test_earnings_beat_is_earnings_result():
    assert classify_market_driver([STOCK_EARNINGS_BEAT]) == "EARNINGS_RESULT"


def test_earnings_miss_is_earnings_result():
    assert classify_market_driver([STOCK_EARNINGS_MISS]) == "EARNINGS_RESULT"


def test_earnings_with_guidance_revised_is_earnings_guidance():
    assert (
        classify_market_driver([STOCK_EARNINGS_BEAT], guidance_revised=True)
        == "EARNINGS_GUIDANCE"
    )


def test_earnings_without_guidance_revision_is_plain_earnings_result():
    assert (
        classify_market_driver([STOCK_EARNINGS_BEAT], guidance_revised=False)
        == "EARNINGS_RESULT"
    )


def test_analyst_upgrade_is_analyst_reassessment():
    assert classify_market_driver([STOCK_ANALYST_UPGRADE]) == "ANALYST_REASSESSMENT"


def test_analyst_downgrade_is_analyst_reassessment():
    assert classify_market_driver([STOCK_ANALYST_DOWNGRADE]) == "ANALYST_REASSESSMENT"


def test_price_move_alone_is_price_dislocation():
    assert classify_market_driver([STOCK_PRICE_MOVE_SIGNIFICANT]) == "PRICE_DISLOCATION"


def test_earnings_takes_priority_over_analyst_and_price_when_converged():
    codes = [
        STOCK_EARNINGS_BEAT,
        STOCK_ANALYST_UPGRADE,
        STOCK_PRICE_MOVE_SIGNIFICANT,
        STOCK_CONVERGENCE_MULTI_SOURCE,
    ]
    assert classify_market_driver(codes) == "EARNINGS_RESULT"


def test_analyst_takes_priority_over_price_when_both_present():
    codes = [STOCK_ANALYST_UPGRADE, STOCK_PRICE_MOVE_SIGNIFICANT]
    assert classify_market_driver(codes) == "ANALYST_REASSESSMENT"


def test_unrecognized_code_alone_is_unclassified():
    assert classify_market_driver(["SOME_FUTURE_TRIGGER_CODE"]) == "UNCLASSIFIED"


# --- primary/secondary signal family -----------------------------------------


def test_primary_signal_family_is_none_when_nothing_recognized():
    assert primary_signal_family([]) is None
    assert primary_signal_family([STOCK_CONVERGENCE_MULTI_SOURCE]) is None


def test_primary_signal_family_matches_the_dominant_driver():
    assert primary_signal_family([STOCK_EARNINGS_BEAT]) == "earnings"
    assert primary_signal_family([STOCK_ANALYST_UPGRADE]) == "analyst_grade"
    assert primary_signal_family([STOCK_PRICE_MOVE_SIGNIFICANT]) == "price"


def test_secondary_signal_families_excludes_the_primary():
    codes = [STOCK_EARNINGS_BEAT, STOCK_ANALYST_UPGRADE, STOCK_PRICE_MOVE_SIGNIFICANT]
    secondaries = secondary_signal_families(codes)
    assert "earnings" not in secondaries
    assert set(secondaries) == {"analyst_grade", "price"}


def test_secondary_signal_families_empty_for_a_single_signal():
    assert secondary_signal_families([STOCK_EARNINGS_BEAT]) == []


def test_secondary_signal_families_deterministic_order():
    codes = [STOCK_PRICE_MOVE_SIGNIFICANT, STOCK_ANALYST_UPGRADE, STOCK_EARNINGS_BEAT]
    first = secondary_signal_families(codes)
    second = secondary_signal_families(list(reversed(codes)))
    assert first == second
