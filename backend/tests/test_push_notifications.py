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
    _notification_body,
    dispatch_eligible_notifications,
    get_pending_push_event_ids,
    register_token,
    reset_notification_state,
)
from logan_core.contracts import LOCAL_FOUNDER_USER_ID


def _mock_client(handler=None):
    if handler is None:

        def handler(request):
            return httpx.Response(200, json={"data": []})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_register_token_stores_and_counts():
    result = register_token(
        LOCAL_FOUNDER_USER_ID,
        RegisterPushTokenRequest(expo_push_token="ExponentPushToken[aaa]"),
    )
    assert result.registered is True
    assert result.token_count == 1

    result2 = register_token(
        LOCAL_FOUNDER_USER_ID,
        RegisterPushTokenRequest(expo_push_token="ExponentPushToken[bbb]"),
    )
    assert result2.token_count == 2


def test_register_same_token_twice_does_not_double_count():
    register_token(
        LOCAL_FOUNDER_USER_ID,
        RegisterPushTokenRequest(expo_push_token="ExponentPushToken[aaa]"),
    )
    result = register_token(
        LOCAL_FOUNDER_USER_ID,
        RegisterPushTokenRequest(expo_push_token="ExponentPushToken[aaa]"),
    )
    assert result.token_count == 1


def test_no_dispatch_without_registered_tokens():
    assert (
        len(get_alert_eligible_items(LOCAL_FOUNDER_USER_ID)) > 0
    )  # sanity: eligible items exist
    dispatched = dispatch_eligible_notifications(client=_mock_client())
    assert dispatched == 0


def test_dispatch_sends_to_registered_token_for_every_eligible_item():
    # Deliberately does not pre-fetch get_alert_eligible_items(LOCAL_FOUNDER_USER_ID) as a
    # reference count -- that call is itself a pipeline poll, and a second
    # poll can legitimately see a different eligible set (e.g. stance
    # shifting new -> confirms lowers novelty/internal_rank_score once an
    # event has been observed once). Assert against what this single
    # dispatch call itself actually sent, not a separately-polled count.
    register_token(
        LOCAL_FOUNDER_USER_ID,
        RegisterPushTokenRequest(expo_push_token="ExponentPushToken[aaa]"),
    )

    captured = {}

    def handler(request):
        captured["body"] = request.content
        return httpx.Response(200, json={"data": []})

    dispatched = dispatch_eligible_notifications(client=_mock_client(handler))
    assert dispatched > 0
    assert captured.get("body")


def test_push_payload_contains_event_id_display_name_and_headline():
    register_token(
        LOCAL_FOUNDER_USER_ID,
        RegisterPushTokenRequest(expo_push_token="ExponentPushToken[aaa]"),
    )

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
    assert nvda_message["body"]  # non-empty body text
    UUID(nvda_message["data"]["event_id"])  # valid UUID, doesn't raise


def test_dispatch_fans_out_to_every_registered_token():
    register_token(
        LOCAL_FOUNDER_USER_ID,
        RegisterPushTokenRequest(expo_push_token="ExponentPushToken[aaa]"),
    )
    register_token(
        LOCAL_FOUNDER_USER_ID,
        RegisterPushTokenRequest(expo_push_token="ExponentPushToken[bbb]"),
    )

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
    register_token(
        LOCAL_FOUNDER_USER_ID,
        RegisterPushTokenRequest(expo_push_token="ExponentPushToken[aaa]"),
    )
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
    register_token(
        LOCAL_FOUNDER_USER_ID,
        RegisterPushTokenRequest(expo_push_token="ExponentPushToken[aaa]"),
    )

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
# get_pending_push_event_ids(LOCAL_FOUNDER_USER_ID) -- dispatched minus reviewed -- so a real
# push always has something to show for it, while items that were never
# pushed keep the original first-load-quiet behavior unchanged.
#
# The exact sequence below (one _run_feed_pipeline(LOCAL_FOUNDER_USER_ID) call representing the
# app's first load, then dispatch_eligible_notifications()'s own internal
# call representing the poller's next cycle) deterministically yields 3
# alert-eligible items against the fixed simulated fixtures/engagement
# data -- reproducing the real reported "3 pushed, badge 0" scenario
# exactly, not a stand-in count.


