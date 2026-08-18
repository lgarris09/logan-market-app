"""Sprint 3.6.6F -- STRATUS Watch, first real push-notification slice.

Smallest production-capable path: reuses the existing Prioritization
Engine's `interruption == "alert"` gate as notification eligibility (no new
threshold invented), dispatches real Expo pushes to registered device
tokens, and dedups per event_id so the same opportunity isn't re-pushed on
every poll cycle. Token storage and dedup state are in-memory,
process-lifetime only -- the same pattern already used for `_orchestrator`/
`_baseline_established` in logan_feed.py, not a new persistence layer. A
real per-user, durable token store is an ADR-006-scale decision, flagged
separately, not folded into this slice.

Known limitation, not solved here: a successful HTTP response from Expo's
push endpoint does not guarantee each individual message was deliverable
(e.g. a stale/unregistered token) -- Expo's receipt API would need a
follow-up call to detect that. Not implemented; a stale token just keeps
failing silently until someone re-registers. Acceptable for a first slice
with a single demo user and a handful of tokens, not for real multi-device
scale.
"""

from typing import Optional
from uuid import UUID

import httpx

from .logan_feed import FeedItem, get_alert_eligible_items
from .models import RegisterPushTokenRequest, RegisterPushTokenResponse

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
# Matches the mobile app's own foreground poll cadence (index.tsx's
# NOTIFICATION_POLL_INTERVAL_MS) -- not a hard requirement, just a
# reasonable default so a real push and the in-app badge stay roughly in
# sync rather than one lagging the other by an arbitrary amount.
NOTIFICATION_POLL_INTERVAL_SECONDS = 60

_registered_tokens: set[str] = set()
_dispatched_event_ids: set[UUID] = set()


def register_token(request: RegisterPushTokenRequest) -> RegisterPushTokenResponse:
    _registered_tokens.add(request.expo_push_token)
    return RegisterPushTokenResponse(
        registered=True, token_count=len(_registered_tokens)
    )


def reset_notification_state() -> None:
    """Test-only (and general-purpose "start over") hook, mirroring
    logan_feed.reset_pipeline_state() -- drops registered tokens and dispatch
    history so the next call behaves like a fresh process start.
    """
    _registered_tokens.clear()
    _dispatched_event_ids.clear()


def _build_push_message(token: str, item: FeedItem) -> dict:
    # event_id is the one piece of data the mobile app actually needs on tap
    # -- it feeds directly into the existing openNotificationCard(eventId)
    # flow already used by the in-app notification dropdown, so a
    # notification tap opens the identical card, not a second
    # implementation.
    return {
        "to": token,
        "title": item.display_name,
        "body": item.delivered_item.headline,
        "data": {"event_id": str(item.event_id)},
        "sound": "default",
    }


def dispatch_eligible_notifications(client: Optional[httpx.Client] = None) -> int:
    """Sends a real Expo push for every alert-eligible, not-yet-dispatched
    item to every registered token. Returns the number of *items* dispatched
    (one item may fan out to multiple registered tokens). Never raises -- a
    push-service failure must not crash the poller loop or whatever request
    happens to trigger this; an item is only marked dispatched after a
    successful send, so a transient failure retries on the next cycle rather
    than silently dropping the notification forever.
    """
    if not _registered_tokens:
        return 0

    eligible = [
        item
        for item in get_alert_eligible_items()
        if item.event_id not in _dispatched_event_ids
    ]
    if not eligible:
        return 0

    owns_client = client is None
    client = client or httpx.Client(timeout=10.0)
    try:
        messages = [
            _build_push_message(token, item)
            for item in eligible
            for token in _registered_tokens
        ]
        try:
            client.post(EXPO_PUSH_URL, json=messages)
        except httpx.RequestError as exc:
            print(
                f"[notifications] Expo push dispatch failed, will retry next poll: {exc}"
            )
            return 0
    finally:
        if owns_client:
            client.close()

    for item in eligible:
        _dispatched_event_ids.add(item.event_id)
    return len(eligible)
