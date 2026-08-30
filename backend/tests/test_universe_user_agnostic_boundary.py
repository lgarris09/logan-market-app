"""Universe Manager V1a Block 15 -- the hard boundary: universe eligibility,
monitoring, and provider scheduling are entirely user-agnostic. Personal
Learning may change relevance, Attention Field selection, Ask explanation,
resurfacing, and future notification decisions -- it must never change the
monitored cohort, polling frequency, provider queue priority, signal
qualification, or evidence freshness rules.

Two proofs: a structural one (none of Universe Manager's own functions
even accept a user_id/personalization input at all -- the boundary is
enforced by the API shape itself, not by a runtime check that could be
bypassed) and a behavioral one (a real Watch for one user has zero effect
on the monitored cohort a reevaluation run produces).
"""

import inspect
from datetime import datetime, timezone

from backend.app.universe_manager import (
    evaluate_candidate_eligibility,
    monitored_tickers,
    reset_universe_manager_state,
    run_universe_reevaluation,
)
from backend.app.watch import create_watch, reset_watch_state
from logan_core.receptors.providers import (
    CompanyProfile,
    EarningsReport,
    FixtureEarningsProvider,
    FixtureMarketDataProvider,
    GradeChange,
    Quote,
)
from logan_core.universe import (
    evaluate_eligibility,
    select_monitored_cohort,
)
from logan_core.universe.candidate_source import load_candidate_snapshot
from logan_core.universe.membership_ledger import rebalance_membership

NOW = datetime.now(timezone.utc)


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


# --- structural proof ---------------------------------------------------------


def test_no_universe_manager_function_accepts_a_user_identity():
    """None of Block 2-7's real entry points even have a parameter that
    could carry a user_id, holdings, interests, Watch state, or engagement
    telemetry -- the boundary is a fact about the function signatures
    themselves, not a runtime check that a future caller could route
    around."""
    functions = [
        evaluate_eligibility,
        select_monitored_cohort,
        rebalance_membership,
        evaluate_candidate_eligibility,
        run_universe_reevaluation,
    ]
    disallowed_substrings = (
        "user",
        "watch",
        "holding",
        "interest",
        "engagement",
        "learn",
    )
    for fn in functions:
        params = inspect.signature(fn).parameters
        for name in params:
            lowered = name.lower()
            assert not any(bad in lowered for bad in disallowed_substrings), (
                f"{fn.__name__} has a parameter ({name}) that looks "
                "user-specific -- Universe Manager must stay user-agnostic"
            )


# --- behavioral proof ----------------------------------------------------------


def test_a_users_watch_never_changes_the_monitored_cohort(monkeypatch):
    monkeypatch.delenv("STRATUS_PERSIST_MEMORY", raising=False)
    reset_universe_manager_state()
    reset_watch_state()

    snapshot = load_candidate_snapshot()
    quotes = {s.symbol: _quote(s.symbol) for s in snapshot.securities}
    profiles = {s.symbol: _profile(s.symbol) for s in snapshot.securities}
    grades = {s.symbol: _grade(s.symbol) for s in snapshot.securities}
    earnings_reports = {s.symbol: _earnings(s.symbol) for s in snapshot.securities}
    market = FixtureMarketDataProvider(
        quotes=quotes, grade_changes=grades, profiles=profiles
    )
    earnings = FixtureEarningsProvider(reports=earnings_reports)

    before = run_universe_reevaluation(
        market_data_provider=market, earnings_provider=earnings, now=NOW
    )
    before_symbols = {c.symbol for c in before.admitted}

    # A real user watches a ticker with no bearing on universe membership
    # (this alone must never make it "more eligible" or "more monitored").
    create_watch("some-real-user", "AAPL")

    after = run_universe_reevaluation(
        market_data_provider=market, earnings_provider=earnings, now=NOW
    )
    after_symbols = {c.symbol for c in after.admitted}

    # The exact same deterministic cohort is admitted again -- the Watch
    # created in between had zero bearing on the computation.
    assert before_symbols == after_symbols
    assert after.removed == []


def test_monitored_tickers_output_is_identical_regardless_of_which_user_asks(
    monkeypatch,
):
    """monitored_tickers() itself takes no user_id at all -- there is no
    per-user view of the monitored universe to diverge in the first place."""
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    params = inspect.signature(monitored_tickers).parameters
    assert len(params) == 0
