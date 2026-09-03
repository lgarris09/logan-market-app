"""Universe Manager V1a Expansion-Review Plumbing (V1a ITERATE block,
Phase 4) -- proves the review wrapper distinguishes an insufficient
observation window from an unable-to-evaluate state, never conflates "no
qualifying opportunity" (a real, observable fact) with "cannot evaluate"
(a governance/data-mapping gap), and never silently reaches EVALUATED
without a confirmed real field mapping.
"""

from datetime import date, datetime, timedelta, timezone

from backend.app.expansion_review import (
    REQUIRED_CONSECUTIVE_DAYS,
    UNCONFIRMED_REQUIRED_FIELDS,
    build_expansion_review,
    check_proof_window_readiness,
    real_time_window_evidence_gaps,
)
from backend.app.universe_operational_observation_store import (
    ProviderCallObservation,
    UniverseOperationalObservationStore,
)
from backend.app.universe_operational_observations import (
    reset_operational_observation_state,
)
from backend.app.universe_telemetry import reset_universe_telemetry_state
from backend.app.universe_telemetry_store import (
    DailyObservationDelta,
    UniverseDailyTelemetryStore,
)


def _seed_days(tmp_path, days: list[date], *, qualified_count: int = 3):
    store = UniverseDailyTelemetryStore(str(tmp_path / "telemetry.db"))
    entities = {f"ENTITY_{i}": 1 for i in range(qualified_count)}
    for day in days:
        store.record(day, DailyObservationDelta(entity_impression_counts=entities))
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

    from backend.app.universe_telemetry import (
        daily_telemetry_range,
        distinct_qualified_entity_count,
    )

    raw_rows = daily_telemetry_range(days[-1], days[0])
    assert all(
        distinct_qualified_entity_count(row) == 0 for row in raw_rows
    )  # real fact

    result = build_expansion_review(as_of=as_of)
    # Still UNABLE_TO_EVALUATE, for the same field-mapping reason as
    # above -- the zero-opportunity fact is separately, honestly visible
    # in raw_rows, never folded into (or mistaken for) this status.
    assert result.status == "UNABLE_TO_EVALUATE"


def test_evaluated_status_is_still_unreachable_after_final_closeout(
    monkeypatch, tmp_path
):
    """V1a Final Proof-Readiness Closeout (CR-2026-002): all 18 fields are
    now confirmed (UNCONFIRMED_REQUIRED_FIELDS is empty), but
    build_expansion_review() still cannot reach EVALUATED for a different,
    honest reason -- this module does not yet assemble real evidence into
    a live evaluate_expansion_gates() call. Proves that closing out the
    field-confirmation gap did not silently fabricate that wiring too."""
    assert UNCONFIRMED_REQUIRED_FIELDS == {}

    as_of = date(2026, 9, 2)
    days = [as_of - timedelta(days=i) for i in range(REQUIRED_CONSECUTIVE_DAYS)]
    _enable(monkeypatch, tmp_path)
    _seed_days(tmp_path, days)

    result = build_expansion_review(as_of=as_of)
    assert result.status == "UNABLE_TO_EVALUATE"
    assert result.unconfirmed_fields == {}
    assert result.gate_report is None
    assert any("not yet" in note for note in result.notes)


def test_all_18_fields_confirmed_after_final_proof_readiness_closeout():
    """V1a Final Proof-Readiness Closeout (CR-2026-002): the last field,
    meaningful_revision_content_rate, now has a real, durable,
    deterministic implementation (a Chuck/Logan-approved Material Revision
    Rubric mapping covering all 15 real persisted change types). Down from
    all 18 fields (V1a ITERATE block) to 10 (Master Plan reconciliation) to
    3 (V1a Proof-Instrumentation Closeout) to 1 (prior closeout) to 0."""
    assert UNCONFIRMED_REQUIRED_FIELDS == {}


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


# --- V1a Proof-Instrumentation Closeout: proof-window readiness --------------


def test_proof_window_readiness_is_ready_after_final_closeout():
    """The key V1a Final Proof-Readiness Closeout deliverable: with all 18
    fields confirmed, READY_TO_START_14_DAY_WINDOW is YES."""
    result = check_proof_window_readiness()
    assert result.ready is True
    assert result.permanently_unconfirmed == {}


