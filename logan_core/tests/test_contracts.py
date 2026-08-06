from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from logan_core.contracts import (
    ConclusionConfidence,
    DeliveredItem,
    EvaluationHorizon,
    FeedbackSignal,
    OutcomeRecord,
    PolicyResult,
    SourceObservation,
    VerificationQuality,
)


def test_policy_result_requires_suppressed_when_not_permitted():
    with pytest.raises(ValidationError):
        PolicyResult(
            event_id=uuid4(),
            permitted=False,
            communication_mode="analysis",
            evaluated_at=datetime.now(timezone.utc),
        )


def test_policy_result_allows_suppressed_when_not_permitted():
    result = PolicyResult(
        event_id=uuid4(),
        permitted=False,
        communication_mode="suppressed",
        evaluated_at=datetime.now(timezone.utc),
    )
    assert result.communication_mode == "suppressed"


def test_feedback_signal_low_confidence_must_be_unknown():
    with pytest.raises(ValidationError):
        FeedbackSignal(
            event_id=uuid4(),
            interaction_type="view",
            inferred_intent="interested",
            intent_confidence=0.2,
            raw_interaction="view",
            observed_at=datetime.now(timezone.utc),
        )


def test_feedback_signal_low_confidence_unknown_is_valid():
    signal = FeedbackSignal(
        event_id=uuid4(),
        interaction_type="view",
        inferred_intent="unknown",
        intent_confidence=0.2,
        raw_interaction="view",
        observed_at=datetime.now(timezone.utc),
    )
    assert signal.inferred_intent == "unknown"


def test_delivered_item_rejects_long_headline():
    with pytest.raises(ValidationError):
        DeliveredItem(
            event_id=uuid4(),
            surface="feed_card",
            headline="x" * 121,
            what_happened="a",
            why_it_matters="a",
            why_it_matters_to_me="a",
            why_now="a",
            confidence_label="High",
            confidence_score=0.9,
            delivered_at=datetime.now(timezone.utc),
        )


def test_feedback_signal_accepts_watch_and_remind():
    for interaction_type in ("watch", "remind"):
        signal = FeedbackSignal(
            event_id=uuid4(),
            interaction_type=interaction_type,
            inferred_intent="interested",
            intent_confidence=0.8,
            raw_interaction=interaction_type,
            observed_at=datetime.now(timezone.utc),
        )
        assert signal.interaction_type == interaction_type


def test_feedback_engine_interprets_watch_and_remind():
    from logan_core.feedback import FeedbackEngine

    engine = FeedbackEngine()
    watch = engine.interpret(uuid4(), "watch")
    remind = engine.interpret(uuid4(), "remind")

    assert watch.inferred_intent == "interested"
    assert watch.intent_confidence >= 0.5
    assert remind.inferred_intent == "interested"
    assert remind.intent_confidence >= 0.5


def _verification_quality(level="verified"):
    return VerificationQuality(
        level=level,
        method="direct_price_data_comparison",
        confidence_in_verification=0.9,
    )


def _evaluation_horizon():
    return EvaluationHorizon(value=5, unit="trading_days")


def test_outcome_record_v2_schema_version_defaults_to_2_0():
    record = OutcomeRecord(
        outcome_id=uuid4(),
        event_id=uuid4(),
        user_id="demo_user",
        entity_id="TSLA",
        outcome_type="signal_accuracy",
        prediction_or_claim_type="directional_price_move",
        raw_predicted_value={"direction": "up", "magnitude_pct": 8.0},
        created_at=datetime.now(timezone.utc),
        evaluation_horizon=_evaluation_horizon(),
        resolvability="unresolved_pending",
        verification_quality=_verification_quality(),
        resolved_at=datetime.now(timezone.utc),
        delay_window="days",
    )
    assert record.schema_version == "2.0"
    assert record.result is None
    assert record.expected is None
    assert record.learning_applied is False


def test_outcome_record_rejects_resolved_without_observed_result():
    with pytest.raises(ValidationError):
        OutcomeRecord(
            outcome_id=uuid4(),
            event_id=uuid4(),
            user_id="demo_user",
            entity_id="TSLA",
            outcome_type="signal_accuracy",
            prediction_or_claim_type="directional_price_move",
            raw_predicted_value={"direction": "up"},
            created_at=datetime.now(timezone.utc),
            evaluation_horizon=_evaluation_horizon(),
            resolvability="resolved",
            verification_quality=_verification_quality(),
            resolved_at=datetime.now(timezone.utc),
            delay_window="days",
        )


def test_outcome_record_rejects_fabricated_observed_result_when_unresolved():
    with pytest.raises(ValidationError):
        OutcomeRecord(
            outcome_id=uuid4(),
            event_id=uuid4(),
            user_id="demo_user",
            entity_id="TSLA",
            outcome_type="signal_accuracy",
            prediction_or_claim_type="directional_price_move",
            raw_predicted_value={"direction": "up"},
            created_at=datetime.now(timezone.utc),
            evaluation_horizon=_evaluation_horizon(),
            resolvability="unresolved_pending",
            observed_result={"direction": "up"},
            verification_quality=_verification_quality(),
            resolved_at=datetime.now(timezone.utc),
            delay_window="days",
        )


def test_outcome_record_resolved_with_observed_result_is_valid():
    record = OutcomeRecord(
        outcome_id=uuid4(),
        event_id=uuid4(),
        user_id="demo_user",
        entity_id="TSLA",
        outcome_type="signal_accuracy",
        prediction_or_claim_type="directional_price_move",
        raw_predicted_value={"direction": "up"},
        created_at=datetime.now(timezone.utc),
        evaluation_horizon=_evaluation_horizon(),
        resolvability="resolved",
        observed_result={"actual_direction": "up", "actual_magnitude_pct": 6.4},
        verification_quality=_verification_quality(),
        resolved_at=datetime.now(timezone.utc),
        delay_window="days",
    )
    assert record.observed_result is not None


def test_source_observation_construction_and_validator():
    observation = SourceObservation(
        observation_id=uuid4(),
        source_id="reuters_wire",
        trigger_or_claim_id="claim_tsla_ai_partnership",
        evaluation_horizon=_evaluation_horizon(),
        resolvability="resolved",
        observed_result={"accurate": True},
        verification_quality=_verification_quality(),
        created_at=datetime.now(timezone.utc),
    )
    assert observation.schema_version == "1.0"

    with pytest.raises(ValidationError):
        SourceObservation(
            observation_id=uuid4(),
            source_id="reuters_wire",
            trigger_or_claim_id="claim_tsla_ai_partnership",
            evaluation_horizon=_evaluation_horizon(),
            resolvability="unresolved_pending",
            observed_result={"accurate": True},
            verification_quality=_verification_quality(),
            created_at=datetime.now(timezone.utc),
        )


def test_conclusion_confidence_reserves_deterministic_baseline_model_version():
    confidence = ConclusionConfidence(
        event_id=uuid4(),
        confidence_score=0.7,
        classification="inference",
        evaluated_at=datetime.now(timezone.utc),
    )
    assert confidence.confidence_model_version == "deterministic-baseline"
    assert confidence.calibrated_at is None


def test_schema_version_defaults_present():
    signal = FeedbackSignal(
        event_id=uuid4(),
        interaction_type="save",
        inferred_intent="interested",
        intent_confidence=0.9,
        raw_interaction="save",
        observed_at=datetime.now(timezone.utc),
    )
    assert signal.schema_version == "1.0"
