from logan_core.contracts import RawSignal

from .providers.base import GradeChange, Quote


def _truthful_quote_summary(quote: Quote) -> str:
    """Mirrors stocks_earnings.py's _truthful_summary: only fields the
    provider actually supplied, no invented commentary."""
    direction = "up" if quote.change_pct >= 0 else "down"
    return (
        f"{quote.entity_id} is {direction} {abs(quote.change_pct):.2f}% "
        f"to {quote.price} (previous close {quote.previous_close})"
    )


def quote_to_raw_signal(quote: Quote) -> RawSignal:
    """The stocks-market-data receptor (Layer 1, Sprint 3.6.7): maps a
    provider-shaped Quote into the same RawSignal contract every other
    receptor already produces, using the existing registered "price_change"
    signal_type (logan_core/normalization/normalize.py's SIGNAL_TYPE_REGISTRY
    already listed this for stocks -- no normalization contract change
    needed). Normalizer itself is unmodified; this is the one place
    provider-specific structure ends, exactly like earnings_report_to_raw_signal.
    """
    raw_value: dict = {
        "entity_id": quote.entity_id,
        "entity_type": "ticker",
        "signal_type": "price_change",
        "value": _truthful_quote_summary(quote),
        "unit": "percent",
        "price": quote.price,
        "previous_close": quote.previous_close,
        "change_pct": quote.change_pct,
    }
    return RawSignal(
        domain="stocks",
        source_id=quote.source_id,
        source_name=quote.source_name,
        raw_value=raw_value,
        captured_at=quote.quote_timestamp,
    )


def _truthful_grade_summary(grade: GradeChange) -> str:
    rating_change = (
        f"{grade.previous_rating} to {grade.new_rating}"
        if grade.previous_rating and grade.new_rating
        else grade.new_rating or "a new rating"
    )
    return (
        f"{grade.grading_firm} rated {grade.entity_id} {rating_change} "
        f"(action: {grade.action})"
    )


def grade_change_to_raw_signal(grade: GradeChange) -> RawSignal:
    """The stocks-analyst-grade receptor (Layer 1, Sprint 3.6.7): maps a
    provider-shaped GradeChange into RawSignal using the existing registered
    "analyst_change" signal_type -- again, no normalization contract change
    needed.
    """
    raw_value: dict = {
        "entity_id": grade.entity_id,
        "entity_type": "ticker",
        "signal_type": "analyst_change",
        "value": _truthful_grade_summary(grade),
        "unit": None,
        "grading_firm": grade.grading_firm,
        "action": grade.action,
    }
    if grade.previous_rating is not None:
        raw_value["previous_rating"] = grade.previous_rating
    if grade.new_rating is not None:
        raw_value["new_rating"] = grade.new_rating

    return RawSignal(
        domain="stocks",
        source_id=grade.source_id,
        source_name=grade.source_name,
        raw_value=raw_value,
        captured_at=grade.action_date,
    )
