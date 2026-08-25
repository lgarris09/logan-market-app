"""Stock Opportunity Logic V2 -- OpportunityLifecycleTracker. Pure unit
tests against the tracker directly (no Orchestrator/pipeline involved) --
see test_pipeline_lifecycle.py for the wired-through-Orchestrator
integration tests, and backend/tests/test_lifecycle_persistence.py for the
durable-storage tests.
"""

from datetime import datetime, timedelta, timezone

from logan_core.opportunity_lifecycle import (
    CONFIDENCE_DELTA_THRESHOLD,
    MAJOR_CONFIDENCE_DELTA_THRESHOLD,
    OpportunityLifecycleTracker,
)

NOW = datetime(2026, 8, 24, 12, 0, 0, tzinfo=timezone.utc)


def _tracker() -> OpportunityLifecycleTracker:
    return OpportunityLifecycleTracker()


# --- Appearance ---------------------------------------------------------


def test_first_observation_is_new_and_meaningful_and_notification_worthy():
    tracker = _tracker()
    delta = tracker.observe(
        entity_id="NVDA",
        confidence_score=0.595,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW,
    )
    assert delta.change_type == "new_opportunity"
    assert delta.is_meaningful is True
    assert delta.is_notification_worthy is True
    assert delta.new_state == "new"
    assert delta.thesis_age_hours == 0.0


# --- Repeated identical poll: no meaningful change ------------------------


def test_repeated_identical_poll_is_not_meaningful():
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
    assert delta.is_meaningful is False
    assert delta.is_notification_worthy is False
    # NEW glides to MONITORING on the very next observation even with zero
    # change -- an opportunity should not stay "new" forever.
    assert delta.new_state == "monitoring"


def test_app_reopened_many_times_produces_no_repeated_new_or_duplicate_meaningful_change():
    tracker = _tracker()
    tracker.observe(
        entity_id="NVDA",
        confidence_score=0.595,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW,
    )
    for i in range(10):
        delta = tracker.observe(
            entity_id="NVDA",
            confidence_score=0.595,
            trigger_codes=["STOCK_EARNINGS_BEAT"],
            user_id="user-a",
            personal_relevance=0.6,
            now=NOW + timedelta(minutes=i + 1),
        )
        assert delta.change_type != "new_opportunity"
        assert delta.is_meaningful is False


# --- Strengthening: confidence increase ------------------------------------


def test_confidence_increase_above_threshold_is_meaningful_and_notification_worthy():
    tracker = _tracker()
    tracker.observe(
        entity_id="NVDA",
        confidence_score=0.50,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW,
    )
    delta = tracker.observe(
        entity_id="NVDA",
        confidence_score=0.50 + CONFIDENCE_DELTA_THRESHOLD + 0.01,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW + timedelta(hours=1),
    )
    assert delta.change_type == "confidence_increased"
    assert delta.is_meaningful is True
    assert delta.is_notification_worthy is True


def test_confidence_increase_below_threshold_is_not_meaningful():
    tracker = _tracker()
    tracker.observe(
        entity_id="NVDA",
        confidence_score=0.50,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW,
    )
    delta = tracker.observe(
        entity_id="NVDA",
        confidence_score=0.50 + (CONFIDENCE_DELTA_THRESHOLD / 2),
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW + timedelta(hours=1),
    )
    assert delta.change_type == "none"
    assert delta.is_meaningful is False


def test_new_signal_appearing_is_meaningful_and_notification_worthy():
    """Analyst upgrade appears after an earlier earnings beat."""
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
        confidence_score=0.66,
        trigger_codes=["STOCK_EARNINGS_BEAT", "STOCK_ANALYST_UPGRADE"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW + timedelta(hours=2),
    )
    assert delta.change_type == "new_signal_appeared"
    assert delta.added_trigger_codes == ["STOCK_ANALYST_UPGRADE"]
    assert delta.is_meaningful is True
    assert delta.is_notification_worthy is True


def test_repeated_same_downgrade_does_nothing():
    tracker = _tracker()
    tracker.observe(
        entity_id="TSLA",
        confidence_score=0.45,
        trigger_codes=["STOCK_ANALYST_DOWNGRADE"],
        user_id="user-a",
        personal_relevance=0.5,
        now=NOW,
    )
    delta = tracker.observe(
        entity_id="TSLA",
        confidence_score=0.45,
        trigger_codes=["STOCK_ANALYST_DOWNGRADE"],
        user_id="user-a",
        personal_relevance=0.5,
        now=NOW + timedelta(hours=1),
    )
    assert delta.change_type == "none"
    assert delta.is_meaningful is False


