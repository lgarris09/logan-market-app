"""Sprint 3.6.7 — live verification: NVIDIA quote and analyst-grade data
through the real FMP provider and the real STRATUS pipeline, end to end.

Deliberately NOT a pytest test and NOT named test_*.py -- pytest's default
discovery will never collect this file, so the normal automated test suite
(and CI) never depends on FMP being reachable or a real API key existing.
This is a manual, human-run verification command, mirroring
nvda_earnings.py's structure for the two new signal types this sprint added.

Usage:

    FMP_API_KEY=your-real-key python -m logan_core.live_verification.nvda_market_data

What this proves: FmpMarketDataProvider.fetch_quote/fetch_latest_grade_change
-> Quote/GradeChange -> RawSignal -> Normalizer -> StocksTriggerEvaluator
(STOCK_PRICE_MOVE_SIGNIFICANT / STOCK_ANALYST_UPGRADE / STOCK_ANALYST_DOWNGRADE)
-> the existing, unmodified Orchestrator pipeline -> a delivered opportunity
with a real Watch disposition (communication_mode/watch_route/interruption).
Each trigger fires or doesn't fire based on NVIDIA's actual current quote and
most recent real analyst rating action -- this script never forces or fakes
an outcome either way. /v1/opportunities and backend/app/logan_feed.py are
untouched by this script and remain unaffected (see the Sprint 3.6.7 ADR for
why wiring these into the live production endpoint is deferred to a
follow-up, not attempted here).
"""

import sys
from datetime import datetime, timezone

from logan_core.community_intelligence import EngagementSample
from logan_core.contracts import Holding
from logan_core.normalization import Normalizer
from logan_core.orchestrator import Orchestrator, PipelineDependencies
from logan_core.receptors import grade_change_to_raw_signal, quote_to_raw_signal
from logan_core.receptors.providers import FmpMarketDataProvider, FmpProviderError
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


def _run_through_pipeline(raw, label: str) -> None:
    now = datetime.now(timezone.utc)
    user_model, engagement_samples = _demo_user_and_engagement(now)
    deps = PipelineDependencies(trigger_detector=StocksTriggerEvaluator())
    orchestrator = Orchestrator(deps=deps)
    result = orchestrator.run(
        raw_signals=[raw],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )
    print(f"      [{label}] headline: {result.delivered_item.headline}")
    print(f"      [{label}] confidence_score: {result.confidence.confidence_score:.4f}")
    print(
        f"      [{label}] trust.trigger_confidence_bonus: "
        f"{result.trust.trigger_confidence_bonus}"
    )
    print(f"      [{label}] event.trigger_events: {len(result.event.trigger_events)}")
    print(
        f"      [{label}] personal_relevance: "
        f"{result.recommendation.dimensions.personal_relevance:.2f}, "
        f"internal_rank_score: {result.recommendation.internal_rank_score:.4f}"
    )
    print(
        f"      [{label}] communication_mode: {result.policy_result.communication_mode}, "
        f"watch_route: {result.policy_result.decision_trace[0].rule.split('watch_route=')[1].split(';')[0]}"
    )
    print(f"      [{label}] interruption: {result.prioritized_item.interruption}")
    print(f"      [{label}] pipeline status: {result.trace.status}\n")


def main() -> int:
    print(
        f"=== Sprint 3.6.7 live verification: {ENTITY_ID} quote + analyst grades via FMP ===\n"
    )

    print(
        "[1/6] Constructing FmpMarketDataProvider from FMP_API_KEY environment variable..."
    )
    try:
        provider = FmpMarketDataProvider()
    except FmpProviderError as exc:
        print(f"FAILED: {exc}")
        return 1
    print("      OK -- API key resolved from environment.\n")

    print(f"[2/6] Fetching real current quote for {ENTITY_ID} from FMP...")
    try:
        quote = provider.fetch_quote(ENTITY_ID)
    except FmpProviderError as exc:
        print(f"FAILED: {exc}")
        return 1
    if quote is None:
        print(f"FAILED: FMP returned no quote for {ENTITY_ID}.")
        return 1
    print(
        f"      OK -- price={quote.price}, previous_close={quote.previous_close}, "
        f"change_pct={quote.change_pct:.4f}\n"
    )

    print("[3/6] Evaluating STOCK_PRICE_MOVE_SIGNIFICANT deterministically...")
    quote_raw = quote_to_raw_signal(quote)
    quote_normalized = Normalizer().normalize(quote_raw)
    quote_trigger = StocksTriggerEvaluator().evaluate(quote_raw, quote_normalized)
    if quote_trigger is None:
        print(
            "      RESULT: did not fire -- |change_pct| below the 5.0 threshold for "
            "NVIDIA's actual current session. Honest result, not forced.\n"
        )
    else:
        print(
            f"      RESULT: FIRED -- {quote_trigger.trigger_code}, "
            f"direction={quote_trigger.direction}, "
            f"confidence_contribution={quote_trigger.confidence_contribution}\n"
        )
    print(
        "[4/6] Running the full existing Orchestrator pipeline for the quote signal..."
    )
    _run_through_pipeline(quote_raw, "price_move")

    print(
        f"[5/6] Fetching the most recent real analyst rating action for {ENTITY_ID} from FMP..."
    )
    try:
        grade = provider.fetch_latest_grade_change(ENTITY_ID)
    except FmpProviderError as exc:
        print(f"FAILED: {exc}")
        return 1
    if grade is None:
        print(f"FAILED: FMP returned no analyst grade history for {ENTITY_ID}.")
        return 1
    print(
        f"      OK -- {grade.grading_firm}: {grade.previous_rating} -> {grade.new_rating} "
        f"(action={grade.action}, date={grade.action_date.date()})\n"
    )

    print("[6/6] Evaluating STOCK_ANALYST_UPGRADE/DOWNGRADE deterministically...")
    grade_raw = grade_change_to_raw_signal(grade)
    grade_normalized = Normalizer().normalize(grade_raw)
    grade_trigger = StocksTriggerEvaluator().evaluate(grade_raw, grade_normalized)
    if grade_trigger is None:
        print(
            f"      RESULT: did not fire -- most recent real action was "
            f"{grade.action!r} (maintain/initiate/reiterate), not upgrade/downgrade. "
            "Honest result, not forced.\n"
        )
    else:
        print(
            f"      RESULT: FIRED -- {grade_trigger.trigger_code}, "
            f"direction={grade_trigger.direction}, "
            f"confidence_contribution={grade_trigger.confidence_contribution}\n"
        )
    print(
        "      Running the full existing Orchestrator pipeline for the grade signal..."
    )
    _run_through_pipeline(grade_raw, "analyst_change")

    print("=== Verification complete. This proved the mechanism against real FMP")
    print("=== responses; /v1/opportunities and the mobile app are still unaffected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