def test_pending_push_notification_full_lifecycle():
    """N pushed -> badge reflects N -> open (review) one -> badge reflects
    N-1 -> review the remaining N-1 -> badge reflects 0. Deliberately does
    not hardcode N: the exact alert-eligible count against the fixed
    simulated fixtures depends on real engagement-derived lifecycle state
    (Sprint 3.6.6I fixed a timing artifact that was inflating it) -- this
    test proves the pending/badge state-machine mechanics, not a specific
    count. See test_engagement_fixture_timing.py for engagement timing
    coverage and the eligibility trace in docs/DECISIONS.md's Sprint
    3.6.6I ADR for what the real count is and why."""
    register_token(
        LOCAL_FOUNDER_USER_ID,
        RegisterPushTokenRequest(expo_push_token="ExponentPushToken[aaa]"),
    )

    # This test scripts two pipeline calls in a fixed order (a first-load-
    # style call, then a dispatch call) to exercise both code paths
    # deterministically -- it is not a claim that the background poller is
    # guaranteed to run after the app's own first request in real deployment.
    # Startup/request ordering between the app's initial fetch and the
    # poller's own first cycle can vary; get_pending_push_event_ids(LOCAL_FOUNDER_USER_ID)'s fix
    # is deliberately correct either way (see its own docstring) rather than
    # relying on one specific order. This sequence matches the on-device
    # scenario this fix was written for, not a guaranteed runtime ordering.
    first_load_items, _now, _alert, _provider_degraded = _run_feed_pipeline(
        LOCAL_FOUNDER_USER_ID
    )
    assert all(not item.is_new_for_user for item in first_load_items)

    # The next pipeline call in this test's own sequence -- dispatches real
    # pushes independent of the first-load badge override above.
    dispatched_count = dispatch_eligible_notifications(client=_mock_client())
    assert dispatched_count >= 2  # sanity: still a real, non-trivial alert set

    pending = get_pending_push_event_ids(LOCAL_FOUNDER_USER_ID)
    assert len(pending) == dispatched_count

    # Badge == items whose is_new_for_user is True.
    items, _now, _alert, _provider_degraded = _run_feed_pipeline(LOCAL_FOUNDER_USER_ID)
    pushed_items = [item for item in items if item.event_id in pending]
    assert len(pushed_items) == dispatched_count
    assert all(item.is_new_for_user for item in pushed_items)
    assert sum(1 for item in items if item.is_new_for_user) == dispatched_count

    # "Open one" -- reviewing a single event_id (what openNotificationCard
    # now does on the mobile side) clears only that one.
    first_reviewed = pushed_items[0].event_id
    mark_notifications_reviewed(LOCAL_FOUNDER_USER_ID, [first_reviewed])
    assert get_pending_push_event_ids(LOCAL_FOUNDER_USER_ID) == pending - {
        first_reviewed
    }

    items, _now, _alert, _provider_degraded = _run_feed_pipeline(LOCAL_FOUNDER_USER_ID)
    reviewed_item = next(i for i in items if i.event_id == first_reviewed)
    assert reviewed_item.is_new_for_user is False
    assert sum(1 for item in items if item.is_new_for_user) == dispatched_count - 1

    # "Review remaining" -- clears the badge to zero.
    remaining = list(pending - {first_reviewed})
    assert len(remaining) == dispatched_count - 1
    mark_notifications_reviewed(LOCAL_FOUNDER_USER_ID, remaining)
    assert get_pending_push_event_ids(LOCAL_FOUNDER_USER_ID) == set()

    items, _now, _alert, _provider_degraded = _run_feed_pipeline(LOCAL_FOUNDER_USER_ID)
    assert sum(1 for item in items if item.is_new_for_user) == 0


def test_repeated_polling_does_not_change_pending_state():
    """Polling alone (no dispatch, no review) must never grow or shrink the
    pending set -- only a real dispatch or a real review changes it."""
    register_token(
        LOCAL_FOUNDER_USER_ID,
        RegisterPushTokenRequest(expo_push_token="ExponentPushToken[aaa]"),
    )
    _run_feed_pipeline(LOCAL_FOUNDER_USER_ID)  # first load
    dispatch_eligible_notifications(client=_mock_client())
    pending_after_dispatch = get_pending_push_event_ids(LOCAL_FOUNDER_USER_ID)

    for _ in range(3):
        _run_feed_pipeline(LOCAL_FOUNDER_USER_ID)
        dispatch_eligible_notifications(
            client=_mock_client()
        )  # already-dispatched, no-op
        assert (
            get_pending_push_event_ids(LOCAL_FOUNDER_USER_ID) == pending_after_dispatch
        )


