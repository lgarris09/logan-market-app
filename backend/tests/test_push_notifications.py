"""Sprint 3.6.6F -- STRATUS Watch backend tests. Every dispatch test uses
httpx.MockTransport (no real network access, no real Expo push ever sent by
the normal suite) -- same pattern as logan_core's FmpEarningsProvider tests.

Deliberately a separate file from test_notifications.py, which covers the
pre-existing, unrelated in-app notification badge/review adapter layer --
keeping the two apart matches the product distinction between STRATUS
Watch's real push notifications and the existing in-app badge, which stays
untouched by this sprint.
"""

import json
from uuid import UUID

import httpx

from backend.app.logan_feed import get_alert_eligible_items
from backend.app.models import RegisterPushTokenRequest
from backend.app.notifications import (
    dispatch_eligible_notifications,
    register_token,
)


def _mock_client(handler=None):
    if handler is None:

        def handler(request):
            return httpx.Response(200, json={"data": []})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_register_token_stores_and_counts():
    result = register_token(
        RegisterPushTokenRequest(expo_push_token="ExponentPushToken[aaa]")
    )
    assert result.registered is True
    assert result.token_count == 1

    result2 = register_token(
        RegisterPushTokenRequest(expo_push_token="ExponentPushToken[bbb]")
    )
    assert result2.token_count == 2


def test_register_same_token_twice_does_not_double_count():
    register_token(RegisterPushTokenRequest(expo_push_token="ExponentPushToken[aaa]"))
    result = register_token(
        RegisterPushTokenRequest(expo_push_token="ExponentPushToken[aaa]")
    )
    assert result.token_count == 1


def test_no_dispatch_without_registered_tokens():
    assert len(get_alert_eligible_items()) > 0  # sanity: eligible items exist
    dispatched = dispatch_eligible_notifications(client=_mock_client())
    assert dispatched == 0


def test_dispatch_sends_to_registered_token_for_every_eligible_item():
    # Deliberately does not pre-fetch get_alert_eligible_items() as a
    # reference count -- that call is itself a pipeline poll, and a second
    # poll can legitimately see a different eligible set (e.g. stance
    # shifting new -> confirms lowers novelty/internal_rank_score once an
    # event has been observed once). Assert against what this single
    # dispatch call itself actually sent, not a separately-polled count.
    register_token(RegisterPushTokenRequest(expo_push_token="ExponentPushToken[aaa]"))

    captured = {}

    def handler(request):
        captured["body"] = request.content
        return httpx.Response(200, json={"data": []})

    dispatched = dispatch_eligible_notifications(client=_mock_client(handler))
    assert dispatched > 0
    assert captured.get("body")


def test_push_payload_contains_event_id_display_name_and_headline():
    register_token(RegisterPushTokenRequest(expo_push_token="ExponentPushToken[aaa]"))

    captured_json = {}

    def handler(request):
        captured_json["messages"] = json.loads(request.content)
        return httpx.Response(200, json={"data": []})

    dispatch_eligible_notifications(client=_mock_client(handler))

    messages = captured_json["messages"]
    assert messages
    nvda_message = next(m for m in messages if m["title"] == "NVIDIA")
    assert nvda_message["to"] == "ExponentPushToken[aaa]"
    assert nvda_message["sound"] == "default"
    assert nvda_message["body"]  # non-empty headline text
    UUID(nvda_message["data"]["event_id"])  # valid UUID, doesn't raise


def test_dispatch_fans_out_to_every_registered_token():
    register_token(RegisterPushTokenRequest(expo_push_token="ExponentPushToken[aaa]"))
    register_token(RegisterPushTokenRequest(expo_push_token="ExponentPushToken[bbb]"))

    captured_json = {}

    def handler(request):
        captured_json["messages"] = json.loads(request.content)
        return httpx.Response(200, json={"data": []})

    dispatched = dispatch_eligible_notifications(client=_mock_client(handler))
    assert dispatched > 0  # items dispatched, not messages sent
    assert len(captured_json["messages"]) == dispatched * 2  # fanned out to both tokens
    tokens_used = {m["to"] for m in captured_json["messages"]}
    assert tokens_used == {"ExponentPushToken[aaa]", "ExponentPushToken[bbb]"}


def test_repeated_dispatch_is_deduped_not_resent():
    register_token(RegisterPushTokenRequest(expo_push_token="ExponentPushToken[aaa]"))
    call_count = {"n": 0}

    def handler(request):
        call_count["n"] += 1
        return httpx.Response(200, json={"data": []})

    first = dispatch_eligible_notifications(client=_mock_client(handler))
    assert first > 0
    assert call_count["n"] == 1

    second = dispatch_eligible_notifications(client=_mock_client(handler))
    assert second == 0
    # No new HTTP call at all -- nothing eligible left to send.
    assert call_count["n"] == 1


def test_failed_dispatch_does_not_mark_items_as_sent():
    register_token(RegisterPushTokenRequest(expo_push_token="ExponentPushToken[aaa]"))

    def failing_handler(request):
        raise httpx.ConnectError("connection refused")

    failed = dispatch_eligible_notifications(client=_mock_client(failing_handler))
    assert failed == 0

    # Nothing was marked dispatched on the failed attempt -- a subsequent
    # successful call still finds eligible items to send, proving the
    # notification wasn't silently dropped by a transient failure (not
    # comparing exact counts against the failed attempt's poll, since each
    # poll can legitimately see a different eligible set -- see the
    # sibling test above).
    def ok_handler(request):
        return httpx.Response(200, json={"data": []})

    succeeded = dispatch_eligible_notifications(client=_mock_client(ok_handler))
    assert succeeded > 0


def test_register_route_via_test_client():
    from fastapi.testclient import TestClient

    from backend.app.main import app

    client = TestClient(app)
    response = client.post(
        "/v1/notifications/register",
        json={"expo_push_token": "ExponentPushToken[ccc]"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["registered"] is True
    assert payload["token_count"] == 1
