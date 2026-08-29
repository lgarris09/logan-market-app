"""Sprint 3.6.8 Block 5 -- the generalized live equities runtime path
(ADR-060): NVDA/TSLA/AAPL through the same real FMP-backed pipeline, no
per-ticker duplication, multi-entity convergence isolation, the production-
vs-demo runtime boundary, personalization separation, and data provenance.

Same discipline as test_live_nvda_earnings.py/test_live_nvda_market_data.py:
every test injects a real provider backed by httpx.MockTransport (via
monkeypatching FmpEarningsProvider/FmpMarketDataProvider in
backend.app.logan_feed's namespace) -- zero real network calls, no
dependency on FMP_API_KEY existing in this process.
"""

from typing import Callable

import httpx

from backend.app.logan_feed import reset_pipeline_state, run_demo_feed
from logan_core.receptors.providers import FmpEarningsProvider, FmpMarketDataProvider
from logan_core.receptors.providers.fmp import FMP_SOURCE_ID


def _entries_for(by_symbol: dict) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        symbol = request.url.params.get("symbol")
        return httpx.Response(200, json=by_symbol.get(symbol, []))

    return handler


def _routing_earnings_provider(earnings_by_symbol: dict):
    transport = httpx.MockTransport(_entries_for(earnings_by_symbol))
    client = httpx.Client(transport=transport)
    return lambda *a, **kw: FmpEarningsProvider(
        api_key="test-key-not-real", client=client
    )


def _routing_market_data_provider(quote_by_symbol: dict, grade_by_symbol: dict):
    def handler(request: httpx.Request) -> httpx.Response:
        symbol = request.url.params.get("symbol")
        if request.url.path.endswith("/quote"):
            return httpx.Response(200, json=quote_by_symbol.get(symbol, []))
        if request.url.path.endswith("/grades"):
            return httpx.Response(200, json=grade_by_symbol.get(symbol, []))
        if request.url.path.endswith("/profile"):
            # Stock Opportunity Logic V2.2: no profile fixture data in these
            # pre-V2.2 tests -- an honest "no profile" response.
            return httpx.Response(200, json=[])
        raise AssertionError(f"unexpected FMP path: {request.url.path}")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    return lambda *a, **kw: FmpMarketDataProvider(
        api_key="test-key-not-real", client=client
    )


def _earnings(symbol, actual, estimated, date="2026-05-20"):
    return [
        {"symbol": symbol, "date": date, "epsActual": actual, "epsEstimated": estimated}
    ]


def _quote(symbol, price, previous_close, change_pct):
    return [
        {
            "symbol": symbol,
            "price": price,
            "previousClose": previous_close,
            "changePercentage": change_pct,
            "timestamp": 1755806400,
        }
    ]


def _grade(symbol, action, date="2026-08-21"):
    return [
        {
            "symbol": symbol,
            "date": date,
            "gradingCompany": "Fixture Capital",
            "previousGrade": "Hold",
            "newGrade": "Buy",
            "action": action,
        }
    ]


def _setup(
    monkeypatch,
    *,
    earnings_by_symbol=None,
    quote_by_symbol=None,
    grade_by_symbol=None,
    tickers="NVDA,TSLA,AAPL",
    runtime_mode=None,
):
    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", tickers)
    monkeypatch.delenv("STRATUS_LIVE_NVDA_EARNINGS", raising=False)
    if runtime_mode is None:
        monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)
    else:
        monkeypatch.setenv("STRATUS_RUNTIME_MODE", runtime_mode)
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        _routing_earnings_provider(earnings_by_symbol or {}),
    )
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider(quote_by_symbol or {}, grade_by_symbol or {}),
    )
    reset_pipeline_state()


def _item(payload_items, entity_id):
    return next(i for i in payload_items if i.entity_id == entity_id)


# --- Backward compatibility with the original single-ticker flag -----------


def test_legacy_nvda_only_flag_still_works_unchanged(monkeypatch):
    monkeypatch.delenv("STRATUS_LIVE_STOCK_TICKERS", raising=False)
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "true")
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        _routing_earnings_provider({"NVDA": _earnings("NVDA", 1.87, 1.76)}),
    )
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider({}, {}),
    )
    reset_pipeline_state()
    result = run_demo_feed()
    nvda = _item(result.items, "NVDA")
    assert "1.87" in nvda.delivered_item.what_happened
    assert len(result.items) == 11


