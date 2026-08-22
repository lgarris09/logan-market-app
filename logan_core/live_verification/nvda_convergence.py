"""Sprint 3.6.7 Block 3 — live verification: STOCK_CONVERGENCE_MULTI_SOURCE
against real NVIDIA data from all three live signal types (earnings, price
move, analyst grade) through the real FMP providers and the real STRATUS
pipeline, end to end.

Deliberately NOT a pytest test and NOT named test_*.py -- pytest's default
discovery will never collect this file, so the normal automated test suite
(and CI) never depends on FMP being reachable or a real API key existing.
This is a manual, human-run verification command, mirroring nvda_earnings.py/
nvda_market_data.py's structure for the Block 2 convergence tracker.

Usage:

    FMP_API_KEY=your-real-key python -m logan_core.live_verification.nvda_convergence

What this proves: FmpEarningsProvider.fetch_latest_earnings +
FmpMarketDataProvider.fetch_quote/fetch_latest_grade_change -> RawSignal (x3)
-> Normalizer -> StocksTriggerEvaluator -> the real, unmodified
StockConvergenceTracker (logan_core/convergence/tracker.py) -> Orchestrator's
coherent-opportunity merge (orchestrator/pipeline.py) -> a delivered
opportunity. Each of the three underlying triggers fires or doesn't fire
based on NVIDIA's actual current data; STOCK_CONVERGENCE_MULTI_SOURCE only
fires when >=3 of them genuinely do, within its real 30-minute
(detected_timestamp) window -- this script never forces, fakes, or lowers
the threshold to manufacture a convergence result either way. A `NOT
QUALIFIED` report on a quiet day is the honest, expected outcome, not a
failure of this script. /v1/opportunities and backend/app/logan_feed.py are
untouched by this script and remain unaffected.
"""

import sys
from datetime import datetime, timezone

from logan_core.community_intelligence import EngagementSample
from logan_core.contracts import Holding, RawSignal, TriggerEvent
from logan_core.convergence import (
    STOCK_CONVERGENCE_MULTI_SOURCE,
    StockConvergenceTracker,
)
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

ENTITY_ID = "NVDA"


