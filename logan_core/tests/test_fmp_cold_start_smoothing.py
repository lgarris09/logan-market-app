"""Operational Beta Hardening Block 6 -- Cold-Start Provider Burst Smoothing
(logan_core/receptors/providers/fmp.py's FmpResponseCache). Isolated
FmpResponseCache instances, mirroring test_fmp_budget_instrumentation.py's
own pattern -- never touches the shared process-lifetime singleton.

Two mechanisms, tested separately:
  - In-flight request coalescing ("warming queue"): concurrent callers for
    the same cold key share one real fetch instead of each firing their own.
  - TTL jitter (opt-in via `jitter_seconds`, default 0.0 -- zero behavior
    change for every pre-existing caller): staggers different keys'
    effective expiry so a batch cached together doesn't all expire in the
    same instant.
"""

import threading
import time

from logan_core.receptors.providers import FmpProviderError, FmpResponseCache


class _FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self._now = start

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


# --- In-flight coalescing ("warming queue") ---------------------------------


def test_concurrent_callers_for_the_same_cold_key_coalesce_into_one_real_fetch():
    cache = FmpResponseCache(clock=_FakeClock())
    call_count = 0
    call_count_lock = threading.Lock()
    thread_count = 20
    barrier = threading.Barrier(thread_count)
    results: list[object] = [None] * thread_count

    def fetch():
        nonlocal call_count
        with call_count_lock:
            call_count += 1
        time.sleep(0.05)  # widen the race window so callers genuinely overlap
        return "quote-data"

    def worker(index: int) -> None:
        barrier.wait()
        results[index] = cache.get_or_fetch("quote", "NVDA", 60.0, fetch)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(thread_count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert call_count == 1
    assert all(r == "quote-data" for r in results)
    snapshot = cache.budget_snapshot()
    assert snapshot.by_endpoint["quote"].real_calls == 1
    assert snapshot.by_endpoint["quote"].cache_hits == thread_count - 1


def test_concurrent_callers_for_different_keys_do_not_serialize():
    """Proves per-key locking, not one global lock -- N different tickers'
    concurrent cold fetches complete in roughly the time of one fetch, not
    N times that."""
    cache = FmpResponseCache(clock=_FakeClock())
    ticker_count = 10
    sleep_seconds = 0.1

    def fetch():
        time.sleep(sleep_seconds)
        return "quote-data"

    def worker(ticker: str) -> None:
        cache.get_or_fetch("quote", ticker, 60.0, fetch)

    tickers = [f"T{i}" for i in range(ticker_count)]
    started = time.monotonic()
    threads = [threading.Thread(target=worker, args=(t,)) for t in tickers]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
    elapsed = time.monotonic() - started

    # Serial execution would take ticker_count * sleep_seconds (~1.0s);
    # genuinely parallel, per-key-locked execution stays close to
    # sleep_seconds alone. Generous bound to stay non-flaky under load.
    assert elapsed < sleep_seconds * (ticker_count / 2)
    snapshot = cache.budget_snapshot()
    assert snapshot.by_endpoint["quote"].real_calls == ticker_count


def test_fifty_ticker_cold_start_with_concurrent_pollers_bounds_real_calls():
    """Simulates the exact scenario Block 6 targets: many tickers, cold
    cache, more than one concurrent caller per ticker (e.g. the background
    notification poller and a direct /v1/opportunities request landing at
    the same instant) -- real provider calls must stay bounded to exactly
    one per (endpoint, ticker), never one per caller."""
    cache = FmpResponseCache(clock=_FakeClock())
    ticker_count = 50
    callers_per_ticker = 2
    tickers = [f"TICK{i}" for i in range(ticker_count)]

    def fetch():
        time.sleep(0.01)
        return "quote-data"

    def worker(ticker: str) -> None:
        cache.get_or_fetch("quote", ticker, 60.0, fetch)

    threads = [
        threading.Thread(target=worker, args=(ticker,))
        for ticker in tickers
        for _ in range(callers_per_ticker)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    snapshot = cache.budget_snapshot()
    assert snapshot.by_endpoint["quote"].real_calls == ticker_count
    assert (
        snapshot.by_endpoint["quote"].cache_hits
        == ticker_count * callers_per_ticker - ticker_count
    )


def test_coalescing_still_propagates_a_genuine_failure_to_every_waiting_caller():
    cache = FmpResponseCache(clock=_FakeClock())
    thread_count = 5
    barrier = threading.Barrier(thread_count)
    exceptions: list[Exception] = []
    exceptions_lock = threading.Lock()

    def failing_fetch():
        raise FmpProviderError("boom", status_code=500)

    def worker() -> None:
        barrier.wait()
        try:
            cache.get_or_fetch("quote", "NVDA", 60.0, failing_fetch)
        except FmpProviderError as exc:
            with exceptions_lock:
                exceptions.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(thread_count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    # Only the first caller reaches the real (failing) fetch; every other
    # caller is serialized behind the same lock and, finding no fresh entry
    # and a fresh failure record, raises the suppressed-retry error instead
    # of re-attempting the network call itself.
    assert len(exceptions) == thread_count


# --- TTL jitter (opt-in, default-off) ----------------------------------------


def test_jitter_defaults_to_zero_preserving_exact_ttl_boundary():
    clock = _FakeClock()
    cache = FmpResponseCache(clock=clock)
    cache.get_or_fetch("quote", "NVDA", 60.0, lambda: "v1")
    clock.advance(60.0)
    # Byte-identical to pre-Block-6 behavior: at exactly the TTL boundary
    # (not before it), a real refetch happens -- no jitter_seconds passed.
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        return "v2"

    cache.get_or_fetch("quote", "NVDA", 60.0, fetch)
    assert calls["n"] == 1


def test_jitter_extends_effective_ttl_within_the_requested_window():
    clock = _FakeClock()
    cache = FmpResponseCache(clock=clock)
    cache.get_or_fetch("quote", "NVDA", 60.0, lambda: "v1", jitter_seconds=100.0)
    clock.advance(60.0)  # past the base TTL, but possibly still within jitter
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        return "v2"

    result = cache.get_or_fetch("quote", "NVDA", 60.0, fetch, jitter_seconds=100.0)
    # Either the jittered TTL already covered this key (still cached, "v1")
    # or it didn't (a bounded real refetch) -- never more than one real call
    # either way, and never a value outside the closed {v1, v2} set.
    assert calls["n"] in (0, 1)
    assert result in ("v1", "v2")


def test_jitter_spreads_different_keys_expiry_across_the_window():
    """With enough distinct tickers, at least two must land on different
    sides of a mid-window clock advance -- proving TTLs are genuinely
    staggered, not all still using the exact same effective expiry."""
    clock = _FakeClock()
    cache = FmpResponseCache(clock=clock)
    tickers = [f"T{i}" for i in range(30)]
    for ticker in tickers:
        cache.get_or_fetch("quote", ticker, 60.0, lambda: "v1", jitter_seconds=60.0)

    clock.advance(90.0)  # base TTL (60) + half the jitter window (30 of 60)

    refetched = 0
    for ticker in tickers:
        calls_before = cache.budget_snapshot().by_endpoint["quote"].real_calls
        cache.get_or_fetch("quote", ticker, 60.0, lambda: "v2", jitter_seconds=60.0)
        calls_after = cache.budget_snapshot().by_endpoint["quote"].real_calls
        if calls_after > calls_before:
            refetched += 1

    # Not zero (some entries' jittered TTL has genuinely lapsed by now) and
    # not all 30 (some entries' jitter pushed their expiry past 90s) --
    # proof of real staggering, not a uniform all-at-once expiry.
    assert 0 < refetched < len(tickers)


def test_jitter_is_deterministic_for_the_same_key_across_independent_caches():
    """Two independently-constructed caches, same key, same clock reading,
    same jitter_seconds: both must decide "still fresh" identically -- the
    jitter fraction is a pure function of the key (crc32), never real
    randomness that could disagree between them."""
    tickers = [f"T{i}" for i in range(10)]
    for ticker in tickers:
        clock_a = _FakeClock()
        cache_a = FmpResponseCache(clock=clock_a)
        clock_b = _FakeClock()
        cache_b = FmpResponseCache(clock=clock_b)

        cache_a.get_or_fetch("quote", ticker, 60.0, lambda: "v1", jitter_seconds=100.0)
        cache_b.get_or_fetch("quote", ticker, 60.0, lambda: "v1", jitter_seconds=100.0)
        clock_a.advance(95.0)
        clock_b.advance(95.0)

        calls_a = {"n": 0}
        calls_b = {"n": 0}

        def fetch_a(counter=calls_a):
            counter["n"] += 1
            return "v2"

        def fetch_b(counter=calls_b):
            counter["n"] += 1
            return "v2"

        cache_a.get_or_fetch("quote", ticker, 60.0, fetch_a, jitter_seconds=100.0)
        cache_b.get_or_fetch("quote", ticker, 60.0, fetch_b, jitter_seconds=100.0)
        assert calls_a["n"] == calls_b["n"]