def test_convergence_forming_is_meaningful_and_notification_worthy():
    tracker = _tracker()
    tracker.observe(
        entity_id="AAPL",
        confidence_score=0.55,
        trigger_codes=["STOCK_EARNINGS_BEAT", "STOCK_PRICE_MOVE_SIGNIFICANT"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW,
    )
    delta = tracker.observe(
        entity_id="AAPL",
        confidence_score=0.75,
        trigger_codes=[
            "STOCK_EARNINGS_BEAT",
            "STOCK_PRICE_MOVE_SIGNIFICANT",
            "STOCK_ANALYST_UPGRADE",
            "STOCK_CONVERGENCE_MULTI_SOURCE",
        ],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW + timedelta(hours=1),
    )
    assert delta.change_type == "convergence_formed"
    assert delta.new_state == "high_attention"
    assert delta.is_notification_worthy is True


# --- Stability: unchanged thesis ------------------------------------------


def test_unchanged_thesis_within_monitoring_window_stays_monitoring_not_meaningful():
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
        now=NOW + timedelta(hours=24),  # well under earnings' 72h monitoring window
    )
    assert delta.new_state == "monitoring"
    assert delta.is_meaningful is False


# --- Cooling / staleness / expiration (earnings: 72h / 240h / 720h) -------


def test_earnings_ages_to_cooling_after_monitoring_window():
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
        now=NOW + timedelta(hours=73),
    )
    assert delta.new_state == "cooling"
    assert delta.change_type == "aged_to_cooling"
    assert delta.is_meaningful is True  # card updates...
    assert delta.is_notification_worthy is False  # ...but never notifies


def test_cooling_does_not_repeat_meaningful_change_on_next_poll():
    tracker = _tracker()
    tracker.observe(
        entity_id="NVDA",
        confidence_score=0.595,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW,
    )
    tracker.observe(
        entity_id="NVDA",
        confidence_score=0.595,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW + timedelta(hours=73),
    )
    delta = tracker.observe(
        entity_id="NVDA",
        confidence_score=0.595,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW + timedelta(hours=74),
    )
    assert delta.new_state == "cooling"
    assert delta.change_type == "none"
    assert delta.is_meaningful is False


def test_earnings_ages_to_stale_after_stale_window():
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
        now=NOW + timedelta(hours=241),
    )
    assert delta.new_state == "stale"
    assert delta.change_type == "aged_to_stale"
    assert delta.is_notification_worthy is False


def test_earnings_expires_after_expire_window():
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
        now=NOW + timedelta(hours=721),
    )
    assert delta.new_state == "expired"
    assert delta.change_type == "aged_to_expired"
    assert delta.is_notification_worthy is False


def test_price_move_cools_much_faster_than_earnings():
    """Signal-specific decay: a price move's monitoring window (6h) is far
    shorter than earnings' (72h)."""
    tracker = _tracker()
    tracker.observe(
        entity_id="TSLA",
        confidence_score=0.5,
        trigger_codes=["STOCK_PRICE_MOVE_SIGNIFICANT"],
        user_id="user-a",
        personal_relevance=0.5,
        now=NOW,
    )
    delta = tracker.observe(
        entity_id="TSLA",
        confidence_score=0.5,
        trigger_codes=["STOCK_PRICE_MOVE_SIGNIFICANT"],
        user_id="user-a",
        personal_relevance=0.5,
        now=NOW + timedelta(hours=7),
    )
    assert delta.new_state == "cooling"