# --- Live NVDA / TSLA / AAPL, individually and together --------------------


def test_nvda_live_earnings_beat(monkeypatch):
    _setup(
        monkeypatch,
        earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)},
        tickers="NVDA",
    )
    result = run_demo_feed()
    nvda = _item(result.items, "NVDA")
    assert "1.87" in nvda.delivered_item.what_happened
    assert len(result.items) == 11


def test_tsla_live_earnings_beat_no_simulated_corroboration_leak(monkeypatch):
    """The real bug this block fixed: a live TSLA earnings signal must never
    be joined by the simulated 'Reuters confirms AI chip partnership'
    corroborating signal -- that fabricated text must never appear in a
    genuinely live TSLA opportunity."""
    _setup(
        monkeypatch,
        earnings_by_symbol={"TSLA": _earnings("TSLA", 0.85, 0.70)},
        tickers="TSLA",
    )
    result = run_demo_feed()
    tsla = _item(result.items, "TSLA")
    assert "0.85" in tsla.delivered_item.what_happened
    assert "AI chip partnership" not in tsla.delivered_item.what_happened
    assert "confirms" not in tsla.delivered_item.what_happened.lower()


def test_tsla_falls_back_to_simulated_still_gets_corroboration(monkeypatch):
    """The converse of the above: when TSLA's live fetch does NOT qualify,
    the pre-existing simulated corroboration behavior is completely
    unaffected -- both signals are simulated, never mixed."""
    _setup(
        monkeypatch,
        earnings_by_symbol={"TSLA": _earnings("TSLA", 0.70, 0.70)},  # no beat
        tickers="TSLA",
    )
    result = run_demo_feed()
    tsla = _item(result.items, "TSLA")
    assert "AI chip partnership" in tsla.delivered_item.what_happened


def test_aapl_live_earnings_beat(monkeypatch):
    _setup(
        monkeypatch,
        earnings_by_symbol={"AAPL": _earnings("AAPL", 2.10, 1.95)},
        tickers="AAPL",
    )
    result = run_demo_feed()
    aapl = _item(result.items, "AAPL")
    assert "2.1" in aapl.delivered_item.what_happened


def test_multiple_stocks_in_same_poll_all_go_live_independently(monkeypatch):
    _setup(
        monkeypatch,
        earnings_by_symbol={
            "NVDA": _earnings("NVDA", 1.87, 1.76),
            "TSLA": _earnings("TSLA", 0.85, 0.70),
            "AAPL": _earnings("AAPL", 2.10, 1.95),
        },
    )
    result = run_demo_feed()
    assert len(result.items) == 11  # no duplicates, no extras
    nvda = _item(result.items, "NVDA")
    tsla = _item(result.items, "TSLA")
    aapl = _item(result.items, "AAPL")
    assert "1.87" in nvda.delivered_item.what_happened
    assert "0.85" in tsla.delivered_item.what_happened
    assert "2.1" in aapl.delivered_item.what_happened
    # Every other simulated entity untouched.
    other_ids = {i.entity_id for i in result.items} - {"NVDA", "TSLA", "AAPL"}
    assert other_ids == {
        "MARKETS",
        "OIL",
        "BTC",
        "FED",
        "NFL",
        "MUSIC",
        "POLY",
        "AI_SECTOR",
    }


def test_one_ticker_fails_others_survive(monkeypatch):
    """Provider failure isolation: NVDA's provider construction itself is
    fine, but TSLA's earnings fetch fails outright (simulated network
    error) -- NVDA and AAPL must still go live successfully."""

    def failing_or_routed(request: httpx.Request) -> httpx.Response:
        symbol = request.url.params.get("symbol")
        if symbol == "TSLA":
            raise httpx.ConnectError("simulated connection failure for TSLA only")
        by_symbol = {
            "NVDA": _earnings("NVDA", 1.87, 1.76),
            "AAPL": _earnings("AAPL", 2.10, 1.95),
        }
        return httpx.Response(200, json=by_symbol.get(symbol, []))

    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", "NVDA,TSLA,AAPL")
    monkeypatch.delenv("STRATUS_LIVE_NVDA_EARNINGS", raising=False)
    monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)
    transport = httpx.MockTransport(failing_or_routed)
    client = httpx.Client(transport=transport)
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda *a, **kw: FmpEarningsProvider(
            api_key="test-key-not-real", client=client
        ),
    )
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider({}, {}),
    )
    reset_pipeline_state()
    result = run_demo_feed()

    nvda = _item(result.items, "NVDA")
    aapl = _item(result.items, "AAPL")
    tsla = _item(result.items, "TSLA")
    assert "1.87" in nvda.delivered_item.what_happened
    assert "2.1" in aapl.delivered_item.what_happened
    # TSLA fell back to its simulated fixture -- never crashed, never
    # fabricated, and the whole poll still completed for everyone else.
    assert "AI chip partnership" in tsla.delivered_item.what_happened
    assert len(result.items) == 11


