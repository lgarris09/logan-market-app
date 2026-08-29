"""V2.3C Telemetry -- durable, append-only event history.

Mirrors `revision_store.py`'s exact pattern (the closest existing precedent
for append-only history in this codebase, not an upsert-in-place store like
`lifecycle_store.py`): `event_id` is the primary key, `INSERT OR IGNORE`
gives event-ID idempotency for free (a retried/duplicate submission of the
same event_id is a silent no-op, never a duplicate row and never an
overwrite of the original), and every column is typed/queryable, not an
opaque JSON blob -- with one exception (`context`), matching
`OpportunityRevisionStore`'s own precedent of JSON-encoding the one
naturally-nested field (`trigger_codes` there, `context` here).

Constructed only when `config.memory_persistence_enabled()` is true, same
gating as every other durable store in this file family.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import UUID

from .telemetry_models import TelemetryContext, TelemetryEvent


class TelemetryStore:
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
            "CREATE TABLE IF NOT EXISTS telemetry_events ("
            "  event_id TEXT PRIMARY KEY,"
            "  schema_version TEXT NOT NULL,"
            "  event_name TEXT NOT NULL,"
            "  occurred_at TEXT NOT NULL,"
            "  recorded_at TEXT NOT NULL,"
            "  user_id TEXT NOT NULL,"
            "  opportunity_id TEXT,"
            "  opportunity_revision INTEGER,"
            "  source_surface TEXT,"
            "  context TEXT"
            ")"
        )
        # Indexed for the exact read shapes Block E's diagnostic API needs:
        # by user (+ time-ordered), by user+opportunity, and by event_name.
        # A composite (user_id, occurred_at) index also serves plain
        # "recent events for a user" without a separate single-column one.
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_telemetry_user_time "
            "ON telemetry_events (user_id, occurred_at)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_telemetry_user_opportunity "
            "ON telemetry_events (user_id, opportunity_id)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_telemetry_event_name "
            "ON telemetry_events (event_name)"
        )
        self._conn.commit()

    def append(self, event: TelemetryEvent) -> bool:
        """INSERT OR IGNORE, keyed by event_id -- a duplicate event_id is a
        silent no-op (this store never overwrites historical telemetry).
        Returns True iff a new row was actually inserted, so callers can
        tell a genuine first write apart from a harmless resubmission.
        """
        cursor = self._conn.execute(
            "INSERT OR IGNORE INTO telemetry_events "
            "(event_id, schema_version, event_name, occurred_at, recorded_at, "
            "user_id, opportunity_id, opportunity_revision, source_surface, context) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(event.event_id),
                event.schema_version,
                event.event_name,
                event.occurred_at.isoformat(),
                event.recorded_at.isoformat(),
                event.user_id,
                str(event.opportunity_id) if event.opportunity_id else None,
                event.opportunity_revision,
                event.source_surface,
                event.context.model_dump_json() if event.context else None,
            ),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def load_all(self) -> list[TelemetryEvent]:
        """Full history, oldest first -- used once at startup to rehydrate
        the in-memory idempotency index (see telemetry.py's _get_store()).
        This codebase's telemetry volume is small enough (a handful of
        product actions, not screen-touch analytics) that loading the full
        table at startup is the same discipline every other store here
        already uses (LifecycleStore, OpportunityRevisionStore, etc.)."""
        rows = self._conn.execute(
            "SELECT * FROM telemetry_events ORDER BY occurred_at ASC"
        ).fetchall()
        return [_row_to_event(row) for row in rows]

    def close(self) -> None:
        self._conn.close()


def _row_to_event(row: sqlite3.Row) -> TelemetryEvent:
    return TelemetryEvent(
        schema_version=row["schema_version"],
        event_id=UUID(row["event_id"]),
        event_name=row["event_name"],
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
        recorded_at=datetime.fromisoformat(row["recorded_at"]),
        user_id=row["user_id"],
        opportunity_id=UUID(row["opportunity_id"]) if row["opportunity_id"] else None,
        opportunity_revision=row["opportunity_revision"],
        source_surface=row["source_surface"],
        context=(
            TelemetryContext.model_validate_json(row["context"])
            if row["context"]
            else None
        ),
    )
