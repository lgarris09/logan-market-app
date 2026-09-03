"""Universe Manager V1a Scheduler Persistence + Cadence Closeout -- durable
backing for restart-safe reevaluation cadence bookkeeping. Deliberately a
separate table (and separate store class, separate file -- see
config.universe_scheduler_state_db_path()) from UniverseMembershipStore's
`universe_membership` table: that ledger stays scoped to membership
history only (see universe_store.py's own docstring), and scheduler
execution state (last-run timestamps, outcome) is a distinct concern that
never touches it. Mirrors UniverseMembershipStore's established connection/
schema pattern, but is upsert-shaped (only one row per job -- current
execution state -- ever matters here), not append-only history.
"""

import sqlite3
from pathlib import Path
from typing import Optional

from logan_core.contracts import SchedulerJobState


class UniverseSchedulerStateStore:
    """Durable backing for `SchedulerJobState` rows -- constructed only when
    config.memory_persistence_enabled() is true."""

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
            "CREATE TABLE IF NOT EXISTS universe_scheduler_state ("
            "  job_name TEXT PRIMARY KEY,"
            "  last_started_at TEXT,"
            "  last_completed_at TEXT,"
            "  last_succeeded_at TEXT,"
            "  last_outcome TEXT"
            ")"
        )
        self._conn.commit()

    def _row_to_state(self, row: sqlite3.Row) -> SchedulerJobState:
        return SchedulerJobState(
            job_name=row["job_name"],
            last_started_at=row["last_started_at"],
            last_completed_at=row["last_completed_at"],
            last_succeeded_at=row["last_succeeded_at"],
            last_outcome=row["last_outcome"],
        )

    def get(self, job_name: str) -> Optional[SchedulerJobState]:
        row = self._conn.execute(
            "SELECT * FROM universe_scheduler_state WHERE job_name = ?",
            (job_name,),
        ).fetchone()
        return self._row_to_state(row) if row is not None else None

    def all_jobs(self) -> list[SchedulerJobState]:
        """Every job's current state, for scheduler diagnostics -- ordered
        by job_name for deterministic output."""
        rows = self._conn.execute(
            "SELECT * FROM universe_scheduler_state ORDER BY job_name"
        ).fetchall()
        return [self._row_to_state(row) for row in rows]

    def mark_started(self, job_name: str, started_at) -> None:
        """Records the start of one attempt. Upserts rather than inserts --
        a job's row is a single current-state record, never a history of
        past attempts (that's what the membership ledger's own append-only
        pattern is for; this store's job is cadence gating, not audit
        history)."""
        self._conn.execute(
            "INSERT INTO universe_scheduler_state (job_name, last_started_at, last_outcome) "
            "VALUES (?, ?, 'running') "
            "ON CONFLICT(job_name) DO UPDATE SET "
            "  last_started_at = excluded.last_started_at, "
            "  last_outcome = excluded.last_outcome",
            (job_name, started_at.isoformat()),
        )
        self._conn.commit()

    def mark_completed(self, job_name: str, completed_at, *, outcome: str) -> None:
        """Records how one attempt ended. `outcome` is `"success"` or
        `"failure"` -- `last_succeeded_at` is only ever advanced on
        `"success"`, so a failed run never fabricates a successful
        timestamp."""
        if outcome == "success":
            self._conn.execute(
                "UPDATE universe_scheduler_state SET last_completed_at = ?, "
                "last_outcome = ?, last_succeeded_at = ? WHERE job_name = ?",
                (
                    completed_at.isoformat(),
                    outcome,
                    completed_at.isoformat(),
                    job_name,
                ),
            )
        else:
            self._conn.execute(
                "UPDATE universe_scheduler_state SET last_completed_at = ?, "
                "last_outcome = ? WHERE job_name = ?",
                (completed_at.isoformat(), outcome, job_name),
            )
        self._conn.commit()

    def clear(self) -> None:
        self._conn.execute("DELETE FROM universe_scheduler_state")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
