"""Universe Manager V1a Block 4 -- deterministic selection of the bounded
monitored cohort from the eligible universe. Optimizes for representative,
monitorable opportunity supply (sector diversity, provider completeness) --
never investment merit, never any per-user input. No Logan-personal
preference, no user telemetry, no Personal Learning, no CTR/Watch counts,
no "trending" signal reaches this function, by construction: its only
inputs are CandidateSecurity + EligibilityResult, both entirely
user-agnostic and already computed before this function runs.
"""

import math

from logan_core.contracts import CandidateSecurity, EligibilityResult

COHORT_POLICY_VERSION_V1 = "universe-cohort-v1"

# The middle of Universe Manager V1a's own 25-35 target range (product
# spec) -- a specific, deterministic target rather than "as many as fit,"
# so cohort size itself doesn't silently drift with candidate-source size.
DEFAULT_TARGET_COHORT_SIZE = 30
MIN_COHORT_SIZE = 25
MAX_COHORT_SIZE = 35

# No single sector may claim more than this fraction of the cohort --
# concentration cap, not a floor; a sector with zero eligible candidates
# simply contributes zero, never backfilled from elsewhere to "fill its
# share."
DEFAULT_SECTOR_CAP_FRACTION = 0.30


def select_monitored_cohort(
    eligible_candidates: list[tuple[CandidateSecurity, EligibilityResult]],
    *,
    target_size: int = DEFAULT_TARGET_COHORT_SIZE,
    sector_cap_fraction: float = DEFAULT_SECTOR_CAP_FRACTION,
) -> list[CandidateSecurity]:
    """`eligible_candidates` is every (CandidateSecurity, EligibilityResult)
    pair this reevaluation considered, eligible and rejected alike -- this
    function itself filters to `result.eligible` internally, so a caller
    never has to pre-filter (and can't accidentally forget to).

    Deterministic selection: eligible candidates are grouped by sector,
    each sector's queue sorted by (full signal-family coverage first, then
    canonical_id alphabetically) for a byte-identical result given the same
    inputs, then filled round-robin across sectors (in alphabetical sector
    order) up to `target_size`, respecting the sector cap. Never reaches
    outside `eligible_candidates` and never pads short of `target_size` if
    the eligible pool itself is smaller.
    """
    if not (MIN_COHORT_SIZE <= target_size <= MAX_COHORT_SIZE):
        raise ValueError(
            f"target_size must be within [{MIN_COHORT_SIZE}, {MAX_COHORT_SIZE}], "
            f"got {target_size}"
        )

    coverage_by_id = {
        candidate.canonical_id: result for candidate, result in eligible_candidates
    }
    by_sector: dict[str, list[CandidateSecurity]] = {}
    seen_ids: set[str] = set()
    for candidate, result in eligible_candidates:
        if not result.eligible or candidate.canonical_id in seen_ids:
            continue
        seen_ids.add(candidate.canonical_id)
        sector = candidate.sector or "UNKNOWN"
        by_sector.setdefault(sector, []).append(candidate)

    def _full_coverage(candidate: CandidateSecurity) -> bool:
        coverage = coverage_by_id[candidate.canonical_id].signal_family_coverage
        return coverage.earnings and coverage.analyst_grades

    for queue in by_sector.values():
        queue.sort(key=lambda c: (0 if _full_coverage(c) else 1, c.canonical_id))

    sector_cap = max(1, math.ceil(target_size * sector_cap_fraction))
    sector_order = sorted(by_sector.keys())
    sector_counts = {sector: 0 for sector in sector_order}

    selected: list[CandidateSecurity] = []
    round_idx = 0
    while len(selected) < target_size:
        progressed = False
        for sector in sector_order:
            if len(selected) >= target_size:
                break
            queue = by_sector[sector]
            if round_idx >= len(queue) or sector_counts[sector] >= sector_cap:
                continue
            selected.append(queue[round_idx])
            sector_counts[sector] += 1
            progressed = True
        if not progressed:
            break
        round_idx += 1

    return selected
