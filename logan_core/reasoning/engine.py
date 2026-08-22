from datetime import datetime, timezone
from typing import Literal

from logan_core.contracts import (
    ActiveContext,
    DecisionTraceEntry,
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
        explicit_interest_topics = {
            i.topic for i in user_model.interests if i.source == "explicit"
        }
        inferred_interest_topics = {
            i.topic for i in user_model.interests if i.source == "inferred"
        }
        event_entity_ids = {e.entity_id for e in event.entities}
        touched_ids = event_entity_ids | set(event.downstream)

        # Explicit interests remain the stronger source of truth (owner
        # decision, behavioral-personalization pass): an entity connected via
        # holdings or an explicit interest keeps the existing full connection
        # signal below; an entity connected *only* via an inferred interest
        # (never also explicit/held) is a separate, weaker signal -- see
        # OpportunityEngine.evaluate()'s "connect" step, which bounds it
        # below the explicit bump rather than treating the two identically.
        connected_explicit = sorted(
            touched_ids & (holding_ids | explicit_interest_topics)
        )
        connected_inferred = sorted(
            (touched_ids & inferred_interest_topics) - set(connected_explicit)
        )
        connected_entities = sorted(set(connected_explicit) | set(connected_inferred))
        holds_directly = bool(event_entity_ids & holding_ids)

        # Sprint 3.6.7 Block 3: the strongest matched inferred Interest.weight
        # among connected_inferred -- lets OpportunityEngine's "connect" step
        # scale an inferred-only connection's relevance with how mature the
        # underlying behavioral evidence actually is (see
        # OpportunityEngine._scale_inferred_relevance), instead of a flat
        # floor regardless of evidence strength. 0.0 when there is no inferred
        # connection at all, matching ReasoningResult's own default.
        inferred_relevance_strength = max(
            (
                i.weight
                for i in user_model.interests
                if i.source == "inferred" and i.topic in connected_inferred
            ),
            default=0.0,
        )

        significance = event.summary
        if event.change_delta:
            delta = event.change_delta[0]
            significance += f" - changed from {delta.prior_value} to {delta.new_value}"

        if holds_directly:
            # Sprint 3.6.6E: wording deliberately says "tracking a holding",
            # not "you hold a position" -- all this layer actually knows is
            # that entity_id is present in user_model.holdings, which today
            # (LOCAL_FOUNDER_USER_ID="demo_user") is hardcoded seed data in
            # backend/app/logan_feed.py, not a real per-user holdings store
            # (ADR-006 remains open) or anything the user explicitly entered
            # through a real flow. "You hold a position" asserts an
            # externally-verified financial fact this system has no way to
            # confirm; "tracking a holding" accurately describes what's
            # actually in the user model, whether that record eventually
            # comes from a real connected/entered holding or today's seed.
            personal_relevance_narrative = (
                f"You're tracking a holding connected to "
                f"{', '.join(sorted(event_entity_ids & holding_ids))}, "
                f"so this is directly relevant to what you already follow."
            )
        elif connected_entities:
            # Sprint 3.6.6E: same truthfulness fix as the holds_directly
            # branch above -- "which you follow" asserts an externally-
            # verified fact (the user actively follows this entity) that
            # this layer cannot confirm. connected_entities is drawn from
            # user_model.interests (also hardcoded seed data today, e.g.
            # AI_SECTOR's source="explicit" in backend/app/logan_feed.py --
            # "explicit" describes how the *demo seed* was authored, not a
            # real user action) and, via downstream ripple, sometimes
            # user_model.holdings. "which you're tracking" accurately
            # describes what's in the user model either way, without
            # overclaiming a verified user behavior.
            personal_relevance_narrative = (
                f"This connects to {', '.join(connected_entities)}, which you're tracking — "
                f"worth understanding even though it's not a direct holding."
            )
        else:
            personal_relevance_narrative = "Nothing in your current holdings or interests is directly connected to this yet."

        stance: Literal["confirms", "contradicts", "complicates", "new"]
        # "contradicts" is currently unreachable: WorldModel never populates
        # event.contradicting (see world_model/model.py's V3.1.4 BATCH-2 note
        # on why a deterministic contradiction rule isn't implementable from
        # the current untyped signal-value model without inventing per-domain
        # semantics). The branch is kept, not removed, so this still routes
        # correctly the moment a real contradiction detector exists.
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
        now = datetime.now(timezone.utc)

        return ReasoningResult(
            event_id=event.event_id,
            significance=significance,
            personal_relevance_narrative=personal_relevance_narrative,
            connected_entities=connected_entities,
            connected_entities_explicit=connected_explicit,
            connected_entities_inferred=connected_inferred,
            inferred_relevance_strength=inferred_relevance_strength,
            stance=stance,
            actionability=actionability,
            explanation=explanation,
            reasoned_at=now,
            decision_trace=[
                DecisionTraceEntry(
                    layer="reasoning",
                    rule=f"stance={stance}, actionability={actionability} "
                    f"(holds_directly={holds_directly}, trust_score={trust.trust_score:.2f})",
                    confidence=trust.trust_score,
                    evidence=[
                        f"explicit_connections={connected_explicit}",
                        f"inferred_connections={connected_inferred}",
                        f"inferred_relevance_strength={inferred_relevance_strength:.2f}",
                    ],
                    timestamp=now,
                )
            ],
        )
