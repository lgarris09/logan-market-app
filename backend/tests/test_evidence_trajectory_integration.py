"""Stock Opportunity Logic V2.2 -- Evidence + Trajectory Enrichment. Backend-
level integration tests: real market-evidence fetching (quote + profile +
benchmark quotes) through backend/app/logan_feed.py's real wiring,
trajectory-driven notification eligibility, restart persistence of the new
evidence/trajectory fields, and Ask STRATUS grounding. Mirrors
test_lifecycle_integration.py's/test_user_sync_integration.py's own
httpx.MockTransport-backed FMP provider pattern -- zero real network calls.

logan_core/tests/test_evidence_trajectory.py covers the pure tracker logic
directly; logan_core/tests/test_fmp_market_data_provider.py covers
fetch_company_profile()'s own contract; this file proves both are correctly
wired together through the real backend.
"""

import httpx

from backend.app.ask_llm_fixture import FixtureAskLlmProvider
from backend.app.ask_llm_provider import build_system_prompt
from backend.app.logan_feed import (
    get_opportunity_context,
    reset_pipeline_state,
    run_demo_feed,
)
from backend.app.notifications import reset_notification_state
from logan_core.contracts import LOCAL_FOUNDER_USER_ID
from logan_core.receptors.providers import FmpEarningsProvider, FmpMarketDataProvider
from logan_core.receptors.providers.fmp import reset_fmp_cache


def _earnings(symbol, actual, estimated, date="2026-05-20"):
    return [
        {"symbol": symbol, "date": date, "epsActual": actual, "epsEstimated": estimated}
    ]


def _quote(symbol, price, previous_close, change_pct, volume=1_000_000):
    return [
        {
            "symbol": symbol,
            "price": price,
            "previousClose": previous_close,
            "changePercentage": change_pct,
            "volume": volume,
            "timestamp": 1787601600,
        }
    ]


def _profile(symbol, sector="Technology", average_volume=1_000_000, beta=1.5):
    return [
        {
            "symbol": symbol,
            "sector": sector,
            "industry": "Semiconductors",
            "averageVolume": average_volume,
            "beta": beta,
        }
    ]


def _routing_market_data_provider(
    quote_by_symbol: dict, grade_by_symbol: dict, profile_by_symbol: dict
):
    def handler(request: httpx.Request) -> httpx.Response:
        symbol = request.url.params.get("symbol")
        if request.url.path.endswith("/quote"):
            return httpx.Response(200, json=quote_by_symbol.get(symbol, []))
        if request.url.path.endswith("/grades"):
            return httpx.Response(200, json=grade_by_symbol.get(symbol, []))
        if request.url.path.endswith("/profile"):
            return httpx.Response(200, json=profile_by_symbol.get(symbol, []))
        raise AssertionError(f"unexpected FMP path: {request.url.path}")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    return lambda *a, **kw: FmpMarketDataProvider(
        api_key="test-key-not-real", client=client
    )


def _setup(
    monkeypatch,
    *,
    nvda_price=100.0,
    nvda_change_pct=0.5,
    spy_change_pct=0.5,
    sector="Technology",
    sector_change_pct=0.5,
    volume=1_000_000,
    average_volume=1_000_000,
    beta=1.5,
    persist=False,
    tmp_path=None,
):
    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", "NVDA")
    monkeypatch.delenv("STRATUS_LIVE_NVDA_EARNINGS", raising=False)
    monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)
    if persist:
        monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
        monkeypatch.setenv("STRATUS_STATE_DB_PATH", str(tmp_path / "state.db"))
    else:
        monkeypatch.delenv("STRATUS_PERSIST_MEMORY", raising=False)

    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda *a, **kw: FmpEarningsProvider(
            api_key="test-key-not-real",
            client=httpx.Client(
                transport=httpx.MockTransport(
                    lambda r: httpx.Response(200, json=_earnings("NVDA", 1.87, 1.76))
                )
            ),
        ),
    )
    quote_by_symbol = {
        "NVDA": _quote("NVDA", nvda_price, 100.0, nvda_change_pct, volume),
        "SPY": _quote("SPY", 500.0, 500.0, spy_change_pct),
        "XLK": _quote("XLK", 200.0, 200.0, sector_change_pct),
    }
    profile_by_symbol = {"NVDA": _profile("NVDA", sector, average_volume, beta)}
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider(quote_by_symbol, {}, profile_by_symbol),
    )
    reset_fmp_cache()
    reset_pipeline_state()
    reset_notification_state()


def _nvda_item(payload_items):
    return next(i for i in payload_items if i.entity_id == "NVDA")


# --- Real evidence reaches the FeedItem contract ---------------------------


def test_real_evidence_reaches_feeditem_contract(monkeypatch):
    _setup(monkeypatch)
    item = _nvda_item(run_demo_feed(LOCAL_FOUNDER_USER_ID).items)
    assert item.evidence is not None
    assert item.evidence.trigger_price == 100.0
    assert item.evidence.sector == "Technology"
    assert item.trajectory == "STEADY"


