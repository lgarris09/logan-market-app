"""Sprint 3.6.9 Block 1 -- durable STRATUS Watch state.

Reconnaissance for Sprint 3.6.9 Block 1 found that registered Expo push
tokens and dispatch/review dedup state (backend/app/notifications.py) were
process-memory only, unrelated to STRATUS_PERSIST_MEMORY -- meaning every
backend redeploy silently dropped every tester's push registration, and
every dispatch's dedup history, requiring the app be reopened just to
re-register. This is the minimum durable state needed to avoid that: which
tokens are registered per user, and which event_ids have already been
pushed/reviewed per user (so a redeploy can never re-push -- or fail to
mark reviewed -- something it already handled).

Deliberately narrow, mirroring logan_core/memory/store.py's own SQLite
pattern rather than inventing a new one: a separate, independent SQLite file
from MemoryStore's own (see config.notification_store_db_path()), so this
store's schema/lifecycle never contends with MemoryStore's. What stays
process-memory-only (Ask STRATUS session history, OpportunityContext cache,
World Model/orchestrator event identity, Prioritization's AttentionState/
Watch fatigue-cooldown) is a deliberate scope decision, not an oversight --
see the Sprint 3.6.9 Block 1 ADR for the full reasoning on each.
"""

import sqlite3
from pathlib import Path
from uuid import UUID


class NotificationStore:
    """Durable backing for `notifications.py`'s three process-memory dicts
    (`_registered_tokens`, `_dispatched_event_ids`, `_reviewed_pushed_event_ids`).
    Constructed only when `config.memory_persistence_enabled()` is true (see
    `notifications._get_store()`) -- disabled mode never imports sqlite3 or
    touches disk, byte-for-byte the pre-Block-1 in-memory-only behavior.
    """

    def __init__(self, db_path: str | Path) -> None:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False: same concurrency model as MemoryStore --
        # this store is reused across FastAPI's worker-thread-pool requests,
        # already guarded by the caller's own state lock/single-writer
        # discipline (see notifications.py).
        self._conn: sqlite3.Connection = sqlite3.connect(
            str(path), check_same_thread=False
        )
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS push_tokens ("
            "  user_id TEXT NOT NULL,"
            "  token TEXT NOT NULL,"
            "  PRIMARY KEY (user_id, token)"
            ")"
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS dispatched_notifications ("
            "  user_id TEXT NOT NULL,"
            "  event_id TEXT NOT NULL,"
            "  PRIMARY KEY (user_id, event_id)"
            ")"
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS reviewed_pushed_notifications ("
            "  user_id TEXT NOT NULL,"
            "  event_id TEXT NOT NULL,"
            "  PRIMARY KEY (user_id, event_id)"
            ")"
        )
        self._conn.commit()

    def load_tokens(self) -> dict[str, set[str]]:
        rows = self._conn.execute("SELECT user_id, token FROM push_tokens").fetchall()
        result: dict[str, set[str]] = {}
        for row in rows:
            result.setdefault(row["user_id"], set()).add(row["token"])
        return result

    def save_token(self, user_id: str, token: str) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO push_tokens (user_id, token) VALUES (?, ?)",
            (user_id, token),
        )
        self._conn.commit()

    def load_dispatched(self) -> dict[str, set[UUID]]:
        rows = self._conn.execute(
            "SELECT user_id, event_id FROM dispatched_notifications"
        ).fetchall()
        result: dict[str, set[UUID]] = {}
        for row in rows:
            result.setdefault(row["user_id"], set()).add(UUID(row["event_id"]))
        return result

    def save_dispatched(self, user_id: str, event_ids: list[UUID]) -> None:
        if not event_ids:
            return
        self._conn.executemany(
            "INSERT OR IGNORE INTO dispatched_notifications (user_id, event_id) "
            "VALUES (?, ?)",
            [(user_id, str(event_id)) for event_id in event_ids],
        )
        self._conn.commit()

    def load_reviewed(self) -> dict[str, set[UUID]]:
        rows = self._conn.execute(
            "SELECT user_id, event_id FROM reviewed_pushed_notifications"
        ).fetchall()
        result: dict[str, set[UUID]] = {}
        for row in rows:
            result.setdefault(row["user_id"], set()).add(UUID(row["event_id"]))
        return result

    def save_reviewed(self, user_id: str, event_ids: list[UUID]) -> None:
        if not event_ids:
            return
        self._conn.executemany(
            "INSERT OR IGNORE INTO reviewed_pushed_notifications "
            "(user_id, event_id) VALUES (?, ?)",
            [(user_id, str(event_id)) for event_id in event_ids],
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
