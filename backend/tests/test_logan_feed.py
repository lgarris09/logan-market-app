"""BATCH-1 (V3.1.4) required tests for the public demo-feed response:
internal ranking fields must never serialize publicly, and the feed must
remain deterministic.
"""

from uuid import uuid4

import backend.app.logan_feed as logan_feed_module
from backend.app.logan_feed import (
    FeedItem,
    record_interaction,
    reset_pipeline_state,
    run_demo_feed,
)


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


def test_user_model_persists_across_repeated_requests():
    """Behavioral-personalization pass: the process-lifetime UserModel
    (`_get_user_model()`) must be seeded once and then rebuilt -- not
    reseeded from scratch -- on every subsequent `/v1/opportunities`-
    equivalent pipeline run, so repeated behavioral evidence recorded
    in between actually compounds instead of being lost.
    """
    reset_pipeline_state()
    run_demo_feed()
    seeded_model = logan_feed_module._user_model
    assert seeded_model is not None
    assert seeded_model.established_behaviors == []

    run_demo_feed()
    rebuilt_model = logan_feed_module._user_model
    assert rebuilt_model is not None
    # A later call must rebuild forward from the same instance -- not
    # silently reseed a brand-new one (`.build()` always increments
    # version by exactly 1 over its `base`).
    assert rebuilt_model.version == seeded_model.version + 1


def test_repeated_behavioral_evidence_compounds_into_persisted_user_model():
    """Two independent "interested"-intent interactions with the same
    (domain, entity) pair -- the minimal MIN_REPEAT_EVIDENCE=2 definition of
    "repeated, not isolated" -- recorded between two live pipeline requests
    must show up in the *next* request's persisted UserModel as an
    established_behaviors entry and an Interest(source="inferred"), without
    disturbing the explicit AI_SECTOR interest seeded at first load.
    """
    reset_pipeline_state()
    run_demo_feed()  # seeds the persisted UserModel

    record_interaction(
        event_id=uuid4(), entity_id="TSLA", domain="stocks", interaction_type="watch"
    )
    record_interaction(
        event_id=uuid4(), entity_id="TSLA", domain="stocks", interaction_type="watch"
    )

    run_demo_feed()  # folds the accumulated feedback_records into the model
    model = logan_feed_module._user_model
    assert model is not None

    behavior_labels = {b.label for b in model.established_behaviors}
    assert "engaged_with_TSLA" in behavior_labels

    inferred_topics = {i.topic for i in model.interests if i.source == "inferred"}
    assert "TSLA" in inferred_topics

    explicit_topics = {i.topic for i in model.interests if i.source == "explicit"}
    assert explicit_topics == {"AI_SECTOR"}


def test_single_interaction_does_not_create_inferred_preference():
    """One isolated interaction (even a strong "interested"-intent one) must
    not create a behavioral preference -- MIN_REPEAT_EVIDENCE=2 guards
    against treating a single click/save as an established pattern.
    """
    reset_pipeline_state()
    run_demo_feed()

    record_interaction(
        event_id=uuid4(), entity_id="OIL", domain="stocks", interaction_type="watch"
    )

    run_demo_feed()
    model = logan_feed_module._user_model
    assert model is not None
    assert "engaged_with_OIL" not in {b.label for b in model.established_behaviors}
    assert "OIL" not in {i.topic for i in model.interests if i.source == "inferred"}
