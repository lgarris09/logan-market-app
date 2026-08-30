"""Operational Beta Live Supply V2, Block 9 -- opportunity_quality_report.py
and GET /v1/dev/opportunity-quality. Full HTTP-level mocking (no real
network), same technique as test_independent_stock_signals.py.
"""

import httpx
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.opportunity_quality_report import format_opportunity_quality_report
from logan_core.receptors.providers import FmpEarningsProvider, FmpMarketDataProvider

client = TestClient(app)


def _json_by_symbol(by_symbol: dict):
    def respond(request: httpx.Request) -> httpx.Response:
        symbol = request.url.params.get("symbol")
        return httpx.Response(200, json=by_symbol.get(symbol, []))

    return respond


def _route(handlers_by_path):
    def handler(request: httpx.Request) -> httpx.Response:
        for path, respond in handlers_by_path.items():
            if request.url.path.endswith(path):
                return respond(request)
        return httpx.Response(200, json=[])

    return handler


def _wire(monkeypatch, *, earnings, quotes, grades):
    earnings_client = httpx.Client(
        transport=httpx.MockTransport(_json_by_symbol(earnings))
    )
    monkeypatch.setattr(
        "backend.app.opportunity_quality_report.FmpEarningsProvider",
        lambda *a, **kw: FmpEarningsProvider(
            api_key="test-key-not-real", client=earnings_client
        ),
    )
    market_client = httpx.Client(
        transport=httpx.MockTransport(
            _route(
                {"/quote": _json_by_symbol(quotes), "/grades": _json_by_symbol(grades)}
            )
        )
    )
    monkeypatch.setattr(
        "backend.app.opportunity_quality_report.FmpMarketDataProvider",
        lambda *a, **kw: FmpMarketDataProvider(
            api_key="test-key-not-real", client=market_client
        ),
    )


def test_report_shows_qualified_earnings_with_real_beat_pct(monkeypatch):
    _wire(
        monkeypatch,
        earnings={
            "NVDA": [
                {
                    "symbol": "NVDA",
                    "date": "2026-08-26",
                    "epsActual": 2.0,
                    "epsEstimated": 1.76,
                }
            ]
        },
        quotes={},
        grades={},
    )
    report = format_opportunity_quality_report(["NVDA"])
    assert "NVDA" in report
    assert "Earnings — QUALIFIED" in report
    assert "% EPS beat" in report
    assert "Price — NOT QUALIFIED" in report
    assert "Analyst — NOT QUALIFIED" in report


def test_report_shows_not_qualified_with_the_real_reason(monkeypatch):
    _wire(
        monkeypatch,
        earnings={
            "NVDA": [
                {
                    "symbol": "NVDA",
                    "date": "2026-08-26",
                    "epsActual": 1.7,
                    "epsEstimated": 1.76,
                }
            ]
        },
        quotes={
            "NVDA": [
                {
                    "symbol": "NVDA",
                    "price": 111.0,
                    "previousClose": 110.0,
                    "changePercentage": 0.9,
                    "timestamp": 1798000000,
                    "volume": 1000,
                }
            ]
        },
        grades={},
    )
    report = format_opportunity_quality_report(["NVDA"])
    assert "Earnings — NOT QUALIFIED" in report
    assert "Price — NOT QUALIFIED" in report


def test_report_handles_multiple_tickers_independently(monkeypatch):
    _wire(
        monkeypatch,
        earnings={
            "NVDA": [
                {
                    "symbol": "NVDA",
                    "date": "2026-08-26",
                    "epsActual": 2.0,
                    "epsEstimated": 1.76,
                }
            ]
        },
        quotes={},
        grades={},
    )
    report = format_opportunity_quality_report(["NVDA", "TSLA"])
    assert report.count("Earnings") == 2
    lines = report.splitlines()
    assert "NVDA" in lines
    assert "TSLA" in lines


def test_route_defaults_to_the_configured_live_ticker_universe(monkeypatch):
    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", "NVDA")
    _wire(monkeypatch, earnings={}, quotes={}, grades={})
    response = client.get("/v1/dev/opportunity-quality")
    assert response.status_code == 200
    assert "NVDA" in response.json()["report"]


def test_route_accepts_an_explicit_ticker_list(monkeypatch):
    _wire(monkeypatch, earnings={}, quotes={}, grades={})
    response = client.get(
        "/v1/dev/opportunity-quality", params={"tickers": "aapl,msft"}
    )
    assert response.status_code == 200
    body = response.json()["report"]
    assert "AAPL" in body
    assert "MSFT" in body


def test_route_never_leaks_a_key(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "totally-real-secret-key-value")
    _wire(monkeypatch, earnings={}, quotes={}, grades={})
    response = client.get("/v1/dev/opportunity-quality", params={"tickers": "NVDA"})
    assert "totally-real-secret-key-value" not in response.text
