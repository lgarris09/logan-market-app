"""Universe Manager V1a Operational + Supply Telemetry (V1a ITERATE block,
Phase 3) -- proves real pipeline observation is recorded durably, never
alters feed output, accumulates correctly within a day, and that the
explicitly-blocked metrics stay unimplemented rather than guessed at.
"""

from datetime import date, datetime, timedelta, timezone

from backend.app.logan_feed import reset_pipeline_state, run_demo_feed
from backend.app.universe_telemetry import (
    BLOCKED_METRICS,
    collect_real_operational_signals,
    daily_telemetry_range,
    distinct_qualified_entity_count,
    max_consecutive_zero_qualified_days,
    max_single_entity_impression_share,
    max_single_sector_impression_share,
    real_meaningful_revision_count,
    reset_universe_telemetry_state,
    stale_grace_read_rate,
    thesis_novelty_rate,
    top_five_competition_ratio,
    top_five_diversity_survival_rate,
    user_visible_stale_beyond_grace_count,
)
from backend.app.universe_telemetry_store import (
    DailyObservationDelta,
    UniverseDailyTelemetryStore,
)


def _enable_persistence(monkeypatch, tmp_path):
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv("STRATUS_STATE_DB_PATH", str(tmp_path / "state.db"))
    reset_pipeline_state()
    reset_universe_telemetry_state()


def test_real_pipeline_run_records_a_daily_telemetry_row(monkeypatch, tmp_path):
    _enable_persistence(monkeypatch, tmp_path)
    today = datetime.now(timezone.utc).date()

    run_demo_feed()

    rows = daily_telemetry_range(today, today)
    assert len(rows) == 1
    row = rows[0]
    assert row.observation_count == 1
    # A real, non-fabricated assertion: the demo fixture set produces at
    # least one qualifying opportunity, so this is real evidence, not a
    # trivially-true structural check.
    assert row.raw_qualified_observation_count >= 1
    assert distinct_qualified_entity_count(row) >= 1
    assert row.diversity_selected_count >= 1


def test_telemetry_recording_never_alters_feed_output(monkeypatch, tmp_path):
    """The core Phase 6 invariant: telemetry observes, it never changes
    what the pipeline returns. Compared on `entity_id` (stable identity),
    not `event_id` (freshly randomized by reset_pipeline_state() on each
    first call after a reset, unrelated to persistence)."""
    monkeypatch.delenv("STRATUS_PERSIST_MEMORY", raising=False)
    reset_pipeline_state()
    reset_universe_telemetry_state()
    without_persistence = run_demo_feed()

    reset_pipeline_state()
    _enable_persistence(monkeypatch, tmp_path)
    with_persistence = run_demo_feed()

    key = lambda items: sorted(  # noqa: E731
        (i.entity_id, i.rank, i.diversity_suppressed, i.exploration_placement_reason)
        for i in items
    )
    assert key(without_persistence.items) == key(with_persistence.items)


def test_telemetry_is_a_no_op_when_persistence_disabled(monkeypatch):
    monkeypatch.delenv("STRATUS_PERSIST_MEMORY", raising=False)
    reset_pipeline_state()
    reset_universe_telemetry_state()

    run_demo_feed()

    today = datetime.now(timezone.utc).date()
    assert daily_telemetry_range(today, today) == []


def test_repeated_observations_in_one_day_accumulate(monkeypatch, tmp_path):
    _enable_persistence(monkeypatch, tmp_path)
    today = datetime.now(timezone.utc).date()

    run_demo_feed()
    first = daily_telemetry_range(today, today)[0]
    run_demo_feed()
    second = daily_telemetry_range(today, today)[0]

    assert second.observation_count == first.observation_count + 1
    assert (
        second.raw_qualified_observation_count >= first.raw_qualified_observation_count
    )
    # The polling-frequency-immune count stays identical across repeated
    # observations of the same real state -- the whole point of the fix.
    assert distinct_qualified_entity_count(second) == distinct_qualified_entity_count(
        first
    )


def test_missing_days_are_a_real_gap_not_zero_filled(monkeypatch, tmp_path):
    _enable_persistence(monkeypatch, tmp_path)
    today = datetime.now(timezone.utc).date()
    run_demo_feed()

    rows = daily_telemetry_range(today - timedelta(days=5), today)
    # Only today has a row -- the prior five days were never observed and
    # must not appear as fabricated zero-value rows.
    assert len(rows) == 1
    assert rows[0].date == today.isoformat()


