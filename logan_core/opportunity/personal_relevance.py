"""V2.3B Phase 2 (Learning-Driven STRATUS) -- Personal Relevance V2.

The deliberate, explainable replacement for the old inline computation in
OpportunityEngine.evaluate() (moved here verbatim where the numeric ranges
are concerned -- see each constant's own comment for what carries over
unchanged and why). Still the Opportunity Engine's own logic (this module
lives inside logan_core/opportunity/, not a new layer) -- "only the
Opportunity Engine scores/ranks" is unchanged; this is that same engine's
code organized into its own submodule now that there is enough of it to
warrant one.

Audit finding this replaces (2026-08-30, docs/DECISIONS.md): the pre-Phase-2
formula was "too dependent on the maximum confidence of a single matching
interest" -- a lone Interest.weight, with no visibility into *why* (evidence
count, recency, Watch state) or *what didn't* contribute (a suppressed
correction). compute_personal_relevance() below produces the same bounded
numeric contribution existing callers already depend on (deliberately
UNCHANGED for the explicit/inferred/none tiers -- see each branch's own
comment for exactly which pre-existing test assertions this preserves), plus
a new, structured, honest explanation of what actually drove it.

New in Phase 2: Watch. A current, active Watch is checked directly (like
holdings/explicit interests already were) rather than folded through
MemoryStore's MIN_REPEAT_EVIDENCE evidence pool -- a single explicit Watch
action is a standalone, deliberate signal, not one that needs a second
corroborating observation to count. It is deliberately the strongest tier
(above explicit), per the product decision that Watch should become "one of
the strongest user-interest observations" -- bounded well below 1.0 (see
WATCH_RELEVANCE), so it still only ever contributes its fixed 25% weight of
internal_rank_score, never enough alone to force a "High attention" surface
decision (anti-echo-chamber requirement, Personal Learning Phase 2 Block 8).
"""

from typing import Literal

from logan_core.contracts import PersonalRelevanceResult

# Sprint 3.6.7 Block 3 constants, UNCHANGED -- preserves every existing
# explicit/inferred numeric assertion (see logan_core/tests/test_opportunity.py).
INFERRED_RELEVANCE_FLOOR = 0.5
INFERRED_RELEVANCE_CEILING = 0.59
_INFERRED_WEIGHT_FLOOR = 0.75
_INFERRED_WEIGHT_CEILING = 0.90

# Deliberately EQUAL to EXPLICIT_RELEVANCE, not higher (2026-08-30 finding):
# PolicyEngine's ADR-049 "personal, explicit tier" notification-eligibility
# gate (logan_core/policy/engine.py) already keys directly off this same
# personal_relevance value at exactly the 0.6 floor -- a Watch tier strictly
# above 0.6 measurably raises internal_rank_score for any already-explicit
# (e.g. holding-connected) entity purely by being watched, which changes
# notification eligibility. That's explicitly out of scope for this block
# ("do not change notification eligibility... until earned notifications are
# validated") -- test_notification_hygiene.py's
# test_watch_alone_does_not_force_a_notification enforces this directly.
# Watch is still "one of the strongest" signals -- distinguished from plain
# explicit interest in basis/explanation (checked first, different narrative,
# a real product signal for Personal Relevance V2's explainability), just not
# by introducing a new numeric ceiling above what an explicit connection
# could already reach. Deliberately below 1.0 -- personal relevance is only
# ever 25% of internal_rank_score (opportunity/engine.py's own locked weighting,
# untouched by this change), so even a maximal Watch-driven value cannot by
# itself push an opportunity to "High attention" -- objective evidence
# (confidence/urgency/actionability, the other 75%) still has to cooperate.
WATCH_RELEVANCE = 0.6
EXPLICIT_RELEVANCE = 0.6


