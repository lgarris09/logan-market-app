from datetime import datetime, timezone
from typing import Literal, Optional

from logan_core.contracts import (
    BehaviorPattern,
    Domain,
    DomainPref,
    Holding,
    Interest,
    MemoryRecord,
    UserModel,
)

# The smallest possible definition of "repeated" rather than "isolated" --
# exactly one qualifying record is, by definition, a single occurrence, not
# a pattern. Not a tuned/weighted threshold (see PrioritizationEngine's own
# FATIGUE_LIMIT=5 for the codebase's existing precedent of a small, plainly-
# reasoned integer gate rather than a data-derived one): "more than one" is
# the literal minimum meaning of "repeated."
MIN_REPEAT_EVIDENCE = 2


class UserModelBuilder:
    """Layer 6a — Logan's durable interpretation of who the user is, built from
    retained Memory evidence. Never updates itself from raw events or clicks — only
    ever rebuilt from MemoryRecord[] supplied by the Memory System, which itself
    only accepts writes from the Learning System.
    """

    def seed(
        self,
        user_id: str,
        holdings: Optional[list[Holding]] = None,
        interests: Optional[list[Interest]] = None,
        risk_tolerance: Literal[
            "conservative", "moderate", "aggressive", "unknown"
        ] = "unknown",
    ) -> UserModel:
        now = datetime.now(timezone.utc)
        domains = {h.domain for h in (holdings or [])} | {
            i.domain for i in (interests or [])
        }
        return UserModel(
            user_id=user_id,
            interests=interests or [],
            holdings=holdings or [],
            risk_tolerance=risk_tolerance,
            domain_preferences=[
                DomainPref(domain=d, active=True, weight=0.5, last_updated=now)
                for d in domains
            ],
            model_confidence=0.5,
            last_updated=now,
            version=1,
        )

    def build(
        self, user_id: str, memory_records: list[MemoryRecord], base: UserModel
    ) -> UserModel:
        """Rebuild the UserModel by folding in preference_signal / user_statement
        memory records (increases model_confidence as evidence accumulates), and by
        folding in repeated behavioral evidence from feedback_record memory records
        (see _fold_behavioral_evidence) into established_behaviors,
        domain_preferences, and Interest(source="inferred") only.

        Explicit holdings/interests/risk_tolerance are always copied through from
        `base` untouched -- behavioral evidence updates only the inferred/behavioral
        portions of the model, never overwrites or weakens an explicit one.
        `inferred_expertise` is deliberately left untouched: view/click/dwell
        signals evidence attention, not demonstrated expertise.
        """
        preference_records = [
            r
            for r in memory_records
            if r.record_type in ("preference_signal", "user_statement")
        ]
        evidence_count = len(preference_records)
        model_confidence = min(0.5 + evidence_count * 0.05, 1.0)

        established_behaviors, domain_preferences, interests = (
            _fold_behavioral_evidence(memory_records, base)
        )

        return base.model_copy(
            update={
                "model_confidence": model_confidence,
                "established_behaviors": established_behaviors,
                "domain_preferences": domain_preferences,
                "interests": interests,
                "last_updated": datetime.now(timezone.utc),
                "version": base.version + 1,
            }
        )


def _fold_behavioral_evidence(
    memory_records: list[MemoryRecord], base: UserModel
) -> tuple[list[BehaviorPattern], list[DomainPref], list[Interest]]:
    """Groups feedback_record evidence by (domain, entity_id) and, only for pairs
    with at least MIN_REPEAT_EVIDENCE independent "interested"-intent records,
    updates established_behaviors/domain_preferences/inferred Interest for that
    pair. "Meaningful" reuses FeedbackEngine's own interpretation verbatim
    (inferred_intent == "interested", the strongest positive signal it produces)
    -- no new confidence threshold or weighting is introduced here. Confidence/
    weight values written below are the max intent_confidence FeedbackEngine
    itself already computed for that pair's qualifying records, not a new number.
    """
    now = datetime.now(timezone.utc)

    by_pair: dict[tuple[Optional[Domain], str], list[dict]] = {}
    for record in memory_records:
        if record.record_type != "feedback_record":
            continue
        content = record.content
        if not isinstance(content, dict):
            continue
        if content.get("inferred_intent") != "interested":
            continue
        for entity_id in record.entities:
            by_pair.setdefault((record.domain, entity_id), []).append(content)

    established_behaviors = list(base.established_behaviors)
    behavior_index = {b.label: i for i, b in enumerate(established_behaviors)}
    domain_preferences = list(base.domain_preferences)
    domain_pref_index = {d.domain: i for i, d in enumerate(domain_preferences)}
    interests = list(base.interests)
    # Explicit holdings and explicit interests are the stronger source of
    # truth (owner decision) -- an entity already covered by either never
    # gets a competing inferred Interest, and an existing explicit Interest
    # is never created, overwritten, or weakened here.
    explicitly_known = {h.entity_id for h in base.holdings} | {
        i.topic for i in interests if i.source == "explicit"
    }
    inferred_index = {
        i.topic: idx for idx, i in enumerate(interests) if i.source == "inferred"
    }

    for (domain, entity_id), evidences in by_pair.items():
        if len(evidences) < MIN_REPEAT_EVIDENCE:
            continue  # isolated -- one click/view is not a preference

        max_confidence = max(e["intent_confidence"] for e in evidences)

        label = f"engaged_with_{entity_id}"
        description = f"Repeated interested-intent interactions with {entity_id}" + (
            f" ({domain})" if domain else ""
        )
        pattern = BehaviorPattern(
            label=label, description=description, confidence=max_confidence
        )
        if label in behavior_index:
            established_behaviors[behavior_index[label]] = pattern
        else:
            behavior_index[label] = len(established_behaviors)
            established_behaviors.append(pattern)

        if domain is not None:
            if domain in domain_pref_index:
                idx = domain_pref_index[domain]
                if not domain_preferences[idx].active:
                    domain_preferences[idx] = domain_preferences[idx].model_copy(
                        update={"active": True, "last_updated": now}
                    )
            else:
                domain_pref_index[domain] = len(domain_preferences)
                domain_preferences.append(
                    DomainPref(domain=domain, active=True, weight=0.5, last_updated=now)
                )

            if entity_id not in explicitly_known:
                if entity_id in inferred_index:
                    idx = inferred_index[entity_id]
                    interests[idx] = interests[idx].model_copy(
                        update={"weight": max_confidence, "last_updated": now}
                    )
                else:
                    inferred_index[entity_id] = len(interests)
                    interests.append(
                        Interest(
                            domain=domain,
                            topic=entity_id,
                            weight=max_confidence,
                            source="inferred",
                            created_at=now,
                            last_updated=now,
                        )
                    )

    return established_behaviors, domain_preferences, interests
