"""Stock Opportunity Logic V2.1 -- User Sync Gap. Pure unit tests: the
tracker's global revision counter (opportunity_lifecycle/tracker.py) and the
deterministic compute_user_sync_delta comparison (opportunity_lifecycle/
sync.py). No backend/SQLite/Orchestrator involved -- see
backend/tests/test_user_sync_integration.py for the wired-through-backend
tests (persistence, notification dispatch, record_interaction, Ask STRATUS
grounding).
"""

from datetime import datetime, timedelta, timezone

from logan_core.opportunity_lifecycle import (
    OpportunityLifecycleTracker,
    UserOpportunityKnowledge,
    compute_user_sync_delta,
)

NOW = datetime(2026, 8, 24, 12, 0, 0, tzinfo=timezone.utc)


def _tracker() -> OpportunityLifecycleTracker:
    return OpportunityLifecycleTracker()


# --- Global revision counter (tracker-level) --------------------------------


def test_first_observation_is_revision_one():
    tracker = _tracker()
    delta = tracker.observe(
        entity_id="NVDA",
        confidence_score=0.595,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW,
    )
    assert delta.previous_revision == 1
    assert delta.new_revision == 1


def test_repeated_unchanged_poll_does_not_advance_revision():
    tracker = _tracker()
    tracker.observe(
        entity_id="NVDA",
        confidence_score=0.595,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW,
    )
    delta = tracker.observe(
        entity_id="NVDA",
        confidence_score=0.595,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW + timedelta(minutes=1),
    )
    assert delta.change_type == "none"
    assert delta.previous_revision == 1
    assert delta.new_revision == 1


def test_meaningful_confidence_change_advances_revision_exactly_once():
    tracker = _tracker()
    tracker.observe(
        entity_id="NVDA",
        confidence_score=0.595,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW,
    )
    delta = tracker.observe(
        entity_id="NVDA",
        confidence_score=0.75,  # +0.155, well past CONFIDENCE_DELTA_THRESHOLD
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW + timedelta(hours=1),
    )
    assert delta.change_type == "confidence_increased"
    assert delta.previous_revision == 1
    assert delta.new_revision == 2

    # A further unchanged poll must not advance it again.
    delta2 = tracker.observe(
        entity_id="NVDA",
        confidence_score=0.75,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW + timedelta(hours=2),
    )
    assert delta2.change_type == "none"
    assert delta2.new_revision == 2


def test_personal_relevance_only_change_does_not_advance_global_revision():
    """The critical global/personal separation: one user's personal
    relevance crossing the threshold updates that user's own experience
    (is_meaningful=True, personal_relevance_changed=True) but must NEVER
    manufacture a new *global* revision -- a different user must see the
    identical revision number for the same real-world opportunity,
    regardless of what the first user's personalization did.
    """
    tracker = _tracker()
    tracker.observe(
        entity_id="NVDA",
        confidence_score=0.595,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.3,
        now=NOW,
    )
    delta = tracker.observe(
        entity_id="NVDA",
        confidence_score=0.595,  # unchanged
        trigger_codes=["STOCK_EARNINGS_BEAT"],  # unchanged
        user_id="user-a",
        personal_relevance=0.8,  # crosses PERSONAL_RELEVANCE_THRESHOLD (0.6)
        now=NOW + timedelta(hours=1),
    )
    assert delta.change_type == "personal_relevance_increased"
    assert delta.is_meaningful is True  # the card-update flag DOES fire
    assert delta.previous_revision == 1
    assert delta.new_revision == 1  # but the global revision does not move


