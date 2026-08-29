"""Sprint 3.6.6C — live NVDA earnings wiring into /v1/opportunities.

Every test that exercises the FMP path injects a real FmpEarningsProvider
backed by httpx.MockTransport (via monkeypatching the FmpEarningsProvider
name in backend.app.logan_feed's namespace) -- so the actual adapter logic
(including the Sprint 3.6.6B selection-logic fix) runs for real, with zero
real network calls and no dependency on FMP_API_KEY existing in this
process. FmpEarningsProvider's own contract is separately covered by
logan_core/tests/test_fmp_provider.py; these tests are about the backend
wiring around it.
"""

import httpx
import pytest

from backend.app.logan_feed import (
    _get_orchestrator,
    reset_pipeline_state,
    run_demo_feed,
)
from logan_core.receptors.providers import FmpEarningsProvider, FmpProviderError


@pytest.fixture(autouse=True)
def _no_live_market_data_by_default(monkeypatch):
    """Sprint 3.6.7 Block 2 wires two more live signal types (price move,
    analyst grade) into the same live-NVDA path this file's tests already
    exercise for earnings alone (see backend/app/logan_feed.py's
    _live_nvda_price_move_raw_signal/_live_nvda_analyst_grade_raw_signal).
    None of the tests in this file are about those two signal types -- keep
    them deterministic and isolated from real network calls regardless of
    whether a real FMP_API_KEY happens to be present in this machine's
    environment, exactly like the "no API key" fallback path this file
    already covers for earnings. Dedicated coverage for the price-move/
    analyst-grade/convergence wiring itself lives in
    test_live_nvda_market_data.py.
    """

    def _unavailable(*args, **kwargs):
        raise FmpProviderError("no live market data configured for this test")

    monkeypatch.setattr("backend.app.logan_feed.FmpMarketDataProvider", _unavailable)


def _mock_fmp_provider(handler) -> FmpEarningsProvider:
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    return FmpEarningsProvider(api_key="test-key-not-real", client=client)


def _nvda_entries_handler(entries):
    def handler(request):
        return httpx.Response(200, json=entries)

    return handler


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
    "epsEstimated": 1.76,  # in-line with consensus -- no beat
}
UPCOMING_SCHEDULED_ONLY = [
    {"symbol": "NVDA", "date": "2026-08-26", "epsEstimated": 2.08}  # no epsActual yet
]


def _nvda_item(payload: dict) -> dict:
    return next(item for item in payload["items"] if item["entity_id"] == "NVDA")


# --- 1. Disabled: existing behavior unchanged ---------------------------


def test_disabled_by_default_uses_simulated_nvda(monkeypatch):
    monkeypatch.delenv("STRATUS_LIVE_NVDA_EARNINGS", raising=False)
    reset_pipeline_state()
    result = run_demo_feed()
    assert len(result.items) == 11
    nvda = next(item for item in result.items if item.entity_id == "NVDA")
    assert nvda.signal_type == "earnings_signal"
    # The simulated fixture's own known content -- see receptors/simulated.py.
    assert "guidance raised" in nvda.delivered_item.what_happened


def test_explicitly_disabled_uses_simulated_nvda(monkeypatch):
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "false")
    reset_pipeline_state()
    result = run_demo_feed()
    assert len(result.items) == 11


def test_disabled_mode_orchestrator_has_no_trigger_detector(monkeypatch):
    """Direct proof for the architectural concern raised mid-implementation:
    Orchestrator.run() appends a "trigger_detection" ExecutionTrace layer
    entry for every raw_signal whenever *any* trigger_detector is configured
    at all (see orchestrator/pipeline.py), regardless of whether that
    detector ultimately fires. Wiring one unconditionally would therefore
    change every simulated entity's execution trace even with the live path
    off. Disabled mode must reconstruct the exact same
    PipelineDependencies() shape every pre-3.6.6C caller already gets."""
    monkeypatch.delenv("STRATUS_LIVE_NVDA_EARNINGS", raising=False)
    reset_pipeline_state()
    assert _get_orchestrator().deps.trigger_detector is None