def test_recorded_freshness_counts_reflect_real_item_states(monkeypatch, tmp_path):
    """Phase 6 safeguard, extended for the per-state breakdown (Master Plan
    reconciliation block): a recorded day's freshness_state_counts must
    reflect the pipeline's own real, already-computed freshness_state
    values exactly, per state -- never silently zero (which would
    misrepresent stale/unavailable data as current) and never collapsed
    into a single bucket that loses the FRESH/RECENTLY_OBSERVED/
    STALE_WITHIN_GRACE/UNAVAILABLE distinction the Master Plan explicitly
    asks to be formalized."""
    _enable_persistence(monkeypatch, tmp_path)
    today = datetime.now(timezone.utc).date()

    demo = run_demo_feed()
    row = daily_telemetry_range(today, today)[0]

    real_counts: dict = {}
    for item in demo.items:
        key = item.freshness_state or "NO_CONTRACT"
        real_counts[key] = real_counts.get(key, 0) + 1

    assert row.freshness_state_counts == real_counts
    assert sum(row.freshness_state_counts.values()) == len(demo.items)


def test_blocked_metrics_are_named_and_not_silently_implemented():
    """Governance guard, updated for the V1a Final Proof-Readiness
    Closeout: complete_evidence_payload_rate now has an approved
    deterministic definition and is implemented -- removed from this
    list. The remaining entries either have no formula anywhere in the
    plan, or need a confirmed classification-mapping decision, or need a
    durable event-log subsystem this block does not build -- none are
    silently guessed at."""
    assert set(BLOCKED_METRICS) == {
        "signal_family_yield_rate",
        "material_revision_rubric_classification_rate",
        "time_sensitive_delay_p95_seconds",
        "time_sensitive_delay_p99_seconds",
        "critical_freshness_p95_ratio",
        "critical_freshness_p99_ratio",
        "peak_calls_per_minute_historical",
        "coalescing_success_rate",
    }


def test_real_operational_signals_are_honest_about_no_data_yet(monkeypatch, tmp_path):
    """Before any real FMP call has been attempted, the failure rate is
    None (honest "no data"), never a fabricated 0.0."""
    _enable_persistence(monkeypatch, tmp_path)
    from logan_core.receptors.providers.fmp import reset_fmp_cache

    reset_fmp_cache()
    signals = collect_real_operational_signals()
    assert signals.real_call_failure_rate is None


def test_real_operational_signals_reflect_a_real_recorded_fault(monkeypatch, tmp_path):
    _enable_persistence(monkeypatch, tmp_path)
    from logan_core.diagnostics import record_fault, reset_fault_state

    reset_fault_state()
    record_fault("DATA-301", "test", context={})
    signals = collect_real_operational_signals()
    assert signals.fmp_rate_limit_responses == 1


def test_real_meaningful_revision_count_reflects_real_store_rows(monkeypatch, tmp_path):
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    revisions_path = tmp_path / "revisions.db"
    monkeypatch.setenv("STRATUS_REVISIONS_DB_PATH", str(revisions_path))

    from backend.app.revision_store import OpportunityRevisionStore
    from logan_core.contracts import OpportunityRevision

    store = OpportunityRevisionStore(str(revisions_path))
    today = datetime.now(timezone.utc)
    store.append(
        OpportunityRevision(
            entity_id="SYMBOL:AAPL",
            revision=1,
            lifecycle_state="developing",
            confidence_score=0.8,
            trigger_codes=["STOCK_PRICE_MOVE_SIGNIFICANT"],
            change_type="new_opportunity",
            reason="test",
            created_at=today,
        )
    )
    store.close()

    count = real_meaningful_revision_count(today.date(), today.date())
    assert count == 1
    assert (
        real_meaningful_revision_count(
            today.date() - timedelta(days=30), today.date() - timedelta(days=29)
        )
        == 0
    )


# --- V1a Proof-Instrumentation Closeout: Material Revision Rubric mapping ----


