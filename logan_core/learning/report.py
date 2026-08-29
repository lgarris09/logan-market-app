"""V2.3B Personal Learning Phase 1 -- makes the existing, already-live
UserModel/MemoryStore/FeedbackEngine/LearningEngine pipeline (see
user_model/model.py, memory/store.py, feedback/engine.py, learning/engine.py)
inspectable and explainable, without adding a second, parallel "learned
profile" concept. Every field this module produces is a plain-language
rendering of data those existing layers already compute (Interest.weight,
BehaviorPattern.confidence/evidence_count/last_reinforced,
UserModel.model_confidence) -- this is presentation of an existing
conclusion, not a new inference.

Read-only: this module never writes to Memory or UserModel (that remains
LearningEngine's sole privilege, per ADR-019/the Learning System's layer
ownership) -- it only reads the same `memory_records`/`UserModel` the real
pipeline already produced for this poll.
"""

from datetime import datetime, timezone
from typing import Optional

from logan_core.contracts import (
    LearnedTrait,
    LearningReport,
    MemoryRecord,
    NotLearnedTrait,
    ObservedBehaviorSummary,
    UserModel,
)
from logan_core.user_model import MIN_REPEAT_EVIDENCE, suppressed_entities

# Mirrors FeedbackEngine's own interaction_type vocabulary (feedback/engine.py)
# -- plain-language verbs for the "Observed" section. Any interaction_type
# not listed here (there are none today; kept as a safe fallback for a
# future addition) falls back to a generic "interacted with" phrasing rather
# than crashing on an unrecognized key.
_OBSERVED_VERB = {
    "view": "Opened",
    "click": "Clicked into",
    "save": "Saved",
    "share": "Shared",
    "watch": "Watched",
    "remind": "Asked to be reminded about",
    "ask_followup": "Asked a follow-up question about",
    "dismiss": "Dismissed",
}

# Standing, honest statements about what this architecture deliberately does
# not attempt in Phase 1 -- never per-user data, never implies a capability
# that doesn't exist. Kept as a module-level constant (not computed) since
# it describes the architecture itself, not any one user's history.
ARCHITECTURE_NOTES = [
    "STRATUS learns per-entity interest and engagement patterns only -- it "
    "does not yet generalize across related entities into a broader theme "
    "or sector preference (e.g. it will not conclude 'prefers semiconductor "
    "stocks' from repeated engagement with one semiconductor ticker alone).",
    "A single interested-intent observation never creates a preference -- "
    f"at least {MIN_REPEAT_EVIDENCE} independent qualifying observations are "
    "required before any inferred trait is created.",
    "Personal Learning does not yet influence which opportunities are "
    "surfaced, ranked, or notified beyond the existing personal_relevance "
    "input already in place before this report existed -- this report adds "
    "visibility and correction, not new ranking influence.",
]


def _observed_summaries(
    memory_records: list[MemoryRecord],
) -> list[ObservedBehaviorSummary]:
    counts: dict[tuple[str, str], int] = {}
    for record in memory_records:
        if record.record_type != "feedback_record":
            continue
        content = record.content
        if not isinstance(content, dict):
            continue
        interaction_type = content.get("interaction_type")
        if not interaction_type:
            continue
        for entity_id in record.entities:
            counts[(entity_id, interaction_type)] = (
                counts.get((entity_id, interaction_type), 0) + 1
            )

    summaries = []
    for (entity_id, interaction_type), count in sorted(counts.items()):
        verb = _OBSERVED_VERB.get(
            interaction_type, f"Recorded a {interaction_type!r} on"
        )
        times = "time" if count == 1 else "times"
        summaries.append(
            ObservedBehaviorSummary(
                entity_id=entity_id,
                description=f"{verb} {entity_id} {count} {times}",
                count=count,
            )
        )
    return summaries


def _qualifying_evidence_by_entity(
    memory_records: list[MemoryRecord],
) -> dict[str, tuple[int, datetime]]:
    """The same "interested-intent feedback_records grouped by entity_id"
    reading _fold_behavioral_evidence (user_model/model.py) uses to decide
    whether a trait qualifies -- recomputed here read-only, for the
    "Not learned" section, so this report can honestly say *why* a candidate
    with some real evidence still didn't become a learned trait. Deliberately
    only counts (count, latest_at); this report never recomputes or
    duplicates the actual weight/decay/maturity math, which stays solely
    UserModelBuilder's -- it only needs enough to explain a decision already
    made.
    """
    by_entity: dict[str, tuple[int, datetime]] = {}
    for record in memory_records:
        if record.record_type != "feedback_record":
            continue
        content = record.content
        if (
            not isinstance(content, dict)
            or content.get("inferred_intent") != "interested"
        ):
            continue
        for entity_id in record.entities:
            count, latest = by_entity.get(entity_id, (0, record.created_at))
            by_entity[entity_id] = (count + 1, max(latest, record.created_at))
    return by_entity


