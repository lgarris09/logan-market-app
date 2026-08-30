"""Universe Manager V1a -- backend/app real-I/O adapter
(universe_manager.py) and durable persistence (universe_store.py). Pure
decision-logic tests live in logan_core/tests/test_universe_manager.py;
this file proves the fixture-injected FMP adapter and the SQLite ledger.
"""

from datetime import datetime, timezone

from backend.app.config import universe_manager_enabled
from backend.app.universe_manager import (
    evaluate_candidate_eligibility,
    monitored_tickers,
    reset_universe_manager_state,
    run_universe_reevaluation,
)
from backend.app.universe_store import UniverseMembershipStore
from logan_core.contracts import CandidateSecurity, MembershipRecord
from logan_core.receptors.providers import (
    CompanyProfile,
    EarningsReport,
    FixtureEarningsProvider,
    FixtureMarketDataProvider,
    FmpProviderError,
    GradeChange,
    Quote,
)
from logan_core.universe.eligibility import (
    ELIGIBLE_ACTIVE_LIQUID,
    PARTIAL_SIGNAL_COVERAGE,
    REJECT_DATA_HEALTH,
    REJECT_INSUFFICIENT_LIQUIDITY,
    REJECT_TRADING_INACTIVE,
)

NOW = datetime.now(timezone.utc)


def _candidate(symbol="AAPL", sector="Technology") -> CandidateSecurity:
    return CandidateSecurity(
        canonical_id=f"SYMBOL:{symbol}", symbol=symbol, sector=sector
    )


def _quote(symbol: str, price: float = 100.0) -> Quote:
    return Quote(
        entity_id=symbol,
        price=price,
        previous_close=price * 0.99,
        change_pct=1.0,
        quote_timestamp=NOW,
        source_id="fixture",
        source_name="fixture",
    )


def _profile(symbol: str, average_volume: float = 1_000_000.0) -> CompanyProfile:
    return CompanyProfile(
        entity_id=symbol,
        sector="Technology",
        industry="Software",
        average_volume=average_volume,
        beta=1.1,
        source_id="fixture",
        source_name="fixture",
    )


def _earnings(symbol: str) -> EarningsReport:
    return EarningsReport(
        entity_id=symbol,
        actual_eps=1.0,
        consensus_eps=0.9,
        fiscal_quarter="Q2 2026",
        guidance_revised=False,
        guidance_delta_pct=0.0,
        report_timestamp=NOW,
        source_id="fixture",
        source_name="fixture",
    )


def _grade(symbol: str) -> GradeChange:
    return GradeChange(
        entity_id=symbol,
        grading_firm="Fixture Analytics",
        previous_rating="Hold",
        new_rating="Buy",
        action="upgrade",
        action_date=NOW,
        source_id="fixture",
        source_name="fixture",
    )


# --- config gating -----------------------------------------------------------


def test_universe_manager_defaults_to_disabled(monkeypatch):
    monkeypatch.delenv("STRATUS_UNIVERSE_MANAGER_ENABLED", raising=False)
    assert universe_manager_enabled() is False


def test_universe_manager_can_be_explicitly_enabled(monkeypatch):
    monkeypatch.setenv("STRATUS_UNIVERSE_MANAGER_ENABLED", "true")
    assert universe_manager_enabled() is True


# --- evaluate_candidate_eligibility (real-shaped fixture I/O) ---------------


def test_healthy_candidate_with_full_coverage_is_eligible():
    market = FixtureMarketDataProvider(
        quotes={"AAPL": _quote("AAPL")},
        grade_changes={"AAPL": _grade("AAPL")},
        profiles={"AAPL": _profile("AAPL", average_volume=1_000_000.0)},
    )
    earnings = FixtureEarningsProvider(reports={"AAPL": _earnings("AAPL")})
    result = evaluate_candidate_eligibility(
        _candidate("AAPL"),
        market_data_provider=market,
        earnings_provider=earnings,
        now=NOW,
    )
    assert result.eligible is True
    assert result.reason_codes == [ELIGIBLE_ACTIVE_LIQUID]