def test_enabled_mode_orchestrator_has_trigger_detector(monkeypatch):
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "true")
    reset_pipeline_state()
    assert _get_orchestrator().deps.trigger_detector is not None


# --- 2. Enabled + mocked successful FMP response -------------------------


def test_enabled_with_real_beat_fires_trigger_and_replaces_nvda_only(monkeypatch):
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "true")
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda *a, **kw: _mock_fmp_provider(_nvda_entries_handler([REPORTED_BEAT])),
    )
    reset_pipeline_state()
    result = run_demo_feed()

    assert len(result.items) == 11  # no duplicate -- replaced, not added
    entity_ids = [item.entity_id for item in result.items]
    assert entity_ids.count("NVDA") == 1

    nvda = next(item for item in result.items if item.entity_id == "NVDA")
    assert "1.87" in nvda.delivered_item.what_happened
    assert "1.76" in nvda.delivered_item.what_happened
    # Real trigger contribution raised confidence relative to the simulated
    # baseline (0.68 as observed for the simulated fixture pre-change).
    assert nvda.confidence_score > 0.5
    # V2.3A.1: a genuine success is not "degraded" -- provider_degraded is
    # strictly about unreachable data, never about which content resulted.
    assert result.provider_degraded is False

    # Every other simulated entity is untouched.
    other_ids = {item.entity_id for item in result.items} - {"NVDA"}
    assert other_ids == {
        "TSLA",
        "AAPL",
        "MARKETS",
        "OIL",
        "BTC",
        "FED",
        "NFL",
        "MUSIC",
        "POLY",
        "AI_SECTOR",
    }


# --- 3. Enabled but trigger does not fire ---------------------------------


def test_enabled_with_no_beat_does_not_manufacture_a_fake_opportunity(monkeypatch):
    """A valid provider response is not itself an opportunity: this 3.6.6C
    slice's intended semantics are that the real NVDA opportunity only
    surfaces when STOCK_EARNINGS_BEAT actually fires. A real report that
    fails to beat consensus by >=5% must fall back to the simulated NVDA
    fixture, not be presented as a (weaker) live opportunity."""
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "true")
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda *a, **kw: _mock_fmp_provider(_nvda_entries_handler([REPORTED_NO_BEAT])),
    )
    reset_pipeline_state()
    result = run_demo_feed()

    assert len(result.items) == 11
    nvda = next(item for item in result.items if item.entity_id == "NVDA")
    assert "guidance raised" in nvda.delivered_item.what_happened
    assert "1.76" not in nvda.delivered_item.what_happened
    # V2.3A.1: a real, valid report that simply doesn't qualify is a genuine
    # answer, not a provider hiccup -- must never read as "degraded."
    assert result.provider_degraded is False


# --- 4. FMP/provider failure ------------------------------------------


def test_enabled_but_fmp_unreachable_falls_back_to_simulated_nvda(monkeypatch):
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "true")

    def handler(request):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda *a, **kw: _mock_fmp_provider(handler),
    )
    reset_pipeline_state()
    result = run_demo_feed()

    assert len(result.items) == 11
    nvda = next(item for item in result.items if item.entity_id == "NVDA")
    # Simulated fallback content, not a crash, not a fabricated live result.
    assert "guidance raised" in nvda.delivered_item.what_happened
    # V2.3A.1: this IS the case provider_degraded exists for -- the data
    # was genuinely unreachable, not merely absent/non-qualifying, and a
    # client must be able to tell the difference.
    assert result.provider_degraded is True


