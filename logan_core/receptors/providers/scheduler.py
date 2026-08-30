"""Universe Manager V1a Block 7 -- Provider Scheduler V1.

Builds on the existing FmpResponseCache (logan_core/receptors/providers/
fmp.py) rather than replacing it: shared TTL cache, negative caching,
in-flight request coalescing, and optional TTL jitter (Operational Beta
Hardening Block 6) are already there and untouched. This module adds
exactly what Block 7 asks for on top: a shared call-admission budget so a
larger monitored universe (up to the 25-35 V1a target, with a clean path
to 40-50) can never burst past STRATUS's own operating ceiling, regardless
of how many concurrent callers (the background poller, a direct request,
a manual reevaluation run) want the same provider at once.

Deliberately NOT wired into the real FmpEarningsProvider/FmpMarketDataProvider
methods -- those keep calling FmpResponseCache directly, byte-identical to
today's production behavior. `ProviderScheduler` is standalone, fully
tested infrastructure; a caller opts in by wrapping its own `fetch`
callable with `scheduler.gate(endpoint, priority, fetch)` before handing
that wrapped callable to `FmpResponseCache.get_or_fetch()` -- gating only
ever wraps the real upstream call itself (get_or_fetch only invokes
`fetch()` on a genuine cache miss), so a cache hit never touches the
budget. backend/app/universe_manager.py's `run_universe_reevaluation()` is
the first real caller (Commit 2).

Rate ceilings (STRATUS's own operating budget, well inside FMP's actual
300-calls/minute Starter-plan limit -- see this session's own Live Supply
V2 reconciliation): GLOBAL_CALLS_PER_MINUTE_CEILING=220,
default per-endpoint-family ceiling = 60% of that (132/min) so one
endpoint family alone can never consume the whole budget.

Priority is observability/default-wait-budget only in V1 -- see
`acquire()`'s own docstring for the honest scope note on why this isn't a
strict preemptive priority queue (Block 7: "keep this simple, do not
create a multi-service orchestration platform").
"""

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Optional, TypeVar

T = TypeVar("T")

GLOBAL_CALLS_PER_MINUTE_CEILING = 220
DEFAULT_PER_ENDPOINT_CEILING_FRACTION = 0.60
RATE_WINDOW_SECONDS = 60.0

# Bounded queue wait: a caller polls for capacity for at most this long
# before giving up -- "bounded queue," not an unbounded wait (Block 7).
DEFAULT_MAX_WAIT_SECONDS = 30.0
_POLL_INTERVAL_SECONDS = 0.05

PRIORITY_TIERS = ("critical", "event_window", "normal", "deferred")
_PRIORITY_RANK = {tier: rank for rank, tier in enumerate(PRIORITY_TIERS)}

# Circuit breaker: an endpoint *family* (e.g. "quote" across every ticker),
# not a single (endpoint, entity_id) pair -- complements, never replaces,
# FmpResponseCache's own existing per-(endpoint, entity_id) negative cache.
# That negative cache answers "has this specific ticker's quote recently
# failed"; this circuit breaker answers "does the quote endpoint itself
# currently look broken across many tickers," and briefly stops admitting
# *new* calls to that whole endpoint family when it trips.
CIRCUIT_BREAKER_FAILURE_THRESHOLD = 5
CIRCUIT_BREAKER_OPEN_SECONDS = 60.0


@dataclass
class _EndpointBudgetState:
    calls: deque = field(default_factory=deque)
    consecutive_failures: int = 0
    circuit_open_until: Optional[float] = None


@dataclass(frozen=True)
class WaitSample:
    endpoint: str
    priority: str
    waited_seconds: float
    admitted: bool


class ProviderSchedulerSaturatedError(Exception):
    """Raised by `gate()` (never by the lower-level `acquire()`, which
    returns a plain bool) when a call could not be admitted within its
    wait budget -- the caller's own fetch is never attempted."""


