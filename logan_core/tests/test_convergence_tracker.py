"""Sprint 3.6.7 Block 2 -- StockConvergenceTracker unit tests.

Covers the registered STOCK_CONVERGENCE_MULTI_SOURCE fire condition
(TRIGGER_REGISTRY_STOCKS.md: >=3 distinct source types within a 30-minute
window) in isolation from the rest of the pipeline: window-boundary behavior,
duplicate/repeated-polling suppression, repeated-alert suppression for one
active episode, and provenance preservation. Pipeline-level (World Model +
Orchestrator merge) coverage lives in test_pipeline_convergence.py.
"""

from datetime import datetime, timedelta
from uuid import uuid4

from logan_core.contracts import TriggerEvent
from logan_core.convergence import (
    CONVERGENCE_WINDOW,
    STOCK_CONVERGENCE_MULTI_SOURCE,
    StockConvergenceTracker,
)


def _trigger(
    entity_id: str,
    trigger_code: str,
    event_timestamp: datetime,
    source_id: str = "fmp",
    originating_signal_ids=None,
) -> TriggerEvent:
    return TriggerEvent(
        trigger_id=uuid4(),
        trigger_code=trigger_code,
        trigger_class="catalyst",
        trigger_type="test",
        trigger_status="confirmed",
        domain="stocks",
        affected_entity_id=entity_id,
        direction="positive",
        raw_magnitude=1.0,
        confidence_contribution=0.1,
        originating_signal_ids=originating_signal_ids or [uuid4()],
        source_id=source_id,
        source_name=source_id,
        event_timestamp=event_timestamp,
        detected_timestamp=event_timestamp,
    )


def test_fewer_than_three_distinct_types_does_not_fire(now):
    tracker = StockConvergenceTracker()
    r1 = tracker.observe(
        _trigger("NVDA", "STOCK_EARNINGS_BEAT", now), "earnings_signal"
    )
    r2 = tracker.observe(
        _trigger("NVDA", "STOCK_PRICE_MOVE_SIGNIFICANT", now + timedelta(minutes=5)),
        "price_change",
    )
    assert r1 is None
    assert r2 is None


def test_three_distinct_types_within_window_fires(now):
    tracker = StockConvergenceTracker()
    tracker.observe(_trigger("NVDA", "STOCK_EARNINGS_BEAT", now), "earnings_signal")
    tracker.observe(
        _trigger("NVDA", "STOCK_PRICE_MOVE_SIGNIFICANT", now + timedelta(minutes=5)),
        "price_change",
    )
    result = tracker.observe(
        _trigger("NVDA", "STOCK_ANALYST_UPGRADE", now + timedelta(minutes=10)),
        "analyst_change",
    )
    assert result is not None
    assert result.trigger_code == STOCK_CONVERGENCE_MULTI_SOURCE
    assert result.affected_entity_id == "NVDA"
    assert result.confidence_contribution == 0.20
    assert result.context["source_count"] == 3
    assert set(result.context["sources"]) == {
        "earnings_signal",
        "price_change",
        "analyst_change",
    }


def test_different_entities_are_tracked_independently(now):
    tracker = StockConvergenceTracker()
    tracker.observe(_trigger("NVDA", "STOCK_EARNINGS_BEAT", now), "earnings_signal")
    tracker.observe(
        _trigger("NVDA", "STOCK_PRICE_MOVE_SIGNIFICANT", now), "price_change"
    )
    # A third distinct type, but for a different entity -- must not count
    # toward NVDA's convergence.
    result = tracker.observe(
        _trigger("TSLA", "STOCK_ANALYST_UPGRADE", now), "analyst_change"
    )
    assert result is None


# --- Window boundary --------------------------------------------------


def test_signal_outside_window_does_not_count_toward_convergence(now):
    tracker = StockConvergenceTracker()
    tracker.observe(_trigger("NVDA", "STOCK_EARNINGS_BEAT", now), "earnings_signal")
    tracker.observe(
        _trigger("NVDA", "STOCK_PRICE_MOVE_SIGNIFICANT", now + timedelta(minutes=5)),
        "price_change",
    )
    # The third distinct signal arrives after the first has aged out of the
    # 30-minute window (relative to this observation) -- only 2 remain active.
    result = tracker.observe(
        _trigger(
            "NVDA",
            "STOCK_ANALYST_UPGRADE",
            now + CONVERGENCE_WINDOW + timedelta(minutes=1),
        ),
        "analyst_change",
    )
    assert result is None


