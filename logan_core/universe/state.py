"""Universe Manager V1a Block 1 -- makes the four-state taxonomy a real,
testable classification rather than only documentation. Two of the four
states are new Universe Manager concepts (UNIVERSE_ELIGIBLE, MONITORED);
the other two already exist elsewhere in this codebase under different
names (OBJECTIVELY_QUALIFIED == AttentionRecommendation.recommend,
PERSONALLY_SURFACED == PrioritizedItem.visibility in ("primary", "feed"))
-- this module does not re-implement those, it only names them
consistently so the distinction stays explicit and auditable wherever a
caller needs to answer "which of the four states is this entity in, for
this user, right now."
"""

from typing import Optional

from logan_core.contracts import UniverseLifecycleState


def classify_universe_lifecycle_state(
    *,
    is_universe_eligible: bool,
    is_monitored: bool,
    is_objectively_qualified: bool,
    is_personally_surfaced: bool,
) -> Optional[UniverseLifecycleState]:
    """Returns the single furthest state reached, or None if not even
    UNIVERSE_ELIGIBLE (i.e. this security isn't part of STRATUS's world at
    all). Each later state implies every earlier one in a well-formed
    system (a personally-surfaced item is always also monitored and
    eligible) -- callers with genuinely inconsistent inputs (a bug
    elsewhere) get the furthest state they claimed, never a raised
    exception, so this stays a pure classifier, not a validator.
    """
    if is_personally_surfaced:
        return "PERSONALLY_SURFACED"
    if is_objectively_qualified:
        return "OBJECTIVELY_QUALIFIED"
    if is_monitored:
        return "MONITORED"
    if is_universe_eligible:
        return "UNIVERSE_ELIGIBLE"
    return None
