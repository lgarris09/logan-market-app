"""Universe Manager V1a Block 5 -- durable backing for the Universe
Membership Ledger. Mirrors watch_store.py's established pattern exactly: a
separate SQLite file, gated behind config.memory_persistence_enabled(),
load-on-first-use, append-only for history (a removal never overwrites its
row -- it's a plain UPDATE of that same row's closing fields, since a
MembershipRecord's identity IS the (canonical_id, effective_from) interval,
never a second row for the same interval).

Unlike WatchStore's UPSERT-shaped "only current state matters" storage,
this store is genuinely historical: every past membership interval stays
queryable forever (Block 5's "why was STRATUS monitoring this security on a
particular date" requirement) -- rows are never deleted except by
`clear()` (test-only) or a future, explicit data-retention decision, never
by normal rebalance operation.
"""

import sqlite3
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from logan_core.contracts import MembershipRecord  # noqa: E402


class UniverseMembershipStore:
    """Durable backing for `MembershipRecord` rows -- constructed only when
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
            "CREATE TABLE IF NOT EXISTS universe_membership ("
            "  canonical_id TEXT NOT NULL,"
            "  symbol TEXT NOT NULL,"
            "  source_version TEXT NOT NULL,"
            "  policy_version TEXT NOT NULL,"
            "  admission_reason_codes TEXT NOT NULL,"  # JSON list
            "  admitted_at TEXT NOT NULL,"
            "  effective_from TEXT NOT NULL,"
            "  effective_until TEXT,"
            "  removed_at TEXT,"
            "  removal_reason TEXT,"
            "  replacement_of TEXT,"
            "  provider_health_snapshot TEXT NOT NULL,"  # JSON object
            "  PRIMARY KEY (canonical_id, effective_from)"
            ")"
        )
        self._conn.commit()

    def _row_to_record(self, row: sqlite3.Row) -> MembershipRecord:
        import json

        return MembershipRecord(
            canonical_id=row["canonical_id"],
            symbol=row["symbol"],
            source_version=row["source_version"],
            policy_version=row["policy_version"],
            admission_reason_codes=json.loads(row["admission_reason_codes"]),
            admitted_at=row["admitted_at"],
            effective_from=row["effective_from"],
            effective_until=row["effective_until"],
            removed_at=row["removed_at"],
            removal_reason=row["removal_reason"],
            replacement_of=row["replacement_of"],
            provider_health_snapshot=json.loads(row["provider_health_snapshot"]),
        )

    def load_all(self) -> list[MembershipRecord]:
        rows = self._conn.execute(
            "SELECT * FROM universe_membership ORDER BY effective_from"
        ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def load_open(self) -> list[MembershipRecord]:
        """Only currently-open (still-monitored) records -- the input
        `rebalance_membership()` (logan_core/universe/membership_ledger.py)
        expects as `current_members`."""
        rows = self._conn.execute(
            "SELECT * FROM universe_membership WHERE effective_until IS NULL "
            "ORDER BY effective_from"
        ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def save_admission(self, record: MembershipRecord) -> None:
        """Inserts a brand-new open membership interval. Never called for a
        record that already has effective_until set -- see save_removal for
        closing an existing one."""
        import json

        self._conn.execute(
            "INSERT INTO universe_membership ("
            "  canonical_id, symbol, source_version, policy_version,"
            "  admission_reason_codes, admitted_at, effective_from,"
            "  effective_until, removed_at, removal_reason, replacement_of,"
            "  provider_health_snapshot"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record.canonical_id,
                record.symbol,
                record.source_version,
                record.policy_version,
                json.dumps(record.admission_reason_codes),
                record.admitted_at.isoformat(),
                record.effective_from.isoformat(),
                None,
                None,
                None,
                record.replacement_of,
                json.dumps(record.provider_health_snapshot),
            ),
        )
        self._conn.commit()

    def save_removal(self, record: MembershipRecord) -> None:
        """Closes the existing open row matching `record`'s own
        (canonical_id, effective_from) -- `record` must be the closed copy
        `rebalance_membership()` produced (effective_until/removed_at/
        removal_reason all set), never a brand-new interval."""
        self._conn.execute(
            "UPDATE universe_membership SET effective_until = ?, removed_at = ?, "
            "removal_reason = ? WHERE canonical_id = ? AND effective_from = ?",
            (
                record.effective_until.isoformat() if record.effective_until else None,
                record.removed_at.isoformat() if record.removed_at else None,
                record.removal_reason,
                record.canonical_id,
                record.effective_from.isoformat(),
            ),
        )
        self._conn.commit()

    def clear(self) -> None:
        self._conn.execute("DELETE FROM universe_membership")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
