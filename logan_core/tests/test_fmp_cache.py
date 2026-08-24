"""Sprint 3.6.9 Remote STRATUS closeout -- FmpResponseCache. Every test here
uses httpx.MockTransport (no real network access) plus an isolated
FmpResponseCache instance with a fake, controllable clock, so cache
expiry is deterministically tested without real sleeping and without
touching the shared, process-lifetime `_shared_fmp_cache` singleton (see
conftest.py's autouse reset_fmp_cache() fixture for why that singleton is
reset between every test regardless).

Reconnaissance against the real hosted deployment (2026-08-23) found ~10,080
real FMP calls/day from the background poller alone -- already producing
real HTTP 429s within ~25 minutes -- because backend/app/logan_feed.py
constructs a fresh provider instance on every call with zero caching. This
file proves the fix at the provider-cache level; test_live_equities.py and
test_config_live_stocks.py continue to exercise the unmodified
trigger/qualification behavior above it.
"""

import httpx
import pytest

from logan_core.receptors.providers import (
    EARNINGS_CACHE_TTL_SECONDS,
    GRADE_CACHE_TTL_SECONDS,
    QUOTE_CACHE_TTL_SECONDS,
    FmpEarningsProvider,
    FmpMarketDataProvider,
    FmpProviderError,
    FmpResponseCache,
)


class _FakeClock:
    """Deterministic, manually-advanced clock for cache-expiry tests."""

    def __init__(self, start: float = 0.0) -> None:
        self._now = start

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


def _earnings_provider(handler, cache: FmpResponseCache) -> FmpEarningsProvider:
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    return FmpEarningsProvider(api_key="test-key-not-real", client=client, cache=cache)


def _market_data_provider(handler, cache: FmpResponseCache) -> FmpMarketDataProvider:
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    return FmpMarketDataProvider(
        api_key="test-key-not-real", client=client, cache=cache
    )


def _earnings_response(eps_actual: float = 1.05) -> httpx.Response:
    return httpx.Response(
        200,
        json=[
            {
                "symbol": "NVDA",
                "date": "2026-05-28",
                "epsActual": eps_actual,
                "epsEstimated": 0.98,
                "fiscalDateEnding": "2026-04-30",
            }
        ],
    )


def _quote_response(price: float = 150.0) -> httpx.Response:
    return httpx.Response(
        200,
        json=[
            {
                "symbol": "NVDA",
                "price": price,
                "previousClose": 145.0,
                "changePercentage": 3.4,
                "timestamp": 1780000000,
            }
        ],
    )


def _grade_response(action: str = "upgrade") -> httpx.Response:
    return httpx.Response(
        200,
        json=[
            {
                "symbol": "NVDA",
                "date": "2026-08-20",
                "gradingCompany": "Morgan Stanley",
                "previousGrade": "Hold",
                "newGrade": "Buy",
                "action": action,
            }
        ],
    )


# --- Cache hits avoid redundant FMP requests --------------------------------


def test_second_call_within_ttl_does_not_hit_fmp_again():
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        return _earnings_response()

    cache = FmpResponseCache(clock=_FakeClock())
    provider = _earnings_provider(handler, cache)

    first = provider.fetch_latest_earnings("NVDA")
    second = provider.fetch_latest_earnings("NVDA")

    assert call_count == 1  # the real HTTP handler only ran once
    assert first is second  # the exact cached object, not a re-parsed copy


def test_cache_hit_works_across_distinct_provider_instances_sharing_one_cache():
    """The whole point: backend/app/logan_feed.py constructs a fresh provider
    instance on every call. A cache that only worked within one instance's
    lifetime would not actually fix anything."""
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        return _earnings_response()

    cache = FmpResponseCache(clock=_FakeClock())
    first_instance = _earnings_provider(handler, cache)
    second_instance = _earnings_provider(handler, cache)

    first_instance.fetch_latest_earnings("NVDA")
    second_instance.fetch_latest_earnings("NVDA")

    assert call_count == 1


# --- Expiry causes a real re-fetch ------------------------------------------