class ProviderScheduler:
    """Shared call-admission control across every endpoint this process
    talks to FMP through. `clock`/`sleep` are injectable (real callers use
    time.monotonic/time.sleep; tests inject fakes) so this is
    deterministically testable without real wall-clock waiting -- same
    discipline as FmpResponseCache's own injectable clock.
    """

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        global_ceiling: int = GLOBAL_CALLS_PER_MINUTE_CEILING,
        per_endpoint_ceiling_fraction: float = DEFAULT_PER_ENDPOINT_CEILING_FRACTION,
    ) -> None:
        self._clock = clock
        self._sleep = sleep
        self._global_ceiling = global_ceiling
        self._per_endpoint_ceiling = max(
            1, int(global_ceiling * per_endpoint_ceiling_fraction)
        )
        self._lock = threading.Lock()
        self._global_calls: deque = deque()
        self._endpoints: dict[str, _EndpointBudgetState] = {}
        self._wait_samples: list[WaitSample] = []

    def _endpoint_state(self, endpoint: str) -> _EndpointBudgetState:
        state = self._endpoints.get(endpoint)
        if state is None:
            state = _EndpointBudgetState()
            self._endpoints[endpoint] = state
        return state

    def _prune(self, calls: deque, now: float) -> None:
        while calls and now - calls[0] > RATE_WINDOW_SECONDS:
            calls.popleft()

    def _is_circuit_open(self, state: _EndpointBudgetState, now: float) -> bool:
        return state.circuit_open_until is not None and now < state.circuit_open_until

    def _capacity_available(self, endpoint: str, now: float) -> bool:
        self._prune(self._global_calls, now)
        state = self._endpoint_state(endpoint)
        self._prune(state.calls, now)
        if self._is_circuit_open(state, now):
            return False
        return (
            len(self._global_calls) < self._global_ceiling
            and len(state.calls) < self._per_endpoint_ceiling
        )

    def acquire(
        self,
        endpoint: str,
        *,
        priority: str = "normal",
        max_wait_seconds: float = DEFAULT_MAX_WAIT_SECONDS,
    ) -> bool:
        """Reserves one call slot for `endpoint`, blocking (via the
        injectable `sleep`) until capacity frees up or `max_wait_seconds`
        elapses. Returns True once reserved (the caller must make its real
        call promptly), False on timeout (a bounded queue, not an
        unbounded wait) -- a caller that gets False must not fetch.

        V1 priority scope note: `priority` is recorded for observability
        (see `wait_samples`/`queue_report`) and is available for a future
        priority-preemptive scheduler, but this V1 implementation does not
        reorder waiting callers by priority under concurrent contention --
        every waiter polls independently for capacity in the order it
        happens to check, not in strict priority order. Block 7's own
        instruction ("keep this simple, do not create a multi-service
        orchestration platform") is why: V1a's realistic call pattern (a
        handful of concurrent callers, never a deeply saturated queue) does
        not yet need strict preemption, and a real one would require
        meaningfully more machinery (a condition-variable-backed priority
        heap) than this scope calls for.
        """
        priority = priority if priority in _PRIORITY_RANK else "normal"
        started = self._clock()
        deadline = started + max_wait_seconds
        while True:
            with self._lock:
                now = self._clock()
                if self._capacity_available(endpoint, now):
                    self._global_calls.append(now)
                    self._endpoint_state(endpoint).calls.append(now)
                    self._wait_samples.append(
                        WaitSample(endpoint, priority, now - started, True)
                    )
                    return True
            now = self._clock()
            if now >= deadline:
                self._wait_samples.append(
                    WaitSample(endpoint, priority, now - started, False)
                )
                return False
            self._sleep(min(_POLL_INTERVAL_SECONDS, deadline - now))

    def gate(
        self,
        endpoint: str,
        fetch: Callable[[], T],
        *,
        priority: str = "normal",
        max_wait_seconds: float = DEFAULT_MAX_WAIT_SECONDS,
    ) -> T:
        """Wraps a real fetch callable: acquires a slot, calls `fetch()`,
        and reports success/failure to the circuit breaker. Intended usage
        is to pass the *result* of `scheduler.gate_callable(...)` (see
        below) as the `fetch` argument to `FmpResponseCache.get_or_fetch()`
        -- that way the budget is only ever spent on a genuine cache miss,
        never a cache hit.
        """
        if not self.acquire(
            endpoint, priority=priority, max_wait_seconds=max_wait_seconds
        ):
            raise ProviderSchedulerSaturatedError(
                f"[scheduler] {endpoint}: no capacity available within "
                f"{max_wait_seconds:.0f}s (global ceiling={self._global_ceiling}/min, "
                f"per-endpoint ceiling={self._per_endpoint_ceiling}/min)"
            )
        try:
            result = fetch()
        except Exception:
            self.record_failure(endpoint)
            raise
        else:
            self.record_success(endpoint)
            return result

    def record_success(self, endpoint: str) -> None:
        with self._lock:
            self._endpoint_state(endpoint).consecutive_failures = 0

    def record_failure(self, endpoint: str) -> None:
        with self._lock:
            state = self._endpoint_state(endpoint)
            state.consecutive_failures += 1
            if state.consecutive_failures >= CIRCUIT_BREAKER_FAILURE_THRESHOLD:
                state.circuit_open_until = self._clock() + CIRCUIT_BREAKER_OPEN_SECONDS

    def is_circuit_open(self, endpoint: str) -> bool:
        with self._lock:
            return self._is_circuit_open(self._endpoint_state(endpoint), self._clock())

    def current_calls_per_minute(self, endpoint: Optional[str] = None) -> int:
        """Real calls admitted within the trailing 60s window -- global, or
        for one endpoint family."""
        with self._lock:
            now = self._clock()
            if endpoint is None:
                self._prune(self._global_calls, now)
                return len(self._global_calls)
            state = self._endpoint_state(endpoint)
            self._prune(state.calls, now)
            return len(state.calls)

    def wait_samples(self) -> list[WaitSample]:
        with self._lock:
            return list(self._wait_samples)

    def reset(self) -> None:
        with self._lock:
            self._global_calls.clear()
            self._endpoints.clear()
            self._wait_samples.clear()


def warm_start_delays(
    entity_ids: list[str], *, total_stagger_seconds: float
) -> dict[str, float]:
    """Block 7's "controlled warming": a startup fanning out to every
    monitored ticker at once is exactly the burst this whole module exists
    to prevent. Returns a deterministic per-entity delay (evenly spread
    across `total_stagger_seconds`) a caller should wait before that
    entity's *first* fetch during a cold start -- pure, no I/O, no actual
    sleeping here; the caller applies the delay itself (e.g. via the
    scheduler's own injectable `sleep`, or its real event loop).
    """
    count = len(entity_ids)
    if count == 0:
        return {}
    step = total_stagger_seconds / count
    return {entity_id: index * step for index, entity_id in enumerate(entity_ids)}
