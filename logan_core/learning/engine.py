from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
from uuid import UUID, uuid4

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

# Sprint 3.6.7 Block 3: short-window idempotency for feedback interactions --
# a duplicate/near-simultaneous re-fire of the *same* (user, event,
# interaction_type) within this window (e.g. a network retry, or a UI
# double-invoke) is treated as one observation, not two independent pieces of
# "repeated" evidence. Deliberately short: a genuinely separate later session
# viewing the same card again (the actual case UserModelBuilder's
# MIN_REPEAT_EVIDENCE is meant to detect) must still count as new evidence.
FEEDBACK_DEDUP_WINDOW = timedelta(minutes=5)

# Exposure/impression records have no such short window at all -- see
# process_exposure's own docstring for why one lifetime record per
# (user, event) is the simpler, sufficient idempotency model here.


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

    def _recent_record(
        self,
        *,
        user_id: str,
        event_id: Optional[UUID],
        record_type: RecordType,
        now: datetime,
        window: Optional[timedelta] = None,
        interaction_type: Optional[str] = None,
    ) -> Optional[MemoryRecord]:
        """Finds the most recent existing record of `record_type` for this
        (user_id, event_id) pair -- shared lookup for both process_feedback's
        short-window dedup and process_exposure's lifetime-record reuse.
        `window=None` (process_exposure's case) means "any time, no cutoff" --
        there is one lifetime exposure_record per (user, event), not a
        rolling window. `interaction_type`, when given, additionally narrows
        the match (process_feedback only wants to dedupe an identical
        interaction_type, not any feedback on the same event -- a "view"
        moments after a "save" on the same card are two real, distinct
        signals, not a duplicate).
        """
        if event_id is None:
            return None
        cutoff = now - window if window is not None else None
        candidates = [
            r
            for r in self._memory_store.all()
            if r.record_type == record_type
            and r.user_id == user_id
            and r.operational_ref == event_id
            and (cutoff is None or r.created_at >= cutoff)
        ]
        if interaction_type is not None:
            candidates = [
                r
                for r in candidates
                if isinstance(r.content, dict)
                and r.content.get("interaction_type") == interaction_type
            ]
        if not candidates:
            return None
        return max(candidates, key=lambda r: r.created_at)

    def process_feedback(
        self,
        feedback: FeedbackSignal,
        user_id: str,
        domain: Domain,
        entities: list[str],
        content: object,
    ) -> MemoryWrite:
        # Reuses FeedbackEngine.interpret()'s own already-computed timestamp
        # (production: effectively "now," since this runs synchronously
        # right after) rather than calling datetime.now() a second time --
        # also makes the short-window dedup check controllable in tests via
        # FeedbackSignal.observed_at, without a separate now= parameter.
        now = feedback.observed_at

        record_type: RecordType
        if feedback.raw_interaction == "memory_inbox_reject":
            record_type = "correction_record"
        elif feedback.interaction_type == "act":
            record_type = "user_statement"
        else:
            record_type = "feedback_record"

        # Sprint 3.6.7 Block 3: short-window duplicate protection, only for
        # the ordinary feedback_record path -- Memory Inbox confirm/reject
        # (user_statement/correction_record) are explicit, deliberate user
        # actions the caller controls directly, never fired by passive
        # polling/retries, so they're never deduped here.
        if record_type == "feedback_record":
            existing = self._recent_record(
                user_id=user_id,
                event_id=feedback.event_id,
                record_type="feedback_record",
                window=FEEDBACK_DEDUP_WINDOW,
                now=now,
                interaction_type=feedback.interaction_type,
            )
            if existing is not None:
                return MemoryWrite(
                    write_id=uuid4(),
                    write_type="update_record",
                    target="memory",
                    content=existing,
                    source_signal=feedback.event_id,
                    confidence=feedback.intent_confidence,
                    authorized_at=now,
                )

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
            operational_ref=feedback.event_id,
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

    def process_exposure(
        self,
        event_id: UUID,
        user_id: str,
        domain: Domain,
        entity_id: str,
        now: Optional[datetime] = None,
    ) -> MemoryWrite:
        """Sprint 3.6.7 Block 3 — records a deterministic exposure/impression
        fact: this opportunity was actually shown to the user. Deliberately
        does NOT go through FeedbackEngine.interpret() -- there is no
        ambiguous user behavior to interpret here, only a system-observed
        fact, so this writes an `exposure_record` MemoryRecord directly
        (still the sole Learning System writer, per this class's own
        docstring).

        Idempotency: one lifetime `exposure_record` per (user_id, event_id),
        not a new row per impression. Every later exposure for the same
        event_id updates that same record's `impression_count`/
        `last_seen_at` in place (write_type="update_record") rather than
        creating a duplicate -- unlike process_feedback's short-window dedup,
        there's no "is this a separate meaningful occasion" question for a
        plain exposure count, so one running counter per event_id is the
        simpler, sufficient model (also naturally bounded storage growth --
        repeated impressions of the same still-visible card never grow the
        store).

        Never itself creates or strengthens established_behaviors/inferred
        Interest -- UserModelBuilder's existing behavioral-evidence folding
        only reads `feedback_record`s with `inferred_intent == "interested"`
        (see _fold_behavioral_evidence); `exposure_record`s are a structurally
        separate record_type it does not read that way at all. A *new*,
        separate folding rule (_fold_exposure_evidence) may use accumulated
        exposure_records to weakly *dampen* an existing inferred Interest
        when there's been extensive exposure with zero engagement -- see
        user_model/model.py and docs/DECISIONS.md's Sprint 3.6.7 Block 3 ADR.
        """
        now = now or datetime.now(timezone.utc)
        write_type: Literal["new_record", "update_record"]

        existing = self._recent_record(
            user_id=user_id,
            event_id=event_id,
            record_type="exposure_record",
            now=now,
        )

        if existing is not None:
            content = (
                dict(existing.content) if isinstance(existing.content, dict) else {}
            )
            impression_count = int(content.get("impression_count", 1)) + 1
            record = existing.model_copy(
                update={
                    "content": {
                        **content,
                        "impression_count": impression_count,
                        "last_seen_at": now.isoformat(),
                    },
                    "last_accessed": now,
                }
            )
            write_type = "update_record"
        else:
            record = MemoryRecord(
                record_id=uuid4(),
                user_id=user_id,
                record_type="exposure_record",
                content={
                    "entity_id": entity_id,
                    "impression_count": 1,
                    "first_seen_at": now.isoformat(),
                    "last_seen_at": now.isoformat(),
                },
                domain=domain,
                entities=[entity_id],
                source_layer="learning_system",
                created_at=now,
                last_accessed=now,
                decay_weight=1.0,
                operational_ref=event_id,
            )
            write_type = "new_record"

        self._memory_store.write(record, writer="learning_system")
        return MemoryWrite(
            write_id=uuid4(),
            write_type=write_type,
            target="memory",
            content=record,
            source_signal=event_id,
            # A deterministic system fact, not an inferred/interpreted one --
            # confidence=1.0 the same way Memory Inbox confirm/reject
            # (explicit, deliberate) already use 1.0, not FeedbackEngine's
            # ambiguity-scaled range.
            confidence=1.0,
            authorized_at=now,
        )

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
