"""Universe Manager V1a Blocks 13/14 -- typed results for the batch-level
"at most one exploration placement among the top five" decision
(logan_core/exploration/placement.py). Distinct from the per-item
promotion this codebase already had (exploration/engine.py's
apply_controlled_exploration) -- see that module's own docstring for the
2026-08-30 reconciliation note.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ExplorationOpportunityCostTrace(BaseModel):
    """Block 14 -- factual decision telemetry only, recorded exactly once
    per placement that actually displaced a non-Watch candidate. Never an
    inference about whether the user liked or engaged with the result
    (this codebase's own standing principle: telemetry records what
    happened, Learning decides what it means later -- see V2.3C's own
    event-contract discipline)."""

    schema_version: str = "1.0"
    exploration_thesis_id: UUID
    displaced_thesis_id: UUID
    objective_comparison: str
    diversity_requirement_satisfied: bool
    newness_requirement_satisfied: bool
    exploration_policy_version: str
    recorded_at: datetime


class ExplorationPlacementResult(BaseModel):
    """The outcome of one `apply_exploration_placement()` call --
    `placed_event_id=None` is the honest, common case: zero exploration
    placements this refresh (Block 13: "It does not exist on every
    refresh")."""

    schema_version: str = "1.0"
    policy_version: str
    placed_event_id: Optional[UUID] = None
    reason: Optional[str] = None
    opportunity_cost: Optional[ExplorationOpportunityCostTrace] = None
