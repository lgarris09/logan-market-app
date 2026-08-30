"""Universe Manager V1a Blocks 1-6 -- pure logan_core decision logic:
candidate source versioning/reproducibility, eligibility rules, cohort
selection, membership diff/churn control, and the four-state classifier.
Real provider I/O (backend/app/universe_manager.py) and durable
persistence (backend/app/universe_store.py) are tested separately in
backend/tests/test_universe_manager.py.
"""

from datetime import datetime, timedelta, timezone

from logan_core.contracts import (
    CandidateSecurity,
    MembershipRecord,
    SignalFamilyCoverage,
)
from logan_core.universe.candidate_source import (
    LATEST_CANDIDATE_SOURCE_VERSION,
    load_candidate_snapshot,
    registered_snapshot_versions,
)
from logan_core.universe.cohort_selection import (
    MAX_COHORT_SIZE,
    MIN_COHORT_SIZE,
    select_monitored_cohort,
)
from logan_core.universe.eligibility import (
    ELIGIBLE_ACTIVE_LIQUID,
    MIN_AVERAGE_DOLLAR_VOLUME,
    PARTIAL_SIGNAL_COVERAGE,
    REJECT_DATA_HEALTH,
    REJECT_INSUFFICIENT_LIQUIDITY,
    REJECT_INVALID_SYMBOL,
    REJECT_TRADING_INACTIVE,
    REJECT_UNSUPPORTED_EXCHANGE,
    evaluate_eligibility,
)
from logan_core.universe.membership_ledger import (
    REMOVAL_REASON_SCHEDULED_REBALANCE,
    rebalance_membership,
)
from logan_core.universe.state import classify_universe_lifecycle_state

NOW = datetime.now(timezone.utc)


def _candidate(symbol="AAPL", sector="Technology") -> CandidateSecurity:
    return CandidateSecurity(
        canonical_id=f"SYMBOL:{symbol}", symbol=symbol, sector=sector
    )


_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _alpha_symbol(group: int, index: int) -> str:
    """A short, purely-alphabetic, deterministic test symbol -- real ticker
    shapes are alphabetic only (see eligibility._has_valid_symbol_shape),
    so test data must be too, never digit-suffixed. `group`/`index` select
    letters rather than being embedded as literal digits."""
    return _LETTERS[group % 26] + _LETTERS[index % 26] + _LETTERS[(group + index) % 26]


# --- Block 2: candidate source ----------------------------------------------


def test_snapshot_has_exactly_one_hundred_securities():
    snapshot = load_candidate_snapshot()
    assert len(snapshot.securities) == 100


def test_snapshot_securities_have_no_duplicate_symbols():
    snapshot = load_candidate_snapshot()
    symbols = [s.symbol for s in snapshot.securities]
    assert len(symbols) == len(set(symbols))


def test_snapshot_carries_required_source_metadata():
    snapshot = load_candidate_snapshot()
    assert snapshot.source_id
    assert snapshot.source_version
    assert snapshot.effective_date
    assert snapshot.retrieved_at


def test_loading_the_same_version_twice_is_byte_identical():
    first = load_candidate_snapshot(LATEST_CANDIDATE_SOURCE_VERSION)
    second = load_candidate_snapshot(LATEST_CANDIDATE_SOURCE_VERSION)
    assert [s.symbol for s in first.securities] == [s.symbol for s in second.securities]
    assert first.effective_date == second.effective_date
    assert first.source_version == second.source_version


def test_an_unregistered_version_raises_rather_than_silently_substituting():
    import pytest

    with pytest.raises(KeyError):
        load_candidate_snapshot("nonexistent-version")


def test_registered_versions_includes_the_latest():
    assert LATEST_CANDIDATE_SOURCE_VERSION in registered_snapshot_versions()


def test_every_security_has_a_canonical_id_distinct_in_form_from_symbol():
    snapshot = load_candidate_snapshot()
    for security in snapshot.securities:
        assert security.canonical_id != security.symbol
        assert security.symbol in security.canonical_id


# --- Block 3: eligibility ----------------------------------------------------


