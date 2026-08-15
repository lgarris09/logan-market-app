from datetime import datetime, timezone
from typing import Optional

from .base import EarningsReport

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


__all__: list[str] = [
    "FixtureEarningsProvider",
    "nvda_earnings_beat_fixture",
    "FIXTURE_SOURCE_ID",
    "FIXTURE_SOURCE_NAME",
]
