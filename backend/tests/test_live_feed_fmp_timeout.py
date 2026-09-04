"""2026-09-04 incident response (STRATUS 3.6.12) -- regression coverage for
the narrow live-feed FMP timeout reduction.

Incident: a real FMP-side TLS handshake stall held live-feed worker threads
for up to the full 10s default (FmpEarningsProvider/FmpMarketDataProvider's
class default, logan_core/receptors/providers/fmp.py) per failing call,
repeatedly, contributing to ~17 minutes of degraded/unavailable /health (see
the Master Plan incident log). Fix: backend/app/logan_feed.py's four
provider-instantiation call sites now pass an explicit
client=httpx.Client(timeout=LIVE_FEED_FMP_TIMEOUT_SECONDS) -- bounded to the
live-feed path only. The monthly reevaluation path
(backend/app/universe_manager.py) is deliberately untouched -- it already
has its own ProviderScheduler-based pacing and is a background batch job,
not a request-blocking one.
"""

import inspect
from datetime import datetime, timezone

import httpx
import pytest

import backend.app.logan_feed as logan_feed
import backend.app.universe_manager as universe_manager
from backend.app.logan_feed import (
    LIVE_FEED_FMP_TIMEOUT_SECONDS,
    _live_price_move_raw_signal,
)
from logan_core.receptors.providers import (
    FmpEarningsProvider,
    FmpMarketDataProvider,
    FmpProviderError,
)


def _network_error_handler(request: httpx.Request) -> httpx.Response:
    # No real network access from any test in this file -- every request
    # fails immediately and deterministically via MockTransport.
    raise httpx.ConnectError("no real network in this test")


def test_timeout_value_is_within_the_approved_incident_response_range():
    # Approved range per the incident decision: 3-4 seconds, materially
    # shorter than the 10s default that let a single stuck call hold a
    # worker thread for up to 10x as long.
    assert 3.0 <= LIVE_FEED_FMP_TIMEOUT_SECONDS <= 4.0


def test_all_four_live_feed_provider_call_sites_use_the_bounded_timeout(monkeypatch):
    """Spies on httpx.Client construction (real construction still happens,
    even when the provider class itself is later mocked out by other tests
    -- argument expressions evaluate before the call) and drives every one
    of logan_feed.py's four live-signal helpers, confirming each
    constructs its client with the new bounded timeout, not the 10.0s
    class default.
    """
    recorded_timeouts: list[float | None] = []

    class _SpyClient(httpx.Client):
        def __init__(self, *args, **kwargs):
            recorded_timeouts.append(kwargs.get("timeout"))
            # Never attempts real network I/O regardless of what the real
            # call site passed -- forces a deterministic MockTransport so
            # this test can never hang or reach the real internet.
            kwargs["transport"] = httpx.MockTransport(_network_error_handler)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", _SpyClient)
    monkeypatch.setenv("FMP_API_KEY", "test-key-not-real")

    now = datetime.now(timezone.utc)
    # Exercise all four call sites directly -- each constructs its own
    # provider (and therefore its own httpx.Client) independently. Every
    # one fails immediately via the mock transport above; these helpers'
    # own honest-absence handling (already covered elsewhere) means this
    # never raises.
    logan_feed._live_earnings_raw_signal("NVDA", now)
    logan_feed._live_price_move_raw_signal("NVDA", now)
    logan_feed._live_analyst_grade_raw_signal("NVDA", now)
    logan_feed._fetch_market_evidence("NVDA", now)

    assert len(recorded_timeouts) == 4
    assert all(
        t == LIVE_FEED_FMP_TIMEOUT_SECONDS for t in recorded_timeouts
    ), recorded_timeouts


def test_connect_timeout_is_caught_as_honest_failure_with_exactly_one_attempt():
    """The exact incident symptom (_ssl.c:993: The handshake operation timed
    out) maps to httpx.ConnectTimeout, a subclass of httpx.RequestError --
    confirms the existing except clause catches it (converts to
    FmpProviderError, the same honest-failure path already used for every
    other network error) and that there is no retry loop: the transport
    handler must be invoked exactly once per fetch attempt.
    """
    call_count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        raise httpx.ConnectTimeout("The handshake operation timed out")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = FmpEarningsProvider(api_key="test-key-not-real", client=client)

    with pytest.raises(FmpProviderError, match="network error"):
        provider.fetch_latest_earnings("NVDA")

    assert call_count["n"] == 1  # no retry storm


def test_market_data_provider_connect_timeout_is_also_a_single_honest_attempt():
    call_count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        raise httpx.ConnectTimeout("The handshake operation timed out")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = FmpMarketDataProvider(api_key="test-key-not-real", client=client)

    with pytest.raises(FmpProviderError, match="network error"):
        provider.fetch_quote("NVDA")

    assert call_count["n"] == 1


def test_live_feed_helper_returns_none_on_timeout_never_a_fixture(monkeypatch):
    """Reproduces the incident's real code path (_live_price_move_raw_signal,
    the function actually seen skipping 'PLD'/'SLB' quotes on 2026-09-04)
    with a raised ConnectTimeout instead of a real network stall -- confirms
    the honest-absence contract (None, no fixture substitution) that was
    already true for HTTP-status failures also holds for a raised network
    timeout, and that nothing here silently retries."""
    call_count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        raise httpx.ConnectTimeout("The handshake operation timed out")

    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        lambda *a, **kw: FmpMarketDataProvider(
            api_key="test-key-not-real",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        ),
    )

    result = _live_price_move_raw_signal("NVDA", datetime.now(timezone.utc))

    assert result is None  # honest absence, never a fabricated/fixture signal
    assert call_count["n"] == 1


def test_reevaluation_path_is_untouched_still_uses_the_class_default_timeout():
    """Narrow-scope guard: the monthly reevaluation path
    (universe_manager.py) must not reference the new live-feed-only
    constant, and must still construct its providers with no explicit
    client override (the class default, 10.0s) -- it already has its own
    ProviderScheduler-based pacing and is a background batch job, not a
    request-blocking one. Broader ProviderScheduler integration for the
    live-feed path is an explicit HOLD item, not part of this fix."""
    source = inspect.getsource(universe_manager)
    assert "LIVE_FEED_FMP_TIMEOUT_SECONDS" not in source
    assert "FmpMarketDataProvider()" in source
    assert "FmpEarningsProvider()" in source
