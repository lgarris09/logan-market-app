"""Universe Manager V1a Operational + Supply Telemetry -- durable,
day-bucketed observation of the real live feed pipeline, so the Master
Plan's (STRATUS_Master_Implementation_Plan_2026-08-30_REV1.md) 14-
consecutive-calendar-day expansion-gate proof can eventually be evaluated
against real evidence instead of only synthetic test fixtures.

Mirrors this codebase's established store pattern exactly (UniverseMembershipStore,
UniverseSchedulerStateStore, TelemetryStore): a separate SQLite file, gated
behind config.memory_persistence_enabled(), load-on-first-use. Unlike those,
this store is neither pure append-only history nor pure current-state
upsert -- it's an *accumulating* daily row: multiple pipeline runs within
one calendar day (UTC) merge into that day's single row. Two different
merge strategies are used deliberately:

  - most counters SUM across the day's observations (entity/sector/driver/
    signal-family impression counts, diversity/exploration/freshness
    counts) -- honest for "how many times did X happen today," but see the
    KNOWN LIMITATION note below.
  - `peak_pre_diversity_thesis_count` MAXES across the day's observations
    -- required for Master Plan Section 16A's Top-Five Competition Ratio,
    which is only meaningful as a per-observation snapshot compared
    against a threshold (a sum across N polls would multiply the ratio by
    N for no real reason).

KNOWN LIMITATION, deliberately not fixed in this pass (see this session's
Master Plan reconciliation report): every SUM-based counter conflates real
opportunity supply with polling frequency. A single calendar day polled
once produces a correct count; the same day polled 50 times (a real
mobile client's 60-second foreground poll, open for hours) sums the same
largely-static state 50 times over. This is a genuine telemetry-model gap
requiring a design decision (e.g. switch to "peak observed" or "last
observed" semantics, or a real deduplicated event log) before these
specific counts can be trusted at realistic polling cadence -- flagged for
review, not silently redesigned here.

Honest scope note, carried forward: this table starts recording at
whatever moment `memory_persistence_enabled()` is first true AND a real
feed request happens after this code ships -- there is no backfill, and
none was fabricated. A day with no matching row simply never had
persistence-enabled traffic; callers must treat that identically to "zero
observed," never a fault, and must never treat a partial history as
satisfying the Master Plan's own 14-*consecutive*-calendar-day requirement
without checking for gaps explicitly (see universe_telemetry.py's own
coverage-window logic for that check).
"""

