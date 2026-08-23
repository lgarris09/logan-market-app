"""Sprint 3.6.9 Block 1 -- durable STRATUS Watch state: registered push
tokens and dispatch/review dedup state survive a simulated backend restart
when STRATUS_PERSIST_MEMORY is enabled, and remain byte-for-byte in-memory
-only (the pre-Block-1 behavior) when it is not. Mirrors
test_memory_persistence.py's own pattern: STRATUS_STATE_DB_PATH points at an
isolated tmp_path file, never the real local database.
"""

from uuid import uuid4

import httpx

from backend.app.models import RegisterPushTokenRequest
from backend.app.notifications import (
    _get_store,
    dispatch_eligible_notifications,
    mark_pushed_notifications_reviewed,
    register_token,
    reset_notification_state,
)
from logan_core.contracts import LOCAL_FOUNDER_USER_ID


def _mock_client(handler=None):
    if handler is None:

        def handler(request):
            return httpx.Response(200, json={"data": []})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_disabled_by_default_no_store_constructed(monkeypatch):
    monkeypatch.delenv("STRATUS_PERSIST_MEMORY", raising=False)
    reset_notification_state()
    assert _get_store() is None


def test_enabled_mode_constructs_a_store(monkeypatch, tmp_path):
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv("STRATUS_STATE_DB_PATH", str(tmp_path / "state.db"))
    reset_notification_state()
    assert _get_store() is not None


def test_disabled_mode_token_does_not_survive_a_simulated_restart(monkeypatch):
    """Local dev / the default test posture must stay exactly as it was
    before this block: purely in-memory, reset on every restart."""
    monkeypatch.delenv("STRATUS_PERSIST_MEMORY", raising=False)
    reset_notification_state()

    register_token(
        LOCAL_FOUNDER_USER_ID,
        RegisterPushTokenRequest(expo_push_token="ExponentPushToken[before]"),
    )

    reset_notification_state()  # simulated restart

    result = register_token(
        LOCAL_FOUNDER_USER_ID,
        RegisterPushTokenRequest(expo_push_token="ExponentPushToken[after]"),
    )
    assert result.token_count == 1  # the pre-restart registration is gone


def test_enabled_mode_token_survives_a_simulated_restart(monkeypatch, tmp_path):
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv("STRATUS_STATE_DB_PATH", str(tmp_path / "state.db"))
    reset_notification_state()

    register_token(
        LOCAL_FOUNDER_USER_ID,
        RegisterPushTokenRequest(expo_push_token="ExponentPushToken[before]"),
    )

    reset_notification_state()  # simulated restart -- SQLite file untouched

    result = register_token(
        LOCAL_FOUNDER_USER_ID,
        RegisterPushTokenRequest(expo_push_token="ExponentPushToken[after]"),
    )
    assert result.token_count == 2  # the pre-restart registration survived


def test_enabled_mode_dispatch_dedup_survives_restart_no_duplicate_push(
    monkeypatch, tmp_path
):
    """The correctness-critical case: a redeploy immediately after a
    successful dispatch must never re-push the same event_id to the same
    user -- this is the exact scenario a fully in-memory dedup set cannot
    protect against across a backend restart."""
    from backend.app import notifications as notifications_module

    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv("STRATUS_STATE_DB_PATH", str(tmp_path / "state.db"))
    reset_notification_state()

    register_token(
        LOCAL_FOUNDER_USER_ID,
        RegisterPushTokenRequest(expo_push_token="ExponentPushToken[dedup]"),
    )

    fake_event_id = uuid4()

    class _FakeItem:
        event_id = fake_event_id
        display_name = "NVDA"
        ticker = "NVDA"

        class delivered_item:  # noqa: N801 -- mirrors the real FeedItem shape
            headline = "NVDA: earnings beat"
            what_happened = "NVDA: earnings beat (EPS 1.87 vs 1.76)"

    sent_payloads: list[list[dict]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        sent_payloads.append(json.loads(request.content))
        return httpx.Response(200, json={"data": []})

    monkeypatch.setattr(
        notifications_module,
        "get_alert_eligible_items",
        lambda user_id: [_FakeItem()],
    )

    dispatched = dispatch_eligible_notifications(_mock_client(handler))
    assert dispatched == 1
    assert len(sent_payloads) == 1

    # Simulated restart -- SQLite file untouched, in-process dicts dropped.
    reset_notification_state()

    dispatched_again = dispatch_eligible_notifications(_mock_client(handler))
    assert dispatched_again == 0  # already-dispatched event_id, correctly not re-sent
    assert len(sent_payloads) == 1  # no second push actually went out


def test_enabled_mode_reviewed_state_survives_restart(monkeypatch, tmp_path):
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv("STRATUS_STATE_DB_PATH", str(tmp_path / "state.db"))
    reset_notification_state()

    from backend.app.notifications import get_pending_push_event_ids

    event_id = uuid4()
    store = _get_store()
    assert store is not None
    store.save_dispatched(LOCAL_FOUNDER_USER_ID, [event_id])
    mark_pushed_notifications_reviewed(LOCAL_FOUNDER_USER_ID, [event_id])

    reset_notification_state()  # simulated restart -- SQLite file untouched

    # _get_store() re-hydrates both dispatched and reviewed state from disk
    # on first use after a restart -- no other setup needed.
    _get_store()
    assert event_id not in get_pending_push_event_ids(LOCAL_FOUNDER_USER_ID)