def _eligibility_kwargs(**overrides):
    defaults = dict(
        is_actively_trading=True,
        is_supported_exchange=True,
        has_price_coverage=True,
        has_earnings_coverage=True,
        has_analyst_grade_coverage=True,
        average_dollar_volume=MIN_AVERAGE_DOLLAR_VOLUME * 2,
        provider_health_ok=True,
    )
    defaults.update(overrides)
    return defaults


def test_fully_healthy_candidate_is_eligible_with_no_partial_coverage_flag():
    result = evaluate_eligibility(_candidate(), **_eligibility_kwargs())
    assert result.eligible is True
    assert result.reason_codes == [ELIGIBLE_ACTIVE_LIQUID]


def test_invalid_symbol_shape_is_rejected():
    candidate = CandidateSecurity(canonical_id="SYMBOL:BAD1", symbol="BAD1")
    result = evaluate_eligibility(candidate, **_eligibility_kwargs())
    assert result.eligible is False
    assert result.reason_codes == [REJECT_INVALID_SYMBOL]


def test_trading_inactive_is_rejected():
    result = evaluate_eligibility(
        _candidate(), **_eligibility_kwargs(is_actively_trading=False)
    )
    assert result.eligible is False
    assert result.reason_codes == [REJECT_TRADING_INACTIVE]


def test_unsupported_exchange_is_rejected():
    result = evaluate_eligibility(
        _candidate(), **_eligibility_kwargs(is_supported_exchange=False)
    )
    assert result.eligible is False
    assert result.reason_codes == [REJECT_UNSUPPORTED_EXCHANGE]


def test_missing_price_coverage_is_a_data_health_rejection():
    result = evaluate_eligibility(
        _candidate(), **_eligibility_kwargs(has_price_coverage=False)
    )
    assert result.eligible is False
    assert result.reason_codes == [REJECT_DATA_HEALTH]


def test_provider_unhealthy_is_a_data_health_rejection_even_with_a_quote_flagged():
    result = evaluate_eligibility(
        _candidate(), **_eligibility_kwargs(provider_health_ok=False)
    )
    assert result.eligible is False
    assert result.reason_codes == [REJECT_DATA_HEALTH]


def test_insufficient_liquidity_is_rejected():
    result = evaluate_eligibility(
        _candidate(),
        **_eligibility_kwargs(average_dollar_volume=MIN_AVERAGE_DOLLAR_VOLUME / 2),
    )
    assert result.eligible is False
    assert result.reason_codes == [REJECT_INSUFFICIENT_LIQUIDITY]


def test_missing_dollar_volume_entirely_is_insufficient_liquidity_not_a_crash():
    result = evaluate_eligibility(
        _candidate(), **_eligibility_kwargs(average_dollar_volume=None)
    )
    assert result.eligible is False
    assert result.reason_codes == [REJECT_INSUFFICIENT_LIQUIDITY]


def test_partial_signal_coverage_still_eligible_but_flagged():
    result = evaluate_eligibility(
        _candidate(), **_eligibility_kwargs(has_earnings_coverage=False)
    )
    assert result.eligible is True
    assert ELIGIBLE_ACTIVE_LIQUID in result.reason_codes
    assert PARTIAL_SIGNAL_COVERAGE in result.reason_codes


def test_eligibility_result_always_carries_signal_family_coverage():
    result = evaluate_eligibility(
        _candidate(),
        **_eligibility_kwargs(
            has_earnings_coverage=False, has_analyst_grade_coverage=False
        ),
    )
    assert result.signal_family_coverage == SignalFamilyCoverage(
        price=True, earnings=False, analyst_grades=False
    )


# --- Block 4: cohort selection -----------------------------------------------


def _eligible_pairs(symbols_by_sector: dict[str, list[str]]) -> list:
    pairs = []
    for sector, symbols in symbols_by_sector.items():
        for symbol in symbols:
            candidate = _candidate(symbol, sector)
            result = evaluate_eligibility(candidate, **_eligibility_kwargs())
            pairs.append((candidate, result))
    return pairs


def test_cohort_selection_respects_target_size():
    symbols_by_sector = {
        f"Sector{i}": [_alpha_symbol(i, j) for j in range(10)] for i in range(5)
    }
    pairs = _eligible_pairs(symbols_by_sector)
    cohort = select_monitored_cohort(pairs, target_size=30)
    assert len(cohort) == 30


