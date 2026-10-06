"""Sprint 3.6.6F -- STRATUS Watch, first real push-notification slice.

Smallest production-capable path: reuses the existing Prioritization
Engine's `interruption == "alert"` gate as notification eligibility (no new
threshold invented), dispatches real Expo pushes to registered device
tokens, and dedups per event_id so the same opportunity isn't re-pushed on
every poll cycle. Token storage and dedup state live in the three
process-memory dicts below, optionally durably backed by SQLite (see
`NotificationStore`, `notification_store.py`) when
`config.memory_persistence_enabled()` is true.

Sprint 3.6.8 Block 2 (ADR-057): every piece of state here is now keyed by
`user_id`, not global -- a single shared token/dedup set meant one user's
push-token registration received every other user's alert-eligible items
(since alert eligibility comes from `get_alert_eligible_items()`, which is
now itself per-user), and one user reviewing a notification silenced the
pending-push badge for everyone.

Sprint 3.6.9 Block 1 (see docs/DECISIONS.md's Sprint 3.6.9 Block 1 ADR):
registered tokens and dispatch/review dedup state now survive a backend
restart when `STRATUS_PERSIST_MEMORY` is enabled -- closing the gap the
Block 2 comment above used to flag as "not made here." Disabled (the
default, and every pre-Block-1 test) leaves this byte-for-byte the prior
in-memory-only behavior.

Known limitation, not solved here: a successful HTTP response from Expo's
push endpoint does not guarantee each individual message was deliverable
(e.g. a stale/unregistered token) -- Expo's receipt API would need a
follow-up call to detect that. Not implemented; a stale token just keeps
failing silently until someone re-registers.
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, cast
from uuid import UUID

import httpx

from .config import (
    memory_persistence_enabled,
    notification_store_db_path,
    notifications_paused,
)
from .logan_feed import (
    FeedItem,
    get_alert_eligible_items,
    get_notification_ledger_store,
    mark_user_notified,
)
from .models import RegisterPushTokenRequest, RegisterPushTokenResponse
from .notification_store import NotificationStore

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from logan_core.contracts import MeaningfulChangeType  # noqa: E402

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

# Sprint 3.6.9 Block 1: optional durable backing for the three dicts above --
# reuses config.memory_persistence_enabled() rather than a second flag (see
# the Sprint 3.6.9 Block 1 ADR): "durable state persistence is on for this
# deployment" is one operator decision covering both behavioral memory and
# this notification state, not two independent toggles. None (the default,
# and every pre-Block-1 test) means these dicts behave exactly as before --
# pure process-memory, reset on every restart.
_store: Optional[NotificationStore] = None


def _get_store() -> Optional[NotificationStore]:
    """Lazily constructs (and loads from) the durable store on first use when
    persistence is enabled; a no-op returning None otherwise. Lazy rather
    than at import time so tests that flip STRATUS_PERSIST_MEMORY/
    STRATUS_STATE_DB_PATH via monkeypatch and then call
    reset_notification_state() (see below) get a fresh store pointed at
    whatever path is configured *now*, matching logan_feed._get_orchestrator()'s
    identical lazy-construction pattern for MemoryStore.
    """
    global _store
    if not memory_persistence_enabled():
        return None
    if _store is None:
        _store = NotificationStore(notification_store_db_path())
        _registered_tokens.clear()
        for user_id, tokens in _store.load_tokens().items():
            _registered_tokens[user_id] = set(tokens)
        _dispatched_event_ids.clear()
        for user_id, event_ids in _store.load_dispatched().items():
            _dispatched_event_ids[user_id] = set(event_ids)
        _reviewed_pushed_event_ids.clear()
        for user_id, event_ids in _store.load_reviewed().items():
            _reviewed_pushed_event_ids[user_id] = set(event_ids)
    return _store


def register_token(
    user_id: str, request: RegisterPushTokenRequest
) -> RegisterPushTokenResponse:
    store = _get_store()
    tokens = _registered_tokens.setdefault(user_id, set())
    tokens.add(request.expo_push_token)
    if store is not None:
        store.save_token(user_id, request.expo_push_token)
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
    store = _get_store()
    if store is not None:
        store.save_reviewed(user_id, event_ids)
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

    Sprint 3.6.9 Block 1: also releases the durable store's SQLite connection
    (mirroring reset_pipeline_state()'s identical handling of MemoryStore) --
    a no-op when persistence is disabled. The underlying file, if any, is
    left untouched: this simulates a real process restart (state reloads
    from disk on next use), not a data wipe. The *next* call to a mutating
    function (or `_get_store()` directly) reconstructs the store and reloads
    whatever was durably saved -- exactly the behavior a real backend restart
    with STRATUS_PERSIST_MEMORY enabled should have.
    """
    global _store
    if _store is not None:
        _store.close()
    _store = None
    _registered_tokens.clear()
    _dispatched_event_ids.clear()
    _reviewed_pushed_event_ids.clear()


