"""Universe Manager V1a Block 7 -- ProviderScheduler (logan_core/receptors/
providers/scheduler.py). Deterministic tests via an injectable fake
clock/sleep -- no real wall-clock waiting, mirroring FmpResponseCache's own
established fake-clock test pattern.
"""

import threading

from logan_core.receptors.providers import (
    CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    ProviderScheduler,
    ProviderSchedulerSaturatedError,
    warm_start_delays,
)


class _FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self._now = start
        self._lock = threading.Lock()

    def __call__(self) -> float:
        with self._lock:
            return self._now

    def advance(self, seconds: float) -> None:
        with self._lock:
            self._now += seconds


def _fake_sleep_factory(clock: _FakeClock):
    def _sleep(seconds: float) -> None:
        clock.advance(seconds)

    return _sleep


def _scheduler(
    global_ceiling=220, per_endpoint_ceiling_fraction=0.60
) -> tuple[ProviderScheduler, _FakeClock]:
    clock = _FakeClock()
    sched = ProviderScheduler(
        clock=clock,
        sleep=_fake_sleep_factory(clock),
        global_ceiling=global_ceiling,
        per_endpoint_ceiling_fraction=per_endpoint_ceiling_fraction,
    )
    return sched, clock


# --- basic admission ----------------------------------------------------------


def test_acquire_succeeds_immediately_when_under_budget():
    sched, _ = _scheduler()
    assert sched.acquire("quote") is True


def test_current_calls_per_minute_reflects_admitted_calls():
    sched, _ = _scheduler()
    for _ in range(5):
        sched.acquire("quote")
    assert sched.current_calls_per_minute("quote") == 5
    assert sched.current_calls_per_minute() == 5


def test_global_ceiling_is_never_exceeded():
    # per_endpoint_ceiling_fraction=1.0 isolates the global ceiling itself --
    # a single endpoint's own budget must not be the more restrictive limit
    # in this test.
    sched, clock = _scheduler(global_ceiling=10, per_endpoint_ceiling_fraction=1.0)
    admitted = 0
    for _ in range(10):
        if sched.acquire("quote", max_wait_seconds=0.0):
            admitted += 1
    assert admitted == 10
    # The 11th call has no capacity and no time to wait -- must be denied,
    # never silently admitted past the ceiling.
    assert sched.acquire("quote", max_wait_seconds=0.0) is False
    assert sched.current_calls_per_minute() == 10


def test_per_endpoint_ceiling_is_never_exceeded_even_with_global_headroom():
    sched, _ = _scheduler(global_ceiling=220, per_endpoint_ceiling_fraction=0.1)
    # per-endpoint ceiling = int(220*0.1) = 22
    admitted = 0
    for _ in range(30):
        if sched.acquire("quote", max_wait_seconds=0.0):
            admitted += 1
    assert admitted == 22


def test_two_endpoints_do_not_share_the_same_per_endpoint_budget():
    sched, _ = _scheduler(global_ceiling=220, per_endpoint_ceiling_fraction=0.1)
    for _ in range(22):
        assert sched.acquire("quote", max_wait_seconds=0.0) is True
    assert sched.acquire("quote", max_wait_seconds=0.0) is False
    # A different endpoint family has its own, untouched budget.
    assert sched.acquire("earnings", max_wait_seconds=0.0) is True


def test_capacity_recovers_once_the_rate_window_elapses():
    sched, clock = _scheduler(global_ceiling=5, per_endpoint_ceiling_fraction=1.0)
    for _ in range(5):
        assert sched.acquire("quote", max_wait_seconds=0.0) is True
    assert sched.acquire("quote", max_wait_seconds=0.0) is False
    clock.advance(61.0)  # past the 60s rolling window
    assert sched.acquire("quote", max_wait_seconds=0.0) is True


def test_acquire_waits_via_the_injected_sleep_until_capacity_frees(monkeypatch):
    sched, clock = _scheduler(global_ceiling=1, per_endpoint_ceiling_fraction=1.0)
    assert sched.acquire("quote", max_wait_seconds=0.0) is True
    # No real capacity until just past the 60s rolling window -- acquire
    # must wait (via fake sleep, which advances the fake clock) rather than
    # fail immediately, since max_wait_seconds is generous.
    assert sched.acquire("quote", max_wait_seconds=120.0) is True
    assert clock() > 60.0


def test_acquire_times_out_and_returns_false_rather_than_waiting_forever():
    sched, _ = _scheduler(global_ceiling=1)
    assert sched.acquire("quote", max_wait_seconds=0.0) is True
    assert sched.acquire("quote", max_wait_seconds=1.0) is False


# --- gate() / circuit breaker --------------------------------------------------


def test_gate_calls_fetch_and_returns_its_value():
    sched, _ = _scheduler()
    result = sched.gate("quote", lambda: "quote-data")
    assert result == "quote-data"


