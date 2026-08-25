"""Stock Opportunity Logic V2 -- Opportunity Lifecycle contracts.

See docs/DECISIONS.md's Sprint 3.6.9 Stock Opportunity Logic V2 ADR for the
full product/architecture reasoning. Summary: every existing layer in this
pipeline (World Model through Presentation) recomputes its output fresh,
statelessly, from the current poll's inputs alone -- nothing anywhere
persists a *prior* snapshot to compare against, which is the root cause of
the "same card looks the same forever" product problem this contract exists
to fix. `LifecycleSnapshot` is that missing prior-state record;
`LifecycleDelta` is the structured answer to "what changed since the last
meaningful state, and does it matter."

Two deliberately separate scopes, matching how personalization already
works elsewhere in this codebase (UserModel is per-user; World Model's
event identity is shared): `LifecycleSnapshot` tracks *objective* world
facts (confidence, which triggers are active) per `entity_id`, shared
across every user -- two users must see the identical objective lifecycle
state for the same real-world opportunity. Personal-relevance-crossing-
threshold is tracked separately, per `(user_id, entity_id)`, and folded
into the same `LifecycleDelta` as an independent signal -- personalization
affects how much an objectively-unchanged opportunity matters to *this*
user, never the objective facts themselves.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

# NEW: never observed before. DEVELOPING: actively strengthening (a
# meaningful world-fact change happened recently). HIGH_ATTENTION: strong,
# multi-signal-confirmed (crosses the same 0.6 bar PrioritizationEngine
# already uses for visibility="primary", and/or convergence is active) --
# reusing an existing anchor, not inventing a new one. MONITORING: the
# original thesis remains valid, nothing materially changed since the last
# meaningful change, and not old enough to be COOLING yet. COOLING: past
# its signal type's natural monitoring window with no new evidence --
# weakening relevance, not yet stale. STALE: past its signal type's natural
# stale window -- still shown, but clearly marked as old. EXPIRED: past its
# signal type's natural expiration window -- no longer worth showing at
# all.
LifecycleState = Literal[
    "new",
    "developing",
    "high_attention",
    "monitoring",
    "cooling",
    "stale",
    "expired",
]

# What kind of meaningful change this delta represents -- drives both the
# card's presentation copy and the notification-worthiness decision (see
# NOTIFICATION_WORTHY_CHANGE_TYPES in opportunity_lifecycle/tracker.py).
# "none" is a real, expected value -- most polls produce no meaningful
# change at all, and that is the honest, common case this whole feature
# exists to represent correctly rather than papering over.
MeaningfulChangeType = Literal[
    "none",
    "new_opportunity",
    "confidence_increased",
    "confidence_decreased",
    "new_signal_appeared",
    "convergence_formed",
    "aged_to_cooling",
    "aged_to_stale",
    "aged_to_expired",
    "reactivated",
    "personal_relevance_increased",
    "personal_relevance_decreased",
]


class LifecycleSnapshot(BaseModel):
    """The durable, objective, per-`entity_id` (shared across every user)
    prior-state record `OpportunityLifecycleTracker` persists and compares
    each new poll against. Deliberately compact -- confidence_score and the
    active trigger_code set are enough to detect every world-fact meaningful
    change type this contract defines; this does not store raw provider
    payloads or full signal history (see the ADR's explicit "compact
    structured state, not payload history" instruction).
    """

    schema_version: str = "1.0"
    entity_id: str
    lifecycle_state: LifecycleState
    confidence_score: float = Field(ge=0.0, le=1.0)
    trigger_codes: list[str] = Field(default_factory=list)
    first_seen_at: datetime
    last_meaningful_change_at: datetime
    last_notification_worthy_at: Optional[datetime] = None
    last_evaluated_at: datetime
    # Stock Opportunity Logic V2.1 (User Sync Gap) -- a monotonic counter of
    # this entity's *meaningful* revisions (bumped exactly when observe()
    # sets is_meaningful=True; a "none"-change poll never advances it). This
    # is the stable, comparable number the per-user sync layer
    # (opportunity_lifecycle/sync.py) diffs a user's last-known revision
    # against -- entity_id remains the stable opportunity identity across
    # every revision, matching how LifecycleSnapshot itself has always been
    # keyed; revision is a version number on that same identity, not a new
    # identity scheme. Defaults to 1 so any snapshot constructed before this
    # field existed (or restored from a pre-V2.1 persisted row) is treated as
    # "already at its first revision," not zero/unknown.
    revision: int = Field(default=1, ge=1)


class LifecycleDelta(BaseModel):
    """The structured answer `OpportunityLifecycleTracker.observe()` returns
    on every call -- what changed, when, why it matters, and whether it's
    enough to update the card / notify the user. `is_meaningful` gates card
    updates (and feeds PrioritizationEngine's `changed_since_view`, finally
    giving that parameter real data -- see the ADR); `is_notification_worthy`
    is the strictly narrower subset that should ever interrupt the user
    (never equated with "opportunity still exists" -- most notification-
    worthy-eligible polls produce `is_notification_worthy=False`).
    """

    schema_version: str = "1.0"
    entity_id: str
    change_type: MeaningfulChangeType
    is_meaningful: bool
    is_notification_worthy: bool
    previous_state: LifecycleState
    new_state: LifecycleState
    previous_confidence: float = Field(ge=0.0, le=1.0)
    new_confidence: float = Field(ge=0.0, le=1.0)
    new_trigger_codes: list[str] = Field(default_factory=list)
    added_trigger_codes: list[str] = Field(default_factory=list)
    personal_relevance_changed: bool = False
    reason: str
    evaluated_at: datetime
    last_meaningful_change_at: datetime
    # Age of the current thesis, measured from first_seen_at (when STRATUS
    # itself first surfaced this opportunity), not from the underlying
    # signal's own occurred_at (a real-world earnings/grade date, which is
    # frequently already old by the time it's first detected and would
    # therefore misrepresent "how long has this been sitting in the user's
    # Attention Field unchanged" -- see the ADR's explicit reasoning on this
    # exact distinction).
    thesis_age_hours: float = Field(ge=0.0)
    # Stock Opportunity Logic V2.1 (User Sync Gap): the entity's meaningful-
    # revision counter before/after this observe() call. previous_revision
    # == new_revision whenever is_meaningful is False (a "none"-change poll
    # never advances the counter); new_revision == previous_revision + 1
    # whenever is_meaningful is True. This is what lets a per-user pointer
    # (UserOpportunityKnowledge.last_seen_revision) be compared against a
    # single integer rather than re-deriving "has anything meaningful
    # happened since this user last looked" from timestamps.
    previous_revision: int = Field(ge=1)
    new_revision: int = Field(ge=1)


class OpportunityRevision(BaseModel):
    """One durable, append-only row in an entity's meaningful-revision
    history -- written only when `OpportunityLifecycleTracker.observe()`
    produced `is_meaningful=True` (see backend/app/revision_store.py), never
    on every poll. `entity_id` is the stable opportunity identity across
    every revision (unchanged from LifecycleSnapshot/LifecycleDelta's own
    keying); `revision` is this row's position in that entity's history.
    Deliberately typed/queryable core fields, not an opaque JSON blob --
    the same "compact structured state, not payload history" discipline
    LifecycleSnapshot already established, extended to a history log instead
    of a single current-state row.
    """

    schema_version: str = "1.0"
    entity_id: str
    revision: int = Field(ge=1)
    lifecycle_state: LifecycleState
    confidence_score: float = Field(ge=0.0, le=1.0)
    trigger_codes: list[str] = Field(default_factory=list)
    change_type: MeaningfulChangeType
    reason: str
    created_at: datetime
