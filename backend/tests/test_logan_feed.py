"""BATCH-1 (V3.1.4) required tests for the public demo-feed response:
internal ranking fields must never serialize publicly, and the feed must
remain deterministic.
"""

from backend.app.logan_feed import FeedItem, reset_pipeline_state, run_demo_feed


def test_feed_item_has_no_internal_score_fields():
    field_names = set(FeedItem.model_fields.keys())
    assert "priority_score" not in field_names
    assert "internal_rank_score" not in field_names
    assert "rank" in field_names


def test_feed_response_serializes_without_internal_score_fields():
    result = run_demo_feed()
    assert len(result.items) > 0
    payload = result.model_dump()
    for item in payload["items"]:
        assert "priority_score" not in item
        assert "internal_rank_score" not in item


def test_feed_rank_is_sequential_starting_at_one():
    result = run_demo_feed()
    ranks = [item.rank for item in result.items]
    assert ranks == list(range(1, len(result.items) + 1))


def test_feed_is_deterministic_across_runs():
    """Same simulated fixtures, same Orchestrator logic -> same entity order
    every time (no wall-clock-dependent or random tie-breaking).

    Resets pipeline state between the two calls: the Orchestrator now
    persists *across* calls (the fix for event_ids randomizing on every
    request), so a second call within the dedup window legitimately
    corroborates the first rather than recomputing identically -- see
    test_opportunities_matches_demo_feed_pipeline_output's comment for the
    full explanation. This test's actual intent (no *hidden* randomness/
    time-dependency) needs both calls isolated from that new, deliberate
    persistence behavior to check cleanly.
    """
    reset_pipeline_state()
    first = run_demo_feed()
    reset_pipeline_state()
    second = run_demo_feed()
    assert [item.entity_id for item in first.items] == [
        item.entity_id for item in second.items
    ]
    assert [item.rank for item in first.items] == [item.rank for item in second.items]


def test_feed_returns_all_eleven_simulated_entities():
    result = run_demo_feed()
    assert len(result.items) == 11