def test_cohort_selection_never_exceeds_the_eligible_pool():
    pairs = _eligible_pairs({"Technology": ["A", "B", "C"]})
    cohort = select_monitored_cohort(pairs, target_size=25)
    assert len(cohort) == 3


def test_cohort_selection_excludes_ineligible_candidates():
    eligible = _candidate("GOOD", "Technology")
    ineligible = _candidate("BAD", "Technology")
    pairs = [
        (eligible, evaluate_eligibility(eligible, **_eligibility_kwargs())),
        (
            ineligible,
            evaluate_eligibility(
                ineligible, **_eligibility_kwargs(is_actively_trading=False)
            ),
        ),
    ]
    cohort = select_monitored_cohort(pairs, target_size=25)
    assert [c.symbol for c in cohort] == ["GOOD"]


def test_cohort_selection_respects_sector_cap():
    symbols_by_sector = {
        "Technology": [_alpha_symbol(0, i) for i in range(20)],
        "Healthcare": [_alpha_symbol(1, i) for i in range(20)],
    }
    pairs = _eligible_pairs(symbols_by_sector)
    cohort = select_monitored_cohort(pairs, target_size=30, sector_cap_fraction=0.30)
    tech_count = sum(1 for c in cohort if c.sector == "Technology")
    assert tech_count <= 9  # ceil(30 * 0.30)


def test_cohort_selection_is_deterministic_across_repeated_calls():
    symbols_by_sector = {
        f"Sector{i}": [_alpha_symbol(i, j) for j in range(8)] for i in range(6)
    }
    pairs = _eligible_pairs(symbols_by_sector)
    first = select_monitored_cohort(pairs, target_size=30)
    second = select_monitored_cohort(pairs, target_size=30)
    assert [c.canonical_id for c in first] == [c.canonical_id for c in second]


def test_cohort_selection_rejects_out_of_range_target_size():
    import pytest

    pairs = _eligible_pairs({"Technology": ["A"]})
    with pytest.raises(ValueError):
        select_monitored_cohort(pairs, target_size=MIN_COHORT_SIZE - 1)
    with pytest.raises(ValueError):
        select_monitored_cohort(pairs, target_size=MAX_COHORT_SIZE + 1)


def test_cohort_selection_prefers_full_signal_coverage_within_a_sector():
    full = _candidate("FULL", "Technology")
    partial = _candidate("PARTIAL", "Technology")
    pairs = [
        (full, evaluate_eligibility(full, **_eligibility_kwargs())),
        (
            partial,
            evaluate_eligibility(
                partial, **_eligibility_kwargs(has_earnings_coverage=False)
            ),
        ),
    ]
    cohort = select_monitored_cohort(pairs, target_size=25)
    assert [c.symbol for c in cohort] == ["FULL", "PARTIAL"]


# --- Block 1: four-state classifier -----------------------------------------


def test_classifier_returns_none_when_not_even_eligible():
    state = classify_universe_lifecycle_state(
        is_universe_eligible=False,
        is_monitored=False,
        is_objectively_qualified=False,
        is_personally_surfaced=False,
    )
    assert state is None


def test_classifier_returns_the_furthest_state_reached():
    assert (
        classify_universe_lifecycle_state(
            is_universe_eligible=True,
            is_monitored=False,
            is_objectively_qualified=False,
            is_personally_surfaced=False,
        )
        == "UNIVERSE_ELIGIBLE"
    )
    assert (
        classify_universe_lifecycle_state(
            is_universe_eligible=True,
            is_monitored=True,
            is_objectively_qualified=False,
            is_personally_surfaced=False,
        )
        == "MONITORED"
    )
    assert (
        classify_universe_lifecycle_state(
            is_universe_eligible=True,
            is_monitored=True,
            is_objectively_qualified=True,
            is_personally_surfaced=False,
        )
        == "OBJECTIVELY_QUALIFIED"
    )
    assert (
        classify_universe_lifecycle_state(
            is_universe_eligible=True,
            is_monitored=True,
            is_objectively_qualified=True,
            is_personally_surfaced=True,
        )
        == "PERSONALLY_SURFACED"
    )


# --- Block 5/6: membership ledger diff + bounded churn ----------------------


