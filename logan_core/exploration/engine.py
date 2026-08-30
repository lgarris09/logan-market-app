"""Operational Beta Hardening Block 2 -- Controlled Exploration, per-item
promotion stage. Reconciled against Universe Manager V1a Blocks 11-14 (see
logan_core/exploration/eligibility.py and placement.py for the newer,
batch-level "at most one exploration slot among the top five" mechanism
those blocks add on top of this one).

Personal Relevance V2 (opportunity/personal_relevance.py) deliberately
rewards a user's existing declared/inferred interests -- left completely
unchecked, that creates a real risk that STRATUS only ever surfaces more of
what a user already looks at, never anything genuinely outside it, even
when the wider world clearly has something else worth their attention.
This module is the deterministic anti-echo-chamber safeguard for that risk.

Never a second scorer: `apply_controlled_exploration()` never re-ranks or
re-scores anything (Opportunity Engine remains the only scorer -- see this
codebase's layer-ownership rule). It only ever promotes an
already-recommended (`AttentionRecommendation.recommend=True`),
already-policy-permitted item that `PrioritizationEngine.prioritize()`
placed in the "background" visibility tier (buried, effectively unseen)
up to "feed" visibility -- and only when one of two specific,
deterministic, explainable reasons applies. It never touches "hidden"
(Policy-suppressed) or fatigued/cooldown-suppressed items, never promotes
to "primary" (bounded, non-dominant -- exploration surfaces something,
it does not force it to the top), and never invents evidence: every
promotion reason is derived from `Dimensions` fields Opportunity Engine
already computed.

Two deterministic promotion reasons:
  strong_world_signal     -- objectively significant regardless of personal
                              fit (global_importance high, risk low, not
                              speculation-adjacent) -- the wider world's own
                              signal, not this user's profile.
  unseen_material_change  -- a genuinely new development (novelty at the
                              "new" stance ceiling) this specific user has
                              never been shown before (is_new_for_user).

`personal_relevance` is the third, ordinary-path label -- applied only
when this module concludes no exploration promotion was warranted (the
item is already visible, or didn't qualify) and personal_relevance was
genuinely the single dominant scored dimension. Left unset (None) whenever
the true driver is genuinely blended/ambiguous -- this module never
fabricates a single reason it can't actually support.

2026-08-30 Universe Manager V1a reconciliation (Block 11): this file used
to carry a third promotion reason, `discovery_allowance` -- a small,
per-item, rolling-24h-window-limited quota (`EXPLORATION_DAILY_LIMIT`,
`AttentionState.exploration_grants`) applied independently to every
background item a user's feed contained. Removed: Block 13's finalized
exploration-placement policy is "at most one exploration-eligible
opportunity among the top five candidates," a single batch-level decision
(see placement.py), not an independent per-item quota that could promote
several unrelated background items in the same feed. Keeping both would
have been exactly the "second exploration system" the reconciliation
instruction explicitly forbade. `ExplorationGrantRecord`/
`AttentionState.exploration_grants` were removed from
logan_core/contracts/prioritization.py alongside this.
"""

from datetime import datetime, timezone
from typing import Optional

from logan_core.contracts import AttentionRecommendation, PrioritizedItem

# strong_world_signal requires the item's own risk dimension to be low --
# exploration must never be the reason a risky or speculative item reaches
# a user who wouldn't otherwise see it.
_MAX_RISK_FOR_PROMOTION = 0.5
STRONG_WORLD_SIGNAL_IMPORTANCE = 0.7
UNSEEN_MATERIAL_CHANGE_NOVELTY = 0.8
PERSONAL_RELEVANCE_DOMINANT_FLOOR = 0.5


def apply_controlled_exploration(
    item: PrioritizedItem,
    recommendation: AttentionRecommendation,
    now: Optional[datetime] = None,
) -> PrioritizedItem:
    """Returns `item` unchanged, or a copy promoted to visibility="feed"
    with `attention_reason` set. Idempotent -- calling this again on an
    already-promoted item (visibility no longer "background") is a no-op
    past the first check.
    """
    now = now or datetime.now(timezone.utc)
    dims = recommendation.dimensions

    if item.visibility != "background":
        if (
            dims.personal_relevance >= PERSONAL_RELEVANCE_DOMINANT_FLOOR
            and dims.personal_relevance >= dims.global_importance
        ):
            return item.model_copy(update={"attention_reason": "personal_relevance"})
        return item

    if not recommendation.recommend or dims.risk >= _MAX_RISK_FOR_PROMOTION:
        return item

    if dims.global_importance >= STRONG_WORLD_SIGNAL_IMPORTANCE:
        return item.model_copy(
            update={"visibility": "feed", "attention_reason": "strong_world_signal"}
        )

    if dims.novelty >= UNSEEN_MATERIAL_CHANGE_NOVELTY and item.is_new_for_user:
        return item.model_copy(
            update={"visibility": "feed", "attention_reason": "unseen_material_change"}
        )

    return item
