from datetime import datetime, timezone
from typing import Literal, Optional

from logan_core.contracts import (
    BehaviorPattern,
    DecisionTraceEntry,
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

# --- Sprint 3.6.7 Block 3: maturity scaling, decay, and exposure-fatigue ---
# Reasoned, bounded constants -- no existing spec value applies to any of
# these (unlike e.g. the 0.6/0.5 relevance bumps, which reuse existing
# anchors per ADR-048). See docs/DECISIONS.md's Sprint 3.6.7 Block 3 ADR for
# the full rationale each is documented against.

# How much an inferred Interest's weight / a BehaviorPattern's confidence
# grows per *additional* qualifying "interested" record beyond
# MIN_REPEAT_EVIDENCE, capped by MAX_MATURITY_BONUS -- lets genuinely
# repeated engagement measurably exceed a single strong observation's own
# confidence, instead of the flat max() this used before Block 3 (which
# saturated at MIN_REPEAT_EVIDENCE and never grew further). 5 additional
# qualifying events (MAX_MATURITY_BONUS / MATURITY_STEP) is a deliberately
# small, slow-growing ceiling -- one active session cannot alone mature a
# behavior past it (see requirement: "maximum behavioral influence").
MATURITY_STEP = 0.02
MAX_MATURITY_BONUS = 0.10
# Leaves headroom below 1.0 and below MemoryRecord/Interest's own [0,1]
# bound -- explicit evidence (FeedbackEngine's memory-inbox-confirm path,
# intent_confidence=1.0) remains the only way to reach the true ceiling.
MAX_INFERRED_INTEREST_WEIGHT = 0.90

# Time-based decay for inferred/behavioral evidence only -- explicit
# holdings/interests/risk_tolerance are never decayed (see build()'s own
# docstring below). A stale, unreinforced inferred interest/behavior fades
# rather than staying at full strength forever, weighted against the most
# recent *qualifying* evidence's own timestamp (not "time since this
# UserModel was last rebuilt," which happens on every pipeline poll and
# would otherwise make decay meaningless). Deliberately a much slower
# half-life than EvidenceTrustEngine's 6-hour RECENCY_HALF_LIFE_HOURS
# (evidence_trust/trust.py) -- that constant answers "how stale is this
# specific market signal," a fundamentally faster-moving question than "does
# this user still care about this," which this constant answers instead.
BEHAVIORAL_HALF_LIFE_DAYS = 14.0
# Below this weight/confidence, an inferred Interest/BehaviorPattern is
# pruned entirely rather than kept as a near-zero entry cluttering the model.
DECAY_PRUNE_FLOOR = 0.10

# Exposure-fatigue dampening: repeated exposure (impressions) with zero
# meaningful engagement has at most a weak negative effect, and only on an
# *existing* inferred Interest built from real positive evidence -- this
# never manufactures a negative interest out of mere non-engagement (an
# entity the user has simply never interacted with is not "disliked," it's
# unobserved -- see requirement: IGNORE must not be naively inferred from
# every non-click). EXPOSURE_FATIGUE_THRESHOLD reuses PrioritizationEngine's
# own FATIGUE_LIMIT=5 (prioritization/engine.py) as the existing "repeated"
# precedent in this codebase rather than inventing a new number.
EXPOSURE_FATIGUE_THRESHOLD = 5
EXPOSURE_FATIGUE_PENALTY = 0.05


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
            # Sprint 3.6.8 Block 2 review finding (not a behavior change):
            # DomainPref.weight is a required contract field (contracts/
            # user_model.py) with no established semantic meaning anywhere in
            # the spec or codebase, and -- confirmed by inspection -- no
            # consumer reads domain_preferences[].weight anywhere in
            # Reasoning/OpportunityEngine/Policy/Prioritization today. This
            # 0.5 is therefore an inert placeholder satisfying the required
            # field, not a computed or reasoned behavioral signal (unlike
            # model_confidence's own 0.5 below, which is a documented,
            # evidence-scaled floor -- see build()'s formula). It is never
            # updated again after creation (see _fold_behavioral_evidence
            # below, which only ever flips `active`/`last_updated` for an
            # existing DomainPref). Left as-is rather than inventing new
            # weighting semantics here -- a real per-domain weighting design
            # is out of this block's scope; flagged in docs/DECISIONS.md's
            # Sprint 3.6.8 Block 2 ADR as a known pre-existing gap instead.
            domain_preferences=[
                DomainPref(domain=d, active=True, weight=0.5, last_updated=now)
                for d in domains
            ],
            model_confidence=0.5,
            last_updated=now,
            version=1,
        )

    def build(
        self,
        user_id: str,
        memory_records: list[MemoryRecord],
        base: UserModel,
        now: Optional[datetime] = None,
    ) -> UserModel:
        """Rebuild the UserModel by folding in preference_signal / user_statement
        memory records (increases model_confidence as evidence accumulates), by
        folding in repeated behavioral evidence from feedback_record memory records
        (see _fold_behavioral_evidence) into established_behaviors,
        domain_preferences, and Interest(source="inferred") only, and (Sprint 3.6.7
        Block 3) by applying time-based decay to stale inferred evidence and a
        weak dampening effect from high-exposure/zero-engagement entities (see
        _fold_exposure_evidence).

        Explicit holdings/interests/risk_tolerance are always copied through from
        `base` untouched -- behavioral evidence updates only the inferred/behavioral
        portions of the model, never overwrites or weakens an explicit one.
        `inferred_expertise` is deliberately left untouched: view/click/dwell
        signals evidence attention, not demonstrated expertise.

        `memory_records` is always the *full* accumulated history (MemoryStore has
        no incremental-since-last-build query), not just what's new since the last
        call -- every qualifying pair is therefore recomputed fresh each call, with
        decay embedded via each pair's *most recent* qualifying evidence timestamp
        rather than "time since this UserModel was last rebuilt" (see
        _weight_for_evidence). A pair no longer represented in memory_records at all
        (e.g. its records aged out of MemoryStore's bounded-history compaction) is
        decayed/pruned separately, from its own last_reinforced/last_updated.

        `now` defaults to the real current time; every existing caller omits
        it, unaffected. Tests that need decay/maturity to be deterministic
        relative to fixture timestamps (rather than real wall-clock time
        passing between when a fixture was written and when the suite runs
        it -- Sprint 3.6.7 Block 2's own lesson, see test_pipeline_market_data.py)
        should pass it explicitly.
        """
        now = now or datetime.now(timezone.utc)
        decision_trace: list[DecisionTraceEntry] = []

        preference_records = [
            r
            for r in memory_records
            if r.record_type in ("preference_signal", "user_statement")
        ]
        evidence_count = len(preference_records)
        model_confidence = min(0.5 + evidence_count * 0.05, 1.0)

        (
            established_behaviors,
            domain_preferences,
            interests,
            latest_engagement_by_entity,
        ) = _fold_behavioral_evidence(memory_records, base, now, decision_trace)
        established_behaviors, interests = _fold_exposure_evidence(
            memory_records,
            established_behaviors,
            interests,
            base.holdings,
            latest_engagement_by_entity,
            now,
            decision_trace,
        )

        return base.model_copy(
            update={
                "model_confidence": model_confidence,
                "established_behaviors": established_behaviors,
                "domain_preferences": domain_preferences,
                "interests": interests,
                "last_updated": now,
                "version": base.version + 1,
                "decision_trace": decision_trace,
            }
        )


