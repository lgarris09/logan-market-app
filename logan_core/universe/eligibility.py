"""Universe Manager V1a Block 3 -- deterministic, STRATUS-owned universe
eligibility rules applied to one CandidateSecurity at a time. Pure
function, no I/O: real provider data (quotes, profiles, signal-family
coverage) is fetched by a caller (backend/app -- the established split
between logan_core's pure decision logic and backend/app's real I/O, e.g.
ask_context.py/opportunity_quality_report.py) and handed in as plain,
already-observed facts.

Every result carries a reason code (never a bare boolean) -- see
EligibilityResult.reason_codes. `PARTIAL_SIGNAL_COVERAGE` is a modifier a
still-eligible candidate can carry alongside `ELIGIBLE_ACTIVE_LIQUID`: this
codebase must never assume "a quote exists" implies "every signal family
is covered" (Block 3's explicit requirement).
"""

from datetime import datetime, timezone
from typing import Optional

from logan_core.contracts import (
    CandidateSecurity,
    EligibilityResult,
    SignalFamilyCoverage,
)

ELIGIBILITY_POLICY_VERSION_V1 = "universe-eligibility-v1"

# A deliberately conservative liquidity floor -- generous enough that every
# S&P 100-caliber candidate in the V1a snapshot clears it under normal
# market conditions, while still excluding a genuinely illiquid/thinly-
# traded name if one ever entered the candidate source. Not tuned against
# live data (no real candidate source is wired to real trading yet) --
# revisit once a real snapshot + real provider health data exists.
MIN_AVERAGE_DOLLAR_VOLUME = 5_000_000.0

REJECT_INVALID_SYMBOL = "REJECT_INVALID_SYMBOL"
REJECT_TRADING_INACTIVE = "REJECT_TRADING_INACTIVE"
REJECT_UNSUPPORTED_EXCHANGE = "REJECT_UNSUPPORTED_EXCHANGE"
REJECT_DATA_HEALTH = "REJECT_DATA_HEALTH"
REJECT_INSUFFICIENT_LIQUIDITY = "REJECT_INSUFFICIENT_LIQUIDITY"
ELIGIBLE_ACTIVE_LIQUID = "ELIGIBLE_ACTIVE_LIQUID"
PARTIAL_SIGNAL_COVERAGE = "PARTIAL_SIGNAL_COVERAGE"

_VALID_SYMBOL_MAX_LENGTH = 10


def _has_valid_symbol_shape(symbol: str) -> bool:
    return bool(symbol) and symbol.isalpha() and len(symbol) <= _VALID_SYMBOL_MAX_LENGTH


def evaluate_eligibility(
    candidate: CandidateSecurity,
    *,
    is_actively_trading: bool,
    is_supported_exchange: bool,
    has_price_coverage: bool,
    has_earnings_coverage: bool,
    has_analyst_grade_coverage: bool,
    average_dollar_volume: Optional[float],
    provider_health_ok: bool,
    now: Optional[datetime] = None,
) -> EligibilityResult:
    """Checks, in order (first failing hard rule wins -- mirrors this
    codebase's existing `_watch_route`-style explicit-order precedent in
    policy/engine.py): valid symbol shape, actively trading, supported
    exchange, minimum provider data health (at least price coverage
    reachable at all), sufficient liquidity. A candidate that clears every
    hard rule is eligible; if it's missing earnings or analyst-grade
    coverage specifically (price coverage always required, checked above),
    `PARTIAL_SIGNAL_COVERAGE` is appended as an informational modifier
    alongside the terminal `ELIGIBLE_ACTIVE_LIQUID` code -- never silently
    dropped and never treated as "coverage doesn't matter."
    """
    now = now or datetime.now(timezone.utc)
    coverage = SignalFamilyCoverage(
        price=has_price_coverage,
        earnings=has_earnings_coverage,
        analyst_grades=has_analyst_grade_coverage,
    )

    def _result(eligible: bool, reason_codes: list[str]) -> EligibilityResult:
        return EligibilityResult(
            canonical_id=candidate.canonical_id,
            symbol=candidate.symbol,
            eligible=eligible,
            reason_codes=reason_codes,
            signal_family_coverage=coverage,
            policy_version=ELIGIBILITY_POLICY_VERSION_V1,
            evaluated_at=now,
        )

    if not _has_valid_symbol_shape(candidate.symbol):
        return _result(False, [REJECT_INVALID_SYMBOL])
    if not is_actively_trading:
        return _result(False, [REJECT_TRADING_INACTIVE])
    if not is_supported_exchange:
        return _result(False, [REJECT_UNSUPPORTED_EXCHANGE])
    if not provider_health_ok or not has_price_coverage:
        # No reliable price coverage at all is a data-health rejection, not
        # merely "partial coverage" -- price is the one signal family every
        # monitored security must have (Block 3: "quote available" is the
        # floor, never itself sufficient, but its absence is disqualifying).
        return _result(False, [REJECT_DATA_HEALTH])
    if (
        average_dollar_volume is None
        or average_dollar_volume < MIN_AVERAGE_DOLLAR_VOLUME
    ):
        return _result(False, [REJECT_INSUFFICIENT_LIQUIDITY])

    reason_codes = [ELIGIBLE_ACTIVE_LIQUID]
    if not (has_earnings_coverage and has_analyst_grade_coverage):
        reason_codes.append(PARTIAL_SIGNAL_COVERAGE)
    return _result(True, reason_codes)
