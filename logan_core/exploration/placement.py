"""Universe Manager V1a Blocks 13/14 -- batch-level exploration placement.
Reconciled sibling to engine.py's per-item promotion (see that module's
own 2026-08-30 reconciliation note): where engine.py decides "should this
one background item ever be considered outside a user's usual profile,"
this module decides "does the field's top five actually contain at most
one such item, and which one if so" -- a single decision per feed
computation, never a per-item independent quota.

Final V1a exploration semantics (Block 11's own summary): zero or one
conditional unfamiliar placement in the top five. Not a reserved slot
(only fills when something genuinely earns it). Not random (deterministic:
highest objective_strength among eligible, distinct-entity candidates).
Does not exist on every refresh (most refreshes place zero). Uses no
separate opaque score (`objective_strength` is the same
global_importance/confidence-derived proxy already used for feed ranking,
never a new model).
"""

from datetime import datetime, timezone
from typing import Optional

from logan_core.contracts import (
    ExplorationOpportunityCostTrace,
    ExplorationPlacementResult,
)
from logan_core.thesis.diversity import ThesisCandidate

EXPLORATION_PLACEMENT_POLICY_VERSION_V1 = "exploration-placement-v1"
EXPLORATION_OBJECTIVE_STRENGTH = "EXPLORATION_OBJECTIVE_STRENGTH"


def apply_exploration_placement(
    top_candidates: list[ThesisCandidate],
    eligible_pool: list[ThesisCandidate],
    *,
    policy_version: str = EXPLORATION_PLACEMENT_POLICY_VERSION_V1,
    now: Optional[datetime] = None,
) -> ExplorationPlacementResult:
    """`top_candidates` is the already-diversified top band (the `selected`
    list from thesis/diversity.py's `apply_diversity_caps()`, Block 10).
    `eligible_pool` is every candidate this refresh that
    `exploration/eligibility.py`'s `is_exploration_eligible()` already
    marked eligible (computed by the caller per-candidate, before this
    batch step) -- this function never computes eligibility itself, it
    only decides placement among already-eligible candidates.

    A placement happens only when all of these hold:
      - at least one eligible candidate has an entity not already present
        in `top_candidates` (Block 13: "distinct from already selected
        theses");
      - `top_candidates` contains at least one non-Watch item (a Watch
        item may never be displaced -- Block 13's own explicit rule, and
        Block 15's Watch-affects-only-personal-relevance boundary is
        upheld by never touching provider/monitoring state here);
      - the strongest such eligible candidate's `objective_strength` is not
        lower than the weakest non-Watch candidate currently in
        `top_candidates` (Block 13: "not materially weaker on objective
        grounds").
    Otherwise, zero exploration placements this refresh -- the honest,
    common case, never forced.
    """
    now = now or datetime.now(timezone.utc)
    if not eligible_pool:
        return ExplorationPlacementResult(policy_version=policy_version)

    already_present_entities = {c.metadata.primary_entity_id for c in top_candidates}
    distinct_eligible = [
        c
        for c in eligible_pool
        if c.metadata.primary_entity_id not in already_present_entities
    ]
    if not distinct_eligible:
        return ExplorationPlacementResult(policy_version=policy_version)

    non_watch_candidates = [c for c in top_candidates if not c.is_watched]
    if not non_watch_candidates:
        # Every current top-band item is a Watch item -- there is nothing
        # exploration is ever allowed to displace.
        return ExplorationPlacementResult(policy_version=policy_version)

    # Deterministic pick: highest objective_strength, tie-broken by
    # event_id (a stable, arbitrary-but-reproducible order) -- never random.
    best = max(distinct_eligible, key=lambda c: (c.objective_strength, str(c.event_id)))
    weakest = min(
        non_watch_candidates, key=lambda c: (c.objective_strength, str(c.event_id))
    )

    if best.objective_strength < weakest.objective_strength:
        return ExplorationPlacementResult(policy_version=policy_version)

    trace = ExplorationOpportunityCostTrace(
        exploration_thesis_id=best.event_id,
        displaced_thesis_id=weakest.event_id,
        objective_comparison=(
            f"exploration_strength={best.objective_strength:.2f} vs "
            f"displaced_strength={weakest.objective_strength:.2f}"
        ),
        diversity_requirement_satisfied=True,
        newness_requirement_satisfied=True,
        exploration_policy_version=policy_version,
        recorded_at=now,
    )
    return ExplorationPlacementResult(
        policy_version=policy_version,
        placed_event_id=best.event_id,
        reason=EXPLORATION_OBJECTIVE_STRENGTH,
        opportunity_cost=trace,
    )
