"""STRATUS 3.6.12 -- Notification Candidate + Decision Ledger V1: durable
storage.

Mirrors revision_store.py/lifecycle_store.py's established pattern exactly:
a separate SQLite file, gated behind the same STRATUS_PERSIST_MEMORY flag
(config.memory_persistence_enabled()), load-on-first-use, write-through on
mutation. Typed, queryable core columns for the fields the developer report
(notification_ledger_report.py) actually aggregates over; the full
Pydantic object (candidate or decision, including every nested snapshot and
the shadow evaluation) is additionally stored as one JSON `payload` column
per row, so nothing is lossy -- the same "typed core columns, JSON for the
rest" discipline this codebase already uses (see e.g. LifecycleStore's own
`trigger_codes` column).

Idempotency (bounded, additive, never a duplicate from a retry):

- `notification_candidates`: PRIMARY KEY is `candidate_id`, which the
  caller derives deterministically from (user_id, event_id, thesis_revision)
  -- see `candidate_id_for()` below. INSERT OR REPLACE: re-polling the same
  still-current revision replaces the row with (typically identical, at
  most slightly refreshed) data rather than ever creating a duplicate row.
  This is a *current-state* table, not an append-only history -- one row
  per (user, event, revision) ever observed, most recently-seen snapshot
  wins.
- `notification_decisions`: a genuine append-only history of *decision
  transitions* -- a new row is written only when the (outcome, reason) for
  a given (user_id, event_id, thesis_revision) actually differs from the
  most recently recorded decision for that same key (e.g.
  cooldown_suppressed at T1, then new_material_revision/SEND at T2 once the
  cooldown lifts). Re-evaluating an unchanged decision on a retried/
  duplicate poll is a genuine no-op -- see `save_decision()`'s own
  docstring.

Bounded retention (documented, not implemented tonight -- see the
Notification Ledger ADR in docs/DECISIONS.md): this table is expected to
grow at roughly one row per (user, lifecycle-tracked entity, meaningful
poll transition), which for a single-operator beta over the current 30-name
monitored cohort is small. A future block should add either a row-count cap
per user or a time-window prune (e.g. keep 90 days) before this ledger is
exposed to more than a handful of users -- flagged here rather than
silently deferred.
"""

import sqlite3
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from logan_core.contracts import LedgerDecision, NotificationCandidate  # noqa: E402

# ADR-081 -- the bounded dispatch-state model. Each value is exactly what
# the push provider's HTTP response established:
#   dispatch_attempted  the request was sent and answered 2xx, but the
#                       response carried no per-message ticket to read
#   dispatch_accepted   at least one ticket came back "ok"
#   dispatch_rejected   every ticket came back "error"
#   dispatch_failed     the request errored or was answered non-2xx
# Delivery to a device is never claimed: no delivery receipt is read, so
# delivery_state is always "unknown".
DISPATCH_STATES = frozenset(
    {
        "dispatch_attempted",
        "dispatch_accepted",
        "dispatch_rejected",
        "dispatch_failed",
    }
)
DELIVERY_STATE_UNKNOWN = "unknown"

# Fixed namespace UUID (arbitrary, but must never change once any real data
# exists under it) -- deterministic candidate_id derivation, never a random
# uuid4, so re-polling the same (user, event, revision) is provably
# idempotent rather than merely "usually the same by convention."
_CANDIDATE_ID_NAMESPACE = uuid.UUID("6f9c9c9a-2b1d-4b0a-8b8b-3b6b6b6b6b6b")


def candidate_id_for(
    user_id: str, event_id: uuid.UUID, thesis_revision: object
) -> uuid.UUID:
    """Deterministic candidate_id from (user_id, event_id, thesis_revision)
    -- the same triple always produces the same id, which is what makes
    `INSERT OR REPLACE` on this key a true idempotent upsert rather than an
    accidental one. `thesis_revision` is `object` (not `int | None`)
    deliberately: it's only ever used here as a stable string component of
    the hash input, never compared or arithmetic'd.
    """
    return uuid.uuid5(
        _CANDIDATE_ID_NAMESPACE, f"{user_id}:{event_id}:{thesis_revision}"
    )