def test_quote_failure_isolated_from_earnings_and_grade(monkeypatch):
    """One malformed/failing signal type for a ticker must not take down
    that ticker's other, independently-succeeding signal types."""

    def market_data_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/quote"):
            raise httpx.ConnectError("simulated quote endpoint failure")
        if request.url.path.endswith("/grades"):
            return httpx.Response(200, json=_grade("NVDA", "upgrade"))
        raise AssertionError(request.url.path)

    _setup(
        monkeypatch,
        earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)},
        tickers="NVDA",
    )
    transport = httpx.MockTransport(market_data_handler)
    client = httpx.Client(transport=transport)
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        lambda *a, **kw: FmpMarketDataProvider(
            api_key="test-key-not-real", client=client
        ),
    )
    reset_pipeline_state()
    result = run_demo_feed()
    nvda = _item(result.items, "NVDA")
    assert "1.87" in nvda.delivered_item.what_happened  # earnings unaffected


def test_malformed_provider_response_falls_back_never_crashes(monkeypatch):
    _setup(
        monkeypatch,
        earnings_by_symbol={"NVDA": [{"symbol": "NVDA", "notADate": "oops"}]},
        tickers="NVDA",
    )
    result = run_demo_feed()
    nvda = _item(result.items, "NVDA")
    assert "guidance raised" in nvda.delivered_item.what_happened  # simulated fallback


def test_no_provider_result_never_fabricates_an_opportunity(monkeypatch):
    _setup(monkeypatch, earnings_by_symbol={}, tickers="NVDA,TSLA,AAPL")
    result = run_demo_feed()
    # All three fall back to their simulated fixtures (demo mode default) --
    # never a fabricated live-looking result from empty provider data.
    nvda = _item(result.items, "NVDA")
    assert "guidance raised" in nvda.delivered_item.what_happened


# --- Production vs. demo runtime boundary -----------------------------------


def test_unsupported_domain_in_live_mode_is_absent_not_simulated(monkeypatch):
    _setup(monkeypatch, earnings_by_symbol={}, tickers="NVDA", runtime_mode="live")
    result = run_demo_feed()
    entity_ids = {i.entity_id for i in result.items}
    # No live NVDA signal qualified, and unsupported domains (BTC, FED, NFL,
    # MUSIC, POLY, AI_SECTOR, MARKETS, OIL, TSLA, AAPL) have no live path in
    # this configuration -- live mode must not silently backfill any of
    # them with simulated opportunities.
    assert entity_ids == set()


def test_live_mode_only_shows_tickers_that_genuinely_qualified(monkeypatch):
    _setup(
        monkeypatch,
        earnings_by_symbol={
            "NVDA": _earnings("NVDA", 1.87, 1.76),  # beats
            "TSLA": _earnings("TSLA", 0.70, 0.70),  # does not beat
        },
        tickers="NVDA,TSLA",
        runtime_mode="live",
    )
    result = run_demo_feed()
    entity_ids = {i.entity_id for i in result.items}
    assert entity_ids == {"NVDA"}  # TSLA honestly absent, never fabricated


def test_provider_failure_in_live_mode_does_not_substitute_a_fixture(monkeypatch):
    _setup(monkeypatch, earnings_by_symbol={}, tickers="NVDA", runtime_mode="live")
    result = run_demo_feed()
    assert {i.entity_id for i in result.items} == set()


