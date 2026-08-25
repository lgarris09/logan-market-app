from datetime import datetime, timezone
from typing import Optional

from .base import CompanyProfile, EarningsReport, GradeChange, Quote

# Explicit, unmistakable marker for anything sourced from this provider --
# Phase 4 instruction: "never quietly fall back to simulated data while
# presenting it as live." Callers/tests should assert on this source_id, not
# on "not equal to a real-sounding name," to keep that distinction load-bearing
# rather than implicit.
FIXTURE_SOURCE_ID = "fixture_earnings_provider"
FIXTURE_SOURCE_NAME = "STRATUS Test Fixture (not live data)"


class FixtureEarningsProvider:
    """Deterministic, in-repo earnings data -- explicitly NOT live. Exists so
    the trigger-detection -> TriggerEvent -> pipeline integration can be
    proven end-to-end (Phase 8's pipeline integration test) before real
    provider credentials exist, without ever letting that proof be mistaken
    for a live result (FIXTURE_SOURCE_ID/FIXTURE_SOURCE_NAME above make the
    distinction visible in every RawSignal/TriggerEvent this produces, not
    just in this class's name).

    Implements the same EarningsProvider Protocol a real provider would, so
    swapping this for a live one later touches only the provider construction
    call site -- nothing in trigger_detection/, world_model/, evidence_trust/,
    or conclusion_confidence/ needs to change.
    """

    def __init__(self, reports: dict[str, EarningsReport]) -> None:
        self._reports = reports

    def fetch_latest_earnings(self, entity_id: str) -> Optional[EarningsReport]:
        return self._reports.get(entity_id)


def nvda_earnings_beat_fixture() -> EarningsReport:
    """The Phase 8 positive-fire fixture: a qualifying NVIDIA earnings beat
    (beat_pct well above the 5.0 threshold). Deterministic and fixed -- not
    randomized, not derived from any live source. See
    trigger_detection/stocks.py's evaluate_earnings_beat_condition() for the
    fire condition this is designed to satisfy.
    """
    return EarningsReport(
        entity_id="NVDA",
        actual_eps=1.05,
        consensus_eps=0.98,
        fiscal_quarter="Q2 2026",
        guidance_revised=True,
        guidance_delta_pct=6.7,
        report_timestamp=datetime(2026, 8, 14, 20, 0, 0, tzinfo=timezone.utc),
        source_id=FIXTURE_SOURCE_ID,
        source_name=FIXTURE_SOURCE_NAME,
    )


class FixtureMarketDataProvider:
    """Sprint 3.6.7 -- deterministic, in-repo quote/grade-change data,
    explicitly NOT live. Same role as FixtureEarningsProvider: proves the
    trigger-detection -> pipeline integration for the new price-move/
    analyst-grade signal types before/alongside real provider verification,
    never mistaken for a live result (FIXTURE_SOURCE_ID/NAME below).
    Implements the same QuoteProvider/AnalystGradesProvider Protocols a real
    provider would.
    """

    def __init__(
        self,
        quotes: Optional[dict[str, Quote]] = None,
        grade_changes: Optional[dict[str, GradeChange]] = None,
        profiles: Optional[dict[str, CompanyProfile]] = None,
    ) -> None:
        self._quotes = quotes or {}
        self._grade_changes = grade_changes or {}
        self._profiles = profiles or {}

    def fetch_quote(self, entity_id: str) -> Optional[Quote]:
        return self._quotes.get(entity_id)

    def fetch_latest_grade_change(self, entity_id: str) -> Optional[GradeChange]:
        return self._grade_changes.get(entity_id)

    def fetch_company_profile(self, entity_id: str) -> Optional[CompanyProfile]:
        """Stock Opportunity Logic V2.2 -- deterministic, in-repo profile
        data, explicitly NOT live. Same role/discipline as the two methods
        above."""
        return self._profiles.get(entity_id)


def nvda_price_move_up_fixture() -> Quote:
    """A qualifying significant price move (change_pct well above the 5.0
    threshold) -- see trigger_detection/stocks.py's
    evaluate_price_move_condition()."""
    return Quote(
        entity_id="NVDA",
        price=127.27,
        previous_close=118.50,
        change_pct=7.4,
        quote_timestamp=datetime(2026, 8, 21, 20, 0, 0, tzinfo=timezone.utc),
        source_id=FIXTURE_SOURCE_ID,
        source_name=FIXTURE_SOURCE_NAME,
    )


def nvda_price_move_down_fixture() -> Quote:
    """A qualifying significant negative price move."""
    return Quote(
        entity_id="NVDA",
        price=109.80,
        previous_close=118.50,
        change_pct=-7.34,
        quote_timestamp=datetime(2026, 8, 21, 20, 0, 0, tzinfo=timezone.utc),
        source_id=FIXTURE_SOURCE_ID,
        source_name=FIXTURE_SOURCE_NAME,
    )


def nvda_no_significant_move_fixture() -> Quote:
    """An ordinary trading day -- change_pct well below the 5.0 threshold,
    must not fire STOCK_PRICE_MOVE_SIGNIFICANT."""
    return Quote(
        entity_id="NVDA",
        price=119.10,
        previous_close=118.50,
        change_pct=0.51,
        quote_timestamp=datetime(2026, 8, 21, 20, 0, 0, tzinfo=timezone.utc),
        source_id=FIXTURE_SOURCE_ID,
        source_name=FIXTURE_SOURCE_NAME,
    )


def nvda_analyst_upgrade_fixture() -> GradeChange:
    """A qualifying analyst upgrade -- see trigger_detection/stocks.py's
    evaluate_analyst_grade_condition()."""
    return GradeChange(
        entity_id="NVDA",
        grading_firm="Fixture Capital",
        previous_rating="Hold",
        new_rating="Buy",
        action="upgrade",
        action_date=datetime(2026, 8, 21, tzinfo=timezone.utc),
        source_id=FIXTURE_SOURCE_ID,
        source_name=FIXTURE_SOURCE_NAME,
    )


def nvda_analyst_downgrade_fixture() -> GradeChange:
    """A qualifying analyst downgrade."""
    return GradeChange(
        entity_id="NVDA",
        grading_firm="Fixture Capital",
        previous_rating="Buy",
        new_rating="Hold",
        action="downgrade",
        action_date=datetime(2026, 8, 21, tzinfo=timezone.utc),
        source_id=FIXTURE_SOURCE_ID,
        source_name=FIXTURE_SOURCE_NAME,
    )


def nvda_analyst_maintain_fixture() -> GradeChange:
    """A rating reaffirmation, not a change -- must not fire either analyst
    trigger code."""
    return GradeChange(
        entity_id="NVDA",
        grading_firm="Fixture Capital",
        previous_rating="Buy",
        new_rating="Buy",
        action="maintain",
        action_date=datetime(2026, 8, 21, tzinfo=timezone.utc),
        source_id=FIXTURE_SOURCE_ID,
        source_name=FIXTURE_SOURCE_NAME,
    )


__all__: list[str] = [
    "FixtureEarningsProvider",
    "nvda_earnings_beat_fixture",
    "FixtureMarketDataProvider",
    "nvda_price_move_up_fixture",
    "nvda_price_move_down_fixture",
    "nvda_no_significant_move_fixture",
    "nvda_analyst_upgrade_fixture",
    "nvda_analyst_downgrade_fixture",
    "nvda_analyst_maintain_fixture",
    "FIXTURE_SOURCE_ID",
    "FIXTURE_SOURCE_NAME",
]
