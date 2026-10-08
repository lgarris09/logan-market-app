"""ADR-083 -- condition-based evidence strength.

Evidence strength answers one question: how well-supported and usable is the
evidence behind this observation. It is not a probability, not an expected
return, not a recommendation, not the size of the event (materiality) and not
how much the event matters to a particular user (personal relevance).

It is derived from named, auditable conditions only. No numeric score
threshold is used and no population percentile: whatever distribution of
labels results is the honest one, including "every opportunity is Supported"
when every opportunity rests on a single origin.

A blocked observation never reaches this function. It emits no trigger, so it
never becomes an opportunity, and it receives no evidence-strength label.
"""

from dataclasses import dataclass
from typing import Literal, Optional

EvidenceStrength = Literal["strong", "supported", "limited", "conflicting"]

# Sentinel: the caller has no freshness classification to offer at all (the
# confidence layer, before the runtime freshness pass). Distinct from None,
# which means "freshness was evaluated and could not be established".
FRESHNESS_NOT_EVALUATED = "NOT_EVALUATED"

_FRESHNESS_ESTABLISHED = frozenset({"FRESH", "RECENTLY_OBSERVED"})

# Every condition code this module can emit, with its plain meaning. Stable:
# these are recorded and shown, so a code is never renamed or reused.
CONDITIONS: dict[str, str] = {
    # met
    "qualified": "A governed trigger qualified on valid, comparable inputs.",
    "independent_corroboration": "At least two independent origins support it.",
    "single_origin": "One origin supports it; nothing independent confirms it yet.",
    "details_complete": "Every expected detail of the event is present.",
    "no_conflict": "No contradicting evidence is on record.",
    "freshness_established": "STRATUS observed this evidence recently.",
    # non-critical limitations
    "details_incomplete": "Some expected details of the event are missing.",
    "elevated_manipulation_risk": "The source pattern carries some manipulation risk.",
    "freshness_within_grace": "STRATUS has not refreshed this evidence recently.",
    "freshness_unconfirmed": "STRATUS cannot confirm how recent this evidence is.",
    "freshness_not_evaluated": "No freshness contract applies to this evidence.",
    # critical
    "contradicting_evidence": "Contradicting evidence is on record.",
    "high_manipulation_risk": "The source pattern carries high manipulation risk.",
}

_LIMITATIONS = (
    "details_incomplete",
    "elevated_manipulation_risk",
    "freshness_within_grace",
    "freshness_unconfirmed",
)
_CRITICAL = ("contradicting_evidence", "high_manipulation_risk")


@dataclass(frozen=True)
class EvidenceStrengthAssessment:
    strength: EvidenceStrength
    # Every condition that held, in a stable order. Includes the limiting or
    # critical ones; `limitations` and `critical` are the subsets.
    conditions: tuple[str, ...]
    limitations: tuple[str, ...]
    critical: tuple[str, ...]


def assess_evidence_strength(
    *,
    corroboration: int,
    completeness: float,
    contradiction_flag: bool,
    manipulation_risk: str,
    freshness_state: Optional[str] = FRESHNESS_NOT_EVALUATED,
) -> EvidenceStrengthAssessment:
    """Pure. The rules, in order:

    conflicting  a critical condition holds: contradicting evidence, or high
                 manipulation risk. No strength tier is claimed.
    limited      qualified with at least one defined non-critical limitation:
                 details incomplete, elevated manipulation risk, freshness
                 within grace, or freshness unconfirmed.
    strong       qualified, corroborated by an independent origin, complete,
                 no conflict, and freshness established.
    supported    qualified on a single origin (or with freshness not
                 evaluated), complete, no conflict.
    """
    conditions: list[str] = ["qualified"]

    conditions.append(
        "independent_corroboration" if corroboration >= 2 else "single_origin"
    )
    conditions.append(
        "details_complete" if completeness >= 1.0 else "details_incomplete"
    )

    if contradiction_flag:
        conditions.append("contradicting_evidence")
    else:
        conditions.append("no_conflict")

    if manipulation_risk == "high":
        conditions.append("high_manipulation_risk")
    elif manipulation_risk != "low":
        conditions.append("elevated_manipulation_risk")

    if freshness_state == FRESHNESS_NOT_EVALUATED:
        conditions.append("freshness_not_evaluated")
    elif freshness_state in _FRESHNESS_ESTABLISHED:
        conditions.append("freshness_established")
    elif freshness_state == "STALE_WITHIN_GRACE":
        conditions.append("freshness_within_grace")
    else:
        # UNAVAILABLE, None, or any state this module does not recognize:
        # unknown is never treated as established.
        conditions.append("freshness_unconfirmed")

    critical = tuple(c for c in conditions if c in _CRITICAL)
    limitations = tuple(c for c in conditions if c in _LIMITATIONS)

    strength: EvidenceStrength
    if critical:
        strength = "conflicting"
    elif limitations:
        strength = "limited"
    elif (
        "independent_corroboration" in conditions
        and "freshness_established" in conditions
    ):
        strength = "strong"
    else:
        strength = "supported"

    return EvidenceStrengthAssessment(
        strength=strength,
        conditions=tuple(conditions),
        limitations=limitations,
        critical=critical,
    )


# Presentation wording. One place, so every surface says the same thing.
EVIDENCE_LABELS: dict[EvidenceStrength, str] = {
    "strong": "Strong evidence",
    "supported": "Supported evidence",
    "limited": "Limited evidence",
    "conflicting": "Conflicting evidence",
}


def evidence_label_for(strength: Optional[str]) -> Optional[str]:
    """The user-facing label, or None when there is no strength to state."""
    for known, label in EVIDENCE_LABELS.items():
        if known == strength:
            return label
    return None