def test_classify_persisted_revisions_maps_only_confident_change_types(
    monkeypatch, tmp_path
):
    from backend.app.revision_store import OpportunityRevisionStore
    from backend.app.universe_telemetry import classify_persisted_revisions
    from logan_core.contracts import OpportunityRevision

    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    revisions_path = tmp_path / "revisions.db"
    monkeypatch.setenv("STRATUS_REVISIONS_DB_PATH", str(revisions_path))

    store = OpportunityRevisionStore(str(revisions_path))
    today = datetime.now(timezone.utc)

    def _revision(revision: int, change_type) -> OpportunityRevision:
        return OpportunityRevision(
            entity_id="SYMBOL:AAPL",
            revision=revision,
            lifecycle_state="developing",
            confidence_score=0.8,
            trigger_codes=["STOCK_PRICE_MOVE_SIGNIFICANT"],
            change_type=change_type,
            reason="test",
            created_at=today,
        )

    store.append(_revision(1, "personal_relevance_increased"))
    store.append(_revision(2, "trajectory_strengthening"))
    store.append(_revision(3, "confidence_increased"))  # deliberately unmapped
    store.close()

    result = classify_persisted_revisions(today.date(), today.date())
    assert result["classified"] == {
        "PERSONAL_RELEVANCE_CHANGE": 1,
        "TRAJECTORY_CHANGE": 1,
    }
    assert result["unclassified"] == 1


def test_classify_persisted_revisions_confident_map_has_no_ambiguous_entries():
    """Governance guard: every mapped change_type must be one this session
    judged as a direct, unambiguous name correspondence -- confidence_*/
    aged_to_*/new_*/convergence_formed/reactivated/new_opportunity must
    never silently appear here."""
    from backend.app.universe_telemetry import (
        REVISION_RUBRIC_CLASS_BY_CHANGE_TYPE,
        UNMAPPED_REVISION_CHANGE_TYPES,
    )

    assert set(REVISION_RUBRIC_CLASS_BY_CHANGE_TYPE) == {
        "personal_relevance_increased",
        "personal_relevance_decreased",
        "trajectory_strengthening",
        "trajectory_weakening",
        "trajectory_reversing",
        "trajectory_reaccelerated",
    }
    assert set(UNMAPPED_REVISION_CHANGE_TYPES) == {
        "new_opportunity",
        "confidence_increased",
        "confidence_decreased",
        "new_signal_appeared",
        "convergence_formed",
        "aged_to_cooling",
        "aged_to_stale",
        "aged_to_expired",
        "reactivated",
    }
    assert not set(REVISION_RUBRIC_CLASS_BY_CHANGE_TYPE) & set(
        UNMAPPED_REVISION_CHANGE_TYPES
    )


# --- Master Plan reconciliation: derived-metric functions --------------------


def test_top_five_competition_ratio_uses_peak_not_sum(tmp_path):
    """Master Plan Section 16A: peak_pre_diversity_thesis_count is MAXED
    across the day's observations, not summed -- a day polled twice (12
    theses, then 8 theses) must report ratio = 12/5, never (12+8)/5."""
    store = UniverseDailyTelemetryStore(str(tmp_path / "telemetry.db"))
    day = date(2026, 9, 2)
    store.record(day, DailyObservationDelta(pre_diversity_thesis_count=12))
    store.record(day, DailyObservationDelta(pre_diversity_thesis_count=8))
    row = store.get(day)
    store.close()

    assert row is not None
    assert row.peak_pre_diversity_thesis_count == 12
    assert top_five_competition_ratio(row) == 12 / 5


def test_thesis_novelty_rate_deterministic_against_recent_history(tmp_path):
    store = UniverseDailyTelemetryStore(str(tmp_path / "telemetry.db"))
    target = date(2026, 9, 14)
    store.record(
        target - timedelta(days=1),
        DailyObservationDelta(distinct_thesis_keys=["AAPL|EARNINGS_RESULT"]),
    )
    store.record(
        target,
        DailyObservationDelta(
            distinct_thesis_keys=[
                "AAPL|EARNINGS_RESULT",  # duplicates yesterday -- not novel
                "TSLA|PRICE_DISLOCATION",  # new -- novel
            ]
        ),
    )
    rows = {row.date: row for row in store.range(target - timedelta(days=14), target)}
    store.close()

    rate = thesis_novelty_rate(rows, target)
    assert rate == 0.5  # 1 of 2 theses is novel


def test_thesis_novelty_rate_is_none_with_no_observations_that_day(tmp_path):
    store = UniverseDailyTelemetryStore(str(tmp_path / "telemetry.db"))
    rows = {row.date: row for row in store.range(date(2026, 1, 1), date(2026, 1, 1))}
    store.close()
    assert thesis_novelty_rate(rows, date(2026, 1, 1)) is None


