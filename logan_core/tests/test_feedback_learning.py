"""Second operational test: Feedback -> Learning -> MemoryWrite, closing the loop the
primary Tesla scenario test intentionally leaves open (ADR-019).
"""

import pytest

from logan_core.memory import MemoryPermissionError
from logan_core.receptors import tesla_ai_partnership_signal


def test_memory_inbox_confirm_writes_through_learning(
    orchestrator, user_model, engagement_samples, now
):
    result = orchestrator.run(
        raw_signals=[tesla_ai_partnership_signal(now)],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )

    feedback, write = orchestrator.run_memory_inbox_confirm(
        event_id=result.event.event_id,
        user_id="demo_user",
        domain="stocks",
        entities=["TSLA"],
        content="User confirmed Tesla AI partnership is relevant to their portfolio.",
    )

    assert feedback.intent_confidence == 1.0
    assert feedback.inferred_intent == "interested"
    assert write.target == "memory"
    assert len(orchestrator.deps.memory_store.all()) == 1
    assert orchestrator.deps.memory_store.all()[0].source_layer == "learning_system"


def test_memory_inbox_reject_writes_correction_record(
    orchestrator, user_model, engagement_samples, now
):
    result = orchestrator.run(
        raw_signals=[tesla_ai_partnership_signal(now)],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )

    feedback, write = orchestrator.run_memory_inbox_reject(
        event_id=result.event.event_id,
        user_id="demo_user",
        domain="stocks",
        entities=["TSLA"],
        content="User rejected this inference.",
    )

    assert feedback.inferred_intent == "dismissing"
    stored = orchestrator.deps.memory_store.all()
    assert stored[0].record_type == "correction_record"


def test_low_confidence_feedback_is_flagged_not_written(
    orchestrator, user_model, engagement_samples, now
):
    result = orchestrator.run(
        raw_signals=[tesla_ai_partnership_signal(now)],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )

    feedback, write = orchestrator.run_feedback_loop(
        event_id=result.event.event_id,
        user_id="demo_user",
        domain="stocks",
        entities=["TSLA"],
        interaction_type="view",
        content="Low-confidence passive view.",
        duration_ms=None,
    )

    assert feedback.inferred_intent == "unknown"
    assert len(orchestrator.deps.memory_store.all()) == 0
    assert write in orchestrator.deps.learning_engine.flagged_for_review


def test_run_feedback_loop_accepts_a_content_builder(
    orchestrator, user_model, engagement_samples, now
):
    """Behavioral-personalization pass: run_feedback_loop()'s `content` may be
    a callable receiving the FeedbackSignal it just computed -- lets a caller
    build structured content from inferred_intent/intent_confidence without
    interpreting the interaction a second time. Static-string callers (every
    other test in this file) remain unaffected."""
    result = orchestrator.run(
        raw_signals=[tesla_ai_partnership_signal(now)],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )

    calls = []

    def build_content(feedback):
        calls.append(feedback)
        return {
            "inferred_intent": feedback.inferred_intent,
            "intent_confidence": feedback.intent_confidence,
        }

    feedback, write = orchestrator.run_feedback_loop(
        event_id=result.event.event_id,
        user_id="demo_user",
        domain="stocks",
        entities=["TSLA"],
        interaction_type="save",
        content=build_content,
    )

    assert len(calls) == 1
    assert calls[0] is feedback
    stored = orchestrator.deps.memory_store.all()
    assert stored[0].content == {
        "inferred_intent": "interested",
        "intent_confidence": 0.85,
    }


def test_only_learning_system_may_write_memory():
    from datetime import datetime, timezone
    from uuid import uuid4

    from logan_core.contracts import MemoryRecord
    from logan_core.memory import MemoryStore

    store = MemoryStore()
    record = MemoryRecord(
        record_id=uuid4(),
        user_id="demo_user",
        record_type="user_statement",
        content="test",
        source_layer="learning_system",
        created_at=datetime.now(timezone.utc),
    )
    with pytest.raises(MemoryPermissionError):
        store.write(record, writer="reasoning_engine")


def test_memory_record_rejects_empty_user_id():
    from datetime import datetime, timezone
    from uuid import uuid4

    import pytest as _pytest
    from pydantic import ValidationError

    from logan_core.contracts import MemoryRecord

    with _pytest.raises(ValidationError):
        MemoryRecord(
            record_id=uuid4(),
            user_id="",
            record_type="user_statement",
            content="test",
            source_layer="learning_system",
            created_at=datetime.now(timezone.utc),
        )


def test_process_outcome_is_an_explicit_unimplemented_stub(orchestrator):
    from datetime import datetime, timezone
    from uuid import uuid4

    from logan_core.contracts import (
        EvaluationHorizon,
        OutcomeRecord,
        VerificationQuality,
    )

    outcome = OutcomeRecord(
        outcome_id=uuid4(),
        event_id=uuid4(),
        user_id="demo_user",
        entity_id="TSLA",
        outcome_type="signal_accuracy",
        prediction_or_claim_type="directional_price_move",
        raw_predicted_value={"direction": "up"},
        created_at=datetime.now(timezone.utc),
        evaluation_horizon=EvaluationHorizon(value=5, unit="trading_days"),
        resolvability="unresolved_pending",
        verification_quality=VerificationQuality(
            level="unverifiable", method="none", confidence_in_verification=0.0
        ),
        resolved_at=datetime.now(timezone.utc),
        delay_window="days",
    )

    with pytest.raises(NotImplementedError):
        orchestrator.deps.learning_engine.process_outcome(outcome)

    # No side effects — nothing was written, nothing was flagged.
    assert orchestrator.deps.memory_store.all() == []
    assert orchestrator.deps.learning_engine.flagged_for_review == []


def test_memory_inbox_confirm_stamps_user_id(
    orchestrator, user_model, engagement_samples, now
):
    result = orchestrator.run(
        raw_signals=[tesla_ai_partnership_signal(now)],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )

    orchestrator.run_memory_inbox_confirm(
        event_id=result.event.event_id,
        user_id="demo_user",
        domain="stocks",
        entities=["TSLA"],
        content="User confirmed Tesla AI partnership is relevant to their portfolio.",
    )

    stored = orchestrator.deps.memory_store.all()
    assert stored[0].user_id == "demo_user"