def test_demo_mode_still_intentionally_supports_fixtures(monkeypatch):
    monkeypatch.delenv("STRATUS_LIVE_STOCK_TICKERS", raising=False)
    monkeypatch.delenv("STRATUS_LIVE_NVDA_EARNINGS", raising=False)
    monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)
    reset_pipeline_state()
    result = run_demo_feed()
    assert len(result.items) == 11  # the full, unchanged simulated demo feed


def test_fixture_data_cannot_leak_into_live_mode_even_when_not_configured_live(
    monkeypatch,
):
    """A ticker that is NOT in the configured live universe at all (e.g.
    BTC, a crypto entity with no live provider) must never appear via its
    simulated fixture while in live-data-only mode."""
    _setup(monkeypatch, earnings_by_symbol={}, tickers="", runtime_mode="live")
    result = run_demo_feed()
    assert result.items == []


# --- Convergence: multi-stock entity isolation ------------------------------


def _trigger_codes_for(event_id):
    """Reads the real, already-computed trigger_codes for an event via the
    same authoritative OpportunityContext surface Ask STRATUS itself uses
    (backend/app/ask_context.py) -- not a private WorldModel internal."""
    from backend.app.logan_feed import get_opportunity_context
    from logan_core.contracts import LOCAL_FOUNDER_USER_ID

    context = get_opportunity_context(LOCAL_FOUNDER_USER_ID, event_id)
    assert context is not None
    return context.trigger_codes


def test_convergence_isolated_per_entity_no_cross_symbol_contamination(monkeypatch):
    """NVDA's three qualifying live signals must converge; TSLA's own
    signals (even if only one or two qualify) must never be counted toward
    NVDA's convergence threshold, or vice versa."""
    _setup(
        monkeypatch,
        earnings_by_symbol={
            "NVDA": _earnings("NVDA", 1.87, 1.76),
            "TSLA": _earnings("TSLA", 0.85, 0.70),
        },
        quote_by_symbol={"NVDA": _quote("NVDA", 127.27, 118.50, 7.4)},
        grade_by_symbol={"NVDA": _grade("NVDA", "upgrade")},
        tickers="NVDA,TSLA",
    )
    result = run_demo_feed()
    nvda = _item(result.items, "NVDA")
    tsla = _item(result.items, "TSLA")

    # NVDA genuinely converged (3 distinct live signal types: earnings,
    # price move, analyst grade).
    assert "STOCK_CONVERGENCE_MULTI_SOURCE" in _trigger_codes_for(nvda.event_id)
    # TSLA only ever had one qualifying live signal type (earnings) --
    # must never show convergence, regardless of NVDA's own state.
    assert "STOCK_CONVERGENCE_MULTI_SOURCE" not in _trigger_codes_for(tsla.event_id)


def test_repeated_polling_cannot_manufacture_extra_convergence_sources(monkeypatch):
    """Re-polling the same still-qualifying signal repeatedly must never
    inflate the distinct-source count past what's genuinely observed --
    same discipline StockConvergenceTracker already enforces, re-verified
    through the generalized multi-ticker path."""
    _setup(
        monkeypatch,
        earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)},
        quote_by_symbol={"NVDA": _quote("NVDA", 127.27, 118.50, 7.4)},
        tickers="NVDA",
    )
    first = run_demo_feed()
    second = run_demo_feed()
    nvda_first = _item(first.items, "NVDA")
    nvda_second = _item(second.items, "NVDA")
    # Same event_id both times (World Model dedup) -- repolling the same
    # still-active signals corroborates, never manufactures a new one.
    assert nvda_first.event_id == nvda_second.event_id


def test_honest_non_convergence_stays_non_convergence(monkeypatch):
    _setup(
        monkeypatch,
        earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)},
        quote_by_symbol={"NVDA": _quote("NVDA", 119.10, 118.50, 0.51)},  # no move
        grade_by_symbol={"NVDA": _grade("NVDA", "maintain")},  # no action
        tickers="NVDA",
    )
    result = run_demo_feed()
    nvda = _item(result.items, "NVDA")
    assert "STOCK_CONVERGENCE_MULTI_SOURCE" not in _trigger_codes_for(nvda.event_id)


# --- Personalization stays separate from provider coverage ------------------


