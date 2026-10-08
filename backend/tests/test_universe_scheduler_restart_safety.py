"""Universe Scheduler restart-safety block (ADR-072) -- proves the
scheduler's due time comes from durable state rather than from process
start: an overdue reevaluation runs exactly once at startup, a not-yet-due
one waits only the remaining time, a restart neither resets nor duplicates
it, a failed run is retried on a bounded delay, and none of this changes
what a reevaluation actually selects.

Same conventions as test_universe_scheduler_runtime.py: no pytest-asyncio,
plain sync tests driving coroutines through `asyncio.run()`.
"""

import asyncio
import threading
import time
from datetime import timedelta

import pytest

import backend.app.main as main
import backend.app.universe_manager as universe_manager
from backend.app.universe_manager import (
    FAILED_RUN_RETRY_SECONDS,
    REEVALUATION_MIN_INTERVAL_SECONDS,
    STALE_RUNNING_TIMEOUT_SECONDS,
    UNIVERSE_REEVALUATION_JOB,
    ScheduledReevaluationOutcome,
    get_scheduler_state,
    reset_universe_manager_state,
    run_scheduled_universe_reevaluation,
    run_universe_reevaluation,
    seconds_until_reevaluation_due,
)
from backend.app.universe_scheduler_store import UniverseSchedulerStateStore
from backend.tests.test_universe_manager import (
    NOW,
    _enable_persistence_with_isolated_dbs,
    _healthy_fixture_providers,
)
from logan_core.contracts import CohortRebalanceResult


def _require_state():
    """The scheduler state, asserted present -- for tests that read a field
    straight off it."""
    state = get_scheduler_state(UNIVERSE_REEVALUATION_JOB)
    assert state is not None
    return state


INTERVAL = timedelta(seconds=REEVALUATION_MIN_INTERVAL_SECONDS)


@pytest.fixture(autouse=True)
def _fresh_process_state():
    main._universe_scheduler_task = None
    yield
    main._universe_scheduler_task = None
    reset_universe_manager_state()


def _stub_reevaluation(monkeypatch, *, fail=False, delay_seconds=0.0):
    """Replaces the real (provider-calling) reevaluation with a counter, so
    these tests exercise only *whether/when* a run happens. Returns the
    mutable call record."""
    record = {"count": 0, "fail": fail}
    lock = threading.Lock()

    def _fake(**kwargs):
        with lock:
            record["count"] += 1
        if delay_seconds:
            time.sleep(delay_seconds)
        if record["fail"]:
            raise RuntimeError("simulated reevaluation failure")
        return CohortRebalanceResult(
            policy_version="test", rebalanced_at=kwargs.get("now") or NOW
        )

    monkeypatch.setattr(universe_manager, "run_universe_reevaluation", _fake)
    return record


def _simulate_restart():
    """Drops every in-memory handle; only the durable files survive."""
    reset_universe_manager_state()
    main._universe_scheduler_task = None


# --- durable due-time semantics ------------------------------------------------


def test_never_run_is_due_immediately(monkeypatch, tmp_path):
    _enable_persistence_with_isolated_dbs(monkeypatch, tmp_path)
    assert seconds_until_reevaluation_due(now=NOW) == 0.0


def test_startup_when_not_due_reports_the_remaining_time_and_skips(
    monkeypatch, tmp_path
):
    _enable_persistence_with_isolated_dbs(monkeypatch, tmp_path)
    record = _stub_reevaluation(monkeypatch)
    assert run_scheduled_universe_reevaluation(now=NOW).executed is True

    _simulate_restart()
    ten_days_later = NOW + timedelta(days=10)
    remaining = seconds_until_reevaluation_due(now=ten_days_later)
    assert remaining == pytest.approx(20 * 24 * 3600.0)

    outcome = run_scheduled_universe_reevaluation(now=ten_days_later)
    assert outcome.executed is False
    assert record["count"] == 1


