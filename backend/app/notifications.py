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

import re
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
# Sprint 3.6.6G: subset of _dispatched_event_ids the user has reviewed/opened
# (see mark_pushed_notifications_reviewed below). Deliberately a separate set
# rather than removing entries from _dispatched_event_ids itself --
# _dispatched_event_ids must stay a permanent record for push dedup (a
# reviewed item must never be re-pushed either), while pending/badge status
# is a derived view on top of it (get_pending_push_event_ids).
_reviewed_pushed_event_ids: set[UUID] = set()


def register_token(request: RegisterPushTokenRequest) -> RegisterPushTokenResponse:
    _registered_tokens.add(request.expo_push_token)
    return RegisterPushTokenResponse(
        registered=True, token_count=len(_registered_tokens)
    )


def mark_pushed_notifications_reviewed(event_ids: list[UUID]) -> None:
    """Sprint 3.6.6G: called by logan_feed.mark_notifications_reviewed() --
    the same POST /v1/notifications/review the in-app badge already used
    before this sprint -- so reviewing an opportunity clears it from the
    pending-push count too. One review action, one endpoint, coherent effect
    on both the pre-existing is_new_for_user badge path and this push-pending
    path. Safe to call with event_ids that were never actually pushed
    (get_pending_push_event_ids' set difference makes that a no-op for them).
    """
    _reviewed_pushed_event_ids.update(event_ids)
    print(f"[notifications] reviewed: {event_ids}")


def get_pending_push_event_ids() -> set[UUID]:
    """Sprint 3.6.6G: event_ids that were successfully pushed
    (_dispatched_event_ids -- the existing push dedup/source-of-truth) but
    not yet reviewed. Read by logan_feed._run_feed_pipeline() to make
    is_new_for_user coherent with real push delivery: a pushed-but-unopened
    notification must show in the in-app badge even on the very first poll
    cycle after a backend restart, when the pre-existing "first load is
    notification-silent" rule would otherwise hide it (real on-device
    finding: 3 real pushes arrived with the badge staying at 0). Deliberately
    a pure derived read (dispatched minus reviewed), not its own independent
    set, so it can never drift out of sync with the real dispatch/review
    state, and reviewing an item already implies removing it from here
    without any separate bookkeeping to keep in sync.
    """
    return _dispatched_event_ids - _reviewed_pushed_event_ids


def reset_notification_state() -> None:
    """Test-only (and general-purpose "start over") hook, mirroring
    logan_feed.reset_pipeline_state() -- drops registered tokens and dispatch
    history so the next call behaves like a fresh process start.
    """
    _registered_tokens.clear()
    _dispatched_event_ids.clear()
    _reviewed_pushed_event_ids.clear()


def _notification_body(item: FeedItem) -> str:
    """Sprint 3.6.6H: a concise, human-scannable push body, built from the
    existing DeliveredItem text rather than a new copy-generation layer.
    `what_happened`/`headline` are both built from one deterministic
    template in World Model (`world_model/model.py`'s `process()`:
    `f"{entity.display_name}: {signal_type_readable} ({value})"`) -- the
    right shape for the in-app card, which benefits from that fuller
    mechanical context, but it reads as raw feed syntax in a push
    notification, where the title already carries the entity name
    (`FeedItem.display_name`). This extracts the same underlying `value`
    text the template already wraps -- already natural, provider-authored
    text, never invented here -- and strips a redundant leading mention of
    the entity (display_name or ticker) from it. Falls back to the
    unmodified headline whenever the expected template shape isn't found,
    so a future receptor that builds `what_happened` differently never
    produces an empty or broken notification.

    Known limitation, not solved here: this is a generic strip/reformat,
    not a semantic rewrite -- "AI infrastructure discussion volume rising"
    becomes "Infrastructure discussion volume rising", not "...is
    accelerating". Genuinely rephrasing tense/wording per signal would mean
    either a hardcoded per-signal-type template table or real generative
    copy -- both out of scope for this pass, and neither is "reusing
    existing presentation logic."
    """
    match = re.search(r"\((.*?)\)", item.delivered_item.what_happened)
    if not match:
        return item.delivered_item.headline

    value = match.group(1).strip()
    for prefix in filter(None, [item.display_name, item.ticker]):
        if value.lower().startswith(prefix.lower()):
            value = value[len(prefix) :].lstrip(" :,-")
            break

    if not value:
        return match.group(1).strip() or item.delivered_item.headline

    return value[0].upper() + value[1:]


def _build_push_message(token: str, item: FeedItem) -> dict:
    # event_id is the one piece of data the mobile app actually needs on tap
    # -- it feeds directly into the existing openNotificationCard(eventId)
    # flow already used by the in-app notification dropdown, so a
    # notification tap opens the identical card, not a second
    # implementation.
    return {
        "to": token,
        "title": item.display_name,
        "body": _notification_body(item),
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

    dispatched_ids = [item.event_id for item in eligible]
    print(
        f"[notifications] dispatched to {len(_registered_tokens)} token(s): "
        f"{dispatched_ids}"
    )

    for item in eligible:
        _dispatched_event_ids.add(item.event_id)
    return len(eligible)
