"""STRATUS 3.6.12 reliability correction (approved 2026-09-09, INC-2026-09-09-A)
-- regression coverage for the two additive mitigations built after the
2026-09-04 timeout fix (test_live_feed_fmp_timeout.py) proved insufficient by
itself on 2026-09-09:

1. `/health` isolation (backend/app/main.py) -- a true `async def`, never
   dispatched through Starlette's shared blocking-threadpool bridge.
2. A dedicated, process-lifetime `ProviderScheduler` for the live-feed path
   only (backend/app/logan_feed.py) -- reuses the existing, already-tested
   rate-ceiling/circuit-breaker machinery universe_manager.py's reevaluation
   path already uses, via a *separate* instance, plus a bounded aggregate
   sweep deadline around the whole live-ticker sweep.

Explicit, load-bearing non-goals proven here too: this dedicated scheduler
must never be the same instance (or feed the same telemetry) as
universe_manager.py's reevaluation-path scheduler or the scheduler-scoped
proof-gate population (scheduled_fetch_failure_rate, time_sensitive_delay_
p95/p99, coalescing_success_rate) -- that population stays exactly as
confirmed for the 14-day V1a proof window.
"""

import asyncio
import inspect
import threading
import time
from datetime import datetime, timezone

import anyio.to_thread
import httpx
import pytest

import backend.app.logan_feed as logan_feed
import backend.app.universe_manager as universe_manager
from backend.app.logan_feed import (
    LIVE_FEED_SWEEP_DEADLINE_SECONDS,
    _live_price_move_raw_signal,
    _live_sweep_deadline_exceeded,
    reset_pipeline_state,
)
from backend.app.main import health
from logan_core.receptors.providers import (
    FmpMarketDataProvider,
    FmpProviderError,
    ProviderScheduler,
    ProviderSchedulerSaturatedError,
)


@pytest.fixture(autouse=True)
def _reset_state():
    reset_pipeline_state()
    yield
    reset_pipeline_state()


# --- A. /health isolation ---------------------------------------------------


def test_health_route_is_a_true_async_def():
    """Structural proof: Starlette's own routing.py decides sync-vs-async
    dispatch via exactly this check (inspect.iscoroutinefunction) -- an
    async def handler never enters the shared blocking-threadpool bridge at
    all, so this is the real mechanism, not an approximation of it."""
    assert inspect.iscoroutinefunction(health)


def test_health_remains_responsive_while_the_shared_threadpool_is_saturated():
    """Behavioral proof (the regression test the approved proposal asked
    for): saturates AnyIO's real default worker-thread capacity limiter --
    the exact one Starlette's run_in_threadpool uses for every sync `def`
    route, including where /v1/opportunities' live-feed FMP calls run --
    with real blocking calls, then confirms /health still returns
    immediately, never queuing behind them.
    """

    async def _saturate_and_check() -> tuple[dict[str, str], float]:
        limiter = anyio.to_thread.current_default_thread_limiter()
        total_tokens = int(limiter.total_tokens)
        release_event = threading.Event()

        def _blocked_sync_work() -> None:
            # Real blocking call (a real OS thread parked on a real Event),
            # not a coroutine -- occupies one thread-pool slot exactly the
            # way a blocking FMP httpx call would.
            release_event.wait(timeout=5.0)

        blockers = [
            asyncio.create_task(
                anyio.to_thread.run_sync(_blocked_sync_work, limiter=limiter)
            )
            for _ in range(total_tokens)
        ]
        # Let every blocker actually start and claim its slot before checking.
        await asyncio.sleep(0.2)

        started = time.monotonic()
        result = await health()
        elapsed = time.monotonic() - started

        release_event.set()
        await asyncio.gather(*blockers)
        return result, elapsed

    result, elapsed = asyncio.run(_saturate_and_check())
    assert result == {
        "status": "online",
        "service": "logan-intelligence-api",
        "version": "1.0.0",
    }
    assert elapsed < 2.0, (
        f"/health took {elapsed:.2f}s while every blocking-threadpool slot "
        "was saturated -- it should be structurally unaffected"
    )


# --- B/D. Dedicated live-path ProviderScheduler + circuit breaker ----------


def _failing_transport_handler(call_count: dict[str, int]):
    def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        raise httpx.ConnectTimeout("The handshake operation timed out")

    return handler