def test_max_consecutive_zero_qualified_days_counts_real_gaps(tmp_path):
    """A missing day (no persisted row at all) counts the same as a real
    zero-qualified day, per No-Opportunity Day's own Master Plan
    definition -- both mean no evidence of qualified supply exists. Uses
    entity_impression_counts (the polling-frequency-immune signal), not
    the raw diagnostic-only count."""
    store = UniverseDailyTelemetryStore(str(tmp_path / "telemetry.db"))
    base = date(2026, 9, 1)
    store.record(
        base, DailyObservationDelta(entity_impression_counts={"AAPL": 1, "TSLA": 1})
    )
    # base+1, base+2, base+3 intentionally never recorded -- a real gap.
    store.record(base + timedelta(days=4), DailyObservationDelta())  # zero entities
    store.record(
        base + timedelta(days=5),
        DailyObservationDelta(entity_impression_counts={"MSFT": 1}),
    )
    rows = store.range(base, base + timedelta(days=5))
    store.close()

    # 3 missing days (2,3,4) + 1 explicit zero day (5) = 4 consecutive.
    assert max_consecutive_zero_qualified_days(rows) == 4


def test_distinct_qualified_entity_count_is_immune_to_polling_frequency(tmp_path):
    """V1a Proof-Instrumentation Closeout regression test: the same real
    supply (3 distinct qualifying entities) observed once vs. 50 times in
    one day must produce the identical day-level count -- polling
    frequency must never inflate "qualified opportunities per market
    day." """
    entities = {"AAPL": 1, "TSLA": 1, "MSFT": 1}

    store_a = UniverseDailyTelemetryStore(str(tmp_path / "once.db"))
    day = date(2026, 9, 2)
    store_a.record(day, DailyObservationDelta(entity_impression_counts=entities))
    row_a = store_a.get(day)
    store_a.close()

    store_b = UniverseDailyTelemetryStore(str(tmp_path / "fifty_times.db"))
    for _ in range(50):
        store_b.record(day, DailyObservationDelta(entity_impression_counts=entities))
    row_b = store_b.get(day)
    store_b.close()

    assert row_a is not None and row_b is not None
    # The raw diagnostic field IS distorted by polling frequency (1 vs 50
    # observations) -- proving the distortion is real, not merely assumed.
    assert row_b.observation_count == 50
    assert row_b.entity_impression_counts["AAPL"] == 50
    # But the authoritative, polling-frequency-immune count is identical.
    assert distinct_qualified_entity_count(row_a) == 3
    assert distinct_qualified_entity_count(row_b) == 3
    assert distinct_qualified_entity_count(row_a) == distinct_qualified_entity_count(
        row_b
    )


def test_top_five_diversity_survival_rate(tmp_path):
    store = UniverseDailyTelemetryStore(str(tmp_path / "telemetry.db"))
    day = date(2026, 9, 2)
    store.record(
        day,
        DailyObservationDelta(diversity_selected_count=9, diversity_suppressed_count=1),
    )
    row = store.get(day)
    store.close()
    assert row is not None
    assert top_five_diversity_survival_rate(row) == 0.9


def test_max_single_entity_and_sector_impression_share(tmp_path):
    store = UniverseDailyTelemetryStore(str(tmp_path / "telemetry.db"))
    day = date(2026, 9, 2)
    store.record(
        day,
        DailyObservationDelta(
            entity_impression_counts={"AAPL": 3, "TSLA": 1},
            sector_impression_counts={"Technology": 4},
        ),
    )
    row = store.get(day)
    store.close()
    assert row is not None
    assert max_single_entity_impression_share(row) == 3 / 4
    assert max_single_sector_impression_share(row) == 1.0


def test_stale_grace_and_unavailable_real_counts(tmp_path):
    store = UniverseDailyTelemetryStore(str(tmp_path / "telemetry.db"))
    day = date(2026, 9, 2)
    store.record(
        day,
        DailyObservationDelta(
            freshness_state_counts={
                "FRESH": 6,
                "STALE_WITHIN_GRACE": 1,
                "UNAVAILABLE": 1,
            }
        ),
    )
    row = store.get(day)
    store.close()
    assert row is not None
    assert stale_grace_read_rate(row) == 1 / 8
    assert user_visible_stale_beyond_grace_count(row) == 1