def test_clean_missing_quote_is_trading_inactive_not_data_health():
    """No exception, just nothing on file for this symbol -- the honest
    "possibly delisted/invalid symbol" signal this codebase's Quote
    contract supports, distinct from a genuine provider failure."""
    market = FixtureMarketDataProvider()
    earnings = FixtureEarningsProvider(reports={})
    result = evaluate_candidate_eligibility(
        _candidate("AAPL"),
        market_data_provider=market,
        earnings_provider=earnings,
        now=NOW,
    )
    assert result.eligible is False
    assert result.reason_codes == [REJECT_TRADING_INACTIVE]


def test_genuine_provider_failure_is_a_data_health_rejection():
    class _RaisingMarketData:
        def fetch_quote(self, entity_id):
            raise FmpProviderError("simulated network failure", status_code=500)

        def fetch_company_profile(self, entity_id):
            return None

        def fetch_latest_grade_change(self, entity_id):
            return None

    earnings = FixtureEarningsProvider(reports={})
    result = evaluate_candidate_eligibility(
        _candidate("AAPL"),
        market_data_provider=_RaisingMarketData(),
        earnings_provider=earnings,
        now=NOW,
    )
    assert result.eligible is False
    assert result.reason_codes == [REJECT_DATA_HEALTH]


def test_missing_earnings_and_grade_coverage_is_partial_not_rejected():
    market = FixtureMarketDataProvider(
        quotes={"AAPL": _quote("AAPL")},
        profiles={"AAPL": _profile("AAPL", average_volume=1_000_000.0)},
    )
    earnings = FixtureEarningsProvider(reports={})
    result = evaluate_candidate_eligibility(
        _candidate("AAPL"),
        market_data_provider=market,
        earnings_provider=earnings,
        now=NOW,
    )
    assert result.eligible is True
    assert PARTIAL_SIGNAL_COVERAGE in result.reason_codes


def test_low_average_volume_is_insufficient_liquidity():
    market = FixtureMarketDataProvider(
        quotes={"AAPL": _quote("AAPL", price=10.0)},
        profiles={"AAPL": _profile("AAPL", average_volume=1.0)},
        grade_changes={"AAPL": _grade("AAPL")},
    )
    earnings = FixtureEarningsProvider(reports={"AAPL": _earnings("AAPL")})
    result = evaluate_candidate_eligibility(
        _candidate("AAPL"),
        market_data_provider=market,
        earnings_provider=earnings,
        now=NOW,
    )
    assert result.eligible is False
    assert result.reason_codes == [REJECT_INSUFFICIENT_LIQUIDITY]


# --- run_universe_reevaluation end-to-end -------------------------------------


def test_reevaluation_selects_a_cohort_from_healthy_fixture_candidates(monkeypatch):
    monkeypatch.delenv("STRATUS_PERSIST_MEMORY", raising=False)

    from logan_core.universe.candidate_source import load_candidate_snapshot

    snapshot = load_candidate_snapshot()
    quotes = {s.symbol: _quote(s.symbol) for s in snapshot.securities}
    profiles = {
        s.symbol: _profile(s.symbol, average_volume=1_000_000.0)
        for s in snapshot.securities
    }
    grades = {s.symbol: _grade(s.symbol) for s in snapshot.securities}
    earnings_reports = {s.symbol: _earnings(s.symbol) for s in snapshot.securities}

    market = FixtureMarketDataProvider(
        quotes=quotes, grade_changes=grades, profiles=profiles
    )
    earnings = FixtureEarningsProvider(reports=earnings_reports)

    result = run_universe_reevaluation(
        market_data_provider=market, earnings_provider=earnings, now=NOW
    )
    assert 25 <= len(result.admitted) <= 35
    assert result.removed == []


