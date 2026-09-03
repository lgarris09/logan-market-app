"""Universe Manager V1a Blocks 17/19 -- the developer-readable universe
report (backend/app/universe_report.py) and GET /v1/dev/universe-report.
"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.universe_manager import (
    reset_universe_manager_state,
    run_universe_reevaluation,
)
from backend.app.universe_operational_observations import (
    reset_operational_observation_state,
)
from backend.app.universe_report import build_universe_report
from backend.app.universe_telemetry import reset_universe_telemetry_state
from logan_core.receptors.providers import (
    CompanyProfile,
    EarningsReport,
    FixtureEarningsProvider,
    FixtureMarketDataProvider,
    GradeChange,
    Quote,
)
from logan_core.universe.candidate_source import load_candidate_snapshot

client = TestClient(app)
NOW = datetime.now(timezone.utc)


def _quote(symbol: str) -> Quote:
    return Quote(
        entity_id=symbol,
        price=100.0,
        previous_close=99.0,
        change_pct=1.0,
        quote_timestamp=NOW,
        source_id="fixture",
        source_name="fixture",
    )


def _profile(symbol: str) -> CompanyProfile:
    return CompanyProfile(
        entity_id=symbol,
        sector="Technology",
        industry="Software",
        average_volume=1_000_000.0,
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


def test_report_includes_universe_provider_exploration_and_diagnostics_sections():
    report = build_universe_report()
    assert "Universe" in report
    assert "Provider" in report
    assert "Exploration" in report
    assert "Diagnostics" in report


def test_report_truthfully_reflects_exploration_wiring(monkeypatch):
    """V1a ITERATE block, Phase 5 correctness fix: this report used to
    claim Controlled Exploration was "not yet wired into the live per-user
    feed-assembly path," which became false once commit 3d6f05f wired
    apply_exploration_placement() into logan_feed.py. The report must say
    it IS wired, and must never fabricate a nonzero placement count when
    persistence is off / nothing has run today."""
    monkeypatch.delenv("STRATUS_PERSIST_MEMORY", raising=False)
    report = build_universe_report()
    assert "not yet wired" not in report
    assert "live-wired into the per-user feed path" in report
    assert "no real observations recorded yet today" in report


def test_report_reflects_candidate_source_metadata():
    snapshot = load_candidate_snapshot()
    report = build_universe_report()
    assert snapshot.source_version in report
    assert str(len(snapshot.securities)) in report


def test_report_reflects_real_monitored_cohort_when_persistence_enabled(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv("STRATUS_UNIVERSE_DB_PATH", str(tmp_path / "universe.db"))
    monkeypatch.setenv(
        "STRATUS_UNIVERSE_TELEMETRY_DB_PATH", str(tmp_path / "telemetry.db")
    )
    monkeypatch.setenv(
        "STRATUS_OPERATIONAL_OBSERVATION_DB_PATH",
        str(tmp_path / "operational_observations.db"),
    )
    reset_universe_manager_state()
    reset_universe_telemetry_state()
    reset_operational_observation_state()

    snapshot = load_candidate_snapshot()
    quotes = {s.symbol: _quote(s.symbol) for s in snapshot.securities}
    profiles = {s.symbol: _profile(s.symbol) for s in snapshot.securities}
    grades = {s.symbol: _grade(s.symbol) for s in snapshot.securities}
    earnings_reports = {s.symbol: _earnings(s.symbol) for s in snapshot.securities}
    market = FixtureMarketDataProvider(
        quotes=quotes, grade_changes=grades, profiles=profiles
    )
    earnings = FixtureEarningsProvider(reports=earnings_reports)

    run_universe_reevaluation(
        market_data_provider=market, earnings_provider=earnings, now=NOW
    )
    report = build_universe_report()
    assert "monitored count: " in report
    assert "sector representation:" in report
    assert "historical admissions:" in report


def test_report_shows_scheduler_disabled_and_no_job_state_by_default(monkeypatch):
    monkeypatch.delenv("STRATUS_UNIVERSE_SCHEDULER_ENABLED", raising=False)
    monkeypatch.delenv("STRATUS_UNIVERSE_MANAGER_ENABLED", raising=False)
    monkeypatch.delenv("STRATUS_PERSIST_MEMORY", raising=False)
    report = build_universe_report()
    assert "runtime invocation: disabled" in report
    assert "live-feed consumption: disabled" in report
    assert "reevaluation job state: unavailable" in report


def test_report_shows_real_scheduler_job_state_when_persisted(monkeypatch, tmp_path):
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv("STRATUS_UNIVERSE_DB_PATH", str(tmp_path / "universe.db"))
    monkeypatch.setenv("STRATUS_UNIVERSE_SCHEDULER_DB_PATH", str(tmp_path / "sched.db"))
    monkeypatch.setenv(
        "STRATUS_UNIVERSE_TELEMETRY_DB_PATH", str(tmp_path / "telemetry.db")
    )
    monkeypatch.setenv(
        "STRATUS_OPERATIONAL_OBSERVATION_DB_PATH",
        str(tmp_path / "operational_observations.db"),
    )
    reset_universe_manager_state()
    reset_universe_telemetry_state()
    reset_operational_observation_state()

    from logan_core.universe.candidate_source import load_candidate_snapshot as _lcs

    snapshot = _lcs()
    quotes = {s.symbol: _quote(s.symbol) for s in snapshot.securities}
    profiles = {s.symbol: _profile(s.symbol) for s in snapshot.securities}
    grades = {s.symbol: _grade(s.symbol) for s in snapshot.securities}
    earnings_reports = {s.symbol: _earnings(s.symbol) for s in snapshot.securities}
    market = FixtureMarketDataProvider(
        quotes=quotes, grade_changes=grades, profiles=profiles
    )
    earnings = FixtureEarningsProvider(reports=earnings_reports)

    from backend.app.universe_manager import run_scheduled_universe_reevaluation

    run_scheduled_universe_reevaluation(
        market_data_provider=market, earnings_provider=earnings, now=NOW
    )

    report = build_universe_report()
    assert "last_outcome='success'" in report


def test_report_never_claims_a_completed_expansion_proof_without_real_data(
    monkeypatch,
):
    monkeypatch.delenv("STRATUS_PERSIST_MEMORY", raising=False)
    report = build_universe_report()
    assert "expansion-review status: INSUFFICIENT_OBSERVATION_WINDOW" in report
    assert "0 of 14 required consecutive real calendar days" in report


def test_report_shows_ready_proof_window_after_final_closeout(monkeypatch):
    """V1a Final Proof-Readiness Closeout: all 18 fields now have a
    confirmed, currently-wired real source, so readiness is wiring-only and
    reports YES regardless of whether persistence/data exists in this
    process -- never a fabricated NO left over from the prior closeout's 1
    permanently-unconfirmed field."""
    monkeypatch.delenv("STRATUS_PERSIST_MEMORY", raising=False)
    report = build_universe_report()
    assert "PROOF_INPUTS_CONFIRMED_REAL: 18 of 18" in report
    assert "READY_TO_START_14_DAY_WINDOW: YES" in report
    assert "permanently-unconfirmed" not in report


def test_route_returns_a_report_string():
    response = client.get("/v1/dev/universe-report")
    assert response.status_code == 200
    body = response.json()
    assert "report" in body
    assert "Universe" in body["report"]


def test_route_never_leaks_a_key():
    import os

    old = os.environ.get("FMP_API_KEY")
    os.environ["FMP_API_KEY"] = "totally-real-secret-key-value"
    try:
        response = client.get("/v1/dev/universe-report")
        assert "totally-real-secret-key-value" not in response.text
    finally:
        if old is not None:
            os.environ["FMP_API_KEY"] = old
        else:
            os.environ.pop("FMP_API_KEY", None)
