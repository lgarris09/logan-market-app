"""Stock Opportunity Logic V2.3D ("Since You Last Looked") -- backend-level
integration tests: real card-open (record_interaction "view") vs a mere feed
fetch, real durable revision history producing a specific change_type, the
no-history fallback, degraded-provider honesty, and per-user isolation.
Mirrors test_user_sync_integration.py's own httpx.MockTransport-backed FMP
provider pattern -- zero real network calls.

logan_core/tests/test_since_last_looked.py covers the pure
compute_since_last_looked comparison directly; this file proves the same
behavior through backend/app/logan_feed.py's real wiring (durable
OpportunityRevisionStore, UserOpportunityKnowledge, provider_degraded).
"""

from typing import Callable
from uuid import uuid4

import httpx

from backend.app.logan_feed import (
    record_interaction,
    reset_pipeline_state,
    run_demo_feed,
)
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


def _failing_earnings_provider():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="rate limited")

    transport = httpx.MockTransport(handler)
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


def _grades(symbol, action, date="2026-08-20"):
    return [{"symbol": symbol, "date": date, "action": action}]


def _setup(
    monkeypatch,
    *,
    earnings_by_symbol=None,
    grade_by_symbol=None,
    earnings_provider=None,
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
        earnings_provider or _routing_earnings_provider(earnings_by_symbol or {}),
    )
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider({}, grade_by_symbol or {}),
    )
    reset_fmp_cache()
    reset_pipeline_state()


def _nvda_item(payload_items):
    return next(i for i in payload_items if i.entity_id == "NVDA")


def _view(user_id: str) -> None:
    record_interaction(
        user_id=user_id,
        event_id=uuid4(),
        entity_id="NVDA",
        domain="stocks",
        interaction_type="view",
        duration_ms=9000,
    )


# --- First view --------------------------------------------------------------


def test_first_view_has_no_since_last_looked_language(monkeypatch):
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})

    item = _nvda_item(run_demo_feed("user-fresh").items)
    assert item.since_last_looked is not None
    assert item.since_last_looked.status == "first_view"
    assert item.since_last_looked.detail is None


def test_mere_feed_fetches_never_produce_a_since_last_looked_return(monkeypatch):
    """Seen/open semantics: fetching the feed repeatedly (no real interaction)
    must never itself count as having "looked" -- avoids the exact failure
    mode the product explicitly warned against (app launch, off-screen
    render, or a bare GET marking something as looked-at)."""
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})

    for _ in range(3):
        item = _nvda_item(run_demo_feed("user-fresh-2").items)
        assert item.since_last_looked.status == "first_view"


# --- No material change --------------------------------------------------


def test_no_material_change_after_viewing_the_current_revision(monkeypatch):
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})
    run_demo_feed("user-a")  # establishes revision 1
    _view("user-a")

    item = _nvda_item(run_demo_feed("user-a").items)
    assert item.since_last_looked.status == "no_material_change"
    assert "still monitoring" in item.since_last_looked.detail.lower()


# --- Material change, with real durable history --------------------------


def test_material_change_reflects_the_specific_recorded_change_type(
    monkeypatch, tmp_path
):
    _setup(
        monkeypatch,
        earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)},
        persist=True,
        tmp_path=tmp_path,
    )
    run_demo_feed("user-b")  # revision 1
    _view("user-b")
    assert _nvda_item(run_demo_feed("user-b").items).since_last_looked.status == (
        "no_material_change"
    )

    # A real, additive world-fact change: a live analyst grade now fires.
    reset_fmp_cache()
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider({}, {"NVDA": _grades("NVDA", "upgrade")}),
    )
    item = _nvda_item(run_demo_feed("user-b").items)
    assert item.opportunity_revision == 2
    assert item.since_last_looked.status == "material_change"
    assert item.since_last_looked.change_type == "new_signal_appeared"
    assert item.since_last_looked.detail  # a real, non-empty sentence


