"""Qualification states, reason codes, comparability checks and materiality
bands -- SHADOW ONLY (ADR-078).

Nothing in the pipeline imports this module. It exists so the governed
rules can be reviewed, tested and replayed against real provider data
before any of them changes what STRATUS surfaces.

The concepts are deliberately separate (docs/CONFIDENCE_SEMANTICS.md):

  qualification      did a governed trigger validly fire?        (this module)
  evidence strength  how well-supported and usable is the evidence?  (not here)
  materiality        how large was the validated observed change?    (this module)

Materiality is a band, never a score, and never an input to evidence
strength. A blocked observation has no materiality at all: an invalid or
incomparable input is not "weak evidence", it is no trigger.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal, Optional

QualificationState = Literal[
    "qualified",
    "not_qualified",
    "blocked_invalid_input",
    "blocked_incomparable_basis",
    "blocked_stale_or_missing_required_fields",
]

MaterialityBand = Literal[
    "barely_qualified", "meaningful", "large", "capped_exceptional"
]

# --- reason codes -------------------------------------------------------------
# code -> (state it produces, plain-language meaning). Stable identifiers:
# never renamed, only added to.
REASON_CODES: dict[str, tuple[QualificationState, str]] = {
    # qualified / not qualified
    "qualified": ("qualified", "All required checks passed and the rule fired."),
    "below_threshold": (
        "not_qualified",
        "Inputs are valid and comparable; the change is below the firing threshold.",
    ),
    "wrong_direction": (
        "not_qualified",
        "Inputs are valid and comparable; the change is not in this trigger's direction.",
    ),
    # invalid input
    "input_non_finite": (
        "blocked_invalid_input",
        "A required number is NaN or infinite.",
    ),
    "issuer_mismatch": (
        "blocked_invalid_input",
        "Actual and estimate do not refer to the same issuer.",
    ),
    "fiscal_period_mismatch": (
        "blocked_invalid_input",
        "Actual and estimate refer to different fiscal periods.",
    ),
    "currency_mismatch": (
        "blocked_invalid_input",
        "Actual and estimate are in different currencies.",
    ),
    "estimate_not_pre_release": (
        "blocked_invalid_input",
        "The estimate is dated at or after the release, so it is not a pre-release consensus.",
    ),
    "unadjusted_split_between_estimate_and_actual": (
        "blocked_invalid_input",
        "A split took effect between the estimate and the actual and is not adjusted for.",
    ),
    "previous_close_not_positive": (
        "blocked_invalid_input",
        "The previous close is zero or negative.",
    ),
    # incomparable basis
    "earnings_eps_comparability_unresolved": (
        "blocked_incomparable_basis",
        "It cannot be established that actual and estimated EPS are on the same basis.",
    ),
    "eps_basis_unknown": (
        "blocked_incomparable_basis",
        "The accounting basis (GAAP or adjusted) of the actual or the estimate is not known.",
    ),
    "eps_basis_mismatch": (
        "blocked_incomparable_basis",
        "Actual and estimate are on different accounting bases.",
    ),
    "eps_share_basis_unknown": (
        "blocked_incomparable_basis",
        "Whether actual or estimate is basic or diluted is not known.",
    ),
    "eps_share_basis_mismatch": (
        "blocked_incomparable_basis",
        "One of actual and estimate is basic and the other diluted.",
    ),
    "revenue_definition_unresolved": (
        "blocked_incomparable_basis",
        "It cannot be established that actual and estimated revenue use the same definition.",
    ),
    "estimate_denominator_ineligible": (
        "blocked_incomparable_basis",
        "The estimate is zero, near zero or negative, so a percentage surprise is not meaningful.",
    ),
    "restatement_unresolved": (
        "blocked_incomparable_basis",
        "The actual has been restated, or it is unknown whether it has.",
    ),
    # stale or missing
    "actual_missing": (
        "blocked_stale_or_missing_required_fields",
        "The reported actual is missing.",
    ),
    "estimate_missing": (
        "blocked_stale_or_missing_required_fields",
        "The estimate is missing.",
    ),
    "fiscal_period_unverified": (
        "blocked_stale_or_missing_required_fields",
        "The fiscal period of the actual or the estimate is not provided.",
    ),
    "estimate_timestamp_unverified": (
        "blocked_stale_or_missing_required_fields",
        "There is no timestamp proving the estimate was captured before the release.",
    ),
    "estimate_stale": (
        "blocked_stale_or_missing_required_fields",
        "The estimate was captured too long before the release.",
    ),
    "release_timestamp_missing": (
        "blocked_stale_or_missing_required_fields",
        "The release time of the actual is not provided.",
    ),
    "currency_unverified": (
        "blocked_stale_or_missing_required_fields",
        "The currency of the actual or the estimate is not provided.",
    ),
    "split_status_unverified": (
        "blocked_stale_or_missing_required_fields",
        "It is not known whether a split falls between the estimate and the actual.",
    ),
    "provenance_missing": (
        "blocked_stale_or_missing_required_fields",
        "The source of the actual or the estimate is not recorded.",
    ),
    "quote_missing": (
        "blocked_stale_or_missing_required_fields",
        "The price or the previous close is missing.",
    ),
    "quote_stale": (
        "blocked_stale_or_missing_required_fields",
        "The quote is older than the allowed age.",
    ),
}

# The most severe state present governs. Invalid outranks incomparable
# outranks missing: a contradiction is worse than an unknown.
_STATE_PRECEDENCE: tuple[QualificationState, ...] = (
    "blocked_invalid_input",
    "blocked_incomparable_basis",
    "blocked_stale_or_missing_required_fields",
    "not_qualified",
    "qualified",
)


@dataclass(frozen=True)
class QualificationResult:
    trigger_family: str
    state: QualificationState
    reason_codes: tuple[str, ...]
    # Only ever set when state == "qualified".
    magnitude_pct: Optional[float] = None
    materiality: Optional[MaterialityBand] = None
    direction: Optional[Literal["positive", "negative"]] = None

    @property
    def is_qualified(self) -> bool:
        return self.state == "qualified"


def _resolve(
    trigger_family: str,
    codes: list[str],
    *,
    magnitude_pct: Optional[float] = None,
    materiality: Optional[MaterialityBand] = None,
    direction: Optional[Literal["positive", "negative"]] = None,
) -> QualificationResult:
    ordered = tuple(dict.fromkeys(codes))  # stable, de-duplicated
    states = {REASON_CODES[code][0] for code in ordered}
    state = next(s for s in _STATE_PRECEDENCE if s in states)
    qualified = state == "qualified"
    return QualificationResult(
        trigger_family=trigger_family,
        state=state,
        reason_codes=ordered,
        magnitude_pct=magnitude_pct if qualified else None,
        materiality=materiality if qualified else None,
        direction=direction if qualified else None,
    )


def _finite(value: Optional[float]) -> bool:
    return value is not None and math.isfinite(value)


# --- denominator eligibility ---------------------------------------------------

# Below these, a percentage of the estimate is not a meaningful measure.
# Absolute floors, not percentiles: an EPS consensus under ten cents turns a
# few cents of difference into a "50% surprise".
EPS_ESTIMATE_MIN_ABS = 0.10
REVENUE_ESTIMATE_MIN = 1.0


def denominator_eligible(estimate: Optional[float], *, minimum: float) -> bool:
    """True only for a finite, positive estimate at or above `minimum`.
    Zero, near-zero and negative estimates are ineligible -- they are never
    capped or clamped into a 'valid' percentage."""
    return _finite(estimate) and estimate >= minimum  # type: ignore[operator]


# --- materiality bands ---------------------------------------------------------


@dataclass(frozen=True)
class BandTable:
    """Lower bounds, in percent of the comparison base, for one trigger
    family. `threshold` is the qualification threshold; below it there is
    no trigger and therefore no band."""

    family: str
    threshold: float
    meaningful: float
    large: float
    capped_exceptional: float

    def band(self, magnitude_pct: float) -> Optional[MaterialityBand]:
        magnitude = abs(magnitude_pct)
        if not math.isfinite(magnitude) or magnitude < self.threshold:
            return None
        if magnitude >= self.capped_exceptional:
            return "capped_exceptional"
        if magnitude >= self.large:
            return "large"
        if magnitude >= self.meaningful:
            return "meaningful"
        return "barely_qualified"


# Proposed, for review. Each bound is a fixed multiple of the family's own
# qualification threshold (1x, 1.5x, 2.5x, 4x) -- chosen for explainability,
# not fitted to any sample. `capped_exceptional` is a ceiling on what the
# band can express: beyond it, size stops adding information.
PRICE_MOVE_BANDS = BandTable(
    "price_move", threshold=5.0, meaningful=7.5, large=12.5, capped_exceptional=20.0
)
REVENUE_SURPRISE_BANDS = BandTable(
    "revenue_surprise", threshold=2.0, meaningful=3.0, large=5.0, capped_exceptional=8.0
)
# EPS surprise: deliberately no band table. EPS magnitude stays blocked until
# comparability can be established (ADR-078). Analyst actions: magnitude-
# neutral by decision; no band table.


# --- price movement ------------------------------------------------------------

PRICE_QUOTE_MAX_AGE = timedelta(hours=24)


def qualify_price_move(
    *,
    price: Optional[float],
    previous_close: Optional[float],
    quote_at: Optional[datetime],
    now: datetime,
    source_id: Optional[str],
) -> QualificationResult:
    codes: list[str] = []
    if price is None or previous_close is None or quote_at is None:
        codes.append("quote_missing")
    if not source_id:
        codes.append("provenance_missing")
    if (price is not None and not math.isfinite(price)) or (
        previous_close is not None and not math.isfinite(previous_close)
    ):
        codes.append("input_non_finite")
    elif previous_close is not None and previous_close <= 0:
        codes.append("previous_close_not_positive")
    if quote_at is not None and now - quote_at > PRICE_QUOTE_MAX_AGE:
        codes.append("quote_stale")
    if codes:
        return _resolve("price_move", codes)

    assert price is not None and previous_close is not None
    change_pct = (price - previous_close) / previous_close * 100.0
    band = PRICE_MOVE_BANDS.band(change_pct)
    if band is None:
        return _resolve("price_move", ["below_threshold"])
    return _resolve(
        "price_move",
        ["qualified"],
        magnitude_pct=change_pct,
        materiality=band,
        direction="positive" if change_pct > 0 else "negative",
    )


# --- estimate vs actual: shared checks ------------------------------------------

ESTIMATE_MAX_AGE_BEFORE_RELEASE = timedelta(days=45)


@dataclass(frozen=True)
class EstimateActualEvidence:
    """Everything needed to decide whether an actual may be compared with
    an estimate. `None` always means 'not known' -- it is never read as
    'fine'. Field names describe facts, not a provider's payload."""

    actual: Optional[float]
    estimate: Optional[float]
    actual_issuer: Optional[str] = None
    estimate_issuer: Optional[str] = None
    actual_fiscal_period: Optional[str] = None  # e.g. "2026-Q2"
    estimate_fiscal_period: Optional[str] = None
    release_at: Optional[datetime] = None  # when the actual became public
    estimate_as_of: Optional[datetime] = None  # when the estimate was captured
    actual_currency: Optional[str] = None
    estimate_currency: Optional[str] = None
    split_between: Optional[bool] = (
        None  # a split between estimate_as_of and release_at
    )
    split_adjusted: Optional[bool] = None
    restated: Optional[bool] = None
    actual_source: Optional[str] = None
    estimate_source: Optional[str] = None
    # EPS only
    actual_basis: Optional[Literal["gaap", "adjusted"]] = None
    estimate_basis: Optional[Literal["gaap", "adjusted"]] = None
    actual_share_basis: Optional[Literal["basic", "diluted"]] = None
    estimate_share_basis: Optional[Literal["basic", "diluted"]] = None
    # Revenue only: do both use the same revenue definition?
    revenue_definition_matched: Optional[bool] = None
    extra: dict = field(default_factory=dict)


