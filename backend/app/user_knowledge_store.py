"""Stock Opportunity Logic V2.1 (User Sync Gap) -- durable per-user
knowledge-pointer state.

One compact row per `(user_id, entity_id)`, updated in place (UPSERT) -- the
explicit "do not create one user row per snapshot interaction; update
pointers instead" instruction. Mirrors `lifecycle_store.py`/
`notification_store.py`'s established pattern exactly: a separate SQLite
file, gated behind the same STRATUS_PERSIST_MEMORY flag, load-on-first-use,
write-through on mutation.
"""

import sqlite3
from pathlib import Path

from logan_core.opportunity_lifecycle import UserOpportunityKnowledge


class UserKnowledgeStore:
    """Durable backing for `UserOpportunityKnowledge` -- constructed only
    when `config.memory_persistence_enabled()` is true.
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
            "CREATE TABLE IF NOT EXISTS user_opportunity_knowledge ("
            "  user_id TEXT NOT NULL,"
            "  entity_id TEXT NOT NULL,"
            "  last_seen_revision INTEGER,"
            "  last_notified_revision INTEGER,"
            "  last_opened_revision INTEGER,"
            "  updated_at TEXT NOT NULL,"
            "  PRIMARY KEY (user_id, entity_id)"
            ")"
        )
        self._conn.commit()

    def load_all(self) -> list[UserOpportunityKnowledge]:
        rows = self._conn.execute(
            "SELECT user_id, entity_id, last_seen_revision, "
            "last_notified_revision, last_opened_revision, updated_at "
            "FROM user_opportunity_knowledge"
        ).fetchall()
        return [
            UserOpportunityKnowledge(
                user_id=row["user_id"],
                entity_id=row["entity_id"],
                last_seen_revision=row["last_seen_revision"],
                last_notified_revision=row["last_notified_revision"],
                last_opened_revision=row["last_opened_revision"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def save(self, knowledge: UserOpportunityKnowledge) -> None:
        self._conn.execute(
            "INSERT INTO user_opportunity_knowledge "
            "(user_id, entity_id, last_seen_revision, last_notified_revision, "
            "last_opened_revision, updated_at) VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, entity_id) DO UPDATE SET "
            "last_seen_revision=excluded.last_seen_revision, "
            "last_notified_revision=excluded.last_notified_revision, "
            "last_opened_revision=excluded.last_opened_revision, "
            "updated_at=excluded.updated_at",
            (
                knowledge.user_id,
                knowledge.entity_id,
                knowledge.last_seen_revision,
                knowledge.last_notified_revision,
                knowledge.last_opened_revision,
                knowledge.updated_at.isoformat(),
            ),
        )
        self._conn.commit()

    def clear(self) -> None:
        self._conn.execute("DELETE FROM user_opportunity_knowledge")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
