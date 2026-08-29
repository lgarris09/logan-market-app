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
    EARNINGS_STALE_GRACE_SECONDS,
    GRADE_CACHE_TTL_SECONDS,
    PERMANENT_FAILURE_SUPPRESSION_SECONDS,
    QUOTE_CACHE_TTL_SECONDS,
    TRANSIENT_FAILURE_SUPPRESSION_SECONDS,
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


# --- Provider errors are never cached AS DATA, but a repeat of a known ------
# --- failure is suppressed rather than retried on every single call --------
#
# 2026-08-29 field fix: get_or_fetch previously had no memory of a failure at
# all, so a persistent outage (a sustained 429, or FMP's stable /quote
# endpoint permanently rejecting a symbol with 402) was retried on every
# single poll -- up to 1,440 wasted calls/day for one (endpoint, entity_id)
# pair at the 60-second poll cadence. These tests cover the negative-cache
# suppression window itself; a fetch that ultimately fails still never
# produces a fabricated value in any of them -- every suppressed retry
# raises FmpProviderError, exactly like a fresh failed fetch would.


def test_repeated_failure_within_suppression_window_does_not_hit_fmp_again():
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
    with pytest.raises(FmpProviderError):
        provider.fetch_latest_earnings("NVDA")

    # The real HTTP handler ran exactly once -- the second and third calls
    # were suppressed from the remembered failure, never fabricating a
    # value, never silently succeeding either (all three raised).
    assert call_count == 1


def test_transient_failure_suppression_expires_and_then_retries():
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(429, text="rate limited")

    clock = _FakeClock()
    cache = FmpResponseCache(clock=clock)
    provider = _earnings_provider(handler, cache)

    with pytest.raises(FmpProviderError):
        provider.fetch_latest_earnings("NVDA")
    assert call_count == 1

    clock.advance(TRANSIENT_FAILURE_SUPPRESSION_SECONDS - 1)
    with pytest.raises(FmpProviderError):
        provider.fetch_latest_earnings("NVDA")
    assert call_count == 1  # still inside the 15-minute window -- suppressed

    clock.advance(2)  # now past the window
    with pytest.raises(FmpProviderError):
        provider.fetch_latest_earnings("NVDA")
    assert call_count == 2  # a genuine recovery check, not withheld forever


def test_error_does_not_poison_a_later_successful_response():
    responses = [httpx.Response(429, text="rate limited"), _earnings_response()]

    def handler(request):
        return responses.pop(0)

    clock = _FakeClock()
    cache = FmpResponseCache(clock=clock)
    provider = _earnings_provider(handler, cache)

    with pytest.raises(FmpProviderError):
        provider.fetch_latest_earnings("NVDA")

    clock.advance(TRANSIENT_FAILURE_SUPPRESSION_SECONDS + 1)
    report = provider.fetch_latest_earnings("NVDA")
    assert report is not None
    assert report.actual_eps == 1.05


def test_permanent_entitlement_failure_uses_the_longer_suppression_window():
    """FMP's stable /quote endpoint returns a genuine, permanent HTTP 402
    for a symbol not covered by this plan (the real, confirmed XLK case --
    see docs/DECISIONS.md) -- fundamentally different from a transient 429.
    Retrying it every 15 minutes like a rate limit would still waste calls
    on a request that is never going to start succeeding on its own; it
    gets the much longer 24-hour window instead."""
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(402, text="Premium Query Parameter")

    clock = _FakeClock()
    cache = FmpResponseCache(clock=clock)
    provider = _market_data_provider(handler, cache)

    with pytest.raises(FmpProviderError):
        provider.fetch_benchmark_quote("XLK")
    assert call_count == 1

    # Well past the transient (15-minute) window, nowhere near the
    # permanent (24-hour) one -- must still be suppressed, not retried like
    # an ordinary rate limit would be.
    clock.advance(TRANSIENT_FAILURE_SUPPRESSION_SECONDS + 1)
    with pytest.raises(FmpProviderError):
        provider.fetch_benchmark_quote("XLK")
    assert call_count == 1

    clock.advance(PERMANENT_FAILURE_SUPPRESSION_SECONDS + 1)
    with pytest.raises(FmpProviderError):
        provider.fetch_benchmark_quote("XLK")
    assert call_count == 2  # a full day later, one honest re-check


