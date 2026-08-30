"""Universe Manager V1a Block 9 -- deterministic market-driver tagging.
Pure function of trigger-code provenance (never an LLM call, never
semantic inference) -- see logan_core/contracts/thesis.py's own module
docstring for the taxonomy and its honest V1a coverage limits.
"""

from typing import Optional

from logan_core.convergence.tracker import STOCK_CONVERGENCE_MULTI_SOURCE
from logan_core.trigger_detection.stocks import (
    STOCK_ANALYST_DOWNGRADE,
    STOCK_ANALYST_UPGRADE,
    STOCK_EARNINGS_BEAT,
    STOCK_EARNINGS_IN_LINE,
    STOCK_EARNINGS_MISS,
    STOCK_PRICE_MOVE_SIGNIFICANT,
)

_EARNINGS_CODES = frozenset(
    {STOCK_EARNINGS_BEAT, STOCK_EARNINGS_MISS, STOCK_EARNINGS_IN_LINE}
)
_ANALYST_CODES = frozenset({STOCK_ANALYST_UPGRADE, STOCK_ANALYST_DOWNGRADE})


def classify_market_driver(
    trigger_codes: list[str], *, guidance_revised: bool = False
) -> str:
    """Priority order when multiple real codes fired together (a genuine
    convergence): earnings > analyst reassessment > price dislocation --
    matches this codebase's own existing precedent for "which signal is
    primary" (ask_engine.py's _dominant_signal_answer / _signals_answer
    already treat earnings as the header signal when present alongside
    others). STOCK_CONVERGENCE_MULTI_SOURCE itself is never a driver -- it
    describes multiple drivers aligning, not a driver on its own -- so it's
    excluded before classification.

    `guidance_revised` (Block 9's EARNINGS_GUIDANCE tag): sourced from the
    real, already-fetched EarningsReport.guidance_revised field (Sprint
    3.6.7), never inferred -- an earnings result that also revised guidance
    is tagged EARNINGS_GUIDANCE instead of the plainer EARNINGS_RESULT.

    Returns "UNCLASSIFIED" when trigger_codes is empty, contains only the
    convergence marker, or contains a code this classifier doesn't
    recognize -- never guesses.
    """
    real_codes = [c for c in trigger_codes if c != STOCK_CONVERGENCE_MULTI_SOURCE]
    if not real_codes:
        return "UNCLASSIFIED"

    if any(c in _EARNINGS_CODES for c in real_codes):
        return "EARNINGS_GUIDANCE" if guidance_revised else "EARNINGS_RESULT"
    if any(c in _ANALYST_CODES for c in real_codes):
        return "ANALYST_REASSESSMENT"
    if STOCK_PRICE_MOVE_SIGNIFICANT in real_codes:
        return "PRICE_DISLOCATION"
    return "UNCLASSIFIED"


def primary_signal_family(trigger_codes: list[str]) -> Optional[str]:
    """The single dominant signal family for diversity-cap purposes (Block
    10's "maximum 2 theses with the same primary signal family") -- earnings
    > analyst > price, same priority as classify_market_driver(). None
    (never a fabricated family) when nothing recognized fired."""
    real_codes = [c for c in trigger_codes if c != STOCK_CONVERGENCE_MULTI_SOURCE]
    if any(c in _EARNINGS_CODES for c in real_codes):
        return "earnings"
    if any(c in _ANALYST_CODES for c in real_codes):
        return "analyst_grade"
    if STOCK_PRICE_MOVE_SIGNIFICANT in real_codes:
        return "price"
    return None


def secondary_signal_families(trigger_codes: list[str]) -> list[str]:
    """Every OTHER recognized signal family beyond the primary one --
    Block 9's `secondary_signal_families[]`. Deterministic order (earnings,
    analyst_grade, price) regardless of trigger_codes' own order."""
    primary = primary_signal_family(trigger_codes)
    real_codes = set(trigger_codes)
    families: list[str] = []
    if _EARNINGS_CODES & real_codes and primary != "earnings":
        families.append("earnings")
    if _ANALYST_CODES & real_codes and primary != "analyst_grade":
        families.append("analyst_grade")
    if STOCK_PRICE_MOVE_SIGNIFICANT in real_codes and primary != "price":
        families.append("price")
    return families
