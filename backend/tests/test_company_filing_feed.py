"""ADR-084 -- the SEC 8-K catalyst path end to end through the feed, with the
EPS comparability gate on. Every provider is mocked; no network call is made.
"""

from datetime import datetime, timedelta, timezone

import httpx

import backend.app.logan_feed as logan_feed
from backend.app.logan_feed import reset_pipeline_state, run_demo_feed
from logan_core.receptors.providers import (
    FmpEarningsProvider,
    FmpMarketDataProvider,
    sec_edgar,
)
from logan_core.receptors.providers.sec_edgar import SecEdgarFilingsProvider

EPS_BEAT = {
    "symbol": "NVDA",
    "date": "2026-05-20",
    "epsActual": 1.87,
    "epsEstimated": 1.76,
}


def _earnings(entries) -> FmpEarningsProvider:
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=entries))
    )
    return FmpEarningsProvider(api_key="test-key-not-real", client=client)


def _market() -> FmpMarketDataProvider:
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=[]))
    )
    return FmpMarketDataProvider(api_key="test-key-not-real", client=client)


def _sec_payload(items: str, form: str = "8-K", age_hours: float = 20.0) -> dict:
    accepted = datetime.now(timezone.utc) - timedelta(hours=age_hours)
    return {
        "tickers": ["NVDA"],
        "filings": {
            "recent": {
                "form": [form],
                "accessionNumber": ["0001045810-26-000101"],
                "acceptanceDateTime": [accepted.strftime("%Y-%m-%dT%H:%M:%S.000Z")],
                "filingDate": [accepted.strftime("%Y-%m-%d")],
                "reportDate": [accepted.strftime("%Y-%m-%d")],
                "items": [items],
                "primaryDocument": ["nvda-8k.htm"],
            }
        },
    }


def _setup(monkeypatch, *, sec_payload, catalysts=True, user_agent=True):
    calls: list[httpx.Request] = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=sec_payload)

    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", "NVDA")
    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "live")
    monkeypatch.setenv("STRATUS_EPS_COMPARABILITY_GATE", "true")
    if catalysts:
        monkeypatch.setenv("STRATUS_SEC_FILING_CATALYSTS", "true")
    else:
        monkeypatch.delenv("STRATUS_SEC_FILING_CATALYSTS", raising=False)
    if user_agent:
        monkeypatch.setenv(
            "STRATUS_SEC_USER_AGENT",
            "STRATUS test / Example LLC; contact=ops@example.invalid",
        )
    else:
        monkeypatch.delenv("STRATUS_SEC_USER_AGENT", raising=False)
    monkeypatch.setitem(sec_edgar.CIK_BY_TICKER, "NVDA", "0001045810")
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda *a, **kw: _earnings([EPS_BEAT]),
    )
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider", lambda *a, **kw: _market()
    )
    real = SecEdgarFilingsProvider

    def factory(*, user_agent):
        return real(
            user_agent=user_agent,
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )

    monkeypatch.setattr("backend.app.logan_feed.SecEdgarFilingsProvider", factory)
    reset_pipeline_state()
    return calls


def test_gate_alone_leaves_the_feed_empty(monkeypatch):
    """The baseline this path exists to fix: an EPS beat the provider cannot
    substantiate, nothing else qualifying, catalysts off."""
    calls = _setup(monkeypatch, sec_payload=_sec_payload("2.02,9.01"), catalysts=False)
    assert run_demo_feed().items == []
    assert calls == []
    reset_pipeline_state()


def test_results_filing_surfaces_as_a_truthful_earnings_result(monkeypatch):
    calls = _setup(monkeypatch, sec_payload=_sec_payload("2.02,9.01"))
    items = run_demo_feed().items
    assert [i.entity_id for i in items] == ["NVDA"]
    item = items[0]
    assert item.signal_type == "company_filing"
    assert item.signal_families == ["earnings_result"]
    headline = item.delivered_item.headline
    assert "8-K Item 2.02: financial results furnished, filed" in headline
    for claim in ("beat", "miss", "consensus", "EPS of", "%"):
        assert claim not in headline
    assert len(calls) == 1
    assert (
        calls[0].headers["user-agent"]
        == "STRATUS test / Example LLC; contact=ops@example.invalid"
    )
    reset_pipeline_state()


def test_filing_item_has_evidence_label_freshness_and_lifecycle(monkeypatch):
    _setup(monkeypatch, sec_payload=_sec_payload("5.02"))
    item = run_demo_feed().items[0]
    assert item.signal_families == ["company_event"]
    assert item.freshness_state == "FRESH"
    # One authoritative origin, nothing independent: Supported, not Strong.
    assert item.delivered_item.evidence_label == "Supported evidence"
    assert "single_origin" in item.delivered_item.evidence_conditions
    assert "freshness_established" in item.delivered_item.evidence_conditions
    assert item.opportunity_revision == 1
    assert item.lifecycle_state is not None
    reset_pipeline_state()


def test_repolling_the_same_filing_never_duplicates_it(monkeypatch):
    calls = _setup(monkeypatch, sec_payload=_sec_payload("2.02"))
    first = run_demo_feed().items
    second = run_demo_feed().items
    assert len(first) == len(second) == 1
    assert first[0].opportunity_revision == second[0].opportunity_revision == 1
    assert len(calls) == 1  # the index is cached, not refetched every poll
    reset_pipeline_state()


def test_ungoverned_filing_does_not_surface(monkeypatch):
    _setup(monkeypatch, sec_payload=_sec_payload("7.01,8.01,9.01"))
    assert run_demo_feed().items == []
    reset_pipeline_state()


def test_financing_filing_does_not_surface(monkeypatch):
    _setup(monkeypatch, sec_payload=_sec_payload("1.01,2.03,9.01"))
    assert run_demo_feed().items == []
    reset_pipeline_state()


def test_old_filing_does_not_start_an_opportunity(monkeypatch):
    _setup(monkeypatch, sec_payload=_sec_payload("2.02", age_hours=24 * 20))
    assert run_demo_feed().items == []
    reset_pipeline_state()


def test_no_user_agent_means_no_request_and_no_item(monkeypatch):
    calls = _setup(monkeypatch, sec_payload=_sec_payload("2.02"), user_agent=False)
    assert run_demo_feed().items == []
    assert calls == []
    reset_pipeline_state()


def test_another_issuers_payload_is_refused(monkeypatch):
    payload = _sec_payload("2.02")
    payload["tickers"] = ["AMD"]
    _setup(monkeypatch, sec_payload=payload)
    assert run_demo_feed().items == []
    reset_pipeline_state()


def test_provider_outage_does_not_break_the_feed(monkeypatch):
    _setup(monkeypatch, sec_payload=_sec_payload("2.02"))

    def failing(*, user_agent):
        return SecEdgarFilingsProvider(
            user_agent=user_agent,
            client=httpx.Client(
                transport=httpx.MockTransport(lambda r: httpx.Response(503, text="x"))
            ),
        )

    monkeypatch.setattr("backend.app.logan_feed.SecEdgarFilingsProvider", failing)
    reset_pipeline_state()
    assert run_demo_feed().items == []
    assert logan_feed.sec_filings_last_successful_fetch_age_seconds("NVDA") is None
    reset_pipeline_state()