def test_reviewing_never_pushed_event_id_is_a_harmless_no_op():
    """Reviewing an event_id that was never pushed must not raise or
    corrupt the pending set for real pushed items."""
    register_token(
        LOCAL_FOUNDER_USER_ID,
        RegisterPushTokenRequest(expo_push_token="ExponentPushToken[aaa]"),
    )
    _run_feed_pipeline(LOCAL_FOUNDER_USER_ID)
    dispatch_eligible_notifications(client=_mock_client())
    pending_before = get_pending_push_event_ids(LOCAL_FOUNDER_USER_ID)

    from uuid import uuid4

    mark_notifications_reviewed(LOCAL_FOUNDER_USER_ID, [uuid4()])  # never pushed
    assert get_pending_push_event_ids(LOCAL_FOUNDER_USER_ID) == pending_before


def test_first_load_quiet_behavior_preserved_for_never_pushed_items():
    """Items that were never pushed at all must keep the original
    first-load-quiet behavior -- the fix only affects items that were
    genuinely dispatched."""
    # No token registered, so nothing is ever dispatched -- pending stays
    # empty throughout, and every item's is_new_for_user should follow the
    # pre-existing first-load rule exactly as before this sprint.
    items, _now, _alert, _provider_degraded = _run_feed_pipeline(LOCAL_FOUNDER_USER_ID)
    assert get_pending_push_event_ids(LOCAL_FOUNDER_USER_ID) == set()
    assert all(not item.is_new_for_user for item in items)


def test_mark_notifications_reviewed_clears_pending_through_the_one_endpoint():
    """The same POST /v1/notifications/review the in-app badge already used
    before this sprint must also clear pending-push state -- one review
    action, coherent effect on both mechanisms, not two separate calls the
    client would need to know about."""
    register_token(
        LOCAL_FOUNDER_USER_ID,
        RegisterPushTokenRequest(expo_push_token="ExponentPushToken[aaa]"),
    )
    _run_feed_pipeline(LOCAL_FOUNDER_USER_ID)
    dispatch_eligible_notifications(client=_mock_client())
    pending = get_pending_push_event_ids(LOCAL_FOUNDER_USER_ID)
    assert pending

    mark_notifications_reviewed(LOCAL_FOUNDER_USER_ID, list(pending))
    assert get_pending_push_event_ids(LOCAL_FOUNDER_USER_ID) == set()


# --- Sprint 3.6.6H: notification wording -----------------------------
#
# _build_push_message previously used delivered_item.headline verbatim --
# World Model's raw "{entity}: {signal_type} ({value})" template, e.g.
# "Federal Reserve: breaking news (Federal Reserve rate decision expected
# this week)". Right for the in-app card; reads as raw feed syntax with a
# redundant entity mention in a push notification, where the title already
# carries the entity name. _notification_body extracts the same
# already-natural `value` text that template wraps and strips a redundant
# leading entity mention from it -- no new copy-generation layer, no
# per-entity special-casing.


def _item_for(entity_id: str):
    items, _now, _alert, _provider_degraded = _run_feed_pipeline(LOCAL_FOUNDER_USER_ID)
    return next(i for i in items if i.entity_id == entity_id)


def test_notification_body_strips_redundant_entity_name_fed():
    """Direction example: 'Federal Reserve -- Rate decision expected this
    week'."""
    item = _item_for("FED")
    body = _notification_body(item)
    assert body == "Rate decision expected this week"
    assert "Federal Reserve" not in body


def test_notification_body_strips_redundant_entity_name_ai_sector():
    """Direction example: 'AI -- Infrastructure discussion volume is
    accelerating'. This mechanical strip/reformat produces 'rising' rather
    than 'is accelerating' -- a real, documented limitation (see
    _notification_body's own docstring), not a bug: genuine tense/wording
    rewriting is out of scope for a generic, reusable transform."""
    item = _item_for("AI_SECTOR")
    body = _notification_body(item)
    assert body == "Infrastructure discussion volume rising"
    assert not body.lower().startswith("ai ")


def test_notification_body_nfl_reads_naturally_without_prefix_stripping():
    """Direction example: 'NFL -- Week 7 spreads are moving sharply'. The
    raw value never mentions 'NFL', so nothing needs stripping here --
    proves the transform is a no-op when there's no redundancy to remove,
    not a rewrite applied unconditionally."""
    item = _item_for("NFL")
    body = _notification_body(item)
    assert body == "Week 7 spreads moving sharply across the board"