def test_trigger_price_persists_across_polls_through_real_backend(monkeypatch):
    _setup(monkeypatch, nvda_price=100.0)
    first = _nvda_item(run_demo_feed(LOCAL_FOUNDER_USER_ID).items)
    assert first.evidence is not None
    assert first.evidence.trigger_price == 100.0

    reset_fmp_cache()
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider(
            {
                "NVDA": _quote("NVDA", 110.0, 100.0, 5.0),
                "SPY": _quote("SPY", 500.0, 500.0, 0.5),
                "XLK": _quote("XLK", 200.0, 200.0, 0.5),
            },
            {},
            {"NVDA": _profile("NVDA")},
        ),
    )
    second = _nvda_item(run_demo_feed(LOCAL_FOUNDER_USER_ID).items)
    assert second.evidence is not None
    assert second.evidence.trigger_price == 100.0  # unchanged
    assert second.evidence.price_change_since_trigger_pct == 10.0


# --- Trajectory-driven meaningful change integrates with the real backend --
#
# Full delivery (a real push/alert) additionally depends on Prioritization's
# own pre-existing fatigue/cooldown vetoes (ADR-050), which apply regardless
# of *why* something is notification-worthy and already have their own
# dedicated test coverage -- not re-tested here. What these tests prove is
# the actual V2.2 integration surface: a real trajectory transition computed
# through the real backend wiring correctly becomes the poll's
# meaningful_change_type and correctly advances the lifecycle snapshot's own
# notification-worthy timestamp (the exact signal get_alert_eligible_items
# reads), matching the pure-tracker proof in
# logan_core/tests/test_evidence_trajectory.py's own
# test_contradictory_evidence_reverses_trajectory.


def test_trajectory_reversal_is_notification_worthy_through_real_backend(monkeypatch):
    _setup(monkeypatch, nvda_change_pct=0.5, spy_change_pct=0.5)  # relative=0.0
    run_demo_feed(LOCAL_FOUNDER_USER_ID)  # establish baseline (first poll, STEADY)

    reset_fmp_cache()
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider(
            {
                "NVDA": _quote("NVDA", 103.0, 100.0, 3.0),
                "SPY": _quote("SPY", 500.0, 500.0, 0.0),
                "XLK": _quote("XLK", 200.0, 200.0, 0.0),
            },
            {},
            {"NVDA": _profile("NVDA")},
        ),
    )
    run_demo_feed(LOCAL_FOUNDER_USER_ID)  # relative moves to +3.0 -- STRENGTHENING

    reset_fmp_cache()
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider(
            {
                # Raw price still up, but now badly underperforming the
                # market -- relative=-3.0, a real reversal from +3.0.
                "NVDA": _quote("NVDA", 101.0, 100.0, 1.0),
                "SPY": _quote("SPY", 500.0, 500.0, 4.0),
                "XLK": _quote("XLK", 200.0, 200.0, 4.0),
            },
            {},
            {"NVDA": _profile("NVDA")},
        ),
    )
    before = _lifecycle_tracker_snapshot("NVDA")
    item = _nvda_item(run_demo_feed(LOCAL_FOUNDER_USER_ID).items)
    after = _lifecycle_tracker_snapshot("NVDA")

    assert item.trajectory == "REVERSING"
    assert item.meaningful_change_type == "trajectory_reversing"
    assert item.is_updated is True
    # This is the exact signal get_alert_eligible_items()/dispatch read --
    # confirms is_notification_worthy actually fired through the real
    # wiring, not just the pure tracker.
    assert after.last_notification_worthy_at != before.last_notification_worthy_at


def test_trajectory_weakening_alone_is_meaningful_but_not_notification_worthy(
    monkeypatch,
):
    """The asymmetry: WEAKENING updates the card but must not, by itself,
    advance the notification-worthy timestamp -- mirrors
    confidence_decreased's own established precedent."""
    _setup(monkeypatch, nvda_change_pct=3.0, spy_change_pct=0.0)  # relative=+3.0
    run_demo_feed(LOCAL_FOUNDER_USER_ID)  # first poll -- real "new_opportunity" alert

    reset_fmp_cache()
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider(
            {
                # Still net-confirming (relative=+1.0), just weaker than
                # before (+3.0 -> +1.0, a real but non-reversing decline).
                "NVDA": _quote("NVDA", 101.0, 100.0, 1.0),
                "SPY": _quote("SPY", 500.0, 500.0, 0.0),
                "XLK": _quote("XLK", 200.0, 200.0, 0.0),
            },
            {},
            {"NVDA": _profile("NVDA")},
        ),
    )
    before = _lifecycle_tracker_snapshot("NVDA")
    item = _nvda_item(run_demo_feed(LOCAL_FOUNDER_USER_ID).items)
    after = _lifecycle_tracker_snapshot("NVDA")

    assert item.trajectory == "WEAKENING"
    assert item.meaningful_change_type == "trajectory_weakening"
    assert item.is_updated is True  # meaningful -- the card does update
    # But NOT notification-worthy -- the timestamp must not have advanced
    # again on this poll.
    assert after.last_notification_worthy_at == before.last_notification_worthy_at


