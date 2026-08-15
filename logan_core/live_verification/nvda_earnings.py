"""Sprint 3.6.6B — live verification: NVIDIA earnings through the real FMP
provider and the real STRATUS pipeline, end to end.

Deliberately NOT a pytest test and NOT named test_*.py -- pytest's default
discovery will never collect this file, so the normal automated test suite
(and CI) never depends on FMP being reachable or a real API key existing.
This is a manual, human-run verification command.

Usage:

    FMP_API_KEY=your-real-key python -m logan_core.live_verification.nvda_earnings

What this proves: FmpEarningsProvider -> EarningsReport -> RawSignal ->
Normalizer -> StocksTriggerEvaluator (STOCK_EARNINGS_BEAT) -> the existing,
unmodified Orchestrator pipeline -> a delivered opportunity. The trigger
fires or doesn't fire based on NVIDIA's actual most-recent reported
earnings -- this script never forces or fakes the outcome either way (Phase
9 instruction: "if it does not [meet the >=5% beat condition], it should
not fire"). /v1/opportunities and backend/app/logan_feed.py are untouched
by this script and remain unaffected.
"""

import sys
from datetime import datetime, timezone

from logan_core.community_intelligence import EngagementSample
from logan_core.contracts import Holding
from logan_core.normalization import Normalizer
from logan_core.orchestrator import Orchestrator, PipelineDependencies
from logan_core.receptors import earnings_report_to_raw_signal
from logan_core.receptors.providers import FmpEarningsProvider, FmpProviderError
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


def main() -> int:
    print(f"=== Sprint 3.6.6B live verification: {ENTITY_ID} earnings via FMP ===\n")

    print(
        "[1/5] Constructing FmpEarningsProvider from FMP_API_KEY environment variable..."
    )
    try:
        provider = FmpEarningsProvider()
    except FmpProviderError as exc:
        print(f"FAILED: {exc}")
        return 1
    print("      OK -- API key resolved from environment.\n")

    print(f"[2/5] Fetching latest real earnings report for {ENTITY_ID} from FMP...")
    try:
        report = provider.fetch_latest_earnings(ENTITY_ID)
    except FmpProviderError as exc:
        print(f"FAILED: {exc}")
        return 1
    if report is None:
        print(f"FAILED: FMP returned no earnings history for {ENTITY_ID}.")
        return 1
    print(
        f"      OK -- report dated {report.report_timestamp.date()}, "
        f"actual_eps={report.actual_eps}, consensus_eps={report.consensus_eps}, "
        f"fiscal_quarter={report.fiscal_quarter}, source={report.source_id}\n"
    )
    if report.actual_eps is None or report.consensus_eps is None:
        print(
            "      NOTE: FMP did not supply actual_eps and/or consensus_eps for this "
            "report -- STOCK_EARNINGS_BEAT cannot fire on missing data (by design, this "
            "is not an error). See the Sprint 3.6.6B report's field-name limitation note."
        )

    print(
        "[3/5] Mapping into RawSignal (receptors/stocks_earnings.py) and normalizing..."
    )
    raw = earnings_report_to_raw_signal(report)
    assert isinstance(raw.raw_value, dict)  # always true -- see stocks_earnings.py
    print(f"      RawSignal.raw_value['value'] = {raw.raw_value.get('value')!r}\n")

    print("[4/5] Evaluating STOCK_EARNINGS_BEAT deterministically...")
    normalized = Normalizer().normalize(raw)
    trigger = StocksTriggerEvaluator().evaluate(raw, normalized)
    if trigger is None:
        print(
            "      RESULT: did not fire. Either the beat_pct threshold (>=5.0) wasn't "
            "met, or required fields were missing -- this is the honest result for "
            "NVIDIA's actual most-recent reported earnings, not a forced outcome.\n"
        )
    else:
        print(
            f"      RESULT: FIRED -- {trigger.trigger_code}, "
            f"beat_pct={trigger.raw_magnitude:.2f}, "
            f"confidence_contribution={trigger.confidence_contribution}\n"
        )

    print(
        "[5/5] Running the full existing Orchestrator pipeline (unmodified downstream)..."
    )
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
    print(f"      headline: {result.delivered_item.headline}")
    print(f"      confidence_score: {result.confidence.confidence_score:.4f}")
    print(
        f"      trust.trigger_confidence_bonus: {result.trust.trigger_confidence_bonus}"
    )
    print(f"      event.trigger_events: {len(result.event.trigger_events)}")
    print(f"      pipeline status: {result.trace.status}\n")

    print("=== Verification complete. This proved the mechanism against a real FMP")
    print("=== response; /v1/opportunities and the mobile app are still unaffected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
