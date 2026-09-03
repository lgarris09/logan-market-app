"""Universe Manager V1a Expansion-Review Plumbing -- an advisory, read-only
orchestration layer over the existing, unmodified
`logan_core.universe.expansion_gates.evaluate_expansion_gates()` decision
function. This module never scores, ranks, expands, or deploys anything --
it only decides whether there is currently enough confirmed real evidence
to call the existing gate function at all, and if not, says exactly why,
distinguishing three different honest states a caller must never conflate:

  INSUFFICIENT_OBSERVATION_WINDOW -- fewer than 14 consecutive real
      calendar days of telemetry exist yet (see universe_telemetry.py).
      Not a judgment about quality -- just "too early to ask the
      question."
  UNABLE_TO_EVALUATE -- the 14-day window exists, but one or more of the
      18 fields evaluate_expansion_gates() requires still has no source
      this session could confirm against the governing Master Plan text
      (see below) -- calling the gate function with a guessed value for
      any of them would be exactly the "invent a substitute definition"
      this work is told not to do. Distinct from "the gate failed": this
      status means the question literally cannot be answered yet, not
      that the answer is no.
  EVALUATED -- every required field has a confirmed-real source; the
      existing, completely unmodified evaluate_expansion_gates() is called
      and its real result (including the unresolved gate-count question
      below) is returned as-is.

Master Plan Reconciliation update: the governing document
(STRATUS_Master_Implementation_Plan_2026-08-30_REV1.md) was located
outside this repository and has now been read in full. Its exact text
confirmed real formulas for several previously-unconfirmed fields
(distinct_surfaced_theses_14d, max_consecutive_zero_qualified_days,
top_five_diversity_survival_rate, max_single_entity/sector_impression_share,
stale_grace_read_rate, user_visible_stale_beyond_grace_count) -- all now
wired in universe_telemetry.py and removed from `UNCONFIRMED_REQUIRED_FIELDS`.
Ten fields remain unconfirmed, each for a specific, named reason (see the
dict below) -- none guessed at.

Separately, and NOT resolved by this module: `expansion_gates.py`'s
`OPPORTUNITY_QUALITY_GATE_COUNT = 7` / `OPPORTUNITY_QUALITY_GATES_REQUIRED
= 6` does not match the Master Plan's own text. Section 4's "Opportunity-
quality gates" lists exactly SIX explicit bullet criteria (distinct
theses, no-opportunity-day run length, diversity survival, entity share,
sector share, evidence completeness) as "At minimum" -- i.e. all six,
not "N of 6". The current code's seventh gate (meaningful_revision_content_rate)
is drawn from a *separate* plan subsection (the Material Revision Rubric's
own ">=70%" target), not from the six-item "Opportunity-quality gates"
list itself. The phrase "5 of the applicable 6" that the existing code's
own docstring attributes to "the governing plan" does not appear anywhere
in REV1, REV2, the original 2026-08-30 plan, or the 2026-08-31 execution-
status copy (all four checked). This module does not change
expansion_gates.py's constants or logic in any way -- see this session's
own Master Plan Reconciliation report for the full finding and the
smallest-reconciliation proposal, left for Chuck/Logan to decide.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal, Optional

from .universe_telemetry import daily_telemetry_range

REQUIRED_CONSECUTIVE_DAYS = 14

ExpansionReviewStatus = Literal[
    "INSUFFICIENT_OBSERVATION_WINDOW", "UNABLE_TO_EVALUATE", "EVALUATED"
]

# The 10 (of 18) evaluate_expansion_gates() fields this session still could
# not confirm a real-data source for, each keyed to the specific reason --
# never a flat "blocked," since the three reasons need different next
# steps (Chuck/Logan policy input vs. a durable event-log build vs.
# accepting a point-in-time proxy's known limitation).
#   "no_durable_event_log": would require a new per-event latency/ratio
#       history this codebase does not have -- a materially new
#       persistence subsystem, flagged for review rather than built.
#   "point_in_time_only": a real signal exists and is wired
#       (universe_telemetry.collect_real_operational_signals()), but it is
#       process-lifetime/instantaneous, never a genuine durable 14-day
#       rolling measure -- using it as-is would understate real risk after
#       any restart.
#   "needs_policy_mapping": the Master Plan states an exact target but the
#       classification/mapping needed to compute it deterministically from
#       existing data has not been confirmed by Chuck/Logan.
#   "no_plan_definition": neither this codebase nor the Master Plan gives
#       an exact, checkable definition -- computing it would mean
#       inventing one.
UNCONFIRMED_REQUIRED_FIELDS: dict[str, str] = {
    "fmp_rate_limit_responses": "point_in_time_only",
    "scheduled_fetch_failure_rate": "point_in_time_only",
    "time_sensitive_delay_p95_seconds": "no_durable_event_log",
    "time_sensitive_delay_p99_seconds": "no_durable_event_log",
    "critical_freshness_p95_ratio": "no_durable_event_log",
    "critical_freshness_p99_ratio": "no_durable_event_log",
    "peak_calls_per_minute": "point_in_time_only",
    "coalescing_success_rate": "no_durable_event_log",
    "complete_evidence_payload_rate": "no_plan_definition",
    "meaningful_revision_content_rate": "needs_policy_mapping",
}


@dataclass(frozen=True)
class ExpansionReviewResult:
    status: ExpansionReviewStatus
    as_of: date
    consecutive_days_observed: int
    required_consecutive_days: int
    unconfirmed_fields: dict = field(default_factory=dict)
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

    # The window requirement is satisfied, but 10 of the 18 fields
    # evaluate_expansion_gates() requires still have no confirmed-real
    # source -- see UNCONFIRMED_REQUIRED_FIELDS for exactly which, and why.
    return ExpansionReviewResult(
        status="UNABLE_TO_EVALUATE",
        as_of=as_of,
        consecutive_days_observed=consecutive_days,
        required_consecutive_days=REQUIRED_CONSECUTIVE_DAYS,
        unconfirmed_fields=dict(UNCONFIRMED_REQUIRED_FIELDS),
        notes=(
            "14-consecutive-day observation window satisfied, but "
            f"{len(UNCONFIRMED_REQUIRED_FIELDS)} of 18 fields "
            "evaluate_expansion_gates() requires have no confirmed-real "
            "source yet (see unconfirmed_fields for exactly which and "
            "why). The existing gate-count policy "
            "(expansion_gates.OPPORTUNITY_QUALITY_GATES_REQUIRED) is "
            "completely untouched and unevaluated here -- this is not a "
            "failed gate, it is an unanswerable question given current "
            "evidence.",
        ),
    )
