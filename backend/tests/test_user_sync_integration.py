"""Stock Opportunity Logic V2.1 (User Sync Gap) -- backend-level integration
tests: real interaction recording advances seen/opened pointers, real
notification dispatch advances the notified pointer, a GET alone never
advances anything, and both global revisions and per-user knowledge survive
a simulated restart. Mirrors test_lifecycle_integration.py's own
httpx.MockTransport-backed FMP provider pattern -- zero real network calls.

logan_core/tests/test_user_sync.py covers the pure tracker/compute_user_sync_
delta logic directly; this file proves the same behavior through backend/
app/logan_feed.py's and notifications.py's real wiring.
"""

from typing import Callable
from uuid import uuid4

import httpx

from backend.app.logan_feed import (
    get_alert_eligible_items,
    record_interaction,
    reset_pipeline_state,
    run_demo_feed,
)
from backend.app.models import RegisterPushTokenRequest
from backend.app.notifications import (
    dispatch_eligible_notifications,
    register_token,
    reset_notification_state,
)
from logan_core.contracts import LOCAL_FOUNDER_USER_ID
from logan_core.receptors.providers import FmpEarningsProvider, FmpMarketDataProvider
from logan_core.receptors.providers.fmp import reset_fmp_cache


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


def _grades(symbol, action, date="2026-08-20"):
    return [{"symbol": symbol, "date": date, "action": action}]


def _setup(
    monkeypatch,
    *,
    earnings_by_symbol,
    grade_by_symbol=None,
    tickers="NVDA",
    persist=False,
    tmp_path=None,
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
        _routing_market_data_provider({}, grade_by_symbol or {}),
    )
    reset_pipeline_state()
    reset_notification_state()


def _nvda_item(payload_items):
    return next(i for i in payload_items if i.entity_id == "NVDA")


# --- API fetch alone never advances seen ------------------------------------


def test_repeated_feed_fetches_never_advance_seen_state(monkeypatch):
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})

    first = _nvda_item(run_demo_feed(LOCAL_FOUNDER_USER_ID).items)
    assert first.opportunity_revision == 1
    assert first.user_sync_status == "NEW_TO_USER"

    # Fetching again (and again) must never itself mark it seen.
    for _ in range(3):
        again = _nvda_item(run_demo_feed(LOCAL_FOUNDER_USER_ID).items)
        assert again.user_sync_status == "NEW_TO_USER"


# --- Real interaction advances seen/opened ----------------------------------


def test_impression_interaction_advances_seen_but_not_opened(monkeypatch):
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})
    run_demo_feed(LOCAL_FOUNDER_USER_ID)  # establishes revision 1

    record_interaction(
        user_id=LOCAL_FOUNDER_USER_ID,
        event_id=uuid4(),
        entity_id="NVDA",
        domain="stocks",
        interaction_type="impression",
    )

    item = _nvda_item(run_demo_feed(LOCAL_FOUNDER_USER_ID).items)
    assert item.user_sync_status == "UP_TO_DATE"


def test_view_interaction_advances_both_seen_and_opened(monkeypatch):
    """No direct public getter for last_opened_revision exists (by design --
    it's internal knowledge-store state), so this proves the effect the
    product cares about: a real card-open ("view") produces the same
    UP_TO_DATE result as an impression, through the identical seen-pointer
    path, and doesn't error touching the opened pointer too.
    """
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})
    run_demo_feed(LOCAL_FOUNDER_USER_ID)

    record_interaction(
        user_id=LOCAL_FOUNDER_USER_ID,
        event_id=uuid4(),
        entity_id="NVDA",
        domain="stocks",
        interaction_type="view",
        duration_ms=9000,
    )

    item = _nvda_item(run_demo_feed(LOCAL_FOUNDER_USER_ID).items)
    assert item.user_sync_status == "UP_TO_DATE"


# --- Notified != seen --------------------------------------------------------