def test_signal_just_inside_window_still_counts(now):
    tracker = StockConvergenceTracker()
    tracker.observe(_trigger("NVDA", "STOCK_EARNINGS_BEAT", now), "earnings_signal")
    tracker.observe(
        _trigger("NVDA", "STOCK_PRICE_MOVE_SIGNIFICANT", now + timedelta(minutes=5)),
        "price_change",
    )
    result = tracker.observe(
        _trigger(
            "NVDA",
            "STOCK_ANALYST_UPGRADE",
            now + CONVERGENCE_WINDOW - timedelta(seconds=1),
        ),
        "analyst_change",
    )
    assert result is not None


def test_episode_lapses_and_can_reform_after_window_expires(now):
    tracker = StockConvergenceTracker()
    tracker.observe(_trigger("NVDA", "STOCK_EARNINGS_BEAT", now), "earnings_signal")
    tracker.observe(
        _trigger("NVDA", "STOCK_PRICE_MOVE_SIGNIFICANT", now + timedelta(minutes=5)),
        "price_change",
    )
    first = tracker.observe(
        _trigger("NVDA", "STOCK_ANALYST_UPGRADE", now + timedelta(minutes=10)),
        "analyst_change",
    )
    assert first is not None

    # Push far enough forward that everything ages out, dropping back below 3.
    lapsed = tracker.observe(
        _trigger(
            "NVDA",
            "STOCK_ANALYST_UPGRADE",
            now + CONVERGENCE_WINDOW + timedelta(hours=1),
        ),
        "analyst_change",
    )
    assert lapsed is None

    # A fresh set of 3 distinct types reforms later -- a genuinely new episode.
    later = now + CONVERGENCE_WINDOW + timedelta(hours=1, minutes=5)
    tracker.observe(_trigger("NVDA", "STOCK_EARNINGS_BEAT", later), "earnings_signal")
    reformed = tracker.observe(
        _trigger("NVDA", "STOCK_PRICE_MOVE_SIGNIFICANT", later + timedelta(minutes=1)),
        "price_change",
    )
    assert reformed is not None
    assert reformed.trigger_id != first.trigger_id


# --- Duplicate / repeated-polling suppression --------------------------


def test_repeated_polls_of_the_same_signal_type_never_reach_three_distinct(now):
    """Prevents repeated polling of one source from falsely satisfying
    convergence -- distinct source *types* are tracked as a set, so
    re-observing the same signal_type any number of times never manufactures
    a second or third distinct source on its own."""
    tracker = StockConvergenceTracker()
    result = None
    for minute in range(10):
        result = tracker.observe(
            _trigger(
                "NVDA",
                "STOCK_PRICE_MOVE_SIGNIFICANT",
                now + timedelta(minutes=minute),
            ),
            "price_change",
        )
    assert result is None


def test_repeated_active_episode_reuses_same_trigger_id_not_a_new_alert(now):
    """Once an episode is active, subsequent polls that keep observing the
    same already-converged signal set must describe the *same* ongoing
    episode (stable trigger_id/event_timestamp), not mint a fresh alert every
    poll."""
    tracker = StockConvergenceTracker()
    tracker.observe(_trigger("NVDA", "STOCK_EARNINGS_BEAT", now), "earnings_signal")
    tracker.observe(
        _trigger("NVDA", "STOCK_PRICE_MOVE_SIGNIFICANT", now + timedelta(minutes=5)),
        "price_change",
    )
    first = tracker.observe(
        _trigger("NVDA", "STOCK_ANALYST_UPGRADE", now + timedelta(minutes=10)),
        "analyst_change",
    )
    assert first is not None

    second = tracker.observe(
        _trigger("NVDA", "STOCK_PRICE_MOVE_SIGNIFICANT", now + timedelta(minutes=12)),
        "price_change",
    )
    assert second is not None
    assert second.trigger_id == first.trigger_id
    assert second.event_timestamp == first.event_timestamp
    # detected_timestamp is allowed to move forward -- it's still active "as
    # of now" -- but identity (trigger_id/event_timestamp) stays pinned.
    assert second.detected_timestamp >= first.detected_timestamp


