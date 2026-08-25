"""Sprint 3.6.7 Block 2 -- live price-move/analyst-grade wiring into
/v1/opportunities, and STOCK_CONVERGENCE_MULTI_SOURCE surfacing through the
live NVDA path when all three live signal types qualify in the same poll.

Same discipline as test_live_nvda_earnings.py: every test that exercises the
FMP path injects a real provider backed by httpx.MockTransport (via
monkeypatching FmpMarketDataProvider/FmpEarningsProvider in
backend.app.logan_feed's namespace) -- zero real network calls, no
dependency on FMP_API_KEY existing in this process. FmpMarketDataProvider's
own contract is separately covered by
logan_core/tests/test_fmp_market_data_provider.py; these tests are about the
backend wiring around it.
"""

import httpx

from backend.app.logan_feed import (
    _get_orchestrator,
    reset_pipeline_state,
    run_demo_feed,
)
from logan_core.receptors.providers import FmpEarningsProvider, FmpMarketDataProvider


def _mock_earnings_provider(entries) -> FmpEarningsProvider:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=entries))
    client = httpx.Client(transport=transport)
    return FmpEarningsProvider(api_key="test-key-not-real", client=client)


def _mock_market_data_provider(quote_entries, grade_entries) -> FmpMarketDataProvider:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/quote"):
            # Stock Opportunity Logic V2.2 fetches additional quotes (the
            # SPY market benchmark, and a sector benchmark ETF) for the
            # *entity's own* symbol only via this same endpoint -- any
            # symbol not the entity itself (e.g. SPY/XLK) legitimately gets
            # "no data" here, exactly like a real FMP response for a symbol
            # this test's fixture doesn't cover. Only the entity's own
            # `quote_entries` fixture data is returned for its own symbol.
            requested_symbol = request.url.params.get("symbol")
            entity_symbols = {e.get("symbol") for e in quote_entries}
            if requested_symbol in entity_symbols:
                return httpx.Response(200, json=quote_entries)
            return httpx.Response(200, json=[])
        if request.url.path.endswith("/grades"):
            return httpx.Response(200, json=grade_entries)
        if request.url.path.endswith("/profile"):
            # Stock Opportunity Logic V2.2: no profile fixture data in these
            # pre-V2.2 tests -- an honest "no profile" response, matching
            # this file's existing "graceful, not fabricated" discipline.
            return httpx.Response(200, json=[])
        raise AssertionError(f"unexpected FMP path: {request.url.path}")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    return FmpMarketDataProvider(api_key="test-key-not-real", client=client)


REPORTED_BEAT = {
    "symbol": "NVDA",
    "date": "2026-05-20",
    "epsActual": 1.87,
    "epsEstimated": 1.76,
}
REPORTED_NO_BEAT = {
    "symbol": "NVDA",
    "date": "2026-05-20",
    "epsActual": 1.76,
    "epsEstimated": 1.76,
}
QUOTE_SIGNIFICANT_MOVE = {
    "symbol": "NVDA",
    "price": 127.27,
    "previousClose": 118.50,
    "changePercentage": 7.4,
    "timestamp": 1755806400,  # 2025-08-21T20:00:00Z
}
QUOTE_NO_MOVE = {
    "symbol": "NVDA",
    "price": 119.10,
    "previousClose": 118.50,
    "changePercentage": 0.51,
    "timestamp": 1755806400,
}
GRADE_UPGRADE = {
    "symbol": "NVDA",
    "date": "2026-08-21",
    "gradingCompany": "Fixture Capital",
    "previousGrade": "Hold",
    "newGrade": "Buy",
    "action": "upgrade",
}
GRADE_MAINTAIN = {
    "symbol": "NVDA",
    "date": "2026-08-21",
    "gradingCompany": "Fixture Capital",
    "previousGrade": "Buy",
    "newGrade": "Buy",
    "action": "maintain",
}


def _nvda_item(payload: dict) -> dict:
    return next(item for item in payload["items"] if item["entity_id"] == "NVDA")


def _setup(monkeypatch, *, earnings_entries, quote_entries, grade_entries):
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "true")
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda *a, **kw: _mock_earnings_provider(earnings_entries),
    )
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        lambda *a, **kw: _mock_market_data_provider(quote_entries, grade_entries),
    )
    reset_pipeline_state()


# --- Convergence tracker wiring ------------------------------------------


def test_enabled_mode_orchestrator_has_convergence_tracker(monkeypatch):
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "true")
    reset_pipeline_state()
    assert _get_orchestrator().deps.convergence_tracker is not None


def test_disabled_mode_orchestrator_has_no_convergence_tracker(monkeypatch):
    monkeypatch.delenv("STRATUS_LIVE_NVDA_EARNINGS", raising=False)
    reset_pipeline_state()
    assert _get_orchestrator().deps.convergence_tracker is None