def test_success_replaces_failure_state_and_is_served_on_the_next_call():
    """The negative state never outlives the condition that created it --
    once a real fetch succeeds, that success (never the stale failure) is
    what the very next call sees."""
    responses = [httpx.Response(429, text="rate limited"), _quote_response(201.0)]

    def handler(request):
        return responses.pop(0)

    clock = _FakeClock()
    cache = FmpResponseCache(clock=clock)
    provider = _market_data_provider(handler, cache)

    with pytest.raises(FmpProviderError):
        provider.fetch_quote("NVDA")

    clock.advance(TRANSIENT_FAILURE_SUPPRESSION_SECONDS + 1)
    quote = provider.fetch_quote("NVDA")
    assert quote is not None
    assert quote.price == 201.0

    # Still well inside what would have been the old suppression window --
    # must serve the fresh success from cache, never re-raise the old error.
    again = provider.fetch_quote("NVDA")
    assert again is quote


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


# --- Stale-serve-on-refetch-failure grace window (V2.3A.1 field fix) -------
#
# Real production incident (2026-08-28): NVDA's real, notification-worthy
# earnings beat (reported 2026-08-26) intermittently vanished from the feed
# entirely ("Nothing to show yet") on polls where FMP's daily quota was
# exhausted at the exact moment this entity's 6-hour earnings cache entry
# expired and a refetch was attempted -- a purely transient refetch failure,
# not a real "no qualifying earnings" result, but get_or_fetch's original
# behavior (correctly uncached-on-error, so a genuine outage is retried
# rather than remembered as "no data") made the two indistinguishable to
# every caller above it.


def test_stale_earnings_are_served_when_a_refetch_fails_within_the_grace_window():
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _earnings_response(eps_actual=1.05)
        return httpx.Response(429, text="rate limited")

    clock = _FakeClock()
    cache = FmpResponseCache(clock=clock)
    provider = _earnings_provider(handler, cache)

    first = provider.fetch_latest_earnings("NVDA")
    assert first is not None
    assert first.actual_eps == 1.05

    # Past the 6h TTL (a real refetch is now attempted), but nowhere near
    # the 24h grace window on top of it -- the refetch fails (quota outage),
    # and the still-recent, still-correct report is served instead of the
    # entity disappearing.
    clock.advance(EARNINGS_CACHE_TTL_SECONDS + 60)
    second = provider.fetch_latest_earnings("NVDA")

    assert second is not None
    assert second.actual_eps == 1.05
    assert call_count == 2  # the refetch was genuinely attempted, not skipped


def test_stale_earnings_grace_expires_eventually_and_then_raises():
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _earnings_response()
        return httpx.Response(429, text="rate limited")

    clock = _FakeClock()
    cache = FmpResponseCache(clock=clock)
    provider = _earnings_provider(handler, cache)

    provider.fetch_latest_earnings("NVDA")
    # Past both the TTL *and* the full stale grace window -- a report this
    # old, during an outage this long, is no longer safe to keep presenting
    # as current; this must fail loudly, the same as the pre-fix behavior,
    # not silently keep serving increasingly ancient data forever.
    clock.advance(EARNINGS_CACHE_TTL_SECONDS + EARNINGS_STALE_GRACE_SECONDS + 1)

    with pytest.raises(FmpProviderError):
        provider.fetch_latest_earnings("NVDA")


def test_a_successful_refetch_within_the_grace_window_still_updates_the_cache():
    """The grace window is a fallback for *failures*, not a reason to stop
    trying -- once FMP recovers, the next real success must replace the
    stale value and reset the TTL clock, not keep serving the old one."""
    responses_served = []

    def handler(request):
        response = _earnings_response(eps_actual=1.05 if not responses_served else 2.22)
        responses_served.append(response)
        return response

    clock = _FakeClock()
    cache = FmpResponseCache(clock=clock)
    provider = _earnings_provider(handler, cache)

    first = provider.fetch_latest_earnings("NVDA")
    assert first.actual_eps == 1.05

    clock.advance(EARNINGS_CACHE_TTL_SECONDS + 60)
    second = provider.fetch_latest_earnings("NVDA")

    assert second.actual_eps == 2.22  # the real, newer report -- not stale 1.05


def test_quotes_still_fail_immediately_on_a_refetch_error_no_stale_grace():
    """Deliberate asymmetry: quotes are the genuinely freshness-sensitive
    path (Sprint 3.6.9's own reasoning for QUOTE_CACHE_TTL_SECONDS being the
    shortest TTL) -- serving a stale price as if current would be actively
    misleading, unlike a quarterly earnings report. fetch_quote must never
    opt into the earnings-only grace window."""
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _quote_response(price=150.0)
        return httpx.Response(429, text="rate limited")

    clock = _FakeClock()
    cache = FmpResponseCache(clock=clock)
    provider = _market_data_provider(handler, cache)

    provider.fetch_quote("NVDA")
    clock.advance(QUOTE_CACHE_TTL_SECONDS + 1)

    with pytest.raises(FmpProviderError):
        provider.fetch_quote("NVDA")


