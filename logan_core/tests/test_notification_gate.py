"""Stock Opportunity Logic V2.4A -- Notification Hygiene & Repeat-Alert
Suppression. Pure unit tests for decide_notification
(opportunity_lifecycle/notification_gate.py). No backend/SQLite/Orchestrator
involved -- see backend/tests/test_notification_hygiene.py for the
wired-through-backend tests.
"""

from datetime import datetime, timedelta, timezone

from logan_core.opportunity_lifecycle import (
    NOTIFICATION_COOLDOWN,
    UserOpportunityKnowledge,
    decide_notification,
)

NOW = datetime(2026, 8, 29, 12, 0, 0, tzinfo=timezone.utc)


def _knowledge(
    notified_revision=None, notified_at=None, notified_change_type=None
) -> UserOpportunityKnowledge:
    return UserOpportunityKnowledge(
        user_id="user-a",
        entity_id="NVDA",
        last_notified_revision=notified_revision,
        last_notified_at=notified_at,
        last_notified_change_type=notified_change_type,
        updated_at=NOW,
    )


def test_no_lifecycle_tracking_is_no_material_delta():
    result = decide_notification(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=None,
        is_notification_worthy=True,
        change_type="confidence_increased",
        knowledge=None,
        provider_degraded=False,
        now=NOW,
    )
    assert result.should_notify is False
    assert result.reason == "no_material_delta"


def test_not_notification_worthy_this_poll_is_no_material_delta():
    result = decide_notification(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=4,
        is_notification_worthy=False,
        change_type="none",
        knowledge=None,
        provider_degraded=False,
        now=NOW,
    )
    assert result.should_notify is False
    assert result.reason == "no_material_delta"


def test_first_ever_notification_worthy_revision_notifies():
    result = decide_notification(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=4,
        is_notification_worthy=True,
        change_type="confidence_increased",
        knowledge=None,
        provider_degraded=False,
        now=NOW,
    )
    assert result.should_notify is True
    assert result.reason == "new_material_revision"


def test_same_revision_already_notified_is_suppressed():
    result = decide_notification(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=4,
        is_notification_worthy=True,
        change_type="confidence_increased",
        knowledge=_knowledge(
            notified_revision=4,
            notified_at=NOW,
            notified_change_type="confidence_increased",
        ),
        provider_degraded=False,
        now=NOW,
    )
    assert result.should_notify is False
    assert result.reason == "same_revision_suppressed"


def test_older_revision_than_already_notified_is_suppressed():
    """Defensive: a revision at or below the already-notified high-water
    mark must never re-notify, even if somehow presented again."""
    result = decide_notification(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=3,
        is_notification_worthy=True,
        change_type="confidence_increased",
        knowledge=_knowledge(
            notified_revision=4,
            notified_at=NOW,
            notified_change_type="confidence_increased",
        ),
        provider_degraded=False,
        now=NOW,
    )
    assert result.should_notify is False
    assert result.reason == "same_revision_suppressed"


def test_newer_revision_past_cooldown_notifies():
    result = decide_notification(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=5,
        is_notification_worthy=True,
        change_type="confidence_increased",
        knowledge=_knowledge(
            notified_revision=4,
            notified_at=NOW - NOTIFICATION_COOLDOWN - timedelta(minutes=1),
            notified_change_type="confidence_increased",
        ),
        provider_degraded=False,
        now=NOW,
    )
    assert result.should_notify is True
    assert result.reason == "new_material_revision"


def test_newer_revision_same_change_type_within_cooldown_is_suppressed():
    """The core rapid-churn case: revision 6 (strengthening) already
    notified 3 minutes ago; revision 7, also strengthening, must not
    re-alert."""
    result = decide_notification(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=7,
        is_notification_worthy=True,
        change_type="trajectory_strengthening",
        knowledge=_knowledge(
            notified_revision=6,
            notified_at=NOW - timedelta(minutes=3),
            notified_change_type="trajectory_strengthening",
        ),
        provider_degraded=False,
        now=NOW,
    )
    assert result.should_notify is False
    assert result.reason == "cooldown_suppressed"


def test_newer_revision_different_change_type_within_cooldown_still_notifies():
    """A genuine reversal must never be hidden by the cooldown, no matter
    how soon after the last (different-kind) notification it happens."""
    result = decide_notification(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=8,
        is_notification_worthy=True,
        change_type="trajectory_reversing",
        knowledge=_knowledge(
            notified_revision=7,
            notified_at=NOW - timedelta(minutes=1),
            notified_change_type="trajectory_strengthening",
        ),
        provider_degraded=False,
        now=NOW,
    )
    assert result.should_notify is True
    assert result.reason == "new_material_revision"


def test_provider_degraded_suppresses_regardless_of_everything_else():
    """Even a genuinely notification-worthy, never-before-notified,
    past-cooldown revision must not fire if this poll's own data was
    degraded -- a real material fact should never be confused with a data
    outage, so the caller passing provider_degraded=True here always wins."""
    result = decide_notification(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=9,
        is_notification_worthy=True,
        change_type="trajectory_reversing",
        knowledge=None,
        provider_degraded=True,
        now=NOW,
    )
    assert result.should_notify is False
    assert result.reason == "provider_degraded_suppressed"


def test_exact_cooldown_boundary_has_elapsed_not_suppressed():
    """(now - last_notified_at) == NOTIFICATION_COOLDOWN exactly means the
    cooldown has fully elapsed (strict less-than is the "still active"
    condition) -- deterministic either way, this pins down which side of
    the boundary wins."""
    result = decide_notification(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=6,
        is_notification_worthy=True,
        change_type="confidence_increased",
        knowledge=_knowledge(
            notified_revision=5,
            notified_at=NOW - NOTIFICATION_COOLDOWN,
            notified_change_type="confidence_increased",
        ),
        provider_degraded=False,
        now=NOW,
    )
    assert result.should_notify is True
    assert result.reason == "new_material_revision"


def test_just_inside_cooldown_boundary_is_suppressed():
    result = decide_notification(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=6,
        is_notification_worthy=True,
        change_type="confidence_increased",
        knowledge=_knowledge(
            notified_revision=5,
            notified_at=NOW - NOTIFICATION_COOLDOWN + timedelta(seconds=1),
            notified_change_type="confidence_increased",
        ),
        provider_degraded=False,
        now=NOW,
    )
    assert result.should_notify is False
    assert result.reason == "cooldown_suppressed"


def test_user_isolation_is_reflected_in_output():
    """Pure/stateless -- isolation is the caller's responsibility (passing
    each user's own knowledge); this just proves the output never swaps
    the given user_id."""
    result_a = decide_notification(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=4,
        is_notification_worthy=True,
        change_type="confidence_increased",
        knowledge=_knowledge(
            notified_revision=4,
            notified_at=NOW,
            notified_change_type="confidence_increased",
        ),
        provider_degraded=False,
        now=NOW,
    )
    result_b = decide_notification(
        entity_id="NVDA",
        user_id="user-b",
        current_revision=4,
        is_notification_worthy=True,
        change_type="confidence_increased",
        knowledge=None,
        provider_degraded=False,
        now=NOW,
    )
    assert result_a.user_id == "user-a"
    assert result_a.should_notify is False  # already notified for revision 4
    assert result_b.user_id == "user-b"
    assert result_b.should_notify is True  # never notified before