def test_signature_change_starts_a_genuinely_new_episode(now):
    """A different qualifying combination of signal_types (not just the same
    set observed again) is a new episode, with its own identity."""
    tracker = StockConvergenceTracker()
    tracker.observe(_trigger("NVDA", "STOCK_EARNINGS_BEAT", now), "earnings_signal")
    tracker.observe(
        _trigger("NVDA", "STOCK_PRICE_MOVE_SIGNIFICANT", now + timedelta(minutes=1)),
        "price_change",
    )
    first = tracker.observe(
        _trigger("NVDA", "STOCK_ANALYST_UPGRADE", now + timedelta(minutes=2)),
        "analyst_change",
    )
    assert first is not None

    # earnings_signal ages out, a 4th distinct type (hypothetical) takes its
    # place -- the qualifying set is now {price_change, analyst_change,
    # social_sentiment}, genuinely different from before.
    later = now + CONVERGENCE_WINDOW + timedelta(minutes=1)
    tracker.observe(
        _trigger("NVDA", "STOCK_PRICE_MOVE_SIGNIFICANT", later), "price_change"
    )
    tracker.observe(
        _trigger("NVDA", "STOCK_ANALYST_UPGRADE", later + timedelta(minutes=1)),
        "analyst_change",
    )
    changed = tracker.observe(
        _trigger("NVDA", "HYPOTHETICAL_SOCIAL_SIGNAL", later + timedelta(minutes=2)),
        "social_sentiment",
    )
    assert changed is not None
    assert changed.trigger_id != first.trigger_id


# --- Provenance ----------------------------------------------------------


def test_provenance_preserves_contributing_originating_signal_ids(now):
    tracker = StockConvergenceTracker()
    earnings_signal_id = uuid4()
    price_signal_id = uuid4()
    grade_signal_id = uuid4()

    tracker.observe(
        _trigger(
            "NVDA",
            "STOCK_EARNINGS_BEAT",
            now,
            originating_signal_ids=[earnings_signal_id],
        ),
        "earnings_signal",
    )
    tracker.observe(
        _trigger(
            "NVDA",
            "STOCK_PRICE_MOVE_SIGNIFICANT",
            now + timedelta(minutes=1),
            originating_signal_ids=[price_signal_id],
        ),
        "price_change",
    )
    result = tracker.observe(
        _trigger(
            "NVDA",
            "STOCK_ANALYST_UPGRADE",
            now + timedelta(minutes=2),
            originating_signal_ids=[grade_signal_id],
        ),
        "analyst_change",
    )

    assert result is not None
    assert set(result.originating_signal_ids) == {
        earnings_signal_id,
        price_signal_id,
        grade_signal_id,
    }
    assert set(result.context["contributing_trigger_codes"]) == {
        "STOCK_EARNINGS_BEAT",
        "STOCK_PRICE_MOVE_SIGNIFICANT",
        "STOCK_ANALYST_UPGRADE",
    }


def test_decision_trace_explains_the_fire_condition(now):
    tracker = StockConvergenceTracker()
    tracker.observe(_trigger("NVDA", "STOCK_EARNINGS_BEAT", now), "earnings_signal")
    tracker.observe(
        _trigger("NVDA", "STOCK_PRICE_MOVE_SIGNIFICANT", now + timedelta(minutes=1)),
        "price_change",
    )
    result = tracker.observe(
        _trigger("NVDA", "STOCK_ANALYST_UPGRADE", now + timedelta(minutes=2)),
        "analyst_change",
    )
    assert result is not None
    assert len(result.decision_trace) == 1
    assert "3 distinct signal types" in result.decision_trace[0].rule
    assert result.decision_trace[0].layer == "convergence_tracker"
