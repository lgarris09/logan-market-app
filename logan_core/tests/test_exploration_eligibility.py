"""Universe Manager V1a Block 12 -- binary Exploration Eligibility
(logan_core/exploration/eligibility.py). Pure function tests only -- no
pipeline, no orchestrator.
"""

from logan_core.exploration.eligibility import (
    EVIDENCE_QUALITY_FLOOR,
    MATERIALITY_FLOOR,
    MAX_RISK,
    is_exploration_eligible,
)


def _eligible_kwargs(**overrides):
    defaults = dict(
        recommend=True,
        global_importance=MATERIALITY_FLOOR + 0.1,
        confidence=EVIDENCE_QUALITY_FLOOR + 0.1,
        risk=MAX_RISK - 0.1,
        freshness_state="FRESH",
        is_new_for_user=True,
        is_materially_revised=False,
        personal_relevance_state="unknown",
        has_active_suppression=False,
    )
    defaults.update(overrides)
    return defaults


def test_fully_qualifying_candidate_is_eligible():
    assert is_exploration_eligible(**_eligible_kwargs()) is True


def test_not_recommended_is_never_eligible():
    assert is_exploration_eligible(**_eligible_kwargs(recommend=False)) is False


def test_active_suppression_is_never_eligible():
    assert (
        is_exploration_eligible(**_eligible_kwargs(has_active_suppression=True))
        is False
    )


def test_high_personal_relevance_is_never_eligible():
    """Exploration exists specifically for low/unknown personal relevance --
    a highly personally-relevant item has no business in the exploration
    slot (it should already be surfacing through the ordinary path)."""
    assert (
        is_exploration_eligible(**_eligible_kwargs(personal_relevance_state="high"))
        is False
    )


def test_moderate_personal_relevance_is_never_eligible():
    assert (
        is_exploration_eligible(**_eligible_kwargs(personal_relevance_state="moderate"))
        is False
    )


def test_low_personal_relevance_is_eligible():
    assert (
        is_exploration_eligible(**_eligible_kwargs(personal_relevance_state="low"))
        is True
    )


def test_below_materiality_floor_is_never_eligible():
    assert (
        is_exploration_eligible(
            **_eligible_kwargs(global_importance=MATERIALITY_FLOOR - 0.01)
        )
        is False
    )


def test_below_evidence_quality_floor_is_never_eligible():
    assert (
        is_exploration_eligible(
            **_eligible_kwargs(confidence=EVIDENCE_QUALITY_FLOOR - 0.01)
        )
        is False
    )


def test_at_or_above_risk_ceiling_is_never_eligible():
    assert is_exploration_eligible(**_eligible_kwargs(risk=MAX_RISK)) is False


def test_non_fresh_data_is_never_eligible():
    for state in ("RECENTLY_OBSERVED", "STALE_WITHIN_GRACE", "UNAVAILABLE"):
        assert (
            is_exploration_eligible(**_eligible_kwargs(freshness_state=state)) is False
        )


def test_neither_new_nor_materially_revised_is_never_eligible():
    assert (
        is_exploration_eligible(
            **_eligible_kwargs(is_new_for_user=False, is_materially_revised=False)
        )
        is False
    )


def test_materially_revised_alone_satisfies_the_newness_requirement():
    assert (
        is_exploration_eligible(
            **_eligible_kwargs(is_new_for_user=False, is_materially_revised=True)
        )
        is True
    )


def test_never_requires_high_personalized_attention_a_circularity_check():
    """Block 12's own explicit non-circularity requirement: eligibility
    must never require the item's already-personalized attention judgment
    to be high -- it only ever reads objective fields plus a LOW/UNKNOWN
    personal-relevance confirmation. There is no "attention_judgment"
    parameter at all in this function's signature, which is itself the
    proof; this test documents that intent for future maintainers."""
    import inspect

    params = inspect.signature(is_exploration_eligible).parameters
    assert "attention_judgment" not in params
    assert "visibility" not in params
