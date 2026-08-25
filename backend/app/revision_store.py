"""Stock Opportunity Logic V2.1 (User Sync Gap) -- durable global
meaningful-revision history.

Append-only, per the explicit "do not persist every poll" instruction: a row
is written only when `OpportunityLifecycleTracker.observe()` produced a
*global* (objective, not personal-relevance-only) meaningful change this poll
-- see logan_feed.py's write-through call, right beside the existing
LifecycleStore.save() call. Deliberately typed/queryable core columns, not an
opaque JSON blob, per the owner's explicit instruction -- the one exception
is `trigger_codes`, a short list of strings serialized as JSON, matching
LifecycleStore's own existing precedent for that same field.

Mirrors `lifecycle_store.py`/`notification_store.py`'s established pattern
exactly: a separate SQLite file, gated behind the same STRATUS_PERSIST_MEMORY
flag, load-on-first-use, write-through on mutation.
"""

import json
import sqlite3
from pathlib import Path

from logan_core.contracts import OpportunityRevision


class OpportunityRevisionStore:
    """Durable backing for each entity's meaningful-revision history.
    Constructed only when `config.memory_persistence_enabled()` is true --
    disabled mode never imports sqlite3 or touches disk.
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
            "CREATE TABLE IF NOT EXISTS opportunity_revisions ("
            "  entity_id TEXT NOT NULL,"
            "  revision INTEGER NOT NULL,"
            "  lifecycle_state TEXT NOT NULL,"
            "  confidence_score REAL NOT NULL,"
            "  trigger_codes TEXT NOT NULL,"
            "  change_type TEXT NOT NULL,"
            "  reason TEXT NOT NULL,"
            "  created_at TEXT NOT NULL,"
            "  PRIMARY KEY (entity_id, revision)"
            ")"
        )
        self._conn.commit()

    def append(self, revision: OpportunityRevision) -> None:
        """INSERT OR IGNORE: a re-delivered write for a revision this store
        already has (e.g. a retried request after a crash mid-poll) is a
        no-op, never a duplicate or a silently-overwritten history row --
        history is append-only, not upsert-in-place like the current-state
        stores.
        """
        self._conn.execute(
            "INSERT OR IGNORE INTO opportunity_revisions "
            "(entity_id, revision, lifecycle_state, confidence_score, "
            "trigger_codes, change_type, reason, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                revision.entity_id,
                revision.revision,
                revision.lifecycle_state,
                revision.confidence_score,
                json.dumps(revision.trigger_codes),
                revision.change_type,
                revision.reason,
                revision.created_at.isoformat(),
            ),
        )
        self._conn.commit()

    def history_for_entity(self, entity_id: str) -> list[OpportunityRevision]:
        rows = self._conn.execute(
            "SELECT entity_id, revision, lifecycle_state, confidence_score, "
            "trigger_codes, change_type, reason, created_at "
            "FROM opportunity_revisions WHERE entity_id = ? ORDER BY revision ASC",
            (entity_id,),
        ).fetchall()
        return [
            OpportunityRevision(
                entity_id=row["entity_id"],
                revision=row["revision"],
                lifecycle_state=row["lifecycle_state"],
                confidence_score=row["confidence_score"],
                trigger_codes=json.loads(row["trigger_codes"]),
                change_type=row["change_type"],
                reason=row["reason"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def latest_revision(self, entity_id: str) -> int | None:
        row = self._conn.execute(
            "SELECT MAX(revision) AS latest FROM opportunity_revisions "
            "WHERE entity_id = ?",
            (entity_id,),
        ).fetchone()
        return row["latest"] if row and row["latest"] is not None else None

    def clear(self) -> None:
        self._conn.execute("DELETE FROM opportunity_revisions")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
