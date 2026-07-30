from datetime import datetime, timezone
from typing import Literal

from logan_core.contracts import (
    ActiveContext,
    EnrichedEvent,
    EvidenceTrust,
    ReasoningResult,
    UserModel,
)


class ReasoningEngine:
    """Layer 7 — determines the meaning of an event in context. Understanding an event
    does not mean surfacing it (that's the Opportunity Engine's decision downstream).
    Forbidden per spec: writing to Memory, modifying User Model, updating trust scores.
    """

    def reason(
        self,
        event: EnrichedEvent,
        trust: EvidenceTrust,
        user_model: UserModel,
        active_context: ActiveContext,
    ) -> ReasoningResult:
        holding_ids = {h.entity_id for h in user_model.holdings}
        interest_topics = {i.topic for i in user_model.interests}
        event_entity_ids = {e.entity_id for e in event.entities}
        touched_ids = event_entity_ids | set(event.downstream)

        connected_entities = sorted(touched_ids & (holding_ids | interest_topics))
        holds_directly = bool(event_entity_ids & holding_ids)

        significance = event.summary
        if event.change_delta:
            delta = event.change_delta[0]
            significance += f" - changed from {delta.prior_value} to {delta.new_value}"

        if holds_directly:
            personal_relevance_narrative = (
                f"You hold a position connected to {', '.join(sorted(event_entity_ids & holding_ids))}, "
                f"so this is directly relevant to what you're already tracking."
            )
        elif connected_entities:
            personal_relevance_narrative = (
                f"This connects to {', '.join(connected_entities)}, which you follow — "
                f"worth understanding even though it's not a direct holding."
            )
        else:
            personal_relevance_narrative = (
                "Nothing in your current holdings or interests is directly connected to this yet."
            )

        stance: Literal["confirms", "contradicts", "complicates", "new"]
        if event.contradicting:
            stance = "contradicts"
        elif not event.is_new and event.change_delta:
            stance = "confirms" if trust.trust_score >= 0.6 else "complicates"
        else:
            stance = "new"

        actionability: Literal["actionable", "informational", "ambiguous"]
        if trust.trust_score < 0.4:
            actionability = "ambiguous"
        elif holds_directly and trust.trust_score >= 0.6:
            actionability = "actionable"
        else:
            actionability = "informational"

        explanation = f"{significance}. {personal_relevance_narrative}"

        return ReasoningResult(
            event_id=event.event_id,
            significance=significance,
            personal_relevance_narrative=personal_relevance_narrative,
            connected_entities=connected_entities,
            stance=stance,
            actionability=actionability,
            explanation=explanation,
            reasoned_at=datetime.now(timezone.utc),
        )
