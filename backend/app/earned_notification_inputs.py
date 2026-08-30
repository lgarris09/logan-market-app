"""Operational Beta Hardening Block 8 -- prepares (never activates) the
typed inputs a future Full Earned Notifications pass would consume.

`build_earned_notification_inputs()` is a pure, read-only adapter from an
already-computed `PipelineResult` to `EarnedNotificationInputs`
(logan_core/contracts/policy.py) -- mirrors backend/app/ask_context.py's
own established shape and discipline exactly: a typed snapshot of real
pipeline fields, never a second computation of anything.

Not called from any real decision path. Push/alert eligibility today
remains exactly `PrioritizedItem.interruption == "alert"`, decided entirely
by `PolicyEngine.evaluate()`'s existing `_watch_route()` gate (ADR-049) --
this module changes nothing about that. Activating Full Earned
Notifications (wiring these inputs into an actual decision, and whatever
new threshold logic that requires) is a separate, explicit, future change,
not something introduced by this file's mere existence.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from logan_core.contracts import (  # noqa: E402
    EarnedNotificationInputs,
    LifecycleDeltaSummary,
)
from logan_core.orchestrator.pipeline import PipelineResult  # noqa: E402


def build_earned_notification_inputs(
    result: PipelineResult,
) -> EarnedNotificationInputs:
    """Assembles `EarnedNotificationInputs` from `result`'s own
    already-computed fields -- `result.lifecycle_delta` (None when
    lifecycle tracking isn't active for this call, same posture as
    ask_context.py's identical handling), `result.trust.trust_score`,
    `result.recommendation.personal_relevance_result`, and
    `result.recommendation.dimensions.urgency`. Never re-derives or
    re-scores any of these.
    """
    delta = result.lifecycle_delta
    material_delta = (
        LifecycleDeltaSummary(
            change_type=delta.change_type,
            is_meaningful=delta.is_meaningful,
            is_notification_worthy=delta.is_notification_worthy,
        )
        if delta is not None
        else None
    )
    relevance = result.recommendation.personal_relevance_result
    return EarnedNotificationInputs(
        event_id=result.event.event_id,
        material_delta=material_delta,
        evidence_credibility=result.trust.trust_score,
        personal_relevance_result=relevance,
        time_sensitivity=result.recommendation.dimensions.urgency,
        is_watched=relevance.is_watched if relevance is not None else False,
        computed_at=datetime.now(timezone.utc),
    )
