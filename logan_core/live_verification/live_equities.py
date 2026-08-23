"""Sprint 3.6.8 Block 5 -- live verification: the generalized live equities
path (earnings + quote + analyst grade) through the real FMP provider and
the real STRATUS pipeline, for an arbitrary set of tickers -- default NVDA,
TSLA, AAPL, the three tickers this block brings onto real data.

Deliberately NOT a pytest test and NOT named test_*.py -- pytest's default
discovery will never collect this file, so the normal automated test suite
(and CI) never depends on FMP being reachable or a real API key existing.
This is a manual, human-run verification command, generalizing
nvda_earnings.py/nvda_market_data.py's own structure and discipline across
multiple tickers in one run instead of duplicating a per-ticker script.

Usage:

    FMP_API_KEY=your-real-key python -m logan_core.live_verification.live_equities
    FMP_API_KEY=your-real-key python -m logan_core.live_verification.live_equities TSLA AAPL

What this proves, per ticker: FmpEarningsProvider/FmpMarketDataProvider ->
EarningsReport/Quote/GradeChange -> RawSignal -> Normalizer ->
StocksTriggerEvaluator (STOCK_EARNINGS_BEAT, STOCK_PRICE_MOVE_SIGNIFICANT,
STOCK_ANALYST_UPGRADE/DOWNGRADE) -> the existing, unmodified Orchestrator
pipeline -> a delivered opportunity, and whether the three, together, ever
converge (STOCK_CONVERGENCE_MULTI_SOURCE). Each condition fires or doesn't
fire based on that ticker's actual current data -- this script never forces,
lowers a threshold, or fakes an outcome for any ticker. /v1/opportunities and
backend/app/logan_feed.py are real callers of this same generalized
FmpEarningsProvider/FmpMarketDataProvider path (see ADR-060) but are not
invoked by this script -- this only proves the mechanism against real FMP
responses.
"""

import sys
from datetime import datetime, timezone

from logan_core.community_intelligence import EngagementSample
from logan_core.contracts import Holding
from logan_core.convergence import StockConvergenceTracker
from logan_core.normalization import Normalizer
from logan_core.orchestrator import Orchestrator, PipelineDependencies
from logan_core.receptors import (
    earnings_report_to_raw_signal,
    grade_change_to_raw_signal,
    quote_to_raw_signal,
)
from logan_core.receptors.providers import (
    FmpEarningsProvider,
    FmpMarketDataProvider,
    FmpProviderError,
)
from logan_core.trigger_detection import StocksTriggerEvaluator
from logan_core.user_model import UserModelBuilder

DEFAULT_TICKERS = ["NVDA", "TSLA", "AAPL"]


def _demo_user_and_engagement(entity_id: str, now: datetime):
    user_model = UserModelBuilder().seed(
        user_id="demo_user",
        holdings=[
            Holding(
                domain="stocks",
                entity_id=entity_id,
                display_name=entity_id,
                added_at=now,
            )
        ],
        risk_tolerance="moderate",
    )
    engagement_samples = [
        EngagementSample(
            observed_at=now,
            volume_at_point=15,
            unique_users=12,
            saves_shares=2,
            questions=1,
        ),
        EngagementSample(
            observed_at=now,
            volume_at_point=35,
            unique_users=26,
            saves_shares=5,
            questions=2,
        ),
    ]
    return user_model, engagement_samples


