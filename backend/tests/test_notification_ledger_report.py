"""STRATUS 3.6.12 -- Notification Candidate + Decision Ledger V1: developer
report + route tests."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.notification_ledger_report import (
    build_notification_ledger_report,
    format_notification_ledger_report,
)
from backend.app.notification_ledger_store import (
    NotificationLedgerStore,
    candidate_id_for,
)
from logan_core.contracts import EarnedNotificationInputs, LedgerDecision
from logan_core.opportunity_lifecycle import (
    build_notification_candidate,
    evaluate_shadow,
)

NOW = datetime(2026, 9, 10, 0, 0, 0, tzinfo=timezone.utc)


def _inputs(event_id):
    return EarnedNotificationInputs(
        event_id=event_id,
        material_delta=None,
        evidence_credibility=0.5,
        personal_relevance_result=None,
        time_sensitivity=0.5,
        is_watched=False,
        computed_at=NOW,
    )


def _seed(
    store,
    *,
    user_id,
    entity_id,
    revision,
    is_watched,
    watch_route,
    interruption,
    outcome,
    reason,
    permitted=True,
):
    event_id = uuid4()
    candidate = build_notification_candidate(
        candidate_id=candidate_id_for(user_id, event_id, revision),
        event_id=event_id,
        user_id=user_id,
        entity_id=entity_id,
        ticker=entity_id,
        signal_family="earnings_signal",
        now=NOW,
        source_captured_at=NOW,
        is_watched=is_watched,
        watch_route=watch_route,
        communication_mode="alert" if interruption == "alert" else "analysis",
        personal_relevance=0.3,
        connection_strength=0.0,
        visibility="feed",
        interruption=interruption,
        in_cooldown=False,
        domain_fatigued=False,
        thesis_revision=revision,
        is_notification_worthy=True,
        change_type="confidence_increased",
        knowledge=None,
        confidence_score=0.6,
        classification="inference",
        provider_degraded=False,
        freshness_state="FRESH",
        market_evidence=None,
        earned_notification_inputs=_inputs(event_id),
    )
    store.save_candidate(candidate)
    # Constructs LedgerDecision directly with the requested outcome/reason
    # -- determine_ledger_outcome's own derivation is already covered by
    # logan_core/tests/test_notification_ledger.py; this file is about
    # report aggregation over already-recorded decisions, not re-proving
    # the derivation itself.
    shadow = evaluate_shadow(
        is_notification_worthy=candidate.revision.is_notification_worthy,
        watch_route=candidate.watch.watch_route,
        domain_fatigued=candidate.prioritization.domain_fatigued,
        in_cooldown=candidate.prioritization.in_cooldown,
        earned_notification_inputs=candidate.earned_notification_inputs,
    )
    decision = LedgerDecision(
        decision_id=uuid4(),
        candidate_id=candidate.candidate_id,
        user_id=candidate.user_id,
        event_id=candidate.event_id,
        outcome=outcome,
        reason=reason,
        decided_at=NOW,
        shadow=shadow,
    )
    store.save_decision(decision, thesis_revision=revision)
    return candidate, decision


def test_report_aggregates_sends_and_suppressions(tmp_path):
    store = NotificationLedgerStore(tmp_path / "ledger.db")
    try:
        _seed(
            store,
            user_id="user-a",
            entity_id="NVDA",
            revision=1,
            is_watched=True,
            watch_route="personal",
            interruption="alert",
            outcome="SEND",
            reason="new_material_revision",
        )
        _seed(
            store,
            user_id="user-b",
            entity_id="AAPL",
            revision=1,
            is_watched=False,
            watch_route="none",
            interruption="digest",
            outcome="SUPPRESS",
            reason="insufficient_personal_relevance_or_urgency",
        )
        report = build_notification_ledger_report(store)
        assert report.total_candidates == 2
        assert report.sends == 1
        assert report.suppressions == 1
        assert report.suppression_reasons == {
            "insufficient_personal_relevance_or_urgency": 1
        }
        assert report.watch_candidates == 1
        assert report.non_watch_candidates == 1
        assert report.distinct_users_with_candidates == 2
        assert report.distinct_entities == 2

        text = format_notification_ledger_report(store)
        assert "Candidates evaluated: 2" in text
        assert "insufficient_personal_relevance_or_urgency: 1" in text
    finally:
        store.close()


def test_report_never_lists_per_user_rows():
    """Aggregate-only guarantee: the formatted report text must never
    contain a raw user_id, satisfying the 'no unsafe cross-user data'
    requirement -- only counts/breakdowns."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        store = NotificationLedgerStore(f"{tmp}/ledger.db")
        try:
            _seed(
                store,
                user_id="a-very-identifiable-user-id-12345",
                entity_id="NVDA",
                revision=1,
                is_watched=True,
                watch_route="personal",
                interruption="alert",
                outcome="SEND",
                reason="new_material_revision",
            )
            text = format_notification_ledger_report(store)
            assert "a-very-identifiable-user-id-12345" not in text
        finally:
            store.close()


def test_route_reports_inactive_when_ledger_not_constructed():
    from backend.app.logan_feed import reset_pipeline_state

    reset_pipeline_state()  # ensures no live-ticker/persistence state lingers
    client = TestClient(app)
    response = client.get("/v1/dev/notification-ledger")
    assert response.status_code == 200
    assert "inactive" in response.json()["report"].lower()