def test_expired_earnings_entry_triggers_a_real_refetch():
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        return _earnings_response()

    clock = _FakeClock()
    cache = FmpResponseCache(clock=clock)
    provider = _earnings_provider(handler, cache)

    provider.fetch_latest_earnings("NVDA")
    clock.advance(EARNINGS_CACHE_TTL_SECONDS + 1)
    provider.fetch_latest_earnings("NVDA")

    assert call_count == 2


def test_earnings_entry_still_cached_one_second_before_expiry():
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        return _earnings_response()

    clock = _FakeClock()
    cache = FmpResponseCache(clock=clock)
    provider = _earnings_provider(handler, cache)

    provider.fetch_latest_earnings("NVDA")
    clock.advance(EARNINGS_CACHE_TTL_SECONDS - 1)
    provider.fetch_latest_earnings("NVDA")

    assert call_count == 1


def test_quote_ttl_is_shorter_than_earnings_ttl():
    """Direct assertion of the owner's endpoint-appropriate-TTL requirement,
    not just the resulting call counts."""
    assert (
        QUOTE_CACHE_TTL_SECONDS < GRADE_CACHE_TTL_SECONDS < EARNINGS_CACHE_TTL_SECONDS
    )


def test_expired_quote_entry_triggers_a_real_refetch():
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        return _quote_response()

    clock = _FakeClock()
    cache = FmpResponseCache(clock=clock)
    provider = _market_data_provider(handler, cache)

    provider.fetch_quote("NVDA")
    clock.advance(QUOTE_CACHE_TTL_SECONDS + 1)
    provider.fetch_quote("NVDA")

    assert call_count == 2


def test_expired_grade_entry_triggers_a_real_refetch():
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        return _grade_response()

    clock = _FakeClock()
    cache = FmpResponseCache(clock=clock)
    provider = _market_data_provider(handler, cache)

    provider.fetch_latest_grade_change("NVDA")
    clock.advance(GRADE_CACHE_TTL_SECONDS + 1)
    provider.fetch_latest_grade_change("NVDA")

    assert call_count == 2


# --- Separation between tickers and endpoints -------------------------------


def test_different_tickers_are_cached_independently():
    seen_symbols = []

    def handler(request):
        symbol = dict(request.url.params)["symbol"]
        seen_symbols.append(symbol)
        return httpx.Response(
            200,
            json=[
                {
                    "symbol": symbol,
                    "date": "2026-05-28",
                    "epsActual": 1.0,
                    "epsEstimated": 0.9,
                }
            ],
        )

    cache = FmpResponseCache(clock=_FakeClock())
    provider = _earnings_provider(handler, cache)

    provider.fetch_latest_earnings("NVDA")
    provider.fetch_latest_earnings("AAPL")
    provider.fetch_latest_earnings("NVDA")  # cache hit, not a third real call

    assert seen_symbols == ["NVDA", "AAPL"]


def test_earnings_and_quote_caches_do_not_collide_for_the_same_ticker():
    """Both endpoints are fetched for the same ticker (NVDA) in a real
    pipeline run -- the cache key must include the endpoint, not just the
    ticker, or one would silently overwrite the other."""
    earnings_calls = 0
    quote_calls = 0

    def earnings_handler(request):
        nonlocal earnings_calls
        earnings_calls += 1
        return _earnings_response()

    def quote_handler(request):
        nonlocal quote_calls
        quote_calls += 1
        return _quote_response()

    cache = FmpResponseCache(clock=_FakeClock())
    earnings_provider = _earnings_provider(earnings_handler, cache)
    quote_provider = _market_data_provider(quote_handler, cache)

    earnings_provider.fetch_latest_earnings("NVDA")
    quote_provider.fetch_quote("NVDA")
    earnings_provider.fetch_latest_earnings("NVDA")
    quote_provider.fetch_quote("NVDA")

    assert earnings_calls == 1
    assert quote_calls == 1


# --- Provider errors are never cached ---------------------------------------


