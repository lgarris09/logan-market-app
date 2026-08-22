"""Sprint 3.6.7 — stocks_market_data.py receptor unit tests: Quote/GradeChange
-> RawSignal mapping. Mirrors test_stocks_earnings_receptor.py's coverage
style and mypy-safe raw_value narrowing pattern for the new receptor.
"""

from datetime import datetime, timezone

from logan_core.contracts import RawSignal
from logan_core.receptors import grade_change_to_raw_signal, quote_to_raw_signal
from logan_core.receptors.providers import GradeChange, Quote

NOW = datetime(2026, 8, 21, 20, 0, 0, tzinfo=timezone.utc)


def _raw_value(raw: RawSignal) -> dict:
    # raw_value is typed `object` on the shared RawSignal contract; both
    # receptor functions here always build a dict, so narrow it here rather
    # than indexing `object` directly (mirrors test_stocks_earnings_receptor.py).
    assert isinstance(raw.raw_value, dict)
    return raw.raw_value


def _quote(change_pct: float = 7.4) -> Quote:
    return Quote(
        entity_id="NVDA",
        price=127.27,
        previous_close=118.50,
        change_pct=change_pct,
        quote_timestamp=NOW,
        source_id="fmp",
        source_name="Financial Modeling Prep",
    )


def _grade(
    action: str = "upgrade",
    previous_rating: str | None = "Hold",
    new_rating: str | None = "Buy",
) -> GradeChange:
    return GradeChange(
        entity_id="NVDA",
        grading_firm="Goldman Sachs",
        previous_rating=previous_rating,
        new_rating=new_rating,
        action=action,
        action_date=NOW,
        source_id="fmp",
        source_name="Financial Modeling Prep",
    )


def test_quote_maps_to_raw_signal_with_price_change_signal_type():
    raw_value = _raw_value(quote_to_raw_signal(_quote()))
    assert raw_value["signal_type"] == "price_change"
    assert raw_value["entity_id"] == "NVDA"
    assert raw_value["entity_type"] == "ticker"
    assert raw_value["change_pct"] == 7.4
    assert raw_value["price"] == 127.27
    assert raw_value["previous_close"] == 118.50


def test_quote_raw_signal_domain_and_source_are_preserved():
    raw = quote_to_raw_signal(_quote())
    assert raw.domain == "stocks"
    assert raw.source_id == "fmp"
    assert raw.captured_at == NOW


def test_quote_summary_is_truthful_and_direction_aware():
    up_value = _raw_value(quote_to_raw_signal(_quote(change_pct=7.4)))
    assert "up" in up_value["value"]
    down_value = _raw_value(quote_to_raw_signal(_quote(change_pct=-7.4)))
    assert "down" in down_value["value"]
    assert "7.40" in down_value["value"]  # abs() applied to the summary


def test_grade_change_maps_to_raw_signal_with_analyst_change_signal_type():
    raw_value = _raw_value(grade_change_to_raw_signal(_grade()))
    assert raw_value["signal_type"] == "analyst_change"
    assert raw_value["entity_id"] == "NVDA"
    assert raw_value["grading_firm"] == "Goldman Sachs"
    assert raw_value["action"] == "upgrade"
    assert raw_value["previous_rating"] == "Hold"
    assert raw_value["new_rating"] == "Buy"


def test_grade_change_raw_signal_domain_and_source_are_preserved():
    raw = grade_change_to_raw_signal(_grade())
    assert raw.domain == "stocks"
    assert raw.source_id == "fmp"
    assert raw.captured_at == NOW


def test_grade_change_never_fabricates_missing_ratings():
    raw_value = _raw_value(
        grade_change_to_raw_signal(_grade(previous_rating=None, new_rating="Buy"))
    )
    assert "previous_rating" not in raw_value
    assert raw_value["new_rating"] == "Buy"


def test_grade_change_summary_reflects_real_action_not_fabricated_text():
    raw_value = _raw_value(
        grade_change_to_raw_signal(
            _grade(action="maintain", previous_rating="Buy", new_rating="Buy")
        )
    )
    assert "maintain" in raw_value["value"]
    assert "maintaind" not in raw_value["value"]  # no naive string-concat typo
