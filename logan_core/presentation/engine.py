from datetime import datetime, timezone
from typing import Literal, Optional

from logan_core.contracts import (
    ConclusionConfidence,
    DecisionTraceEntry,
    DeliveredItem,
    PersonalRelevanceResult,
    PolicyResult,
    PrioritizedItem,
    ReasoningResult,
)
from logan_core.contracts.presentation import confidence_label_for

_URGENCY_BY_INTERRUPTION = {
    "alert": "This is moving quickly enough to flag right now.",
    "digest": "Worth reviewing in your next check-in — not urgent enough for an interruption.",
    "none": "No immediate time pressure; surfaced for background awareness.",
}


class PresentationEngine:
    """Layer 13 — chooses surface and format, delivers a complete explanation. Does not
    own content, does not modify scores/policy/priority order, does not write Memory.
    Reads PolicyResult in addition to the layers listed in the original spec's Input
    list, because `required_disclaimers` must appear verbatim in DeliveredItem per the
    Data Contracts validation rule — the original Input list omitted PolicyResult,
    which is otherwise unsatisfiable. Logged as an implementation decision.
    """

    def deliver(
        self,
        prioritized_item: PrioritizedItem,
        reasoning: ReasoningResult,
        confidence: ConclusionConfidence,
        policy_result: PolicyResult,
        personal_relevance_result: Optional[PersonalRelevanceResult] = None,
    ) -> DeliveredItem:
        now = datetime.now(timezone.utc)

        surface: Literal["wheel", "feed_card", "alert", "digest", "background"]
        if prioritized_item.interruption == "alert":
            surface = "alert"
        elif prioritized_item.interruption == "digest":
            surface = "digest"
        elif prioritized_item.visibility == "primary":
            surface = "wheel"
        elif prioritized_item.visibility == "feed":
            surface = "feed_card"
        else:
            surface = "background"

        headline = reasoning.significance[:120]

        return DeliveredItem(
            event_id=prioritized_item.event_id,
            surface=surface,
            headline=headline,
            what_happened=reasoning.significance,
            why_it_matters=reasoning.explanation,
            why_it_matters_to_me=reasoning.personal_relevance_narrative,
            why_now=_URGENCY_BY_INTERRUPTION.get(prioritized_item.interruption, ""),
            confidence_label=confidence_label_for(confidence.confidence_score),
            confidence_score=confidence.confidence_score,
            personal_relevance_result=personal_relevance_result,
            required_disclaimers=policy_result.required_disclaimers,
            delivered_at=now,
            decision_trace=[
                DecisionTraceEntry(
                    layer="presentation",
                    rule=f"surface={surface} from visibility={prioritized_item.visibility}, "
                    f"interruption={prioritized_item.interruption}",
                    timestamp=now,
                )
            ],
        )