def test_proof_window_readiness_is_deterministic_and_pure():
    first = check_proof_window_readiness()
    second = check_proof_window_readiness()
    assert first == second


def test_real_time_window_evidence_gaps_reports_everything_missing_with_no_data(
    monkeypatch, tmp_path
):
    """Fail-closed: an empty window must report every confirmed field as a
    real gap, never silently treat zero observations as a passing 0/None."""
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv(
        "STRATUS_OPERATIONAL_OBSERVATION_DB_PATH", str(tmp_path / "obs.db")
    )
    monkeypatch.setenv(
        "STRATUS_UNIVERSE_TELEMETRY_DB_PATH", str(tmp_path / "telemetry.db")
    )
    monkeypatch.setenv("STRATUS_REVISIONS_DB_PATH", str(tmp_path / "revisions.db"))
    reset_operational_observation_state()
    reset_universe_telemetry_state()

    now = datetime.now(timezone.utc)
    gaps = real_time_window_evidence_gaps(now - timedelta(days=1), now)

    assert gaps["time_sensitive_delay_p95_seconds"] == "no_real_observations_in_window"
    assert gaps["distinct_surfaced_theses_14d"] == "no_real_observations_in_window"
    assert gaps["peak_calls_per_minute"] == "no_real_observations_in_window"
    assert gaps["complete_evidence_payload_rate"] == "no_real_observations_in_window"
    assert gaps["meaningful_revision_content_rate"] == "no_real_observations_in_window"
    # Plain counts (0 is a real, honest answer -- "no faults occurred" /
    # "no bad ledger rows exist" -- not "no evidence was collected") are
    # never treated as gaps, mirroring unexplained_universe_changes' own
    # documented posture.
    assert "fmp_rate_limit_responses" not in gaps
    assert "unexplained_universe_changes" not in gaps


