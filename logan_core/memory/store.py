import json
import sqlite3
from pathlib import Path
from typing import Optional
from uuid import UUID

from logan_core.contracts import Domain, MemoryRecord

# Sprint 3.6.7 Block 3: schema version for the optional SQLite-backed store
# below, tracked in its own `schema_meta` table -- not the same thing as
# MemoryRecord.schema_version (that's the *contract's* version; this is the
# *table layout's* version). Bump this and add a version-gated migration step
# in `_migrate()` whenever the table layout changes; do not silently ALTER
# TABLE without a bump, and do not bump without a migration step that handles
# every prior version.
MEMORY_STORE_SCHEMA_VERSION = 1

# Local single-user scale (ADR-006: SQLite + local dev for Phase 1) -- a
# generous cap, not a tuned production limit. Only feedback_record/
# exposure_record rows are ever pruned (see _compact); user_statement,
# preference_signal, and correction_record rows -- explicit, high-value, or
# already-reviewed -- are never pruned by this cap.
MAX_PRUNABLE_RECORDS_PER_USER = 2000
_PRUNABLE_RECORD_TYPES = ("feedback_record", "exposure_record")


class MemoryPermissionError(PermissionError):
    pass


class MemoryStore:
    """Layer 5 (Logan Memory only — Operational History is owned by the Orchestrator,
    see orchestrator/history.py per ADR-016). Only the Learning System may write here
    (enforced at the call site by requiring a `LearningSystem` writer token).

    Sprint 3.6.7 Block 3: optionally backed by a local SQLite file (`db_path`)
    so behavioral/interaction history survives a process restart -- see
    docs/DECISIONS.md's Sprint 3.6.7 Block 3 ADR for the full persistence
    decision record. `db_path=None` (the default, and every pre-Block-3
    caller/test) keeps this a pure in-memory dict, byte-for-byte unchanged
    from before. Reads are always served from the in-memory dict (`_records`)
    -- SQLite is a durable write-behind/reload mechanism, not a second source
    of truth queried independently, so `query()`/`all()` are completely
    unmodified either way.
    """

    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        self._records: dict[UUID, MemoryRecord] = {}
        self._conn: Optional[sqlite3.Connection] = None
        if db_path is not None:
            path = Path(db_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            # check_same_thread=False: this store is reused across FastAPI's
            # worker-thread-pool requests exactly like the rest of the
            # process-lifetime pipeline state in backend/app/logan_feed.py,
            # already guarded there by one shared `_state_lock` around every
            # pipeline-run/write call -- the same concurrency model, not a
            # new one.
            self._conn = sqlite3.connect(str(path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._init_schema()
            self._load_all()

    def _init_schema(self) -> None:
        assert self._conn is not None
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_meta ("
            "  key TEXT PRIMARY KEY,"
            "  value TEXT NOT NULL"
            ")"
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS memory_records ("
            "  record_id TEXT PRIMARY KEY,"
            "  user_id TEXT NOT NULL,"
            "  record_type TEXT NOT NULL,"
            "  domain TEXT,"
            "  entities TEXT NOT NULL,"
            "  created_at TEXT NOT NULL,"
            "  payload TEXT NOT NULL"
            ")"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_records_user ON memory_records(user_id)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_records_created_at "
            "ON memory_records(created_at)"
        )
        self._conn.commit()
        self._migrate()

    def _migrate(self) -> None:
        """Version-gated migration point. No-op today (schema is already at
        MEMORY_STORE_SCHEMA_VERSION==1 the first time this table is created);
        exists so a future schema change has a real, tested place to add a
        version-by-version upgrade path instead of ad hoc ALTER TABLE calls
        at call sites. A fresh database is stamped straight to the current
        version -- there is nothing to migrate *from* for a database that
        never existed at an older version.
        """
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT value FROM schema_meta WHERE key = 'version'"
        ).fetchone()
        current_version = int(row["value"]) if row is not None else 0

        if current_version == 0:
            # Fresh database (or one created before versioning existed) --
            # stamp it at the current version. No column/table transform is
            # needed to reach v1 from "nothing," by definition.
            current_version = MEMORY_STORE_SCHEMA_VERSION

        # Future migrations: `if current_version < 2: ...; current_version = 2`

        self._conn.execute(
            "INSERT INTO schema_meta (key, value) VALUES ('version', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (str(current_version),),
        )
        self._conn.commit()

    def _load_all(self) -> None:
        assert self._conn is not None
        for row in self._conn.execute("SELECT payload FROM memory_records"):
            record = MemoryRecord.model_validate_json(row["payload"])
            self._records[record.record_id] = record

    def write(self, record: MemoryRecord, *, writer: str) -> None:
        if writer != "learning_system":
            raise MemoryPermissionError(
                "Only the Learning System may write to Memory (see ADR-019)."
            )
        self._records[record.record_id] = record
        if self._conn is not None:
            self._conn.execute(
                "INSERT INTO memory_records "
                "(record_id, user_id, record_type, domain, entities, created_at, payload) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(record_id) DO UPDATE SET "
                "  user_id = excluded.user_id, record_type = excluded.record_type, "
                "  domain = excluded.domain, entities = excluded.entities, "
                "  created_at = excluded.created_at, payload = excluded.payload",
                (
                    str(record.record_id),
                    record.user_id,
                    record.record_type,
                    record.domain,
                    json.dumps(record.entities),
                    record.created_at.isoformat(),
                    record.model_dump_json(),
                ),
            )
            self._conn.commit()
            self._compact(record.user_id)

    def _compact(self, user_id: str) -> None:
        """Bounded-history compaction: once a user's *prunable* record count
        (feedback_record/exposure_record only -- see module docstring)
        exceeds MAX_PRUNABLE_RECORDS_PER_USER, delete the oldest excess so
        this store cannot grow unbounded from routine polling/interaction
        traffic. explicit/high-value record types are never touched here.
        """
        if self._conn is None:
            return
        placeholders = ",".join("?" for _ in _PRUNABLE_RECORD_TYPES)
        row = self._conn.execute(
            f"SELECT COUNT(*) AS n FROM memory_records "
            f"WHERE user_id = ? AND record_type IN ({placeholders})",
            (user_id, *_PRUNABLE_RECORD_TYPES),
        ).fetchone()
        count = row["n"] if row is not None else 0
        excess = count - MAX_PRUNABLE_RECORDS_PER_USER
        if excess <= 0:
            return

        to_delete = self._conn.execute(
            f"SELECT record_id FROM memory_records "
            f"WHERE user_id = ? AND record_type IN ({placeholders}) "
            f"ORDER BY created_at ASC LIMIT ?",
            (user_id, *_PRUNABLE_RECORD_TYPES, excess),
        ).fetchall()
        ids_to_delete = [r["record_id"] for r in to_delete]
        if not ids_to_delete:
            return

        delete_placeholders = ",".join("?" for _ in ids_to_delete)
        self._conn.execute(
            f"DELETE FROM memory_records WHERE record_id IN ({delete_placeholders})",
            ids_to_delete,
        )
        self._conn.commit()
        for record_id in ids_to_delete:
            self._records.pop(UUID(record_id), None)

    def query(
        self,
        user_id: str,
        domain: Domain | None = None,
        entities: list[str] | None = None,
    ) -> list[MemoryRecord]:
        """`user_id` is required, not optional (Sprint 3.6.8 Block 2, ADR-057)
        -- there is no "all users" mode. A record's isolation depends on
        every reader filtering by user_id; making it required turns a
        forgotten filter into a loud signature error at every call site
        instead of a silent cross-user leak (the exact bug this decision
        closes -- see orchestrator/pipeline.py's pre-Block-2 unfiltered
        `query(entities=...)` call, which fed one user's MemoryRecords into
        every other user's UserModel rebuild).
        """
        results = [r for r in self._records.values() if r.user_id == user_id]
        if domain is not None:
            results = [r for r in results if r.domain == domain]
        if entities is not None:
            entity_set = set(entities)
            results = [r for r in results if entity_set.intersection(r.entities)]
        return sorted(results, key=lambda r: r.created_at)

    def all(self, user_id: str) -> list[MemoryRecord]:
        """`user_id` is required -- see `query()`'s own docstring."""
        return [r for r in self._records.values() if r.user_id == user_id]

    def delete_user(self, user_id: str) -> int:
        """V2.3A (Identity & Account Foundation) -- the Memory-layer half of
        `purge_user_data()` (see backend/app/account_lifecycle.py). Removes
        every record for `user_id`, in-memory and (when persistence is
        enabled) durably. Returns the number of records removed. Unlike
        `_compact()`, this is unconditional -- every record_type is
        removed, including explicit/high-value ones `_compact()` would
        never prune, since account deletion means genuinely all of this
        user's data, not just bounded history.
        """
        to_delete = [
            record_id
            for record_id, record in self._records.items()
            if record.user_id == user_id
        ]
        for record_id in to_delete:
            del self._records[record_id]
        if self._conn is not None and to_delete:
            self._conn.execute(
                "DELETE FROM memory_records WHERE user_id = ?", (user_id,)
            )
            self._conn.commit()
        return len(to_delete)

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
