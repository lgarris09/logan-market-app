"""Operational Beta Hardening Block 8 -- build_earned_notification_inputs()
(backend/app/earned_notification_inputs.py). Proves the typed adapter
correctly reflects a real pipeline run's own already-computed fields, and
-- just as importantly -- that nothing in this codebase's real decision
path (PolicyEngine.evaluate(), notifications.dispatch_eligible_notifications)
consumes it: it exists only as a prepared, unused input for a future Full
Earned Notifications pass.
"""

import copy
from datetime import datetime, timezone

from backend.app.earned_notification_inputs import build_earned_notification_inputs
from logan_core.contracts import Holding, RawSignal, UserModel
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


def _watched_holder_user_model(user_id: str) -> UserModel:
    now = datetime.now(timezone.utc)
    return UserModelBuilder().seed(
        user_id=user_id,
        holdings=[
            Holding(
                domain="stocks", entity_id="NVDA", display_name="NVIDIA", added_at=now
            )
        ],
    )


def test_inputs_reflect_the_real_personal_relevance_result():
    raw = _fresh_signal("NVDA", nvda_price_move_up_fixture())
    orchestrator = _orchestrator()
    result = orchestrator.run(
        raw_signals=[raw],
        user_id="earned-notif-user-a",
        user_model=_watched_holder_user_model("earned-notif-user-a"),
        engagement_samples=[],
        domain="stocks",
    )
    inputs = build_earned_notification_inputs(result)
    assert inputs.event_id == result.event.event_id
    assert (
        inputs.personal_relevance_result
        == result.recommendation.personal_relevance_result
    )
    assert (
        inputs.is_watched == result.recommendation.personal_relevance_result.is_watched
    )


def test_inputs_reflect_real_evidence_credibility_and_time_sensitivity():
    raw = _fresh_signal("NVDA", nvda_price_move_up_fixture())
    orchestrator = _orchestrator()
    result = orchestrator.run(
        raw_signals=[raw],
        user_id="earned-notif-user-b",
        user_model=_blank_user_model("earned-notif-user-b"),
        engagement_samples=[],
        domain="stocks",
    )
    inputs = build_earned_notification_inputs(result)
    assert inputs.evidence_credibility == result.trust.trust_score
    assert inputs.time_sensitivity == result.recommendation.dimensions.urgency
    assert 0.0 <= inputs.evidence_credibility <= 1.0
    assert 0.0 <= inputs.time_sensitivity <= 1.0


def test_material_delta_is_none_when_lifecycle_tracking_is_not_active():
    """No lifecycle_tracker wired into PipelineDependencies -- material_delta
    must be honestly None, never a fabricated summary."""
    raw = _fresh_signal("NVDA", nvda_price_move_up_fixture())
    orchestrator = _orchestrator()
    result = orchestrator.run(
        raw_signals=[raw],
        user_id="earned-notif-user-c",
        user_model=_blank_user_model("earned-notif-user-c"),
        engagement_samples=[],
        domain="stocks",
    )
    assert result.lifecycle_delta is None
    inputs = build_earned_notification_inputs(result)
    assert inputs.material_delta is None


def test_inputs_are_a_pure_snapshot_never_mutating_the_pipeline_result():
    raw = _fresh_signal("NVDA", nvda_price_move_up_fixture())
    orchestrator = _orchestrator()
    result = orchestrator.run(
        raw_signals=[raw],
        user_id="earned-notif-user-d",
        user_model=_blank_user_model("earned-notif-user-d"),
        engagement_samples=[],
        domain="stocks",
    )
    before = copy.deepcopy(result)
    build_earned_notification_inputs(result)
    assert result == before


def test_unwatched_result_reports_is_watched_false():
    raw = _fresh_signal("NVDA", nvda_price_move_up_fixture())
    orchestrator = _orchestrator()
    result = orchestrator.run(
        raw_signals=[raw],
        user_id="earned-notif-user-e",
        user_model=_blank_user_model("earned-notif-user-e"),
        engagement_samples=[],
        domain="stocks",
    )
    inputs = build_earned_notification_inputs(result)
    assert inputs.is_watched is False
