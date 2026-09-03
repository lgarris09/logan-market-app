"""Universe Manager V1a Expansion-Review Plumbing (V1a ITERATE block,
Phase 4) -- an advisory, read-only orchestration layer over the existing,
unmodified `logan_core.universe.expansion_gates.evaluate_expansion_gates()`
decision function. This module never scores, ranks, expands, or deploys
anything -- it only decides whether there is currently enough confirmed
real evidence to call the existing gate function at all, and if not, says
exactly why, distinguishing three different honest states a caller must
never conflate:

  INSUFFICIENT_OBSERVATION_WINDOW -- fewer than 14 consecutive real
      calendar days of telemetry exist yet (see universe_telemetry.py).
      Not a judgment about quality -- just "too early to ask the
      question."
  UNABLE_TO_EVALUATE -- the 14-day window exists, but one or more of the
      18 fields evaluate_expansion_gates() requires has no source this
      session could confirm against the actual governing plan text (see
      below) -- calling the gate function with a guessed value for any of
      them would be exactly the "invent a substitute definition" this
      block was told not to do. Distinct from "the gate failed": this
      status means the question literally cannot be answered yet, not
      that the answer is no.
  EVALUATED -- every required field has a confirmed-real source; the
      existing, completely unmodified evaluate_expansion_gates() is called
      and its real result (including the unresolved 6-of-7 policy this
      module never touches or reinterprets) is returned as-is.

Governance blocker, load-bearing and unresolved by this module: this
session searched the full repository for
`STRATUS_Master_Implementation_Plan_2026-08-30_REV1.md` and it does not
exist anywhere. Without it, no field-by-field mapping from this session's
real telemetry (universe_telemetry.py) to `OperationalMetricsSnapshot`/
`OpportunityQualityMetricsSnapshot`'s 18 specific fields can be *confirmed*
correct rather than guessed -- even a plausible-looking mapping (e.g.
"real FMP call failure rate" for `scheduled_fetch_failure_rate`) is a
guess about the plan's exact intended measurement without the source text,
and this module deliberately refuses to guess. `EVALUATED` is therefore an
honestly unreachable status today, proven by test -- the code path exists
so this module isn't dead weight once the plan text (or an explicit,
confirmed field-mapping decision) becomes available, but nothing here
pretends that day has already come.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal, Optional

from .universe_telemetry import daily_telemetry_range

REQUIRED_CONSECUTIVE_DAYS = 14

ExpansionReviewStatus = Literal[
    "INSUFFICIENT_OBSERVATION_WINDOW", "UNABLE_TO_EVALUATE", "EVALUATED"
]

# The 18 fields evaluate_expansion_gates() requires (11 operational + 7
# opportunity-quality, per logan_core/universe/expansion_gates.py) that
# this session found NO confirmed real-data source for, absent the actual
# governing plan text -- see this module's own docstring. Every one of
# these is either entirely unobserved anywhere in this codebase, or has a
# plausible-but-unconfirmed candidate this module refuses to guess is
# correct without the plan's own definition.
UNCONFIRMED_REQUIRED_FIELDS = (
    "fmp_rate_limit_responses",
    "scheduled_fetch_failure_rate",
    "time_sensitive_delay_p95_seconds",
    "time_sensitive_delay_p99_seconds",
    "critical_freshness_p95_ratio",
    "critical_freshness_p99_ratio",
    "stale_grace_read_rate",
    "user_visible_stale_beyond_grace_count",
    "peak_calls_per_minute",
    "coalescing_success_rate",
    "unexplained_universe_changes",
    "distinct_surfaced_theses_14d",
    "max_consecutive_zero_qualified_days",
    "top_five_diversity_survival_rate",
    "max_single_entity_impression_share",
    "max_single_sector_impression_share",
    "complete_evidence_payload_rate",
    "meaningful_revision_content_rate",
)


@dataclass(frozen=True)
class ExpansionReviewResult:
    status: ExpansionReviewStatus
    as_of: date
    consecutive_days_observed: int
    required_consecutive_days: int
    unconfirmed_fields: tuple = field(default_factory=tuple)
    notes: tuple = field(default_factory=tuple)
    gate_report: Optional[object] = None  # ExpansionGateReport, only when EVALUATED


def _consecutive_days_observed(as_of: date) -> int:
    """Walks backward from `as_of` counting real, unbroken daily telemetry
    rows -- a missing day anywhere in the walk stops the count immediately
    (a real gap, never bridged or assumed). Bounded to
    REQUIRED_CONSECUTIVE_DAYS + 1 lookback days since that's the most this
    caller ever needs to know ("do we have at least 14, and if not, how
    many do we actually have")."""
    rows_by_date = {
        row.date: row
        for row in daily_telemetry_range(
            as_of - timedelta(days=REQUIRED_CONSECUTIVE_DAYS + 1), as_of
        )
    }
    count = 0
    cursor = as_of
    while cursor.isoformat() in rows_by_date:
        count += 1
        cursor -= timedelta(days=1)
    return count


def build_expansion_review(*, as_of: Optional[date] = None) -> ExpansionReviewResult:
    """The one entry point a report/route calls. Purely advisory: never
    triggers expansion, never deploys, never mutates any state -- reads
    real telemetry and reports honestly on whether the existing expansion-
    gate decision function can currently be evaluated against it.
    """
    as_of = as_of or date.today()
    consecutive_days = _consecutive_days_observed(as_of)

    if consecutive_days < REQUIRED_CONSECUTIVE_DAYS:
        return ExpansionReviewResult(
            status="INSUFFICIENT_OBSERVATION_WINDOW",
            as_of=as_of,
            consecutive_days_observed=consecutive_days,
            required_consecutive_days=REQUIRED_CONSECUTIVE_DAYS,
            notes=(
                f"{consecutive_days} of {REQUIRED_CONSECUTIVE_DAYS} required "
                "consecutive real calendar days observed -- too early to "
                "evaluate the expansion gates at all, regardless of what "
                "those days show.",
            ),
        )

    # The window requirement is satisfied, but this session could not
    # confirm a correct field-by-field mapping from real telemetry to
    # every field evaluate_expansion_gates() requires, absent the missing
    # governing plan text -- see this module's own docstring. Reported
    # honestly as UNABLE_TO_EVALUATE, never silently defaulted or guessed.
    return ExpansionReviewResult(
        status="UNABLE_TO_EVALUATE",
        as_of=as_of,
        consecutive_days_observed=consecutive_days,
        required_consecutive_days=REQUIRED_CONSECUTIVE_DAYS,
        unconfirmed_fields=UNCONFIRMED_REQUIRED_FIELDS,
        notes=(
            "14-consecutive-day observation window satisfied, but "
            f"{len(UNCONFIRMED_REQUIRED_FIELDS)} of the 18 fields "
            "evaluate_expansion_gates() requires have no source this "
            "session could confirm against the actual governing plan "
            "text (STRATUS_Master_Implementation_Plan_2026-08-30_REV1.md, "
            "which does not exist anywhere in this repository). The "
            "existing 6-of-7 policy implementation "
            "(expansion_gates.OPPORTUNITY_QUALITY_GATES_REQUIRED) is "
            "completely untouched and unevaluated here -- this is not a "
            "failed gate, it is an unanswerable question given current "
            "evidence.",
        ),
    )
