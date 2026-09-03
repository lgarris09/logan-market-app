"""V1a Proof-Instrumentation Closeout -- the smallest durable, per-event
operational observation layer needed to evaluate the Master Plan's
(STRATUS_Master_Implementation_Plan_2026-08-30_REV1.md) written operational
gates from real, restart-safe, arbitrary-14-day-window data instead of
in-memory, process-lifetime proxies.

Explicit scope guardrails (do not expand beyond these without stopping and
reporting, per this session's own instruction):
  - V1a operational proof only -- never a general analytics platform.
  - Not user-engagement telemetry, not Personal Learning, not a
    replacement for V2.3C's usefulness telemetry (backend/app/telemetry.py)
    -- that module owns per-user interaction events; this one owns
    system-level operational facts (provider health, scheduler timing,
    freshness ratios, signal-family yield) with no user_id anywhere in it.
  - Append-only, minimum fields per named operational gate -- five small
    tables, each mapping 1:1 to a specific Master Plan operational-gate
    input (see each table's own docstring below).
  - Bounded, explicitly configurable retention
    (config.operational_observation_retention_days(), default 45 days --
    comfortably covers the 14-day proof window plus review margin).
  - Restart-safe: durable SQLite, same established pattern as every other
    store in this codebase (config-gated behind
    memory_persistence_enabled(), load-on-first-use).
  - No sensitive user data anywhere in this schema -- every table's fields
    are provider/scheduler/freshness facts, never a user_id, IP, or
    behavioral signal.
  - No LLM/semantic interpretation anywhere in this module.

Known, disclosed limitation (not silently smoothed over): `FmpResponseCache`
is one process-wide singleton shared by both the background reevaluation
scheduler and the per-request feed pipeline (see fmp.py's own docstring).
`provider_call_observations`/`coalescing_observations` are recorded only
by bracketing a reevaluation run's own before/after budget snapshot,
tagged source="scheduler" -- the specific population the Master Plan's
"scheduled provider failure rate" gate names. This does not separately
attribute per-request feed-path calls to a "feed_request" source, because
doing so via the same shared cumulative counters would create a real
attribution race if a reevaluation run and a per-request call interleave
concurrently -- an honest gap, not a number that looks precise but isn't.
"""

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class ProviderCallObservation:
    """Master Plan Section 4 operational gates: 'scheduled provider
    failure rate <1%' and (via the `rate_limited` flag) 'FMP rate-limit
    responses: 0'. One row per (source, endpoint) delta captured at a
    reevaluation run's completion -- an aggregate over that run's own
    calls, not one row per individual HTTP call (see module docstring for
    why per-call attribution isn't attempted)."""

    occurred_at: datetime
    source: str  # "scheduler" -- see module docstring's disclosed scope limit
    endpoint: str
    real_calls: int
    failures: int
    rate_limited: int


@dataclass(frozen=True)
class CoalescingObservation:
    """Master Plan Section 4 operational gate: 'coalescing success rate
    >99%'. One row per (source, endpoint) delta per reevaluation run,
    mirroring ProviderCallObservation's own scope."""

    occurred_at: datetime
    source: str
    endpoint: str
    real_calls: int
    coalesced_calls: int


@dataclass(frozen=True)
class ProviderWaitObservation:
    """Master Plan Section 4 operational gates: 'time-sensitive scheduler
    P95 <5 min, P99 <15 min'. One row per admitted/denied call from
    `ProviderScheduler.wait_samples()`, persisted at reevaluation-run
    completion. `occurred_at` is the run's own completion timestamp for
    every sample in that run (this codebase's ProviderScheduler does not
    itself timestamp individual samples in wall-clock terms) -- sufficient
    for a real P95/P99 distribution of `waited_seconds` across many runs,
    not for reconstructing a true intra-run, minute-by-minute timeline."""

    occurred_at: datetime
    endpoint: str
    priority: str
    waited_seconds: float
    admitted: bool


@dataclass(frozen=True)
class FreshnessRatioObservation:
    """Master Plan Section 4 operational gates: 'critical freshness P95
    <=1.25x TTL, P99 <=2x TTL'. One row per real per-item freshness
    classification with a genuinely computed age (never a NO_CONTRACT or
    provider-failure item, which have no numeric age to report)."""

    occurred_at: datetime
    signal_family: str
    age_seconds: float
    ttl_seconds: float
    ratio: float


@dataclass(frozen=True)
class SignalFamilyAttemptObservation:
    """Master Plan measurement list: 'signal-family yield' -- the
    denominator (attempted) this codebase previously had no primitive for.
    One row per (candidate, signal_family) coverage check during a
    reevaluation run, real from EligibilityResult.signal_family_coverage."""

    occurred_at: datetime
    signal_family: str
    qualified: bool


@dataclass(frozen=True)
class FaultMirrorObservation:
    """Master Plan Section 4 operational gate: 'FMP rate-limit responses:
    0'. A durable, real-time mirror of every logan_core fault occurrence
    (see logan_core.diagnostics.fault_codes.set_fault_sink()) -- the
    in-memory 200-entry ring buffer that already exists is not durable and
    cannot support a genuine 14-day count."""

    occurred_at: datetime
    code: str
    correlation_id: str