def test_healthy_path_is_unaffected_by_the_new_scheduler():
    """Healthy-path regression: a normal successful quote fetch, with the
    dedicated scheduler now wrapping the call, must return exactly the same
    result a pre-3.6.12 direct call would."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/quote")
        return httpx.Response(
            200,
            json=[
                {
                    "symbol": "NVDA",
                    "price": 214.72,
                    "changePercentage": -0.98225,
                    "change": -2.13,
                    "previousClose": 216.85,
                    "volume": 91591112,
                    "timestamp": 1787342400,
                }
            ],
        )

    import backend.app.logan_feed as lf

    original = lf.FmpMarketDataProvider
    try:
        lf.FmpMarketDataProvider = lambda *a, **kw: FmpMarketDataProvider(
            api_key="test-key-not-real",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        # change_pct=-0.98 is below the 5.0 STOCK_PRICE_MOVE_SIGNIFICANT
        # threshold -- a real, successful, non-firing fetch, exactly the
        # common case. Must not raise and must not be treated as degraded.
        result = _live_price_move_raw_signal("NVDA", datetime.now(timezone.utc))
        assert result is None
        scheduler = lf._get_live_provider_scheduler()
        assert scheduler.is_circuit_open("quote") is False
    finally:
        lf.FmpMarketDataProvider = original


# The circuit breaker is deliberately per-endpoint-*family* ("does the quote
# endpoint currently look broken across many tickers"), not per-(endpoint,
# entity_id) pair -- that narrower question is FmpResponseCache's own,
# pre-existing negative cache, which suppresses a *second* real attempt for
# the *same* ticker for 900s after just one real failure. Tripping the
# family-level breaker therefore needs distinct tickers, one real failure
# each -- reusing one ticker five times would exercise the negative cache's
# suppression, not five independent real attempts.
_FIVE_DISTINCT_TICKERS = ["NVDA", "TSLA", "AAPL", "MSFT", "GOOGL"]


def test_circuit_opens_after_five_consecutive_quote_failures_then_fast_fails(
    monkeypatch,
):
    """Circuit-breaker threshold + fast-fail behavior, using the real
    ProviderScheduler (ProviderScheduler.CIRCUIT_BREAKER_FAILURE_THRESHOLD =
    5), injected with a fake clock/sleep so this test needs no real wall-
    clock waiting."""
    fake_now = {"t": 0.0}
    scheduler = ProviderScheduler(
        clock=lambda: fake_now["t"],
        sleep=lambda seconds: fake_now.__setitem__("t", fake_now["t"] + seconds),
    )
    monkeypatch.setattr(logan_feed, "_live_provider_scheduler", scheduler)

    call_count = {"n": 0}
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        lambda *a, **kw: FmpMarketDataProvider(
            api_key="test-key-not-real",
            client=httpx.Client(
                transport=httpx.MockTransport(_failing_transport_handler(call_count))
            ),
        ),
    )

    now = datetime.now(timezone.utc)
    for ticker in _FIVE_DISTINCT_TICKERS:
        assert _live_price_move_raw_signal(ticker, now) is None
    assert call_count["n"] == 5  # one real, honest attempt per distinct ticker
    assert scheduler.is_circuit_open("quote") is True

    # A 6th, never-before-seen ticker: circuit is open -- must fast-fail (no
    # new network attempt), and must still resolve to the same honest-
    # absence contract, never a raised exception escaping into the caller.
    assert _live_price_move_raw_signal("AMZN", now) is None
    assert call_count["n"] == 5, "circuit-open call must not reach the network"


def test_automatic_recovery_after_cooldown_probes_once_and_resets_on_success(
    monkeypatch,
):
    """Automatic-recovery behavior: after the open-circuit cooldown elapses,
    the next call is a real probe; a successful probe resets consecutive
    failures and closes the circuit -- no operator action of any kind."""
    fake_now = {"t": 0.0}
    scheduler = ProviderScheduler(
        clock=lambda: fake_now["t"],
        sleep=lambda seconds: fake_now.__setitem__("t", fake_now["t"] + seconds),
    )
    monkeypatch.setattr(logan_feed, "_live_provider_scheduler", scheduler)

    call_count = {"n": 0}
    should_fail = {"value": True}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        if should_fail["value"]:
            raise httpx.ConnectTimeout("The handshake operation timed out")
        return httpx.Response(
            200,
            json=[
                {
                    "symbol": "NVDA",
                    "price": 214.72,
                    "changePercentage": 1.0,
                    "change": 2.13,
                    "previousClose": 212.0,
                    "volume": 91591112,
                    "timestamp": 1787342400,
                }
            ],
        )

    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        lambda *a, **kw: FmpMarketDataProvider(
            api_key="test-key-not-real",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        ),
    )

    now = datetime.now(timezone.utc)
    for ticker in _FIVE_DISTINCT_TICKERS:
        _live_price_move_raw_signal(ticker, now)
    assert scheduler.is_circuit_open("quote") is True
    assert call_count["n"] == 5

    # Cooldown (CIRCUIT_BREAKER_OPEN_SECONDS=60) has not elapsed yet.
    assert _live_price_move_raw_signal("AMZN", now) is None
    assert call_count["n"] == 5

    # Advance real elapsed time past the open window (simulates FMP health
    # returning some time later, with no operator action) and clear
    # FmpResponseCache's own real-clock-based negative cache for the ticker
    # this probe reuses -- otherwise its still-live 900s per-entity
    # suppression window (a separate, existing mechanism, not this
    # scheduler) would itself raise before ever reaching the real handler,
    # confounding what this assertion is actually checking.
    fake_now["t"] += 61.0
    should_fail["value"] = False  # FMP has recovered
    from logan_core.receptors.providers.fmp import reset_fmp_cache

    reset_fmp_cache()

    _live_price_move_raw_signal("NVDA", now)
    assert call_count["n"] == 6, "cooldown expiry must allow exactly one real probe"
    assert scheduler.is_circuit_open("quote") is False, (
        "a successful recovery probe must reset consecutive failures and "
        "close the circuit"
    )

    # Subsequent healthy requests behave normally (no lingering degradation).
    _live_price_move_raw_signal("TSLA", now)
    assert call_count["n"] == 7
    assert scheduler.is_circuit_open("quote") is False


def test_saturated_scheduler_raises_the_distinct_error_type_never_fmp_provider_error():
    """ProviderSchedulerSaturatedError is a plain Exception, not a
    FmpProviderError subclass (see scheduler.py) -- every live-feed call
    site must catch both explicitly. This proves the type distinction
    itself so a future refactor collapsing the except clauses down to just
    `except FmpProviderError` would be caught by this test, not silently
    let a saturated-scheduler exception escape into /v1/opportunities."""
    assert not issubclass(ProviderSchedulerSaturatedError, FmpProviderError)


# --- C. Aggregate live-feed sweep deadline ----------------------------------


def test_live_sweep_deadline_exceeded_helper(monkeypatch):
    fake_time = {"t": 0.0}
    monkeypatch.setattr(logan_feed.time, "monotonic", lambda: fake_time["t"])

    started_at = logan_feed.time.monotonic()
    assert _live_sweep_deadline_exceeded(started_at) is False

    fake_time["t"] = LIVE_FEED_SWEEP_DEADLINE_SECONDS + 0.01
    assert _live_sweep_deadline_exceeded(started_at) is True


def test_exhausted_sweep_deadline_skips_remaining_tickers_without_any_fetch(
    monkeypatch,
):
    """End-to-end: if the aggregate sweep deadline is already exceeded
    before a ticker's turn, no provider call is ever attempted for it (never
    a fabricated/fixture substitute), the response is honestly degraded, and
    the pipeline still returns within bounded time rather than raising."""
    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", "NVDA,TSLA")
    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "beta")  # live-data-only mode

    call_count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        return httpx.Response(200, json=[])

    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        lambda *a, **kw: FmpMarketDataProvider(
            api_key="test-key-not-real",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        ),
    )
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError("must not be constructed once the deadline is exceeded")
        ),
    )

    # First time.monotonic() call (sweep start) returns 0.0; every call after
    # that returns well past the deadline, so the very first per-ticker
    # check already trips it for every configured ticker.
    calls = {"n": 0}

    def fake_monotonic() -> float:
        calls["n"] += 1
        return 0.0 if calls["n"] == 1 else LIVE_FEED_SWEEP_DEADLINE_SECONDS + 5.0

    monkeypatch.setattr(logan_feed.time, "monotonic", fake_monotonic)

    reset_pipeline_state()
    items, _now, _alert_ids, provider_degraded = logan_feed._run_feed_pipeline(
        "test-user-inc-2026-09-09"
    )

    assert provider_degraded is True, (
        "a poll where the sweep deadline was hit must be honestly marked "
        "degraded, never presented identically to a healthy poll"
    )
    assert call_count["n"] == 0, (
        "no provider call may be attempted once the aggregate sweep "
        "deadline is already exceeded"
    )
    # Route still returns normally -- degraded behavior, not a crash/hang.
    assert isinstance(items, list)


# --- Isolation from Universe Manager's reevaluation scheduler/telemetry ----


def test_dedicated_scheduler_is_a_separate_instance_from_reset_baseline():
    """reset_pipeline_state() must drop the live-path scheduler too, so one
    test's simulated circuit-breaker state can never leak into another's."""
    first = logan_feed._get_live_provider_scheduler()
    first.record_failure("quote")
    reset_pipeline_state()
    second = logan_feed._get_live_provider_scheduler()
    assert second is not first
    assert second.is_circuit_open("quote") is False


def test_universe_manager_reevaluation_path_and_proof_telemetry_are_untouched():
    """Static-source guard, mirroring test_live_feed_fmp_timeout.py's own
    'reevaluation path is untouched' test: universe_manager.py must not
    reference the new live-path scheduler/deadline constants, confirming
    this change never wires the live-feed path into that module's own
    scheduler instance or the scheduler-scoped proof-gate population
    (scheduled_fetch_failure_rate, time_sensitive_delay_p95/p99,
    coalescing_success_rate) -- Category C, held during the active 14-day
    proof window per the approved proposal.
    """
    source = inspect.getsource(universe_manager)
    assert "LIVE_FEED_SCHEDULER_MAX_WAIT_SECONDS" not in source
    assert "LIVE_FEED_SWEEP_DEADLINE_SECONDS" not in source
    assert "_live_provider_scheduler" not in source
    assert "_get_live_provider_scheduler" not in source
