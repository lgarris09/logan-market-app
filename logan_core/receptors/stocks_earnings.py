from logan_core.contracts import RawSignal

from .providers.base import EarningsReport


def _truthful_summary(report: EarningsReport) -> str:
    """Builds the human-readable RawSignal.raw_value['value'] string from only
    the fields the provider actually supplied -- no invented guidance/market-
    reaction/analyst commentary (Phase 7 instruction). Mirrors
    SimulatedReceptor's fixtures in *shape* (a short declarative sentence)
    but every number here is real, provider-sourced data, not a hand-authored
    demo string.
    """
    if report.actual_eps is None or report.consensus_eps is None:
        return f"{report.entity_id} earnings report received"
    return (
        f"{report.entity_id} reported EPS of {report.actual_eps} "
        f"vs. consensus {report.consensus_eps}"
    )


def earnings_report_to_raw_signal(report: EarningsReport) -> RawSignal:
    """The stocks-earnings receptor (Layer 1): maps a provider-shaped
    EarningsReport (see providers/base.py) into the same RawSignal contract
    every other receptor already produces. This is the one place
    provider-specific structure ends -- normalization, world_model, and
    every downstream layer consume raw_value's dict exactly as they already
    do for SimulatedReceptor's fixtures (entity_id/entity_type/signal_type/
    value/unit), with the earnings-specific numeric fields
    (actual_eps/consensus_eps/fiscal_quarter/guidance_*) present alongside
    them for trigger_detection/stocks.py to read -- Normalizer itself is
    unmodified and still only extracts the five fields it already knows
    about (see normalization/normalize.py), so this never risks that layer's
    behavior for any other receptor.
    """
    raw_value: dict = {
        "entity_id": report.entity_id,
        "entity_type": "ticker",
        "signal_type": "earnings_signal",
        "value": _truthful_summary(report),
        "unit": None,
        "actual_eps": report.actual_eps,
        "consensus_eps": report.consensus_eps,
    }
    if report.fiscal_quarter is not None:
        raw_value["fiscal_quarter"] = report.fiscal_quarter
    if report.guidance_revised is not None:
        raw_value["guidance_revised"] = report.guidance_revised
    if report.guidance_delta_pct is not None:
        raw_value["guidance_delta_pct"] = report.guidance_delta_pct

    return RawSignal(
        domain="stocks",
        source_id=report.source_id,
        source_name=report.source_name,
        raw_value=raw_value,
        captured_at=report.report_timestamp,
    )