def _weight_for_evidence(
    max_confidence: float,
    evidence_count: int,
    latest_evidence_at: datetime,
    now: datetime,
) -> float:
    """Sprint 3.6.7 Block 3 -- combines maturity scaling (more repeated
    qualifying evidence -> higher weight, bounded) with recency decay (the
    longer since the *last* qualifying evidence, the more this fades),
    computed directly from real evidence timestamps rather than from a
    separately-tracked "last rebuilt" state. See the module-level constants'
    own comments for the rationale behind each number.
    """
    maturity_bonus = min(
        max(evidence_count - MIN_REPEAT_EVIDENCE, 0) * MATURITY_STEP,
        MAX_MATURITY_BONUS,
    )
    raw_weight = min(max_confidence + maturity_bonus, MAX_INFERRED_INTEREST_WEIGHT)

    age_days = max((now - latest_evidence_at).total_seconds() / 86400.0, 0.0)
    decay_factor = 0.5 ** (age_days / BEHAVIORAL_HALF_LIFE_DAYS)
    return raw_weight * decay_factor


def _decay_orphaned_entries(
    established_behaviors: list[BehaviorPattern],
    interests: list[Interest],
    live_labels: set[str],
    live_topics: set[str],
    now: datetime,
    decision_trace: list[DecisionTraceEntry],
) -> tuple[list[BehaviorPattern], list[Interest]]:
    """Applies plain age-based decay (from each entry's own
    last_reinforced/last_updated, since it has no live evidence this call to
    recompute recency from) to established_behaviors/inferred Interests that
    were NOT recomputed by _fold_behavioral_evidence this call -- e.g. their
    underlying feedback_records aged out of MemoryStore's bounded-history
    compaction. Prunes entries that decay below DECAY_PRUNE_FLOOR. Entries
    that *were* recomputed this call (live_labels/live_topics) are left
    untouched here -- they already carry their own recency-aware weight from
    _weight_for_evidence.
    """
    decayed_behaviors = []
    for pattern in established_behaviors:
        if pattern.label in live_labels:
            decayed_behaviors.append(pattern)
            continue
        reference_time = pattern.last_reinforced or now
        age_days = max((now - reference_time).total_seconds() / 86400.0, 0.0)
        decayed_confidence = pattern.confidence * 0.5 ** (
            age_days / BEHAVIORAL_HALF_LIFE_DAYS
        )
        if decayed_confidence < DECAY_PRUNE_FLOOR:
            decision_trace.append(
                DecisionTraceEntry(
                    layer="user_model",
                    rule=f"decay: pruned established_behavior {pattern.label!r} "
                    f"(no reinforcing evidence, confidence decayed to "
                    f"{decayed_confidence:.2f} < {DECAY_PRUNE_FLOOR})",
                    timestamp=now,
                )
            )
            continue
        decayed_behaviors.append(
            pattern.model_copy(update={"confidence": decayed_confidence})
        )

    decayed_interests = []
    for interest in interests:
        if interest.source == "explicit" or interest.topic in live_topics:
            decayed_interests.append(interest)
            continue
        age_days = max((now - interest.last_updated).total_seconds() / 86400.0, 0.0)
        decayed_weight = interest.weight * 0.5 ** (age_days / BEHAVIORAL_HALF_LIFE_DAYS)
        if decayed_weight < DECAY_PRUNE_FLOOR:
            decision_trace.append(
                DecisionTraceEntry(
                    layer="user_model",
                    rule=f"decay: pruned inferred Interest {interest.topic!r} "
                    f"(no reinforcing evidence, weight decayed to "
                    f"{decayed_weight:.2f} < {DECAY_PRUNE_FLOOR})",
                    timestamp=now,
                )
            )
            continue
        decayed_interests.append(interest.model_copy(update={"weight": decayed_weight}))

    return decayed_behaviors, decayed_interests


