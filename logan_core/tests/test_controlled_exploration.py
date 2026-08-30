"""Operational Beta Hardening Block 2 -- Controlled Exploration
(logan_core/exploration/engine.py). Pure unit tests against
apply_controlled_exploration() directly: hand-built PrioritizedItem +
AttentionRecommendation + AttentionState, no orchestrator. The
pipeline-level wiring itself (orchestrator/pipeline.py calling this right
after PrioritizationEngine.prioritize()) is proven separately in
test_orchestrator's own suite additions.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from logan_core.contracts import (
    AttentionRecommendation,
    AttentionState,
    Dimensions,
    ExplorationGrantRecord,
    PrioritizedItem,
)
from logan_core.exploration import apply_controlled_exploration
from logan_core.exploration.engine import EXPLORATION_DAILY_LIMIT

NOW = datetime.now(timezone.utc)


def _dims(**overrides) -> Dimensions:
    defaults = dict(
        personal_relevance=0.1,
        global_importance=0.3,
        community_momentum=0.0,
        urgency=0.3,
        confidence=0.5,
        novelty=0.3,
        opportunity_magnitude=0.2,
        risk=0.1,
        actionability=0.2,
        connection_strength=0.0,
    )
    defaults.update(overrides)
    return Dimensions(**defaults)


def _recommendation(
    event_id, recommend=True, **dim_overrides
) -> AttentionRecommendation:
    return AttentionRecommendation(
        event_id=event_id,
        recommend=recommend,
        dimensions=_dims(**dim_overrides),
        internal_rank_score=0.4,
        recommended_at=NOW,
    )


def _item(event_id, visibility="background", is_new_for_user=True) -> PrioritizedItem:
    return PrioritizedItem(
        event_id=event_id,
        visibility=visibility,
        interruption="none",
        rank=1,
        changed_since_view=True,
        is_new_for_user=is_new_for_user,
        prioritized_at=NOW,
    )


def _state() -> AttentionState:
    return AttentionState(user_id="user-1", last_updated=NOW)


def test_never_touches_a_non_background_item_with_no_dominant_dimension():
    event_id = uuid4()
    item = _item(event_id, visibility="primary")
    recommendation = _recommendation(
        event_id, personal_relevance=0.3, global_importance=0.3
    )
    result = apply_controlled_exploration(item, recommendation, _state())
    assert result.visibility == "primary"
    assert result.attention_reason is None


def test_non_background_item_gets_personal_relevance_label_when_it_dominates():
    event_id = uuid4()
    item = _item(event_id, visibility="feed")
    recommendation = _recommendation(
        event_id, personal_relevance=0.7, global_importance=0.2
    )
    result = apply_controlled_exploration(item, recommendation, _state())
    assert result.visibility == "feed"
    assert result.attention_reason == "personal_relevance"


def test_non_background_item_not_labeled_when_world_signal_dominates_instead():
    event_id = uuid4()
    item = _item(event_id, visibility="feed")
    recommendation = _recommendation(
        event_id, personal_relevance=0.2, global_importance=0.8
    )
    result = apply_controlled_exploration(item, recommendation, _state())
    assert result.attention_reason is None


def test_background_item_not_recommended_is_never_promoted():
    event_id = uuid4()
    item = _item(event_id, visibility="background")
    recommendation = _recommendation(
        event_id, recommend=False, global_importance=0.9, risk=0.0
    )
    result = apply_controlled_exploration(item, recommendation, _state())
    assert result.visibility == "background"
    assert result.attention_reason is None


def test_background_item_high_risk_is_never_promoted_even_with_strong_world_signal():
    event_id = uuid4()
    item = _item(event_id, visibility="background")
    recommendation = _recommendation(event_id, global_importance=0.9, risk=0.6)
    result = apply_controlled_exploration(item, recommendation, _state())
    assert result.visibility == "background"
    assert result.attention_reason is None


def test_strong_world_signal_promotes_background_to_feed():
    event_id = uuid4()
    item = _item(event_id, visibility="background")
    recommendation = _recommendation(
        event_id, global_importance=0.75, risk=0.1, personal_relevance=0.0
    )
    result = apply_controlled_exploration(item, recommendation, _state())
    assert result.visibility == "feed"
    assert result.attention_reason == "strong_world_signal"


def test_strong_world_signal_never_promotes_to_primary():
    event_id = uuid4()
    item = _item(event_id, visibility="background")
    recommendation = _recommendation(event_id, global_importance=0.99, risk=0.0)
    result = apply_controlled_exploration(item, recommendation, _state())
    assert result.visibility == "feed"


def test_unseen_material_change_promotes_background_to_feed():
    event_id = uuid4()
    item = _item(event_id, visibility="background", is_new_for_user=True)
    recommendation = _recommendation(
        event_id, novelty=0.9, global_importance=0.2, risk=0.1
    )
    result = apply_controlled_exploration(item, recommendation, _state())
    assert result.visibility == "feed"
    assert result.attention_reason == "unseen_material_change"


def test_high_novelty_but_not_new_for_user_does_not_qualify_as_unseen_material_change():
    event_id = uuid4()
    item = _item(event_id, visibility="background", is_new_for_user=False)
    recommendation = _recommendation(
        event_id, novelty=0.9, global_importance=0.2, risk=0.1
    )
    result = apply_controlled_exploration(item, recommendation, _state())
    # Falls through to discovery_allowance (quota available), not
    # unseen_material_change -- proving is_new_for_user is actually checked.
    assert result.attention_reason != "unseen_material_change"


def test_discovery_allowance_used_when_no_other_reason_applies():
    event_id = uuid4()
    item = _item(event_id, visibility="background")
    recommendation = _recommendation(
        event_id, global_importance=0.2, novelty=0.2, risk=0.1, personal_relevance=0.1
    )
    state = _state()
    result = apply_controlled_exploration(item, recommendation, state)
    assert result.visibility == "feed"
    assert result.attention_reason == "discovery_allowance"
    assert len(state.exploration_grants) == 1
    assert state.exploration_grants[0].event_id == event_id


def test_discovery_allowance_is_bounded_by_the_daily_limit():
    state = _state()
    promoted_count = 0
    for _ in range(EXPLORATION_DAILY_LIMIT + 3):
        event_id = uuid4()
        item = _item(event_id, visibility="background")
        recommendation = _recommendation(
            event_id, global_importance=0.2, novelty=0.2, risk=0.1
        )
        result = apply_controlled_exploration(item, recommendation, state)
        if result.attention_reason == "discovery_allowance":
            promoted_count += 1
    assert promoted_count == EXPLORATION_DAILY_LIMIT


def test_discovery_allowance_quota_recovers_once_grants_age_out_of_the_window():
    state = _state()
    state.exploration_grants = [
        ExplorationGrantRecord(event_id=uuid4(), granted_at=NOW - timedelta(hours=25))
        for _ in range(EXPLORATION_DAILY_LIMIT)
    ]
    event_id = uuid4()
    item = _item(event_id, visibility="background")
    recommendation = _recommendation(
        event_id, global_importance=0.2, novelty=0.2, risk=0.1
    )
    result = apply_controlled_exploration(item, recommendation, state, now=NOW)
    assert result.attention_reason == "discovery_allowance"


def test_discovery_allowance_exhausted_leaves_item_in_background():
    state = _state()
    state.exploration_grants = [
        ExplorationGrantRecord(event_id=uuid4(), granted_at=NOW)
        for _ in range(EXPLORATION_DAILY_LIMIT)
    ]
    event_id = uuid4()
    item = _item(event_id, visibility="background")
    recommendation = _recommendation(
        event_id, global_importance=0.2, novelty=0.2, risk=0.1
    )
    result = apply_controlled_exploration(item, recommendation, state, now=NOW)
    assert result.visibility == "background"
    assert result.attention_reason is None


def test_strong_world_signal_takes_priority_over_discovery_allowance_and_uses_no_quota():
    event_id = uuid4()
    item = _item(event_id, visibility="background")
    recommendation = _recommendation(event_id, global_importance=0.9, risk=0.1)
    state = _state()
    apply_controlled_exploration(item, recommendation, state)
    assert state.exploration_grants == []


def test_original_item_is_never_mutated_in_place():
    event_id = uuid4()
    item = _item(event_id, visibility="background")
    recommendation = _recommendation(event_id, global_importance=0.9, risk=0.1)
    apply_controlled_exploration(item, recommendation, _state())
    assert item.visibility == "background"
    assert item.attention_reason is None
