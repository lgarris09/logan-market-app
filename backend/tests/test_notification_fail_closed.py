"""ADR-080 / ADR-081 -- notifications fail closed, can be paused, and never
claim more about delivery than the push provider's response established.
"""

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
import pytest

from backend.app.logan_feed import get_alert_eligible_items
from backend.app.models import RegisterPushTokenRequest
from backend.app.notification_ledger_store import (
    DELIVERY_STATE_UNKNOWN,
    DISPATCH_STATES,
    NotificationLedgerStore,
)
from backend.app.notifications import (
    classify_dispatch_response,
    dispatch_eligible_notifications,
    get_pending_push_event_ids,
    register_token,
)
from logan_core.contracts import LOCAL_FOUNDER_USER_ID
from logan_core.opportunity_lifecycle import decide_notification
from logan_core.opportunity_lifecycle.sync import UserOpportunityKnowledge

NOW = datetime(2026, 10, 5, 21, 0, tzinfo=timezone.utc)


def _decide(**overrides):
    kwargs = dict(
        entity_id="NVDA",
        user_id="u1",
        current_revision=3,
        is_notification_worthy=True,
        change_type="confidence_increased",
        knowledge=None,
        provider_degraded=False,
        now=NOW,
    )
    kwargs.update(overrides)
    return decide_notification(**kwargs)


# --- decision: uncertainty never becomes SEND ----------------------------------


def test_baseline_material_revision_sends():
    decision = _decide(freshness_state="FRESH")
    assert decision.should_notify is True
    assert decision.reason == "new_material_revision"


@pytest.mark.parametrize("state", ["FRESH", "RECENTLY_OBSERVED"])
def test_established_freshness_allows_interruption(state):
    assert _decide(freshness_state=state).should_notify is True


@pytest.mark.parametrize("state", [None, "UNAVAILABLE", "", "SOMETHING_NEW"])
def test_unestablished_freshness_suppresses(state):
    decision = _decide(freshness_state=state)
    assert decision.should_notify is False
    assert decision.reason == "freshness_unestablished_suppressed"


def test_known_stale_evidence_suppresses_under_its_own_reason():
    decision = _decide(freshness_state="STALE_WITHIN_GRACE")
    assert decision.should_notify is False
    assert decision.reason == "stale_evidence_suppressed"


def test_provider_degraded_suppresses():
    decision = _decide(provider_degraded=True, freshness_state="FRESH")
    assert decision.should_notify is False
    assert decision.reason == "provider_degraded_suppressed"


def test_missing_revision_suppresses():
    decision = _decide(current_revision=None, freshness_state="FRESH")
    assert decision.should_notify is False
    assert decision.reason == "no_material_delta"


def test_pause_suppresses_everything_and_is_the_recorded_reason():
    for extra in (
        {},
        {"provider_degraded": True},
        {"freshness_state": None},
        {"is_notification_worthy": False},
    ):
        decision = _decide(notifications_paused=True, **extra)
        assert decision.should_notify is False
        assert decision.reason == "beta_notifications_paused"


def test_duplicate_suppression_stays_deterministic():
    knowledge = UserOpportunityKnowledge(
        user_id="u1",
        entity_id="NVDA",
        last_notified_revision=3,
        last_notified_at=NOW - timedelta(hours=5),
        last_notified_change_type="confidence_increased",
        updated_at=NOW,
    )
    first = _decide(knowledge=knowledge, freshness_state="FRESH")
    second = _decide(knowledge=knowledge, freshness_state="FRESH")
    assert first.reason == second.reason == "same_revision_suppressed"
    assert first.should_notify is False


def test_unpausing_does_not_release_a_backlog():
    """A revision suppressed while paused is only notification-worthy on
    the poll that produced it. On the next poll the same revision carries
    no new delta, so nothing is sent when the pause is lifted."""
    paused = _decide(notifications_paused=True, freshness_state="FRESH")
    assert paused.reason == "beta_notifications_paused"
    later = _decide(is_notification_worthy=False, freshness_state="FRESH")
    assert later.should_notify is False
    assert later.reason == "no_material_delta"


# --- dispatch states -----------------------------------------------------------


def _response(status, body=None):
    if body is None:
        return httpx.Response(status, text="x")
    return httpx.Response(status, json=body)


def test_non_2xx_is_failed():
    outcomes = classify_dispatch_response(_response(500), 2, 1)
    assert [o[0] for o in outcomes] == ["dispatch_failed", "dispatch_failed"]


def test_2xx_without_tickets_is_attempted_not_accepted():
    for body in ({"data": []}, {}, {"data": "nope"}, None):
        outcomes = classify_dispatch_response(_response(200, body), 2, 1)
        assert [o[0] for o in outcomes] == ["dispatch_attempted"] * 2


def test_tickets_are_read_per_item_across_tokens():
    body = {
        "data": [
            {"status": "ok", "id": "a"},
            {"status": "error", "details": {"error": "DeviceNotRegistered"}},
            {"status": "error", "details": {"error": "DeviceNotRegistered"}},
            {"status": "error", "details": {"error": "MessageRateExceeded"}},
        ]
    }
    outcomes = classify_dispatch_response(_response(200, body), 2, 2)
    assert outcomes[0][:3] == ("dispatch_accepted", 1, 1)
    assert outcomes[1][:3] == ("dispatch_rejected", 0, 2)
    assert outcomes[1][3] == "DeviceNotRegistered,MessageRateExceeded"