def test_startup_when_overdue_runs_exactly_once(monkeypatch, tmp_path):
    _enable_persistence_with_isolated_dbs(monkeypatch, tmp_path)
    record = _stub_reevaluation(monkeypatch)
    run_scheduled_universe_reevaluation(now=NOW)

    _simulate_restart()
    overdue = NOW + timedelta(days=31)
    assert seconds_until_reevaluation_due(now=overdue) == 0.0
    assert run_scheduled_universe_reevaluation(now=overdue).executed is True
    assert run_scheduled_universe_reevaluation(now=overdue).executed is False
    assert record["count"] == 2  # the original run + exactly one overdue run


def test_exact_due_boundary_counts_as_due(monkeypatch, tmp_path):
    _enable_persistence_with_isolated_dbs(monkeypatch, tmp_path)
    record = _stub_reevaluation(monkeypatch)
    run_scheduled_universe_reevaluation(now=NOW)

    one_second_early = NOW + INTERVAL - timedelta(seconds=1)
    assert seconds_until_reevaluation_due(now=one_second_early) == pytest.approx(1.0)
    assert run_scheduled_universe_reevaluation(now=one_second_early).executed is False

    exactly_due = NOW + INTERVAL
    assert seconds_until_reevaluation_due(now=exactly_due) == 0.0
    assert run_scheduled_universe_reevaluation(now=exactly_due).executed is True
    assert record["count"] == 2


def test_restart_before_due_never_resets_or_advances_the_clock(monkeypatch, tmp_path):
    _enable_persistence_with_isolated_dbs(monkeypatch, tmp_path)
    record = _stub_reevaluation(monkeypatch)
    run_scheduled_universe_reevaluation(now=NOW)

    # Many restarts across the window: the remaining time tracks wall-clock
    # time since the durable last start, never time since "this" start.
    for days in (1, 5, 12, 29):
        _simulate_restart()
        at = NOW + timedelta(days=days)
        assert seconds_until_reevaluation_due(now=at) == pytest.approx(
            (30 - days) * 24 * 3600.0
        )
        assert run_scheduled_universe_reevaluation(now=at).executed is False
    assert record["count"] == 1


def test_restart_after_due_runs_once_and_later_restarts_do_not_repeat_it(
    monkeypatch, tmp_path
):
    _enable_persistence_with_isolated_dbs(monkeypatch, tmp_path)
    record = _stub_reevaluation(monkeypatch)
    run_scheduled_universe_reevaluation(now=NOW)

    overdue = NOW + timedelta(days=30, minutes=5)
    _simulate_restart()
    assert run_scheduled_universe_reevaluation(now=overdue).executed is True
    for minutes in (1, 30, 600):
        _simulate_restart()
        again = run_scheduled_universe_reevaluation(
            now=overdue + timedelta(minutes=minutes)
        )
        assert again.executed is False
    assert record["count"] == 2


def test_persisted_last_success_survives_restart_and_a_later_failure(
    monkeypatch, tmp_path
):
    _enable_persistence_with_isolated_dbs(monkeypatch, tmp_path)
    record = _stub_reevaluation(monkeypatch)
    run_scheduled_universe_reevaluation(now=NOW)
    first_success = _require_state().last_succeeded_at
    assert first_success is not None

    _simulate_restart()
    assert _require_state().last_succeeded_at == first_success

    record["fail"] = True
    with pytest.raises(RuntimeError):
        run_scheduled_universe_reevaluation(now=NOW + INTERVAL)
    _simulate_restart()
    state = get_scheduler_state(UNIVERSE_REEVALUATION_JOB)
    assert state is not None
    assert state.last_outcome == "failure"
    assert state.last_succeeded_at == first_success  # never fabricated/moved


