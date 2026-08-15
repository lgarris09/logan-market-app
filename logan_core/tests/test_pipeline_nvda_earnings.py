"""Sprint 3.6.6 — Phase 8 pipeline integration test / Phase 9's deterministic
positive-fire proof: NVIDIA earnings-beat data enters through the same
receptor/provider abstraction production would use, deterministically fires
STOCK_EARNINGS_BEAT, flows through the unmodified existing intelligence
pipeline (World Model, Evidence Trust, Reasoning, Conclusion Confidence,
Opportunity Engine, Policy, Prioritization, Presentation), and produces a
delivered opportunity with a real, traceable higher confidence than the same
event would get without the trigger.

Uses FixtureEarningsProvider -- explicitly not live data (see
receptors/providers/fixture.py). Proving this same path against a real
provider is the sprint's next step once credentials exist; see
docs/DECISIONS.md's Sprint 3.6.6 ADR.
"""

from logan_core.orchestrator import Orchestrator, PipelineDependencies
from logan_core.receptors import earnings_report_to_raw_signal
from logan_core.receptors.providers import (
    FIXTURE_SOURCE_ID,
    FIXTURE_SOURCE_NAME,
    EarningsReport,
    FixtureEarningsProvider,
    nvda_earnings_beat_fixture,
)
from logan_core.trigger_detection import StocksTriggerEvaluator

EXPECTED_LAYERS_WITH_TRIGGER = [
    "normalization",
    "orchestrator.operational_history",
    "trigger_detection",
    "world_model",
    "orchestrator.operational_history",
    "evidence_trust",
    "community_intelligence",
    "memory",
    "user_model",
    "active_context",
    "reasoning",
    "mental_model",
    "conclusion_confidence",
    "opportunity",
    "policy",
    "prioritization",
    "presentation",
]


def _nvda_earnings_orchestrator() -> tuple[Orchestrator, FixtureEarningsProvider]:
    provider = FixtureEarningsProvider({"NVDA": nvda_earnings_beat_fixture()})
    deps = PipelineDependencies(trigger_detector=StocksTriggerEvaluator())
    orchestrator = Orchestrator(deps=deps)
    return orchestrator, provider


def test_nvda_earnings_beat_produces_delivered_opportunity(
    user_model, engagement_samples
):
    orchestrator, provider = _nvda_earnings_orchestrator()
    report = provider.fetch_latest_earnings("NVDA")
    assert report is not None
    raw = earnings_report_to_raw_signal(report)

    result = orchestrator.run(
        raw_signals=[raw],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )

    # The trigger actually fired and is traceable end-to-end.
    assert len(result.event.trigger_events) == 1
    trigger = result.event.trigger_events[0]
    assert trigger.trigger_code == "STOCK_EARNINGS_BEAT"
    assert trigger.source_id == FIXTURE_SOURCE_ID  # unmistakably fixture, not live
    assert trigger.originating_signal_ids == [result.normalized_signals[0].signal_id]

    # Confidence genuinely reflects the trigger (Evidence Trust -> Conclusion
    # Confidence), not just the base trust formula.
    assert result.trust.trigger_confidence_bonus == 0.22
    assert result.confidence.confidence_score >= result.trust.trust_score

    # A real, delivered opportunity -- the existing downstream layers,
    # completely unmodified, produced this.
    assert result.delivered_item.headline
    assert 0.0 <= result.delivered_item.confidence_score <= 1.0
    assert result.trace.status == "complete"
    assert [m.layer for m in result.trace.layers] == EXPECTED_LAYERS_WITH_TRIGGER
    assert all(m.success for m in result.trace.layers)


def test_nvda_non_qualifying_earnings_produces_no_trigger_but_still_delivers(
    user_model, engagement_samples
):
    """Phase 9: 'if the current record does not meet the threshold, do not
    force it to fire ... use the real result honestly.' Simulated here via a
    fixture report engineered to miss the 5.0 beat_pct threshold -- the
    pipeline must still run end-to-end and deliver an (unboosted) opportunity,
    not error or silently fabricate a fire.
    """
    provider = FixtureEarningsProvider(
        {
            "NVDA": EarningsReport(
                entity_id="NVDA",
                actual_eps=0.99,
                consensus_eps=0.98,  # beat_pct ~1.02%, below the 5.0 threshold
                fiscal_quarter="Q2 2026",
                report_timestamp=nvda_earnings_beat_fixture().report_timestamp,
                source_id=FIXTURE_SOURCE_ID,
                source_name=FIXTURE_SOURCE_NAME,
            )
        }
    )
    deps = PipelineDependencies(trigger_detector=StocksTriggerEvaluator())
    orchestrator = Orchestrator(deps=deps)

    report = provider.fetch_latest_earnings("NVDA")
    assert report is not None
    raw = earnings_report_to_raw_signal(report)

    result = orchestrator.run(
        raw_signals=[raw],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )

    assert result.event.trigger_events == []
    assert result.trust.trigger_confidence_bonus == 0.0
    assert result.delivered_item.headline  # pipeline still completes honestly
    assert result.trace.status == "complete"


def test_without_trigger_detector_wired_behaves_exactly_as_before(
    user_model, engagement_samples
):
    """Backward-compatibility guarantee: PipelineDependencies() with no
    trigger_detector (every pre-Sprint-3.6.6 caller, including
    backend/app/logan_feed.py today) must not gain a 'trigger_detection'
    trace entry or any trigger_events, even when fed the same raw earnings
    signal shape."""
    provider = FixtureEarningsProvider({"NVDA": nvda_earnings_beat_fixture()})
    orchestrator = Orchestrator()  # default deps -- trigger_detector=None
    report = provider.fetch_latest_earnings("NVDA")
    assert report is not None
    raw = earnings_report_to_raw_signal(report)

    result = orchestrator.run(
        raw_signals=[raw],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )

    assert "trigger_detection" not in [m.layer for m in result.trace.layers]
    assert result.event.trigger_events == []
