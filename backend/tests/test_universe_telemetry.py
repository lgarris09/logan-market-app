"""Universe Manager V1a Operational + Supply Telemetry (V1a ITERATE block,
Phase 3) -- proves real pipeline observation is recorded durably, never
alters feed output, accumulates correctly within a day, and that the
explicitly-blocked metrics stay unimplemented rather than guessed at.
"""

from datetime import datetime, timedelta, timezone

from backend.app.logan_feed import reset_pipeline_state, run_demo_feed
from backend.app.universe_telemetry import (
    BLOCKED_METRICS,
    collect_real_operational_signals,
    daily_telemetry_range,
    real_meaningful_revision_count,
    reset_universe_telemetry_state,
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
    assert row.qualified_opportunity_count >= 1
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
    assert second.qualified_opportunity_count >= first.qualified_opportunity_count


def test_missing_days_are_a_real_gap_not_zero_filled(monkeypatch, tmp_path):
    _enable_persistence(monkeypatch, tmp_path)
    today = datetime.now(timezone.utc).date()
    run_demo_feed()

    rows = daily_telemetry_range(today - timedelta(days=5), today)
    # Only today has a row -- the prior five days were never observed and
    # must not appear as fabricated zero-value rows.
    assert len(rows) == 1
    assert rows[0].date == today.isoformat()


def test_blocked_metrics_are_named_and_not_silently_implemented():
    """Governance guard: the metrics this session found no definition for
    anywhere in the repo stay explicitly listed as blocked, not quietly
    added to any real snapshot function."""
    assert set(BLOCKED_METRICS) == {
        "signal_yield",
        "top_five_competition_ratio",
        "deterministic_thesis_novelty_rate",
        "complete_evidence_payload_rate",
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