def purge_user(user_id: str) -> None:
    """V2.3A (Identity & Account Foundation) -- the notification-state half
    of `purge_user_data()` (see backend/app/account_lifecycle.py). Removes
    this user's registered push tokens and dispatch/review dedup history,
    in-memory and durably.
    """
    store = _get_store()
    if store is not None:
        store.delete_user(user_id)
    _registered_tokens.pop(user_id, None)
    _dispatched_event_ids.pop(user_id, None)
    _reviewed_pushed_event_ids.pop(user_id, None)


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


def classify_dispatch_response(
    response: object, items_count: int, tokens_count: int
) -> list[tuple[str, int, int, Optional[str]]]:
    """ADR-081. Reads the push provider's response and returns, per item (in
    the order the messages were built: item-major, token-minor), a tuple
    `(state, accepted_count, rejected_count, detail)` using the bounded
    states in notification_ledger_store.DISPATCH_STATES. Claims only what
    the response establishes; anything unreadable is "dispatch_attempted",
    never "accepted".
    """
    status_code = getattr(response, "status_code", None)
    if not isinstance(status_code, int) or not 200 <= status_code < 300:
        return [("dispatch_failed", 0, 0, f"http_status={status_code}")] * items_count

    tickets: object = None
    try:
        body = response.json()  # type: ignore[attr-defined]
        tickets = body.get("data") if isinstance(body, dict) else None
    except Exception:  # noqa: BLE001 -- an unreadable body is "unknown", not a crash
        tickets = None

    expected = items_count * tokens_count
    if not isinstance(tickets, list) or len(tickets) != expected:
        return [("dispatch_attempted", 0, 0, "no_per_message_tickets")] * items_count

    outcomes: list[tuple[str, int, int, Optional[str]]] = []
    for index in range(items_count):
        chunk = tickets[index * tokens_count : (index + 1) * tokens_count]
        accepted = sum(
            1 for t in chunk if isinstance(t, dict) and t.get("status") == "ok"
        )
        errors = [
            t for t in chunk if isinstance(t, dict) and t.get("status") == "error"
        ]
        detail: Optional[str] = None
        if errors:
            codes = sorted(
                {
                    str((t.get("details") or {}).get("error") or "error")
                    for t in errors
                    if isinstance(t.get("details") or {}, dict)
                }
            )
            detail = ",".join(codes) or "error"
        if accepted:
            outcomes.append(("dispatch_accepted", accepted, len(errors), detail))
        elif errors and len(errors) == len(chunk):
            outcomes.append(("dispatch_rejected", 0, len(errors), detail))
        else:
            outcomes.append(("dispatch_attempted", 0, len(errors), detail))
    return outcomes


