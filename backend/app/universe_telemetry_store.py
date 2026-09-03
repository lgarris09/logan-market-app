"""Universe Manager V1a Operational + Supply Telemetry (V1a ITERATE block,
Phase 3) -- durable, day-bucketed observation of the real live feed
pipeline, so the Master Plan's 14-consecutive-calendar-day expansion-gate
proof can eventually be evaluated against real evidence instead of only
synthetic test fixtures.

Mirrors this codebase's established store pattern exactly (UniverseMembershipStore,
UniverseSchedulerStateStore, TelemetryStore): a separate SQLite file, gated
behind config.memory_persistence_enabled(), load-on-first-use. Unlike those,
this store is neither pure append-only history nor pure current-state
upsert -- it's an *accumulating* daily row: multiple pipeline runs within
one calendar day (UTC) merge into that day's single row (integer counters
sum, set/dict fields union), so "how many qualified opportunities occurred
today" is a real running total, not overwritten by the next request.

Honest scope note, carried forward from this session's own V1a deployment-
review findings (do not silently narrow this note away): this table
starts recording at whatever moment `memory_persistence_enabled()` is
first true AND a real feed request happens after this code ships -- there
is no backfill, and none was fabricated. A day with no matching row simply
never had persistence-enabled traffic; callers must treat that identically
to "zero observed," never a fault, and must never treat a partial history
as satisfying the Master Plan's own 14-*consecutive*-calendar-day
requirement without checking for gaps explicitly (see
universe_telemetry.py's own coverage-window logic for that check).
"""

import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class DailyUniverseTelemetry(BaseModel):
    """One durable, accumulated day's real observations. Every count here
    is additive-only within the day; every dict/list field is a union
    across every pipeline run recorded that day, never a replacement."""

    schema_version: str = "1.0"
    date: str  # ISO calendar date, UTC, e.g. "2026-09-02"
    observation_count: int = 0
    qualified_opportunity_count: int = 0
    distinct_thesis_keys: list[str] = Field(default_factory=list)
    entity_impression_counts: dict[str, int] = Field(default_factory=dict)
    sector_impression_counts: dict[str, int] = Field(default_factory=dict)
    signal_family_impression_counts: dict[str, int] = Field(default_factory=dict)
    diversity_selected_count: int = 0
    diversity_suppressed_count: int = 0
    exploration_eligible_count: int = 0
    exploration_placed_count: int = 0
    freshness_unavailable_count: int = 0
    freshness_total_count: int = 0
    top_five_eligible_count: int = 0


class DailyObservationDelta(BaseModel):
    """What one real pipeline run contributes to its calendar day's row --
    the input to `UniverseDailyTelemetryStore.record()`, built by
    universe_telemetry.py from one `_run_feed_pipeline()` call's own
    already-computed real values. Never itself persisted directly; always
    merged into the day's accumulated `DailyUniverseTelemetry` row."""

    qualified_opportunity_count: int = 0
    distinct_thesis_keys: list[str] = Field(default_factory=list)
    entity_impression_counts: dict[str, int] = Field(default_factory=dict)
    sector_impression_counts: dict[str, int] = Field(default_factory=dict)
    signal_family_impression_counts: dict[str, int] = Field(default_factory=dict)
    diversity_selected_count: int = 0
    diversity_suppressed_count: int = 0
    exploration_eligible_count: int = 0
    exploration_placed_count: int = 0
    freshness_unavailable_count: int = 0
    freshness_total_count: int = 0
    top_five_eligible_count: int = 0


def _merge_counts(existing: dict[str, int], delta: dict[str, int]) -> dict[str, int]:
    merged = dict(existing)
    for key, value in delta.items():
        merged[key] = merged.get(key, 0) + value
    return merged


