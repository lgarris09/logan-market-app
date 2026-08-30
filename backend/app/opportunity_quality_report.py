"""Operational Beta Live Supply V2, Block 9 -- a developer-readable, per-
ticker, per-signal qualification report answering "why is this card here"
and "why isn't this ticker showing" without reading logs manually.

Reuses the exact same qualification functions the real live pipeline calls
(logan_core.trigger_detection's evaluate_earnings_beat_condition/
evaluate_price_move_condition/evaluate_analyst_grade_condition) and the
same provider classes (backend/app/logan_feed.py's
_live_earnings_raw_signal/_live_price_move_raw_signal/
_live_analyst_grade_raw_signal do the identical fetch+evaluate) -- this
module never re-derives or duplicates a qualification rule, it only
reports on the same real fetch and the same real evaluation the pipeline
itself would run for each ticker, read-only (no RawSignal is constructed,
nothing is written to Memory/UserModel/the orchestrator).
"""

from dataclasses import dataclass

from logan_core.receptors.providers import (
    FmpEarningsProvider,
    FmpMarketDataProvider,
    FmpProviderError,
)
from logan_core.trigger_detection import (
    evaluate_analyst_grade_condition,
    evaluate_earnings_beat_condition,
    evaluate_price_move_condition,
)


@dataclass(frozen=True)
class SignalQualification:
    name: str
    qualified: bool
    reason: str


def _earnings_qualification(ticker: str) -> SignalQualification:
    try:
        provider = FmpEarningsProvider()
    except FmpProviderError as exc:
        return SignalQualification("Earnings", False, f"provider unavailable ({exc})")
    try:
        report = provider.fetch_latest_earnings(ticker)
    except FmpProviderError as exc:
        return SignalQualification("Earnings", False, f"fetch failed ({exc})")
    if report is None:
        return SignalQualification("Earnings", False, "no reported earnings on file")
    fired, beat_pct, reason = evaluate_earnings_beat_condition(
        report.actual_eps, report.consensus_eps
    )
    if fired:
        return SignalQualification("Earnings", True, f"{beat_pct:.2f}% EPS beat")
    return SignalQualification("Earnings", False, reason)


def _price_qualification(ticker: str) -> SignalQualification:
    try:
        provider = FmpMarketDataProvider()
    except FmpProviderError as exc:
        return SignalQualification("Price", False, f"provider unavailable ({exc})")
    try:
        quote = provider.fetch_quote(ticker)
    except FmpProviderError as exc:
        return SignalQualification("Price", False, f"fetch failed ({exc})")
    if quote is None:
        return SignalQualification("Price", False, "no quote on file")
    fired, change_pct, reason = evaluate_price_move_condition(quote.change_pct)
    if fired:
        return SignalQualification("Price", True, f"{change_pct:.2f}% move")
    return SignalQualification("Price", False, reason)


def _analyst_qualification(ticker: str) -> SignalQualification:
    try:
        provider = FmpMarketDataProvider()
    except FmpProviderError as exc:
        return SignalQualification("Analyst", False, f"provider unavailable ({exc})")
    try:
        grade = provider.fetch_latest_grade_change(ticker)
    except FmpProviderError as exc:
        return SignalQualification("Analyst", False, f"fetch failed ({exc})")
    if grade is None:
        return SignalQualification("Analyst", False, "no analyst grade on file")
    trigger_code, reason = evaluate_analyst_grade_condition(grade.action)
    if trigger_code is not None:
        return SignalQualification("Analyst", True, grade.action)
    return SignalQualification("Analyst", False, reason)


@dataclass(frozen=True)
class TickerQualityReport:
    ticker: str
    signals: list


def build_ticker_quality_report(ticker: str) -> TickerQualityReport:
    return TickerQualityReport(
        ticker=ticker,
        signals=[
            _earnings_qualification(ticker),
            _price_qualification(ticker),
            _analyst_qualification(ticker),
        ],
    )


def format_opportunity_quality_report(tickers: list) -> str:
    """The exact developer-readable table format requested: one section per
    ticker, one line per independent signal family, QUALIFIED/NOT QUALIFIED
    plus the real reason -- never a fabricated one, since every reason
    string here is the same one evaluate_*_condition already returned to
    the real pipeline (or a real provider-failure message)."""
    lines = []
    for ticker in tickers:
        report = build_ticker_quality_report(ticker)
        lines.append(report.ticker)
        for sig in report.signals:
            status = "QUALIFIED" if sig.qualified else "NOT QUALIFIED"
            lines.append(f"  {sig.name} — {status} — {sig.reason}")
        lines.append("")
    return "\n".join(lines).rstrip()
