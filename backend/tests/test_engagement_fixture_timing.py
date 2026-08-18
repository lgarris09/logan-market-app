"""Sprint 3.6.6I: engagement fixture timing fix.

_engagement_samples() previously gave every simulated sample the identical
`observed_at=now` timestamp. CommunityIntelligenceEngine.measure() floors
elapsed time at 0.25 hours when two samples appear simultaneous (its own
division-by-zero guard) -- with real fixture point-deltas divided by that
floor instead of a real elapsed interval, engagement_velocity was silently
inflated 4x for every entity, pushing lifecycle_state to "emerging" almost
universally regardless of whether the underlying delta was a real spike.
These tests prove the fix: samples now span a real elapsed window, and
CommunityIntelligenceEngine (untouched) computes velocity from that real
window instead of the floor artifact.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from backend.app.logan_feed import (
    _ENGAGEMENT_BY_ENTITY,
    ENGAGEMENT_SAMPLE_WINDOW,
    _engagement_samples,
    _spaced_timestamps,
)
from logan_core.community_intelligence import CommunityIntelligenceEngine
from logan_core.contracts import EnrichedEvent, Entity

NOW = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)


def _event(entity_id: str) -> EnrichedEvent:
    entity = Entity(
        entity_id=entity_id,
        entity_type="ticker",
        display_name=entity_id,
        domain="stocks",
    )
    return EnrichedEvent(
        event_id=uuid4(),
        signal_ids=[uuid4()],
        domain="stocks",
        is_new=True,
        entities=[entity],
        summary=f"{entity_id} test event",
        occurred_at=NOW,
        enriched_at=NOW,
    )


def test_samples_no_longer_share_an_identical_timestamp():
    """The actual bug: two samples both stamped `now` collapse elapsed time
    to (near) zero, hitting CommunityIntelligenceEngine's 0.25h floor."""
    samples = _engagement_samples("FED", NOW)
    assert len(samples) == 2
    assert samples[0].observed_at != samples[1].observed_at


def test_samples_span_exactly_the_engagement_sample_window():
    samples = _engagement_samples("FED", NOW)
    elapsed = samples[-1].observed_at - samples[0].observed_at
    assert elapsed == ENGAGEMENT_SAMPLE_WINDOW


def test_most_recent_sample_is_anchored_to_now():
    """The last sample represents "right now" -- earlier samples represent
    the past, not the other way around."""
    samples = _engagement_samples("FED", NOW)
    assert samples[-1].observed_at == NOW
    assert samples[0].observed_at < NOW


def test_spaced_timestamps_single_point_is_safe_and_returns_now():
    """A single reading has no interval to span -- must not divide by zero,
    and the one timestamp represents "now", not some arbitrary past point."""
    result = _spaced_timestamps(NOW, 1, ENGAGEMENT_SAMPLE_WINDOW)
    assert result == [NOW]


def test_spaced_timestamps_multi_point_fixture_is_evenly_spaced():
    """Today's real fixtures always have exactly 2 points, but the spacing
    logic is written generally -- proves N>2 spacing directly, independent
    of the entity fixture lookup."""
    window = timedelta(hours=3)
    result = _spaced_timestamps(NOW, 4, window)

    assert len(result) == 4
    assert result[0] == NOW - window
    assert result[-1] == NOW
    gaps = [result[i + 1] - result[i] for i in range(len(result) - 1)]
    assert all(gap == timedelta(hours=1) for gap in gaps)  # 3h / (4-1) = 1h each


def test_spaced_timestamps_two_point_spans_the_full_window_exactly():
    result = _spaced_timestamps(NOW, 2, ENGAGEMENT_SAMPLE_WINDOW)
    assert result[0] == NOW - ENGAGEMENT_SAMPLE_WINDOW
    assert result[1] == NOW


def test_zero_elapsed_floor_artifact_is_no_longer_possible_for_real_fixtures():
    """The root cause required two samples sharing one timestamp. Every real
    fixture entity now produces strictly increasing, distinct timestamps --
    that precondition can no longer occur."""
    for entity_id in _ENGAGEMENT_BY_ENTITY:
        samples = _engagement_samples(entity_id, NOW)
        timestamps = [s.observed_at for s in samples]
        assert len(set(timestamps)) == len(timestamps), (
            f"{entity_id}: duplicate observed_at timestamps would recreate "
            f"the 0.25h floor artifact"
        )
        assert timestamps == sorted(timestamps)


def test_fixture_data_values_are_unchanged_by_the_timing_fix():
    """This is a timing fix only -- the (volume, unique_users, saves_shares,
    questions) fixture values themselves must be untouched."""
    for entity_id, points in _ENGAGEMENT_BY_ENTITY.items():
        samples = _engagement_samples(entity_id, NOW)
        actual_points = [
            (s.volume_at_point, s.unique_users, s.saves_shares, s.questions)
            for s in samples
        ]
        assert actual_points == points


def test_engagement_velocity_reflects_real_elapsed_time_not_the_floor_artifact():
    """End-to-end through the real, unmodified CommunityIntelligenceEngine:
    NFL's fixture points are (5, 9) volume -- a real delta of 4 over the real
    1-hour window is velocity=4.0, not the floor-inflated 16.0 the old
    same-timestamp samples produced ((9-5)/0.25 = 16.0). velocity=4.0 does
    NOT clear the emerging threshold (>5) -- this is the exact case that
    flips NFL's lifecycle_state as a direct result of the timing fix, not a
    threshold change (LIFECYCLE_URGENCY/the >5 threshold are untouched).
    """
    engine = CommunityIntelligenceEngine()
    samples = _engagement_samples("NFL", NOW)
    signal = engine.measure(_event("NFL"), samples, now=NOW)

    assert signal.engagement_velocity == 4.0  # (9 - 5) / 1.0 hour
    assert signal.engagement_velocity != 16.0  # the old floor-inflated value
    assert signal.lifecycle_state == "peak"  # 4.0 is not > 5


def test_engagement_velocity_for_a_genuine_high_delta_entity_still_emerges():
    """Fixing the timing artifact must not turn every entity non-emerging --
    a genuinely large real delta (TSLA: 10 -> 40) still clears the real,
    untouched >5 threshold over a real 1-hour window."""
    engine = CommunityIntelligenceEngine()
    samples = _engagement_samples("TSLA", NOW)
    signal = engine.measure(_event("TSLA"), samples, now=NOW)

    assert signal.engagement_velocity == 30.0  # (40 - 10) / 1.0 hour
    assert signal.lifecycle_state == "emerging"
