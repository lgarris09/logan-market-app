"""Operational Beta Hardening Block 2 -- Controlled Exploration.

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
up to "feed" visibility -- and only when one of three specific,
deterministic, explainable reasons applies. It never touches "hidden"
(Policy-suppressed) or fatigued/cooldown-suppressed items, never promotes
to "primary" (bounded, non-dominant -- exploration surfaces something,
it does not force it to the top), and never invents evidence: every
promotion reason is derived from `Dimensions` fields Opportunity Engine
already computed.

Three deterministic promotion reasons:
  strong_world_signal     -- objectively significant regardless of personal
                              fit (global_importance high, risk low, not
                              speculation-adjacent) -- the wider world's own
                              signal, not this user's profile.
  unseen_material_change  -- a genuinely new development (novelty at the
                              "new" stance ceiling) this specific user has
                              never been shown before (is_new_for_user).
  discovery_allowance     -- a small, bounded, rolling-24h-window-limited
                              slot (EXPLORATION_DAILY_LIMIT) for something
                              outside the user's usual profile that still
                              cleared Opportunity's own recommend threshold
                              and Prioritization's risk bar -- chosen
                              deterministically (whichever eligible
                              background item this call is given; callers
                              iterate items in a stable, already-existing
                              order, never a random draw), not randomly.

`personal_relevance` is the fourth, ordinary-path label -- applied only
when this module concludes no exploration promotion was warranted (the
item is already visible, or didn't qualify) and personal_relevance was
genuinely the single dominant scored dimension. Left unset (None) whenever
the true driver is genuinely blended/ambiguous -- this module never
fabricates a single reason it can't actually support.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from logan_core.contracts import (
    AttentionRecommendation,
    AttentionState,
    ExplorationGrantRecord,
    PrioritizedItem,
)

# Rolling window, not a calendar day -- consistent with FatigueRecord's own
# windowing style elsewhere in Prioritization, and avoids a UTC-midnight
# edge case a real calendar-day boundary would introduce.
EXPLORATION_WINDOW = timedelta(hours=24)
EXPLORATION_DAILY_LIMIT = 2

# strong_world_signal / discovery_allowance both require the item's own
# risk dimension to be low -- exploration must never be the reason a
# risky or speculative item reaches a user who wouldn't otherwise see it.
_MAX_RISK_FOR_PROMOTION = 0.5
STRONG_WORLD_SIGNAL_IMPORTANCE = 0.7
UNSEEN_MATERIAL_CHANGE_NOVELTY = 0.8
PERSONAL_RELEVANCE_DOMINANT_FLOOR = 0.5


def _active_grant_count(state: AttentionState, now: datetime) -> int:
    return sum(
        1
        for g in state.exploration_grants
        if (now - g.granted_at) <= EXPLORATION_WINDOW
    )


def apply_controlled_exploration(
    item: PrioritizedItem,
    recommendation: AttentionRecommendation,
    state: AttentionState,
    now: Optional[datetime] = None,
) -> PrioritizedItem:
    """Returns `item` unchanged, or a copy promoted to visibility="feed"
    with `attention_reason` set. Idempotent per call -- a caller that
    already promoted this exact PrioritizedItem instance and calls again
    with the same `state` will not double-grant (the item's own
    visibility is no longer "background" on the second call).
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

    if _active_grant_count(state, now) < EXPLORATION_DAILY_LIMIT:
        state.exploration_grants.append(
            ExplorationGrantRecord(event_id=item.event_id, granted_at=now)
        )
        return item.model_copy(
            update={"visibility": "feed", "attention_reason": "discovery_allowance"}
        )

    return item
