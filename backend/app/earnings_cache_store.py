"""V2.3A.1 field reliability work -- durable last-successful-earnings-
observation persistence.

The stale-grace mechanism `fetch_latest_earnings()` opted into (see
`logan_core/receptors/providers/fmp.py`'s `EARNINGS_STALE_GRACE_SECONDS`)
only protects a provider outage that happens *while the process keeps
running* -- its in-memory `FmpResponseCache` never survives a restart. A
hosted-production audit (2026-08-28/29) directly confirmed this gap live: a
deploy restarted the backend during an ongoing FMP quota outage, the shared
cache came up empty, and NVDA/AAPL's real, still-valid earnings had no
in-memory entry to fall back to until this process's own first successful
fetch -- which never happened, because the outage was still ongoing.

This store closes that gap: the *wall-clock* moment of the last genuinely
successful earnings fetch survives a restart, so grace eligibility is always
measured from the real age of the underlying data, not from when this
process happened to start. See `logan_feed.py`'s `_get_orchestrator()` for
the load-and-seed wiring (`seed_earnings_from_durable_observation`) and
`FmpEarningsProvider`'s `on_successful_fetch` for the write side.

Deliberately minimal, mirroring `lifecycle_store.py`'s own "do not persist
huge raw provider payload histories" discipline: one row per `entity_id`,
the already-normalized `EarningsReport` plus the wall-clock UTC timestamp of
that one successful observation -- nothing else. Never a failed response --
`FmpEarningsProvider._fetch_and_observe` is the only call site that writes
here, and it only ever fires after a genuine, fresh, successful HTTP round-
trip (never a TTL cache hit, never a raised FmpProviderError, never a
genuine "no earnings on file" `None` result -- see its own docstring).
"""

import sqlite3
from datetime import datetime
from pathlib import Path

from logan_core.receptors.providers import EarningsReport


class EarningsCacheStore:
    """Durable backing for `FmpEarningsProvider`'s last successful earnings
    observation, keyed by `entity_id`. Constructed only when
    `config.memory_persistence_enabled()` is true -- mirrors
    `lifecycle_store.py`'s `LifecycleStore` pattern exactly (separate SQLite
    file, load-on-first-use, write-through on mutation).
    """

    def __init__(self, db_path: str | Path) -> None:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection = sqlite3.connect(
            str(path), check_same_thread=False
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS earnings_observations ("
            "  entity_id TEXT PRIMARY KEY,"
            "  report_json TEXT NOT NULL,"
            "  observed_at TEXT NOT NULL"
            ")"
        )
        self._conn.commit()

    def load_all(self) -> dict[str, tuple[EarningsReport, datetime]]:
        """V2.3A.1 closeout edge-case fix: a single malformed row (a future
        schema change, manual edit, or disk corruption) must never take down
        the entire backend startup -- every other durable store's load_all()
        in this file family has this same latent exposure, but this is new
        code, so it gets the more defensive behavior here rather than
        inheriting the gap. A row that fails to parse is skipped and logged
        (entity_id and error only -- never raw payload content), and every
        other entity's valid recovery still proceeds normally.
        """
        rows = self._conn.execute(
            "SELECT entity_id, report_json, observed_at FROM earnings_observations"
        ).fetchall()
        result: dict[str, tuple[EarningsReport, datetime]] = {}
        for row in rows:
            try:
                result[row["entity_id"]] = (
                    EarningsReport.model_validate_json(row["report_json"]),
                    datetime.fromisoformat(row["observed_at"]),
                )
            except (ValueError, TypeError) as exc:
                print(
                    f"[earnings-cache] skipping unreadable durable row for "
                    f"{row['entity_id']}: {exc}"
                )
        return result

    def save(
        self, entity_id: str, report: EarningsReport, observed_at: datetime
    ) -> None:
        self._conn.execute(
            "INSERT INTO earnings_observations "
            "(entity_id, report_json, observed_at) VALUES (?, ?, ?) "
            "ON CONFLICT(entity_id) DO UPDATE SET "
            "report_json=excluded.report_json, "
            "observed_at=excluded.observed_at",
            (entity_id, report.model_dump_json(), observed_at.isoformat()),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
