"""Sprint 3.6.7 — FmpMarketDataProvider contract tests (fetch_quote,
fetch_latest_grade_change). Every test here uses httpx.MockTransport (no real
network access), mirroring test_fmp_provider.py's pattern exactly. The one
test that calls the live FMP API lives outside pytest collection entirely --
see logan_core/live_verification/nvda_market_data.py.
"""

import httpx
import pytest

from logan_core.receptors.providers import (
    FMP_SOURCE_ID,
    FMP_SOURCE_NAME,
    FmpMarketDataProvider,
    FmpProviderError,
)


def _provider(handler) -> FmpMarketDataProvider:
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    return FmpMarketDataProvider(api_key="test-key-not-real", client=client)


def test_missing_api_key_raises_without_making_any_request(monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)

    def handler(request):
        raise AssertionError("must not make a request when the key is missing")

    with pytest.raises(FmpProviderError, match="FMP_API_KEY"):
        FmpMarketDataProvider(
            api_key=None, client=httpx.Client(transport=httpx.MockTransport(handler))
        )


def test_api_key_read_from_environment(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "env-key")
    seen = {}

    def handler(request):
        seen["apikey"] = dict(request.url.params)["apikey"]
        return httpx.Response(200, json=[])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    FmpMarketDataProvider(client=client).fetch_quote("NVDA")
    assert seen["apikey"] == "env-key"


# --- fetch_quote ---


def test_successful_quote_response_maps_into_quote():
    def handler(request):
        assert request.url.path.endswith("/quote")
        assert dict(request.url.params)["symbol"] == "NVDA"
        return httpx.Response(
            200,
            json=[
                {
                    "symbol": "NVDA",
                    "price": 214.72,
                    "changePercentage": -0.98225,
                    "change": -2.13,
                    "previousClose": 216.85,
                    "volume": 91591112,
                    "timestamp": 1787342400,
                }
            ],
        )

    quote = _provider(handler).fetch_quote("NVDA")
    assert quote is not None
    assert quote.entity_id == "NVDA"
    assert quote.price == 214.72
    assert quote.previous_close == 216.85
    assert quote.change_pct == -0.98225
    assert quote.quote_timestamp.year == 2026
    assert quote.source_id == FMP_SOURCE_ID
    assert quote.source_name == FMP_SOURCE_NAME


def test_quote_empty_list_returns_none_not_an_error():
    def handler(request):
        return httpx.Response(200, json=[])

    assert _provider(handler).fetch_quote("NOSYMBOL") is None


def test_quote_missing_required_field_raises():
    def handler(request):
        return httpx.Response(
            200,
            json=[
                {"symbol": "NVDA", "price": 214.72}
            ],  # no previousClose/changePercentage/timestamp
        )

    with pytest.raises(FmpProviderError, match="missing"):
        _provider(handler).fetch_quote("NVDA")


def test_quote_rate_limit_raises():
    def handler(request):
        return httpx.Response(429, text="rate limited")

    with pytest.raises(FmpProviderError, match="rate limit"):
        _provider(handler).fetch_quote("NVDA")


def test_quote_non_200_raises():
    def handler(request):
        return httpx.Response(500, text="server error")

    with pytest.raises(FmpProviderError, match="HTTP 500"):
        _provider(handler).fetch_quote("NVDA")


def test_quote_malformed_json_raises():
    def handler(request):
        return httpx.Response(200, text="not json")

    with pytest.raises(FmpProviderError, match="not valid JSON"):
        _provider(handler).fetch_quote("NVDA")


def test_quote_non_list_response_raises():
    def handler(request):
        return httpx.Response(200, json={"not": "a list"})

    with pytest.raises(FmpProviderError, match="not a list"):
        _provider(handler).fetch_quote("NVDA")


def test_quote_network_error_raises():
    def handler(request):
        raise httpx.ConnectError("connection refused")

    with pytest.raises(FmpProviderError, match="network error"):
        _provider(handler).fetch_quote("NVDA")


# --- fetch_latest_grade_change ---


def test_successful_grades_response_maps_into_grade_change():
    def handler(request):
        assert request.url.path.endswith("/grades")
        assert dict(request.url.params)["symbol"] == "NVDA"
        return httpx.Response(
            200,
            json=[
                {
                    "symbol": "NVDA",
                    "date": "2026-08-21",
                    "gradingCompany": "BMO Capital",
                    "previousGrade": "Outperform",
                    "newGrade": "Outperform",
                    "action": "maintain",
                }
            ],
        )

    grade = _provider(handler).fetch_latest_grade_change("NVDA")
    assert grade is not None
    assert grade.entity_id == "NVDA"
    assert grade.grading_firm == "BMO Capital"
    assert grade.previous_rating == "Outperform"
    assert grade.new_rating == "Outperform"
    assert grade.action == "maintain"
    assert grade.action_date.year == 2026
    assert grade.action_date.month == 8
    assert grade.action_date.day == 21
    assert grade.source_id == FMP_SOURCE_ID


def test_picks_most_recent_grade_entry_by_date_not_list_position():
    def handler(request):
        return httpx.Response(
            200,
            json=[
                {
                    "symbol": "NVDA",
                    "date": "2026-06-01",  # older, listed first
                    "gradingCompany": "Old Capital",
                    "previousGrade": "Hold",
                    "newGrade": "Sell",
                    "action": "downgrade",
                },
                {
                    "symbol": "NVDA",
                    "date": "2026-08-21",  # newer, listed second
                    "gradingCompany": "RBC Capital",
                    "previousGrade": "Hold",
                    "newGrade": "Buy",
                    "action": "upgrade",
                },
            ],
        )

    grade = _provider(handler).fetch_latest_grade_change("NVDA")
    assert grade is not None
    assert grade.grading_firm == "RBC Capital"
    assert grade.action == "upgrade"


def test_grades_empty_list_returns_none_not_an_error():
    def handler(request):
        return httpx.Response(200, json=[])

    assert _provider(handler).fetch_latest_grade_change("NOSYMBOL") is None


def test_grades_missing_action_raises():
    def handler(request):
        return httpx.Response(
            200,
            json=[
                {
                    "symbol": "NVDA",
                    "date": "2026-08-21",
                    "gradingCompany": "BMO Capital",
                }
            ],
        )

    with pytest.raises(FmpProviderError, match="action"):
        _provider(handler).fetch_latest_grade_change("NVDA")


def test_grades_rate_limit_raises():
    def handler(request):
        return httpx.Response(429, text="rate limited")

    with pytest.raises(FmpProviderError, match="rate limit"):
        _provider(handler).fetch_latest_grade_change("NVDA")