# --- Restart-recovery seeding (V2.3A.1 field reliability work) -------------
#
# A hosted-production audit (2026-08-28/29) confirmed live that d482af8's
# stale-grace fix above only protects an outage that happens *while the
# process keeps running* -- FmpResponseCache is process-lifetime, in-memory
# only, so a restart during an ongoing FMP outage empties it along with
# everything else, leaving grace with nothing to fall back to until this
# process's own first successful fetch. seed_stale_entry (and
# backend/app/earnings_cache_store.py's durable store, which calls it via
# seed_earnings_from_durable_observation) closes that gap. These tests cover
# the generic cache primitive directly; test_earnings_cache_persistence.py
# (backend/tests/) covers the full durable-store/restart integration.


def test_seed_stale_entry_lets_a_refetch_failure_fall_back_immediately():
    """A freshly-started process, seeded with a recovered observation, must
    be able to serve it on the very first call if FMP is already down --
    with zero prior in-process fetch of its own."""

    def handler(request):
        return httpx.Response(429, text="rate limited")

    from logan_core.receptors.providers import EarningsReport

    clock = _FakeClock(start=1000.0)
    cache = FmpResponseCache(clock=clock)
    provider = _earnings_provider(handler, cache)
    report = EarningsReport(
        entity_id="NVDA",
        actual_eps=1.87,
        consensus_eps=0.98,
        source_id="fmp",
        source_name="Financial Modeling Prep",
        report_timestamp="2026-08-26T00:00:00+00:00",
    )
    # Seeded as though observed 1 hour ago -- well within both the 6h TTL and
    # the 24h grace window on top of it.
    cache.seed_stale_entry("earnings", "NVDA", report, age_seconds=60 * 60)

    result = provider.fetch_latest_earnings("NVDA")

    assert result is not None
    assert result.actual_eps == 1.87


def test_seeded_entry_within_ttl_is_served_without_any_fetch_attempt():
    """A recovered observation younger than the normal TTL should behave
    exactly like any other still-fresh cache entry -- no network call at all,
    not even an attempted one."""
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(429, text="rate limited")

    from logan_core.receptors.providers import EarningsReport

    clock = _FakeClock(start=5000.0)
    cache = FmpResponseCache(clock=clock)
    provider = _earnings_provider(handler, cache)
    report = EarningsReport(
        entity_id="NVDA",
        actual_eps=2.22,
        consensus_eps=2.09,
        source_id="fmp",
        source_name="Financial Modeling Prep",
        report_timestamp="2026-08-26T00:00:00+00:00",
    )
    cache.seed_stale_entry("earnings", "NVDA", report, age_seconds=60)

    result = provider.fetch_latest_earnings("NVDA")

    assert result is not None
    assert result.actual_eps == 2.22
    assert call_count == 0  # served straight from the seeded entry, TTL-fresh


def test_seeded_entry_outside_ttl_but_within_grace_is_served_on_failure():
    def handler(request):
        return httpx.Response(429, text="rate limited")

    from logan_core.receptors.providers import EarningsReport

    clock = _FakeClock(start=0.0)
    cache = FmpResponseCache(clock=clock)
    provider = _earnings_provider(handler, cache)
    report = EarningsReport(
        entity_id="NVDA",
        actual_eps=1.87,
        consensus_eps=0.98,
        source_id="fmp",
        source_name="Financial Modeling Prep",
        report_timestamp="2026-08-26T00:00:00+00:00",
    )
    # Past the 6h TTL (a real refetch is attempted) but nowhere near the
    # additional 24h grace window -- the same shape as
    # test_stale_earnings_are_served_when_a_refetch_fails_within_the_grace_window
    # above, except the entry came from durable recovery, not this process's
    # own earlier fetch.
    cache.seed_stale_entry(
        "earnings", "NVDA", report, age_seconds=EARNINGS_CACHE_TTL_SECONDS + 60
    )

    result = provider.fetch_latest_earnings("NVDA")

    assert result is not None
    assert result.actual_eps == 1.87