def test_failed_reevaluation_is_retried_after_the_bounded_delay_then_recovers(
    monkeypatch, tmp_path
):
    _enable_persistence_with_isolated_dbs(monkeypatch, tmp_path)
    record = _stub_reevaluation(monkeypatch, fail=True)
    with pytest.raises(RuntimeError):
        run_scheduled_universe_reevaluation(now=NOW)

    # Not retried immediately, and not on every restart either.
    _simulate_restart()
    an_hour_later = NOW + timedelta(hours=1)
    assert seconds_until_reevaluation_due(now=an_hour_later) == pytest.approx(
        FAILED_RUN_RETRY_SECONDS - 3600.0
    )
    assert run_scheduled_universe_reevaluation(now=an_hour_later).executed is False
    assert record["count"] == 1

    # Due again one retry interval after the failed attempt started -- not
    # a full 30-day cadence window later.
    record["fail"] = False
    retry_at = NOW + timedelta(seconds=FAILED_RUN_RETRY_SECONDS)
    assert seconds_until_reevaluation_due(now=retry_at) == 0.0
    assert run_scheduled_universe_reevaluation(now=retry_at).executed is True
    state = get_scheduler_state(UNIVERSE_REEVALUATION_JOB)
    assert state is not None
    assert state.last_outcome == "success"
    assert state.last_succeeded_at is not None

    # After the recovery succeeds, the ordinary cadence applies again.
    assert seconds_until_reevaluation_due(
        now=retry_at + timedelta(days=1)
    ) == pytest.approx(29 * 24 * 3600.0)


def test_repeated_failures_never_retry_faster_than_the_bounded_delay(
    monkeypatch, tmp_path
):
    _enable_persistence_with_isolated_dbs(monkeypatch, tmp_path)
    record = _stub_reevaluation(monkeypatch, fail=True)
    # A restart loop hammering the gate every 10 minutes for three days.
    at = NOW
    while at <= NOW + timedelta(days=3):
        _simulate_restart()
        try:
            run_scheduled_universe_reevaluation(now=at)
        except RuntimeError:
            pass
        at += timedelta(minutes=10)
    assert record["count"] == 4  # day 0, 1, 2, 3 -- one attempt per day


def test_restart_during_reevaluation_waits_for_the_stale_running_bound(
    monkeypatch, tmp_path
):
    _enable_persistence_with_isolated_dbs(monkeypatch, tmp_path)
    record = _stub_reevaluation(monkeypatch)
    store = UniverseSchedulerStateStore(str(tmp_path / "universe_scheduler.db"))
    store.mark_started(UNIVERSE_REEVALUATION_JOB, NOW)  # killed mid-run
    store.close()
    _simulate_restart()

    just_after = NOW + timedelta(seconds=30)
    assert seconds_until_reevaluation_due(now=just_after) == pytest.approx(
        STALE_RUNNING_TIMEOUT_SECONDS - 30.0
    )
    assert run_scheduled_universe_reevaluation(now=just_after).executed is False

    recovered_at = NOW + timedelta(seconds=STALE_RUNNING_TIMEOUT_SECONDS)
    assert run_scheduled_universe_reevaluation(now=recovered_at).executed is True
    assert record["count"] == 1


def test_no_durable_due_time_when_persistence_is_disabled(monkeypatch):
    monkeypatch.delenv("STRATUS_PERSIST_MEMORY", raising=False)
    reset_universe_manager_state()
    assert seconds_until_reevaluation_due(now=NOW) is None


# --- duplicate-start protection ------------------------------------------------


