"""Stock Opportunity Logic V2 -- backend-level integration tests: repeated
polling does not re-notify, lifecycle state survives a simulated restart,
and the lifecycle_* fields are genuinely exposed through the real
/v1/opportunities response. Uses the same httpx.MockTransport-backed FMP
provider pattern as test_live_equities.py -- zero real network calls.

logan_core/tests/test_opportunity_lifecycle.py and test_pipeline_lifecycle.py
cover the tracker's own logic and its wiring through a bare Orchestrator;
this file proves the same behavior through backend/app/logan_feed.py's real
wiring (persistence, notification eligibility, the FeedItem contract).
"""

from typing import Callable

import httpx

from backend.app.logan_feed import (
    get_alert_eligible_items,
    reset_pipeline_state,
    run_demo_feed,
)
from logan_core.contracts import LOCAL_FOUNDER_USER_ID
from logan_core.receptors.providers import FmpEarningsProvider, FmpMarketDataProvider


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
            # Stock Opportunity Logic V2.2: no profile fixture data in
            # these pre-V2.2 tests -- an honest "no profile" response.
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


def _setup(
    monkeypatch, *, earnings_by_symbol, tickers="NVDA", persist=False, tmp_path=None
):
    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", tickers)
    monkeypatch.delenv("STRATUS_LIVE_NVDA_EARNINGS", raising=False)
    monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)
    if persist:
        monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
        monkeypatch.setenv("STRATUS_STATE_DB_PATH", str(tmp_path / "state.db"))
    else:
        monkeypatch.delenv("STRATUS_PERSIST_MEMORY", raising=False)
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        _routing_earnings_provider(earnings_by_symbol),
    )
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider({}, {}),
    )
    reset_pipeline_state()


def _nvda_item(payload_items):
    return next(i for i in payload_items if i.entity_id == "NVDA")


# --- Notification suppression on repeated polling --------------------------


def test_repeated_poll_of_unchanged_live_data_is_not_alert_eligible(monkeypatch):
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})

    first = get_alert_eligible_items(LOCAL_FOUNDER_USER_ID)
    assert any(item.entity_id == "NVDA" for item in first)

    second = get_alert_eligible_items(LOCAL_FOUNDER_USER_ID)
    assert not any(item.entity_id == "NVDA" for item in second)


def test_repeated_poll_still_returns_the_opportunity_just_not_alert_eligible(
    monkeypatch,
):
    """Not equating "opportunity exists" with "send notification" -- the
    item must still be visible in /v1/opportunities on the second poll, just
    no longer notification-eligible."""
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})

    run_demo_feed(LOCAL_FOUNDER_USER_ID)
    result = run_demo_feed(LOCAL_FOUNDER_USER_ID)

    nvda = _nvda_item(result.items)
    assert nvda.is_updated is False
    assert nvda.meaningful_change_type == "none"


# --- lifecycle_* fields genuinely exposed -----------------------------------


def test_lifecycle_fields_present_on_first_poll(monkeypatch):
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})

    result = run_demo_feed(LOCAL_FOUNDER_USER_ID)
    nvda = _nvda_item(result.items)

    assert nvda.lifecycle_state == "new"
    assert nvda.is_updated is True
    assert nvda.meaningful_change_type == "new_opportunity"
    assert nvda.lifecycle_reason
    assert nvda.last_meaningful_change_at is not None
    assert nvda.thesis_age_hours == 0.0


def test_lifecycle_fields_absent_in_demo_mode_no_live_tickers(monkeypatch):
    """Backward compatibility: no live tickers configured means no
    lifecycle_tracker wired at all -- fields stay None, matching the exact
    pre-Sprint-3.6.9 contract for every existing demo-mode caller."""
    monkeypatch.delenv("STRATUS_LIVE_STOCK_TICKERS", raising=False)
    monkeypatch.delenv("STRATUS_LIVE_NVDA_EARNINGS", raising=False)
    monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)
    reset_pipeline_state()

    result = run_demo_feed(LOCAL_FOUNDER_USER_ID)
    nvda = _nvda_item(result.items)

    assert nvda.lifecycle_state is None
    assert nvda.is_updated is False
    assert nvda.meaningful_change_type is None


# --- Restart/redeploy persistence -------------------------------------------


def test_lifecycle_state_survives_a_simulated_restart(monkeypatch, tmp_path):
    _setup(
        monkeypatch,
        earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)},
        persist=True,
        tmp_path=tmp_path,
    )

    first = run_demo_feed(LOCAL_FOUNDER_USER_ID)
    assert _nvda_item(first.items).lifecycle_state == "new"

    # Simulated restart -- drops every in-process singleton; the SQLite file
    # itself is untouched, exactly what a real process exit/restart would do.
    reset_pipeline_state()

    second = run_demo_feed(LOCAL_FOUNDER_USER_ID)
    nvda = _nvda_item(second.items)
    # Must NOT become "new" again solely because process memory reset.
    assert nvda.meaningful_change_type != "new_opportunity"
    assert nvda.is_updated is False


def test_no_duplicate_notification_after_restart(monkeypatch, tmp_path):
    _setup(
        monkeypatch,
        earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)},
        persist=True,
        tmp_path=tmp_path,
    )

    first_alerts = get_alert_eligible_items(LOCAL_FOUNDER_USER_ID)
    assert any(item.entity_id == "NVDA" for item in first_alerts)

    reset_pipeline_state()  # simulated restart

    second_alerts = get_alert_eligible_items(LOCAL_FOUNDER_USER_ID)
    assert not any(item.entity_id == "NVDA" for item in second_alerts)


def test_without_persistence_restart_does_reset_lifecycle_to_new(monkeypatch):
    """The converse, proving persistence is actually doing something: with
    STRATUS_PERSIST_MEMORY off (the default), a simulated restart legitimately
    loses lifecycle history -- this is documented, expected behavior, not a
    bug, and confirms the persistence test above isn't a false positive."""
    _setup(
        monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)}
    )  # persist=False (default)

    run_demo_feed(LOCAL_FOUNDER_USER_ID)
    reset_pipeline_state()
    second = run_demo_feed(LOCAL_FOUNDER_USER_ID)

    assert _nvda_item(second.items).meaningful_change_type == "new_opportunity"
