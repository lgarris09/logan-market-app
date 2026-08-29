"""Stock Opportunity Logic V2.1 -- User Sync Gap.

V2 (see docs/DECISIONS.md's Sprint 3.6.9 ADR) answered "has the opportunity
meaningfully changed since STRATUS last evaluated it?" -- an objective,
entity-keyed question, identical for every user. This module answers the
next, genuinely different question: "has the opportunity meaningfully
changed since *this specific user* last knew about it?"

Deliberately kept separate from `tracker.py`'s objective lifecycle logic --
`UserOpportunityKnowledge` is per-`(user_id, entity_id)` state (what this
user has seen/been notified about/opened), never mixed into the shared,
entity-keyed `LifecycleSnapshot`/`revision` counter. `compute_user_sync_delta`
is a pure function, not a class with its own state: all the state it needs
(the current global revision, and this user's own knowledge pointers) is
handed in by the caller (backend/app/logan_feed.py), which owns reading it
from durable storage. This mirrors `OpportunityLifecycleTracker.observe()`'s
own determinism discipline -- same inputs always produce the same answer,
never learned, never LLM-influenced.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from logan_core.contracts import MeaningfulChangeType, OpportunityRevision

# UP_TO_DATE: the user has seen the current global revision already --
#   nothing to surface as "updated."
# NEW_TO_USER: this user has never seen this opportunity at any revision,
#   and was never notified about it either -- their first exposure.
# UPDATED_SINCE_SEEN: the user has seen some earlier revision, a newer one
#   now exists, and there is no unseen notification pointing at it (either
#   never notified, or already notified-and-seen for an earlier revision) --
#   e.g. a meaningful change occurred that didn't clear the alert bar.
# NOTIFIED_BUT_UNSEEN: STRATUS notified this user about a revision they have
#   still not seen (seen_revision is None, or behind the notified revision)
#   -- takes priority over the other three: "you have an unopened
#   notification" is the most actionable state to surface, whether or not
#   this is also this user's first-ever exposure to the opportunity.
SyncStatus = Literal[
    "UP_TO_DATE",
    "NEW_TO_USER",
    "UPDATED_SINCE_SEEN",
    "NOTIFIED_BUT_UNSEEN",
]


class UserOpportunityKnowledge(BaseModel):
    """Compact, durable, per-`(user_id, entity_id)` high-water marks --
    updated in place (an UPSERT), never one row per interaction. Pointers
    only ever move forward (see backend/app/logan_feed.py's
    `_advance_user_knowledge`) -- a later interaction can raise a pointer,
    never lower it.

    `last_seen_revision`: the highest global revision for which STRATUS has
    defensible evidence this user actually encountered the opportunity in
    the app (an "impression" -- the card became focused/visible -- or
    anything stronger). Never advanced merely because `/v1/opportunities`
    returned the item in a response.

    `last_notified_revision`: the highest global revision for which a real
    push notification was actually dispatched to this user. Advanced only by
    a successful Expo dispatch (backend/app/notifications.py), never by
    "this item was alert-eligible" alone.

    `last_opened_revision`: the highest global revision for which the user
    actually opened the card (a real disclosure, matching the existing "view"
    interaction/dwell-tracking semantics) -- a strictly stronger signal than
    `last_seen_revision`, tracked separately per the product requirement to
    distinguish "surfaced" from "opened" wherever the app can honestly tell
    the difference.
    """

    schema_version: str = "1.0"
    user_id: str
    entity_id: str
    last_seen_revision: Optional[int] = Field(default=None, ge=1)
    last_notified_revision: Optional[int] = Field(default=None, ge=1)
    last_opened_revision: Optional[int] = Field(default=None, ge=1)
    updated_at: datetime


class UserSyncDelta(BaseModel):
    """The deterministic answer to "what does this user know, relative to
    the current global revision, and what should STRATUS do about it" --
    computed fresh on every call, never itself persisted (the durable state
    is `UserOpportunityKnowledge`; this is a derived read). Never alters
    objective lifecycle, confidence, or market truth -- purely a comparison
    of two already-durable pointers.
    """

    schema_version: str = "1.0"
    entity_id: str
    user_id: str
    current_revision: int = Field(ge=1)
    last_seen_revision: Optional[int] = Field(default=None, ge=1)
    last_notified_revision: Optional[int] = Field(default=None, ge=1)
    last_opened_revision: Optional[int] = Field(default=None, ge=1)
    status: SyncStatus
    # Convenience for callers that just want a boolean ("should this render
    # as updated for this user") without switching on `status` themselves --
    # true for every status except UP_TO_DATE.
    is_new_or_updated_for_user: bool
    evaluated_at: datetime


def compute_user_sync_delta(
    entity_id: str,
    user_id: str,
    current_revision: int,
    knowledge: Optional[UserOpportunityKnowledge],
    now: datetime,
) -> UserSyncDelta:
    """Pure, deterministic comparison of the current global revision against
    one user's own knowledge pointers. `knowledge=None` means this user has
    no durable record for this entity at all (never seen, never notified) --
    the same as every pointer being None.
    """
    seen = knowledge.last_seen_revision if knowledge else None
    notified = knowledge.last_notified_revision if knowledge else None
    opened = knowledge.last_opened_revision if knowledge else None

    has_unseen_notification = notified is not None and (seen is None or seen < notified)

    status: SyncStatus
    if has_unseen_notification:
        status = "NOTIFIED_BUT_UNSEEN"
    elif seen is None:
        status = "NEW_TO_USER"
    elif seen < current_revision:
        status = "UPDATED_SINCE_SEEN"
    else:
        status = "UP_TO_DATE"

    return UserSyncDelta(
        entity_id=entity_id,
        user_id=user_id,
        current_revision=current_revision,
        last_seen_revision=seen,
        last_notified_revision=notified,
        last_opened_revision=opened,
        status=status,
        is_new_or_updated_for_user=status != "UP_TO_DATE",
        evaluated_at=now,
    )


# --- "Since You Last Looked" (V2.3D) -----------------------------------------
#
# A deliberately stricter, narrower question than compute_user_sync_delta
# above: not "has this user seen the current revision" (last_seen_revision,
# which advances on a mere impression -- see UserOpportunityKnowledge's own
# docstring), but "what materially changed since this user last *opened* this
# opportunity" (last_opened_revision, which only advances on a real card
# disclosure -- see backend/app/logan_feed.py's record_interaction). The
# product requirement this exists for is explicit that fetching a feed,
# briefly appearing off-screen, or the app merely launching must never be
# mistaken for "the user looked at this" -- last_opened_revision is the one
# existing pointer in this codebase already held to that exact bar, so this
# reuses it rather than inventing a second, parallel "has looked" concept.

SinceLastLookedStatus = Literal[
    "first_view",
    "material_change",
    "no_material_change",
    "degraded",
]


class SinceLastLookedSummary(BaseModel):
    """The deterministic answer to "what should STRATUS tell this user
    changed since they last deliberately opened this opportunity" --
    computed fresh on every feed request, never itself persisted (mirrors
    UserSyncDelta's own "derived read over durable pointers" discipline).

    `status`:
    - "first_view": this user has never opened this opportunity before
      (last_opened_revision is None). The caller must present the briefing
      normally, with no "Since You Last Looked" language at all -- there is
      nothing to compare against.
    - "no_material_change": the user has opened this opportunity at or after
      its current revision -- nothing has changed since their last look.
    - "material_change": the user's last opened revision is behind the
      current revision, and at least one durable, objective (global,
      not personal-relevance-only -- see OpportunityRevisionStore's own
      "is_global_meaningful" gating) revision exists in between.
    - "degraded": would otherwise be "no_material_change", but this poll's
      live data was genuinely unreachable (provider_degraded) -- STRATUS
      cannot honestly vouch for "nothing changed" when it couldn't check.
      Deliberately does NOT override "material_change": a durable revision
      already on record is a historical fact unaffected by whether *this*
      poll's own live fetch succeeded.

    `change_type`/`detail` are only ever populated for "material_change" --
    `change_type` is the MeaningfulChangeType of the most recent qualifying
    revision since the user's last open (the freshest fact, not a full
    activity log), and `detail` is that same revision's own already-authored
    natural-language `reason` (see OpportunityRevision.reason) -- reused
    verbatim, never re-derived or re-worded here, so there is exactly one
    place in this codebase that authors this sentence.
    """

    schema_version: str = "1.0"
    entity_id: str
    user_id: str
    status: SinceLastLookedStatus
    change_type: Optional[MeaningfulChangeType] = None
    detail: Optional[str] = None
    evaluated_at: datetime


_NO_MATERIAL_CHANGE_DETAIL = (
    "No major change since your last look. STRATUS is still monitoring."
)
_DEGRADED_DETAIL = (
    "Live data was temporarily unavailable this check -- STRATUS can't confirm "
    "whether anything changed since your last look."
)
_MATERIAL_CHANGE_FALLBACK_DETAIL = (
    "STRATUS detected a meaningful change since your last look, but the "
    "specific details from that revision aren't available."
)


def compute_since_last_looked(
    entity_id: str,
    user_id: str,
    current_revision: Optional[int],
    knowledge: Optional[UserOpportunityKnowledge],
    revisions_since_last_open: list[OpportunityRevision],
    provider_degraded: bool,
    now: datetime,
) -> Optional[SinceLastLookedSummary]:
    """Pure, deterministic comparison -- no I/O, no storage access. The
    caller (backend/app/logan_feed.py) owns fetching `knowledge` and
    filtering `revisions_since_last_open` to entries with
    `revision > knowledge.last_opened_revision` from the durable
    OpportunityRevisionStore; this function only ever reasons about what
    it's handed.

    Returns None when lifecycle/revision tracking isn't active for this
    entity at all (current_revision is None) -- there is nothing to compare,
    the same "additive, absent means not available" discipline every other
    lifecycle-adjacent FeedItem field already follows.
    """
    if current_revision is None:
        return None

    opened = knowledge.last_opened_revision if knowledge else None

    if opened is None:
        return SinceLastLookedSummary(
            entity_id=entity_id,
            user_id=user_id,
            status="first_view",
            evaluated_at=now,
        )

    if opened >= current_revision:
        if provider_degraded:
            return SinceLastLookedSummary(
                entity_id=entity_id,
                user_id=user_id,
                status="degraded",
                detail=_DEGRADED_DETAIL,
                evaluated_at=now,
            )
        return SinceLastLookedSummary(
            entity_id=entity_id,
            user_id=user_id,
            status="no_material_change",
            detail=_NO_MATERIAL_CHANGE_DETAIL,
            evaluated_at=now,
        )

    if revisions_since_last_open:
        latest = max(revisions_since_last_open, key=lambda r: r.revision)
        return SinceLastLookedSummary(
            entity_id=entity_id,
            user_id=user_id,
            status="material_change",
            change_type=latest.change_type,
            detail=latest.reason,
            evaluated_at=now,
        )

    # The revision counter advanced, but no matching durable history row
    # exists (e.g. persistence was toggled off across the gap) -- an honest
    # generic signal, never a fabricated specific reason.
    return SinceLastLookedSummary(
        entity_id=entity_id,
        user_id=user_id,
        status="material_change",
        detail=_MATERIAL_CHANGE_FALLBACK_DETAIL,
        evaluated_at=now,
    )