def _fold_behavioral_evidence(
    memory_records: list[MemoryRecord],
    base: UserModel,
    now: datetime,
    decision_trace: list[DecisionTraceEntry],
) -> tuple[
    list[BehaviorPattern], list[DomainPref], list[Interest], dict[str, datetime]
]:
    """Groups feedback_record evidence by (domain, entity_id) and, only for pairs
    with at least MIN_REPEAT_EVIDENCE independent "interested"-intent records,
    updates established_behaviors/domain_preferences/inferred Interest for that
    pair. "Meaningful" reuses FeedbackEngine's own interpretation verbatim
    (inferred_intent == "interested", the strongest positive signal it produces)
    -- no new confidence threshold or weighting is introduced here. Confidence/
    weight values are maturity- and recency-scaled by _weight_for_evidence (Sprint
    3.6.7 Block 3), not simply the max intent_confidence FeedbackEngine computed.
    """
    by_pair: dict[tuple[Optional[Domain], str], list[tuple[dict, datetime]]] = {}
    for record in memory_records:
        if record.record_type != "feedback_record":
            continue
        content = record.content
        if not isinstance(content, dict):
            continue
        if content.get("inferred_intent") != "interested":
            continue
        for entity_id in record.entities:
            by_pair.setdefault((record.domain, entity_id), []).append(
                (content, record.created_at)
            )

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

    live_labels: set[str] = set()
    live_topics: set[str] = set()
    latest_engagement_by_entity: dict[str, datetime] = {}

    for (domain, entity_id), evidences in by_pair.items():
        latest_evidence_at = max(created_at for _, created_at in evidences)
        latest_engagement_by_entity[entity_id] = max(
            latest_engagement_by_entity.get(entity_id, latest_evidence_at),
            latest_evidence_at,
        )
        if len(evidences) < MIN_REPEAT_EVIDENCE:
            continue  # isolated -- one click/view is not a preference

        max_confidence = max(e["intent_confidence"] for e, _ in evidences)
        evidence_count = len(evidences)
        scaled = _weight_for_evidence(
            max_confidence, evidence_count, latest_evidence_at, now
        )

        label = f"engaged_with_{entity_id}"
        live_labels.add(label)
        description = f"Repeated interested-intent interactions with {entity_id}" + (
            f" ({domain})" if domain else ""
        )
        pattern = BehaviorPattern(
            label=label,
            description=description,
            confidence=scaled,
            evidence_count=evidence_count,
            last_reinforced=latest_evidence_at,
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
                # See seed()'s own comment above -- weight=0.5 here is the
                # same inert contract-required placeholder, not a reasoned
                # behavioral value; nothing downstream reads it.
                domain_preferences.append(
                    DomainPref(domain=domain, active=True, weight=0.5, last_updated=now)
                )

            if entity_id not in explicitly_known:
                live_topics.add(entity_id)
                if entity_id in inferred_index:
                    idx = inferred_index[entity_id]
                    interests[idx] = interests[idx].model_copy(
                        update={"weight": scaled, "last_updated": now}
                    )
                else:
                    inferred_index[entity_id] = len(interests)
                    interests.append(
                        Interest(
                            domain=domain,
                            topic=entity_id,
                            weight=scaled,
                            source="inferred",
                            created_at=now,
                            last_updated=now,
                        )
                    )

    established_behaviors, interests = _decay_orphaned_entries(
        established_behaviors, interests, live_labels, live_topics, now, decision_trace
    )

    # Final floor pass: applies uniformly whether an entry's low confidence/
    # weight came from _weight_for_evidence's own recency decay (very stale
    # evidence still present in memory_records) or from _decay_orphaned_entries
    # above -- one consistent rule for "too faint to keep," checked once,
    # rather than duplicating the threshold check at every place a value
    # could end up low.
    kept_behaviors = []
    for pattern in established_behaviors:
        if pattern.confidence < DECAY_PRUNE_FLOOR:
            decision_trace.append(
                DecisionTraceEntry(
                    layer="user_model",
                    rule=f"decay: pruned established_behavior {pattern.label!r} "
                    f"(confidence {pattern.confidence:.2f} < {DECAY_PRUNE_FLOOR})",
                    timestamp=now,
                )
            )
            continue
        kept_behaviors.append(pattern)

    kept_interests = []
    for interest in interests:
        if interest.source == "inferred" and interest.weight < DECAY_PRUNE_FLOOR:
            decision_trace.append(
                DecisionTraceEntry(
                    layer="user_model",
                    rule=f"decay: pruned inferred Interest {interest.topic!r} "
                    f"(weight {interest.weight:.2f} < {DECAY_PRUNE_FLOOR})",
                    timestamp=now,
                )
            )
            continue
        kept_interests.append(interest)

    return (
        kept_behaviors,
        domain_preferences,
        kept_interests,
        latest_engagement_by_entity,
    )


# How much more recent an entity's last impression must be than its last
# qualifying engagement before "we kept showing you this and you stopped
# reacting" is treated as real signal rather than an ordinary, still-active
# engagement pattern (a user who engaged yesterday and was shown the same
# card again today is not "fatigued," just mid-conversation with it).
EXPOSURE_FATIGUE_GRACE_PERIOD_DAYS = 1.0


def _fold_exposure_evidence(
    memory_records: list[MemoryRecord],
    established_behaviors: list[BehaviorPattern],
    interests: list[Interest],
    holdings: list[Holding],
    latest_engagement_by_entity: dict[str, datetime],
    now: datetime,
    decision_trace: list[DecisionTraceEntry],
) -> tuple[list[BehaviorPattern], list[Interest]]:
    """Sprint 3.6.7 Block 3 -- weak, bounded dampening: an entity that
    already has an *existing* inferred Interest (built from real prior
    "interested"-intent evidence -- this never creates one from scratch),
    but has since accumulated >= EXPOSURE_FATIGUE_THRESHOLD impressions with
    its most recent impression at least EXPOSURE_FATIGUE_GRACE_PERIOD_DAYS
    *after* its last qualifying engagement, has that interest's weight (and
    matching established_behaviors confidence) reduced by a small fixed
    EXPOSURE_FATIGUE_PENALTY, floored at 0.0 and pruned below
    DECAY_PRUNE_FLOOR exactly like ordinary decay.

    The recency comparison (not just a raw lifetime impression count) is the
    load-bearing guardrail: memory_records is always the full accumulated
    history, so a lifetime impression count alone would eventually cross the
    threshold for almost any actively-engaged entity too, incorrectly
    punishing sustained genuine interest. Only exposure that continues to
    accumulate *after* engagement has gone quiet counts here.

    Deliberately never touches explicit holdings/interests, and never
    dampens an entity purely because it was never engaged with at all (no
    existing inferred Interest means nothing here can fire for it) --
    "impressions alone cannot strongly increase relevance" has a
    mirror-image guardrail here: impressions can only ever weakly *decrease*
    an already-established inferred interest as engagement goes quiet, never
    manufacture disinterest in an entity the user simply hasn't acted on
    either way (unobserved is not the same as ignored).
    """
    exposure_counts: dict[str, int] = {}
    latest_impression_by_entity: dict[str, datetime] = {}
    for record in memory_records:
        if record.record_type != "exposure_record":
            continue
        content = record.content
        if not isinstance(content, dict):
            continue
        entity_id = content.get("entity_id")
        if not entity_id:
            continue
        exposure_counts[entity_id] = exposure_counts.get(entity_id, 0) + int(
            content.get("impression_count", 1)
        )
        last_seen_at = content.get("last_seen_at")
        if last_seen_at:
            candidate = datetime.fromisoformat(last_seen_at)
            latest_impression_by_entity[entity_id] = max(
                latest_impression_by_entity.get(entity_id, candidate), candidate
            )

    holding_entities = {h.entity_id for h in holdings}
    grace_period = EXPOSURE_FATIGUE_GRACE_PERIOD_DAYS

    fatigued_entities: set[str] = set()
    for entity_id, count in exposure_counts.items():
        if count < EXPOSURE_FATIGUE_THRESHOLD or entity_id in holding_entities:
            continue
        last_engaged_at = latest_engagement_by_entity.get(entity_id)
        last_seen_at = latest_impression_by_entity.get(entity_id)
        if last_engaged_at is None or last_seen_at is None:
            continue
        idle_days = (last_seen_at - last_engaged_at).total_seconds() / 86400.0
        if idle_days >= grace_period:
            fatigued_entities.add(entity_id)

    if not fatigued_entities:
        return established_behaviors, interests

    updated_interests = []
    for interest in interests:
        if interest.source == "inferred" and interest.topic in fatigued_entities:
            dampened = max(interest.weight - EXPOSURE_FATIGUE_PENALTY, 0.0)
            if dampened < DECAY_PRUNE_FLOOR:
                decision_trace.append(
                    DecisionTraceEntry(
                        layer="user_model",
                        rule=f"exposure_fatigue: pruned inferred Interest "
                        f"{interest.topic!r} ({exposure_counts[interest.topic]} "
                        f"impressions, no engagement)",
                        timestamp=now,
                    )
                )
                continue
            decision_trace.append(
                DecisionTraceEntry(
                    layer="user_model",
                    rule=f"exposure_fatigue: dampened inferred Interest "
                    f"{interest.topic!r} to {dampened:.2f} "
                    f"({exposure_counts[interest.topic]} impressions, no engagement)",
                    timestamp=now,
                )
            )
            updated_interests.append(
                interest.model_copy(update={"weight": dampened, "last_updated": now})
            )
        else:
            updated_interests.append(interest)

    remaining_topics = {i.topic for i in updated_interests if i.source == "inferred"}
    updated_behaviors = [
        b
        for b in established_behaviors
        if not (
            b.label.startswith("engaged_with_")
            and b.label[len("engaged_with_") :] in fatigued_entities
            and b.label[len("engaged_with_") :] not in remaining_topics
        )
    ]

    return updated_behaviors, updated_interests
