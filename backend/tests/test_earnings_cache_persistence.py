"""V2.3A.1 field reliability work -- durable last-successful-earnings-
observation persistence across a simulated backend restart during an
ongoing FMP outage.

Mirrors test_notification_persistence.py's exact pattern (STRATUS_STATE_DB_PATH
pointed at an isolated tmp_path file, never the real local database), with
one addition specific to this feature: a real backend restart empties
logan_core's shared FmpResponseCache too -- a separate process-lifetime
singleton that reset_pipeline_state() alone does not touch (see
conftest.py's autouse fixture, which resets it independently) -- so
`_simulated_restart()` below calls both.

Real production incident this closes (hosted audit, 2026-08-28/29): a Fly
deploy restarted the backend while FMP's daily quota was already exhausted.
The in-memory FmpResponseCache came up empty, so fetch_latest_earnings's
stale-grace fallback had nothing to serve from until this process's own
first successful fetch -- which never happened, because the outage was
still ongoing. NVDA/AAPL's real, still-valid earnings were absent from the
feed entirely for the outage's full duration, indistinguishable from "no
qualifying opportunity."
"""

from datetime import datetime, timedelta, timezone

import httpx
import pytest

from backend.app import logan_feed
from backend.app.config import earnings_cache_store_db_path
from backend.app.earnings_cache_store import EarningsCacheStore
from backend.app.logan_feed import reset_pipeline_state, run_demo_feed
from logan_core.receptors.providers import (
    EARNINGS_CACHE_TTL_SECONDS,
    EARNINGS_STALE_GRACE_SECONDS,
    FmpEarningsProvider,
    FmpProviderError,
    reset_fmp_cache,
)


@pytest.fixture(autouse=True)
def _no_live_market_data_by_default(monkeypatch):
    """A successful earnings substitution makes NVDA `live_substituted`,
    which additionally triggers price-move/analyst-grade/market-evidence
    fetches via FmpMarketDataProvider (see logan_feed.py's
    _run_feed_pipeline) -- this file's tests are about the earnings-cache-
    store path alone. Mirrors test_live_nvda_earnings.py's identical
    fixture: without it, a real FMP_API_KEY present in a developer's local
    backend/.env would make real, quota-consuming network calls to FMP's
    live API on every test run here, against the exact account whose quota
    this whole fix exists because of."""

    def _unavailable(*args, **kwargs):
        raise FmpProviderError("no live market data configured for this test")

    monkeypatch.setattr("backend.app.logan_feed.FmpMarketDataProvider", _unavailable)


def _mock_fmp_provider(handler, **kwargs) -> FmpEarningsProvider:
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    return FmpEarningsProvider(api_key="test-key-not-real", client=client, **kwargs)


def _nvda_entries_handler(entries):
    def handler(request):
        return httpx.Response(200, json=entries)

    return handler


def _rate_limited_handler(request):
    return httpx.Response(429, text="rate limited")


REPORTED_BEAT = {
    "symbol": "NVDA",
    "date": "2026-08-26",
    "epsActual": 2.22,
    "epsEstimated": 2.09,
}


def _simulated_restart() -> None:
    """A real backend restart drops both this file's own module-lifetime
    state (Orchestrator, lifecycle tracker, and -- as of this fix --
    _earnings_cache_store) AND logan_core's separate shared FmpResponseCache
    singleton. Calling only reset_pipeline_state() would leave the in-memory
    FMP cache still warm from before the "restart," which would trivially
    survive an outage with or without this fix and defeat the point of these
    tests."""
    reset_pipeline_state()
    reset_fmp_cache()


# --- Gating: disabled by default, same discipline as every other store -----


def test_disabled_by_default_no_earnings_cache_store_constructed(monkeypatch):
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "true")
    monkeypatch.delenv("STRATUS_PERSIST_MEMORY", raising=False)
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda **kwargs: _mock_fmp_provider(
            _nvda_entries_handler([REPORTED_BEAT]), **kwargs
        ),
    )
    reset_pipeline_state()

    run_demo_feed()

    assert logan_feed._earnings_cache_store is None  # noqa: SLF001


def test_disabled_mode_still_falls_back_to_simulated_nvda_on_outage(monkeypatch):
    """Test #7 -- existing normal TTL cache / fallback behavior is byte-for-
    byte unchanged when persistence is off, the default and every pre-
    V2.3A.1 test's posture. Mirrors
    test_live_nvda_earnings.py's own test_enabled_but_fmp_unreachable_falls_
    back_to_simulated_nvda."""
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "true")
    monkeypatch.delenv("STRATUS_PERSIST_MEMORY", raising=False)
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda **kwargs: _mock_fmp_provider(_rate_limited_handler, **kwargs),
    )
    reset_pipeline_state()

    result = run_demo_feed()

    assert result.provider_degraded is True
    nvda = next(item for item in result.items if item.entity_id == "NVDA")
    assert "guidance raised" in nvda.delivered_item.what_happened  # simulated fixture


# --- Test #1: a successful response persists --------------------------------


def test_successful_response_persists(monkeypatch, tmp_path):
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "true")
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv("STRATUS_STATE_DB_PATH", str(tmp_path / "state.db"))
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda **kwargs: _mock_fmp_provider(
            _nvda_entries_handler([REPORTED_BEAT]), **kwargs
        ),
    )
    reset_pipeline_state()

    result = run_demo_feed()
    assert result.provider_degraded is False
    nvda = next(item for item in result.items if item.entity_id == "NVDA")
    assert "2.22" in nvda.delivered_item.what_happened

    store = EarningsCacheStore(earnings_cache_store_db_path())
    persisted = store.load_all()
    store.close()

    assert "NVDA" in persisted
    report, observed_at = persisted["NVDA"]
    assert report.actual_eps == 2.22
    assert observed_at.tzinfo is not None