def test_notification_body_strips_ticker_when_display_name_does_not_match():
    """A report-style value starting with the ticker (e.g. live NVDA
    earnings: 'NVDA reported EPS of 1.87 vs. consensus 1.76') rather than
    the full display_name ('NVIDIA') must still be recognized as
    redundant."""
    item = _item_for("NVDA")
    fabricated = item.model_copy(
        update={
            "delivered_item": item.delivered_item.model_copy(
                update={
                    "what_happened": (
                        "NVIDIA: earnings signal "
                        "(NVDA reported EPS of 1.87 vs. consensus 1.76)"
                    )
                }
            )
        }
    )
    body = _notification_body(fabricated)
    assert body == "Reported EPS of 1.87 vs. consensus 1.76"


def test_notification_body_falls_back_to_headline_on_unexpected_shape():
    """A what_happened string that doesn't match World Model's template at
    all (e.g. a hypothetical future receptor) must never crash or produce
    an empty body -- falls back to the existing headline."""
    item = _item_for("FED")
    fabricated = item.model_copy(
        update={
            "delivered_item": item.delivered_item.model_copy(
                update={"what_happened": "No parenthetical value in this string"}
            )
        }
    )
    assert _notification_body(fabricated) == fabricated.delivered_item.headline


def test_notification_body_never_contains_raw_signal_type_phrases():
    """No mechanical signal_type label should ever leak into a push body
    across the full simulated fixture set. Deliberately excludes labels
    like "volatility spike" that legitimately overlap with real English in
    a fixture's natural value text (BTC's "volatility spikes on ETF flow
    data" is a genuine sentence, not leaked jargon) -- this checks for the
    template's mechanical LABEL form specifically, not any word overlap."""
    items, _now, _alert, _provider_degraded = _run_feed_pipeline(LOCAL_FOUNDER_USER_ID)
    mechanical_phrases = [
        "trend emerging",
        "line move",
        "breaking news",
        "technical breakout",
        "earnings signal",
        "news event",
        "price change",
    ]
    for item in items:
        body = _notification_body(item).lower()
        for phrase in mechanical_phrases:
            assert phrase not in body, f"{item.entity_id}: {body!r} contains {phrase!r}"


def test_notification_body_does_not_repeat_the_title_verbatim():
    """The body must never restate item.display_name at its start -- title
    and body are shown together, so a leading repeat is always redundant."""
    items, _now, _alert, _provider_degraded = _run_feed_pipeline(LOCAL_FOUNDER_USER_ID)
    for item in items:
        body = _notification_body(item)
        assert not body.lower().startswith(
            item.display_name.lower()
        ), f"{item.entity_id}: {body!r} repeats display_name {item.display_name!r}"


def test_notification_body_is_short_enough_to_scan():
    """Every simulated fixture's transformed body stays well under iOS's
    ~2-line preview -- not a hard contract, just a sanity bound so this
    stays 'concise' as new fixtures are added."""
    items, _now, _alert, _provider_degraded = _run_feed_pipeline(LOCAL_FOUNDER_USER_ID)
    for item in items:
        assert len(_notification_body(item)) <= 80


# --- Sprint 3.6.8 Block 4: per-user dispatch isolation on pipeline failure --


def test_one_users_pipeline_failure_does_not_stop_dispatch_for_other_users():
    """Beta-readiness hardening finding: dispatch_eligible_notifications()'s
    docstring already claimed a failure for one user must not stop dispatch
    for any other user -- but only the push-send itself was actually guarded
    against that. get_alert_eligible_items(user_id) (which runs that user's
    full pipeline) was not, so an exception there used to propagate straight
    out of the per-user loop and silently skip every other registered user
    for that entire poll cycle. This proves the fix: a failing user is
    skipped, everyone else still gets dispatched, in the same call."""
    from unittest.mock import patch

    reset_notification_state()
    register_token(
        "failing-user",
        RegisterPushTokenRequest(expo_push_token="ExponentPushToken[fail]"),
    )
    register_token(
        LOCAL_FOUNDER_USER_ID,
        RegisterPushTokenRequest(expo_push_token="ExponentPushToken[ok]"),
    )

    real_get_alert_eligible_items = get_alert_eligible_items

    def _flaky(user_id):
        if user_id == "failing-user":
            raise RuntimeError("simulated pipeline failure for this user only")
        return real_get_alert_eligible_items(user_id)

    with patch(
        "backend.app.notifications.get_alert_eligible_items", side_effect=_flaky
    ):
        dispatched = dispatch_eligible_notifications(client=_mock_client())

    # The founder's dispatch still happened despite failing-user's exception.
    assert dispatched > 0
    assert get_pending_push_event_ids(LOCAL_FOUNDER_USER_ID)
    assert get_pending_push_event_ids("failing-user") == set()