def _demo_user_and_engagement(now: datetime):
    user_model = UserModelBuilder().seed(
        user_id="demo_user",
        holdings=[
            Holding(
                domain="stocks",
                entity_id=ENTITY_ID,
                display_name="NVIDIA",
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


def _fetch_signals() -> tuple[list[RawSignal], list[str]]:
    """Fetches all three live signal types for NVDA, collecting each real
    RawSignal that could be built. Returns (raw_signals, notes) -- `notes`
    records exactly what was fetched or skipped and why, for the report.
    Never fabricates a signal a provider didn't actually return.
    """
    raw_signals: list[RawSignal] = []
    notes: list[str] = []

    try:
        earnings_provider = FmpEarningsProvider()
        report = earnings_provider.fetch_latest_earnings(ENTITY_ID)
        if report is None:
            notes.append("earnings: FMP has no reported earnings for NVDA")
        else:
            raw_signals.append(earnings_report_to_raw_signal(report))
            notes.append(
                f"earnings: fetched (actual_eps={report.actual_eps}, "
                f"consensus_eps={report.consensus_eps}, date={report.report_timestamp.date()})"
            )
    except FmpProviderError as exc:
        notes.append(f"earnings: provider error -- {exc}")

    try:
        market_provider = FmpMarketDataProvider()
    except FmpProviderError as exc:
        notes.append(f"market data provider unavailable -- {exc}")
        return raw_signals, notes

    try:
        quote = market_provider.fetch_quote(ENTITY_ID)
        if quote is None:
            notes.append("price: FMP has no quote for NVDA")
        else:
            raw_signals.append(quote_to_raw_signal(quote))
            notes.append(
                f"price: fetched (price={quote.price}, change_pct={quote.change_pct:.4f})"
            )
    except FmpProviderError as exc:
        notes.append(f"price: provider error -- {exc}")

    try:
        grade = market_provider.fetch_latest_grade_change(ENTITY_ID)
        if grade is None:
            notes.append("analyst grade: FMP has no grade history for NVDA")
        else:
            raw_signals.append(grade_change_to_raw_signal(grade))
            notes.append(
                f"analyst grade: fetched ({grade.grading_firm}: "
                f"{grade.previous_rating} -> {grade.new_rating}, action={grade.action})"
            )
    except FmpProviderError as exc:
        notes.append(f"analyst grade: provider error -- {exc}")

    return raw_signals, notes


def main() -> int:
    print(
        f"=== Sprint 3.6.7 Block 3 live verification: {ENTITY_ID} "
        "STOCK_CONVERGENCE_MULTI_SOURCE via real FMP data ===\n"
    )

    print("[1/4] Fetching all three live signal types for NVDA from FMP...")
    raw_signals, notes = _fetch_signals()
    for note in notes:
        print(f"      {note}")
    if not raw_signals:
        print("\nFAILED: no live signals could be fetched at all.")
        return 1
    print(f"      -> {len(raw_signals)} of 3 signal types fetched.\n")

    print(
        "[2/4] Evaluating deterministic triggers for each fetched signal "
        "(StocksTriggerEvaluator)..."
    )
    evaluator = StocksTriggerEvaluator()
    normalizer = Normalizer()
    fired_triggers: list[tuple[RawSignal, TriggerEvent]] = []
    for raw in raw_signals:
        normalized = normalizer.normalize(raw)
        trigger = evaluator.evaluate(raw, normalized)
        if trigger is None:
            print(
                f"      {normalized.signal_type}: did not fire (no qualifying condition)"
            )
        else:
            print(
                f"      {normalized.signal_type}: FIRED -- {trigger.trigger_code} "
                f"(direction={trigger.direction}, confidence_contribution="
                f"{trigger.confidence_contribution})"
            )
            fired_triggers.append((raw, trigger))
    print(
        f"      -> {len(fired_triggers)} of {len(raw_signals)} fetched signals fired.\n"
    )

    print(
        "[3/4] Evaluating the registered STOCK_CONVERGENCE_MULTI_SOURCE rule "
        "(>=3 distinct signal types within 30 minutes, real StockConvergenceTracker)..."
    )
    tracker = StockConvergenceTracker()
    convergence_result = None
    for raw, trigger in fired_triggers:
        normalized = normalizer.normalize(raw)
        observed = tracker.observe(trigger, normalized.signal_type)
        if observed is not None:
            convergence_result = observed

    if convergence_result is None:
        print(
            f"      RESULT: NOT QUALIFIED -- only {len(fired_triggers)} distinct "
            "qualifying signal type(s) fired for NVDA right now (or their "
            "detection times fell outside the 30-minute window). This is an "
            "honest, unforced result -- the threshold was never lowered and "
            "no signal was fabricated to reach it.\n"
        )
    else:
        print(
            f"      RESULT: QUALIFIED -- {convergence_result.trigger_code} fired "
            f"(source_count={convergence_result.context['source_count']}, "
            f"sources={convergence_result.context['sources']})\n"
        )

    print(
        "[4/4] Running the full existing Orchestrator pipeline (all fetched "
        "signals, one coherent opportunity, real convergence tracker wired in)..."
    )
    now = datetime.now(timezone.utc)
    user_model, engagement_samples = _demo_user_and_engagement(now)
    deps = PipelineDependencies(
        trigger_detector=StocksTriggerEvaluator(),
        convergence_tracker=StockConvergenceTracker(),
    )
    orchestrator = Orchestrator(deps=deps)
    result = orchestrator.run(
        raw_signals=raw_signals,
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )
    trigger_codes = sorted({t.trigger_code for t in result.event.trigger_events})
    print(f"      headline: {result.delivered_item.headline}")
    print(f"      event.trigger_events: {trigger_codes}")
    print(
        f"      convergence present in coherent opportunity: "
        f"{STOCK_CONVERGENCE_MULTI_SOURCE in trigger_codes}"
    )
    print(f"      confidence_score: {result.confidence.confidence_score:.4f}")
    print(
        f"      trust.trigger_confidence_bonus: {result.trust.trigger_confidence_bonus}"
    )
    print(
        f"      personal_relevance: {result.recommendation.dimensions.personal_relevance:.2f}, "
        f"internal_rank_score: {result.recommendation.internal_rank_score:.4f}"
    )
    print(f"      communication_mode: {result.policy_result.communication_mode}")
    print(f"      interruption: {result.prioritized_item.interruption}")
    print(f"      pipeline status: {result.trace.status}\n")

    print("=== Verification complete. This proved the mechanism against real FMP")
    print("=== responses; /v1/opportunities and the mobile app are still unaffected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