def test_multiple_revisions_since_last_view_reports_only_the_latest(
    monkeypatch, tmp_path
):
    _setup(
        monkeypatch,
        earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)},
        persist=True,
        tmp_path=tmp_path,
    )
    run_demo_feed("user-c")  # revision 1
    _view("user-c")

    # Revision 2: a grade change fires.
    reset_fmp_cache()
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider({}, {"NVDA": _grades("NVDA", "upgrade")}),
    )
    second = _nvda_item(run_demo_feed("user-c").items)
    assert second.opportunity_revision == 2

    # Revision 3: a stronger earnings beat fires next, still without the
    # user ever re-opening the card in between.
    reset_fmp_cache()
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        _routing_earnings_provider({"NVDA": _earnings("NVDA", 2.50, 1.76)}),
    )
    third = _nvda_item(run_demo_feed("user-c").items)
    assert third.opportunity_revision == 3

    # The user finally returns: must report revision 3's own change, not a
    # concatenation of revisions 2 and 3, and not revision 2's stale reason.
    final = _nvda_item(run_demo_feed("user-c").items)
    assert final.since_last_looked.status == "material_change"
    assert final.since_last_looked.change_type == "confidence_increased"


def test_material_change_without_persistence_falls_back_honestly(monkeypatch):
    """No durable OpportunityRevisionStore active (persistence disabled) --
    the revision counter still advances (in-memory tracker), but there is no
    history row to explain it. Must report an honest, generic material
    change, never a fabricated specific reason."""
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})
    run_demo_feed("user-d")
    _view("user-d")

    reset_fmp_cache()
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider({}, {"NVDA": _grades("NVDA", "upgrade")}),
    )
    item = _nvda_item(run_demo_feed("user-d").items)
    assert item.opportunity_revision == 2
    assert item.since_last_looked.status == "material_change"
    assert item.since_last_looked.change_type is None
    assert item.since_last_looked.detail  # still a real, honest sentence


# --- Degraded live data ----------------------------------------------------


def test_degraded_provider_state_is_reported_instead_of_false_reassurance(
    monkeypatch,
):
    """The live earnings provider fails on every poll here (matching
    test_live_nvda_earnings.py's own falls-back-to-simulated pattern) --
    NVDA still appears via its simulated demo fixture, with an unchanging
    signal poll-to-poll (so the revision genuinely never advances), while
    provider_degraded stays True throughout. Isolates "degraded" from
    "material_change": nothing about the tracked entity's own signal
    changes here, only whether the live fetch itself succeeded."""
    _setup(monkeypatch, earnings_provider=_failing_earnings_provider())
    run_demo_feed("user-e")  # revision 1, via the simulated fixture
    _view("user-e")

    item = _nvda_item(run_demo_feed("user-e").items)
    assert item.opportunity_revision == 1  # unchanged -- no real signal shift
    assert item.since_last_looked.status == "degraded"
    assert "unavailable" in item.since_last_looked.detail.lower()
    # Never a false "still monitoring, nothing changed" claim.
    assert "still monitoring" not in item.since_last_looked.detail.lower()


# --- Per-user isolation ------------------------------------------------------


def test_each_user_has_their_own_independent_since_last_looked(monkeypatch):
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})
    run_demo_feed("user-f")

    _view("user-f")  # only user-f has opened this opportunity

    viewer_result = _nvda_item(run_demo_feed("user-f").items)
    stranger_result = _nvda_item(run_demo_feed("user-g").items)

    assert viewer_result.since_last_looked.status == "no_material_change"
    assert stranger_result.since_last_looked.status == "first_view"


def test_anonymous_style_and_authenticated_style_user_ids_both_work(monkeypatch):
    """resolve_user_id() hands this function whatever string identity it
    resolved (an anonymous device UUID or a linked authenticated
    stratus_user_id) -- since_last_looked must not special-case the shape
    of that string."""
    _setup(monkeypatch, earnings_by_symbol={"NVDA": _earnings("NVDA", 1.87, 1.76)})
    run_demo_feed("anon-3f9a7b21-4e2d-4c11-9c3a-6b1d2e8f0a11")
    _view("anon-3f9a7b21-4e2d-4c11-9c3a-6b1d2e8f0a11")

    item = _nvda_item(run_demo_feed("anon-3f9a7b21-4e2d-4c11-9c3a-6b1d2e8f0a11").items)
    assert item.since_last_looked.status == "no_material_change"