class UniverseDailyTelemetryStore:
    """Durable backing for `DailyUniverseTelemetry` rows -- constructed only
    when config.memory_persistence_enabled() is true."""

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
            "CREATE TABLE IF NOT EXISTS universe_daily_telemetry ("
            "  date TEXT PRIMARY KEY,"
            "  observation_count INTEGER NOT NULL DEFAULT 0,"
            "  qualified_opportunity_count INTEGER NOT NULL DEFAULT 0,"
            "  distinct_thesis_keys TEXT NOT NULL DEFAULT '[]',"
            "  entity_impression_counts TEXT NOT NULL DEFAULT '{}',"
            "  sector_impression_counts TEXT NOT NULL DEFAULT '{}',"
            "  signal_family_impression_counts TEXT NOT NULL DEFAULT '{}',"
            "  diversity_selected_count INTEGER NOT NULL DEFAULT 0,"
            "  diversity_suppressed_count INTEGER NOT NULL DEFAULT 0,"
            "  exploration_eligible_count INTEGER NOT NULL DEFAULT 0,"
            "  exploration_placed_count INTEGER NOT NULL DEFAULT 0,"
            "  freshness_unavailable_count INTEGER NOT NULL DEFAULT 0,"
            "  freshness_total_count INTEGER NOT NULL DEFAULT 0,"
            "  top_five_eligible_count INTEGER NOT NULL DEFAULT 0"
            ")"
        )
        self._conn.commit()

    def _row_to_record(self, row: sqlite3.Row) -> DailyUniverseTelemetry:
        return DailyUniverseTelemetry(
            date=row["date"],
            observation_count=row["observation_count"],
            qualified_opportunity_count=row["qualified_opportunity_count"],
            distinct_thesis_keys=json.loads(row["distinct_thesis_keys"]),
            entity_impression_counts=json.loads(row["entity_impression_counts"]),
            sector_impression_counts=json.loads(row["sector_impression_counts"]),
            signal_family_impression_counts=json.loads(
                row["signal_family_impression_counts"]
            ),
            diversity_selected_count=row["diversity_selected_count"],
            diversity_suppressed_count=row["diversity_suppressed_count"],
            exploration_eligible_count=row["exploration_eligible_count"],
            exploration_placed_count=row["exploration_placed_count"],
            freshness_unavailable_count=row["freshness_unavailable_count"],
            freshness_total_count=row["freshness_total_count"],
            top_five_eligible_count=row["top_five_eligible_count"],
        )

    def get(self, day: date) -> Optional[DailyUniverseTelemetry]:
        row = self._conn.execute(
            "SELECT * FROM universe_daily_telemetry WHERE date = ?",
            (day.isoformat(),),
        ).fetchone()
        return self._row_to_record(row) if row is not None else None

    def range(self, start: date, end: date) -> list[DailyUniverseTelemetry]:
        """Inclusive [start, end] range, ordered by date -- callers must
        treat a missing date in the middle of this list as a real
        coverage gap, never assume every calendar day has a row."""
        rows = self._conn.execute(
            "SELECT * FROM universe_daily_telemetry WHERE date >= ? AND date <= ? "
            "ORDER BY date",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def record(self, day: date, delta: DailyObservationDelta) -> None:
        """Merges one pipeline run's real observations into `day`'s
        accumulated row -- integer counters sum, dict/list fields union.
        Never overwrites a day's existing accumulated state."""
        existing = self.get(day)
        if existing is None:
            merged = DailyUniverseTelemetry(
                date=day.isoformat(),
                observation_count=1,
                qualified_opportunity_count=delta.qualified_opportunity_count,
                distinct_thesis_keys=sorted(set(delta.distinct_thesis_keys)),
                entity_impression_counts=dict(delta.entity_impression_counts),
                sector_impression_counts=dict(delta.sector_impression_counts),
                signal_family_impression_counts=dict(
                    delta.signal_family_impression_counts
                ),
                diversity_selected_count=delta.diversity_selected_count,
                diversity_suppressed_count=delta.diversity_suppressed_count,
                exploration_eligible_count=delta.exploration_eligible_count,
                exploration_placed_count=delta.exploration_placed_count,
                freshness_unavailable_count=delta.freshness_unavailable_count,
                freshness_total_count=delta.freshness_total_count,
                top_five_eligible_count=delta.top_five_eligible_count,
            )
        else:
            merged = DailyUniverseTelemetry(
                date=day.isoformat(),
                observation_count=existing.observation_count + 1,
                qualified_opportunity_count=(
                    existing.qualified_opportunity_count
                    + delta.qualified_opportunity_count
                ),
                distinct_thesis_keys=sorted(
                    set(existing.distinct_thesis_keys) | set(delta.distinct_thesis_keys)
                ),
                entity_impression_counts=_merge_counts(
                    existing.entity_impression_counts, delta.entity_impression_counts
                ),
                sector_impression_counts=_merge_counts(
                    existing.sector_impression_counts, delta.sector_impression_counts
                ),
                signal_family_impression_counts=_merge_counts(
                    existing.signal_family_impression_counts,
                    delta.signal_family_impression_counts,
                ),
                diversity_selected_count=(
                    existing.diversity_selected_count + delta.diversity_selected_count
                ),
                diversity_suppressed_count=(
                    existing.diversity_suppressed_count
                    + delta.diversity_suppressed_count
                ),
                exploration_eligible_count=(
                    existing.exploration_eligible_count
                    + delta.exploration_eligible_count
                ),
                exploration_placed_count=(
                    existing.exploration_placed_count + delta.exploration_placed_count
                ),
                freshness_unavailable_count=(
                    existing.freshness_unavailable_count
                    + delta.freshness_unavailable_count
                ),
                freshness_total_count=(
                    existing.freshness_total_count + delta.freshness_total_count
                ),
                top_five_eligible_count=(
                    existing.top_five_eligible_count + delta.top_five_eligible_count
                ),
            )

        self._conn.execute(
            "INSERT INTO universe_daily_telemetry ("
            "  date, observation_count, qualified_opportunity_count,"
            "  distinct_thesis_keys, entity_impression_counts,"
            "  sector_impression_counts, signal_family_impression_counts,"
            "  diversity_selected_count, diversity_suppressed_count,"
            "  exploration_eligible_count, exploration_placed_count,"
            "  freshness_unavailable_count, freshness_total_count,"
            "  top_five_eligible_count"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(date) DO UPDATE SET "
            "  observation_count = excluded.observation_count,"
            "  qualified_opportunity_count = excluded.qualified_opportunity_count,"
            "  distinct_thesis_keys = excluded.distinct_thesis_keys,"
            "  entity_impression_counts = excluded.entity_impression_counts,"
            "  sector_impression_counts = excluded.sector_impression_counts,"
            "  signal_family_impression_counts = excluded.signal_family_impression_counts,"
            "  diversity_selected_count = excluded.diversity_selected_count,"
            "  diversity_suppressed_count = excluded.diversity_suppressed_count,"
            "  exploration_eligible_count = excluded.exploration_eligible_count,"
            "  exploration_placed_count = excluded.exploration_placed_count,"
            "  freshness_unavailable_count = excluded.freshness_unavailable_count,"
            "  freshness_total_count = excluded.freshness_total_count,"
            "  top_five_eligible_count = excluded.top_five_eligible_count",
            (
                merged.date,
                merged.observation_count,
                merged.qualified_opportunity_count,
                json.dumps(merged.distinct_thesis_keys),
                json.dumps(merged.entity_impression_counts),
                json.dumps(merged.sector_impression_counts),
                json.dumps(merged.signal_family_impression_counts),
                merged.diversity_selected_count,
                merged.diversity_suppressed_count,
                merged.exploration_eligible_count,
                merged.exploration_placed_count,
                merged.freshness_unavailable_count,
                merged.freshness_total_count,
                merged.top_five_eligible_count,
            ),
        )
        self._conn.commit()

    def clear(self) -> None:
        self._conn.execute("DELETE FROM universe_daily_telemetry")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