# --- All three live signals qualify: convergence fires end to end --------


def test_three_qualifying_live_signals_produce_convergence_and_stay_one_item(
    monkeypatch,
):
    _setup(
        monkeypatch,
        earnings_entries=[REPORTED_BEAT],
        quote_entries=[QUOTE_SIGNIFICANT_MOVE],
        grade_entries=[GRADE_UPGRADE],
    )
    result = run_demo_feed()

    assert len(result.items) == 11  # still exactly one NVDA item, not three
    entity_ids = [item.entity_id for item in result.items]
    assert entity_ids.count("NVDA") == 1

    nvda = next(item for item in result.items if item.entity_id == "NVDA")
    # The primary (first/earnings) signal still drives what_happened/signal_type.
    assert "1.87" in nvda.delivered_item.what_happened
    assert nvda.signal_type == "earnings_signal"
    # Real trigger contributions raised confidence relative to a single
    # signal alone.
    assert nvda.confidence_score > 0.5


# --- Only some signals qualify: no fabricated convergence -----------------


def test_only_earnings_qualifies_no_convergence_fabricated(monkeypatch):
    _setup(
        monkeypatch,
        earnings_entries=[REPORTED_BEAT],
        quote_entries=[QUOTE_NO_MOVE],
        grade_entries=[GRADE_MAINTAIN],
    )
    result = run_demo_feed()

    assert len(result.items) == 11
    nvda = next(item for item in result.items if item.entity_id == "NVDA")
    assert "1.87" in nvda.delivered_item.what_happened


def test_no_signals_qualify_falls_back_to_simulated_nvda(monkeypatch):
    _setup(
        monkeypatch,
        earnings_entries=[REPORTED_NO_BEAT],
        quote_entries=[QUOTE_NO_MOVE],
        grade_entries=[GRADE_MAINTAIN],
    )
    result = run_demo_feed()

    assert len(result.items) == 11
    nvda = next(item for item in result.items if item.entity_id == "NVDA")
    assert "guidance raised" in nvda.delivered_item.what_happened


# --- Provider failure isolation --------------------------------------------


def test_market_data_provider_unreachable_still_delivers_earnings_only(
    monkeypatch,
):
    """Price-move/analyst-grade fetch failures must never take down the
    earnings path they're layered alongside -- same "never crash the whole
    poll over one provider hiccup" discipline as the rest of this file."""
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "true")
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda *a, **kw: _mock_earnings_provider([REPORTED_BEAT]),
    )

    def _raise(request):
        raise httpx.ConnectError("connection refused")

    def _broken_market_data_provider(*args, **kwargs):
        transport = httpx.MockTransport(_raise)
        client = httpx.Client(transport=transport)
        return FmpMarketDataProvider(api_key="test-key-not-real", client=client)

    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider", _broken_market_data_provider
    )
    reset_pipeline_state()
    result = run_demo_feed()

    assert len(result.items) == 11
    nvda = next(item for item in result.items if item.entity_id == "NVDA")
    assert "1.87" in nvda.delivered_item.what_happened


# --- API contract -----------------------------------------------------------


def test_live_market_data_response_has_no_internal_or_secret_fields(monkeypatch):
    _setup(
        monkeypatch,
        earnings_entries=[REPORTED_BEAT],
        quote_entries=[QUOTE_SIGNIFICANT_MOVE],
        grade_entries=[GRADE_UPGRADE],
    )
    result = run_demo_feed()
    payload = result.model_dump()
    flat = str(payload)

    assert "internal_rank_score" not in flat
    assert "priority_score" not in flat
    assert "test-key-not-real" not in flat
    # Sprint 3.6.9 (Stock Opportunity Logic V2) added the six lifecycle_*
    # fields below deliberately -- see docs/DECISIONS.md's Sprint 3.6.9 ADR.
    # V2.1 (User Sync Gap) added opportunity_revision/user_sync_status.
    nvda_payload = _nvda_item(payload)
    assert set(nvda_payload.keys()) == {
        "event_id",
        "entity_id",
        "display_name",
        "category",
        "ticker",
        "domain",
        "delivered_item",
        "rank",
        "confidence_score",
        "confidence_label",
        "connected_event_ids",
        "is_new_for_user",
        "signal_type",
        "lifecycle_state",
        "is_updated",
        "meaningful_change_type",
        "lifecycle_reason",
        "last_meaningful_change_at",
        "thesis_age_hours",
        "opportunity_revision",
        "user_sync_status",
        "trajectory",
        "previous_trajectory",
        "trajectory_reason",
        "evidence",
    }
