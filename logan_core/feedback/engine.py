from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from logan_core.contracts import FeedbackSignal


class FeedbackEngine:
    """Layer 14 — observes user responses and interprets their meaning. A click is not
    confirmation; behavior is interpreted before anything updates. Forbidden per spec:
    writing to Memory or User Model directly, updating weights directly.
    """

    def interpret(
        self, event_id: UUID, interaction_type: str, duration_ms: Optional[int] = None
    ) -> FeedbackSignal:
        now = datetime.now(timezone.utc)

        if interaction_type == "dismiss":
            inferred_intent, intent_confidence = "dismissing", 0.80
        elif interaction_type in ("save", "share", "watch"):
            # "watch" (add to watchlist) is an explicit, sustained-interest action,
            # same confidence tier as save/share — not an ML-derived signal, just the
            # same deterministic mapping every other explicit action already gets.
            inferred_intent, intent_confidence = "interested", 0.85
        elif interaction_type == "remind":
            # "remind" signals interest deferred to a later time, not immediate action —
            # still explicit and high-confidence, but distinct enough from save/share
            # that it doesn't share their exact tier.
            inferred_intent, intent_confidence = "interested", 0.75
        elif interaction_type == "click":
            inferred_intent, intent_confidence = "curious", 0.55
        elif interaction_type == "view":
            if duration_ms is None:
                inferred_intent, intent_confidence = "unknown", 0.30
            elif duration_ms >= 8000:
                inferred_intent, intent_confidence = "interested", 0.65
            elif duration_ms >= 2000:
                inferred_intent, intent_confidence = "curious", 0.55
            else:
                inferred_intent, intent_confidence = "accidental", 0.55
        else:
            inferred_intent, intent_confidence = "unknown", 0.30

        if intent_confidence < 0.50:
            inferred_intent = "unknown"

        return FeedbackSignal(
            event_id=event_id,
            interaction_type=interaction_type,
            inferred_intent=inferred_intent,
            intent_confidence=intent_confidence,
            duration_ms=duration_ms,
            raw_interaction=interaction_type,
            observed_at=now,
        )

    def confirm_memory_inbox(self, event_id: UUID) -> FeedbackSignal:
        """Memory Inbox 'confirm' action — an explicit, maximum-confidence signal that
        the Learning System should process immediately rather than on its normal
        delayed cadence (ADR-019).
        """
        return FeedbackSignal(
            event_id=event_id,
            interaction_type="act",
            inferred_intent="interested",
            intent_confidence=1.0,
            raw_interaction="memory_inbox_confirm",
            observed_at=datetime.now(timezone.utc),
        )

    def reject_memory_inbox(self, event_id: UUID) -> FeedbackSignal:
        """Memory Inbox 'reject' action — see confirm_memory_inbox (ADR-019)."""
        return FeedbackSignal(
            event_id=event_id,
            interaction_type="act",
            inferred_intent="dismissing",
            intent_confidence=1.0,
            raw_interaction="memory_inbox_reject",
            observed_at=datetime.now(timezone.utc),
        )
