"""V2.3A -- Identity & Account Foundation: the central account-deletion
primitive.

`purge_user_data(stratus_user_id)` is the one function every user-scoped
store in this backend plugs into -- built now, per the owner's explicit
instruction, rather than retrofitted once more stores exist. A future V2.3B
store (learning state, watchlists, notification preferences) adds one more
call here, not a new deletion mechanism.

Deliberately narrow in scope, matching this codebase's own "objective vs.
personal" boundary (see docs/DECISIONS.md's ADR-069 privacy section):
purges only user-owned state. Global/shared opportunity intelligence
(LifecycleStore, RevisionStore, World Model) is never touched here -- an
account's deletion must never alter what any other user sees for the same
real-world opportunity.
"""

from . import logan_feed, notifications, user_context, watch


def purge_user_data(stratus_user_id: str) -> None:
    """Removes every piece of `stratus_user_id`'s user-owned state across
    this backend's current persistence model:

    - Memory records (behavioral evidence, feedback, exposure records).
    - Prioritization's in-memory AttentionState (fatigue/cooldown/surfaced).
    - Per-user UserModel, OpportunityContext cache, Ask STRATUS sessions.
    - Per-(user, entity) opportunity-knowledge pointers (V2.1 seen/notified/
      opened revision state).
    - Registered push tokens and notification dispatch/review history.
    - Minimal STRATUS Watch state (V2.3E) -- every entity this user asked
      STRATUS to keep watching.
    - The account row and every external-identity mapping pointing at it.

    Idempotent -- calling this for a `stratus_user_id` with no data at all
    (or calling it twice) is always safe and a no-op past the first real
    deletion.
    """
    logan_feed.purge_user(stratus_user_id)
    notifications.purge_user(stratus_user_id)
    watch.purge_user(stratus_user_id)
    user_context.purge_account_identity(stratus_user_id)