def test_enabled_but_no_api_key_falls_back_to_simulated_nvda(monkeypatch):
    """No FmpEarningsProvider mock injected at all here -- the real
    constructor runs and fails naturally because FMP_API_KEY isn't set,
    exercising the actual missing-credential failure path, not a stand-in."""
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "true")
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    reset_pipeline_state()
    result = run_demo_feed()

    assert len(result.items) == 11
    nvda = next(item for item in result.items if item.entity_id == "NVDA")
    assert "guidance raised" in nvda.delivered_item.what_happened
    # V2.3A.1: a missing credential is a provider-construction failure, the
    # same "genuinely unreachable" category as a network error.
    assert result.provider_degraded is True


def test_enabled_but_fmp_returns_no_data_falls_back_to_simulated_nvda(monkeypatch):
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "true")
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda *a, **kw: _mock_fmp_provider(_nvda_entries_handler([])),
    )
    reset_pipeline_state()
    result = run_demo_feed()

    assert len(result.items) == 11
    nvda = next(item for item in result.items if item.entity_id == "NVDA")
    assert "guidance raised" in nvda.delivered_item.what_happened
    # V2.3A.1: FMP answered successfully with genuinely no reported
    # earnings on file -- an honest empty answer, not a provider failure.
    assert result.provider_degraded is False


# --- 5. Missing actual EPS / future scheduled earnings --------------------


def test_upcoming_scheduled_only_falls_back_to_simulated_nvda(monkeypatch):
    """Reproduces the exact live scenario hit against real NVDA data (only
    an upcoming/unreported entry available -- actual_eps is None). With no
    actual_eps, evaluate_earnings_beat_condition cannot fire, so this must
    fall back to the simulated fixture rather than surfacing a no-data
    "opportunity" built from an unreported entry."""
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "true")
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda *a, **kw: _mock_fmp_provider(
            _nvda_entries_handler(UPCOMING_SCHEDULED_ONLY)
        ),
    )
    reset_pipeline_state()
    result = run_demo_feed()

    assert len(result.items) == 11
    nvda = next(item for item in result.items if item.entity_id == "NVDA")
    assert "guidance raised" in nvda.delivered_item.what_happened


def test_reported_entry_preferred_over_later_scheduled_entry_end_to_end(monkeypatch):
    """The same scenario, but with a real reported quarter also present
    (exactly like the live NVDA case) -- confirms the reported one wins and
    the trigger fires through the full backend path."""
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "true")
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda *a, **kw: _mock_fmp_provider(
            _nvda_entries_handler([REPORTED_BEAT] + UPCOMING_SCHEDULED_ONLY)
        ),
    )
    reset_pipeline_state()
    result = run_demo_feed()

    nvda = next(item for item in result.items if item.entity_id == "NVDA")
    assert "1.87" in nvda.delivered_item.what_happened


# --- 6. API contract: backward-compatible, no internal/secret leaks -------


def test_live_nvda_response_has_no_internal_or_secret_fields(monkeypatch):
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "true")
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda *a, **kw: _mock_fmp_provider(
            _nvda_entries_handler([REPORTED_BEAT]),
        ),
    )
    reset_pipeline_state()
    result = run_demo_feed()
    payload = result.model_dump()
    flat = str(payload)

    assert "internal_rank_score" not in flat
    assert "priority_score" not in flat
    assert "test-key-not-real" not in flat
    # Field set is exactly the current, intentional FeedItem contract -- no
    # accidental/internal/secret fields. Sprint 3.6.9 (Stock Opportunity
    # Logic V2) added the six lifecycle_* fields below -- see
    # docs/DECISIONS.md's Sprint 3.6.9 ADR; V2.1 (User Sync Gap) added
    # opportunity_revision/user_sync_status -- these are here deliberately,
    # not a leak this test needs to keep guarding against.
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


def test_live_nvda_route_returns_successfully_via_test_client(monkeypatch):
    from fastapi.testclient import TestClient

    from backend.app.main import app

    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "true")
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda *a, **kw: _mock_fmp_provider(_nvda_entries_handler([REPORTED_BEAT])),
    )
    reset_pipeline_state()
    client = TestClient(app)
    response = client.get("/v1/opportunities")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 11
    assert "test-key-not-real" not in response.text