def test_rebalance_admits_every_newly_selected_candidate_when_starting_empty():
    cohort = [_candidate("AAPL"), _candidate("MSFT")]
    result = rebalance_membership(
        [], cohort, source_version="v1", now=NOW, max_churn=10
    )
    assert {r.canonical_id for r in result.admitted} == {c.canonical_id for c in cohort}
    assert result.removed == []
    assert result.unchanged_count == 0


def test_rebalance_removes_a_member_no_longer_selected():
    existing = MembershipRecord(
        canonical_id="SYMBOL:AAPL",
        symbol="AAPL",
        source_version="v0",
        policy_version="p0",
        admitted_at=NOW - timedelta(days=30),
        effective_from=NOW - timedelta(days=30),
    )
    result = rebalance_membership(
        [existing], [_candidate("MSFT")], source_version="v1", now=NOW, max_churn=10
    )
    assert len(result.removed) == 1
    removed = result.removed[0]
    assert removed.canonical_id == "SYMBOL:AAPL"
    assert removed.effective_until == NOW
    assert removed.removed_at == NOW
    assert removed.removal_reason == REMOVAL_REASON_SCHEDULED_REBALANCE


def test_rebalance_leaves_unchanged_members_untouched():
    existing = MembershipRecord(
        canonical_id="SYMBOL:AAPL",
        symbol="AAPL",
        source_version="v0",
        policy_version="p0",
        admitted_at=NOW - timedelta(days=30),
        effective_from=NOW - timedelta(days=30),
    )
    result = rebalance_membership(
        [existing], [_candidate("AAPL")], source_version="v1", now=NOW, max_churn=10
    )
    assert result.admitted == []
    assert result.removed == []
    assert result.unchanged_count == 1


def test_rebalance_never_mutates_the_original_record_when_removing():
    existing = MembershipRecord(
        canonical_id="SYMBOL:AAPL",
        symbol="AAPL",
        source_version="v0",
        policy_version="p0",
        admitted_at=NOW - timedelta(days=30),
        effective_from=NOW - timedelta(days=30),
    )
    rebalance_membership([existing], [], source_version="v1", now=NOW, max_churn=10)
    assert existing.effective_until is None
    assert existing.removed_at is None


def test_bounded_churn_caps_total_changes_per_rebalance():
    existing = [
        MembershipRecord(
            canonical_id=f"SYMBOL:OLD{i}",
            symbol=f"OLD{i}",
            source_version="v0",
            policy_version="p0",
            admitted_at=NOW - timedelta(days=30),
            effective_from=NOW - timedelta(days=30),
        )
        for i in range(10)
    ]
    new_cohort = [_candidate(f"NEW{i}") for i in range(10)]
    result = rebalance_membership(
        existing, new_cohort, source_version="v1", now=NOW, max_churn=5
    )
    assert result.churn_count == 5


def test_bounded_churn_prioritizes_removals_over_admissions():
    existing = [
        MembershipRecord(
            canonical_id=f"SYMBOL:OLD{i}",
            symbol=f"OLD{i}",
            source_version="v0",
            policy_version="p0",
            admitted_at=NOW - timedelta(days=30),
            effective_from=NOW - timedelta(days=30),
        )
        for i in range(10)
    ]
    new_cohort = [_candidate(f"NEW{i}") for i in range(10)]
    result = rebalance_membership(
        existing, new_cohort, source_version="v1", now=NOW, max_churn=5
    )
    assert len(result.removed) == 5
    assert len(result.admitted) == 0


def test_admission_reason_codes_are_persisted_on_the_new_record():
    result = rebalance_membership(
        [],
        [_candidate("AAPL")],
        source_version="v1",
        now=NOW,
        max_churn=10,
        admission_reason_codes_by_id={"SYMBOL:AAPL": [ELIGIBLE_ACTIVE_LIQUID]},
    )
    assert result.admitted[0].admission_reason_codes == [ELIGIBLE_ACTIVE_LIQUID]


def test_churn_count_property_matches_admitted_plus_removed():
    cohort = [_candidate("AAPL"), _candidate("MSFT")]
    result = rebalance_membership(
        [], cohort, source_version="v1", now=NOW, max_churn=10
    )
    assert result.churn_count == len(result.admitted) + len(result.removed)
