from datetime import datetime, timezone
from uuid import uuid4

from logan_core.contracts import (
    Domain,
    FeedbackSignal,
    MemoryRecord,
    MemoryWrite,
    OutcomeRecord,
    RecordType,
)
from logan_core.memory import MemoryStore

REVIEW_CONFIDENCE_THRESHOLD = 0.40


class LearningEngine:
    """Layer 15 — the only layer permitted to write to Memory System and User Model.
    Controls the pace and magnitude of all updates. V1 processes explicit, high-
    confidence feedback (e.g. Memory Inbox confirm/reject, ADR-019) immediately;
    everything else is queued conceptually for the normal delayed cadence, which a
    real batch scheduler would implement — out of scope for this vertical slice.
    """

    def __init__(self, memory_store: MemoryStore) -> None:
        self._memory_store = memory_store
        self.flagged_for_review: list[MemoryWrite] = []

    def process_feedback(
        self,
        feedback: FeedbackSignal,
        user_id: str,
        domain: Domain,
        entities: list[str],
        content: object,
    ) -> MemoryWrite:
        now = datetime.now(timezone.utc)

        record_type: RecordType
        if feedback.raw_interaction == "memory_inbox_reject":
            record_type = "correction_record"
        elif feedback.interaction_type == "act":
            record_type = "user_statement"
        else:
            record_type = "feedback_record"

        record = MemoryRecord(
            record_id=uuid4(),
            user_id=user_id,
            record_type=record_type,
            content=content,
            domain=domain,
            entities=entities,
            source_layer="learning_system",
            created_at=now,
            decay_weight=1.0,
        )

        write = MemoryWrite(
            write_id=uuid4(),
            write_type="new_record",
            target="memory",
            content=record,
            source_signal=feedback.event_id,
            confidence=feedback.intent_confidence,
            authorized_at=now,
        )

        if feedback.intent_confidence < REVIEW_CONFIDENCE_THRESHOLD:
            self.flagged_for_review.append(write)
            return write

        self._memory_store.write(record, writer="learning_system")
        return write

    def process_outcome(self, outcome: OutcomeRecord) -> MemoryWrite:
        """Intentionally unimplemented (ADR-036, LEARNING_AND_FEEDBACK_SPECIFICATION.md).

        The delayed-outcome learning path (UNRESOLVED_QUESTIONS.md #4) has no batch
        scheduler yet — nothing in this vertical slice calls this method. This stub
        exists only so the interface shape is typed and reviewable ahead of that work;
        it deliberately does *not* train a model, update weights, alter scoring, change
        source trust, fabricate verification, or write a real MemoryWrite. Raising here
        rather than silently returning a placeholder result is the point: a caller that
        reaches this before a real scheduler exists should fail loudly, not proceed as
        if outcome-driven learning were already happening.
        """
        raise NotImplementedError(
            "LearningEngine.process_outcome is a typed interface stub only (ADR-036) — "
            "no delayed-outcome learning scheduler exists yet. See "
            "LEARNING_AND_FEEDBACK_SPECIFICATION.md and UNRESOLVED_QUESTIONS.md #4."
        )
