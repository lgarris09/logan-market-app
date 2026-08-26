"""V2.3A -- Identity & Account Foundation: durable account / external-
identity mapping.

Two small tables, deliberately minimal for this block (see docs/DECISIONS.md's
ADR-069):

`accounts` -- one row per STRATUS internal identity (`stratus_user_id`),
whether anonymous or authenticated. This is the anchor row future V2.3B
learning-state tables can key off of, and the row `purge_account()`
(account_lifecycle.py) removes last.

`external_identities` -- the `(provider, external_subject) -> stratus_user_id`
mapping. Many external identities may eventually map to one `stratus_user_id`
(a user could later also link Google after Apple), but the reverse is never
true -- one external identity always maps to exactly one canonical STRATUS
identity (the primary key is `(provider, external_subject)`, not
`stratus_user_id`).

Mirrors `notification_store.py`/`lifecycle_store.py`'s established pattern
exactly: a separate SQLite file, gated behind the same STRATUS_PERSIST_MEMORY
flag, load-on-first-use, write-through on mutation. Objective/global
opportunity data (LifecycleStore, RevisionStore) is NEVER touched by this
module -- accounts are personal identity state, kept in their own store, per
the explicit "objective intelligence must remain global" boundary (see
ADR-069's privacy/data-ownership section).
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple, Optional


class Account(NamedTuple):
    stratus_user_id: str
    created_at: str
    is_anonymous: bool


class AccountStore:
    """Durable backing for the account/external-identity mapping.
    Constructed only when `config.memory_persistence_enabled()` is true --
    disabled mode (local dev default) keeps this mapping process-memory-only,
    same discipline as every other Sprint 3.6.9+ store.
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
            "CREATE TABLE IF NOT EXISTS accounts ("
            "  stratus_user_id TEXT PRIMARY KEY,"
            "  created_at TEXT NOT NULL,"
            "  is_anonymous INTEGER NOT NULL"
            ")"
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS external_identities ("
            "  provider TEXT NOT NULL,"
            "  external_subject TEXT NOT NULL,"
            "  stratus_user_id TEXT NOT NULL,"
            "  linked_at TEXT NOT NULL,"
            "  PRIMARY KEY (provider, external_subject)"
            ")"
        )
        self._conn.commit()

    def load_all_identities(self) -> dict[tuple[str, str], str]:
        rows = self._conn.execute(
            "SELECT provider, external_subject, stratus_user_id FROM external_identities"
        ).fetchall()
        return {
            (row["provider"], row["external_subject"]): row["stratus_user_id"]
            for row in rows
        }

    def load_all_accounts(self) -> dict[str, Account]:
        rows = self._conn.execute(
            "SELECT stratus_user_id, created_at, is_anonymous FROM accounts"
        ).fetchall()
        return {
            row["stratus_user_id"]: Account(
                stratus_user_id=row["stratus_user_id"],
                created_at=row["created_at"],
                is_anonymous=bool(row["is_anonymous"]),
            )
            for row in rows
        }

    def create_account(self, stratus_user_id: str, *, is_anonymous: bool) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO accounts (stratus_user_id, created_at, is_anonymous) "
            "VALUES (?, ?, ?)",
            (
                stratus_user_id,
                datetime.now(timezone.utc).isoformat(),
                int(is_anonymous),
            ),
        )
        self._conn.commit()

    def mark_authenticated(self, stratus_user_id: str) -> None:
        self._conn.execute(
            "UPDATE accounts SET is_anonymous = 0 WHERE stratus_user_id = ?",
            (stratus_user_id,),
        )
        self._conn.commit()

    def link_external_identity(
        self, provider: str, external_subject: str, stratus_user_id: str
    ) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO external_identities "
            "(provider, external_subject, stratus_user_id, linked_at) "
            "VALUES (?, ?, ?, ?)",
            (
                provider,
                external_subject,
                stratus_user_id,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self._conn.commit()

    def lookup_stratus_user_id(
        self, provider: str, external_subject: str
    ) -> Optional[str]:
        row = self._conn.execute(
            "SELECT stratus_user_id FROM external_identities "
            "WHERE provider = ? AND external_subject = ?",
            (provider, external_subject),
        ).fetchone()
        return row["stratus_user_id"] if row is not None else None

    def delete_account(self, stratus_user_id: str) -> None:
        self._conn.execute(
            "DELETE FROM accounts WHERE stratus_user_id = ?", (stratus_user_id,)
        )
        self._conn.execute(
            "DELETE FROM external_identities WHERE stratus_user_id = ?",
            (stratus_user_id,),
        )
        self._conn.commit()

    def clear(self) -> None:
        self._conn.execute("DELETE FROM accounts")
        self._conn.execute("DELETE FROM external_identities")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