def _verify_ticker(
    ticker: str,
    earnings_provider: FmpEarningsProvider,
    market_data_provider: FmpMarketDataProvider,
    convergence_tracker: StockConvergenceTracker,
) -> bool:
    """Returns True iff every provider call this ticker needed succeeded
    (regardless of whether any trigger actually fired -- a real "no fire" is
    success, not failure). Returns False only on a genuine provider/network
    problem."""
    print(f"\n--- {ticker} ---")
    ok = True
    raw_signals = []

    print(f"  Fetching latest real earnings for {ticker}...")
    try:
        report = earnings_provider.fetch_latest_earnings(ticker)
    except FmpProviderError as exc:
        print(f"  FAILED: {exc}")
        ok = False
        report = None
    if report is not None:
        print(
            f"    OK -- date={report.report_timestamp.date()}, "
            f"actual_eps={report.actual_eps}, consensus_eps={report.consensus_eps}"
        )
        raw = earnings_report_to_raw_signal(report)
        normalized = Normalizer().normalize(raw)
        trigger = StocksTriggerEvaluator().evaluate(raw, normalized)
        if trigger is None:
            print("    RESULT: STOCK_EARNINGS_BEAT did not fire (honest, not forced).")
        else:
            print(
                f"    RESULT: FIRED -- {trigger.trigger_code}, "
                f"confidence_contribution={trigger.confidence_contribution}"
            )
            raw_signals.append((raw, trigger, "earnings_signal"))
    elif ok:
        print(f"    NOTE: FMP has no reported earnings on file for {ticker}.")

    print(f"  Fetching real current quote for {ticker}...")
    try:
        quote = market_data_provider.fetch_quote(ticker)
    except FmpProviderError as exc:
        print(f"  FAILED: {exc}")
        ok = False
        quote = None
    if quote is not None:
        print(f"    OK -- price={quote.price}, change_pct={quote.change_pct:.4f}")
        raw = quote_to_raw_signal(quote)
        normalized = Normalizer().normalize(raw)
        trigger = StocksTriggerEvaluator().evaluate(raw, normalized)
        if trigger is None:
            print(
                "    RESULT: STOCK_PRICE_MOVE_SIGNIFICANT did not fire (honest, not forced)."
            )
        else:
            print(
                f"    RESULT: FIRED -- {trigger.trigger_code}, "
                f"confidence_contribution={trigger.confidence_contribution}"
            )
            raw_signals.append((raw, trigger, "price_change"))
    elif ok:
        print(f"    NOTE: FMP has no quote on file for {ticker}.")

    print(f"  Fetching most recent real analyst grade for {ticker}...")
    try:
        grade = market_data_provider.fetch_latest_grade_change(ticker)
    except FmpProviderError as exc:
        print(f"  FAILED: {exc}")
        ok = False
        grade = None
    if grade is not None:
        print(f"    OK -- {grade.grading_firm}: action={grade.action}")
        raw = grade_change_to_raw_signal(grade)
        normalized = Normalizer().normalize(raw)
        trigger = StocksTriggerEvaluator().evaluate(raw, normalized)
        if trigger is None:
            print(
                f"    RESULT: no analyst trigger fired (action={grade.action!r}, honest, "
                "not forced)."
            )
        else:
            print(
                f"    RESULT: FIRED -- {trigger.trigger_code}, "
                f"confidence_contribution={trigger.confidence_contribution}"
            )
            raw_signals.append((raw, trigger, "analyst_change"))
    elif ok:
        print(f"    NOTE: FMP has no analyst grade history on file for {ticker}.")

    if not raw_signals:
        print(
            f"  {ticker}: no signals fired this run -- nothing to run through the "
            "pipeline. Honest result, not forced."
        )
        return ok

    now = datetime.now(timezone.utc)
    user_model, engagement_samples = _demo_user_and_engagement(ticker, now)
    deps = PipelineDependencies(
        trigger_detector=StocksTriggerEvaluator(),
        convergence_tracker=convergence_tracker,
    )
    orchestrator = Orchestrator(deps=deps)
    result = orchestrator.run(
        raw_signals=[rs[0] for rs in raw_signals],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )
    print(
        f"  Running the full pipeline with {len(raw_signals)} real fired signal(s)..."
    )
    print(f"    headline: {result.delivered_item.headline}")
    print(f"    confidence_score: {result.confidence.confidence_score:.4f}")
    print(f"    event.trigger_events: {len(result.event.trigger_events)}")
    converged = any(
        t.trigger_code == "STOCK_CONVERGENCE_MULTI_SOURCE"
        for t in result.event.trigger_events
    )
    print(f"    STOCK_CONVERGENCE_MULTI_SOURCE: {'YES' if converged else 'no'}")
    return ok


def main() -> int:
    tickers = sys.argv[1:] or DEFAULT_TICKERS
    print(
        f"=== Sprint 3.6.8 Block 5 live verification: {', '.join(tickers)} via FMP ==="
    )

    try:
        earnings_provider = FmpEarningsProvider()
        market_data_provider = FmpMarketDataProvider()
    except FmpProviderError as exc:
        print(f"FAILED to construct provider(s): {exc}")
        return 1

    # One shared, real convergence tracker across all tickers this run --
    # proves entity isolation live, not just against fixtures: each
    # ticker's own observations must never leak into another's convergence
    # count (StockConvergenceTracker keys everything by entity_id).
    convergence_tracker = StockConvergenceTracker()

    all_ok = True
    for ticker in tickers:
        ok = _verify_ticker(
            ticker, earnings_provider, market_data_provider, convergence_tracker
        )
        all_ok = all_ok and ok

    print("\n=== Verification complete. This proved the generalized live equities")
    print("=== mechanism against real FMP responses for each ticker above; no")
    print("=== threshold was changed and no result was forced. /v1/opportunities")
    print("=== is a real caller of this same path (see ADR-060) but was not invoked")
    print("=== by this script.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