def test_reevaluation_with_persistence_enabled_round_trips_through_the_store(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv("STRATUS_UNIVERSE_DB_PATH", str(tmp_path / "universe.db"))
    reset_universe_manager_state()

    from logan_core.universe.candidate_source import load_candidate_snapshot

    snapshot = load_candidate_snapshot()
    quotes = {s.symbol: _quote(s.symbol) for s in snapshot.securities}
    profiles = {
        s.symbol: _profile(s.symbol, average_volume=1_000_000.0)
        for s in snapshot.securities
    }
    grades = {s.symbol: _grade(s.symbol) for s in snapshot.securities}
    earnings_reports = {s.symbol: _earnings(s.symbol) for s in snapshot.securities}
    market = FixtureMarketDataProvider(
        quotes=quotes, grade_changes=grades, profiles=profiles
    )
    earnings = FixtureEarningsProvider(reports=earnings_reports)

    run_universe_reevaluation(
        market_data_provider=market, earnings_provider=earnings, now=NOW
    )
    tickers = monitored_tickers()
    assert 25 <= len(tickers) <= 35

    reset_universe_manager_state()  # simulates a process restart
    assert monitored_tickers() == tickers


def test_monitored_tickers_is_empty_when_persistence_disabled(monkeypatch):
    monkeypatch.delenv("STRATUS_PERSIST_MEMORY", raising=False)
    reset_universe_manager_state()
    assert monitored_tickers() == ()


# --- UniverseMembershipStore ---------------------------------------------------


def test_store_admission_and_load_open_round_trip(tmp_path):
    store = UniverseMembershipStore(str(tmp_path / "universe.db"))
    record = MembershipRecord(
        canonical_id="SYMBOL:AAPL",
        symbol="AAPL",
        source_version="v1",
        policy_version="p1",
        admission_reason_codes=[ELIGIBLE_ACTIVE_LIQUID],
        admitted_at=NOW,
        effective_from=NOW,
    )
    store.save_admission(record)
    open_records = store.load_open()
    assert len(open_records) == 1
    assert open_records[0].canonical_id == "SYMBOL:AAPL"
    assert open_records[0].admission_reason_codes == [ELIGIBLE_ACTIVE_LIQUID]
    store.close()


def test_store_removal_closes_the_record_but_keeps_it_in_load_all(tmp_path):
    store = UniverseMembershipStore(str(tmp_path / "universe.db"))
    record = MembershipRecord(
        canonical_id="SYMBOL:AAPL",
        symbol="AAPL",
        source_version="v1",
        policy_version="p1",
        admitted_at=NOW,
        effective_from=NOW,
    )
    store.save_admission(record)
    closed = record.model_copy(
        update={"effective_until": NOW, "removed_at": NOW, "removal_reason": "TEST"}
    )
    store.save_removal(closed)

    assert store.load_open() == []
    all_records = store.load_all()
    assert len(all_records) == 1
    assert all_records[0].removal_reason == "TEST"
    store.close()


def test_store_survives_a_simulated_restart(tmp_path):
    db_path = str(tmp_path / "universe.db")
    store = UniverseMembershipStore(db_path)
    store.save_admission(
        MembershipRecord(
            canonical_id="SYMBOL:AAPL",
            symbol="AAPL",
            source_version="v1",
            policy_version="p1",
            admitted_at=NOW,
            effective_from=NOW,
        )
    )
    store.close()

    reopened = UniverseMembershipStore(db_path)
    assert len(reopened.load_open()) == 1
    reopened.close()


def test_store_clear_removes_all_history(tmp_path):
    store = UniverseMembershipStore(str(tmp_path / "universe.db"))
    store.save_admission(
        MembershipRecord(
            canonical_id="SYMBOL:AAPL",
            symbol="AAPL",
            source_version="v1",
            policy_version="p1",
            admitted_at=NOW,
            effective_from=NOW,
        )
    )
    store.clear()
    assert store.load_all() == []
    store.close()
