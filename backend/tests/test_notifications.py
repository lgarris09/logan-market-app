"""Backend-level tests for the notification/attention-state fix (owner-
approved persistent-Orchestrator change -- see logan_feed.py's module
docstring for the full root-cause writeup): the first response for a user is
notification-silent, and repeated observations of the same underlying
opportunities do not re-notify. The event-identity-vs-user-review distinction
itself (a genuinely new event staying flagged independent of a reviewed one)
is covered at the PrioritizationEngine unit level in
logan_core/tests/test_prioritization.py -- these tests cover what's specific
to this adapter layer: the first-load baseline and the real fixture pipeline
staying stable across requests.
"""

from backend.app.logan_feed import (
    _run_feed_pipeline,
    mark_notifications_reviewed,
    reset_pipeline_state,
)


def test_first_load_is_notification_silent():
    reset_pipeline_state()
    items, _ = _run_feed_pipeline()
    assert len(items) == 11
    assert all(item.is_new_for_user is False for item in items)


def test_repeated_request_does_not_re_notify():
    """Same underlying opportunities, requested twice -- the second request
    must not re-flag anything as new, and must keep the same event_ids (the
    root-cause fix this feature depends on).
    """
    reset_pipeline_state()
    first_items, _ = _run_feed_pipeline()
    second_items, _ = _run_feed_pipeline()
    assert {item.event_id for item in first_items} == {
        item.event_id for item in second_items
    }
    assert all(item.is_new_for_user is False for item in second_items)


def test_mark_notifications_reviewed_is_reachable_from_the_adapter_layer():
    """Smoke test for the function backend/app/main.py's
    POST /v1/notifications/review route calls -- confirms it runs against
    real event_ids from a real pipeline run without raising. (Proving a
    genuinely new event's badge clears end-to-end isn't possible against the
    static demo fixtures without inventing data; that distinction is tested
    directly at the PrioritizationEngine level instead.)
    """
    reset_pipeline_state()
    items, _ = _run_feed_pipeline()
    mark_notifications_reviewed([item.event_id for item in items])
