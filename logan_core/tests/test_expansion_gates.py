"""Universe Manager V1a Block 21 -- V1a -> V1b expansion gates
(logan_core/universe/expansion_gates.py). Pure evaluation-function tests
against synthetic metrics snapshots -- this module never collects real
metrics itself.
"""

from logan_core.universe.expansion_gates import (
    MIN_WARMUP_DAYS,
    OPPORTUNITY_QUALITY_GATES_REQUIRED,
    OperationalMetricsSnapshot,
    OpportunityQualityMetricsSnapshot,
    evaluate_expansion_gates,
)


def _passing_operational() -> OperationalMetricsSnapshot:
    return OperationalMetricsSnapshot(
        fmp_rate_limit_responses=0,
        scheduled_fetch_failure_rate=0.001,
        time_sensitive_delay_p95_seconds=60.0,
        time_sensitive_delay_p99_seconds=120.0,
        critical_freshness_p95_ratio=1.0,
        critical_freshness_p99_ratio=1.1,
        stale_grace_read_rate=0.001,
        user_visible_stale_beyond_grace_count=0,
        peak_calls_per_minute=150,
        coalescing_success_rate=0.999,
        unexplained_universe_changes=0,
    )


def _passing_opportunity_quality() -> OpportunityQualityMetricsSnapshot:
    return OpportunityQualityMetricsSnapshot(
        distinct_surfaced_theses_14d=10,
        max_consecutive_zero_qualified_days=1,
        top_five_diversity_survival_rate=0.95,
        max_single_entity_impression_share=0.20,
        max_single_sector_impression_share=0.30,
        complete_evidence_payload_rate=0.98,
        meaningful_revision_content_rate=0.80,
    )


def test_fully_passing_snapshot_recommends_expansion():
    report = evaluate_expansion_gates(
        _passing_operational(),
        _passing_opportunity_quality(),
        warmup_days_elapsed=MIN_WARMUP_DAYS,
    )
    assert report.all_operational_gates_pass is True
    assert report.opportunity_quality_gates_passed_count == 7
    assert report.recommend_expansion is True


def test_insufficient_warmup_blocks_expansion_even_with_perfect_metrics():
    report = evaluate_expansion_gates(
        _passing_operational(),
        _passing_opportunity_quality(),
        warmup_days_elapsed=MIN_WARMUP_DAYS - 1,
    )
    assert report.warmup_satisfied is False
    assert report.recommend_expansion is False


def test_a_single_failing_operational_gate_blocks_expansion():
    operational = OperationalMetricsSnapshot(
        fmp_rate_limit_responses=1,  # violates the hard 0 ceiling
        scheduled_fetch_failure_rate=0.001,
        time_sensitive_delay_p95_seconds=60.0,
        time_sensitive_delay_p99_seconds=120.0,
        critical_freshness_p95_ratio=1.0,
        critical_freshness_p99_ratio=1.1,
        stale_grace_read_rate=0.001,
        user_visible_stale_beyond_grace_count=0,
        peak_calls_per_minute=150,
        coalescing_success_rate=0.999,
        unexplained_universe_changes=0,
    )
    report = evaluate_expansion_gates(
        operational, _passing_opportunity_quality(), warmup_days_elapsed=MIN_WARMUP_DAYS
    )
    assert report.all_operational_gates_pass is False
    assert report.recommend_expansion is False
    failing = [c for c in report.operational_checks if not c.passed]
    assert failing[0].name == "fmp_rate_limit_responses"


def test_operational_gates_pass_but_opportunity_quality_fails_blocks_expansion():
    """Explicit Block 21 requirement: if operations pass but opportunity
    yield fails, do not recommend expansion (the report should prompt
    diagnosis, never "just add more tickers")."""
    weak_quality = OpportunityQualityMetricsSnapshot(
        distinct_surfaced_theses_14d=2,  # well below the floor of 8
        max_consecutive_zero_qualified_days=6,  # above the 4-day ceiling
        top_five_diversity_survival_rate=0.50,
        max_single_entity_impression_share=0.60,
        max_single_sector_impression_share=0.70,
        complete_evidence_payload_rate=0.50,
        meaningful_revision_content_rate=0.30,
    )
    report = evaluate_expansion_gates(
        _passing_operational(), weak_quality, warmup_days_elapsed=MIN_WARMUP_DAYS
    )
    assert report.all_operational_gates_pass is True
    assert report.opportunity_quality_gates_passed_count == 0
    assert report.recommend_expansion is False


def test_exactly_the_required_count_of_opportunity_quality_gates_still_recommends():
    quality = OpportunityQualityMetricsSnapshot(
        distinct_surfaced_theses_14d=10,  # pass
        max_consecutive_zero_qualified_days=1,  # pass
        top_five_diversity_survival_rate=0.95,  # pass
        max_single_entity_impression_share=0.20,  # pass
        max_single_sector_impression_share=0.30,  # pass
        complete_evidence_payload_rate=0.98,  # pass
        meaningful_revision_content_rate=0.10,  # FAIL (below 0.70 floor)
    )
    report = evaluate_expansion_gates(
        _passing_operational(), quality, warmup_days_elapsed=MIN_WARMUP_DAYS
    )
    assert (
        report.opportunity_quality_gates_passed_count
        == OPPORTUNITY_QUALITY_GATES_REQUIRED
    )
    assert report.recommend_expansion is True


def test_one_below_the_required_count_blocks_expansion():
    quality = OpportunityQualityMetricsSnapshot(
        distinct_surfaced_theses_14d=10,  # pass
        max_consecutive_zero_qualified_days=1,  # pass
        top_five_diversity_survival_rate=0.95,  # pass
        max_single_entity_impression_share=0.20,  # pass
        max_single_sector_impression_share=0.30,  # pass
        complete_evidence_payload_rate=0.10,  # FAIL
        meaningful_revision_content_rate=0.10,  # FAIL
    )
    report = evaluate_expansion_gates(
        _passing_operational(), quality, warmup_days_elapsed=MIN_WARMUP_DAYS
    )
    assert (
        report.opportunity_quality_gates_passed_count
        == OPPORTUNITY_QUALITY_GATES_REQUIRED - 1
    )
    assert report.recommend_expansion is False


def test_unresolved_integrity_incident_blocks_expansion_even_if_everything_else_passes():
    report = evaluate_expansion_gates(
        _passing_operational(),
        _passing_opportunity_quality(),
        warmup_days_elapsed=MIN_WARMUP_DAYS,
        unresolved_integrity_incident=True,
    )
    assert report.recommend_expansion is False


def test_evaluate_expansion_gates_never_auto_expands_anything():
    """This module produces an advisory boolean only -- it has no side
    effects, no config write, nothing that could itself change the
    monitored cohort."""
    import inspect

    source = inspect.getsource(evaluate_expansion_gates)
    assert "select_monitored_cohort" not in source
    assert "run_universe_reevaluation" not in source
