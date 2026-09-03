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

Master Plan Reconciliation + V1a Final Proof-Readiness Closeout update: the
governing document (STRATUS_Master_Implementation_Plan_2026-08-30_REV1.md,
superseded by REV2's Section 21 execution-status updates and CR-2026-002)
was located outside this repository and has now been read in full, and a
durable per-event operational observation layer
(universe_operational_observations.py) now exists. Together these confirmed
real sources for 18 of the 18 fields evaluate_expansion_gates() requires --
UNCONFIRMED_REQUIRED_FIELDS is now empty (see below).

  fmp_rate_limit_responses, scheduled_fetch_failure_rate,
  time_sensitive_delay_p95/p99_seconds, critical_freshness_p95/p99_ratio,
  coalescing_success_rate, peak_calls_per_minute -- all now real and durable
  via universe_operational_observations.build_operational_gate_evidence()
  (peak_calls_per_minute added this closeout: a genuine per-call outbound
  timestamp table, keyed off logan_core's ProviderCallObserver hook at the
  one real network-call boundary in FmpResponseCache.get_or_fetch(), with a
  deterministic fixed-calendar-minute bucketing definition -- see
  historical_peak_calls_per_minute()).
  unexplained_universe_changes, distinct_surfaced_theses_14d,
  max_consecutive_zero_qualified_days, top_five_diversity_survival_rate,
  max_single_entity/sector_impression_share, stale_grace_read_rate,
  user_visible_stale_beyond_grace_count, complete_evidence_payload_rate --
  real via universe_telemetry.daily_telemetry_range()
  (complete_evidence_payload_rate added the prior closeout: a
  deterministic, approved definition over real surfaced theses -- see
  compute_thesis_evidence_completeness() and
  complete_evidence_payload_rate() in universe_telemetry.py).
  meaningful_revision_content_rate -- real via
  universe_telemetry.meaningful_revision_content_rate(), the last of the
  18 fields, closed out this session: a deterministic
  change_type -> Material Revision Rubric class mapping approved via
  Master Plan CR-2026-002 now covers all 15 real persisted
  OpportunityRevision.change_type values (14 mapped +
  new_opportunity excluded from the denominator) -- see
  REVISION_RUBRIC_CLASS_BY_CHANGE_TYPE in universe_telemetry.py.

Gate-policy resolution (Master Plan CR-2026-002, 2026-09-03): the prior
closeout treated the Master Plan's Section 4 "Opportunity-quality gates"
as the six explicit bullets it lists (distinct theses, no-opportunity-day
run length, diversity survival, entity share, sector share, evidence
completeness), stated as "At minimum" -- i.e. all six, not "N of 6" -- as
a planning-only interpretation that deliberately left
`expansion_gates.py`'s code untouched pending a governance entry.
CR-2026-002 now formally ratifies that reading: `expansion_gates.py`'s
`OpportunityQualityMetricsSnapshot` has exactly six fields,
`OPPORTUNITY_QUALITY_GATE_COUNT == OPPORTUNITY_QUALITY_GATES_REQUIRED ==
6`, and `meaningful_revision_content_rate` is evaluated as a separate
`MaterialRevisionMetricsSnapshot` / `material_revision_check` that is
reported but never folded into `recommend_expansion`'s six-gate pass/fail
result. `_CONFIRMED_OPPORTUNITY_QUALITY_FIELDS` below still lists
meaningful_revision_content_rate alongside the six gates -- it remains one
of the 18 fields this module tracks proof-readiness for, distinct from
the separate policy question (now resolved) of whether it counts as one
of "the" six opportunity-quality gates.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Literal, Optional

from .universe_operational_observations import build_operational_gate_evidence
from .universe_telemetry import (
    UnmappedRevisionChangeType,
    complete_evidence_payload_rate,
    daily_telemetry_range,
    meaningful_revision_content_rate,
)

REQUIRED_CONSECUTIVE_DAYS = 14
TOTAL_REQUIRED_FIELDS = 18

ExpansionReviewStatus = Literal[
    "INSUFFICIENT_OBSERVATION_WINDOW", "UNABLE_TO_EVALUATE", "EVALUATED"
]

# V1a Final Proof-Readiness Closeout (Master Plan CR-2026-002): empty.
# Every one of the 18 fields evaluate_expansion_gates() requires now has a
# confirmed, currently-wired real source -- meaningful_revision_content_rate
# was the last one, closed out via a deterministic change_type -> Material
# Revision Rubric class mapping (see universe_telemetry.py's
# REVISION_RUBRIC_CLASS_BY_CHANGE_TYPE). Left as a dict (not deleted) so a
# future field that genuinely can't be confirmed has an established place
# to be listed -- distinct from a field that has a real source but happens
# to have zero observations in a particular window (see
# check_proof_window_readiness()'s own per-window evidence check for that
# case).
UNCONFIRMED_REQUIRED_FIELDS: dict[str, str] = {}

# The 18 fields that DO have a confirmed real source -- used by
# check_proof_window_readiness() to fail closed per-window (a confirmed
# source with zero real observations in a specific window is not "ready"
# either).
_CONFIRMED_OPERATIONAL_FIELDS = (
    "fmp_rate_limit_responses",
    "scheduled_fetch_failure_rate",
    "time_sensitive_delay_p95_seconds",
    "time_sensitive_delay_p99_seconds",
    "critical_freshness_p95_ratio",
    "critical_freshness_p99_ratio",
    "coalescing_success_rate",
    "peak_calls_per_minute",
    "unexplained_universe_changes",
)
_CONFIRMED_OPPORTUNITY_QUALITY_FIELDS = (
    "distinct_surfaced_theses_14d",
    "max_consecutive_zero_qualified_days",
    "top_five_diversity_survival_rate",
    "max_single_entity_impression_share",
    "max_single_sector_impression_share",
    "stale_grace_read_rate",
    "user_visible_stale_beyond_grace_count",
    "complete_evidence_payload_rate",
    "meaningful_revision_content_rate",
)


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

    if UNCONFIRMED_REQUIRED_FIELDS:
        # A future field could become unconfirmed again (see
        # UNCONFIRMED_REQUIRED_FIELDS's own docstring) -- this branch stays
        # in place even though the dict is empty as of this closeout.
        return ExpansionReviewResult(
            status="UNABLE_TO_EVALUATE",
            as_of=as_of,
            consecutive_days_observed=consecutive_days,
            required_consecutive_days=REQUIRED_CONSECUTIVE_DAYS,
            unconfirmed_fields=dict(UNCONFIRMED_REQUIRED_FIELDS),
            notes=(
                "14-consecutive-day observation window satisfied, but "
                f"{len(UNCONFIRMED_REQUIRED_FIELDS)} of {TOTAL_REQUIRED_FIELDS} "
                "fields evaluate_expansion_gates() requires have no "
                "confirmed-real source yet (see unconfirmed_fields for "
                "exactly which and why). The existing gate-count policy "
                "(expansion_gates.OPPORTUNITY_QUALITY_GATES_REQUIRED) is "
                "completely untouched and unevaluated here -- this is not a "
                "failed gate, it is an unanswerable question given current "
                "evidence.",
            ),
        )

    # V1a Final Proof-Readiness Closeout: all 18 fields are now confirmed
    # (UNCONFIRMED_REQUIRED_FIELDS is empty), but this module still does
    # not assemble real evidence into OperationalMetricsSnapshot /
    # OpportunityQualityMetricsSnapshot / MaterialRevisionMetricsSnapshot
    # and call the existing evaluate_expansion_gates() with it -- that
    # live-evaluation wiring is a distinct, not-yet-implemented
    # integration task, explicitly out of this closeout's scope (see
    # Master Plan CR-2026-002, "no change to V1a scope ... sequencing").
    # Status therefore stays UNABLE_TO_EVALUATE (accurately -- this
    # function genuinely cannot evaluate the gates yet), never a
    # fabricated EVALUATED. Use check_proof_window_readiness() to answer
    # "is the 14-day clock startable" -- that question doesn't depend on
    # this wiring existing.
    return ExpansionReviewResult(
        status="UNABLE_TO_EVALUATE",
        as_of=as_of,
        consecutive_days_observed=consecutive_days,
        required_consecutive_days=REQUIRED_CONSECUTIVE_DAYS,
        unconfirmed_fields={},
        notes=(
            f"All {TOTAL_REQUIRED_FIELDS} of {TOTAL_REQUIRED_FIELDS} required "
            "fields now have confirmed-real sources (see "
            "check_proof_window_readiness() for the fail-closed wiring "
            "check), but this module does not yet assemble that real "
            "evidence into a live call to evaluate_expansion_gates() -- "
            "that integration is a separate, not-yet-implemented task. This "
            "status answers 'can the gates be evaluated right now,' not "
            "'is the 14-day clock startable' -- see "
            "check_proof_window_readiness() for that question.",
        ),
    )


@dataclass(frozen=True)
class ProofWindowReadiness:
    """Answers exactly one question, deterministically and fail-closed:
    if the 14-day proof window started right now, could every required
    operational and opportunity-quality gate be evaluated from real
    durable observations by the time Day 14 ends? `ready` is True only
    when every one of the 18 fields has a confirmed, currently-wired
    recording mechanism -- never because historical data already happens
    to exist (a mechanism that will keep recording for the next 14 days is
    what matters, not what's in the store today)."""

    ready: bool
    permanently_unconfirmed: dict  # field -> reason, from UNCONFIRMED_REQUIRED_FIELDS
    notes: tuple = field(default_factory=tuple)


def check_proof_window_readiness() -> ProofWindowReadiness:
    """Fail-closed by construction: `ready` can only be True when
    `UNCONFIRMED_REQUIRED_FIELDS` is empty. No proxy, point-in-time signal,
    or partial mapping is ever allowed to count as "ready" -- a field
    either has a confirmed, durably-recording real source, or it does not.
    Deliberately does not inspect whether historical data already exists
    (that is INSUFFICIENT_OBSERVATION_WINDOW's job in build_expansion_review()) --
    this answers "would the next 14 days of real operation actually produce
    everything needed," which is a fact about wiring, not about what has
    already been observed.
    """
    if UNCONFIRMED_REQUIRED_FIELDS:
        return ProofWindowReadiness(
            ready=False,
            permanently_unconfirmed=dict(UNCONFIRMED_REQUIRED_FIELDS),
            notes=(
                f"{len(UNCONFIRMED_REQUIRED_FIELDS)} of {TOTAL_REQUIRED_FIELDS} "
                "required fields have no confirmed, durably-recording real "
                "source at all -- starting the 14-day clock now would still "
                "leave these fields unanswerable on Day 14, regardless of how "
                "much other real evidence accumulates. See "
                "permanently_unconfirmed for exactly which fields and why.",
            ),
        )
    return ProofWindowReadiness(
        ready=True,
        permanently_unconfirmed={},
        notes=(
            f"Every one of the {TOTAL_REQUIRED_FIELDS} fields "
            "evaluate_expansion_gates() requires has a confirmed, "
            "currently-wired real recording mechanism.",
        ),
    )


def confirmed_field_count() -> int:
    """`PROOF_INPUTS_CONFIRMED_REAL` -- how many of the 18 required fields
    currently have a confirmed real source. Reported alongside
    READY_TO_START_14_DAY_WINDOW."""
    return TOTAL_REQUIRED_FIELDS - len(UNCONFIRMED_REQUIRED_FIELDS)


def real_time_window_evidence_gaps(start: datetime, end: datetime) -> dict:
    """A second, complementary fail-closed check: even for the 18
    confirmed fields, a specific [start, end] window can genuinely have
    zero real observations (e.g. persistence was only just enabled, or the
    scheduler hasn't run yet in that window). Returns the subset of
    confirmed fields with no real evidence in this exact window -- never
    silently treated as "0, therefore passing." Read-only; never mutates
    or triggers anything.
    """
    gaps: dict[str, str] = {}
    operational_evidence = build_operational_gate_evidence(start, end)
    # fmp_rate_limit_responses (a plain count, like unexplained_universe_
    # changes) is deliberately excluded from this dict -- 0 is always a
    # real, honest "no rate-limit faults occurred" answer, never
    # indistinguishable from "no evidence was collected" the way a None
    # percentile/rate/peak is.
    operational_values = {
        "scheduled_fetch_failure_rate": operational_evidence.scheduled_provider_failure_rate,
        "time_sensitive_delay_p95_seconds": operational_evidence.time_sensitive_delay_p95_seconds,
        "time_sensitive_delay_p99_seconds": operational_evidence.time_sensitive_delay_p99_seconds,
        "critical_freshness_p95_ratio": operational_evidence.critical_freshness_p95_ratio,
        "critical_freshness_p99_ratio": operational_evidence.critical_freshness_p99_ratio,
        "coalescing_success_rate": operational_evidence.coalescing_success_rate,
        "peak_calls_per_minute": operational_evidence.peak_calls_per_minute,
    }
    for field_name, value in operational_values.items():
        if value is None:
            gaps[field_name] = "no_real_observations_in_window"

    # meaningful_revision_content_rate is sourced from
    # OpportunityRevisionStore's own SQLite file, entirely independent of
    # the daily_telemetry_range() store the other opportunity-quality
    # fields below use -- computed unconditionally, never coupled to
    # whether daily_rows is empty (revision data can exist with zero daily
    # telemetry rows, or vice versa).
    _daily_quality_fields = tuple(
        f
        for f in _CONFIRMED_OPPORTUNITY_QUALITY_FIELDS
        if f != "meaningful_revision_content_rate"
    )
    daily_rows = daily_telemetry_range(start.date(), end.date())
    if not daily_rows:
        for field_name in _daily_quality_fields:
            gaps[field_name] = "no_real_observations_in_window"
    else:
        # complete_evidence_payload_rate is per-day (thesis_completeness_
        # by_event_id), unlike the other opportunity-quality fields which
        # are computed over the whole daily_rows range -- a day with real
        # telemetry but zero surfaced theses that day is a real gap for
        # this specific field even when daily_rows overall is non-empty.
        if all(complete_evidence_payload_rate(row) is None for row in daily_rows):
            gaps["complete_evidence_payload_rate"] = "no_real_observations_in_window"

    try:
        revision_rate = meaningful_revision_content_rate(start.date(), end.date())
    except UnmappedRevisionChangeType:
        # A real, reachable revision exists in this window whose
        # change_type has no approved rubric mapping -- a more severe,
        # distinct condition than "no evidence collected," never conflated
        # with it.
        gaps["meaningful_revision_content_rate"] = "unmapped_change_type_encountered"
    else:
        if revision_rate is None:
            gaps["meaningful_revision_content_rate"] = "no_real_observations_in_window"

    # unexplained_universe_changes is always computable (zero is a real,
    # honest answer when the membership ledger has no bad rows), so it
    # never appears here as a gap.
    return gaps