def test_seeded_entry_outside_ttl_and_grace_is_rejected():
    def handler(request):
        return httpx.Response(429, text="rate limited")

    from logan_core.receptors.providers import EarningsReport

    clock = _FakeClock(start=0.0)
    cache = FmpResponseCache(clock=clock)
    provider = _earnings_provider(handler, cache)
    report = EarningsReport(
        entity_id="NVDA",
        actual_eps=1.87,
        consensus_eps=0.98,
        source_id="fmp",
        source_name="Financial Modeling Prep",
        report_timestamp="2026-08-26T00:00:00+00:00",
    )
    # A durably-recovered observation this old is no longer safe to present
    # as current, exactly like a same-process entry that aged past grace --
    # this must fail loudly, not silently keep serving ancient data forever.
    cache.seed_stale_entry(
        "earnings",
        "NVDA",
        report,
        age_seconds=EARNINGS_CACHE_TTL_SECONDS + EARNINGS_STALE_GRACE_SECONDS + 1,
    )

    with pytest.raises(FmpProviderError):
        provider.fetch_latest_earnings("NVDA")


def test_a_successful_fetch_replaces_a_recovered_seeded_value():
    """Recovery is a bridge, not a ceiling -- once FMP responds again, the
    real, newer report must replace the recovered one and reset the TTL
    clock, exactly like the same-process grace-recovery precedent above."""
    from logan_core.receptors.providers import EarningsReport

    def handler(request):
        return _earnings_response(eps_actual=2.22)

    clock = _FakeClock(start=0.0)
    cache = FmpResponseCache(clock=clock)
    provider = _earnings_provider(handler, cache)
    old_report = EarningsReport(
        entity_id="NVDA",
        actual_eps=1.05,
        consensus_eps=0.98,
        source_id="fmp",
        source_name="Financial Modeling Prep",
        report_timestamp="2026-05-28T00:00:00+00:00",
    )
    cache.seed_stale_entry(
        "earnings", "NVDA", old_report, age_seconds=EARNINGS_CACHE_TTL_SECONDS + 60
    )

    result = provider.fetch_latest_earnings("NVDA")

    assert result.actual_eps == 2.22  # the real, fresh report -- not the seeded 1.05


# --- on_successful_fetch: the durable-persistence write hook ---------------


def test_on_successful_fetch_fires_once_for_a_genuine_fresh_success():
    observations = []

    def handler(request):
        return _earnings_response(eps_actual=1.87)

    cache = FmpResponseCache(clock=_FakeClock())
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    provider = FmpEarningsProvider(
        api_key="test-key-not-real",
        client=client,
        cache=cache,
        on_successful_fetch=lambda entity_id, report, observed_at: observations.append(
            (entity_id, report, observed_at)
        ),
    )

    report = provider.fetch_latest_earnings("NVDA")

    assert len(observations) == 1
    entity_id, observed_report, observed_at = observations[0]
    assert entity_id == "NVDA"
    assert observed_report is report
    assert observed_at is not None


def test_on_successful_fetch_does_not_fire_on_a_cache_hit():
    """The whole point of persisting only genuine observations: a TTL cache
    hit never calls FMP at all, so it must never re-report itself as a new
    observation either."""
    observations = []

    def handler(request):
        return _earnings_response(eps_actual=1.87)

    cache = FmpResponseCache(clock=_FakeClock())
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    provider = FmpEarningsProvider(
        api_key="test-key-not-real",
        client=client,
        cache=cache,
        on_successful_fetch=lambda entity_id, report, observed_at: observations.append(
            entity_id
        ),
    )

    provider.fetch_latest_earnings("NVDA")
    provider.fetch_latest_earnings("NVDA")  # served from cache, no real fetch

    assert len(observations) == 1


def test_on_successful_fetch_never_fires_on_a_failure():
    def handler(request):
        return httpx.Response(429, text="rate limited")

    observations = []
    cache = FmpResponseCache(clock=_FakeClock())
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    provider = FmpEarningsProvider(
        api_key="test-key-not-real",
        client=client,
        cache=cache,
        on_successful_fetch=lambda entity_id, report, observed_at: observations.append(
            entity_id
        ),
    )

    with pytest.raises(FmpProviderError):
        provider.fetch_latest_earnings("NVDA")

    assert observations == []


def test_on_successful_fetch_does_not_fire_for_a_genuine_no_data_result():
    """A real 'no earnings on file' None is a successful call, but there is
    no payload to persist for restart-recovery purposes -- the callback is
    earnings-report-shaped, not a generic 'any successful call' hook."""
    observations = []

    def handler(request):
        return httpx.Response(200, json=[])

    cache = FmpResponseCache(clock=_FakeClock())
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    provider = FmpEarningsProvider(
        api_key="test-key-not-real",
        client=client,
        cache=cache,
        on_successful_fetch=lambda entity_id, report, observed_at: observations.append(
            entity_id
        ),
    )

    result = provider.fetch_latest_earnings("NVDA")

    assert result is None
    assert observations == []


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