def test_every_classified_state_is_in_the_bounded_model():
    bodies = [
        (500, None),
        (200, {"data": []}),
        (200, {"data": [{"status": "ok"}]}),
        (200, {"data": [{"status": "error"}]}),
        (200, {"data": [{"status": "weird"}]}),
    ]
    for status, body in bodies:
        for outcome in classify_dispatch_response(_response(status, body), 1, 1):
            assert outcome[0] in DISPATCH_STATES


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def _register():
    register_token(
        LOCAL_FOUNDER_USER_ID,
        RegisterPushTokenRequest(expo_push_token="ExponentPushToken[aaa]"),
    )


def test_pause_sends_nothing_and_marks_nothing(monkeypatch):
    _register()
    assert get_alert_eligible_items(LOCAL_FOUNDER_USER_ID)
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"data": []})

    monkeypatch.setenv("STRATUS_NOTIFICATIONS_PAUSED", "1")
    assert dispatch_eligible_notifications(client=_client(handler)) == 0
    assert calls == []
    assert get_pending_push_event_ids(LOCAL_FOUNDER_USER_ID) == set()

    # Reversible without touching any state: clearing the flag restores sends.
    monkeypatch.delenv("STRATUS_NOTIFICATIONS_PAUSED")
    assert dispatch_eligible_notifications(client=_client(handler)) > 0
    assert calls


def test_http_error_response_is_not_recorded_as_sent():
    _register()

    def handler(request):
        return httpx.Response(503, text="unavailable")

    assert dispatch_eligible_notifications(client=_client(handler)) == 0
    assert get_pending_push_event_ids(LOCAL_FOUNDER_USER_ID) == set()

    # ...and it is retried on the next poll.
    def ok(request):
        return httpx.Response(200, json={"data": []})

    assert dispatch_eligible_notifications(client=_client(ok)) > 0


def test_rejected_by_every_token_is_not_counted_as_dispatched():
    _register()

    def handler(request):
        messages = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "data": [
                    {"status": "error", "details": {"error": "DeviceNotRegistered"}}
                    for _ in messages
                ]
            },
        )

    assert dispatch_eligible_notifications(client=_client(handler)) == 0


# --- ledger store: dispatch rows and retention ---------------------------------


def test_dispatch_rows_never_claim_delivery(tmp_path):
    store = NotificationLedgerStore(tmp_path / "ledger.db")
    for state in sorted(DISPATCH_STATES):
        store.record_dispatch(
            user_id="u1",
            event_id=uuid4(),
            entity_id="NVDA",
            thesis_revision=2,
            state=state,
            accepted_count=1 if state == "dispatch_accepted" else 0,
            rejected_count=0,
            detail=None,
            attempted_at=NOW,
        )
    rows = store.all_dispatches()
    assert {r["state"] for r in rows} == DISPATCH_STATES
    assert {r["delivery_state"] for r in rows} == {DELIVERY_STATE_UNKNOWN}
    store.close()


def test_unknown_dispatch_state_is_refused(tmp_path):
    store = NotificationLedgerStore(tmp_path / "ledger.db")
    with pytest.raises(ValueError):
        store.record_dispatch(
            user_id="u1",
            event_id=uuid4(),
            entity_id="NVDA",
            thesis_revision=1,
            state="delivered",
            accepted_count=1,
            rejected_count=0,
            detail=None,
            attempted_at=NOW,
        )
    store.close()


def test_retention_purges_old_rows_and_keeps_recent_ones(tmp_path):
    store = NotificationLedgerStore(tmp_path / "ledger.db")
    for age_days in (200, 10):
        store.record_dispatch(
            user_id="u1",
            event_id=uuid4(),
            entity_id="NVDA",
            thesis_revision=1,
            state="dispatch_accepted",
            accepted_count=1,
            rejected_count=0,
            detail=None,
            attempted_at=NOW - timedelta(days=age_days),
        )
    store.maybe_purge(NOW, 120)
    assert len(store.all_dispatches()) == 1
    # At most once a day per process: a second call inside the day is a no-op.
    store.record_dispatch(
        user_id="u1",
        event_id=uuid4(),
        entity_id="NVDA",
        thesis_revision=1,
        state="dispatch_accepted",
        accepted_count=1,
        rejected_count=0,
        detail=None,
        attempted_at=NOW - timedelta(days=300),
    )
    store.maybe_purge(NOW + timedelta(hours=1), 120)
    assert len(store.all_dispatches()) == 2
    store.maybe_purge(NOW + timedelta(days=1, minutes=1), 120)
    assert len(store.all_dispatches()) == 1
    store.close()


def test_account_deletion_removes_dispatch_rows(tmp_path):
    store = NotificationLedgerStore(tmp_path / "ledger.db")
    for user in ("u1", "u2"):
        store.record_dispatch(
            user_id=user,
            event_id=uuid4(),
            entity_id="NVDA",
            thesis_revision=1,
            state="dispatch_attempted",
            accepted_count=0,
            rejected_count=0,
            detail=None,
            attempted_at=NOW,
        )
    store.delete_user("u1")
    assert [r["user_id"] for r in store.all_dispatches()] == ["u2"]
    store.close()
