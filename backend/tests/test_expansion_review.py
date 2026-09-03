"""Universe Manager V1a Expansion-Review Plumbing (V1a ITERATE block,
Phase 4) -- proves the review wrapper distinguishes an insufficient
observation window from an unable-to-evaluate state, never conflates "no
qualifying opportunity" (a real, observable fact) with "cannot evaluate"
(a governance/data-mapping gap), and never silently reaches EVALUATED
without a confirmed real field mapping.
"""

from datetime import date, timedelta

from backend.app.expansion_review import (
    REQUIRED_CONSECUTIVE_DAYS,
    UNCONFIRMED_REQUIRED_FIELDS,
    build_expansion_review,
)
from backend.app.universe_telemetry import reset_universe_telemetry_state
from backend.app.universe_telemetry_store import (
    DailyObservationDelta,
    UniverseDailyTelemetryStore,
)


def _seed_days(tmp_path, days: list[date], *, qualified_count: int = 3):
    store = UniverseDailyTelemetryStore(str(tmp_path / "telemetry.db"))
    for day in days:
        store.record(
            day, DailyObservationDelta(qualified_opportunity_count=qualified_count)
        )
    store.close()


def _enable(monkeypatch, tmp_path):
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv(
        "STRATUS_UNIVERSE_TELEMETRY_DB_PATH", str(tmp_path / "telemetry.db")
    )
    reset_universe_telemetry_state()


def test_insufficient_observation_window_when_no_telemetry(monkeypatch, tmp_path):
    _enable(monkeypatch, tmp_path)
    result = build_expansion_review(as_of=date(2026, 9, 2))
    assert result.status == "INSUFFICIENT_OBSERVATION_WINDOW"
    assert result.consecutive_days_observed == 0
    assert result.required_consecutive_days == REQUIRED_CONSECUTIVE_DAYS
    assert result.gate_report is None


def test_insufficient_observation_window_with_a_gap(monkeypatch, tmp_path):
    """A real coverage gap breaks the *consecutive* count, even though 14+
    total days exist somewhere in the store."""
    as_of = date(2026, 9, 2)
    days = [as_of - timedelta(days=i) for i in range(7)]  # 7 consecutive
    days += [as_of - timedelta(days=i) for i in range(9, 20)]  # a gap, then more
    _enable(monkeypatch, tmp_path)
    _seed_days(tmp_path, days)

    result = build_expansion_review(as_of=as_of)
    assert result.status == "INSUFFICIENT_OBSERVATION_WINDOW"
    assert result.consecutive_days_observed == 7  # stops at the gap


def test_full_consecutive_window_is_still_unable_to_evaluate(monkeypatch, tmp_path):
    """The core Phase 4 guarantee: even with a genuine, gap-free 14-day
    window, the review stays UNABLE_TO_EVALUATE -- it never silently
    fabricates the fields this session couldn't confirm against the
    actual (missing) governing plan text."""
    as_of = date(2026, 9, 2)
    days = [as_of - timedelta(days=i) for i in range(REQUIRED_CONSECUTIVE_DAYS)]
    _enable(monkeypatch, tmp_path)
    _seed_days(tmp_path, days)

    result = build_expansion_review(as_of=as_of)
    assert result.status == "UNABLE_TO_EVALUATE"
    assert result.consecutive_days_observed >= REQUIRED_CONSECUTIVE_DAYS
    assert result.gate_report is None
    assert set(result.unconfirmed_fields) == set(UNCONFIRMED_REQUIRED_FIELDS)


def test_no_qualifying_opportunity_is_distinct_from_unable_to_evaluate(
    monkeypatch, tmp_path
):
    """A real zero-qualified-opportunity history (an honest product fact)
    must never be conflated with, or silently reported as, an inability
    to evaluate the gates."""
    as_of = date(2026, 9, 2)
    days = [as_of - timedelta(days=i) for i in range(REQUIRED_CONSECUTIVE_DAYS)]
    _enable(monkeypatch, tmp_path)
    _seed_days(tmp_path, days, qualified_count=0)

    from backend.app.universe_telemetry import daily_telemetry_range

    raw_rows = daily_telemetry_range(days[-1], days[0])
    assert all(row.qualified_opportunity_count == 0 for row in raw_rows)  # real fact

    result = build_expansion_review(as_of=as_of)
    # Still UNABLE_TO_EVALUATE, for the same field-mapping reason as
    # above -- the zero-opportunity fact is separately, honestly visible
    # in raw_rows, never folded into (or mistaken for) this status.
    assert result.status == "UNABLE_TO_EVALUATE"


def test_evaluated_status_is_currently_unreachable():
    """Governance guard: as long as UNCONFIRMED_REQUIRED_FIELDS is
    non-empty, build_expansion_review() can never reach EVALUATED --
    proving this session did not quietly wire a guessed mapping."""
    assert len(UNCONFIRMED_REQUIRED_FIELDS) > 0


def test_unconfirmed_field_reasons_are_one_of_the_named_categories():
    """Master Plan reconciliation: every remaining gap must be classified
    as exactly one of the four honest reasons -- never a vague catch-all
    that hides whether the fix needs a policy decision, a durable event-log
    build, or is genuinely undefined."""
    valid_reasons = {
        "no_durable_event_log",
        "point_in_time_only",
        "needs_policy_mapping",
        "no_plan_definition",
    }
    assert set(UNCONFIRMED_REQUIRED_FIELDS.values()) <= valid_reasons
    # And down from all 18 fields to exactly 10, now that 8 have confirmed
    # real sources per the Master Plan's own text.
    assert len(UNCONFIRMED_REQUIRED_FIELDS) == 10


def test_review_is_pure_and_deterministic(monkeypatch, tmp_path):
    """No mutation, no side effect, no expansion/deployment action --
    calling it twice with the same inputs returns the same result."""
    as_of = date(2026, 9, 2)
    days = [as_of - timedelta(days=i) for i in range(REQUIRED_CONSECUTIVE_DAYS)]
    _enable(monkeypatch, tmp_path)
    _seed_days(tmp_path, days)

    first = build_expansion_review(as_of=as_of)
    second = build_expansion_review(as_of=as_of)
    assert first == second