def _lifecycle_tracker_snapshot(entity_id: str):
    from backend.app import logan_feed as _module

    assert _module._lifecycle_tracker is not None
    snapshot = _module._lifecycle_tracker.export_snapshot(entity_id)
    assert snapshot is not None
    return snapshot


# --- Restart persistence ----------------------------------------------------


def test_evidence_and_trajectory_survive_a_simulated_restart(monkeypatch, tmp_path):
    _setup(
        monkeypatch,
        nvda_change_pct=0.5,
        spy_change_pct=0.5,  # relative=0.0 baseline
        persist=True,
        tmp_path=tmp_path,
    )
    run_demo_feed(LOCAL_FOUNDER_USER_ID)

    reset_fmp_cache()
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider(
            {
                "NVDA": _quote("NVDA", 103.0, 100.0, 3.0),
                "SPY": _quote("SPY", 500.0, 500.0, 0.0),
                "XLK": _quote("XLK", 200.0, 200.0, 0.0),
            },
            {},
            {"NVDA": _profile("NVDA")},
        ),
    )
    before = _nvda_item(run_demo_feed(LOCAL_FOUNDER_USER_ID).items)
    assert before.trajectory == "STRENGTHENING"
    assert before.evidence is not None
    assert before.evidence.trigger_price == 100.0

    # Simulated restart -- drops every in-process singleton; the SQLite
    # files themselves are untouched.
    reset_pipeline_state()
    reset_fmp_cache()
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        _routing_market_data_provider(
            {
                "NVDA": _quote("NVDA", 103.0, 100.0, 3.0),
                "SPY": _quote("SPY", 500.0, 500.0, 0.0),
                "XLK": _quote("XLK", 200.0, 200.0, 0.0),
            },
            {},
            {"NVDA": _profile("NVDA")},
        ),
    )
    after = _nvda_item(run_demo_feed(LOCAL_FOUNDER_USER_ID).items)
    # Trigger price and trajectory must not reset just because the process
    # restarted -- a fresh "1==brand new" story would silently re-fire
    # is_meaningful/trajectory transitions that already happened pre-restart.
    assert after.evidence is not None
    assert after.evidence.trigger_price == 100.0
    assert after.trajectory == "STRENGTHENING"


# --- Ask STRATUS grounding ---------------------------------------------------


def test_ask_stratus_receives_grounded_trajectory_and_evidence(monkeypatch):
    _setup(monkeypatch, nvda_change_pct=3.0, spy_change_pct=0.0, sector_change_pct=0.0)
    first = run_demo_feed(LOCAL_FOUNDER_USER_ID)
    nvda_event_id = next(i.event_id for i in first.items if i.entity_id == "NVDA")

    context = get_opportunity_context(LOCAL_FOUNDER_USER_ID, nvda_event_id)
    assert context is not None
    assert context.evidence is not None
    assert context.evidence.relative_to_market_pct == 3.0

    prompt = build_system_prompt(context)
    assert "Evidence trajectory:" in prompt
    assert "Performance vs. the broad market" in prompt
    assert "outperforming" in prompt

    provider = FixtureAskLlmProvider(
        answer="NVDA continues to outperform the market, so the thesis is strengthening."
    )
    result = provider.generate(context, "Is this getting stronger or weaker?")
    assert "strengthening" in result.text
    passed_context = provider.calls[0][0]
    assert passed_context.evidence is not None


def test_deterministic_fallback_unaffected_when_no_evidence_available(monkeypatch):
    """No live tickers configured at all -- demo mode -- evidence/trajectory
    stay at their inert defaults, and Ask STRATUS's deterministic fallback
    path (answer_question) is completely untouched by this block."""
    monkeypatch.delenv("STRATUS_LIVE_STOCK_TICKERS", raising=False)
    monkeypatch.delenv("STRATUS_LIVE_NVDA_EARNINGS", raising=False)
    monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)
    reset_pipeline_state()

    from backend.app.ask_engine import answer_question

    result = run_demo_feed(LOCAL_FOUNDER_USER_ID)
    nvda_event_id = next(i.event_id for i in result.items if i.entity_id == "NVDA")
    context = get_opportunity_context(LOCAL_FOUNDER_USER_ID, nvda_event_id)
    assert context is not None
    assert context.evidence is None
    assert context.trajectory == "STEADY"

    answer = answer_question(context, "What happened?")
    assert answer  # deterministic path still produces a real answer
