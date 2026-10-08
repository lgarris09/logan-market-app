"""Universe Manager V1a Blocks 13/14 -- batch-level exploration placement
(logan_core/exploration/placement.py).
"""

from uuid import uuid4

from logan_core.contracts import ThesisMetadata
from logan_core.exploration.placement import (
    EXPLORATION_OBJECTIVE_STRENGTH,
    apply_exploration_placement,
)
from logan_core.thesis.diversity import ThesisCandidate


def _metadata(entity_id="AAPL", sector="Technology") -> ThesisMetadata:
    return ThesisMetadata(
        event_id=uuid4(),
        primary_entity_id=entity_id,
        sector=sector,
        primary_signal_family="earnings",
        market_driver_tag="EARNINGS_RESULT",
        thesis_state="developing",
    )


def _candidate(
    entity_id="AAPL", is_watched=False, objective_strength=0.5, rank=1
) -> ThesisCandidate:
    return ThesisCandidate(
        event_id=uuid4(),
        rank=rank,
        metadata=_metadata(entity_id=entity_id),
        is_watched=is_watched,
        objective_strength=objective_strength,
    )


def test_no_eligible_pool_places_nothing():
    top = [_candidate("AAPL")]
    result = apply_exploration_placement(top, [])
    assert result.placed_event_id is None
    assert result.reason is None
    assert result.opportunity_cost is None


def test_eligible_candidate_already_represented_by_entity_is_not_placed():
    top = [_candidate("AAPL", objective_strength=0.5)]
    eligible = [_candidate("AAPL", objective_strength=0.9)]  # same entity
    result = apply_exploration_placement(top, eligible)
    assert result.placed_event_id is None


def test_strong_distinct_eligible_candidate_is_placed():
    top = [_candidate("AAPL", objective_strength=0.5)]
    eligible = [_candidate("MSFT", objective_strength=0.6)]
    result = apply_exploration_placement(top, eligible)
    assert result.placed_event_id == eligible[0].event_id
    assert result.reason == EXPLORATION_OBJECTIVE_STRENGTH
    assert result.opportunity_cost is not None
    assert result.opportunity_cost.exploration_thesis_id == eligible[0].event_id
    assert result.opportunity_cost.displaced_thesis_id == top[0].event_id


def test_weaker_eligible_candidate_is_not_placed():
    top = [_candidate("AAPL", objective_strength=0.8)]
    eligible = [_candidate("MSFT", objective_strength=0.3)]
    result = apply_exploration_placement(top, eligible)
    assert result.placed_event_id is None


def test_watch_item_is_never_displaced():
    top = [_candidate("AAPL", is_watched=True, objective_strength=0.1)]
    eligible = [_candidate("MSFT", objective_strength=0.99)]
    result = apply_exploration_placement(top, eligible)
    assert result.placed_event_id is None


def test_only_the_weakest_non_watch_candidate_can_be_displaced():
    top = [
        _candidate("AAPL", is_watched=True, objective_strength=0.1),
        _candidate("GOOGL", objective_strength=0.4),
        _candidate("AMZN", objective_strength=0.9),
    ]
    eligible = [_candidate("MSFT", objective_strength=0.5)]
    result = apply_exploration_placement(top, eligible)
    assert result.placed_event_id == eligible[0].event_id
    assert result.opportunity_cost is not None
    assert (
        result.opportunity_cost.displaced_thesis_id == top[1].event_id
    )  # GOOGL, weakest non-Watch


def test_most_objectively_strong_eligible_candidate_is_chosen_when_several_qualify():
    top = [_candidate("AAPL", objective_strength=0.3)]
    eligible = [
        _candidate("MSFT", objective_strength=0.5),
        _candidate("GOOGL", objective_strength=0.7),
    ]
    result = apply_exploration_placement(top, eligible)
    assert result.placed_event_id == eligible[1].event_id  # GOOGL, the stronger one


def test_zero_placements_is_the_common_honest_case():
    top = [_candidate("AAPL", objective_strength=0.9)]
    eligible = [_candidate("MSFT", objective_strength=0.1)]
    result = apply_exploration_placement(top, eligible)
    assert result.placed_event_id is None
    assert result.reason is None


def test_placement_is_deterministic_across_repeated_calls():
    top = [_candidate("AAPL", objective_strength=0.5)]
    eligible = [_candidate("MSFT", objective_strength=0.6)]
    first = apply_exploration_placement(top, eligible)
    second = apply_exploration_placement(top, eligible)
    assert first.placed_event_id == second.placed_event_id


def test_opportunity_cost_trace_records_the_policy_version_and_timestamp():
    top = [_candidate("AAPL", objective_strength=0.5)]
    eligible = [_candidate("MSFT", objective_strength=0.6)]
    result = apply_exploration_placement(top, eligible)
    assert result.opportunity_cost is not None
    assert result.opportunity_cost.exploration_policy_version == result.policy_version
    assert result.opportunity_cost.recorded_at is not None


def test_no_non_watch_candidates_at_all_places_nothing():
    top = [_candidate("AAPL", is_watched=True, objective_strength=0.1)]
    eligible = [_candidate("MSFT", objective_strength=0.9)]
    result = apply_exploration_placement(top, eligible)
    assert result.placed_event_id is None
