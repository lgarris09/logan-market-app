"""Operational Beta Hardening Block 2 -- proves Orchestrator.run() actually
wires Controlled Exploration in (calls it after Prioritization, with the
real AttentionRecommendation, and uses its returned PrioritizedItem
downstream), rather than re-proving apply_controlled_exploration()'s own
decision logic -- that's already exhaustively covered, in isolation, by
test_controlled_exploration.py.
"""

from datetime import datetime, timezone

import logan_core.orchestrator.pipeline as pipeline_module
from logan_core.contracts import RawSignal, UserModel
from logan_core.orchestrator import Orchestrator, PipelineDependencies
from logan_core.receptors import quote_to_raw_signal
from logan_core.receptors.providers import (
    FixtureMarketDataProvider,
    nvda_price_move_up_fixture,
)
from logan_core.trigger_detection import StocksTriggerEvaluator
from logan_core.user_model import UserModelBuilder


def _orchestrator() -> Orchestrator:
    return Orchestrator(
        deps=PipelineDependencies(trigger_detector=StocksTriggerEvaluator())
    )


def _fresh_signal(ticker: str, fixture) -> RawSignal:
    provider = FixtureMarketDataProvider(quotes={ticker: fixture})
    quote = provider.fetch_quote(ticker)
    assert quote is not None
    raw = quote_to_raw_signal(quote)
    return raw.model_copy(update={"captured_at": datetime.now(timezone.utc)})


def _blank_user_model(user_id: str) -> UserModel:
    return UserModelBuilder().seed(user_id=user_id)


def test_pipeline_run_passes_the_real_recommendation_through(monkeypatch):
    seen: dict = {}

    def _spy(item, recommendation, now=None):
        seen["item"] = item
        seen["recommendation"] = recommendation
        return item.model_copy(
            update={"visibility": "feed", "attention_reason": "unseen_material_change"}
        )

    monkeypatch.setattr(pipeline_module, "apply_controlled_exploration", _spy)

    raw = _fresh_signal("NVDA", nvda_price_move_up_fixture())
    orchestrator = _orchestrator()
    result = orchestrator.run(
        raw_signals=[raw],
        user_id="exploration-wiring-user",
        user_model=_blank_user_model("exploration-wiring-user"),
        engagement_samples=[],
        domain="stocks",
    )

    assert seen["recommendation"] is result.recommendation
    # The stub's return value is what the pipeline actually uses downstream,
    # not silently discarded.
    assert result.prioritized_item.visibility == "feed"
    assert result.prioritized_item.attention_reason == "unseen_material_change"


def test_pipeline_run_without_stubbing_never_crashes_and_always_returns_a_reason_field():
    """Real (non-stubbed) end-to-end run -- attention_reason is always a
    valid value of the closed set (None included), never raises."""
    raw = _fresh_signal("NVDA", nvda_price_move_up_fixture())
    orchestrator = _orchestrator()
    result = orchestrator.run(
        raw_signals=[raw],
        user_id="exploration-real-run-user",
        user_model=_blank_user_model("exploration-real-run-user"),
        engagement_samples=[],
        domain="stocks",
    )
    assert result.prioritized_item.attention_reason in (
        None,
        "personal_relevance",
        "strong_world_signal",
        "unseen_material_change",
    )
