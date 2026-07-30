"""Second operational test: Feedback -> Learning -> MemoryWrite, closing the loop the
primary Tesla scenario test intentionally leaves open (ADR-019).
"""

import pytest

from logan_core.memory import MemoryPermissionError
from logan_core.receptors import tesla_ai_partnership_signal


def test_memory_inbox_confirm_writes_through_learning(orchestrator, user_model, engagement_samples, now):
    result = orchestrator.run(
        raw_signals=[tesla_ai_partnership_signal(now)],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )

    feedback, write = orchestrator.run_memory_inbox_confirm(
        event_id=result.event.event_id,
        domain="stocks",
        entities=["TSLA"],
        content="User confirmed Tesla AI partnership is relevant to their portfolio.",
    )

    assert feedback.intent_confidence == 1.0
    assert feedback.inferred_intent == "interested"
    assert write.target == "memory"
    assert len(orchestrator.deps.memory_store.all()) == 1
    assert orchestrator.deps.memory_store.all()[0].source_layer == "learning_system"


def test_memory_inbox_reject_writes_correction_record(orchestrator, user_model, engagement_samples, now):
    result = orchestrator.run(
        raw_signals=[tesla_ai_partnership_signal(now)],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )

    feedback, write = orchestrator.run_memory_inbox_reject(
        event_id=result.event.event_id,
        domain="stocks",
        entities=["TSLA"],
        content="User rejected this inference.",
    )

    assert feedback.inferred_intent == "dismissing"
    stored = orchestrator.deps.memory_store.all()
    assert stored[0].record_type == "correction_record"


def test_low_confidence_feedback_is_flagged_not_written(orchestrator, user_model, engagement_samples, now):
    result = orchestrator.run(
        raw_signals=[tesla_ai_partnership_signal(now)],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )

    feedback, write = orchestrator.run_feedback_loop(
        event_id=result.event.event_id,
        domain="stocks",
        entities=["TSLA"],
        interaction_type="view",
        content="Low-confidence passive view.",
        duration_ms=None,
    )

    assert feedback.inferred_intent == "unknown"
    assert len(orchestrator.deps.memory_store.all()) == 0
    assert write in orchestrator.deps.learning_engine.flagged_for_review


def test_only_learning_system_may_write_memory():
    from datetime import datetime, timezone
    from uuid import uuid4

    from logan_core.contracts import MemoryRecord
    from logan_core.memory import MemoryStore

    store = MemoryStore()
    record = MemoryRecord(
        record_id=uuid4(),
        record_type="user_statement",
        content="test",
        source_layer="learning_system",
        created_at=datetime.now(timezone.utc),
    )
    with pytest.raises(MemoryPermissionError):
        store.write(record, writer="reasoning_engine")