def test_rate_limit_error_is_not_cached_next_call_retries():
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(429, text="rate limited")

    cache = FmpResponseCache(clock=_FakeClock())
    provider = _earnings_provider(handler, cache)

    with pytest.raises(FmpProviderError):
        provider.fetch_latest_earnings("NVDA")
    with pytest.raises(FmpProviderError):
        provider.fetch_latest_earnings("NVDA")

    assert call_count == 2  # never remembered as "no data" -- retried both times


def test_error_does_not_poison_a_later_successful_response():
    responses = [httpx.Response(429, text="rate limited"), _earnings_response()]

    def handler(request):
        return responses.pop(0)

    cache = FmpResponseCache(clock=_FakeClock())
    provider = _earnings_provider(handler, cache)

    with pytest.raises(FmpProviderError):
        provider.fetch_latest_earnings("NVDA")

    report = provider.fetch_latest_earnings("NVDA")
    assert report is not None
    assert report.actual_eps == 1.05


def test_legitimate_no_data_response_is_cached_not_treated_as_an_error():
    """A real, empty FMP response (no earnings on file) is not an error --
    it should be cached like any other real response, not re-fetched every
    call the way a genuine error is."""
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json=[])

    cache = FmpResponseCache(clock=_FakeClock())
    provider = _earnings_provider(handler, cache)

    first = provider.fetch_latest_earnings("NVDA")
    second = provider.fetch_latest_earnings("NVDA")

    assert first is None
    assert second is None
    assert call_count == 1


# --- Shared-cache path (the actual production topology) ---------------------


def test_two_independently_constructed_providers_share_the_module_default_cache(
    monkeypatch,
):
    """backend/app/logan_feed.py never passes a `cache=` argument -- both the
    background poller (via get_alert_eligible_items) and a direct
    /v1/opportunities request constructing their own fresh
    FmpEarningsProvider() must land on the same shared module-level cache by
    default, not two independent ones."""
    from logan_core.receptors.providers import fmp as fmp_module

    monkeypatch.setenv("FMP_API_KEY", "test-key-not-real")
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        return _earnings_response()

    client = httpx.Client(transport=httpx.MockTransport(handler))

    # No `cache=` passed -- both instances resolve to fmp_module._shared_fmp_cache.
    poller_style_provider = fmp_module.FmpEarningsProvider(client=client)
    direct_request_style_provider = fmp_module.FmpEarningsProvider(client=client)

    poller_style_provider.fetch_latest_earnings("NVDA")
    direct_request_style_provider.fetch_latest_earnings("NVDA")

    assert call_count == 1


# --- Live/demo integrity remains intact -------------------------------------


def test_cached_beat_result_still_produces_the_same_trigger_evaluation():
    """The cache must be transparent to trigger evaluation -- a cached
    EarningsReport feeds evaluate_earnings_beat_condition() identically to a
    freshly-fetched one. Guards against the cache accidentally changing what
    downstream intelligence sees."""
    from logan_core.trigger_detection.stocks import evaluate_earnings_beat_condition

    def handler(request):
        return _earnings_response(eps_actual=1.87)

    cache = FmpResponseCache(clock=_FakeClock())
    provider = _earnings_provider(handler, cache)

    fresh = provider.fetch_latest_earnings("NVDA")
    cached = provider.fetch_latest_earnings("NVDA")  # served from cache
    assert fresh is not None
    assert cached is not None

    fired_fresh, _, _ = evaluate_earnings_beat_condition(
        fresh.actual_eps, fresh.consensus_eps
    )
    fired_cached, _, _ = evaluate_earnings_beat_condition(
        cached.actual_eps, cached.consensus_eps
    )
    assert fired_fresh is True
    assert fired_cached is True
    assert fresh.actual_eps == cached.actual_eps == 1.87


def test_a_rate_limited_ticker_produces_no_cached_fallback_data():
    """Live-data integrity: when FMP is unavailable and nothing valid was
    ever cached, the caller must see a real error (leading to honest
    absence upstream), never a fabricated or stale-disguised-as-fresh
    result."""

    def handler(request):
        return httpx.Response(429, text="rate limited")

    cache = FmpResponseCache(clock=_FakeClock())
    provider = _earnings_provider(handler, cache)

    with pytest.raises(FmpProviderError):
        provider.fetch_latest_earnings("NVDA")
