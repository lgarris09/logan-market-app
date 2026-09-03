"""V1a Proof-Instrumentation Closeout -- recording and query API for the
durable operational observation layer (see
universe_operational_observation_store.py for the schema, retention, and
scope guardrails this module operates under).

Every `record_*` function here is called from a real call site (universe_
manager.py's reevaluation run, logan_feed.py's freshness classification)
and is wrapped in try/except at that call site's own level of
responsibility -- consistent with universe_telemetry.py's own "telemetry
observes, it never breaks the real work it's observing" discipline.
"""

import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .config import (
    memory_persistence_enabled,
    operational_observation_retention_days,
    universe_operational_observation_db_path,
)
from .universe_operational_observation_store import (
    CoalescingObservation,
    FaultMirrorObservation,
    FreshnessRatioObservation,
    ProviderCallObservation,
    ProviderCallTimestamp,
    ProviderWaitObservation,
    SignalFamilyAttemptObservation,
    UniverseOperationalObservationStore,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from logan_core.diagnostics import FaultOccurrence, set_fault_sink  # noqa: E402
from logan_core.receptors.providers import (  # noqa: E402
    FmpBudgetSnapshot,
    set_call_observer,
)
from logan_core.receptors.providers.scheduler import ProviderScheduler  # noqa: E402

_store: Optional[UniverseOperationalObservationStore] = None
_last_persisted_wait_sample_index: dict[int, int] = {}


def _fault_sink_callback(occurrence: FaultOccurrence) -> None:
    """Registered once via set_fault_sink() -- durably mirrors every real
    fault occurrence. A no-op when persistence is disabled, exactly like
    every other store in this codebase."""
    store = _get_store()
    if store is None:
        return
    store.record_fault_mirror(
        FaultMirrorObservation(
            occurred_at=occurrence.occurred_at,
            code=occurrence.code,
            correlation_id=occurrence.correlation_id,
        )
    )


def _call_observer_callback(endpoint: str) -> None:
    """Registered once via set_call_observer() -- durably records exactly
    one row per real outbound provider call. A no-op when persistence is
    disabled. `datetime.now(timezone.utc)` is read here, synchronously, at
    the moment the real call boundary in fmp.py fires this callback --
    genuine wall-clock time, never the injectable monotonic clock fmp.py's
    own cache/TTL logic uses for deterministic test timing."""
    store = _get_store()
    if store is None:
        return
    store.record_provider_call_timestamp(
        ProviderCallTimestamp(
            occurred_at=datetime.now(timezone.utc), provider="fmp", endpoint=endpoint
        )
    )


def _get_store() -> Optional[UniverseOperationalObservationStore]:
    global _store
    if not memory_persistence_enabled():
        return None
    if _store is None:
        _store = UniverseOperationalObservationStore(
            universe_operational_observation_db_path()
        )
    return _store


# Registered at import time (not lazily inside _get_store()) so a fault or
# real call occurring before this module's first real recording call is
# never missed -- both callbacks check memory_persistence_enabled() /
# _get_store() internally and are total no-ops when disabled, so eager
# registration has no real side effect on its own (consistent with "an
# import must never start anything by itself").
set_fault_sink(_fault_sink_callback)
set_call_observer(_call_observer_callback)


def reset_operational_observation_state() -> None:
    """Test-only (and general-purpose "start over") hook, mirroring every
    other store's identical reset_*_state() shape. Re-arms (never clears)
    the fault sink and call observer -- they must stay registered across a
    reset exactly like they do across a real process restart (this module
    gets re-imported, which re-registers them); a test calling this must
    still durably capture the very next fault/call, not need a second,
    unrelated call first."""
    global _store
    if _store is not None:
        _store.close()
    _store = None
    _last_persisted_wait_sample_index.clear()
    set_fault_sink(_fault_sink_callback)
    set_call_observer(_call_observer_callback)


def _maybe_purge(now: datetime) -> None:
    store = _get_store()
    if store is None:
        return
    cutoff = now.date() - timedelta(days=operational_observation_retention_days())
    store.purge_older_than(cutoff)


def record_reevaluation_provider_observations(
    *,
    before: FmpBudgetSnapshot,
    after: FmpBudgetSnapshot,
    now: datetime,
) -> None:
    """Brackets one `run_universe_reevaluation()` call's own real provider
    calls -- tagged source="scheduler" (see the store module's own
    disclosed scope limit on why per-request feed-path calls are not
    separately attributed here). Never raises -- a recording failure must
    never break a real reevaluation run."""
    try:
        store = _get_store()
        if store is None:
            return
        endpoints = set(before.by_endpoint) | set(after.by_endpoint)
        for endpoint in sorted(endpoints):
            before_counts = before.by_endpoint.get(endpoint)
            after_counts = after.by_endpoint.get(endpoint)
            before_real = before_counts.real_calls if before_counts else 0
            after_real = after_counts.real_calls if after_counts else 0
            before_fail = before_counts.failures if before_counts else 0
            after_fail = after_counts.failures if after_counts else 0
            before_coalesced = before_counts.coalesced if before_counts else 0
            after_coalesced = after_counts.coalesced if after_counts else 0

            real_delta = after_real - before_real
            failures_delta = after_fail - before_fail
            coalesced_delta = after_coalesced - before_coalesced
            if real_delta == 0 and failures_delta == 0 and coalesced_delta == 0:
                continue  # nothing happened on this endpoint this run

            store.record_provider_call(
                ProviderCallObservation(
                    occurred_at=now,
                    source="scheduler",
                    endpoint=endpoint,
                    real_calls=max(real_delta, 0),
                    failures=max(failures_delta, 0),
                    rate_limited=0,  # real rate-limit counting is the fault
                    # mirror's job (DATA-301), not this endpoint-level
                    # delta -- avoids double-counting the same real event
                    # two different ways.
                )
            )
            store.record_coalescing(
                CoalescingObservation(
                    occurred_at=now,
                    source="scheduler",
                    endpoint=endpoint,
                    real_calls=max(real_delta, 0),
                    coalesced_calls=max(coalesced_delta, 0),
                )
            )
        _maybe_purge(now)
    except Exception as exc:  # noqa: BLE001 -- observation must never break a real run
        print(f"[operational-observation] provider-call recording failed: {exc}")


def record_scheduler_wait_samples(scheduler: ProviderScheduler, now: datetime) -> None:
    """Persists every new (not-yet-persisted) sample from `scheduler.
    wait_samples()` -- tracked by index per scheduler instance so repeated
    calls (e.g. once per reevaluation run against the same long-lived
    production scheduler) never re-persist the same sample twice. Never
    raises."""
    try:
        store = _get_store()
        if store is None:
            return
        samples = scheduler.wait_samples()
        key = id(scheduler)
        start_index = _last_persisted_wait_sample_index.get(key, 0)
        new_samples = samples[start_index:]
        store.record_provider_waits_batch(
            [
                ProviderWaitObservation(
                    occurred_at=now,
                    endpoint=sample.endpoint,
                    priority=sample.priority,
                    waited_seconds=sample.waited_seconds,
                    admitted=sample.admitted,
                )
                for sample in new_samples
            ]
        )
        _last_persisted_wait_sample_index[key] = len(samples)
    except Exception as exc:  # noqa: BLE001
        print(f"[operational-observation] wait-sample recording failed: {exc}")


def record_freshness_ratio_observation(
    *, signal_family: str, age_seconds: float, ttl_seconds: float, now: datetime
) -> None:
    """Called from logan_feed.py at the exact point a real freshness
    classification already computed a genuine numeric age -- never for a
    NO_CONTRACT or provider-failure item, which have no real age to
    report. Never raises."""
    try:
        store = _get_store()
        if store is None or ttl_seconds <= 0:
            return
        store.record_freshness_ratio(
            FreshnessRatioObservation(
                occurred_at=now,
                signal_family=signal_family,
                age_seconds=age_seconds,
                ttl_seconds=ttl_seconds,
                ratio=age_seconds / ttl_seconds,
            )
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[operational-observation] freshness-ratio recording failed: {exc}")


def record_signal_family_attempt_observations_batch(
    attempts: list[tuple[str, bool]], now: datetime
) -> None:
    """`attempts` is a list of (signal_family, qualified) pairs -- called
    once per reevaluation run with every candidate's real
    EligibilityResult.signal_family_coverage data (up to ~300 per run),
    batched into one commit rather than one per candidate. Never raises."""
    try:
        store = _get_store()
        if store is None:
            return
        store.record_signal_family_attempts_batch(
            [
                SignalFamilyAttemptObservation(
                    occurred_at=now, signal_family=family, qualified=qualified
                )
                for family, qualified in attempts
            ]
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[operational-observation] signal-family recording failed: {exc}")


# --- query / gate-input computation -----------------------------------------


def _percentile(values: list[float], p: float) -> Optional[float]:
    """Nearest-rank percentile -- deterministic, no interpolation guess.
    Returns None for an empty input (honest "no data"), never 0.0."""
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(p * (len(ordered) - 1))))
    return ordered[index]


@dataclass(frozen=True)
class OperationalGateEvidence:
    """The real, durable evidence for every operational gate this layer
    can support -- each field is None when zero real observations exist
    yet in the requested window (honest "no data," never a fabricated
    passing value)."""

    durable_fmp_rate_limit_count: int
    scheduled_provider_failure_rate: Optional[float]
    time_sensitive_delay_p95_seconds: Optional[float]
    time_sensitive_delay_p99_seconds: Optional[float]
    critical_freshness_p95_ratio: Optional[float]
    critical_freshness_p99_ratio: Optional[float]
    coalescing_success_rate: Optional[float]
    signal_family_yield: dict
    peak_calls_per_minute: Optional[int]


def build_operational_gate_evidence(
    start: datetime, end: datetime
) -> OperationalGateEvidence:
    """Real, durable evidence for the operational gates this layer
    supports, over [start, end]. Returns [] / None wherever no real
    observation exists -- never fabricates a passing value for a window
    with no data."""
    store = _get_store()
    if store is None:
        return OperationalGateEvidence(
            durable_fmp_rate_limit_count=0,
            scheduled_provider_failure_rate=None,
            time_sensitive_delay_p95_seconds=None,
            time_sensitive_delay_p99_seconds=None,
            critical_freshness_p95_ratio=None,
            critical_freshness_p99_ratio=None,
            coalescing_success_rate=None,
            signal_family_yield={},
            peak_calls_per_minute=None,
        )

    faults = store.fault_mirrors_in_range(start, end)
    rate_limit_count = sum(1 for f in faults if f.code == "DATA-301")

    calls = [
        c for c in store.provider_calls_in_range(start, end) if c.source == "scheduler"
    ]
    total_real = sum(c.real_calls for c in calls)
    total_fail = sum(c.failures for c in calls)
    failure_rate = (
        total_fail / (total_real + total_fail)
        if (total_real + total_fail) > 0
        else None
    )

    waits = [
        w.waited_seconds
        for w in store.provider_waits_in_range(start, end)
        if w.admitted
    ]
    p95_delay = _percentile(waits, 0.95)
    p99_delay = _percentile(waits, 0.99)

    ratios = [r.ratio for r in store.freshness_ratios_in_range(start, end)]
    p95_ratio = _percentile(ratios, 0.95)
    p99_ratio = _percentile(ratios, 0.99)

    coalescing = [
        c for c in store.coalescing_in_range(start, end) if c.source == "scheduler"
    ]
    total_real_c = sum(c.real_calls for c in coalescing)
    total_coalesced = sum(c.coalesced_calls for c in coalescing)
    coalescing_rate = (
        total_coalesced / (total_real_c + total_coalesced)
        if (total_real_c + total_coalesced) > 0
        else None
    )

    attempts = store.signal_family_attempts_in_range(start, end)
    by_family: dict[str, list[bool]] = {}
    for a in attempts:
        by_family.setdefault(a.signal_family, []).append(a.qualified)
    signal_family_yield = {
        family: (sum(qualified) / len(qualified) if qualified else None)
        for family, qualified in by_family.items()
    }

    return OperationalGateEvidence(
        durable_fmp_rate_limit_count=rate_limit_count,
        scheduled_provider_failure_rate=failure_rate,
        time_sensitive_delay_p95_seconds=p95_delay,
        time_sensitive_delay_p99_seconds=p99_delay,
        critical_freshness_p95_ratio=p95_ratio,
        critical_freshness_p99_ratio=p99_ratio,
        coalescing_success_rate=coalescing_rate,
        signal_family_yield=signal_family_yield,
        peak_calls_per_minute=historical_peak_calls_per_minute(start, end),
    )


def historical_peak_calls_per_minute(start: datetime, end: datetime) -> Optional[int]:
    """Master Plan Section 4 operational gate: 'provider burst never
    >220/min'. Deterministic definition: buckets every real outbound
    provider call (see fmp.py's own call-observer boundary) into its
    FIXED calendar-minute (occurred_at truncated to the minute, e.g.
    "2026-09-03T12:34"), then returns the largest single bucket's count --
    a real historical peak, computed from real persisted timestamps, never
    the current instantaneous rate (see ProviderScheduler.
    current_calls_per_minute(), a completely separate, point-in-time-only
    signal this function never touches or substitutes for).

    Fixed-minute bucketing (not a sliding 60-second window) is the
    explicit, documented choice here -- simpler, and every call falls into
    exactly one bucket unambiguously, so a call landing near a minute
    boundary is handled the same deterministic way every time. Returns
    None only when zero real calls exist in the window (honest "no data,"
    never a fabricated 0).
    """
    store = _get_store()
    if store is None:
        return None
    timestamps = store.provider_call_timestamps_in_range(start, end)
    if not timestamps:
        return None
    bucket_counts: dict[str, int] = {}
    for entry in timestamps:
        bucket_key = entry.occurred_at.replace(second=0, microsecond=0).isoformat()
        bucket_counts[bucket_key] = bucket_counts.get(bucket_key, 0) + 1
    return max(bucket_counts.values())


def observation_coverage(start: date, end: date) -> dict:
    """How many real observations of each kind exist in [start, end] --
    used by the proof-window readiness check to fail closed rather than
    treat zero observations as a passing/ready state."""
    store = _get_store()
    if store is None:
        return {
            "provider_call_observations": 0,
            "provider_wait_observations": 0,
            "freshness_ratio_observations": 0,
            "signal_family_attempt_observations": 0,
            "fault_mirror_observations": 0,
        }
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end, datetime.max.time())
    return {
        "provider_call_observations": len(
            store.provider_calls_in_range(start_dt, end_dt)
        ),
        "provider_wait_observations": len(
            store.provider_waits_in_range(start_dt, end_dt)
        ),
        "freshness_ratio_observations": len(
            store.freshness_ratios_in_range(start_dt, end_dt)
        ),
        "signal_family_attempt_observations": len(
            store.signal_family_attempts_in_range(start_dt, end_dt)
        ),
        "fault_mirror_observations": len(
            store.fault_mirrors_in_range(start_dt, end_dt)
        ),
    }
