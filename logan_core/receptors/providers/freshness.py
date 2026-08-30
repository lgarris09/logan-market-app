"""Universe Manager V1a Block 8 -- the explicit freshness contract. Four
states, never collapsed into a single "live" boolean:

  FRESH               -- observed well within its target refresh cadence.
  RECENTLY_OBSERVED   -- still within its TTL, but past the "just fetched"
                         half of that window.
  STALE_WITHIN_GRACE   -- past its TTL, but still within the signal
                         family's own grace window -- may still support an
                         existing opportunity/revision (never a brand-new
                         one), matching FmpResponseCache's own existing
                         stale_grace_seconds mechanism.
  UNAVAILABLE          -- no value at all, or past even the grace window.

This distinction matters because "no opportunity qualified" and "STRATUS
could not reliably evaluate this security" are different facts (Block 8's
explicit requirement) -- the first is an honest, healthy empty result; the
second is UNAVAILABLE and belongs in diagnostics/operational reporting,
never silently presented the same way.

Every TTL value reused here is the exact existing constant from fmp.py --
this module never redefines or re-derives a cache lifetime, it only
attaches a grace window and a classification function on top of the TTLs
that already govern real caching behavior.
"""

from dataclasses import dataclass
from typing import Literal, Optional

from .fmp import (
    BENCHMARK_QUOTE_CACHE_TTL_SECONDS,
    EARNINGS_CACHE_TTL_SECONDS,
    EARNINGS_STALE_GRACE_SECONDS,
    GRADE_CACHE_TTL_SECONDS,
    PROFILE_CACHE_TTL_SECONDS,
    QUOTE_CACHE_TTL_SECONDS,
)

FreshnessState = Literal[
    "FRESH", "RECENTLY_OBSERVED", "STALE_WITHIN_GRACE", "UNAVAILABLE"
]


@dataclass(frozen=True)
class FreshnessContract:
    signal_family: str
    target_ttl_seconds: float
    grace_seconds: float


# Grace windows, one per signal family -- quote (price-sensitive) gets the
# shortest relative grace; profile (slow-changing static reference data)
# gets the longest. Earnings reuses the exact existing
# EARNINGS_STALE_GRACE_SECONDS this codebase already wired into
# FmpEarningsProvider's stale-serving fallback (V2.3A.1) -- the other four
# families' grace windows are newly defined by this contract but not yet
# wired into their own get_or_fetch() calls (see this module's own
# docstring: defining the contract is Block 8's job; activating
# stale-serving for a family that doesn't have it today is a separate,
# explicit follow-up, not a silent behavior change made here).
SIGNAL_FRESHNESS_CONTRACTS: dict[str, FreshnessContract] = {
    "quote": FreshnessContract("quote", QUOTE_CACHE_TTL_SECONDS, 15 * 60),
    "earnings": FreshnessContract(
        "earnings", EARNINGS_CACHE_TTL_SECONDS, EARNINGS_STALE_GRACE_SECONDS
    ),
    "analyst_grade": FreshnessContract(
        "analyst_grade", GRADE_CACHE_TTL_SECONDS, 6 * 60 * 60
    ),
    "profile": FreshnessContract("profile", PROFILE_CACHE_TTL_SECONDS, 72 * 60 * 60),
    "benchmark_quote": FreshnessContract(
        "benchmark_quote", BENCHMARK_QUOTE_CACHE_TTL_SECONDS, 2 * 60 * 60
    ),
}


def classify_freshness(
    *,
    has_value: bool,
    age_seconds: Optional[float],
    contract: FreshnessContract,
) -> FreshnessState:
    """Pure, deterministic classification. `age_seconds=None` is only valid
    when `has_value=False` (no observation exists at all, so age is
    meaningless) -- any other combination is a caller bug, not silently
    tolerated.
    """
    if not has_value:
        return "UNAVAILABLE"
    assert age_seconds is not None, "age_seconds is required when has_value=True"
    if age_seconds <= contract.target_ttl_seconds * 0.5:
        return "FRESH"
    if age_seconds <= contract.target_ttl_seconds:
        return "RECENTLY_OBSERVED"
    if age_seconds <= contract.target_ttl_seconds + contract.grace_seconds:
        return "STALE_WITHIN_GRACE"
    return "UNAVAILABLE"


def signal_family_contract(signal_family: str) -> FreshnessContract:
    """Raises KeyError for an unregistered family -- never silently
    returns a default/guessed contract for a signal family this module
    doesn't actually know about."""
    return SIGNAL_FRESHNESS_CONTRACTS[signal_family]
