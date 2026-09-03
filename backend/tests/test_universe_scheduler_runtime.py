"""Universe Manager V1a Scheduler Runtime Invocation (V1a ITERATE block,
Phase 1) -- proves `main.py`'s `_lifespan()` actually starts/stops the
background reevaluation poller under the real FastAPI app-lifecycle
pattern, gated correctly by STRATUS_UNIVERSE_SCHEDULER_ENABLED (default
disabled), without ever bypassing `run_scheduled_universe_reevaluation()`'s
own durable cadence gate.

Drives `_lifespan()` directly via `asyncio.run()` (no ASGI server / no
`TestClient` needed -- `_lifespan()` never actually uses its `_app`
argument) rather than through the pytest suite's own event loop: this repo
has no pytest-asyncio dependency, and a plain sync `def test_...()` calling
`asyncio.run()` internally needs none.
"""

import ast
import asyncio
import inspect

import pytest

import backend.app.main as main
from backend.app.universe_manager import ScheduledReevaluationOutcome


@pytest.fixture(autouse=True)
def _reset_scheduler_task_handle():
    """Every test starts from "no scheduler task running yet," mirroring a
    fresh process -- without this, one test enabling the flag would leak a
    non-None `_universe_scheduler_task` into the next test's guard check."""
    main._universe_scheduler_task = None
    yield
    main._universe_scheduler_task = None


def test_scheduler_task_does_not_start_when_disabled(monkeypatch):
    monkeypatch.delenv("STRATUS_UNIVERSE_SCHEDULER_ENABLED", raising=False)

    async def _run():
        async with main._lifespan(None):
            await asyncio.sleep(0)
            return main._universe_scheduler_task

    task_during_lifespan = asyncio.run(_run())
    assert task_during_lifespan is None
    assert main._universe_scheduler_task is None


def test_scheduler_task_starts_when_enabled(monkeypatch):
    monkeypatch.setenv("STRATUS_UNIVERSE_SCHEDULER_ENABLED", "true")

    async def _run():
        async with main._lifespan(None):
            await asyncio.sleep(0)
            task = main._universe_scheduler_task
            assert task is not None
            # Checked *inside* the context, before teardown's own
            # task.cancel() runs -- asyncio.run()'s cleanup would otherwise
            # have already finished cancelling it by the time a caller
            # inspects the task after this coroutine returns.
            assert not task.done()
            return task

    task_during_lifespan = asyncio.run(_run())
    assert task_during_lifespan is not None


def test_importing_main_never_starts_the_scheduler_by_itself():
    """Merely having already imported backend.app.main (every test file in
    this suite does, transitively) must never itself have a scheduler task
    running -- only an actual `_lifespan()` entry with the flag enabled
    does. This module's own import happened long before this test body
    runs, so this is a real assertion, not a tautology."""
    assert main._universe_scheduler_task is None


def test_shutdown_cancels_the_task(monkeypatch):
    monkeypatch.setenv("STRATUS_UNIVERSE_SCHEDULER_ENABLED", "true")

    async def _run():
        async with main._lifespan(None):
            await asyncio.sleep(0)
            task = main._universe_scheduler_task
        await asyncio.sleep(0)  # let the scheduled cancellation land
        return task

    task = asyncio.run(_run())
    assert task is not None
    assert task.cancelled()
    assert main._universe_scheduler_task is None


def test_duplicate_lifespan_entry_does_not_start_a_second_task(monkeypatch):
    """A second `_lifespan()` entry within the same process (before the
    first has shut down) must reuse the existing task, not create a
    second one -- and its own exit must not cancel the outer, still-
    running task out from under it."""
    monkeypatch.setenv("STRATUS_UNIVERSE_SCHEDULER_ENABLED", "true")

    async def _run():
        async with main._lifespan(None):
            first_task = main._universe_scheduler_task
            async with main._lifespan(None):
                second_task = main._universe_scheduler_task
            # The inner context has exited -- the outer task must still be
            # alive and untouched. Checked *inside* the outer context,
            # before its own teardown runs.
            still_running_task = main._universe_scheduler_task
            assert still_running_task is not None
            assert not still_running_task.done()
            return first_task, second_task, still_running_task

    first_task, second_task, still_running_task = asyncio.run(_run())
    assert first_task is second_task
    assert still_running_task is first_task


def test_poll_loop_invokes_the_production_scheduled_wrapper(monkeypatch):
    calls = []

    def _fake_run(*, now=None):
        calls.append(now)
        return ScheduledReevaluationOutcome(
            executed=False, skipped_reason="test stub", rebalance=None
        )

    monkeypatch.setattr(main, "run_production_scheduled_reevaluation", _fake_run)
    monkeypatch.setattr(main, "UNIVERSE_REEVALUATION_POLL_INTERVAL_SECONDS", 0.01)

    async def _run():
        task = asyncio.create_task(main._universe_reevaluation_poll_loop())
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(_run())
    assert len(calls) >= 1


def _referenced_names(func) -> set:
    """AST-level identifier-reference extraction, not a naive substring
    search on source text -- a substring check would also match this
    function's own explanatory docstring prose (which necessarily
    *mentions* run_universe_reevaluation() by name to describe what it
    must NOT do), producing a false failure on the exact guarantee this
    test verifies. Collects every `Load`-context Name (not just direct
    Call targets) since `_universe_reevaluation_poll_loop` references
    `run_production_scheduled_reevaluation` as a bare callable passed to
    `asyncio.to_thread(...)`, not as a direct call expression."""
    tree = ast.parse(inspect.getsource(func))
    return {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }


def test_poll_loop_never_bypasses_the_scheduled_wrapper():
    """A source-level guarantee, not just a mock check: the loop only ever
    calls run_production_scheduled_reevaluation() -- it never calls the
    un-gated run_universe_reevaluation() directly, which would bypass the
    durable cadence gate entirely."""
    referenced = _referenced_names(main._universe_reevaluation_poll_loop)
    assert "run_production_scheduled_reevaluation" in referenced
    assert "run_universe_reevaluation" not in referenced


def test_production_wrapper_never_bypasses_the_scheduled_gate():
    """The same guarantee one layer down: run_production_scheduled_
    reevaluation() itself must call run_scheduled_universe_reevaluation()
    (the cadence-gated entry point), never run_universe_reevaluation()
    (the un-gated one) directly."""
    from backend.app import universe_manager

    referenced = _referenced_names(
        universe_manager.run_production_scheduled_reevaluation
    )
    assert "run_scheduled_universe_reevaluation" in referenced
    assert "run_universe_reevaluation" not in referenced


def test_poll_loop_survives_a_failing_cycle(monkeypatch):
    """One bad cycle must not kill all future cycles -- mirrors
    `_notification_poll_loop()`'s own identical guarantee."""
    calls = {"count": 0}

    def _fake_run(*, now=None):
        calls["count"] += 1
        raise RuntimeError("simulated scheduler failure")

    monkeypatch.setattr(main, "run_production_scheduled_reevaluation", _fake_run)
    monkeypatch.setattr(main, "UNIVERSE_REEVALUATION_POLL_INTERVAL_SECONDS", 0.01)

    async def _run():
        task = asyncio.create_task(main._universe_reevaluation_poll_loop())
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(_run())
    assert calls["count"] >= 2  # more than one cycle ran despite the failure
