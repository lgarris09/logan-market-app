"""Universe Manager V1a Operational + Supply Telemetry -- real-data
recording and reporting for the metrics
STRATUS_Master_Implementation_Plan_2026-08-30_REV1.md (the governing
Master Plan, located outside this repository and now available) requires
for the 14-consecutive-calendar-day expansion-gate proof.

Reconciliation note (Master Plan Reconciliation + V1a Telemetry Completion
block): the previous pass ("V1a ITERATE") ran without access to the
Master Plan text and therefore treated several metrics as unimplementable
without a definition -- signal_yield, top_five_competition_ratio,
deterministic_thesis_novelty_rate. The plan text is now available (Section
3, Section 4, Section 16A) and gives exact formulas for Top-Five
Competition Ratio and Thesis Novelty Rate, both now wired below. It does
NOT give an exact, checkable definition of "complete evidence/explanation
chain," and its Material Revision Rubric (Section 4) names seven auditable
change classes that do not correspond 1:1 to this codebase's existing
`OpportunityRevision.change_type` values -- both remain in
`BLOCKED_METRICS`, for different reasons (no definition at all, vs. a
definition that needs a confirmed mapping decision before it can be
computed without guessing). "Signal-family yield" is named in the plan's
measurement list but never given a formula anywhere (unlike Top-Five
Competition Ratio and Thesis Novelty Rate, which Section 16A defines
precisely) -- the raw distribution (signal_family_impression_counts) is
real and wired; a true yield (rate) needs an attempted/eligible-per-family
denominator this codebase does not track, so it stays blocked too.

Telemetry observes; it never decides. Every function in this module is
read-only with respect to the pipeline it observes --
`record_pipeline_observation()` is called after a feed response is
already fully computed, wrapped in try/except at its one call site
(logan_feed.py), so a telemetry failure can never affect a real request's
output. Nothing here touches qualification, ranking, polling cadence, or
Personal Relevance.
"""

