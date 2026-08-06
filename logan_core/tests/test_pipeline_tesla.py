"""The primary Phase 1 operational test: Tesla announces a major AI chip partnership,
run through the full pipeline (Raw Signal -> Presentation) using simulated data only.
Scope resolved in docs/specs/LOGAN_IMPLEMENTATION_PLAN.md.
"""

from logan_core.receptors import (
    tesla_ai_partnership_corroboration,
    tesla_ai_partnership_signal,
)

PER_SIGNAL_LAYERS = ["normalization", "orchestrator.operational_history", "world_model"]

EXPECTED_LAYERS = [
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


def test_tesla_scenario_produces_opportunity_card(
    orchestrator, user_model, engagement_samples, now
):
    result = orchestrator.run(
        raw_signals=[
            tesla_ai_partnership_signal(now),
            tesla_ai_partnership_corroboration(now),
        ],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )

    # Opportunity card
    assert result.delivered_item.headline
    assert len(result.delivered_item.headline) <= 120
    # Confidence score
    assert 0.0 <= result.delivered_item.confidence_score <= 1.0
    assert result.delivered_item.confidence_label in (
        "High",
        "Moderate",
        "Low",
        "Speculative",
    )
    # Explanation
    assert result.delivered_item.why_it_matters
    assert result.delivered_item.why_it_matters_to_me
    # Supporting evidence
    assert result.trust.corroboration >= 1
    assert len(result.event.supporting) == 1
    # Decision trace / execution metrics
    assert result.trace.status == "complete"
    expected = PER_SIGNAL_LAYERS * 2 + EXPECTED_LAYERS
    assert [m.layer for m in result.trace.layers] == expected
    assert all(m.success for m in result.trace.layers)
    assert all(m.latency_ms >= 0 for m in result.trace.layers)
    assert result.trace.final_output == result.delivered_item.event_id


def test_tesla_scenario_is_relevant_to_nvda_holder(
    orchestrator, user_model, engagement_samples, now
):
    result = orchestrator.run(
        raw_signals=[tesla_ai_partnership_signal(now)],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )
    assert "NVDA" in result.reasoning.connected_entities


def test_tesla_scenario_respects_advice_boundary(
    orchestrator, user_model, engagement_samples, now
):
    result = orchestrator.run(
        raw_signals=[tesla_ai_partnership_signal(now)],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )
    disclaimer = "This is analysis and context, not financial or betting advice. You decide what to do next."
    assert disclaimer in result.delivered_item.required_disclaimers
    for phrase in ("buy ", "sell ", "you should"):
        assert phrase not in result.delivered_item.headline.lower()
        assert phrase not in result.delivered_item.why_it_matters.lower()
