"""Universe Manager V1a (Block 1-6) -- the typed contracts for STRATUS's
own shared, objective, user-agnostic decision about which securities it
monitors at all, distinct from (and prerequisite to) every existing
per-user decision this codebase already makes.

Four first-class, distinct states (Block 1) -- preserved as a hard
invariant throughout this codebase, never collapsed into one another:

  UNIVERSE_ELIGIBLE     -- satisfies STRATUS's objective universe rules
                           (eligibility.py) and MAY be considered for
                           monitoring. Not yet monitored.
  MONITORED             -- currently part of the bounded active upstream
                           data cohort (cohort_selection.py) -- STRATUS is
                           actually polling this security's signals. Not
                           necessarily producing any opportunity right now.
  OBJECTIVELY_QUALIFIED -- live evidence produced a real opportunity under
                           the existing, unchanged objective signal/thesis
                           rules (AttentionRecommendation.recommend, already
                           built in opportunity/engine.py) -- entirely
                           unaware of any specific user.
  PERSONALLY_SURFACED   -- the opportunity was actually selected for a
                           specific user's Attention Field (PrioritizedItem.
                           visibility in ("primary", "feed"), already built
                           in prioritization/engine.py + exploration/).

Eligible != Monitored != Opportunity != Surfaced. Personal Learning may
only ever participate once OBJECTIVELY_QUALIFIED truth already exists --
it must never influence whether something is UNIVERSE_ELIGIBLE or
MONITORED (see Block 15's hard user-agnostic-provider-sensing boundary).
"""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

UniverseLifecycleState = Literal[
    "UNIVERSE_ELIGIBLE",
    "MONITORED",
    "OBJECTIVELY_QUALIFIED",
    "PERSONALLY_SURFACED",
]

# A plain string, matching CompanyProfile.sector's own established
# convention (logan_core/receptors/providers/base.py) -- not a closed
# enum, since a real profile provider's own sector vocabulary (FMP's GICS-
# derived strings) isn't a value this codebase invents or constrains.
MarketCapBand = Literal["mega", "large", "mid", "small", "unknown"]


class CandidateSecurity(BaseModel):
    """One entry in a versioned candidate-source snapshot (Block 2) -- the
    bounded, replaceable input Universe eligibility (Block 3) evaluates.
    Never itself an investment recommendation, a preferred-stock list, or a
    signal of opportunity quality -- purely a candidate identity + the
    static reference data needed to evaluate eligibility/diversity.

    `canonical_id` is deliberately distinct from `symbol` (Block 2's own
    "canonical security identity" requirement) -- a real security can
    survive a ticker-symbol change (e.g. a rename or exchange migration);
    `symbol` is the current tradable string, `canonical_id` is meant to
    outlive it. V1a has no real security-master service, so `canonical_id`
    defaults to `"SYMBOL:{symbol}"` when no richer identifier (e.g. a CIK)
    is available -- an honest, documented V1a limitation, not a fabricated
    permanent identifier.
    """

    schema_version: str = "1.0"
    canonical_id: str
    symbol: str
    sector: Optional[str] = None
    market_cap_band: MarketCapBand = "unknown"


class CandidateSourceSnapshot(BaseModel):
    """The versioned, reproducible candidate source itself (Block 2) --
    e.g. one dated S&P 100 constituent list. A new `source_version` is a
    new, independently retrievable snapshot; loading an older version must
    always reproduce the exact same `securities` list it did when first
    published -- an updated snapshot must never silently rewrite a past
    version's membership.
    """

    schema_version: str = "1.0"
    source_id: str
    source_version: str
    effective_date: date
    retrieved_at: datetime
    securities: list[CandidateSecurity] = Field(default_factory=list)


class SignalFamilyCoverage(BaseModel):
    """Block 3's explicit rejection of "quote available = full signal
    coverage" -- each family tracked independently, since a real candidate
    may have live quotes but no analyst coverage, or vice versa."""

    price: bool = False
    earnings: bool = False
    analyst_grades: bool = False


class EligibilityResult(BaseModel):
    """The deterministic outcome of applying STRATUS-owned eligibility
    rules (eligibility.py) to one CandidateSecurity -- always carries a
    reason code (Block 3's explicit requirement), never a bare boolean."""

    schema_version: str = "1.0"
    canonical_id: str
    symbol: str
    eligible: bool
    reason_codes: list[str] = Field(default_factory=list)
    signal_family_coverage: SignalFamilyCoverage
    policy_version: str
    evaluated_at: datetime


class MembershipRecord(BaseModel):
    """One durable row in the Universe Membership Ledger (Block 5) -- the
    authoritative, queryable answer to "why was STRATUS monitoring this
    security on a particular date," without reconstructing it from
    application logs. `effective_until=None` means still-current
    membership; a non-None value plus `removal_reason` is a closed,
    historical membership interval that must never be mutated once closed
    (a later rule change opens a *new* record, never edits history).
    """

    schema_version: str = "1.0"
    canonical_id: str
    symbol: str
    source_version: str
    policy_version: str
    admission_reason_codes: list[str] = Field(default_factory=list)
    admitted_at: datetime
    effective_from: datetime
    effective_until: Optional[datetime] = None
    removed_at: Optional[datetime] = None
    removal_reason: Optional[str] = None
    replacement_of: Optional[str] = None  # a prior canonical_id, if any
    provider_health_snapshot: dict = Field(default_factory=dict)


class CohortRebalanceResult(BaseModel):
    """The outcome of one Block 4/6 cohort (re)selection pass -- every
    admission/removal decided this run, plus the policy version and churn
    count, so "no unexplained universe changes" (Block 6) is always
    verifiable from this one object."""

    schema_version: str = "1.0"
    policy_version: str
    rebalanced_at: datetime
    admitted: list[MembershipRecord] = Field(default_factory=list)
    removed: list[MembershipRecord] = Field(default_factory=list)
    unchanged_count: int = Field(ge=0, default=0)

    @property
    def churn_count(self) -> int:
        return len(self.admitted) + len(self.removed)
