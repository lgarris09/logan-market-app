"""Sprint 3.6.7 — pipeline integration tests for the generalized stock-signal
architecture: real price-move and analyst-grade data enters through the same
receptor/provider abstraction production would use, deterministically fires
STOCK_PRICE_MOVE_SIGNIFICANT / STOCK_ANALYST_UPGRADE / STOCK_ANALYST_DOWNGRADE,
flows through the unmodified existing intelligence pipeline (World Model,
Evidence Trust, Reasoning, Conclusion Confidence, Opportunity Engine, Policy,
Prioritization, Presentation), and produces a delivered opportunity --
mirroring test_pipeline_nvda_earnings.py's structure exactly for the new
signal types.

Uses FixtureMarketDataProvider -- explicitly not live data (see
receptors/providers/fixture.py). Proving this same path against the real FMP
provider is logan_core/live_verification/nvda_market_data.py.
"""

from logan_core.orchestrator import Orchestrator, PipelineDependencies
from logan_core.receptors import grade_change_to_raw_signal, quote_to_raw_signal
from logan_core.receptors.providers import (
    FIXTURE_SOURCE_ID,
    FixtureMarketDataProvider,
    nvda_analyst_downgrade_fixture,
    nvda_analyst_maintain_fixture,
    nvda_analyst_upgrade_fixture,
    nvda_no_significant_move_fixture,
    nvda_price_move_up_fixture,
)
from logan_core.trigger_detection import StocksTriggerEvaluator
from logan_core.trigger_detection.stocks import (
    STOCK_ANALYST_DOWNGRADE,
    STOCK_ANALYST_UPGRADE,
    STOCK_PRICE_MOVE_SIGNIFICANT,
)


def _orchestrator() -> Orchestrator:
    deps = PipelineDependencies(trigger_detector=StocksTriggerEvaluator())
    return Orchestrator(deps=deps)


def test_nvda_significant_price_move_produces_delivered_opportunity(
    user_model, engagement_samples
):
    """End-to-end proof for the price-move signal type, and -- since
    `user_model` (conftest.py) holds NVDA directly, giving personal_relevance
    the Personal route's explicit tier (a direct holding always yields at
    least the 0.6 explicit-connection floor, per OpportunityEngine's
    "connect" step; it reaches the full 1.0 actionable value only when
    ReasoningEngine also classifies the event as immediately actionable,
    which depends on trust_score and isn't guaranteed by holding it alone)
    -- a case that reaches a real interruption=="alert" Watch disposition,
    per ADR-049/050."""
    provider = FixtureMarketDataProvider(quotes={"NVDA": nvda_price_move_up_fixture()})
    quote = provider.fetch_quote("NVDA")
    assert quote is not None
    raw = quote_to_raw_signal(quote)

    orchestrator = _orchestrator()
    result = orchestrator.run(
        raw_signals=[raw],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )

    assert len(result.event.trigger_events) == 1
    trigger = result.event.trigger_events[0]
    assert trigger.trigger_code == STOCK_PRICE_MOVE_SIGNIFICANT
    assert trigger.source_id == FIXTURE_SOURCE_ID
    assert trigger.originating_signal_ids == [result.normalized_signals[0].signal_id]

    assert result.trust.trigger_confidence_bonus == 0.10
    assert result.confidence.confidence_score >= result.trust.trust_score
    assert result.delivered_item.headline
    assert result.trace.status == "complete"

    # Full Watch disposition, end to end: Opportunity -> Policy (Personal
    # route, explicit tier -- direct NVDA holding) -> Prioritization.
    assert result.recommendation.dimensions.personal_relevance >= 0.6
    assert "NVDA" in result.reasoning.connected_entities_explicit
    assert result.recommendation.internal_rank_score >= 0.6
    assert result.policy_result.communication_mode == "alert"
    assert "watch_route=personal" in result.policy_result.decision_trace[0].rule
    assert result.prioritized_item.interruption == "alert"


def test_nvda_ordinary_price_move_produces_no_trigger_but_still_delivers(
    user_model, engagement_samples
):
    provider = FixtureMarketDataProvider(
        quotes={"NVDA": nvda_no_significant_move_fixture()}
    )
    quote = provider.fetch_quote("NVDA")
    assert quote is not None
    raw = quote_to_raw_signal(quote)

    result = _orchestrator().run(
        raw_signals=[raw],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )

    assert result.event.trigger_events == []
    assert result.trust.trigger_confidence_bonus == 0.0
    assert result.delivered_item.headline
    assert result.trace.status == "complete"


def test_nvda_analyst_upgrade_produces_delivered_opportunity(
    user_model, engagement_samples
):
    provider = FixtureMarketDataProvider(
        grade_changes={"NVDA": nvda_analyst_upgrade_fixture()}
    )
    grade = provider.fetch_latest_grade_change("NVDA")
    assert grade is not None
    raw = grade_change_to_raw_signal(grade)

    result = _orchestrator().run(
        raw_signals=[raw],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )

    assert len(result.event.trigger_events) == 1
    trigger = result.event.trigger_events[0]
    assert trigger.trigger_code == STOCK_ANALYST_UPGRADE
    assert trigger.direction == "positive"
    assert result.trust.trigger_confidence_bonus == 0.08
    assert result.delivered_item.headline
    assert result.trace.status == "complete"


def test_nvda_analyst_downgrade_produces_delivered_opportunity(
    user_model, engagement_samples
):
    provider = FixtureMarketDataProvider(
        grade_changes={"NVDA": nvda_analyst_downgrade_fixture()}
    )
    grade = provider.fetch_latest_grade_change("NVDA")
    assert grade is not None
    raw = grade_change_to_raw_signal(grade)

    result = _orchestrator().run(
        raw_signals=[raw],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )

    assert len(result.event.trigger_events) == 1
    trigger = result.event.trigger_events[0]
    assert trigger.trigger_code == STOCK_ANALYST_DOWNGRADE
    assert trigger.direction == "negative"
    assert result.trust.trigger_confidence_bonus == 0.08
    assert result.trace.status == "complete"


def test_nvda_analyst_maintain_produces_no_trigger_but_still_delivers(
    user_model, engagement_samples
):
    provider = FixtureMarketDataProvider(
        grade_changes={"NVDA": nvda_analyst_maintain_fixture()}
    )
    grade = provider.fetch_latest_grade_change("NVDA")
    assert grade is not None
    raw = grade_change_to_raw_signal(grade)

    result = _orchestrator().run(
        raw_signals=[raw],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )

    assert result.event.trigger_events == []
    assert result.trust.trigger_confidence_bonus == 0.0
    assert result.delivered_item.headline
    assert result.trace.status == "complete"


def test_without_trigger_detector_wired_behaves_exactly_as_before_for_market_data(
    user_model, engagement_samples
):
    """Backward-compatibility guarantee, mirroring the earnings suite's own:
    PipelineDependencies() with no trigger_detector must not gain a
    'trigger_detection' trace entry or any trigger_events for the new signal
    types either."""
    provider = FixtureMarketDataProvider(quotes={"NVDA": nvda_price_move_up_fixture()})
    quote = provider.fetch_quote("NVDA")
    assert quote is not None
    raw = quote_to_raw_signal(quote)

    orchestrator = Orchestrator()  # default deps -- trigger_detector=None
    result = orchestrator.run(
        raw_signals=[raw],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )

    assert "trigger_detection" not in [m.layer for m in result.trace.layers]
    assert result.event.trigger_events == []