def test_gate_raises_saturated_error_without_calling_fetch_when_no_capacity():
    sched, _ = _scheduler(global_ceiling=1)
    sched.acquire("quote", max_wait_seconds=0.0)
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        return "should-not-run"

    import pytest

    with pytest.raises(ProviderSchedulerSaturatedError):
        sched.gate("quote", fetch, max_wait_seconds=0.0)
    assert calls["n"] == 0


def test_repeated_failures_open_the_circuit_for_that_endpoint():
    sched, _ = _scheduler()

    def failing():
        raise RuntimeError("boom")

    for _ in range(CIRCUIT_BREAKER_FAILURE_THRESHOLD):
        try:
            sched.gate("quote", failing)
        except RuntimeError:
            pass
    assert sched.is_circuit_open("quote") is True


def test_open_circuit_denies_new_calls_to_that_endpoint_only():
    sched, _ = _scheduler()

    def failing():
        raise RuntimeError("boom")

    for _ in range(CIRCUIT_BREAKER_FAILURE_THRESHOLD):
        try:
            sched.gate("quote", failing)
        except RuntimeError:
            pass
    assert sched.acquire("quote", max_wait_seconds=0.0) is False
    # A different endpoint is completely unaffected.
    assert sched.acquire("earnings", max_wait_seconds=0.0) is True


def test_circuit_closes_again_after_the_open_window_elapses():
    sched, clock = _scheduler()

    def failing():
        raise RuntimeError("boom")

    for _ in range(CIRCUIT_BREAKER_FAILURE_THRESHOLD):
        try:
            sched.gate("quote", failing)
        except RuntimeError:
            pass
    assert sched.is_circuit_open("quote") is True
    clock.advance(61.0)
    assert sched.is_circuit_open("quote") is False


def test_a_success_resets_the_consecutive_failure_count():
    sched, _ = _scheduler()

    def failing():
        raise RuntimeError("boom")

    for _ in range(CIRCUIT_BREAKER_FAILURE_THRESHOLD - 1):
        try:
            sched.gate("quote", failing)
        except RuntimeError:
            pass
    sched.gate("quote", lambda: "ok")
    # One more failure should not trip the breaker -- the streak was reset.
    try:
        sched.gate("quote", failing)
    except RuntimeError:
        pass
    assert sched.is_circuit_open("quote") is False


# --- wait sample observability --------------------------------------------------


def test_wait_samples_record_priority_and_outcome():
    sched, _ = _scheduler()
    sched.acquire("quote", priority="critical")
    samples = sched.wait_samples()
    assert len(samples) == 1
    assert samples[0].endpoint == "quote"
    assert samples[0].priority == "critical"
    assert samples[0].admitted is True


def test_an_unrecognized_priority_falls_back_to_normal():
    sched, _ = _scheduler()
    sched.acquire("quote", priority="not-a-real-tier")
    assert sched.wait_samples()[0].priority == "normal"


def test_reset_clears_budgets_and_samples():
    sched, _ = _scheduler(global_ceiling=1)
    sched.acquire("quote")
    sched.reset()
    assert sched.wait_samples() == []
    assert sched.current_calls_per_minute() == 0
    assert sched.acquire("quote", max_wait_seconds=0.0) is True


# --- concurrent-caller cold-start bound (the actual Block 7 requirement) -----


def test_fifty_ticker_times_four_endpoint_cold_start_never_exceeds_the_ceiling():
    """Simulates the realistic V1a-scale cold start: 50 monitored tickers,
    4 endpoint families each, many concurrent callers (threads) all racing
    to warm the cache at once -- real admitted calls, measured over the
    scheduler's own rolling window, must never exceed the global ceiling."""
    sched, clock = _scheduler(global_ceiling=220)
    tickers = [f"T{i}" for i in range(50)]
    endpoints = ["quote", "earnings", "analyst_grade", "profile"]
    admitted_count = {"n": 0}
    admitted_lock = threading.Lock()

    def worker(endpoint: str) -> None:
        if sched.acquire(endpoint, max_wait_seconds=0.0):
            with admitted_lock:
                admitted_count["n"] += 1

    threads = [
        threading.Thread(target=worker, args=(endpoint,))
        for _ in tickers
        for endpoint in endpoints
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert admitted_count["n"] <= 220
    assert sched.current_calls_per_minute() <= 220


# --- warm_start_delays ----------------------------------------------------------


def test_warm_start_delays_spreads_entities_evenly_across_the_window():
    delays = warm_start_delays(["A", "B", "C", "D"], total_stagger_seconds=40.0)
    assert delays["A"] == 0.0
    assert delays["B"] == 10.0
    assert delays["C"] == 20.0
    assert delays["D"] == 30.0


def test_warm_start_delays_is_empty_for_no_entities():
    assert warm_start_delays([], total_stagger_seconds=60.0) == {}


def test_warm_start_delays_is_deterministic():
    entities = [f"T{i}" for i in range(25)]
    first = warm_start_delays(entities, total_stagger_seconds=60.0)
    second = warm_start_delays(entities, total_stagger_seconds=60.0)
    assert first == second
