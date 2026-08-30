"""Operational Beta Hardening Block 2 -- Controlled Exploration
(logan_core/exploration/engine.py). Pure unit tests against
apply_controlled_exploration() directly: hand-built PrioritizedItem +
AttentionRecommendation, no orchestrator, no AttentionState (removed by the
2026-08-30 Universe Manager V1a reconciliation -- see engine.py's own
module docstring). The pipeline-level wiring itself (orchestrator/
pipeline.py calling this right after PrioritizationEngine.prioritize()) is
proven separately in test_orchestrator's own suite additions. The newer
batch-level "at most one exploration placement among the top five"
mechanism (Blocks 12-14) is tested separately in
test_exploration_eligibility.py / test_exploration_placement.py.
"""

from datetime import datetime, timezone
from uuid import uuid4

from logan_core.contracts import AttentionRecommendation, Dimensions, PrioritizedItem
from logan_core.exploration import apply_controlled_exploration

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


def test_never_touches_a_non_background_item_with_no_dominant_dimension():
    event_id = uuid4()
    item = _item(event_id, visibility="primary")
    recommendation = _recommendation(
        event_id, personal_relevance=0.3, global_importance=0.3
    )
    result = apply_controlled_exploration(item, recommendation)
    assert result.visibility == "primary"
    assert result.attention_reason is None


def test_non_background_item_gets_personal_relevance_label_when_it_dominates():
    event_id = uuid4()
    item = _item(event_id, visibility="feed")
    recommendation = _recommendation(
        event_id, personal_relevance=0.7, global_importance=0.2
    )
    result = apply_controlled_exploration(item, recommendation)
    assert result.visibility == "feed"
    assert result.attention_reason == "personal_relevance"


def test_non_background_item_not_labeled_when_world_signal_dominates_instead():
    event_id = uuid4()
    item = _item(event_id, visibility="feed")
    recommendation = _recommendation(
        event_id, personal_relevance=0.2, global_importance=0.8
    )
    result = apply_controlled_exploration(item, recommendation)
    assert result.attention_reason is None


def test_background_item_not_recommended_is_never_promoted():
    event_id = uuid4()
    item = _item(event_id, visibility="background")
    recommendation = _recommendation(
        event_id, recommend=False, global_importance=0.9, risk=0.0
    )
    result = apply_controlled_exploration(item, recommendation)
    assert result.visibility == "background"
    assert result.attention_reason is None


def test_background_item_high_risk_is_never_promoted_even_with_strong_world_signal():
    event_id = uuid4()
    item = _item(event_id, visibility="background")
    recommendation = _recommendation(event_id, global_importance=0.9, risk=0.6)
    result = apply_controlled_exploration(item, recommendation)
    assert result.visibility == "background"
    assert result.attention_reason is None


def test_strong_world_signal_promotes_background_to_feed():
    event_id = uuid4()
    item = _item(event_id, visibility="background")
    recommendation = _recommendation(
        event_id, global_importance=0.75, risk=0.1, personal_relevance=0.0
    )
    result = apply_controlled_exploration(item, recommendation)
    assert result.visibility == "feed"
    assert result.attention_reason == "strong_world_signal"


def test_strong_world_signal_never_promotes_to_primary():
    event_id = uuid4()
    item = _item(event_id, visibility="background")
    recommendation = _recommendation(event_id, global_importance=0.99, risk=0.0)
    result = apply_controlled_exploration(item, recommendation)
    assert result.visibility == "feed"


def test_unseen_material_change_promotes_background_to_feed():
    event_id = uuid4()
    item = _item(event_id, visibility="background", is_new_for_user=True)
    recommendation = _recommendation(
        event_id, novelty=0.9, global_importance=0.2, risk=0.1
    )
    result = apply_controlled_exploration(item, recommendation)
    assert result.visibility == "feed"
    assert result.attention_reason == "unseen_material_change"


def test_high_novelty_but_not_new_for_user_does_not_qualify_as_unseen_material_change():
    event_id = uuid4()
    item = _item(event_id, visibility="background", is_new_for_user=False)
    recommendation = _recommendation(
        event_id, novelty=0.9, global_importance=0.2, risk=0.1
    )
    result = apply_controlled_exploration(item, recommendation)
    # No other reason applies (global_importance/novelty both below their
    # own promotion floors once is_new_for_user is false) -- the item stays
    # in background, proving is_new_for_user is actually checked rather
    # than novelty alone being sufficient.
    assert result.visibility == "background"
    assert result.attention_reason is None


def test_neither_reason_applies_leaves_item_in_background():
    """2026-08-30 reconciliation: the old third reason (discovery_allowance,
    a per-item rolling quota) was removed -- an eligible-but-unremarkable
    background item with neither strong_world_signal nor
    unseen_material_change now simply stays in background. The newer
    batch-level "at most one exploration slot among the top five" mechanism
    (exploration/placement.py) is what may still surface something like
    this, as a single per-refresh decision, not a per-item quota."""
    event_id = uuid4()
    item = _item(event_id, visibility="background")
    recommendation = _recommendation(
        event_id, global_importance=0.2, novelty=0.2, risk=0.1, personal_relevance=0.1
    )
    result = apply_controlled_exploration(item, recommendation)
    assert result.visibility == "background"
    assert result.attention_reason is None


def test_original_item_is_never_mutated_in_place():
    event_id = uuid4()
    item = _item(event_id, visibility="background")
    recommendation = _recommendation(event_id, global_importance=0.9, risk=0.1)
    apply_controlled_exploration(item, recommendation)
    assert item.visibility == "background"
    assert item.attention_reason is None