def _shared_checks(e: EstimateActualEvidence, *, minimum_estimate: float) -> list[str]:
    codes: list[str] = []
    if e.actual is None:
        codes.append("actual_missing")
    if e.estimate is None:
        codes.append("estimate_missing")
    if (e.actual is not None and not math.isfinite(e.actual)) or (
        e.estimate is not None and not math.isfinite(e.estimate)
    ):
        codes.append("input_non_finite")
    elif e.estimate is not None and not denominator_eligible(
        e.estimate, minimum=minimum_estimate
    ):
        codes.append("estimate_denominator_ineligible")

    if not e.actual_source or not e.estimate_source:
        codes.append("provenance_missing")

    if e.actual_issuer and e.estimate_issuer:
        if e.actual_issuer != e.estimate_issuer:
            codes.append("issuer_mismatch")
    else:
        codes.append("provenance_missing")

    if e.actual_fiscal_period is None or e.estimate_fiscal_period is None:
        codes.append("fiscal_period_unverified")
    elif e.actual_fiscal_period != e.estimate_fiscal_period:
        codes.append("fiscal_period_mismatch")

    if e.release_at is None:
        codes.append("release_timestamp_missing")
    if e.estimate_as_of is None:
        codes.append("estimate_timestamp_unverified")
    if e.release_at is not None and e.estimate_as_of is not None:
        if e.estimate_as_of >= e.release_at:
            codes.append("estimate_not_pre_release")
        elif e.release_at - e.estimate_as_of > ESTIMATE_MAX_AGE_BEFORE_RELEASE:
            codes.append("estimate_stale")

    if e.actual_currency is None or e.estimate_currency is None:
        codes.append("currency_unverified")
    elif e.actual_currency != e.estimate_currency:
        codes.append("currency_mismatch")

    if e.split_between is None:
        codes.append("split_status_unverified")
    elif e.split_between and e.split_adjusted is not True:
        codes.append("unadjusted_split_between_estimate_and_actual")

    if e.restated is not False:
        codes.append("restatement_unresolved")
    return codes