class UniverseOperationalObservationStore:
    """Durable backing for the five observation tables above -- constructed
    only when config.memory_persistence_enabled() is true. Every `record_*`
    method is append-only; nothing here is ever updated in place."""

    def __init__(self, db_path: str | Path) -> None:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection = sqlite3.connect(
            str(path), check_same_thread=False
        )
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS provider_call_observations ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  occurred_at TEXT NOT NULL,"
            "  source TEXT NOT NULL,"
            "  endpoint TEXT NOT NULL,"
            "  real_calls INTEGER NOT NULL,"
            "  failures INTEGER NOT NULL,"
            "  rate_limited INTEGER NOT NULL"
            ")"
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS coalescing_observations ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  occurred_at TEXT NOT NULL,"
            "  source TEXT NOT NULL,"
            "  endpoint TEXT NOT NULL,"
            "  real_calls INTEGER NOT NULL,"
            "  coalesced_calls INTEGER NOT NULL"
            ")"
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS provider_wait_observations ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  occurred_at TEXT NOT NULL,"
            "  endpoint TEXT NOT NULL,"
            "  priority TEXT NOT NULL,"
            "  waited_seconds REAL NOT NULL,"
            "  admitted INTEGER NOT NULL"
            ")"
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS freshness_ratio_observations ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  occurred_at TEXT NOT NULL,"
            "  signal_family TEXT NOT NULL,"
            "  age_seconds REAL NOT NULL,"
            "  ttl_seconds REAL NOT NULL,"
            "  ratio REAL NOT NULL"
            ")"
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS signal_family_attempt_observations ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  occurred_at TEXT NOT NULL,"
            "  signal_family TEXT NOT NULL,"
            "  qualified INTEGER NOT NULL"
            ")"
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS fault_mirror_observations ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  occurred_at TEXT NOT NULL,"
            "  code TEXT NOT NULL,"
            "  correlation_id TEXT NOT NULL UNIQUE"
            ")"
        )
        self._conn.commit()

    # --- recording (append-only) ---------------------------------------

    def record_provider_call(self, obs: ProviderCallObservation) -> None:
        self._conn.execute(
            "INSERT INTO provider_call_observations "
            "(occurred_at, source, endpoint, real_calls, failures, rate_limited) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                obs.occurred_at.isoformat(),
                obs.source,
                obs.endpoint,
                obs.real_calls,
                obs.failures,
                int(obs.rate_limited),
            ),
        )
        self._conn.commit()

    def record_coalescing(self, obs: CoalescingObservation) -> None:
        self._conn.execute(
            "INSERT INTO coalescing_observations "
            "(occurred_at, source, endpoint, real_calls, coalesced_calls) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                obs.occurred_at.isoformat(),
                obs.source,
                obs.endpoint,
                obs.real_calls,
                obs.coalesced_calls,
            ),
        )
        self._conn.commit()

    def record_provider_wait(self, obs: ProviderWaitObservation) -> None:
        self.record_provider_waits_batch([obs])

    def record_provider_waits_batch(
        self, observations: list[ProviderWaitObservation]
    ) -> None:
        """One commit for the whole batch -- a single reevaluation run can
        produce up to ~400 wait samples (100 candidates x 4 endpoints), and
        committing once per row measurably slows down every real run for
        no benefit (nothing reads this table mid-run)."""
        if not observations:
            return
        self._conn.executemany(
            "INSERT INTO provider_wait_observations "
            "(occurred_at, endpoint, priority, waited_seconds, admitted) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                (
                    obs.occurred_at.isoformat(),
                    obs.endpoint,
                    obs.priority,
                    obs.waited_seconds,
                    int(obs.admitted),
                )
                for obs in observations
            ],
        )
        self._conn.commit()

    def record_freshness_ratio(self, obs: FreshnessRatioObservation) -> None:
        self._conn.execute(
            "INSERT INTO freshness_ratio_observations "
            "(occurred_at, signal_family, age_seconds, ttl_seconds, ratio) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                obs.occurred_at.isoformat(),
                obs.signal_family,
                obs.age_seconds,
                obs.ttl_seconds,
                obs.ratio,
            ),
        )
        self._conn.commit()

    def record_signal_family_attempt(self, obs: SignalFamilyAttemptObservation) -> None:
        self.record_signal_family_attempts_batch([obs])

    def record_signal_family_attempts_batch(
        self, observations: list[SignalFamilyAttemptObservation]
    ) -> None:
        """One commit for the whole batch -- see record_provider_waits_batch's
        own docstring for why (a reevaluation run produces 3 observations
        per candidate, up to ~300 per run)."""
        if not observations:
            return
        self._conn.executemany(
            "INSERT INTO signal_family_attempt_observations "
            "(occurred_at, signal_family, qualified) VALUES (?, ?, ?)",
            [
                (obs.occurred_at.isoformat(), obs.signal_family, int(obs.qualified))
                for obs in observations
            ],
        )
        self._conn.commit()

    def record_fault_mirror(self, obs: FaultMirrorObservation) -> None:
        """INSERT OR IGNORE keyed on correlation_id -- a fault occurrence
        must never be double-counted if this is ever called more than once
        for the same real occurrence."""
        self._conn.execute(
            "INSERT OR IGNORE INTO fault_mirror_observations "
            "(occurred_at, code, correlation_id) VALUES (?, ?, ?)",
            (obs.occurred_at.isoformat(), obs.code, obs.correlation_id),
        )
        self._conn.commit()

    # --- querying (read-only) -------------------------------------------

    def provider_calls_in_range(
        self, start: datetime, end: datetime
    ) -> list[ProviderCallObservation]:
        rows = self._conn.execute(
            "SELECT * FROM provider_call_observations "
            "WHERE occurred_at >= ? AND occurred_at <= ? ORDER BY occurred_at",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        return [
            ProviderCallObservation(
                occurred_at=datetime.fromisoformat(r["occurred_at"]),
                source=r["source"],
                endpoint=r["endpoint"],
                real_calls=r["real_calls"],
                failures=r["failures"],
                rate_limited=r["rate_limited"],
            )
            for r in rows
        ]

    def coalescing_in_range(
        self, start: datetime, end: datetime
    ) -> list[CoalescingObservation]:
        rows = self._conn.execute(
            "SELECT * FROM coalescing_observations "
            "WHERE occurred_at >= ? AND occurred_at <= ? ORDER BY occurred_at",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        return [
            CoalescingObservation(
                occurred_at=datetime.fromisoformat(r["occurred_at"]),
                source=r["source"],
                endpoint=r["endpoint"],
                real_calls=r["real_calls"],
                coalesced_calls=r["coalesced_calls"],
            )
            for r in rows
        ]

    def provider_waits_in_range(
        self, start: datetime, end: datetime
    ) -> list[ProviderWaitObservation]:
        rows = self._conn.execute(
            "SELECT * FROM provider_wait_observations "
            "WHERE occurred_at >= ? AND occurred_at <= ? ORDER BY occurred_at",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        return [
            ProviderWaitObservation(
                occurred_at=datetime.fromisoformat(r["occurred_at"]),
                endpoint=r["endpoint"],
                priority=r["priority"],
                waited_seconds=r["waited_seconds"],
                admitted=bool(r["admitted"]),
            )
            for r in rows
        ]

    def freshness_ratios_in_range(
        self, start: datetime, end: datetime
    ) -> list[FreshnessRatioObservation]:
        rows = self._conn.execute(
            "SELECT * FROM freshness_ratio_observations "
            "WHERE occurred_at >= ? AND occurred_at <= ? ORDER BY occurred_at",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        return [
            FreshnessRatioObservation(
                occurred_at=datetime.fromisoformat(r["occurred_at"]),
                signal_family=r["signal_family"],
                age_seconds=r["age_seconds"],
                ttl_seconds=r["ttl_seconds"],
                ratio=r["ratio"],
            )
            for r in rows
        ]

    def signal_family_attempts_in_range(
        self, start: datetime, end: datetime
    ) -> list[SignalFamilyAttemptObservation]:
        rows = self._conn.execute(
            "SELECT * FROM signal_family_attempt_observations "
            "WHERE occurred_at >= ? AND occurred_at <= ? ORDER BY occurred_at",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        return [
            SignalFamilyAttemptObservation(
                occurred_at=datetime.fromisoformat(r["occurred_at"]),
                signal_family=r["signal_family"],
                qualified=bool(r["qualified"]),
            )
            for r in rows
        ]

    def fault_mirrors_in_range(
        self, start: datetime, end: datetime
    ) -> list[FaultMirrorObservation]:
        rows = self._conn.execute(
            "SELECT * FROM fault_mirror_observations "
            "WHERE occurred_at >= ? AND occurred_at <= ? ORDER BY occurred_at",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        return [
            FaultMirrorObservation(
                occurred_at=datetime.fromisoformat(r["occurred_at"]),
                code=r["code"],
                correlation_id=r["correlation_id"],
            )
            for r in rows
        ]

    # --- retention --------------------------------------------------------

    def purge_older_than(self, cutoff: date) -> None:
        """Deletes every observation strictly older than `cutoff` across
        all six tables -- bounded, explicit retention (see module
        docstring), never touches a row on or after `cutoff`."""
        cutoff_text = cutoff.isoformat()
        for table in (
            "provider_call_observations",
            "coalescing_observations",
            "provider_wait_observations",
            "freshness_ratio_observations",
            "signal_family_attempt_observations",
            "fault_mirror_observations",
        ):
            self._conn.execute(
                f"DELETE FROM {table} WHERE occurred_at < ?", (cutoff_text,)
            )
        self._conn.commit()

    def clear(self) -> None:
        for table in (
            "provider_call_observations",
            "coalescing_observations",
            "provider_wait_observations",
            "freshness_ratio_observations",
            "signal_family_attempt_observations",
            "fault_mirror_observations",
        ):
            self._conn.execute(f"DELETE FROM {table}")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
