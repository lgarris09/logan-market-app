"""Universe Manager V1a Block 10 -- deterministic top-band thesis
diversity. Applied after objective thesis synthesis and personal-relevance
ranking (each candidate's `rank` is already-computed, objective-plus-
personal-relevance feed order) -- this module never re-ranks or re-scores
anything, it only decides which already-ranked candidates actually occupy
the top `top_n` (default 5) positions, so a user's field isn't dominated by
near-duplicate theses (five earnings-driven Technology cards, say) even
when they'd otherwise all rank highly.

An excluded candidate is never deleted, never has its objective
qualification changed, and never has its thesis weakened -- it simply
isn't in `selected`, with a SuppressionRecord explaining exactly why
(Block 10's own explicit requirement).
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from logan_core.contracts.thesis import ThesisMetadata

DIVERSITY_POLICY_VERSION_V1 = "thesis-diversity-v1"

DEFAULT_TOP_N = 5
DEFAULT_ENTITY_CAP = 1
DEFAULT_SECTOR_CAP = 2
DEFAULT_SIGNAL_FAMILY_CAP = 2
DEFAULT_SECTOR_DRIVER_CAP = 1

SuppressionReason = Literal[
    "ENTITY_CAP", "SECTOR_CAP", "SIGNAL_FAMILY_CAP", "DRIVER_CAP"
]


class ThesisCandidate(BaseModel):
    """A minimal, typed candidate for diversity enforcement -- `rank` is the
    already-computed feed order (objective qualification + personal
    relevance both already applied upstream; this module reads it, never
    computes it). `is_watched` lets an active Watch bypass at most one
    non-entity cap (Block 10's own explicit limit)."""

    event_id: UUID
    rank: int = Field(ge=1)
    metadata: ThesisMetadata
    is_watched: bool = False


class SuppressionRecord(BaseModel):
    schema_version: str = "1.0"
    event_id: UUID
    suppression_reason: SuppressionReason
    blocking_thesis_id: UUID
    diversity_policy_version: str


class DiversityResult(BaseModel):
    schema_version: str = "1.0"
    policy_version: str
    selected: list[ThesisCandidate] = Field(default_factory=list)
    suppressed: list[SuppressionRecord] = Field(default_factory=list)


def apply_diversity_caps(
    candidates: list[ThesisCandidate],
    *,
    top_n: int = DEFAULT_TOP_N,
    entity_cap: int = DEFAULT_ENTITY_CAP,
    sector_cap: int = DEFAULT_SECTOR_CAP,
    signal_family_cap: int = DEFAULT_SIGNAL_FAMILY_CAP,
    sector_driver_cap: int = DEFAULT_SECTOR_DRIVER_CAP,
    policy_version: str = DIVERSITY_POLICY_VERSION_V1,
) -> DiversityResult:
    """Walks `candidates` in ascending rank order, admitting up to `top_n`
    into `selected`. A candidate that would violate the one-thesis-per-
    entity cap is always suppressed, Watch included -- that cap has no
    bypass. A candidate that violates exactly one of the other three caps
    (sector/signal-family/(sector,driver)) is admitted anyway when
    `is_watched` is True; violating more than one simultaneously is never
    bypassed, even by Watch (Block 10: Watch may bypass *one* diversity
    cap, not several at once).
    """
    ordered = sorted(candidates, key=lambda c: c.rank)
    selected: list[ThesisCandidate] = []
    suppressed: list[SuppressionRecord] = []

    entity_counts: dict[str, int] = {}
    sector_counts: dict[str, int] = {}
    signal_family_counts: dict[str, int] = {}
    sector_driver_counts: dict[tuple[str, str], int] = {}
    first_for_entity: dict[str, UUID] = {}
    first_for_sector: dict[str, UUID] = {}
    first_for_signal_family: dict[str, UUID] = {}
    first_for_sector_driver: dict[tuple[str, str], UUID] = {}

    for candidate in ordered:
        if len(selected) >= top_n:
            break
        m = candidate.metadata
        entity_key = m.primary_entity_id
        sector_key = m.sector or "UNKNOWN"
        signal_family_key = m.primary_signal_family
        driver_key = (sector_key, m.market_driver_tag)

        if entity_counts.get(entity_key, 0) >= entity_cap:
            suppressed.append(
                SuppressionRecord(
                    event_id=candidate.event_id,
                    suppression_reason="ENTITY_CAP",
                    blocking_thesis_id=first_for_entity[entity_key],
                    diversity_policy_version=policy_version,
                )
            )
            continue

        violations: list[tuple[SuppressionReason, UUID]] = []
        if sector_counts.get(sector_key, 0) >= sector_cap:
            violations.append(("SECTOR_CAP", first_for_sector[sector_key]))
        if signal_family_counts.get(signal_family_key, 0) >= signal_family_cap:
            violations.append(
                ("SIGNAL_FAMILY_CAP", first_for_signal_family[signal_family_key])
            )
        if sector_driver_counts.get(driver_key, 0) >= sector_driver_cap:
            violations.append(("DRIVER_CAP", first_for_sector_driver[driver_key]))

        if violations and not (candidate.is_watched and len(violations) == 1):
            reason, blocking_id = violations[0]
            suppressed.append(
                SuppressionRecord(
                    event_id=candidate.event_id,
                    suppression_reason=reason,
                    blocking_thesis_id=blocking_id,
                    diversity_policy_version=policy_version,
                )
            )
            continue

        selected.append(candidate)
        entity_counts[entity_key] = entity_counts.get(entity_key, 0) + 1
        sector_counts[sector_key] = sector_counts.get(sector_key, 0) + 1
        signal_family_counts[signal_family_key] = (
            signal_family_counts.get(signal_family_key, 0) + 1
        )
        sector_driver_counts[driver_key] = sector_driver_counts.get(driver_key, 0) + 1
        first_for_entity.setdefault(entity_key, candidate.event_id)
        first_for_sector.setdefault(sector_key, candidate.event_id)
        first_for_signal_family.setdefault(signal_family_key, candidate.event_id)
        first_for_sector_driver.setdefault(driver_key, candidate.event_id)

    return DiversityResult(
        policy_version=policy_version, selected=selected, suppressed=suppressed
    )
