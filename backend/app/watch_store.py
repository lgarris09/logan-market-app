"""Minimal STRATUS Watch (V2.3E) -- durable per-(user_id, entity_id) row
recording one explicit fact: "this user asked STRATUS to keep watching this
opportunity." Not a portfolio, not a notification-rule builder, not inferred
from behavior -- see backend/app/watch.py's own module docstring for the
full scope boundary this was built to.

Mirrors user_knowledge_store.py's established pattern exactly: a separate
SQLite file, gated behind config.memory_persistence_enabled(), load-on-
first-use, write-through on mutation, one row per (user_id, entity_id) --
deliberately UPSERT-shaped storage (INSERT OR IGNORE), not one row per
watch/unwatch action, since only "is this currently watched" is durable
state; the history of toggling it is not a concept this store has.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel


class Watch(BaseModel):
    schema_version: str = "1.0"
    user_id: str
    entity_id: str
    created_at: datetime


class WatchStore:
    """Durable backing for `Watch` rows -- constructed only when
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
            "CREATE TABLE IF NOT EXISTS watches ("
            "  user_id TEXT NOT NULL,"
            "  entity_id TEXT NOT NULL,"
            "  created_at TEXT NOT NULL,"
            "  PRIMARY KEY (user_id, entity_id)"
            ")"
        )
        self._conn.commit()

    def load_all(self) -> list[Watch]:
        rows = self._conn.execute(
            "SELECT user_id, entity_id, created_at FROM watches"
        ).fetchall()
        return [
            Watch(
                user_id=row["user_id"],
                entity_id=row["entity_id"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def save(self, watch: Watch) -> None:
        """INSERT OR IGNORE -- a repeat save for an already-watched
        (user_id, entity_id) is a durable no-op, never a second row and
        never a refreshed created_at. The in-memory idempotency check in
        watch.py's create_watch() already prevents this from ever firing on
        a genuine duplicate in practice; this is the storage layer's own
        independent guarantee, not a duplicate of that check."""
        self._conn.execute(
            "INSERT OR IGNORE INTO watches (user_id, entity_id, created_at) "
            "VALUES (?, ?, ?)",
            (watch.user_id, watch.entity_id, watch.created_at.isoformat()),
        )
        self._conn.commit()

    def delete(self, user_id: str, entity_id: str) -> bool:
        """Returns True iff a row genuinely existed and was removed."""
        cursor = self._conn.execute(
            "DELETE FROM watches WHERE user_id = ? AND entity_id = ?",
            (user_id, entity_id),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def delete_user(self, user_id: str) -> None:
        """The Watch half of purge_user_data() (see account_lifecycle.py).
        Removes every watch for `user_id`, across every entity."""
        self._conn.execute("DELETE FROM watches WHERE user_id = ?", (user_id,))
        self._conn.commit()

    def clear(self) -> None:
        self._conn.execute("DELETE FROM watches")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