def test_earnings_plus_price_move_uses_the_longer_earnings_window():
    """The most generous active window governs -- a price-move signal
    attached alongside an earnings signal must not force the whole
    opportunity to cool on the price move's much shorter schedule."""
    tracker = _tracker()
    tracker.observe(
        entity_id="AAPL",
        confidence_score=0.6,
        trigger_codes=["STOCK_EARNINGS_BEAT", "STOCK_PRICE_MOVE_SIGNIFICANT"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW,
    )
    delta = tracker.observe(
        entity_id="AAPL",
        confidence_score=0.6,
        trigger_codes=["STOCK_EARNINGS_BEAT", "STOCK_PRICE_MOVE_SIGNIFICANT"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW + timedelta(hours=7),  # past price-move's own window, not earnings'
    )
    assert delta.new_state == "monitoring"  # earnings' 72h window still governs


# --- Reactivation -----------------------------------------------------------


def test_reactivation_after_cooling_is_meaningful_and_notification_worthy():
    tracker = _tracker()
    tracker.observe(
        entity_id="NVDA",
        confidence_score=0.595,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW,
    )
    tracker.observe(
        entity_id="NVDA",
        confidence_score=0.595,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW + timedelta(hours=73),  # ages to cooling
    )
    delta = tracker.observe(
        entity_id="NVDA",
        confidence_score=0.75,
        trigger_codes=["STOCK_EARNINGS_BEAT", "STOCK_ANALYST_UPGRADE"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW + timedelta(hours=80),
    )
    assert delta.change_type == "reactivated"
    assert delta.previous_state == "cooling"
    assert delta.new_state == "high_attention"
    assert delta.is_notification_worthy is True


# --- Major invalidation vs. modest weakening --------------------------------


def test_modest_confidence_decrease_is_meaningful_but_not_notification_worthy():
    tracker = _tracker()
    tracker.observe(
        entity_id="TSLA",
        confidence_score=0.60,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.5,
        now=NOW,
    )
    delta = tracker.observe(
        entity_id="TSLA",
        confidence_score=0.60 - (MAJOR_CONFIDENCE_DELTA_THRESHOLD - 0.01),
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.5,
        now=NOW + timedelta(hours=1),
    )
    assert delta.change_type == "confidence_decreased"
    assert delta.is_meaningful is True
    assert delta.is_notification_worthy is False


def test_major_confidence_decrease_is_notification_worthy():
    tracker = _tracker()
    tracker.observe(
        entity_id="TSLA",
        confidence_score=0.70,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.5,
        now=NOW,
    )
    delta = tracker.observe(
        entity_id="TSLA",
        confidence_score=0.70 - MAJOR_CONFIDENCE_DELTA_THRESHOLD - 0.01,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.5,
        now=NOW + timedelta(hours=1),
    )
    assert delta.change_type == "confidence_decreased"
    assert delta.is_meaningful is True
    assert delta.is_notification_worthy is True


# --- Per-user personal relevance vs. shared objective lifecycle -----------


def test_different_users_get_independent_personal_relevance_but_identical_objective_state():
    tracker = _tracker()
    tracker.observe(
        entity_id="NVDA",
        confidence_score=0.595,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW,
    )
    tracker.observe(
        entity_id="NVDA",
        confidence_score=0.595,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-b",
        personal_relevance=0.2,
        now=NOW,
    )
    # user-a's relevance rises sharply; user-b's doesn't move.
    delta_a = tracker.observe(
        entity_id="NVDA",
        confidence_score=0.595,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.75,
        now=NOW + timedelta(hours=1),
    )
    delta_b = tracker.observe(
        entity_id="NVDA",
        confidence_score=0.595,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-b",
        personal_relevance=0.2,
        now=NOW + timedelta(hours=1),
    )
    assert delta_a.personal_relevance_changed is True
    assert delta_a.change_type == "personal_relevance_increased"
    assert delta_b.personal_relevance_changed is False
    assert delta_b.change_type == "none"
    # Objective world facts (confidence, state) are identical for both --
    # personalization never changes the objective lifecycle.
    assert delta_a.new_confidence == delta_b.new_confidence


# --- Persistence primitives (load/export) -----------------------------------


def test_export_and_load_snapshot_round_trips_state():
    tracker = _tracker()
    tracker.observe(
        entity_id="NVDA",
        confidence_score=0.595,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW,
    )
    exported = tracker.export_snapshot("NVDA")
    assert exported is not None

    fresh_tracker = _tracker()
    fresh_tracker.load_snapshot(exported)
    # A restart-simulated tracker, rehydrated from the exported snapshot,
    # must not treat the next observation as brand new.
    delta = fresh_tracker.observe(
        entity_id="NVDA",
        confidence_score=0.595,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW + timedelta(hours=1),
    )
    assert delta.change_type != "new_opportunity"
    assert delta.is_meaningful is False
