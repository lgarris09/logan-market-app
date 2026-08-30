"""Operational Beta Live Supply V2, Block 4/11 -- FmpResponseCache's call-
budget instrumentation (real_calls/cache_hits/suppressed_negative_cache/
failures, by endpoint and by (endpoint, entity_id)). Isolated FmpResponseCache
instances with a fake clock, mirroring test_fmp_cache.py's own established
pattern -- never touches the shared process-lifetime singleton.
"""

from logan_core.receptors.providers import FmpProviderError, FmpResponseCache


class _FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self._now = start

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


def test_a_fresh_successful_fetch_counts_as_one_real_call():
    cache = FmpResponseCache(clock=_FakeClock())
    cache.get_or_fetch("quote", "NVDA", 60.0, lambda: "quote-data")
    snapshot = cache.budget_snapshot()
    assert snapshot.by_endpoint["quote"].real_calls == 1
    assert snapshot.by_endpoint["quote"].cache_hits == 0


def test_a_repeat_call_within_ttl_counts_as_a_cache_hit_not_a_real_call():
    clock = _FakeClock()
    cache = FmpResponseCache(clock=clock)
    cache.get_or_fetch("quote", "NVDA", 60.0, lambda: "quote-data")
    cache.get_or_fetch("quote", "NVDA", 60.0, lambda: "quote-data")
    snapshot = cache.budget_snapshot()
    assert snapshot.by_endpoint["quote"].real_calls == 1
    assert snapshot.by_endpoint["quote"].cache_hits == 1


def test_a_failed_fetch_counts_as_a_failure_not_a_real_call():
    cache = FmpResponseCache(clock=_FakeClock())

    def _fail():
        raise FmpProviderError("boom", status_code=500)

    try:
        cache.get_or_fetch("earnings", "NVDA", 60.0, _fail)
    except FmpProviderError:
        pass
    snapshot = cache.budget_snapshot()
    assert snapshot.by_endpoint["earnings"].failures == 1
    assert snapshot.by_endpoint["earnings"].real_calls == 0


def test_a_repeated_call_during_negative_cache_suppression_is_counted_separately():
    clock = _FakeClock()
    cache = FmpResponseCache(clock=clock)

    def _fail():
        raise FmpProviderError("boom", status_code=402)  # permanent-tier

    try:
        cache.get_or_fetch("earnings", "NVDA", 60.0, _fail)
    except FmpProviderError:
        pass
    # Second call within the suppression window never reaches `fetch` again.
    try:
        cache.get_or_fetch("earnings", "NVDA", 60.0, _fail)
    except FmpProviderError:
        pass
    snapshot = cache.budget_snapshot()
    assert snapshot.by_endpoint["earnings"].failures == 1
    assert snapshot.by_endpoint["earnings"].suppressed_negative_cache == 1


def test_counts_are_tracked_independently_per_ticker():
    cache = FmpResponseCache(clock=_FakeClock())
    cache.get_or_fetch("quote", "NVDA", 60.0, lambda: "a")
    cache.get_or_fetch("quote", "AAPL", 60.0, lambda: "b")
    cache.get_or_fetch("quote", "AAPL", 60.0, lambda: "b")
    snapshot = cache.budget_snapshot()
    assert snapshot.by_ticker[("quote", "NVDA")].real_calls == 1
    assert snapshot.by_ticker[("quote", "NVDA")].cache_hits == 0
    assert snapshot.by_ticker[("quote", "AAPL")].real_calls == 1
    assert snapshot.by_ticker[("quote", "AAPL")].cache_hits == 1
    # Endpoint-level total is the sum across tickers.
    assert snapshot.by_endpoint["quote"].real_calls == 2
    assert snapshot.by_endpoint["quote"].cache_hits == 1


def test_clear_resets_every_counter():
    cache = FmpResponseCache(clock=_FakeClock())
    cache.get_or_fetch("quote", "NVDA", 60.0, lambda: "a")
    cache.clear()
    snapshot = cache.budget_snapshot()
    assert snapshot.by_endpoint == {}
    assert snapshot.by_ticker == {}


def test_report_never_contains_an_api_key_or_secret():
    cache = FmpResponseCache(clock=_FakeClock())
    cache.get_or_fetch("earnings", "NVDA", 60.0, lambda: "a")
    report = cache.budget_snapshot().format_report()
    assert "apikey" not in report.lower()
    assert "FMP Provider Budget" in report
    assert "earnings" in report


def test_report_estimates_a_24h_rate_from_elapsed_window():
    clock = _FakeClock()
    cache = FmpResponseCache(clock=clock)
    cache.get_or_fetch("quote", "NVDA", 3600.0, lambda: "a")
    clock.advance(3600.0)  # exactly one hour elapsed
    report = cache.budget_snapshot().format_report()
    # One real call over a 1h window -> an estimated 24 calls/24h.
    assert "estimated 24h real-call rate" in report
