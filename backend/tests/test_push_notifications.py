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

from backend.app.logan_feed import (
    _run_feed_pipeline,
    get_alert_eligible_items,
    mark_notifications_reviewed,
)
from backend.app.models import RegisterPushTokenRequest
from backend.app.notifications import (
    dispatch_eligible_notifications,
    get_pending_push_event_ids,
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


# --- Sprint 3.6.6G: badge/push coherence -------------------------------
#
# Real on-device finding: 3 real pushes arrived, but the in-app badge
# stayed at 0. Root cause -- two independent "is this new" signals:
# is_new_for_user (forced False on the very first /v1/opportunities call
# after a restart, by design -- see test_notifications.py's
# test_first_load_is_notification_silent) and interruption=="alert" (push
# eligibility, untouched by that first-load override). These tests cover
# the fix: the badge (is_new_for_user) now also reflects
# get_pending_push_event_ids() -- dispatched minus reviewed -- so a real
# push always has something to show for it, while items that were never
# pushed keep the original first-load-quiet behavior unchanged.
#
# The exact sequence below (one _run_feed_pipeline() call representing the
# app's first load, then dispatch_eligible_notifications()'s own internal
# call representing the poller's next cycle) deterministically yields 3
# alert-eligible items against the fixed simulated fixtures/engagement
# data -- reproducing the real reported "3 pushed, badge 0" scenario
# exactly, not a stand-in count.


def test_pending_push_notification_full_lifecycle():
    """3 pushed -> badge reflects 3 -> open (review) one -> badge reflects
    2 -> review the remaining two -> badge reflects 0."""
    register_token(RegisterPushTokenRequest(expo_push_token="ExponentPushToken[aaa]"))

    # The app's first-ever /v1/opportunities call -- forces is_new_for_user
    # False for everything under the pre-existing first-load rule.
    first_load_items, _now, _alert = _run_feed_pipeline()
    assert all(not item.is_new_for_user for item in first_load_items)

    # The poller's own next cycle -- dispatches real pushes independent of
    # the first-load badge override above.
    dispatched_count = dispatch_eligible_notifications(client=_mock_client())
    assert dispatched_count == 3  # deterministic against the fixed fixtures

    pending = get_pending_push_event_ids()
    assert len(pending) == 3

    # Badge == items whose is_new_for_user is True.
    items, _now, _alert = _run_feed_pipeline()
    pushed_items = [item for item in items if item.event_id in pending]
    assert len(pushed_items) == 3
    assert all(item.is_new_for_user for item in pushed_items)
    assert sum(1 for item in items if item.is_new_for_user) == 3

    # "Open one" -- reviewing a single event_id (what openNotificationCard
    # now does on the mobile side) clears only that one.
    first_reviewed = pushed_items[0].event_id
    mark_notifications_reviewed([first_reviewed])
    assert get_pending_push_event_ids() == pending - {first_reviewed}

    items, _now, _alert = _run_feed_pipeline()
    reviewed_item = next(i for i in items if i.event_id == first_reviewed)
    assert reviewed_item.is_new_for_user is False
    assert sum(1 for item in items if item.is_new_for_user) == 2

    # "Review remaining" -- clears the badge to zero.
    remaining = list(pending - {first_reviewed})
    assert len(remaining) == 2
    mark_notifications_reviewed(remaining)
    assert get_pending_push_event_ids() == set()

    items, _now, _alert = _run_feed_pipeline()
    assert sum(1 for item in items if item.is_new_for_user) == 0


def test_repeated_polling_does_not_change_pending_state():
    """Polling alone (no dispatch, no review) must never grow or shrink the
    pending set -- only a real dispatch or a real review changes it."""
    register_token(RegisterPushTokenRequest(expo_push_token="ExponentPushToken[aaa]"))
    _run_feed_pipeline()  # first load
    dispatch_eligible_notifications(client=_mock_client())
    pending_after_dispatch = get_pending_push_event_ids()

    for _ in range(3):
        _run_feed_pipeline()
        dispatch_eligible_notifications(
            client=_mock_client()
        )  # already-dispatched, no-op
        assert get_pending_push_event_ids() == pending_after_dispatch


def test_reviewing_never_pushed_event_id_is_a_harmless_no_op():
    """Reviewing an event_id that was never pushed must not raise or
    corrupt the pending set for real pushed items."""
    register_token(RegisterPushTokenRequest(expo_push_token="ExponentPushToken[aaa]"))
    _run_feed_pipeline()
    dispatch_eligible_notifications(client=_mock_client())
    pending_before = get_pending_push_event_ids()

    from uuid import uuid4

    mark_notifications_reviewed([uuid4()])  # never pushed
    assert get_pending_push_event_ids() == pending_before


def test_first_load_quiet_behavior_preserved_for_never_pushed_items():
    """Items that were never pushed at all must keep the original
    first-load-quiet behavior -- the fix only affects items that were
    genuinely dispatched."""
    # No token registered, so nothing is ever dispatched -- pending stays
    # empty throughout, and every item's is_new_for_user should follow the
    # pre-existing first-load rule exactly as before this sprint.
    items, _now, _alert = _run_feed_pipeline()
    assert get_pending_push_event_ids() == set()
    assert all(not item.is_new_for_user for item in items)


def test_mark_notifications_reviewed_clears_pending_through_the_one_endpoint():
    """The same POST /v1/notifications/review the in-app badge already used
    before this sprint must also clear pending-push state -- one review
    action, coherent effect on both mechanisms, not two separate calls the
    client would need to know about."""
    register_token(RegisterPushTokenRequest(expo_push_token="ExponentPushToken[aaa]"))
    _run_feed_pipeline()
    dispatch_eligible_notifications(client=_mock_client())
    pending = get_pending_push_event_ids()
    assert pending

    mark_notifications_reviewed(list(pending))
    assert get_pending_push_event_ids() == set()