# --- Test #6: a failed response is never persisted --------------------------


def test_failed_response_is_never_persisted(monkeypatch, tmp_path):
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "true")
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv("STRATUS_STATE_DB_PATH", str(tmp_path / "state.db"))
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda **kwargs: _mock_fmp_provider(_rate_limited_handler, **kwargs),
    )
    reset_pipeline_state()

    result = run_demo_feed()
    assert (
        result.provider_degraded is True
    )  # a genuine failure, no prior entry to recover

    store = EarningsCacheStore(earnings_cache_store_db_path())
    persisted = store.load_all()
    store.close()

    assert persisted == {}


# --- Test #2 + #3: recovery during a simulated restart+outage, within grace


def test_persisted_response_recovers_across_a_simulated_restart_within_grace(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "true")
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv("STRATUS_STATE_DB_PATH", str(tmp_path / "state.db"))
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda **kwargs: _mock_fmp_provider(
            _nvda_entries_handler([REPORTED_BEAT]), **kwargs
        ),
    )
    reset_pipeline_state()
    first = run_demo_feed()
    assert first.provider_degraded is False

    # Backdate the persisted observation to simulate a real refetch attempt
    # being due by the time the "restart" happens -- past the 6h TTL,
    # comfortably within the 24h grace window on top of it. This is what
    # makes the mocked 429 below an actual attempted-and-failed refetch, not
    # a TTL cache hit that never calls FMP at all.
    store = EarningsCacheStore(earnings_cache_store_db_path())
    report, _observed_at = store.load_all()["NVDA"]
    backdated = datetime.now(timezone.utc) - timedelta(
        seconds=EARNINGS_CACHE_TTL_SECONDS + 3600
    )
    store.save("NVDA", report, backdated)
    store.close()

    # Simulate a real restart during an ongoing outage: every in-process
    # state this feature touches is dropped, then FMP fails on every
    # request from this fresh process's very first poll onward -- the exact
    # hosted incident this fix closes.
    _simulated_restart()
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda **kwargs: _mock_fmp_provider(_rate_limited_handler, **kwargs),
    )

    second = run_demo_feed()

    assert second.provider_degraded is False  # recovered via grace, not a failure
    nvda_after = next(item for item in second.items if item.entity_id == "NVDA")
    assert "2.22" in nvda_after.delivered_item.what_happened


# --- Test #4: a persisted response outside grace is rejected ----------------


def test_persisted_response_outside_grace_is_rejected_after_a_simulated_restart(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "true")
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv("STRATUS_STATE_DB_PATH", str(tmp_path / "state.db"))
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda **kwargs: _mock_fmp_provider(
            _nvda_entries_handler([REPORTED_BEAT]), **kwargs
        ),
    )
    reset_pipeline_state()
    run_demo_feed()

    store = EarningsCacheStore(earnings_cache_store_db_path())
    report, _observed_at = store.load_all()["NVDA"]
    # Past both the TTL *and* the full stale grace window -- a report this
    # old, during an outage this long, is no longer safe to keep presenting
    # as current.
    too_old = datetime.now(timezone.utc) - timedelta(
        seconds=EARNINGS_CACHE_TTL_SECONDS + EARNINGS_STALE_GRACE_SECONDS + 3600
    )
    store.save("NVDA", report, too_old)
    store.close()

    _simulated_restart()
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda **kwargs: _mock_fmp_provider(_rate_limited_handler, **kwargs),
    )

    result = run_demo_feed()

    assert result.provider_degraded is True
    nvda = next(item for item in result.items if item.entity_id == "NVDA")
    # Falls back to the simulated fixture, same honest degradation as any
    # other genuine provider failure -- never a fabricated live result, and
    # never the too-old recovered report either.
    assert "guidance raised" in nvda.delivered_item.what_happened


# --- Test #5: a fresh successful fetch replaces the persisted value --------


def test_a_fresh_successful_fetch_after_restart_replaces_the_persisted_value(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("STRATUS_LIVE_NVDA_EARNINGS", "true")
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv("STRATUS_STATE_DB_PATH", str(tmp_path / "state.db"))
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda **kwargs: _mock_fmp_provider(
            _nvda_entries_handler([REPORTED_BEAT]), **kwargs
        ),
    )
    reset_pipeline_state()
    run_demo_feed()

    store = EarningsCacheStore(earnings_cache_store_db_path())
    old_report, _observed_at = store.load_all()["NVDA"]
    backdated = datetime.now(timezone.utc) - timedelta(
        seconds=EARNINGS_CACHE_TTL_SECONDS + 3600
    )
    store.save("NVDA", old_report, backdated)
    store.close()

    # Restart, but this time FMP has genuinely recovered with a newer report
    # -- the real, fresh value must win over the recovered one, and the
    # durable store must reflect that new observation, not the old one.
    _simulated_restart()
    newer_beat = {**REPORTED_BEAT, "epsActual": 2.50}
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda **kwargs: _mock_fmp_provider(
            _nvda_entries_handler([newer_beat]), **kwargs
        ),
    )

    result = run_demo_feed()

    assert result.provider_degraded is False
    nvda = next(item for item in result.items if item.entity_id == "NVDA")
    assert "2.5" in nvda.delivered_item.what_happened

    store = EarningsCacheStore(earnings_cache_store_db_path())
    persisted_report, persisted_observed_at = store.load_all()["NVDA"]
    store.close()
    assert persisted_report.actual_eps == 2.50
    assert persisted_observed_at > backdated
