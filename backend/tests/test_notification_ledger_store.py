"""STRATUS 3.6.12 -- Notification Candidate + Decision Ledger V1. Direct
store-level tests (idempotency, restart persistence, user isolation) --
no Orchestrator/pipeline involved. See
backend/tests/test_notification_ledger_integration.py for the full,
wired-through-the-real-pipeline tests.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from backend.app.notification_ledger_store import (
    NotificationLedgerStore,
    candidate_id_for,
)
from logan_core.contracts import EarnedNotificationInputs, LedgerDecision
from logan_core.opportunity_lifecycle import build_notification_candidate

NOW = datetime(2026, 9, 10, 0, 0, 0, tzinfo=timezone.utc)


def _inputs(event_id) -> EarnedNotificationInputs:
    return EarnedNotificationInputs(
        event_id=event_id,
        material_delta=None,
        evidence_credibility=0.5,
        personal_relevance_result=None,
        time_sensitivity=0.5,
        is_watched=False,
        computed_at=NOW,
    )


def _candidate(user_id="user-a", entity_id="NVDA", revision=1, event_id=None):
    event_id = event_id or uuid4()
    return build_notification_candidate(
        candidate_id=candidate_id_for(user_id, event_id, revision),
        event_id=event_id,
        user_id=user_id,
        entity_id=entity_id,
        ticker=entity_id,
        signal_family="earnings_signal",
        now=NOW,
        source_captured_at=NOW,
        is_watched=False,
        watch_route="none",
        communication_mode="analysis",
        personal_relevance=0.3,
        connection_strength=0.0,
        visibility="feed",
        interruption="digest",
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


def _decision(
    candidate, outcome="SUPPRESS", reason="insufficient_personal_relevance_or_urgency"
):
    from logan_core.opportunity_lifecycle import evaluate_shadow

    shadow = evaluate_shadow(
        is_notification_worthy=candidate.revision.is_notification_worthy,
        watch_route=candidate.watch.watch_route,
        domain_fatigued=candidate.prioritization.domain_fatigued,
        in_cooldown=candidate.prioritization.in_cooldown,
        earned_notification_inputs=candidate.earned_notification_inputs,
    )
    return LedgerDecision(
        decision_id=uuid4(),
        candidate_id=candidate.candidate_id,
        user_id=candidate.user_id,
        event_id=candidate.event_id,
        outcome=outcome,
        reason=reason,
        decided_at=NOW,
        shadow=shadow,
    )


@pytest.fixture
def store(tmp_path):
    s = NotificationLedgerStore(tmp_path / "ledger.db")
    yield s
    s.close()


def test_candidate_id_is_deterministic():
    event_id = uuid4()
    first = candidate_id_for("user-a", event_id, 1)
    second = candidate_id_for("user-a", event_id, 1)
    assert first == second


def test_candidate_id_differs_by_revision():
    event_id = uuid4()
    assert candidate_id_for("user-a", event_id, 1) != candidate_id_for(
        "user-a", event_id, 2
    )


def test_save_candidate_then_read_back(store):
    candidate = _candidate()
    store.save_candidate(candidate)
    rows = store.candidates_for_user("user-a")
    assert len(rows) == 1
    assert rows[0]["entity_id"] == "NVDA"
    assert rows[0]["thesis_revision"] == 1


def test_repolling_same_revision_replaces_not_duplicates(store):
    candidate = _candidate(revision=1, event_id=uuid4())
    store.save_candidate(candidate)
    store.save_candidate(candidate)  # identical re-poll
    rows = store.candidates_for_user("user-a")
    assert len(rows) == 1


def test_save_decision_first_time_returns_true_and_persists(store):
    candidate = _candidate()
    decision = _decision(candidate)
    wrote = store.save_decision(decision, thesis_revision=1)
    assert wrote is True
    rows = store.decisions_for_user("user-a")
    assert len(rows) == 1
    assert rows[0]["outcome"] == "SUPPRESS"


def test_identical_redecision_is_a_noop_not_a_duplicate(store):
    """The core idempotency-under-retry guarantee: re-evaluating the exact
    same (user, event, revision) with an unchanged (outcome, reason) must
    never create a second row."""
    candidate = _candidate()
    decision_a = _decision(candidate)
    decision_b = _decision(candidate)  # same outcome/reason, new decision_id
    assert store.save_decision(decision_a, thesis_revision=1) is True
    assert store.save_decision(decision_b, thesis_revision=1) is False
    rows = store.decisions_for_user("user-a")
    assert len(rows) == 1


def test_genuine_transition_creates_a_new_row(store):
    """A real state change (suppressed -> sent for the same revision, e.g.
    once a cooldown lifts) must be recorded as a new, legitimate row --
    idempotency must never hide a real transition."""
    candidate = _candidate()
    suppressed = _decision(candidate, outcome="SUPPRESS", reason="view_cooldown_active")
    sent = _decision(candidate, outcome="SEND", reason="new_material_revision")
    assert store.save_decision(suppressed, thesis_revision=1) is True
    assert store.save_decision(sent, thesis_revision=1) is True
    rows = store.decisions_for_user("user-a")
    assert len(rows) == 2
    assert [r["outcome"] for r in rows] == ["SUPPRESS", "SEND"]


def test_new_material_revision_is_a_distinct_key_not_deduped_against(store):
    """A later revision of the *same* entity/event must never be silently
    deduped against an earlier revision's decision -- distinct thesis
    revisions are always distinct ledger keys."""
    event_id = uuid4()
    candidate_r1 = _candidate(revision=1, event_id=event_id)
    candidate_r2 = _candidate(revision=2, event_id=event_id)
    decision_r1 = _decision(
        candidate_r1, outcome="SUPPRESS", reason="no_material_delta"
    )
    decision_r2 = _decision(
        candidate_r2, outcome="SEND", reason="new_material_revision"
    )
    assert store.save_decision(decision_r1, thesis_revision=1) is True
    assert store.save_decision(decision_r2, thesis_revision=2) is True
    rows = store.decisions_for_user("user-a")
    assert len(rows) == 2


def test_user_isolation(store):
    candidate_a = _candidate(user_id="user-a")
    candidate_b = _candidate(user_id="user-b")
    store.save_candidate(candidate_a)
    store.save_candidate(candidate_b)
    store.save_decision(_decision(candidate_a), thesis_revision=1)
    store.save_decision(_decision(candidate_b), thesis_revision=1)
    assert len(store.candidates_for_user("user-a")) == 1
    assert len(store.candidates_for_user("user-b")) == 1
    assert len(store.decisions_for_user("user-a")) == 1
    assert len(store.decisions_for_user("user-b")) == 1
    assert len(store.all_candidates()) == 2
    assert len(store.all_decisions()) == 2


def test_delete_user_removes_only_that_users_rows(store):
    candidate_a = _candidate(user_id="user-a")
    candidate_b = _candidate(user_id="user-b")
    store.save_candidate(candidate_a)
    store.save_candidate(candidate_b)
    store.save_decision(_decision(candidate_a), thesis_revision=1)
    store.save_decision(_decision(candidate_b), thesis_revision=1)
    store.delete_user("user-a")
    assert store.candidates_for_user("user-a") == []
    assert store.decisions_for_user("user-a") == []
    assert len(store.candidates_for_user("user-b")) == 1
    assert len(store.decisions_for_user("user-b")) == 1


def test_restart_persistence(tmp_path):
    """Durable across restart: reopening the same file finds every
    previously saved candidate/decision."""
    db_path = tmp_path / "ledger.db"
    candidate = _candidate()
    decision = _decision(candidate)

    first = NotificationLedgerStore(db_path)
    first.save_candidate(candidate)
    first.save_decision(decision, thesis_revision=1)
    first.close()

    second = NotificationLedgerStore(db_path)
    try:
        assert len(second.candidates_for_user("user-a")) == 1
        assert len(second.decisions_for_user("user-a")) == 1
    finally:
        second.close()


def test_payload_round_trips_the_full_pydantic_shape(store):
    """The JSON payload column must preserve every nested field (watch,
    prioritization, revision, evidence, earned_notification_inputs) -- not
    just the typed core columns used for aggregation."""
    import json

    candidate = _candidate()
    store.save_candidate(candidate)
    row = store.candidates_for_user("user-a")[0]
    payload = json.loads(row["payload"])
    assert payload["watch"]["watch_route"] == "none"
    assert payload["evidence"]["classification"] == "inference"
    assert "earned_notification_inputs" in payload