def _learned_traits(user_model: UserModel) -> list[LearnedTrait]:
    behavior_by_entity = {
        b.label[len("engaged_with_") :]: b
        for b in user_model.established_behaviors
        if b.label.startswith("engaged_with_")
    }

    traits: list[LearnedTrait] = []
    for interest in user_model.interests:
        behavior = behavior_by_entity.get(interest.topic)
        if interest.source == "explicit":
            why = "You explicitly declared this interest."
            what_would_change_this = (
                "This is explicit and does not decay or get relearned automatically -- "
                "it only changes if you update your declared interests."
            )
        else:
            evidence_count = behavior.evidence_count if behavior else None
            evidence_phrase = (
                f"{evidence_count} qualifying engagement(s)"
                if evidence_count is not None
                else "repeated qualifying engagement"
            )
            why = (
                f"Based on {evidence_phrase} with {interest.topic}, most recently on "
                f"{interest.last_updated.date().isoformat()}."
            )
            what_would_change_this = (
                f"This fades over roughly two weeks without further engagement with "
                f"{interest.topic}, or you can tell STRATUS this isn't relevant."
            )
        traits.append(
            LearnedTrait(
                entity_id=interest.topic,
                kind="interest",
                source=interest.source,
                description=f"Interest in {interest.topic}"
                + (f" ({interest.domain})" if interest.domain else ""),
                strength=interest.weight,
                evidence_count=behavior.evidence_count if behavior else 0,
                first_learned_at=interest.created_at,
                last_updated_at=interest.last_updated,
                why=why,
                what_would_change_this=what_would_change_this,
            )
        )

    interest_entities = {i.topic for i in user_model.interests}
    for behavior in user_model.established_behaviors:
        if not behavior.label.startswith("engaged_with_"):
            continue
        entity_id = behavior.label[len("engaged_with_") :]
        if entity_id in interest_entities:
            # Already represented by its matching Interest above -- this
            # BehaviorPattern is the same underlying evidence, not a second
            # independent conclusion.
            continue
        last_updated = behavior.last_reinforced or user_model.last_updated
        traits.append(
            LearnedTrait(
                entity_id=entity_id,
                kind="behavior",
                source="inferred",
                description=behavior.description,
                strength=behavior.confidence,
                evidence_count=behavior.evidence_count,
                first_learned_at=None,
                last_updated_at=last_updated,
                why=(
                    f"Based on {behavior.evidence_count} qualifying engagement(s) with "
                    f"{entity_id}, most recently on {last_updated.date().isoformat()}."
                ),
                what_would_change_this=(
                    f"This fades over roughly two weeks without further engagement with "
                    f"{entity_id}, or you can tell STRATUS this isn't relevant."
                ),
            )
        )

    return traits


def _not_learned_traits(
    memory_records: list[MemoryRecord], learned: list[LearnedTrait]
) -> list[NotLearnedTrait]:
    learned_entities = {t.entity_id for t in learned}
    suppressed_at = suppressed_entities(memory_records)
    qualifying = _qualifying_evidence_by_entity(memory_records)

    not_learned: list[NotLearnedTrait] = []
    for entity_id, (count, latest_at) in sorted(qualifying.items()):
        if entity_id in learned_entities:
            continue
        cutoff = suppressed_at.get(entity_id)
        if cutoff is not None and latest_at <= cutoff:
            not_learned.append(
                NotLearnedTrait(
                    candidate=entity_id,
                    reason=(
                        f"Suppressed by an explicit correction on "
                        f"{cutoff.date().isoformat()} -- no qualifying engagement since."
                    ),
                )
            )
        elif count < MIN_REPEAT_EVIDENCE:
            not_learned.append(
                NotLearnedTrait(
                    candidate=entity_id,
                    reason=(
                        f"Only {count} qualifying observation(s) "
                        f"({MIN_REPEAT_EVIDENCE} required) to treat this as a preference."
                    ),
                )
            )
        else:
            not_learned.append(
                NotLearnedTrait(
                    candidate=entity_id,
                    reason=(
                        "No longer supported by recent evidence -- this decayed or was "
                        f"pruned since its last qualifying engagement on "
                        f"{latest_at.date().isoformat()}."
                    ),
                )
            )
    return not_learned


def build_learning_report(
    user_id: str,
    user_model: UserModel,
    memory_records: list[MemoryRecord],
    now: Optional[datetime] = None,
) -> LearningReport:
    """The one function this module exposes: a complete, human-readable
    Personal Learning inspection report for `user_id`, built entirely from
    the `UserModel` the real pipeline already rebuilt this poll and the same
    `memory_records` it was built from -- never a second, independent
    computation of what STRATUS believes."""
    now = now or datetime.now(timezone.utc)
    learned = _learned_traits(user_model)
    return LearningReport(
        user_id=user_id,
        generated_at=now,
        model_confidence=user_model.model_confidence,
        observed=_observed_summaries(memory_records),
        learned=learned,
        not_learned=_not_learned_traits(memory_records, learned),
        architecture_notes=list(ARCHITECTURE_NOTES),
    )