def test_notified_but_not_opened_reports_notified_but_unseen(monkeypatch):
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})
    register_token(
        LOCAL_FOUNDER_USER_ID,
        RegisterPushTokenRequest(expo_push_token="ExponentPushToken[sync-test]"),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": []})

    dispatched = dispatch_eligible_notifications(
        httpx.Client(transport=httpx.MockTransport(handler))
    )
    # Several simulated demo entities are alert-eligible alongside NVDA on a
    # first poll (unrelated to this test) -- what matters here is that a
    # real dispatch happened at all.
    assert dispatched >= 1

    item = _nvda_item(run_demo_feed(LOCAL_FOUNDER_USER_ID).items)
    assert item.user_sync_status == "NOTIFIED_BUT_UNSEEN"

    # Now the user actually opens it -- the pointer must clear the notified-
    # but-unseen state, without needing any second notification.
    record_interaction(
        user_id=LOCAL_FOUNDER_USER_ID,
        event_id=uuid4(),
        entity_id="NVDA",
        domain="stocks",
        interaction_type="view",
        duration_ms=9000,
    )
    item_after_open = _nvda_item(run_demo_feed(LOCAL_FOUNDER_USER_ID).items)
    assert item_after_open.user_sync_status == "UP_TO_DATE"


def test_eligibility_alone_without_a_real_dispatch_never_advances_notified(
    monkeypatch,
):
    """get_alert_eligible_items() only computes eligibility -- it must never
    itself count as "notified" (only notifications.dispatch_eligible_
    notifications' real Expo send may advance last_notified_revision).
    """
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})

    eligible = get_alert_eligible_items(LOCAL_FOUNDER_USER_ID)
    assert any(item.entity_id == "NVDA" for item in eligible)

    item = _nvda_item(run_demo_feed(LOCAL_FOUNDER_USER_ID).items)
    assert item.user_sync_status == "NEW_TO_USER"  # not NOTIFIED_BUT_UNSEEN


# --- New meaningful change after the user has seen the prior revision ------


def test_new_change_after_seen_reports_updated_since_seen(monkeypatch):
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})
    run_demo_feed(LOCAL_FOUNDER_USER_ID)  # revision 1
    record_interaction(
        user_id=LOCAL_FOUNDER_USER_ID,
        event_id=uuid4(),
        entity_id="NVDA",
        domain="stocks",
        interaction_type="view",
        duration_ms=9000,
    )
    seen_item = _nvda_item(run_demo_feed(LOCAL_FOUNDER_USER_ID).items)
    assert seen_item.user_sync_status == "UP_TO_DATE"
    assert seen_item.opportunity_revision == 1

    # Without resetting pipeline state (same process, same tracker instance),
    # add a live analyst-grade provider so a *new* signal_type fires on the
    # next poll -- a real, additive world-fact change (new_signal_appeared).
    # reset_fmp_cache() is required here (not just a fresh provider instance)
    # because FmpMarketDataProvider defaults to a shared, process-lifetime
    # TTL cache (receptors/providers/fmp.py's _shared_fmp_cache) -- the first
    # "no grade" result for NVDA would otherwise still be served from cache.
    reset_fmp_cache()
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider({}, {"NVDA": _grades("NVDA", "upgrade")}),
    )
    updated_item = _nvda_item(run_demo_feed(LOCAL_FOUNDER_USER_ID).items)
    assert updated_item.opportunity_revision == 2
    assert updated_item.user_sync_status == "UPDATED_SINCE_SEEN"


# --- Restart/redeploy persistence -------------------------------------------


def test_revisions_and_user_knowledge_survive_a_simulated_restart(
    monkeypatch, tmp_path
):
    _setup(
        monkeypatch,
        earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)},
        persist=True,
        tmp_path=tmp_path,
    )

    run_demo_feed(LOCAL_FOUNDER_USER_ID)
    record_interaction(
        user_id=LOCAL_FOUNDER_USER_ID,
        event_id=uuid4(),
        entity_id="NVDA",
        domain="stocks",
        interaction_type="view",
        duration_ms=9000,
    )
    before = _nvda_item(run_demo_feed(LOCAL_FOUNDER_USER_ID).items)
    assert before.opportunity_revision == 1
    assert before.user_sync_status == "UP_TO_DATE"

    # Simulated restart -- drops every in-process singleton; the SQLite
    # files themselves are untouched.
    reset_pipeline_state()

    after = _nvda_item(run_demo_feed(LOCAL_FOUNDER_USER_ID).items)
    # Revision must not reset to a fresh "1 == brand new" story, and this
    # user's own seen pointer must not have been forgotten either.
    assert after.opportunity_revision == before.opportunity_revision
    assert after.user_sync_status == "UP_TO_DATE"


def test_without_persistence_restart_does_lose_user_knowledge(monkeypatch):
    """The converse, proving persistence is actually doing something: with
    STRATUS_PERSIST_MEMORY off, a simulated restart legitimately forgets
    this user's seen pointer, so the (freshly re-tracked) opportunity again
    reports NEW_TO_USER."""
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})

    run_demo_feed(LOCAL_FOUNDER_USER_ID)
    record_interaction(
        user_id=LOCAL_FOUNDER_USER_ID,
        event_id=uuid4(),
        entity_id="NVDA",
        domain="stocks",
        interaction_type="view",
        duration_ms=9000,
    )
    before = _nvda_item(run_demo_feed(LOCAL_FOUNDER_USER_ID).items)
    assert before.user_sync_status == "UP_TO_DATE"

    reset_pipeline_state()

    after = _nvda_item(run_demo_feed(LOCAL_FOUNDER_USER_ID).items)
    assert after.user_sync_status == "NEW_TO_USER"