def _scale_inferred_relevance(inferred_relevance_strength: float) -> float:
    """UNCHANGED from the pre-Phase-2 implementation (moved here verbatim) --
    maps a matched inferred Interest.weight onto the bounded
    [INFERRED_RELEVANCE_FLOOR, INFERRED_RELEVANCE_CEILING] range, linear
    within the realistic weight range, clamped at both ends.
    `inferred_relevance_strength <= _INFERRED_WEIGHT_FLOOR` (including the
    0.0 default every caller that doesn't populate the field supplies)
    returns exactly INFERRED_RELEVANCE_FLOOR.
    """
    if inferred_relevance_strength <= _INFERRED_WEIGHT_FLOOR:
        return INFERRED_RELEVANCE_FLOOR
    span = _INFERRED_WEIGHT_CEILING - _INFERRED_WEIGHT_FLOOR
    fraction = min((inferred_relevance_strength - _INFERRED_WEIGHT_FLOOR) / span, 1.0)
    return INFERRED_RELEVANCE_FLOOR + fraction * (
        INFERRED_RELEVANCE_CEILING - INFERRED_RELEVANCE_FLOOR
    )


def compute_personal_relevance(
    *,
    connected_entities_explicit: list[str],
    connected_entities_inferred: list[str],
    inferred_relevance_strength: float,
    inferred_evidence_count: int,
    is_watched: bool,
    actionability_floor: float,
) -> PersonalRelevanceResult:
    """Priority order -- watch > explicit > inferred > none -- matching the
    product decision that Watch is the strongest tier. A correction/
    suppression never needs special-casing here: `_apply_corrections`
    (user_model/model.py) already removes a suppressed entity from
    `user_model.interests` entirely before ReasoningEngine ever computes
    `connected_entities_inferred`, so a corrected entity simply presents as
    "none" here, honestly, with no contribution and no signal cited for it.

    `actionability_floor` is the pre-Phase-2 `_ACTIONABILITY_SCORE.get(
    reasoning.actionability, 0.2)` value the caller (OpportunityEngine)
    already computes -- passed through unchanged for the "none" tier so a
    signal with no personal connection at all keeps exactly its pre-Phase-2
    numeric contribution (preserves the `==0.2`/`==0.5` assertions in
    test_opportunity.py that depend on actionability alone, not learning).
    """
    basis: Literal["explicit", "watch", "inferred", "none"]
    state: Literal["high", "moderate", "low", "unknown"]
    if is_watched:
        value = WATCH_RELEVANCE
        basis = "watch"
        state = "high"
        strongest_signals = ["You're actively watching this."]
        if connected_entities_explicit:
            strongest_signals.append("This also matches a declared interest.")
        not_contributing: list[str] = []
    elif connected_entities_explicit:
        value = EXPLICIT_RELEVANCE
        basis = "explicit"
        state = "high"
        strongest_signals = ["This matches an interest you've explicitly declared."]
        not_contributing = ["You are not currently watching this."]
    elif connected_entities_inferred:
        value = _scale_inferred_relevance(inferred_relevance_strength)
        basis = "inferred"
        state = "moderate"
        if inferred_evidence_count >= 3:
            strongest_signals = [
                f"You've returned to this {inferred_evidence_count} times recently."
            ]
        elif inferred_evidence_count == 2:
            strongest_signals = ["You've shown early repeated interest in this."]
        else:
            strongest_signals = [
                "This weakly matches a pattern STRATUS has started to notice."
            ]
        not_contributing = ["No explicit declared interest or active Watch."]
    else:
        value = actionability_floor
        basis = "none"
        state = "unknown"
        strongest_signals = []
        not_contributing = [
            "No declared interest, Watch, or repeated engagement with this yet."
        ]

    explanation = (
        strongest_signals[0]
        if strongest_signals
        else "STRATUS has limited evidence that this is personally relevant to you."
    )

    return PersonalRelevanceResult(
        value=value,
        state=state,
        basis=basis,
        is_watched=is_watched,
        evidence_count=inferred_evidence_count if basis == "inferred" else 0,
        explicit=basis in ("explicit", "watch"),
        strongest_signals=strongest_signals,
        not_contributing=not_contributing,
        explanation=explanation,
    )