def test_real_time_window_evidence_gaps_shrinks_with_real_operational_data(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv(
        "STRATUS_OPERATIONAL_OBSERVATION_DB_PATH", str(tmp_path / "obs.db")
    )
    monkeypatch.setenv(
        "STRATUS_UNIVERSE_TELEMETRY_DB_PATH", str(tmp_path / "telemetry.db")
    )
    monkeypatch.setenv("STRATUS_REVISIONS_DB_PATH", str(tmp_path / "revisions.db"))
    reset_operational_observation_state()
    reset_universe_telemetry_state()

    now = datetime.now(timezone.utc)
    store = UniverseOperationalObservationStore(str(tmp_path / "obs.db"))
    store.record_provider_call(
        ProviderCallObservation(
            occurred_at=now,
            source="scheduler",
            endpoint="quote",
            real_calls=10,
            failures=1,
            rate_limited=0,
        )
    )
    store.close()

    gaps = real_time_window_evidence_gaps(
        now - timedelta(minutes=1), now + timedelta(minutes=1)
    )
    assert "scheduled_fetch_failure_rate" not in gaps
    # Still a real gap -- no wait samples or freshness ratios were recorded.
    assert "time_sensitive_delay_p95_seconds" in gaps


def test_peak_calls_per_minute_gap_shrinks_with_a_real_recorded_call(
    monkeypatch, tmp_path
):
    from backend.app.universe_operational_observation_store import (
        ProviderCallTimestamp,
    )

    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv(
        "STRATUS_OPERATIONAL_OBSERVATION_DB_PATH", str(tmp_path / "obs.db")
    )
    monkeypatch.setenv(
        "STRATUS_UNIVERSE_TELEMETRY_DB_PATH", str(tmp_path / "telemetry.db")
    )
    monkeypatch.setenv("STRATUS_REVISIONS_DB_PATH", str(tmp_path / "revisions.db"))
    reset_operational_observation_state()
    reset_universe_telemetry_state()

    now = datetime.now(timezone.utc)
    store = UniverseOperationalObservationStore(str(tmp_path / "obs.db"))
    store.record_provider_call_timestamp(
        ProviderCallTimestamp(occurred_at=now, provider="fmp", endpoint="quote")
    )
    store.close()

    gaps = real_time_window_evidence_gaps(
        now - timedelta(minutes=1), now + timedelta(minutes=1)
    )
    assert "peak_calls_per_minute" not in gaps


def test_complete_evidence_payload_rate_gap_shrinks_with_real_thesis_data(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv(
        "STRATUS_OPERATIONAL_OBSERVATION_DB_PATH", str(tmp_path / "obs.db")
    )
    monkeypatch.setenv(
        "STRATUS_UNIVERSE_TELEMETRY_DB_PATH", str(tmp_path / "telemetry.db")
    )
    monkeypatch.setenv("STRATUS_REVISIONS_DB_PATH", str(tmp_path / "revisions.db"))
    reset_operational_observation_state()
    reset_universe_telemetry_state()

    today = date.today()
    store = UniverseDailyTelemetryStore(str(tmp_path / "telemetry.db"))
    store.record(
        today,
        DailyObservationDelta(thesis_completeness_by_event_id={"EVT-1": True}),
    )
    store.close()

    now = datetime.now(timezone.utc)
    gaps = real_time_window_evidence_gaps(now - timedelta(days=1), now)
    assert "complete_evidence_payload_rate" not in gaps


def test_meaningful_revision_content_rate_gap_shrinks_with_real_revision_data(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv(
        "STRATUS_OPERATIONAL_OBSERVATION_DB_PATH", str(tmp_path / "obs.db")
    )
    monkeypatch.setenv(
        "STRATUS_UNIVERSE_TELEMETRY_DB_PATH", str(tmp_path / "telemetry.db")
    )
    monkeypatch.setenv("STRATUS_REVISIONS_DB_PATH", str(tmp_path / "revisions.db"))
    reset_operational_observation_state()
    reset_universe_telemetry_state()

    from backend.app.revision_store import OpportunityRevisionStore
    from logan_core.contracts import OpportunityRevision

    today = datetime.now(timezone.utc)
    store = OpportunityRevisionStore(str(tmp_path / "revisions.db"))
    store.append(
        OpportunityRevision(
            entity_id="SYMBOL:AAPL",
            revision=1,
            lifecycle_state="developing",
            confidence_score=0.8,
            trigger_codes=["STOCK_PRICE_MOVE_SIGNIFICANT"],
            change_type="confidence_increased",
            reason="Confidence strengthened.",
            created_at=today,
        )
    )
    store.close()

    gaps = real_time_window_evidence_gaps(today - timedelta(days=1), today)
    assert "meaningful_revision_content_rate" not in gaps


def test_meaningful_revision_content_rate_gap_is_distinct_for_unmapped_type(
    monkeypatch, tmp_path
):
    """An unmapped change_type in the window is a more severe condition
    than 'no evidence collected' -- never conflated with it."""
    import sqlite3

    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv(
        "STRATUS_OPERATIONAL_OBSERVATION_DB_PATH", str(tmp_path / "obs.db")
    )
    monkeypatch.setenv(
        "STRATUS_UNIVERSE_TELEMETRY_DB_PATH", str(tmp_path / "telemetry.db")
    )
    revisions_path = tmp_path / "revisions.db"
    monkeypatch.setenv("STRATUS_REVISIONS_DB_PATH", str(revisions_path))
    reset_operational_observation_state()
    reset_universe_telemetry_state()

    from backend.app.revision_store import OpportunityRevisionStore

    OpportunityRevisionStore(str(revisions_path)).close()  # create schema
    today = datetime.now(timezone.utc)
    conn = sqlite3.connect(str(revisions_path))
    conn.execute(
        "INSERT INTO opportunity_revisions (entity_id, revision, "
        "lifecycle_state, confidence_score, trigger_codes, change_type, "
        "reason, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "SYMBOL:AAPL",
            1,
            "developing",
            0.8,
            "[]",
            "some_future_change_type",
            "test",
            today.isoformat(),
        ),
    )
    conn.commit()
    conn.close()

    gaps = real_time_window_evidence_gaps(today - timedelta(days=1), today)
    assert (
        gaps["meaningful_revision_content_rate"] == "unmapped_change_type_encountered"
    )