import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class DailyUniverseTelemetry(BaseModel):
    """One durable, accumulated day's real observations. See this module's
    own docstring for which fields SUM vs MAX across the day's
    observations."""

    schema_version: str = "1.0"
    date: str  # ISO calendar date, UTC, e.g. "2026-09-02"
    observation_count: int = 0
    qualified_opportunity_count: int = 0
    distinct_thesis_keys: list[str] = Field(default_factory=list)
    entity_impression_counts: dict[str, int] = Field(default_factory=dict)
    sector_impression_counts: dict[str, int] = Field(default_factory=dict)
    signal_family_impression_counts: dict[str, int] = Field(default_factory=dict)
    # Master Plan Section 3/16A: market_driver_tag concentration --
    # EARNINGS_RESULT / EARNINGS_GUIDANCE / PRICE_DISLOCATION / etc.
    driver_impression_counts: dict[str, int] = Field(default_factory=dict)
    diversity_selected_count: int = 0
    diversity_suppressed_count: int = 0
    # Master Plan Section 3: "diversity suppression rate and reason" --
    # keyed by thesis/diversity.py's own SuppressionReason values
    # (ENTITY_CAP/SECTOR_CAP/SIGNAL_FAMILY_CAP/DRIVER_CAP).
    suppression_reason_counts: dict[str, int] = Field(default_factory=dict)
    exploration_eligible_count: int = 0
    exploration_placed_count: int = 0
    # Master Plan Section 3: "Formalize: FRESH / RECENTLY_OBSERVED /
    # STALE_WITHIN_GRACE / UNAVAILABLE" -- keyed by freshness.py's own
    # FreshnessState values, plus "NO_CONTRACT" for an item whose
    # signal_type has no registered freshness contract at all (the honest
    # None case, never silently folded into UNAVAILABLE).
    freshness_state_counts: dict[str, int] = Field(default_factory=dict)
    # Master Plan Section 16A: Top-Five Competition Ratio's numerator is
    # "eligible distinct theses before diversity constraints" -- this is
    # the count of distinct (entity, driver) thesis keys among a single
    # observation's thesis_candidates, i.e. the same population as
    # `distinct_thesis_keys` but per-observation, not unioned across the
    # day. MAX (not SUM) across the day's observations -- see class
    # docstring.
    peak_pre_diversity_thesis_count: int = 0
    # Master Plan Section 3: "top-five eligible candidate count" -- the
    # same pre-diversity eligible population as
    # peak_pre_diversity_thesis_count, but summed (not maxed) across the
    # day's observations, matching every other count field's convention.
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
    driver_impression_counts: dict[str, int] = Field(default_factory=dict)
    diversity_selected_count: int = 0
    diversity_suppressed_count: int = 0
    suppression_reason_counts: dict[str, int] = Field(default_factory=dict)
    exploration_eligible_count: int = 0
    exploration_placed_count: int = 0
    freshness_state_counts: dict[str, int] = Field(default_factory=dict)
    pre_diversity_thesis_count: int = 0  # this observation's own count -- both
    # summed into top_five_eligible_count and maxed into
    # peak_pre_diversity_thesis_count by record() below.


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
            "  driver_impression_counts TEXT NOT NULL DEFAULT '{}',"
            "  diversity_selected_count INTEGER NOT NULL DEFAULT 0,"
            "  diversity_suppressed_count INTEGER NOT NULL DEFAULT 0,"
            "  suppression_reason_counts TEXT NOT NULL DEFAULT '{}',"
            "  exploration_eligible_count INTEGER NOT NULL DEFAULT 0,"
            "  exploration_placed_count INTEGER NOT NULL DEFAULT 0,"
            "  freshness_state_counts TEXT NOT NULL DEFAULT '{}',"
            "  peak_pre_diversity_thesis_count INTEGER NOT NULL DEFAULT 0,"
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
            driver_impression_counts=json.loads(row["driver_impression_counts"]),
            diversity_selected_count=row["diversity_selected_count"],
            diversity_suppressed_count=row["diversity_suppressed_count"],
            suppression_reason_counts=json.loads(row["suppression_reason_counts"]),
            exploration_eligible_count=row["exploration_eligible_count"],
            exploration_placed_count=row["exploration_placed_count"],
            freshness_state_counts=json.loads(row["freshness_state_counts"]),
            peak_pre_diversity_thesis_count=row["peak_pre_diversity_thesis_count"],
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
        accumulated row. Most fields sum; `peak_pre_diversity_thesis_count`
        maxes -- see this module's own docstring for why."""
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
                driver_impression_counts=dict(delta.driver_impression_counts),
                diversity_selected_count=delta.diversity_selected_count,
                diversity_suppressed_count=delta.diversity_suppressed_count,
                suppression_reason_counts=dict(delta.suppression_reason_counts),
                exploration_eligible_count=delta.exploration_eligible_count,
                exploration_placed_count=delta.exploration_placed_count,
                freshness_state_counts=dict(delta.freshness_state_counts),
                peak_pre_diversity_thesis_count=delta.pre_diversity_thesis_count,
                top_five_eligible_count=delta.pre_diversity_thesis_count,
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
                driver_impression_counts=_merge_counts(
                    existing.driver_impression_counts, delta.driver_impression_counts
                ),
                diversity_selected_count=(
                    existing.diversity_selected_count + delta.diversity_selected_count
                ),
                diversity_suppressed_count=(
                    existing.diversity_suppressed_count
                    + delta.diversity_suppressed_count
                ),
                suppression_reason_counts=_merge_counts(
                    existing.suppression_reason_counts,
                    delta.suppression_reason_counts,
                ),
                exploration_eligible_count=(
                    existing.exploration_eligible_count
                    + delta.exploration_eligible_count
                ),
                exploration_placed_count=(
                    existing.exploration_placed_count + delta.exploration_placed_count
                ),
                freshness_state_counts=_merge_counts(
                    existing.freshness_state_counts, delta.freshness_state_counts
                ),
                peak_pre_diversity_thesis_count=max(
                    existing.peak_pre_diversity_thesis_count,
                    delta.pre_diversity_thesis_count,
                ),
                top_five_eligible_count=(
                    existing.top_five_eligible_count + delta.pre_diversity_thesis_count
                ),
            )

        self._conn.execute(
            "INSERT INTO universe_daily_telemetry ("
            "  date, observation_count, qualified_opportunity_count,"
            "  distinct_thesis_keys, entity_impression_counts,"
            "  sector_impression_counts, signal_family_impression_counts,"
            "  driver_impression_counts,"
            "  diversity_selected_count, diversity_suppressed_count,"
            "  suppression_reason_counts,"
            "  exploration_eligible_count, exploration_placed_count,"
            "  freshness_state_counts,"
            "  peak_pre_diversity_thesis_count, top_five_eligible_count"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(date) DO UPDATE SET "
            "  observation_count = excluded.observation_count,"
            "  qualified_opportunity_count = excluded.qualified_opportunity_count,"
            "  distinct_thesis_keys = excluded.distinct_thesis_keys,"
            "  entity_impression_counts = excluded.entity_impression_counts,"
            "  sector_impression_counts = excluded.sector_impression_counts,"
            "  signal_family_impression_counts = excluded.signal_family_impression_counts,"
            "  driver_impression_counts = excluded.driver_impression_counts,"
            "  diversity_selected_count = excluded.diversity_selected_count,"
            "  diversity_suppressed_count = excluded.diversity_suppressed_count,"
            "  suppression_reason_counts = excluded.suppression_reason_counts,"
            "  exploration_eligible_count = excluded.exploration_eligible_count,"
            "  exploration_placed_count = excluded.exploration_placed_count,"
            "  freshness_state_counts = excluded.freshness_state_counts,"
            "  peak_pre_diversity_thesis_count = excluded.peak_pre_diversity_thesis_count,"
            "  top_five_eligible_count = excluded.top_five_eligible_count",
            (
                merged.date,
                merged.observation_count,
                merged.qualified_opportunity_count,
                json.dumps(merged.distinct_thesis_keys),
                json.dumps(merged.entity_impression_counts),
                json.dumps(merged.sector_impression_counts),
                json.dumps(merged.signal_family_impression_counts),
                json.dumps(merged.driver_impression_counts),
                merged.diversity_selected_count,
                merged.diversity_suppressed_count,
                json.dumps(merged.suppression_reason_counts),
                merged.exploration_eligible_count,
                merged.exploration_placed_count,
                json.dumps(merged.freshness_state_counts),
                merged.peak_pre_diversity_thesis_count,
                merged.top_five_eligible_count,
            ),
        )
        self._conn.commit()

    def clear(self) -> None:
        self._conn.execute("DELETE FROM universe_daily_telemetry")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
