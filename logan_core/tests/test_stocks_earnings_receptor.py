"""Sprint 3.6.6 — Phase 8 receptor/provider tests: maps a provider-shaped
EarningsReport into STRATUS-owned RawSignal without leaking provider
structure downstream, and without fabricating fields the provider omitted.
"""

from datetime import datetime, timezone

from logan_core.contracts import RawSignal
from logan_core.receptors import earnings_report_to_raw_signal
from logan_core.receptors.providers import (
    FIXTURE_SOURCE_ID,
    FIXTURE_SOURCE_NAME,
    EarningsReport,
    nvda_earnings_beat_fixture,
)


def _raw_value(raw: RawSignal) -> dict:
    # raw_value is typed `object` on the shared RawSignal contract (every
    # receptor's payload shape differs); earnings_report_to_raw_signal always
    # builds a dict, so narrow it here rather than indexing `object` directly.
    assert isinstance(raw.raw_value, dict)
    return raw.raw_value


def test_maps_full_report_into_raw_signal_contract():
    report = nvda_earnings_beat_fixture()
    raw = earnings_report_to_raw_signal(report)
    raw_value = _raw_value(raw)

    assert raw.domain == "stocks"
    assert raw.source_id == FIXTURE_SOURCE_ID
    assert raw.source_name == FIXTURE_SOURCE_NAME
    assert raw_value["entity_id"] == "NVDA"
    assert raw_value["entity_type"] == "ticker"
    assert raw_value["signal_type"] == "earnings_signal"
    assert raw_value["actual_eps"] == report.actual_eps
    assert raw_value["consensus_eps"] == report.consensus_eps
    assert raw_value["fiscal_quarter"] == report.fiscal_quarter
    # The human-readable summary must be built from the real numbers, not a
    # hand-authored/fabricated sentence.
    assert str(report.actual_eps) in raw_value["value"]
    assert str(report.consensus_eps) in raw_value["value"]


def test_never_fabricates_omitted_optional_fields():
    report = EarningsReport(
        entity_id="NVDA",
        actual_eps=1.05,
        consensus_eps=0.98,
        # fiscal_quarter / guidance_revised / guidance_delta_pct
        # deliberately omitted -- provider didn't supply them.
        report_timestamp=datetime(2026, 8, 14, tzinfo=timezone.utc),
        source_id=FIXTURE_SOURCE_ID,
        source_name=FIXTURE_SOURCE_NAME,
    )
    raw_value = _raw_value(earnings_report_to_raw_signal(report))

    assert "fiscal_quarter" not in raw_value
    assert "guidance_revised" not in raw_value
    assert "guidance_delta_pct" not in raw_value


def test_missing_eps_produces_generic_truthful_summary():
    report = EarningsReport(
        entity_id="NVDA",
        report_timestamp=datetime(2026, 8, 14, tzinfo=timezone.utc),
        source_id=FIXTURE_SOURCE_ID,
        source_name=FIXTURE_SOURCE_NAME,
    )
    raw_value = _raw_value(earnings_report_to_raw_signal(report))
    assert raw_value["actual_eps"] is None
    assert raw_value["consensus_eps"] is None
    # No invented EPS numbers in the summary when the provider has none.
    assert raw_value["value"] == "NVDA earnings report received"