def test_new_trigger_code_advances_revision():
    tracker = _tracker()
    tracker.observe(
        entity_id="NVDA",
        confidence_score=0.6,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW,
    )
    delta = tracker.observe(
        entity_id="NVDA",
        confidence_score=0.6,
        trigger_codes=["STOCK_EARNINGS_BEAT", "STOCK_ANALYST_UPGRADE"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW + timedelta(hours=1),
    )
    assert delta.change_type == "new_signal_appeared"
    assert delta.new_revision == 2


# --- compute_user_sync_delta (pure comparison) ------------------------------


def test_never_seen_or_notified_is_new_to_user():
    delta = compute_user_sync_delta(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=1,
        knowledge=None,
        now=NOW,
    )
    assert delta.status == "NEW_TO_USER"
    assert delta.is_new_or_updated_for_user is True


def test_seen_current_revision_is_up_to_date():
    knowledge = UserOpportunityKnowledge(
        user_id="user-a", entity_id="NVDA", last_seen_revision=2, updated_at=NOW
    )
    delta = compute_user_sync_delta(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=2,
        knowledge=knowledge,
        now=NOW,
    )
    assert delta.status == "UP_TO_DATE"
    assert delta.is_new_or_updated_for_user is False


def test_seen_older_revision_is_updated_since_seen():
    knowledge = UserOpportunityKnowledge(
        user_id="user-a", entity_id="NVDA", last_seen_revision=1, updated_at=NOW
    )
    delta = compute_user_sync_delta(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=3,
        knowledge=knowledge,
        now=NOW,
    )
    assert delta.status == "UPDATED_SINCE_SEEN"
    assert delta.is_new_or_updated_for_user is True


def test_notified_but_never_seen_is_notified_but_unseen():
    knowledge = UserOpportunityKnowledge(
        user_id="user-a",
        entity_id="NVDA",
        last_seen_revision=None,
        last_notified_revision=1,
        updated_at=NOW,
    )
    delta = compute_user_sync_delta(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=1,
        knowledge=knowledge,
        now=NOW,
    )
    assert delta.status == "NOTIFIED_BUT_UNSEEN"


def test_notified_at_a_revision_the_user_has_not_yet_seen_takes_priority():
    """Even when the user HAS seen an earlier revision, an unseen
    notification for a later revision must still surface as
    NOTIFIED_BUT_UNSEEN, not merely UPDATED_SINCE_SEEN -- "you have an
    unopened notification" is the more actionable, specific fact.
    """
    knowledge = UserOpportunityKnowledge(
        user_id="user-a",
        entity_id="NVDA",
        last_seen_revision=1,
        last_notified_revision=2,
        updated_at=NOW,
    )
    delta = compute_user_sync_delta(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=2,
        knowledge=knowledge,
        now=NOW,
    )
    assert delta.status == "NOTIFIED_BUT_UNSEEN"


def test_notified_and_since_seen_is_up_to_date_not_notified_but_unseen():
    knowledge = UserOpportunityKnowledge(
        user_id="user-a",
        entity_id="NVDA",
        last_seen_revision=2,
        last_notified_revision=2,
        updated_at=NOW,
    )
    delta = compute_user_sync_delta(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=2,
        knowledge=knowledge,
        now=NOW,
    )
    assert delta.status == "UP_TO_DATE"


def test_same_global_revision_different_users_different_sync_status():
    """The exact acceptance scenario: two users share identical market
    truth (current_revision=2 for both) but genuinely different sync
    results because their own knowledge pointers differ.
    """
    current_revision = 2
    user_a_knowledge = UserOpportunityKnowledge(
        user_id="user-a", entity_id="NVDA", last_seen_revision=2, updated_at=NOW
    )
    user_b_knowledge = None  # user B has never seen this opportunity at all

    delta_a = compute_user_sync_delta(
        entity_id="NVDA",
        user_id="user-a",
        current_revision=current_revision,
        knowledge=user_a_knowledge,
        now=NOW,
    )
    delta_b = compute_user_sync_delta(
        entity_id="NVDA",
        user_id="user-b",
        current_revision=current_revision,
        knowledge=user_b_knowledge,
        now=NOW,
    )

    assert delta_a.current_revision == delta_b.current_revision == 2
    assert delta_a.status == "UP_TO_DATE"
    assert delta_b.status == "NEW_TO_USER"
