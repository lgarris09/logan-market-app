"""Universe Manager V1a Block 12 -- binary Exploration Eligibility. A
policy result, not another ranking score: `is_exploration_eligible()`
returns a plain bool, derived entirely from objective, already-computed
STRATUS state -- never a new score invented to satisfy this rule.

Critically, this never requires the already-personalized attention
judgment to be "High attention" -- that would be circular, since
exploration specifically concerns items with LOW or UNKNOWN personal
relevance. Every criterion here is either world/evidence-objective, or
(for personal_relevance_state) checked only to confirm it's genuinely low/
unknown, never the reverse.
"""

from typing import Literal

EXPLORATION_ELIGIBILITY_POLICY_VERSION_V1 = "exploration-eligibility-v1"

# Reuses the exact same objective bars logan_core/exploration/engine.py's
# strong_world_signal reason already established last session -- Block 12
# is a refinement/unification of that existing objective-strength bar, not
# a new, independently-tuned threshold.
MATERIALITY_FLOOR = 0.7
EVIDENCE_QUALITY_FLOOR = 0.7
MAX_RISK = 0.5

PersonalRelevanceState = Literal["high", "moderate", "low", "unknown"]
_LOW_OR_UNKNOWN: frozenset[str] = frozenset({"low", "unknown"})


def is_exploration_eligible(
    *,
    recommend: bool,
    global_importance: float,
    confidence: float,
    risk: float,
    freshness_state: str,
    is_new_for_user: bool,
    is_materially_revised: bool,
    personal_relevance_state: PersonalRelevanceState,
    has_active_suppression: bool,
) -> bool:
    """All eight conceptual requirements from Block 12, in the order
    they're checked:
      1. objectively qualified opportunity exists       -> `recommend`
      2. objective materiality tier is high              -> `global_importance`
      3. evidence quality meets a strong threshold        -> `confidence`
      4. (risk bar, same as strong_world_signal's own)    -> `risk`
      5. freshness is FRESH                               -> `freshness_state`
      6. opportunity is new or materially revised         -> `is_new_for_user`/
                                                              `is_materially_revised`
      7. Personal Relevance is LOW or UNKNOWN              -> `personal_relevance_state`
      8. no applicable correction/suppression             -> `has_active_suppression`

    Requirement 8 in Block 12's own list ("thesis diversity rules pass") is
    deliberately NOT checked here -- diversity is a batch-level property
    (whether this candidate is distinct from others already selected),
    unknowable from a single candidate in isolation. It's enforced by
    `apply_exploration_placement()` instead (Block 13), which only ever
    considers a candidate this function has already marked eligible.
    """
    if not recommend:
        return False
    if has_active_suppression:
        return False
    if personal_relevance_state not in _LOW_OR_UNKNOWN:
        return False
    if global_importance < MATERIALITY_FLOOR:
        return False
    if confidence < EVIDENCE_QUALITY_FLOOR:
        return False
    if risk >= MAX_RISK:
        return False
    if freshness_state != "FRESH":
        return False
    if not (is_new_for_user or is_materially_revised):
        return False
    return True
