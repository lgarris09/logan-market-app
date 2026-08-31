"""Universe Manager V1a Block 21 -- V1a -> V1b expansion gates. Pure
evaluation logic only: given a metrics snapshot, decides whether every
hard operational gate passes and how many of the opportunity-quality gates
pass. Never auto-expands anything -- `recommend_expansion` is advisory
output for a human to act on, exactly like every other "propose, human
approves" decision in this codebase (ADR-008). Measurement of the real,
rolling 14-day metrics this function consumes is a separate,
future instrumentation task (durable telemetry aggregation) -- this module
is the decision function that would run once that data exists, not the
collector itself.

UNRESOLVED PLAN CONTRADICTION (flagged 2026-08-30, re-confirmed unresolved
2026-08-31 -- see this session's own conformance report, item 4): the
governing plan lists seven concrete opportunity-quality bullet points
(MIN_DISTINCT_SURFACED_THESES_14D through MIN_MEANINGFUL_REVISION_
CONTENT_RATE below) but separately states the expansion recommendation
requires "at least 5 of the applicable 6" of them passing. Seven items
were specified; "6" was named as the denominator. This is an internal
inconsistency in the plan text itself, not a gap this module's author is
positioned to resolve -- OPPORTUNITY_QUALITY_GATES_REQUIRED is set to 6
(all seven items implemented, six required to pass) as the closest
integer reading, but this is a stand-in pending the plan owner's explicit
resolution, not a ratified decision. Do not treat this constant as settled;
do not silently change it to a different number without that resolution
either -- flag it again rather than re-guessing.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

EXPANSION_GATE_POLICY_VERSION_V1 = "expansion-gates-v1"

MIN_WARMUP_DAYS = 14

# Hard operational gate thresholds -- see this module's own docstring for
# the "why" behind each (all directly reused from the product spec, not
# independently re-derived).
MAX_FMP_RATE_LIMIT_RESPONSES = 0
MAX_SCHEDULED_FETCH_FAILURE_RATE = 0.01
MAX_TIME_SENSITIVE_DELAY_P95_SECONDS = 5 * 60
MAX_TIME_SENSITIVE_DELAY_P99_SECONDS = 15 * 60
MAX_CRITICAL_FRESHNESS_P95_RATIO = 1.25
MAX_CRITICAL_FRESHNESS_P99_RATIO = 2.0
MAX_STALE_GRACE_READ_RATE = 0.02
MAX_USER_VISIBLE_STALE_BEYOND_GRACE = 0
MAX_PEAK_CALLS_PER_MINUTE = 220
MIN_COALESCING_SUCCESS_RATE = 0.99
MAX_UNEXPLAINED_UNIVERSE_CHANGES = 0

# Opportunity-quality gate thresholds.
MIN_DISTINCT_SURFACED_THESES_14D = 8
MAX_CONSECUTIVE_ZERO_QUALIFIED_DAYS = 4
MIN_TOP_FIVE_DIVERSITY_SURVIVAL_RATE = 0.90
MAX_SINGLE_ENTITY_IMPRESSION_SHARE = 0.30
MAX_SINGLE_SECTOR_IMPRESSION_SHARE = 0.40
MIN_COMPLETE_EVIDENCE_PAYLOAD_RATE = 0.95
MIN_MEANINGFUL_REVISION_CONTENT_RATE = 0.70

OPPORTUNITY_QUALITY_GATE_COUNT = 7
OPPORTUNITY_QUALITY_GATES_REQUIRED = 6


@dataclass(frozen=True)
class OperationalMetricsSnapshot:
    fmp_rate_limit_responses: int
    scheduled_fetch_failure_rate: float
    time_sensitive_delay_p95_seconds: float
    time_sensitive_delay_p99_seconds: float
    critical_freshness_p95_ratio: float
    critical_freshness_p99_ratio: float
    stale_grace_read_rate: float
    user_visible_stale_beyond_grace_count: int
    peak_calls_per_minute: int
    coalescing_success_rate: float
    unexplained_universe_changes: int


@dataclass(frozen=True)
class OpportunityQualityMetricsSnapshot:
    distinct_surfaced_theses_14d: int
    max_consecutive_zero_qualified_days: int
    top_five_diversity_survival_rate: float
    max_single_entity_impression_share: float
    max_single_sector_impression_share: float
    complete_evidence_payload_rate: float
    meaningful_revision_content_rate: float


@dataclass(frozen=True)
class GateCheckResult:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ExpansionGateReport:
    policy_version: str
    evaluated_at: datetime
    warmup_days_elapsed: int
    warmup_satisfied: bool
    operational_checks: list[GateCheckResult] = field(default_factory=list)
    opportunity_quality_checks: list[GateCheckResult] = field(default_factory=list)
    unresolved_integrity_incident: bool = False

    @property
    def all_operational_gates_pass(self) -> bool:
        return all(c.passed for c in self.operational_checks)

    @property
    def opportunity_quality_gates_passed_count(self) -> int:
        return sum(1 for c in self.opportunity_quality_checks if c.passed)

    @property
    def recommend_expansion(self) -> bool:
        return (
            self.warmup_satisfied
            and self.all_operational_gates_pass
            and self.opportunity_quality_gates_passed_count
            >= OPPORTUNITY_QUALITY_GATES_REQUIRED
            and not self.unresolved_integrity_incident
        )


def _check(name: str, passed: bool, detail: str) -> GateCheckResult:
    return GateCheckResult(name=name, passed=passed, detail=detail)


def _operational_checks(m: OperationalMetricsSnapshot) -> list[GateCheckResult]:
    return [
        _check(
            "fmp_rate_limit_responses",
            m.fmp_rate_limit_responses <= MAX_FMP_RATE_LIMIT_RESPONSES,
            f"{m.fmp_rate_limit_responses} (must be {MAX_FMP_RATE_LIMIT_RESPONSES})",
        ),
        _check(
            "scheduled_fetch_failure_rate",
            m.scheduled_fetch_failure_rate < MAX_SCHEDULED_FETCH_FAILURE_RATE,
            f"{m.scheduled_fetch_failure_rate:.4f} (must be < {MAX_SCHEDULED_FETCH_FAILURE_RATE})",
        ),
        _check(
            "time_sensitive_delay_p95",
            m.time_sensitive_delay_p95_seconds < MAX_TIME_SENSITIVE_DELAY_P95_SECONDS,
            f"{m.time_sensitive_delay_p95_seconds:.0f}s (must be < "
            f"{MAX_TIME_SENSITIVE_DELAY_P95_SECONDS}s)",
        ),
        _check(
            "time_sensitive_delay_p99",
            m.time_sensitive_delay_p99_seconds < MAX_TIME_SENSITIVE_DELAY_P99_SECONDS,
            f"{m.time_sensitive_delay_p99_seconds:.0f}s (must be < "
            f"{MAX_TIME_SENSITIVE_DELAY_P99_SECONDS}s)",
        ),
        _check(
            "critical_freshness_p95",
            m.critical_freshness_p95_ratio <= MAX_CRITICAL_FRESHNESS_P95_RATIO,
            f"{m.critical_freshness_p95_ratio:.2f}x (must be <= "
            f"{MAX_CRITICAL_FRESHNESS_P95_RATIO}x)",
        ),
        _check(
            "critical_freshness_p99",
            m.critical_freshness_p99_ratio <= MAX_CRITICAL_FRESHNESS_P99_RATIO,
            f"{m.critical_freshness_p99_ratio:.2f}x (must be <= "
            f"{MAX_CRITICAL_FRESHNESS_P99_RATIO}x)",
        ),
        _check(
            "stale_grace_read_rate",
            m.stale_grace_read_rate < MAX_STALE_GRACE_READ_RATE,
            f"{m.stale_grace_read_rate:.4f} (must be < {MAX_STALE_GRACE_READ_RATE})",
        ),
        _check(
            "user_visible_stale_beyond_grace",
            m.user_visible_stale_beyond_grace_count
            <= MAX_USER_VISIBLE_STALE_BEYOND_GRACE,
            f"{m.user_visible_stale_beyond_grace_count} (must be "
            f"{MAX_USER_VISIBLE_STALE_BEYOND_GRACE})",
        ),
        _check(
            "peak_calls_per_minute",
            m.peak_calls_per_minute <= MAX_PEAK_CALLS_PER_MINUTE,
            f"{m.peak_calls_per_minute} (must be <= {MAX_PEAK_CALLS_PER_MINUTE})",
        ),
        _check(
            "coalescing_success_rate",
            m.coalescing_success_rate > MIN_COALESCING_SUCCESS_RATE,
            f"{m.coalescing_success_rate:.4f} (must be > {MIN_COALESCING_SUCCESS_RATE})",
        ),
        _check(
            "unexplained_universe_changes",
            m.unexplained_universe_changes <= MAX_UNEXPLAINED_UNIVERSE_CHANGES,
            f"{m.unexplained_universe_changes} (must be "
            f"{MAX_UNEXPLAINED_UNIVERSE_CHANGES})",
        ),
    ]


def _opportunity_quality_checks(
    m: OpportunityQualityMetricsSnapshot,
) -> list[GateCheckResult]:
    return [
        _check(
            "distinct_surfaced_theses_14d",
            m.distinct_surfaced_theses_14d >= MIN_DISTINCT_SURFACED_THESES_14D,
            f"{m.distinct_surfaced_theses_14d} (must be >= "
            f"{MIN_DISTINCT_SURFACED_THESES_14D})",
        ),
        _check(
            "max_consecutive_zero_qualified_days",
            m.max_consecutive_zero_qualified_days
            <= MAX_CONSECUTIVE_ZERO_QUALIFIED_DAYS,
            f"{m.max_consecutive_zero_qualified_days} (must be <= "
            f"{MAX_CONSECUTIVE_ZERO_QUALIFIED_DAYS})",
        ),
        _check(
            "top_five_diversity_survival_rate",
            m.top_five_diversity_survival_rate >= MIN_TOP_FIVE_DIVERSITY_SURVIVAL_RATE,
            f"{m.top_five_diversity_survival_rate:.2f} (must be >= "
            f"{MIN_TOP_FIVE_DIVERSITY_SURVIVAL_RATE})",
        ),
        _check(
            "max_single_entity_impression_share",
            m.max_single_entity_impression_share <= MAX_SINGLE_ENTITY_IMPRESSION_SHARE,
            f"{m.max_single_entity_impression_share:.2f} (must be <= "
            f"{MAX_SINGLE_ENTITY_IMPRESSION_SHARE})",
        ),
        _check(
            "max_single_sector_impression_share",
            m.max_single_sector_impression_share <= MAX_SINGLE_SECTOR_IMPRESSION_SHARE,
            f"{m.max_single_sector_impression_share:.2f} (must be <= "
            f"{MAX_SINGLE_SECTOR_IMPRESSION_SHARE})",
        ),
        _check(
            "complete_evidence_payload_rate",
            m.complete_evidence_payload_rate >= MIN_COMPLETE_EVIDENCE_PAYLOAD_RATE,
            f"{m.complete_evidence_payload_rate:.2f} (must be >= "
            f"{MIN_COMPLETE_EVIDENCE_PAYLOAD_RATE})",
        ),
        _check(
            "meaningful_revision_content_rate",
            m.meaningful_revision_content_rate >= MIN_MEANINGFUL_REVISION_CONTENT_RATE,
            f"{m.meaningful_revision_content_rate:.2f} (must be >= "
            f"{MIN_MEANINGFUL_REVISION_CONTENT_RATE})",
        ),
    ]


def evaluate_expansion_gates(
    operational: OperationalMetricsSnapshot,
    opportunity_quality: OpportunityQualityMetricsSnapshot,
    *,
    warmup_days_elapsed: int,
    unresolved_integrity_incident: bool = False,
    now: Optional[datetime] = None,
) -> ExpansionGateReport:
    """`warmup_days_elapsed` must be measured from steady state (Block 21:
    "start the measurement clock only after V1a reaches steady state,
    initial warming is complete, and the scheduler has stabilized") -- this
    function does not itself know when that was, it only checks the count
    a caller supplies against `MIN_WARMUP_DAYS`.
    """
    now = now or datetime.now(timezone.utc)
    return ExpansionGateReport(
        policy_version=EXPANSION_GATE_POLICY_VERSION_V1,
        evaluated_at=now,
        warmup_days_elapsed=warmup_days_elapsed,
        warmup_satisfied=warmup_days_elapsed >= MIN_WARMUP_DAYS,
        operational_checks=_operational_checks(operational),
        opportunity_quality_checks=_opportunity_quality_checks(opportunity_quality),
        unresolved_integrity_incident=unresolved_integrity_incident,
    )
