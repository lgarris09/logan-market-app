"""Universe Manager V1a Block 5/6 -- the pure decision logic behind the
Universe Membership Ledger: given the currently-open membership records and
a freshly (re)selected cohort, computes exactly what changed and why,
bounded by a churn policy so membership stays relatively stable rather than
churning continuously (Block 6). Durable persistence of the resulting
MembershipRecord history lives in backend/app (mirrors this codebase's
existing split -- watch_store.py, notification_store.py, etc. -- of "pure
decision logic in logan_core, durable storage in backend/app").

Every record this produces is immutable once closed: a removal never edits
history, it appends a new, closed MembershipRecord (removed_at/
removal_reason/effective_until set) alongside the open one it succeeds --
callers persist both, never overwrite.
"""

from datetime import datetime
from typing import Optional

from logan_core.contracts import (
    CandidateSecurity,
    CohortRebalanceResult,
    MembershipRecord,
)

MEMBERSHIP_POLICY_VERSION_V1 = "universe-membership-v1"

# Bounded churn control (Block 6): a scheduled rebalance may not change more
# than this many memberships in one pass -- deliberately small relative to
# the 25-35 cohort size (well under 20%) so a single rebalance cycle can
# never look like a near-total universe replacement. Any churn beyond this
# budget is deferred, not lost -- it simply reappears as the same diff the
# next time rebalance_membership() runs against still-current inputs.
DEFAULT_MAX_CHURN_PER_REBALANCE = 5

REMOVAL_REASON_SCHEDULED_REBALANCE = "SCHEDULED_COHORT_REBALANCE"
REMOVAL_REASON_ELIGIBILITY_LOST = "ELIGIBILITY_LOST"


def rebalance_membership(
    current_members: list[MembershipRecord],
    newly_selected: list[CandidateSecurity],
    *,
    source_version: str,
    now: datetime,
    admission_reason_codes_by_id: Optional[dict[str, list[str]]] = None,
    removal_reason: str = REMOVAL_REASON_SCHEDULED_REBALANCE,
    provider_health_snapshot: Optional[dict] = None,
    policy_version: str = MEMBERSHIP_POLICY_VERSION_V1,
    max_churn: int = DEFAULT_MAX_CHURN_PER_REBALANCE,
) -> CohortRebalanceResult:
    """`current_members` should be only the currently-open records
    (`effective_until is None`) -- a caller loading from the durable store
    filters to open rows before calling this (the store itself, not this
    pure function, owns "what does 'currently open' mean against real
    wall-clock data"). Removals are prioritized over new admissions when
    both compete for a limited churn budget (losing eligibility matters
    more than optimizing composition) -- both sorted by canonical_id for a
    fully deterministic, reproducible tie-break.
    """
    admission_reason_codes_by_id = admission_reason_codes_by_id or {}
    provider_health_snapshot = provider_health_snapshot or {}

    current_by_id = {m.canonical_id: m for m in current_members}
    current_ids = set(current_by_id.keys())
    selected_by_id = {c.canonical_id: c for c in newly_selected}
    selected_ids = set(selected_by_id.keys())

    to_admit_ids = sorted(selected_ids - current_ids)
    to_remove_ids = sorted(current_ids - selected_ids)
    unchanged_count = len(current_ids & selected_ids)

    if not current_members:
        # Bootstrap, not churn: populating a universe that doesn't exist
        # yet is a one-time cold start, not the "continuous reshuffling of
        # an existing cohort" the churn cap exists to bound (Block 6). A
        # brand-new deployment's very first reevaluation must be able to
        # admit its whole initial cohort in one pass.
        applied_removal_ids: list[str] = []
        applied_admit_ids = to_admit_ids
    else:
        remaining_budget = max_churn
        applied_removal_ids = to_remove_ids[:remaining_budget]
        remaining_budget -= len(applied_removal_ids)
        applied_admit_ids = to_admit_ids[: max(0, remaining_budget)]

    admitted: list[MembershipRecord] = []
    for canonical_id in applied_admit_ids:
        candidate = selected_by_id[canonical_id]
        admitted.append(
            MembershipRecord(
                canonical_id=candidate.canonical_id,
                symbol=candidate.symbol,
                source_version=source_version,
                policy_version=policy_version,
                admission_reason_codes=admission_reason_codes_by_id.get(
                    canonical_id, []
                ),
                admitted_at=now,
                effective_from=now,
                effective_until=None,
                provider_health_snapshot=provider_health_snapshot,
            )
        )

    removed: list[MembershipRecord] = []
    for canonical_id in applied_removal_ids:
        existing = current_by_id[canonical_id]
        removed.append(
            existing.model_copy(
                update={
                    "effective_until": now,
                    "removed_at": now,
                    "removal_reason": removal_reason,
                }
            )
        )

    return CohortRebalanceResult(
        policy_version=policy_version,
        rebalanced_at=now,
        admitted=admitted,
        removed=removed,
        unchanged_count=unchanged_count,
    )
