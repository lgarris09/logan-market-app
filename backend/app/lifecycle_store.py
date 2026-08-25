"""Stock Opportunity Logic V2 -- durable Opportunity Lifecycle state.

Meaningful-change detection (logan_core/opportunity_lifecycle/tracker.py)
requires comparing the current poll against a *prior* snapshot -- without
durable storage, every backend restart/redeploy would silently reset every
opportunity back to "new" (exactly the restart-safety gap the Sprint 3.6.9
audit's own test scenarios explicitly require closing) and could produce a
duplicate notification for an opportunity a user had already been alerted
about pre-restart.

Deliberately compact, per the owner's explicit "do not persist huge raw
provider payload histories if a compact structured state is enough"
instruction: this stores only `LifecycleSnapshot`'s own small set of fields
(confidence_score, the active trigger_code set, lifecycle_state, and three
timestamps) -- never raw provider payloads or full signal history. Keyed by
`entity_id` only, matching `OpportunityLifecycleTracker`'s own scope: this
is objective, shared-across-users world-fact state (two users must see the
identical objective lifecycle for the same real-world opportunity), not
per-user state. Per-user personal-relevance-change tracking remains
process-memory-only, matching this codebase's existing AttentionState
precedent (fatigue/cooldown are not durable either) -- a deliberate,
documented, bounded scope choice, not an oversight; see the Sprint 3.6.9
Stock Opportunity Logic V2 ADR.

Mirrors `notification_store.py`'s established pattern exactly: a separate,
independent SQLite file (a sibling of `memory_store_db_path()`'s own file),
gated behind the same `STRATUS_PERSIST_MEMORY` flag, load-on-first-use,
write-through on mutation.
"""

import json
import sqlite3
from pathlib import Path

from logan_core.contracts import LifecycleSnapshot


class LifecycleStore:
    """Durable backing for `OpportunityLifecycleTracker`'s per-`entity_id`
    snapshots. Constructed only when `config.memory_persistence_enabled()`
    is true -- disabled mode never imports sqlite3 or touches disk,
    byte-for-byte the pre-Sprint-3.6.9 in-memory-only behavior.
    """

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
            "CREATE TABLE IF NOT EXISTS lifecycle_snapshots ("
            "  entity_id TEXT PRIMARY KEY,"
            "  lifecycle_state TEXT NOT NULL,"
            "  confidence_score REAL NOT NULL,"
            "  trigger_codes TEXT NOT NULL,"
            "  first_seen_at TEXT NOT NULL,"
            "  last_meaningful_change_at TEXT NOT NULL,"
            "  last_notification_worthy_at TEXT,"
            "  last_evaluated_at TEXT NOT NULL"
            ")"
        )
        # Stock Opportunity Logic V2.1 (User Sync Gap): additive column on an
        # existing table -- a plain CREATE TABLE would silently do nothing
        # against a pre-V2.1 database file already on disk (e.g. the hosted
        # Fly volume's already-live v7 deployment), leaving `revision`
        # missing and every read below failing. ALTER TABLE ADD COLUMN is
        # itself idempotent-unsafe (errors if the column already exists), so
        # this is guarded rather than run unconditionally every startup.
        existing_columns = {
            row["name"]
            for row in self._conn.execute(
                "PRAGMA table_info(lifecycle_snapshots)"
            ).fetchall()
        }
        if "revision" not in existing_columns:
            self._conn.execute(
                "ALTER TABLE lifecycle_snapshots ADD COLUMN revision INTEGER "
                "NOT NULL DEFAULT 1"
            )
            existing_columns.add("revision")
        # Stock Opportunity Logic V2.2 (Evidence + Trajectory Enrichment):
        # same additive-column-guard pattern as `revision` above -- every
        # new column is nullable (no NOT NULL/DEFAULT constraint beyond
        # `trajectory`, which defaults to the same inert "STEADY" every
        # pre-V2.2 row should be read back as).
        v22_columns = {
            "trigger_price": "REAL",
            "price_at_last_revision": "REAL",
            "last_relative_strength": "REAL",
            "last_volume_ratio": "REAL",
            "trajectory": "TEXT NOT NULL DEFAULT 'STEADY'",
        }
        for column, ddl in v22_columns.items():
            if column not in existing_columns:
                self._conn.execute(
                    f"ALTER TABLE lifecycle_snapshots ADD COLUMN {column} {ddl}"
                )
        self._conn.commit()

    def load_all(self) -> list[LifecycleSnapshot]:
        rows = self._conn.execute(
            "SELECT entity_id, lifecycle_state, confidence_score, trigger_codes, "
            "first_seen_at, last_meaningful_change_at, last_notification_worthy_at, "
            "last_evaluated_at, revision, trigger_price, price_at_last_revision, "
            "last_relative_strength, last_volume_ratio, trajectory "
            "FROM lifecycle_snapshots"
        ).fetchall()
        return [
            LifecycleSnapshot(
                entity_id=row["entity_id"],
                lifecycle_state=row["lifecycle_state"],
                confidence_score=row["confidence_score"],
                trigger_codes=json.loads(row["trigger_codes"]),
                first_seen_at=row["first_seen_at"],
                last_meaningful_change_at=row["last_meaningful_change_at"],
                last_notification_worthy_at=row["last_notification_worthy_at"],
                last_evaluated_at=row["last_evaluated_at"],
                revision=row["revision"],
                trigger_price=row["trigger_price"],
                price_at_last_revision=row["price_at_last_revision"],
                last_relative_strength=row["last_relative_strength"],
                last_volume_ratio=row["last_volume_ratio"],
                trajectory=row["trajectory"],
            )
            for row in rows
        ]

    def save(self, snapshot: LifecycleSnapshot) -> None:
        self._conn.execute(
            "INSERT INTO lifecycle_snapshots "
            "(entity_id, lifecycle_state, confidence_score, trigger_codes, "
            "first_seen_at, last_meaningful_change_at, last_notification_worthy_at, "
            "last_evaluated_at, revision, trigger_price, price_at_last_revision, "
            "last_relative_strength, last_volume_ratio, trajectory) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(entity_id) DO UPDATE SET "
            "lifecycle_state=excluded.lifecycle_state, "
            "confidence_score=excluded.confidence_score, "
            "trigger_codes=excluded.trigger_codes, "
            "last_meaningful_change_at=excluded.last_meaningful_change_at, "
            "last_notification_worthy_at=excluded.last_notification_worthy_at, "
            "last_evaluated_at=excluded.last_evaluated_at, "
            "revision=excluded.revision, "
            "trigger_price=excluded.trigger_price, "
            "price_at_last_revision=excluded.price_at_last_revision, "
            "last_relative_strength=excluded.last_relative_strength, "
            "last_volume_ratio=excluded.last_volume_ratio, "
            "trajectory=excluded.trajectory",
            (
                snapshot.entity_id,
                snapshot.lifecycle_state,
                snapshot.confidence_score,
                json.dumps(snapshot.trigger_codes),
                snapshot.first_seen_at.isoformat(),
                snapshot.last_meaningful_change_at.isoformat(),
                (
                    snapshot.last_notification_worthy_at.isoformat()
                    if snapshot.last_notification_worthy_at
                    else None
                ),
                snapshot.last_evaluated_at.isoformat(),
                snapshot.revision,
                snapshot.trigger_price,
                snapshot.price_at_last_revision,
                snapshot.last_relative_strength,
                snapshot.last_volume_ratio,
                snapshot.trajectory,
            ),
        )
        self._conn.commit()

    def clear(self) -> None:
        self._conn.execute("DELETE FROM lifecycle_snapshots")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