def _record_dispatch_outcomes(
    user_id: str,
    eligible: list[FeedItem],
    outcomes: list[tuple[str, int, int, Optional[str]]],
    attempted_at: datetime,
) -> None:
    """Writes one Decision Ledger dispatch row per item. Observation only:
    a recording failure never affects dispatch."""
    ledger = get_notification_ledger_store()
    if ledger is None:
        return
    for item, (state, accepted, rejected, detail) in zip(
        eligible, outcomes, strict=True
    ):
        try:
            ledger.record_dispatch(
                user_id=user_id,
                event_id=item.event_id,
                entity_id=item.entity_id,
                thesis_revision=item.opportunity_revision,
                state=state,
                accepted_count=accepted,
                rejected_count=rejected,
                detail=detail,
                attempted_at=attempted_at,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[notification-ledger] dispatch recording failed: {exc}")


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

    Sprint 3.6.9 Block 1: `_get_store()` is called here, first, specifically
    so this works correctly on the very first poll cycle after a real
    restart with persistence enabled -- before any client has re-registered
    a token this process's lifetime. Without this, `_registered_tokens`
    would still be empty at the `if not _registered_tokens` check below (no
    other code path had triggered the lazy load yet), the background poller
    would short-circuit to 0 every cycle, and durable token persistence
    would silently never actually restore delivery -- exactly the bug this
    block exists to close.
    """
    _get_store()
    if notifications_paused():
        # ADR-080: the operator pause. Nothing is sent and nothing is marked
        # dispatched or notified. The decision path records
        # `beta_notifications_paused` for each would-be interruption (see
        # logan_feed._run_feed_pipeline); this guard makes the pause hold at
        # the send boundary as well, independently of that path.
        return 0
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
                attempt_time = datetime.now(timezone.utc)
                try:
                    response = client.post(EXPO_PUSH_URL, json=messages)
                except httpx.RequestError as exc:
                    print(
                        f"[notifications] Expo push dispatch to {user_id} failed, "
                        f"will retry next poll: {exc}"
                    )
                    _record_dispatch_outcomes(
                        user_id,
                        eligible,
                        [("dispatch_failed", 0, 0, type(exc).__name__)] * len(eligible),
                        attempt_time,
                    )
                    continue

                # ADR-081: dispatch is not delivery. Read what the provider
                # actually said, per item, and act only on that:
                #   failed    -> not sent; retried on the next poll
                #   rejected  -> every token refused; never recorded as a
                #                notification the user received, and not
                #                retried (the refusal is deterministic)
                #   accepted / attempted -> handed to the provider; counts
                #                as "notified" for dedup so an unreadable
                #                response can never cause a second push
                outcomes = classify_dispatch_response(
                    response, len(eligible), len(tokens)
                )
                _record_dispatch_outcomes(user_id, eligible, outcomes, attempt_time)
                if outcomes and all(o[0] == "dispatch_failed" for o in outcomes):
                    print(
                        f"[notifications] Expo push dispatch to {user_id} was not "
                        f"accepted ({outcomes[0][3]}), will retry next poll"
                    )
                    continue
                rejected_items = [
                    item
                    for item, outcome in zip(eligible, outcomes, strict=True)
                    if outcome[0] == "dispatch_rejected"
                ]
                if rejected_items:
                    rejected_ids = [item.event_id for item in rejected_items]
                    print(
                        f"[notifications] push rejected for {user_id}: "
                        f"{rejected_ids}; not recorded as notified"
                    )
                    dispatched_ids.update(rejected_ids)
                    rejected_store = _get_store()
                    if rejected_store is not None:
                        rejected_store.save_dispatched(user_id, rejected_ids)
                eligible = [
                    item
                    for item, outcome in zip(eligible, outcomes, strict=True)
                    if outcome[0] in ("dispatch_accepted", "dispatch_attempted")
                ]
                if not eligible:
                    continue

                dispatched_item_ids = [item.event_id for item in eligible]
                print(
                    f"[notifications] dispatched to {user_id}'s {len(tokens)} "
                    f"token(s): {dispatched_item_ids}"
                )
                dispatched_ids.update(dispatched_item_ids)
                store = _get_store()
                if store is not None:
                    store.save_dispatched(user_id, dispatched_item_ids)
                # Stock Opportunity Logic V2.1 (User Sync Gap): the only
                # place last_notified_revision ever advances -- exactly here,
                # immediately after a real successful Expo dispatch, never at
                # "alert eligible" computation time (see
                # get_alert_eligible_items -- eligibility alone is not a
                # send). A no-op per item when opportunity_revision is None
                # (lifecycle/revision tracking not active for that entity).
                #
                # V2.4A (Notification Hygiene): also records this dispatch's
                # own meaningful_change_type (the same one decide_notification()
                # already evaluated to allow it through) alongside the
                # revision/timestamp, so a later poll's cooldown check can
                # tell a repeat of the same kind of change apart from a
                # materially different one.
                dispatch_time = datetime.now(timezone.utc)
                for item in eligible:
                    mark_user_notified(
                        user_id,
                        item.entity_id,
                        item.opportunity_revision,
                        now=dispatch_time,
                        # FeedItem.meaningful_change_type is deliberately
                        # typed str | None on the public API contract (see
                        # logan_feed.py's own FeedItem), but this value only
                        # ever originates from LifecycleDelta.change_type,
                        # which *is* the tight MeaningfulChangeType Literal --
                        # safe to narrow back here at this internal boundary.
                        change_type=cast(
                            Optional[MeaningfulChangeType],
                            item.meaningful_change_type,
                        ),
                    )
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