class NotificationLedgerStore:
    """Durable backing for NotificationCandidate/LedgerDecision. Constructed
    only when config.memory_persistence_enabled() is true -- disabled mode
    never imports sqlite3 or touches disk (same posture as every other
    *_store.py in this file's sibling set).
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
            "CREATE TABLE IF NOT EXISTS notification_candidates ("
            "  candidate_id TEXT PRIMARY KEY,"
            "  user_id TEXT NOT NULL,"
            "  event_id TEXT NOT NULL,"
            "  entity_id TEXT NOT NULL,"
            "  ticker TEXT,"
            "  signal_family TEXT,"
            "  thesis_id TEXT NOT NULL,"
            "  thesis_revision INTEGER,"
            "  is_watched INTEGER NOT NULL,"
            "  watch_route TEXT NOT NULL,"
            "  communication_mode TEXT NOT NULL,"
            "  interruption TEXT NOT NULL,"
            "  created_at TEXT NOT NULL,"
            "  payload TEXT NOT NULL"
            ")"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_notification_candidates_user "
            "ON notification_candidates (user_id)"
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS notification_decisions ("
            "  decision_id TEXT PRIMARY KEY,"
            "  candidate_id TEXT NOT NULL,"
            "  user_id TEXT NOT NULL,"
            "  event_id TEXT NOT NULL,"
            "  thesis_revision INTEGER,"
            "  outcome TEXT NOT NULL,"
            "  reason TEXT NOT NULL,"
            "  decided_at TEXT NOT NULL,"
            "  payload TEXT NOT NULL"
            ")"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_notification_decisions_lookup "
            "ON notification_decisions (user_id, event_id, thesis_revision, decided_at)"
        )
        # ADR-081: what actually happened to a SEND. One row per dispatch
        # attempt for one (user, opportunity, revision). `state` is what the
        # push provider's own response established and nothing more;
        # `delivery_state` stays "unknown" because no delivery receipt is
        # read -- acceptance by the provider is not delivery to a device.
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS notification_dispatches ("
            "  dispatch_id TEXT PRIMARY KEY,"
            "  user_id TEXT NOT NULL,"
            "  event_id TEXT NOT NULL,"
            "  entity_id TEXT NOT NULL,"
            "  thesis_revision INTEGER,"
            "  state TEXT NOT NULL,"
            "  accepted_count INTEGER NOT NULL,"
            "  rejected_count INTEGER NOT NULL,"
            "  detail TEXT,"
            "  delivery_state TEXT NOT NULL,"
            "  attempted_at TEXT NOT NULL"
            ")"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_notification_dispatches_lookup "
            "ON notification_dispatches (user_id, event_id, attempted_at)"
        )
        self._conn.commit()
        self._last_purge_at: Optional[datetime] = None

    # --- dispatch outcomes ---------------------------------------------------

    def record_dispatch(
        self,
        *,
        user_id: str,
        event_id: uuid.UUID,
        entity_id: str,
        thesis_revision: Optional[int],
        state: str,
        accepted_count: int,
        rejected_count: int,
        detail: Optional[str],
        attempted_at: datetime,
    ) -> None:
        if state not in DISPATCH_STATES:
            raise ValueError(f"unknown dispatch state: {state}")
        self._conn.execute(
            "INSERT INTO notification_dispatches "
            "(dispatch_id, user_id, event_id, entity_id, thesis_revision, state, "
            "accepted_count, rejected_count, detail, delivery_state, attempted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                user_id,
                str(event_id),
                entity_id,
                thesis_revision,
                state,
                accepted_count,
                rejected_count,
                (detail or "")[:500] or None,
                DELIVERY_STATE_UNKNOWN,
                attempted_at.isoformat(),
            ),
        )
        self._conn.commit()

    def all_dispatches(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM notification_dispatches ORDER BY attempted_at ASC"
        ).fetchall()
        return [dict(row) for row in rows]

    # --- retention -----------------------------------------------------------

    def purge_older_than(self, cutoff: datetime) -> int:
        """Deletes every row older than `cutoff` from all three tables.
        Returns the number of rows removed."""
        removed = 0
        for statement in (
            "DELETE FROM notification_candidates WHERE created_at < ?",
            "DELETE FROM notification_decisions WHERE decided_at < ?",
            "DELETE FROM notification_dispatches WHERE attempted_at < ?",
        ):
            removed += self._conn.execute(statement, (cutoff.isoformat(),)).rowcount
        self._conn.commit()
        return removed

    def maybe_purge(self, now: datetime, retention_days: int) -> None:
        """Runs purge_older_than() at most once a day per process. A restart
        simply purges again at startup, which is cheap and idempotent."""
        if (
            self._last_purge_at is not None
            and (now - self._last_purge_at).total_seconds() < 86400
        ):
            return
        self._last_purge_at = now
        self.purge_older_than(now - timedelta(days=retention_days))

    def save_candidate(self, candidate: NotificationCandidate) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO notification_candidates "
            "(candidate_id, user_id, event_id, entity_id, ticker, signal_family, "
            "thesis_id, thesis_revision, is_watched, watch_route, "
            "communication_mode, interruption, created_at, payload) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(candidate.candidate_id),
                candidate.user_id,
                str(candidate.event_id),
                candidate.entity_id,
                candidate.ticker,
                candidate.signal_family,
                candidate.thesis_id,
                candidate.revision.thesis_revision,
                int(candidate.watch.is_watched),
                candidate.watch.watch_route,
                candidate.watch.communication_mode,
                candidate.prioritization.interruption,
                candidate.created_at.isoformat(),
                candidate.model_dump_json(),
            ),
        )
        self._conn.commit()

    def _latest_decision_outcome_reason(
        self, user_id: str, event_id: uuid.UUID, thesis_revision: Optional[int]
    ) -> Optional[tuple[str, str]]:
        row = self._conn.execute(
            "SELECT outcome, reason FROM notification_decisions "
            "WHERE user_id = ? AND event_id = ? AND thesis_revision IS ? "
            "ORDER BY decided_at DESC LIMIT 1",
            (user_id, str(event_id), thesis_revision),
        ).fetchone()
        return (row["outcome"], row["reason"]) if row is not None else None

    def save_decision(
        self, decision: LedgerDecision, thesis_revision: Optional[int]
    ) -> bool:
        """Appends a new decision row only when it represents a genuine
        transition -- (outcome, reason) differs from the most recently
        recorded decision for this exact (user_id, event_id,
        thesis_revision) key. Returns True when a new row was written,
        False when this was a no-op (an identical re-evaluation of an
        unchanged state, e.g. a retried request or a duplicate poll within
        the same revision) -- exactly the "no duplicate ledger entries from
        retries" requirement, without ever discarding a real transition.
        """
        latest = self._latest_decision_outcome_reason(
            decision.user_id, decision.event_id, thesis_revision
        )
        if latest is not None and latest == (decision.outcome, decision.reason):
            return False
        self._conn.execute(
            "INSERT INTO notification_decisions "
            "(decision_id, candidate_id, user_id, event_id, thesis_revision, "
            "outcome, reason, decided_at, payload) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(decision.decision_id),
                str(decision.candidate_id),
                decision.user_id,
                str(decision.event_id),
                thesis_revision,
                decision.outcome,
                decision.reason,
                decision.decided_at.isoformat(),
                decision.model_dump_json(),
            ),
        )
        self._conn.commit()
        return True

    def decisions_for_user(self, user_id: str) -> list[dict]:
        """Raw rows (not reconstructed Pydantic objects -- callers that need
        the full LedgerDecision should parse `payload` themselves) ordered
        oldest-first, for report aggregation. Kept as plain dicts rather
        than a new typed contract: this is a read path for
        notification_ledger_report.py's own aggregation, not a second
        source of truth for LedgerDecision's shape.
        """
        rows = self._conn.execute(
            "SELECT * FROM notification_decisions WHERE user_id = ? "
            "ORDER BY decided_at ASC",
            (user_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def candidates_for_user(self, user_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM notification_candidates WHERE user_id = ? "
            "ORDER BY created_at ASC",
            (user_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def all_decisions(self) -> list[dict]:
        """Every user's decisions -- used only by the aggregate developer
        report (notification_ledger_report.py), never by any per-user API
        response. Callers must not expose this cross-user."""
        rows = self._conn.execute(
            "SELECT * FROM notification_decisions ORDER BY decided_at ASC"
        ).fetchall()
        return [dict(row) for row in rows]

    def all_candidates(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM notification_candidates ORDER BY created_at ASC"
        ).fetchall()
        return [dict(row) for row in rows]

    def delete_user(self, user_id: str) -> None:
        self._conn.execute(
            "DELETE FROM notification_candidates WHERE user_id = ?", (user_id,)
        )
        self._conn.execute(
            "DELETE FROM notification_decisions WHERE user_id = ?", (user_id,)
        )
        self._conn.execute(
            "DELETE FROM notification_dispatches WHERE user_id = ?", (user_id,)
        )
        self._conn.commit()

    def clear(self) -> None:
        self._conn.execute("DELETE FROM notification_candidates")
        self._conn.execute("DELETE FROM notification_decisions")
        self._conn.execute("DELETE FROM notification_dispatches")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