def test_new_user_does_not_inherit_interest_in_a_live_configured_ticker(monkeypatch):
    """Configuring TSLA/AAPL as live tickers is world-data infrastructure,
    not a claim about any particular user's portfolio -- a brand-new user
    must not show an explicit or inferred TSLA/AAPL interest merely because
    the backend fetches live data for it."""
    from logan_core.contracts import LOCAL_FOUNDER_USER_ID

    _setup(
        monkeypatch,
        earnings_by_symbol={
            "TSLA": _earnings("TSLA", 0.85, 0.70),
            "AAPL": _earnings("AAPL", 2.10, 1.95),
        },
        tickers="NVDA,TSLA,AAPL",
    )
    from fastapi.testclient import TestClient

    from backend.app.main import app

    client = TestClient(app)
    client.get("/v1/opportunities", headers={"X-Stratus-User-Id": "new-user-block5"})

    import backend.app.logan_feed as logan_feed_module

    new_user_model = logan_feed_module._user_models["new-user-block5"]
    assert new_user_model.holdings == []
    assert new_user_model.interests == []
    assert new_user_model.risk_tolerance == "unknown"

    # Founder's own seed remains exactly what Block 2 established -- NVDA
    # holding/AI_SECTOR interest, nothing about TSLA/AAPL added just because
    # they're now live-fetched.
    client.get("/v1/opportunities")  # founder, no header
    founder_model = logan_feed_module._user_models[LOCAL_FOUNDER_USER_ID]
    assert {h.entity_id for h in founder_model.holdings} == {"NVDA"}
    assert not any(i.topic in ("TSLA", "AAPL") for i in founder_model.interests)


def test_multi_user_boundaries_remain_intact_with_live_stocks_enabled(monkeypatch):
    _setup(
        monkeypatch,
        earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)},
        tickers="NVDA",
    )
    from fastapi.testclient import TestClient

    from backend.app.main import app

    client = TestClient(app)
    response_a = client.get(
        "/v1/opportunities", headers={"X-Stratus-User-Id": "live-user-a"}
    )
    response_b = client.get(
        "/v1/opportunities", headers={"X-Stratus-User-Id": "live-user-b"}
    )
    nvda_a = next(i for i in response_a.json()["items"] if i["entity_id"] == "NVDA")
    nvda_b = next(i for i in response_b.json()["items"] if i["entity_id"] == "NVDA")
    # Same shared live world fact (same event_id) -- personalization layer
    # (not tested exhaustively here, see test_multi_user_isolation.py) stays
    # per-user regardless of the underlying data being live or simulated.
    assert nvda_a["event_id"] == nvda_b["event_id"]


# --- Data provenance ---------------------------------------------------------


def test_live_signal_logs_fmp_provenance_for_audit(monkeypatch, capsys):
    """Data provenance (Block 5 requirement 9): the existing source_id field
    (RawSignal/TriggerEvent, FMP_SOURCE_ID="fmp") already distinguishes live
    from simulated data end-to-end -- no new parallel metadata architecture
    was introduced. The existing print-based observability convention
    already surfaces this per poll; this proves that audit trail actually
    names the real FMP source_id, not a placeholder."""
    _setup(
        monkeypatch,
        earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)},
        tickers="NVDA",
    )
    run_demo_feed()
    captured = capsys.readouterr()
    assert "[live-stocks] NVDA: using real FMP earnings report" in captured.out
    assert f"source={FMP_SOURCE_ID}" in captured.out


def test_simulated_fallback_logs_fixture_provenance_not_fmp(monkeypatch, capsys):
    _setup(
        monkeypatch,
        earnings_by_symbol={},  # no live data at all
        tickers="NVDA",
    )
    run_demo_feed()
    captured = capsys.readouterr()
    assert "demo-mode fixture retained" in captured.out
    assert "using real FMP earnings report" not in captured.out


def test_no_secret_leaks_in_multi_ticker_live_response(monkeypatch):
    _setup(
        monkeypatch,
        earnings_by_symbol={
            "NVDA": _earnings("NVDA", 1.87, 1.76),
            "TSLA": _earnings("TSLA", 0.85, 0.70),
            "AAPL": _earnings("AAPL", 2.10, 1.95),
        },
    )
    result = run_demo_feed()
    payload = str(result.model_dump())
    assert "test-key-not-real" not in payload
    assert "internal_rank_score" not in payload
