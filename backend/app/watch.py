"""Minimal STRATUS Watch (V2.3E).

Answers exactly one consumer intent: "STRATUS, keep watching this for me."
Deliberately NOT a portfolio, NOT a watchlist-management product, NOT a
notification-rule builder, NOT a subscription feature, NOT Personal
Learning -- a Watch is durable, explicit, factual user intent, nothing
else. Notification-worthiness of a change is a separate, later decision
(the notification-quality block) -- this module has no opinion on it and
never triggers a push itself.

Mirrors notifications.py's own module shape: an in-memory dict always
present (byte-for-byte in-memory behavior when persistence is disabled,
matching every existing store's posture in this codebase), a durable
SQLite-backed mirror layered on top only when
config.memory_persistence_enabled() is true -- reusing that one existing
flag rather than inventing a second toggle. Deliberately independent of
live_stock_tickers()/lifecycle tracking (unlike _revision_store/
_user_knowledge_store in logan_feed.py) -- a user can watch any opportunity
they can see, not only a live-tracked stock, so this module's own state
is never reset by logan_feed.reset_pipeline_state().
"""

from datetime import datetime, timezone
from typing import Optional

from .config import memory_persistence_enabled, watch_store_db_path
from .watch_store import Watch, WatchStore

_watches: dict[tuple[str, str], Watch] = {}
_store: Optional[WatchStore] = None


def _get_store() -> Optional[WatchStore]:
    """Lazily constructs (and loads from) the durable store on first use
    when persistence is enabled; a no-op returning None otherwise. Mirrors
    notifications.py's own _get_store() exactly."""
    global _store
    if not memory_persistence_enabled():
        return None
    if _store is None:
        _store = WatchStore(watch_store_db_path())
        _watches.clear()
        for watch in _store.load_all():
            _watches[(watch.user_id, watch.entity_id)] = watch
    return _store


def create_watch(user_id: str, entity_id: str) -> tuple[Watch, bool]:
    """Idempotent: a repeat create for an already-watched entity returns the
    existing Watch unchanged -- never a duplicate record, never a second
    durable write. Returns (watch, created_new) so the caller (main.py's
    route) can tell whether this specific call is the one that should
    produce watch_created telemetry -- a repeat call must never emit it
    again."""
    store = _get_store()
    key = (user_id, entity_id)
    existing = _watches.get(key)
    if existing is not None:
        return existing, False
    watch = Watch(
        user_id=user_id, entity_id=entity_id, created_at=datetime.now(timezone.utc)
    )
    _watches[key] = watch
    if store is not None:
        store.save(watch)
    return watch, True


def remove_watch(user_id: str, entity_id: str) -> bool:
    """Returns True iff a watch genuinely existed and was removed -- False
    for a repeat/no-op removal, so the caller can tell whether this call
    should produce watch_removed telemetry."""
    key = (user_id, entity_id)
    existed = _watches.pop(key, None) is not None
    store = _get_store()
    if store is not None:
        store.delete(user_id, entity_id)
    return existed


def is_watched(user_id: str, entity_id: str) -> bool:
    """Pure read -- never mutates, never itself creates or removes a watch.
    A provider outage/degraded poll has no bearing on this at all: Watch
    represents user intent, not current provider availability, and this
    function never consults provider state."""
    _get_store()  # ensures the cache reflects durable state after a reset
    return (user_id, entity_id) in _watches


def list_watches(user_id: str) -> list[Watch]:
    """Every current watch for `user_id`, for the optional lightweight
    Watching list -- never another user's watches (see this module's own
    (user_id, entity_id) keying)."""
    _get_store()
    return [w for w in _watches.values() if w.user_id == user_id]


def purge_user(user_id: str) -> None:
    """The Watch half of purge_user_data() (see account_lifecycle.py) --
    removes every watch for `user_id`, across every entity. Named to match
    logan_feed.purge_user()/notifications.purge_user()'s established
    convention."""
    for key in [k for k in _watches if k[0] == user_id]:
        del _watches[key]
    store = _get_store()
    if store is not None:
        store.delete_user(user_id)


def reset_watch_state() -> None:
    """Test-only (and general-purpose "start over") hook, mirroring
    reset_notification_state(). Releases the durable store's SQLite
    connection (a no-op when persistence is disabled) without touching the
    underlying file -- the next call reconstructs the store and reloads
    whatever was durably saved, simulating a real process restart."""
    global _store
    _watches.clear()
    if _store is not None:
        _store.close()
    _store = None