def _surprise_pct(e: EstimateActualEvidence) -> float:
    assert e.actual is not None and e.estimate is not None
    return (e.actual - e.estimate) / e.estimate * 100.0


# --- EPS beat ------------------------------------------------------------------

EPS_BEAT_THRESHOLD_PCT = 5.0  # the existing STOCK_EARNINGS_BEAT rule, unchanged


def qualify_eps_beat(e: EstimateActualEvidence) -> QualificationResult:
    """Hard gate. An EPS beat qualifies only when actual and estimate are
    proven comparable. Anything unknown blocks it -- it is never
    soft-discounted, and no magnitude or band is ever reported for EPS."""
    codes = _shared_checks(e, minimum_estimate=EPS_ESTIMATE_MIN_ABS)

    basis_unresolved = False
    if e.actual_basis is None or e.estimate_basis is None:
        codes.append("eps_basis_unknown")
        basis_unresolved = True
    elif e.actual_basis != e.estimate_basis:
        codes.append("eps_basis_mismatch")
        basis_unresolved = True
    if e.actual_share_basis is None or e.estimate_share_basis is None:
        codes.append("eps_share_basis_unknown")
        basis_unresolved = True
    elif e.actual_share_basis != e.estimate_share_basis:
        codes.append("eps_share_basis_mismatch")
        basis_unresolved = True
    if basis_unresolved:
        codes.insert(0, "earnings_eps_comparability_unresolved")

    if codes:
        return _resolve("earnings_eps_beat", codes)

    surprise = _surprise_pct(e)
    if surprise <= 0:
        return _resolve("earnings_eps_beat", ["wrong_direction"])
    if surprise < EPS_BEAT_THRESHOLD_PCT:
        return _resolve("earnings_eps_beat", ["below_threshold"])
    # Qualified, but magnitude-neutral: no magnitude_pct, no band.
    return _resolve("earnings_eps_beat", ["qualified"], direction="positive")


# --- revenue surprise ----------------------------------------------------------


def qualify_revenue_surprise(e: EstimateActualEvidence) -> QualificationResult:
    codes = _shared_checks(e, minimum_estimate=REVENUE_ESTIMATE_MIN)
    if e.revenue_definition_matched is not True:
        codes.append("revenue_definition_unresolved")
    if codes:
        return _resolve("revenue_surprise", codes)

    surprise = _surprise_pct(e)
    band = REVENUE_SURPRISE_BANDS.band(surprise)
    if band is None:
        return _resolve("revenue_surprise", ["below_threshold"])
    return _resolve(
        "revenue_surprise",
        ["qualified"],
        magnitude_pct=surprise,
        materiality=band,
        direction="positive" if surprise > 0 else "negative",
    )