import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .config import memory_persistence_enabled, universe_daily_telemetry_db_path
from .universe_telemetry_store import (
    DailyObservationDelta,
    DailyUniverseTelemetry,
    UniverseDailyTelemetryStore,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from logan_core.contracts import ExplorationPlacementResult  # noqa: E402
from logan_core.diagnostics import recent_faults  # noqa: E402
from logan_core.receptors.providers import fmp_budget_snapshot  # noqa: E402
from logan_core.thesis.diversity import DiversityResult, ThesisCandidate  # noqa: E402

# Master Plan Section 16A defines an exact formula for these two; neither
# is guessed. TOP_FIVE_POSITIONS is the plan's own literal "/ 5" --
# thesis/diversity.py's DEFAULT_TOP_N, not independently chosen here.
TOP_FIVE_POSITIONS = 5

# Master Plan Section 16A: Thesis Novelty Rate's "recent deterministic
# thesis metadata" has no explicit window size stated for this specific
# metric -- this session reuses the plan's own dominant window (the
# 14-consecutive-calendar-day proof window used everywhere else in the
# plan) as the most defensible default, NOT a number the plan states for
# this metric specifically. Flagged as an explicit assumption, not a
# silent invention of the underlying formula (which the plan does give
# exactly).
THESIS_NOVELTY_RECENCY_WINDOW_DAYS = 14

# Requested by name in the V1a work but with no exact, checkable
# definition anywhere in the Master Plan (confirmed against the full text)
# or this codebase -- not implemented, not approximated, not silently
# redefined.
BLOCKED_METRICS = (
    # No formula anywhere in the Master Plan (unlike Top-Five Competition
    # Ratio / Thesis Novelty Rate, which Section 16A defines exactly) --
    # only the raw distribution (signal_family_impression_counts) is real.
    "signal_family_yield_rate",
    # Master Plan Section 4: "≥95% complete evidence/explanation chains" --
    # no field anywhere in this codebase's FeedItem/DeliveredItem/
    # ConclusionConfidence contracts marks an item's evidence payload as
    # "complete," and the plan itself never enumerates what completeness
    # requires. Computing this would mean inventing the definition, not
    # observing an existing signal.
    "complete_evidence_payload_rate",
    # Master Plan Section 4's Material Revision Rubric names seven
    # auditable classes (STATE_CHANGE, EVIDENCE_STRENGTH_CHANGE,
    # TRAJECTORY_CHANGE, INVALIDATION_RISK_CHANGE, TIME_SENSITIVITY_CHANGE,
    # PERSONAL_RELEVANCE_CHANGE, FRESHNESS_DEGRADED_CHANGE) that do not
    # correspond 1:1 to OpportunityRevision.change_type's existing 15
    # values -- some mappings are obvious (personal_relevance_increased ->
    # PERSONAL_RELEVANCE_CHANGE), others are genuinely ambiguous
    # (confidence_increased -> EVIDENCE_STRENGTH_CHANGE or STATE_CHANGE?).
    # The raw meaningful-revision count is real (real_meaningful_revision_count());
    # the rubric-CLASS-based >=70% rate needs a confirmed mapping decision
    # before it can be computed without guessing a classification policy.
    "material_revision_rubric_classification_rate",
    # Master Plan Section 4 operational gates: time-sensitive scheduler
    # delay P95/P99, critical freshness P95/P99 ratio, a genuine historical
    # peak calls/minute, and coalescing success rate all require a
    # per-event latency/ratio distribution history this codebase has no
    # durable event log for. Building one is a materially new persistence
    # subsystem -- flagged for review per this block's own stop condition,
    # not built here.
    "time_sensitive_delay_p95_seconds",
    "time_sensitive_delay_p99_seconds",
    "critical_freshness_p95_ratio",
    "critical_freshness_p99_ratio",
    "peak_calls_per_minute_historical",
    "coalescing_success_rate",
)

_store: Optional[UniverseDailyTelemetryStore] = None


def _get_store() -> Optional[UniverseDailyTelemetryStore]:
    global _store
    if not memory_persistence_enabled():
        return None
    if _store is None:
        _store = UniverseDailyTelemetryStore(universe_daily_telemetry_db_path())
    return _store


def reset_universe_telemetry_state() -> None:
    """Test-only (and general-purpose "start over") hook, mirroring every
    other store's identical reset_*_state() shape."""
    global _store
    if _store is not None:
        _store.close()
    _store = None


def _thesis_key(candidate: ThesisCandidate) -> str:
    """A "distinct thesis" is the same (entity, driver) identity
    thesis/diversity.py's own DRIVER_CAP already treats as one thesis --
    reusing that module's established concept, not inventing a second one."""
    return (
        f"{candidate.metadata.primary_entity_id}|{candidate.metadata.market_driver_tag}"
    )


def build_observation_delta(
    *,
    thesis_candidates: list[ThesisCandidate],
    diversity_result: DiversityResult,
    exploration_eligible_pool: list[ThesisCandidate],
    exploration_result: ExplorationPlacementResult,
    freshness_states: list[Optional[str]],
) -> DailyObservationDelta:
    """Pure transformation from one real `_run_feed_pipeline()` call's
    already-computed values into one day's observation delta -- no I/O, no
    provider calls, nothing invented. `raw_qualified_observation_count` is
    `len(thesis_candidates)`: every thesis_candidates entry corresponds
    1:1 to a FeedItem this response actually delivered (an
    OBJECTIVELY_QUALIFIED opportunity, per contracts/universe.py's own
    four-state taxonomy), never a raw pre-qualification count. This is
    explicitly diagnostic-only (see universe_telemetry_store.py's own
    field docstring) -- V1a Proof-Instrumentation Closeout's polling-
    frequency fix means gate calculations must read
    `distinct_qualified_entity_count()` below instead, which is immune to
    how many times this function is called for the same real-world state.
    """
    entity_counts = Counter(c.metadata.primary_entity_id for c in thesis_candidates)
    sector_counts = Counter(c.metadata.sector or "UNKNOWN" for c in thesis_candidates)
    signal_family_counts = Counter(
        c.metadata.primary_signal_family for c in thesis_candidates
    )
    driver_counts = Counter(c.metadata.market_driver_tag for c in thesis_candidates)
    suppression_reason_counts = Counter(
        s.suppression_reason for s in diversity_result.suppressed
    )
    # Master Plan Section 3: freshness states are FRESH / RECENTLY_OBSERVED
    # / STALE_WITHIN_GRACE / UNAVAILABLE -- "NO_CONTRACT" is this
    # codebase's own honest fourth case (an item whose signal_type has no
    # registered freshness contract at all), never silently folded into
    # UNAVAILABLE (a materially different, real-degradation state).
    freshness_counts = Counter(state or "NO_CONTRACT" for state in freshness_states)

    distinct_thesis_keys = {_thesis_key(c) for c in thesis_candidates}

    return DailyObservationDelta(
        raw_qualified_observation_count=len(thesis_candidates),
        distinct_thesis_keys=sorted(distinct_thesis_keys),
        entity_impression_counts=dict(entity_counts),
        sector_impression_counts=dict(sector_counts),
        signal_family_impression_counts=dict(signal_family_counts),
        driver_impression_counts=dict(driver_counts),
        diversity_selected_count=len(diversity_result.selected),
        diversity_suppressed_count=len(diversity_result.suppressed),
        suppression_reason_counts={
            str(reason): count for reason, count in suppression_reason_counts.items()
        },
        exploration_eligible_count=len(exploration_eligible_pool),
        exploration_placed_count=(
            1 if exploration_result.placed_event_id is not None else 0
        ),
        freshness_state_counts=dict(freshness_counts),
        # Master Plan Section 16A: Top-Five Competition Ratio's numerator
        # -- "eligible distinct theses before diversity constraints" --
        # this observation's own distinct thesis count, pre-diversity.
        pre_diversity_thesis_count=len(distinct_thesis_keys),
    )


def record_pipeline_observation(
    *,
    now: datetime,
    thesis_candidates: list[ThesisCandidate],
    diversity_result: DiversityResult,
    exploration_eligible_pool: list[ThesisCandidate],
    exploration_result: ExplorationPlacementResult,
    freshness_states: list[Optional[str]],
) -> None:
    """The single call site's entry point (logan_feed.py). Never raises --
    a telemetry failure must never affect a real request's response. A
    no-op, exactly like every other store in this codebase, when
    persistence is disabled."""
    try:
        store = _get_store()
        if store is None:
            return
        delta = build_observation_delta(
            thesis_candidates=thesis_candidates,
            diversity_result=diversity_result,
            exploration_eligible_pool=exploration_eligible_pool,
            exploration_result=exploration_result,
            freshness_states=freshness_states,
        )
        store.record(now.date(), delta)
    except Exception as exc:  # noqa: BLE001 -- telemetry must never break a request
        print(f"[universe-telemetry] observation recording failed, continuing: {exc}")


def daily_telemetry_range(start: date, end: date) -> list[DailyUniverseTelemetry]:
    """Real, persisted daily rows in [start, end] -- returns [] when
    persistence is disabled or no rows exist yet. A missing date inside the
    range is a real coverage gap, never backfilled or interpolated."""
    store = _get_store()
    if store is None:
        return []
    return store.range(start, end)


# --- Master Plan Section 16A: derived metrics, computed from already- ---
# --- persisted real daily rows, no new storage needed for either. -------


def top_five_competition_ratio(row: DailyUniverseTelemetry) -> Optional[float]:
    """Master Plan Section 16A: `eligible distinct theses before diversity
    constraints / 5`. Uses `peak_pre_diversity_thesis_count` (the largest
    single-observation count that day), never a sum across the day's
    observations -- a sum would scale with polling frequency, not real
    competition for the five slots. Returns None only when the row itself
    represents zero observations (should not occur for a real persisted
    row, but guarded rather than dividing nonsense)."""
    if row.observation_count == 0:
        return None
    return row.peak_pre_diversity_thesis_count / TOP_FIVE_POSITIONS


def thesis_novelty_rate(
    rows_by_date: dict[str, DailyUniverseTelemetry],
    target: date,
    *,
    recency_window_days: int = THESIS_NOVELTY_RECENCY_WINDOW_DAYS,
) -> Optional[float]:
    """Master Plan Section 16A: `surfaceable theses not materially
    duplicating recent deterministic thesis metadata / total surfaceable
    theses`. "Recent" is this session's own explicit
    `recency_window_days`-day assumption (see module docstring) -- the
    underlying comparison (thesis-key set membership) is deterministic and
    metadata-based only, per the plan's own explicit instruction not to
    imply semantic equivalence detection.

    `rows_by_date` must be keyed by ISO date string (as
    `DailyUniverseTelemetry.date` already is) and should span at least
    `target - recency_window_days` through `target` for an honest answer;
    a caller with a shorter history will get a rate computed against
    whatever "recent" history actually exists, never fabricated.
    """
    target_row = rows_by_date.get(target.isoformat())
    if target_row is None or not target_row.distinct_thesis_keys:
        return None

    recent_keys: set = set()
    for offset in range(1, recency_window_days + 1):
        prior_row = rows_by_date.get((target - timedelta(days=offset)).isoformat())
        if prior_row is not None:
            recent_keys.update(prior_row.distinct_thesis_keys)

    target_keys = set(target_row.distinct_thesis_keys)
    novel_keys = target_keys - recent_keys
    return len(novel_keys) / len(target_keys)


def distinct_qualified_entity_count(row: DailyUniverseTelemetry) -> int:
    """V1a Proof-Instrumentation Closeout: the polling-frequency-immune
    count of distinct entities with at least one qualifying opportunity
    that day -- the authoritative source for the "qualified opportunities
    per market day" / No-Opportunity Day gates, replacing the raw,
    polling-frequency-sensitive `raw_qualified_observation_count`.

    `entity_impression_counts`' VALUES sum across a day's observations
    (inflated by repeated polling of the same real state), but its KEY SET
    does not -- observing the same 5 qualifying entities once or 500 times
    in one day yields the same 5-entity key set either way. This reuses
    entity_id as the stable "opportunity identity" for day-level supply
    counting, distinct from `distinct_thesis_keys`' (entity, driver)
    identity used for thesis-level counting -- the Master Plan's own text
    treats "qualified opportunities" and "distinct theses" as two separate
    measurement bullets, so this session does not conflate them.
    """
    return len(row.entity_impression_counts)


def max_consecutive_zero_qualified_days(rows: list[DailyUniverseTelemetry]) -> int:
    """Master Plan Section 4's operational gate input -- `rows` must be in
    ascending date order with no caller-side gap-filling; a missing date
    (no row at all) is treated the same as a genuine zero-qualified day
    for this specific run-length count, since Section 16A's own
    No-Opportunity Day definition ("zero objectively qualified theses
    survive... before personalization") does not distinguish "STRATUS
    observed zero" from "STRATUS was not observed that day" -- both mean
    no evidence of qualified supply exists for that day. Days are compared
    by calendar continuity (not just list adjacency), so a real gap is
    correctly counted as intervening zero-days. Uses
    `distinct_qualified_entity_count()` (polling-frequency-immune), never
    the raw summed field.
    """
    if not rows:
        return 0
    by_date = {row.date: row for row in rows}
    start = date.fromisoformat(rows[0].date)
    end = date.fromisoformat(rows[-1].date)

    longest = current = 0
    cursor = start
    while cursor <= end:
        row = by_date.get(cursor.isoformat())
        is_zero_day = row is None or distinct_qualified_entity_count(row) == 0
        current = current + 1 if is_zero_day else 0
        longest = max(longest, current)
        cursor += timedelta(days=1)
    return longest


def top_five_diversity_survival_rate(row: DailyUniverseTelemetry) -> Optional[float]:
    """Master Plan Section 4: `>=90% of top-five candidates survive
    diversity checks`. survival_rate = selected / (selected + suppressed)
    -- both already real, wired counts."""
    total = row.diversity_selected_count + row.diversity_suppressed_count
    if total == 0:
        return None
    return row.diversity_selected_count / total


def max_single_entity_impression_share(row: DailyUniverseTelemetry) -> Optional[float]:
    """Master Plan Section 4: `no entity >30% of top-five impressions`."""
    total = sum(row.entity_impression_counts.values())
    if total == 0:
        return None
    return max(row.entity_impression_counts.values()) / total


def max_single_sector_impression_share(row: DailyUniverseTelemetry) -> Optional[float]:
    """Master Plan Section 4: `no sector >40%`."""
    total = sum(row.sector_impression_counts.values())
    if total == 0:
        return None
    return max(row.sector_impression_counts.values()) / total


def stale_grace_read_rate(row: DailyUniverseTelemetry) -> Optional[float]:
    """Master Plan Section 4: `stale-grace reads <2%` -- real, from
    freshness.py's own STALE_WITHIN_GRACE state, now that freshness is
    tracked per-state rather than as a single available/unavailable
    boolean."""
    total = sum(row.freshness_state_counts.values())
    if total == 0:
        return None
    return row.freshness_state_counts.get("STALE_WITHIN_GRACE", 0) / total


def user_visible_stale_beyond_grace_count(row: DailyUniverseTelemetry) -> int:
    """Master Plan Section 4: `user-visible stale beyond grace: 0`. Maps
    directly to freshness.py's own UNAVAILABLE state definition ("no value
    at all, or past even the grace window") -- a real count, not a proxy."""
    return row.freshness_state_counts.get("UNAVAILABLE", 0)


@dataclass(frozen=True)
class RealOperationalSignals:
    """Real, currently-observable operational signals -- explicitly
    process-lifetime/point-in-time where noted, never a genuine durable
    14-day rolling window (this codebase has no durable event log for
    per-call provider history; `recent_faults()` is an in-memory ring
    buffer capped at 200 entries, and `fmp_budget_snapshot()` is cumulative
    since process start). Callers must not present these as satisfying the
    Master Plan's literal 14-day requirement.
    """

    fmp_rate_limit_responses: int
    real_call_failure_rate: Optional[float]
    peak_calls_per_minute_now: int
    unexplained_universe_changes: int


def collect_real_operational_signals(*, scheduler=None) -> RealOperationalSignals:
    """Every value here is real and currently observable -- none is a
    synthetic placeholder. `real_call_failure_rate` is None when zero real
    calls have been attempted yet (an honest "no data," not a fabricated
    0.0)."""
    faults = recent_faults(limit=200)
    fmp_rate_limit_responses = sum(1 for f in faults if f.code == "DATA-301")

    budget = fmp_budget_snapshot()
    total_real_calls = sum(c.real_calls for c in budget.by_endpoint.values())
    total_failures = sum(c.failures for c in budget.by_endpoint.values())
    real_call_failure_rate = (
        total_failures / total_real_calls if total_real_calls > 0 else None
    )

    peak_calls_per_minute_now = (
        scheduler.current_calls_per_minute() if scheduler is not None else 0
    )

    from .universe_manager import get_membership_store

    unexplained_universe_changes = 0
    membership_store = get_membership_store()
    if membership_store is not None:
        for record in membership_store.load_all():
            if not record.admission_reason_codes:
                unexplained_universe_changes += 1
            if record.effective_until is not None and not record.removal_reason:
                unexplained_universe_changes += 1

    return RealOperationalSignals(
        fmp_rate_limit_responses=fmp_rate_limit_responses,
        real_call_failure_rate=real_call_failure_rate,
        peak_calls_per_minute_now=peak_calls_per_minute_now,
        unexplained_universe_changes=unexplained_universe_changes,
    )


def real_meaningful_revision_count(start: date, end: date) -> int:
    """Real count of GLOBAL meaningful revisions in [start, end], sourced
    directly from the already-existing, already-durable
    OpportunityRevisionStore's own SQLite file (opportunity_revisions.db)
    -- no new instrumentation needed for the numerator, and no change to
    revision_store.py itself (a plain, read-only, schema-matching query
    against its file, not a private-attribute reach-in). This is the raw
    count only -- see BLOCKED_METRICS for why the Material Revision
    Rubric's >=70% rubric-CLASS rate is not computed from it.
    """
    import sqlite3

    from .config import revision_store_db_path

    if not memory_persistence_enabled():
        return 0
    path = revision_store_db_path()
    if not path.exists():
        return 0
    conn = sqlite3.connect(str(path))
    try:
        rows = conn.execute("SELECT created_at FROM opportunity_revisions").fetchall()
    finally:
        conn.close()
    count = 0
    for (created_at_text,) in rows:
        created_at = datetime.fromisoformat(created_at_text)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if start <= created_at.date() <= end:
            count += 1
    return count
