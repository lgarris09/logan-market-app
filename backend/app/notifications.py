"""Sprint 3.6.6F -- STRATUS Watch, first real push-notification slice.

Smallest production-capable path: reuses the existing Prioritization
Engine's `interruption == "alert"` gate as notification eligibility (no new
threshold invented), dispatches real Expo pushes to registered device
tokens, and dedups per event_id so the same opportunity isn't re-pushed on
every poll cycle. Token storage and dedup state are in-memory,
process-lifetime only -- the same pattern already used for `_orchestrator`/
`_baseline_established` in logan_feed.py, not a new persistence layer.

Sprint 3.6.8 Block 2 (ADR-057): every piece of state here is now keyed by
`user_id`, not global -- a single shared token/dedup set meant one user's
push-token registration received every other user's alert-eligible items
(since alert eligibility comes from `get_alert_eligible_items()`, which is
now itself per-user), and one user reviewing a notification silenced the
pending-push badge for everyone. A real per-user, *durable* token store
(surviving a backend restart) remains an ADR-006-scale decision, still not
made here -- this block fixes cross-user isolation, not persistence.

Known limitation, not solved here: a successful HTTP response from Expo's
push endpoint does not guarantee each individual message was deliverable
(e.g. a stale/unregistered token) -- Expo's receipt API would need a
follow-up call to detect that. Not implemented; a stale token just keeps
failing silently until someone re-registers.
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

_registered_tokens: dict[str, set[str]] = {}
_dispatched_event_ids: dict[str, set[UUID]] = {}
# Sprint 3.6.6G: subset of _dispatched_event_ids the user has reviewed/opened
# (see mark_pushed_notifications_reviewed below). Deliberately a separate set
# rather than removing entries from _dispatched_event_ids itself --
# _dispatched_event_ids must stay a permanent record for push dedup (a
# reviewed item must never be re-pushed either), while pending/badge status
# is a derived view on top of it (get_pending_push_event_ids).
_reviewed_pushed_event_ids: dict[str, set[UUID]] = {}


def register_token(
    user_id: str, request: RegisterPushTokenRequest
) -> RegisterPushTokenResponse:
    tokens = _registered_tokens.setdefault(user_id, set())
    tokens.add(request.expo_push_token)
    return RegisterPushTokenResponse(registered=True, token_count=len(tokens))


def mark_pushed_notifications_reviewed(user_id: str, event_ids: list[UUID]) -> None:
    """Sprint 3.6.6G: called by logan_feed.mark_notifications_reviewed() --
    the same POST /v1/notifications/review the in-app badge already used
    before this sprint -- so reviewing an opportunity clears it from the
    pending-push count too. One review action, one endpoint, coherent effect
    on both the pre-existing is_new_for_user badge path and this push-pending
    path. Safe to call with event_ids that were never actually pushed
    (get_pending_push_event_ids' set difference makes that a no-op for them).
    Scoped to `user_id` (Sprint 3.6.8 Block 2) -- one user reviewing an
    event_id must never clear another user's own pending-push state for that
    same event_id.
    """
    _reviewed_pushed_event_ids.setdefault(user_id, set()).update(event_ids)
    print(f"[notifications] reviewed for {user_id}: {event_ids}")


def get_pending_push_event_ids(user_id: str) -> set[UUID]:
    """Sprint 3.6.6G: event_ids that were successfully pushed to `user_id`
    (_dispatched_event_ids -- the existing push dedup/source-of-truth) but
    not yet reviewed by them. Read by logan_feed._run_feed_pipeline() to make
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
    return _dispatched_event_ids.get(user_id, set()) - _reviewed_pushed_event_ids.get(
        user_id, set()
    )


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
    item to every registered token, once per user_id that has at least one
    registered token (Sprint 3.6.8 Block 2 -- was a single pass over one
    shared token set/eligibility list; each user's alert eligibility is now
    itself computed from that user's own personalized pipeline run via
    `get_alert_eligible_items(user_id)`, so a per-user dispatch pass is what
    actually keeps one user's tokens receiving only that user's own eligible
    items). Returns the number of *items* dispatched across every user
    (one item may still fan out to multiple tokens for the same user).
    Never raises -- a push-service failure for one user must not crash the
    poller loop or stop dispatch for any other user; an item is only marked
    dispatched (for that user) after a successful send, so a transient
    failure retries on the next cycle rather than silently dropping the
    notification forever.
    """
    if not _registered_tokens:
        return 0

    owns_client = client is None
    client = client or httpx.Client(timeout=10.0)
    total_dispatched = 0
    try:
        for user_id, tokens in list(_registered_tokens.items()):
            if not tokens:
                continue

            # Sprint 3.6.8 Block 4 (beta-readiness hardening): the whole
            # per-user body -- not just the push send below -- is guarded
            # here. get_alert_eligible_items(user_id) runs that user's full
            # personalized pipeline (including any live provider calls);
            # before this fix, an exception there propagated straight out of
            # this loop and skipped dispatch for every *other* registered
            # user in the same poll cycle too, contradicting this function's
            # own documented contract ("a failure for one user must not stop
            # dispatch for any other user"). The outer poller loop
            # (main.py's _notification_poll_loop) still catches anything
            # that somehow escapes this, but that would silently cost an
            # entire cycle for every user, not just the one that failed.
            try:
                dispatched_ids = _dispatched_event_ids.setdefault(user_id, set())
                eligible = [
                    item
                    for item in get_alert_eligible_items(user_id)
                    if item.event_id not in dispatched_ids
                ]
                if not eligible:
                    continue

                messages = [
                    _build_push_message(token, item)
                    for item in eligible
                    for token in tokens
                ]
                try:
                    client.post(EXPO_PUSH_URL, json=messages)
                except httpx.RequestError as exc:
                    print(
                        f"[notifications] Expo push dispatch to {user_id} failed, "
                        f"will retry next poll: {exc}"
                    )
                    continue

                dispatched_item_ids = [item.event_id for item in eligible]
                print(
                    f"[notifications] dispatched to {user_id}'s {len(tokens)} "
                    f"token(s): {dispatched_item_ids}"
                )
                dispatched_ids.update(dispatched_item_ids)
                total_dispatched += len(eligible)
            except Exception as exc:  # noqa: BLE001 -- see comment above
                print(
                    f"[notifications] dispatch pass for {user_id} failed "
                    f"unexpectedly, skipping to the next user: {exc}"
                )
                continue
    finally:
        if owns_client:
            client.close()

    return total_dispatched
