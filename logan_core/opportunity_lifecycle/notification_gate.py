"""Stock Opportunity Logic V2.4A -- Notification Hygiene & Repeat-Alert
Suppression.

Locks in the core invariant this block exists to establish: *re-showing is
okay, re-alerting requires a meaningful new reason.* A user seeing an
opportunity again in the Attention Field is never, by itself, sufficient
reason for another push -- a push requires a genuinely new
notification-worthy delta since the last one this user was actually sent
for this opportunity.

This module owns the DECISION ("should this user be notified about this
entity right now, and why/why not") -- it never sends anything, never
persists anything, and never re-derives whether a change is
notification-worthy in the first place (that stays
opportunity_lifecycle/tracker.py's own LifecycleDelta.is_notification_worthy,
computed once, used everywhere). `decide_notification()` is a pure function,
mirroring compute_user_sync_delta/compute_since_last_looked's own
discipline: all state it needs (the current delta's own verdict, this
user's durable knowledge, and whether *this specific entity's* provider
fetch degraded this poll) is handed in by the caller
(backend/app/logan_feed.py), which owns reading it from durable storage.

Two independent suppression layers, both grounded in the existing
`UserOpportunityKnowledge.last_notified_revision`/`last_notified_at`/
`last_notified_change_type` pointers -- no parallel "notification version"
of opportunity truth:

1. Revision dedup (hard rule): a revision already notified (or an older
   one) never notifies again, regardless of how the eligibility check was
   reached. This is what makes "same revision cannot alert twice" true even
   across a backend restart (these pointers are durable) or a change to how
   event_id dedup happens to behave.
2. Cooldown (soft rule): a *new*, genuinely notification-worthy revision is
   still suppressed if it is the exact same kind of change
   (MeaningfulChangeType) as the last one this user was actually notified
   about, within a short deterministic window -- this is what prevents a
   burst of several rapid, low-value "still strengthening" pings. A
   *different* change_type (a reversal following a strengthening, a
   strengthening following a reactivation, etc.) is, by definition, a
   materially distinct kind of news and always bypasses the cooldown --
   this suppression can never hide a genuine reversal.

Provider-degraded polls are handled by construction, not by a special case
in most situations: a ticker whose live fetch failed this poll either
disappears from consideration entirely (live-data-only/beta mode) or
observes unchanged simulated fallback data (demo mode) -- either way,
`is_notification_worthy` for that poll is naturally false. `provider_degraded`
is still accepted here as an explicit, auditable belt-and-suspenders guard
(not inferred from silence) so a future change to that fallback behavior can
never accidentally turn a data outage into a false "material" alert.
"""

from datetime import datetime, timedelta
from typing import Literal, Optional

from pydantic import BaseModel

from logan_core.contracts import MeaningfulChangeType

from .sync import UserOpportunityKnowledge

# A small, deterministic starting value -- not learned, not configurable per
# user (that belongs to a later Personal Learning / interruption-budget
# block). 30 minutes is long enough to absorb a burst of same-kind rapid
# revisions (e.g. a few "still strengthening" ticks minutes apart on a
# volatile poll) without meaningfully delaying a real, distinct follow-up.
NOTIFICATION_COOLDOWN = timedelta(minutes=30)

NotificationDecisionReason = Literal[
    "new_material_revision",
    "same_revision_suppressed",
    "cooldown_suppressed",
    "provider_degraded_suppressed",
    "no_material_delta",
]


class NotificationDecision(BaseModel):
    """The deterministic, auditable answer to "why did/didn't STRATUS send
    this notification" -- computed fresh on every eligibility check, never
    itself persisted (the durable state is UserOpportunityKnowledge; this
    is a derived read, exactly like UserSyncDelta/SinceLastLookedSummary).
    """

    schema_version: str = "1.0"
    entity_id: str
    user_id: str
    should_notify: bool
    reason: NotificationDecisionReason
    evaluated_at: datetime


def decide_notification(
    entity_id: str,
    user_id: str,
    current_revision: Optional[int],
    is_notification_worthy: bool,
    change_type: Optional[MeaningfulChangeType],
    knowledge: Optional[UserOpportunityKnowledge],
    provider_degraded: bool,
    now: datetime,
) -> NotificationDecision:
    """`current_revision`/`is_notification_worthy`/`change_type` are this
    poll's own already-computed LifecycleDelta verdict -- never
    re-evaluated here. `knowledge=None` means this user has no durable
    record for this entity at all (never notified) -- the same as every
    pointer being None.
    """

    def _decision(
        should_notify: bool, reason: NotificationDecisionReason
    ) -> NotificationDecision:
        return NotificationDecision(
            entity_id=entity_id,
            user_id=user_id,
            should_notify=should_notify,
            reason=reason,
            evaluated_at=now,
        )

    if provider_degraded:
        return _decision(False, "provider_degraded_suppressed")

    if current_revision is None or not is_notification_worthy:
        return _decision(False, "no_material_delta")

    last_notified_revision = knowledge.last_notified_revision if knowledge else None
    if (
        last_notified_revision is not None
        and current_revision <= last_notified_revision
    ):
        return _decision(False, "same_revision_suppressed")

    last_notified_at = knowledge.last_notified_at if knowledge else None
    last_notified_change_type = (
        knowledge.last_notified_change_type if knowledge else None
    )
    if (
        last_notified_at is not None
        and change_type == last_notified_change_type
        and (now - last_notified_at) < NOTIFICATION_COOLDOWN
    ):
        return _decision(False, "cooldown_suppressed")

    return _decision(True, "new_material_revision")