def test_concurrent_callers_seeing_the_same_due_state_run_only_once(
    monkeypatch, tmp_path
):
    _enable_persistence_with_isolated_dbs(monkeypatch, tmp_path)
    record = _stub_reevaluation(monkeypatch, delay_seconds=0.05)
    outcomes = []
    barrier = threading.Barrier(8)

    def _caller():
        barrier.wait()
        outcomes.append(run_scheduled_universe_reevaluation(now=NOW))

    threads = [threading.Thread(target=_caller) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert record["count"] == 1
    assert sum(1 for outcome in outcomes if outcome.executed) == 1
    assert sum(1 for outcome in outcomes if not outcome.executed) == 7


def test_claim_is_atomic_across_two_connections_to_the_same_file(tmp_path):
    """Two store instances on one file stand in for two processes/startup
    paths: only the first claim of a given due state can succeed."""
    path = tmp_path / "scheduler.db"
    first, second = UniverseSchedulerStateStore(path), UniverseSchedulerStateStore(path)

    def _due_if_never_started(state):
        return state is None or state.last_started_at is None

    claimed_first, seen_first = first.claim_start(
        "job", NOW, is_due=_due_if_never_started
    )
    claimed_second, seen_second = second.claim_start(
        "job", NOW, is_due=_due_if_never_started
    )
    assert (claimed_first, seen_first) == (True, None)
    assert claimed_second is False
    assert seen_second is not None and seen_second.last_outcome == "running"
    first.close()
    second.close()


def test_declined_claim_writes_nothing(tmp_path):
    store = UniverseSchedulerStateStore(tmp_path / "scheduler.db")
    store.mark_started("job", NOW)
    store.mark_completed("job", NOW, outcome="success")
    before = store.get("job")
    claimed, seen = store.claim_start(
        "job", NOW + timedelta(days=1), is_due=lambda state: False
    )
    assert claimed is False
    assert seen == before
    assert store.get("job") == before
    store.close()


# --- the runtime loop (main.py) ------------------------------------------------


def _run_loop_for(seconds):
    async def _run():
        task = asyncio.create_task(main._universe_reevaluation_poll_loop())
        await asyncio.sleep(seconds)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(_run())


def _skipped(**_kwargs):
    return ScheduledReevaluationOutcome(
        executed=False, skipped_reason="test stub", rebalance=None
    )


def test_wait_is_the_remaining_due_time_capped_at_the_daily_check(monkeypatch):
    daily = main.UNIVERSE_REEVALUATION_POLL_INTERVAL_SECONDS
    monkeypatch.setattr(main, "seconds_until_reevaluation_due", lambda: 0.0)
    assert main._universe_reevaluation_wait_seconds() == 0.0
    monkeypatch.setattr(main, "seconds_until_reevaluation_due", lambda: 5400.0)
    assert main._universe_reevaluation_wait_seconds() == 5400.0
    monkeypatch.setattr(main, "seconds_until_reevaluation_due", lambda: 20 * daily)
    assert main._universe_reevaluation_wait_seconds() == daily


def test_wait_falls_back_to_the_daily_check_without_durable_state(monkeypatch):
    daily = main.UNIVERSE_REEVALUATION_POLL_INTERVAL_SECONDS
    monkeypatch.setattr(main, "seconds_until_reevaluation_due", lambda: None)
    assert main._universe_reevaluation_wait_seconds() == daily

    def _boom():
        raise RuntimeError("state store unavailable")

    monkeypatch.setattr(main, "seconds_until_reevaluation_due", _boom)
    assert main._universe_reevaluation_wait_seconds() == daily


def test_loop_checks_immediately_at_startup_when_overdue(monkeypatch):
    calls = []
    remaining = {"value": 0.0}

    def _fake_run(*, now=None):
        calls.append(time.monotonic())
        remaining["value"] = 3600.0  # the run just happened; next is far off
        return ScheduledReevaluationOutcome(
            executed=True, skipped_reason=None, rebalance=None
        )

    monkeypatch.setattr(main, "run_production_scheduled_reevaluation", _fake_run)
    monkeypatch.setattr(
        main, "seconds_until_reevaluation_due", lambda: remaining["value"]
    )
    started = time.monotonic()
    _run_loop_for(0.2)
    assert len(calls) == 1  # exactly once -- no 24h pre-sleep, no repeat
    assert calls[0] - started < 0.15


def test_loop_does_not_check_before_the_remaining_time_has_passed(monkeypatch):
    calls = []
    monkeypatch.setattr(
        main,
        "run_production_scheduled_reevaluation",
        lambda *, now=None: calls.append(1) or _skipped(),  # type: ignore[func-returns-value]
    )
    monkeypatch.setattr(main, "seconds_until_reevaluation_due", lambda: 3600.0)
    _run_loop_for(0.1)
    assert calls == []


def test_loop_sleeps_only_the_remaining_time_then_checks(monkeypatch):
    calls = []
    remaining = {"value": 0.15}

    def _fake_run(*, now=None):
        calls.append(time.monotonic())
        remaining["value"] = 3600.0
        return _skipped()

    monkeypatch.setattr(main, "run_production_scheduled_reevaluation", _fake_run)
    monkeypatch.setattr(
        main, "seconds_until_reevaluation_due", lambda: remaining["value"]
    )
    started = time.monotonic()
    _run_loop_for(0.5)
    assert len(calls) == 1
    assert calls[0] - started >= 0.14


def test_loop_never_spins_when_state_stays_due_without_a_claim(monkeypatch):
    calls = []
    monkeypatch.setattr(
        main,
        "run_production_scheduled_reevaluation",
        lambda *, now=None: calls.append(1) or _skipped(),  # type: ignore[func-returns-value]
    )
    monkeypatch.setattr(main, "seconds_until_reevaluation_due", lambda: 0.0)
    monkeypatch.setattr(main, "UNIVERSE_REEVALUATION_MIN_RECHECK_SECONDS", 0.05)
    _run_loop_for(0.22)
    assert 2 <= len(calls) <= 6  # floored re-checks, not a hot loop


def test_real_loop_runs_an_overdue_reevaluation_once_across_restarts(
    monkeypatch, tmp_path
):
    """End to end through the real loop, the real production wrapper, the
    real gate and the real durable store -- only the provider-calling
    reevaluation itself is stubbed."""
    _enable_persistence_with_isolated_dbs(monkeypatch, tmp_path)
    record = _stub_reevaluation(monkeypatch)

    # Durable state as production has it: last success long ago.
    store = UniverseSchedulerStateStore(str(tmp_path / "universe_scheduler.db"))
    long_ago = NOW - timedelta(days=31)
    store.mark_started(UNIVERSE_REEVALUATION_JOB, long_ago)
    store.mark_completed(UNIVERSE_REEVALUATION_JOB, long_ago, outcome="success")
    store.close()

    for _ in range(3):  # three process starts in a row
        _simulate_restart()
        _run_loop_for(0.2)

    assert record["count"] == 1
    state = get_scheduler_state(UNIVERSE_REEVALUATION_JOB)
    assert state is not None
    assert state.last_outcome == "success"
    assert state.last_succeeded_at is not None
    assert state.last_succeeded_at > long_ago


def test_real_loop_does_nothing_at_startup_when_not_yet_due(monkeypatch, tmp_path):
    _enable_persistence_with_isolated_dbs(monkeypatch, tmp_path)
    record = _stub_reevaluation(monkeypatch)
    store = UniverseSchedulerStateStore(str(tmp_path / "universe_scheduler.db"))
    recent = NOW - timedelta(days=3)
    store.mark_started(UNIVERSE_REEVALUATION_JOB, recent)
    store.mark_completed(UNIVERSE_REEVALUATION_JOB, recent, outcome="success")
    store.close()

    for _ in range(3):
        _simulate_restart()
        _run_loop_for(0.1)

    assert record["count"] == 0
    assert _require_state().last_started_at == recent


# --- Universe membership / selection semantics are untouched ------------------


def test_gated_run_selects_exactly_what_an_ungated_run_selects(monkeypatch, tmp_path):
    """The scheduler decides only *whether* a reevaluation happens. The
    cohort a gated run admits is identical to what the un-gated
    reevaluation admits from the same inputs."""
    market, earnings = _healthy_fixture_providers()

    _enable_persistence_with_isolated_dbs(monkeypatch, tmp_path / "direct")
    direct = run_universe_reevaluation(
        market_data_provider=market, earnings_provider=earnings, now=NOW
    )

    _enable_persistence_with_isolated_dbs(monkeypatch, tmp_path / "gated")
    gated = run_scheduled_universe_reevaluation(
        market_data_provider=market, earnings_provider=earnings, now=NOW
    )

    assert gated.executed is True
    assert gated.rebalance is not None
    assert gated.rebalance.policy_version == direct.policy_version
    assert sorted(r.symbol for r in gated.rebalance.admitted) == sorted(
        r.symbol for r in direct.admitted
    )
    assert len(gated.rebalance.removed) == len(direct.removed) == 0
    assert 25 <= len(gated.rebalance.admitted) <= 35


def test_cadence_constants_are_unchanged():
    assert REEVALUATION_MIN_INTERVAL_SECONDS == 30.0 * 24.0 * 3600.0
    assert STALE_RUNNING_TIMEOUT_SECONDS == 3600.0
    assert main.UNIVERSE_REEVALUATION_POLL_INTERVAL_SECONDS == 24.0 * 3600.0
