from datetime import datetime, timezone
from uuid import uuid4

from logan_core.contracts import AttentionRecommendation, CommunitySignal, Dimensions
from logan_core.policy import (
    ANALYSIS_DISCLAIMER,
    BOT_RISK_SUPPRESSION_THRESHOLD,
    EXCEPTIONAL_CONFIDENCE_FLOOR,
    EXCEPTIONAL_NOVELTY_FLOOR,
    EXCEPTIONAL_URGENCY_FLOOR,
    GAMBLING_DISCLAIMER,
    PERSONAL_EXPLICIT_RELEVANCE_FLOOR,
    PERSONAL_INFERRED_CONFIDENCE_FLOOR,
    PERSONAL_INFERRED_RELEVANCE_FLOOR,
    PERSONAL_INFERRED_URGENCY_FLOOR,
    PERSONAL_RANK_SCORE_FLOOR,
    PolicyEngine,
)


def _dimensions(**overrides):
    base = dict(
        personal_relevance=0.7,
        global_importance=0.6,
        community_momentum=0.5,
        urgency=0.5,
        confidence=0.7,
        novelty=0.6,
        opportunity_magnitude=0.6,
        risk=0.1,
        actionability=0.7,
        connection_strength=0.5,
    )
    base.update(overrides)
    return Dimensions(**base)


def _recommendation(event_id, recommend=True, internal_rank_score=0.6, **dim_overrides):
    now = datetime.now(timezone.utc)
    return AttentionRecommendation(
        event_id=event_id,
        recommend=recommend,
        dimensions=_dimensions(**dim_overrides),
        internal_rank_score=internal_rank_score,
        reasons=["test"],
        recommended_at=now,
    )


def _community(event_id, bot_risk=0.0):
    now = datetime.now(timezone.utc)
    return CommunitySignal(
        event_id=event_id,
        engagement_volume=20,
        engagement_velocity=2.0,
        unique_users=15,
        saves_shares=2,
        questions=1,
        lifecycle_state="peak",
        coordinated_risk=bot_risk,
        bot_risk=bot_risk,
        momentum_score=0.4,
        measured_at=now,
    )


def test_sports_domain_gets_objectivity_language_constraints():
    event_id = uuid4()
    recommendation = _recommendation(event_id)
    community = _community(event_id)

    result = PolicyEngine().evaluate(recommendation, community, domain="sports")

    assert "objective_data_forward_only" in result.language_constraints
    assert "no_urgency_framing" in result.language_constraints
    assert GAMBLING_DISCLAIMER in result.required_disclaimers
    assert ANALYSIS_DISCLAIMER in result.required_disclaimers


def test_stocks_domain_does_not_get_gambling_disclaimer():
    event_id = uuid4()
    recommendation = _recommendation(event_id)
    community = _community(event_id)

    result = PolicyEngine().evaluate(recommendation, community, domain="stocks")

    assert "objective_data_forward_only" not in result.language_constraints
    assert GAMBLING_DISCLAIMER not in result.required_disclaimers
    assert ANALYSIS_DISCLAIMER in result.required_disclaimers


def test_high_bot_risk_suppresses_communication():
    event_id = uuid4()
    recommendation = _recommendation(event_id)
    community = _community(event_id, bot_risk=0.9)

    result = PolicyEngine().evaluate(recommendation, community, domain="social")

    assert result.permitted is False
    assert result.communication_mode == "suppressed"


def test_advice_boundary_language_constraint_always_present():
    event_id = uuid4()
    recommendation = _recommendation(event_id)
    community = _community(event_id)

    for domain in ("stocks", "sports", "poly", "social", "news"):
        result = PolicyEngine().evaluate(recommendation, community, domain=domain)
        assert "no_directive_language" in result.language_constraints
        assert ANALYSIS_DISCLAIMER in result.required_disclaimers


def test_poly_domain_gets_objectivity_language_constraints():
    """ADR-013 applies equally to poly (prediction markets), not just sports --
    only sports had a dedicated assertion before V3.1.4 BATCH-2."""
    event_id = uuid4()
    recommendation = _recommendation(event_id)
    community = _community(event_id)

    result = PolicyEngine().evaluate(recommendation, community, domain="poly")

    assert "objective_data_forward_only" in result.language_constraints
    assert "no_urgency_framing" in result.language_constraints
    assert GAMBLING_DISCLAIMER in result.required_disclaimers


def test_bot_risk_just_below_threshold_does_not_suppress():
    event_id = uuid4()
    recommendation = _recommendation(event_id)
    community = _community(event_id, bot_risk=BOT_RISK_SUPPRESSION_THRESHOLD - 0.01)

    result = PolicyEngine().evaluate(recommendation, community, domain="social")

    assert result.permitted is True
    assert result.communication_mode != "suppressed"


def test_bot_risk_exactly_at_threshold_suppresses():
    event_id = uuid4()
    recommendation = _recommendation(event_id)
    community = _community(event_id, bot_risk=BOT_RISK_SUPPRESSION_THRESHOLD)

    result = PolicyEngine().evaluate(recommendation, community, domain="social")

    assert result.permitted is False
    assert result.communication_mode == "suppressed"


def test_bot_risk_above_threshold_suppresses():
    event_id = uuid4()
    recommendation = _recommendation(event_id)
    community = _community(
        event_id, bot_risk=min(BOT_RISK_SUPPRESSION_THRESHOLD + 0.1, 1.0)
    )

    result = PolicyEngine().evaluate(recommendation, community, domain="social")

    assert result.permitted is False
    assert result.communication_mode == "suppressed"


def test_bot_risk_suppression_applies_even_in_objective_only_domain():
    """Bot-risk suppression and the sports/poly objectivity rule are independent
    -- a suppressed result from an objective-only domain must still carry the
    domain's required disclaimers (they're appended before the suppression
    check runs), not silently drop them.
    """
    event_id = uuid4()
    recommendation = _recommendation(event_id)
    community = _community(event_id, bot_risk=0.95)

    result = PolicyEngine().evaluate(recommendation, community, domain="sports")

    assert result.permitted is False
    assert result.communication_mode == "suppressed"
    assert GAMBLING_DISCLAIMER in result.required_disclaimers


def test_decision_trace_populated_for_both_permitted_and_suppressed():
    event_id = uuid4()
    recommendation = _recommendation(event_id)

    permitted = PolicyEngine().evaluate(
        recommendation, _community(event_id, bot_risk=0.0), domain="stocks"
    )
    suppressed = PolicyEngine().evaluate(
        recommendation, _community(event_id, bot_risk=0.95), domain="stocks"
    )

    assert len(permitted.decision_trace) == 1
    assert len(suppressed.decision_trace) == 1
    assert "suppressed" in suppressed.decision_trace[0].rule


# --- STRATUS Watch eligibility: Personal / Exceptional routes (ADR-049) ---
#
# communication_mode="alert" now requires qualifying through one of two
# explicit routes rather than the old single `urgency >= 0.7` gate. Not
# permitted (bot-risk suppressed) is already covered above and is unchanged
# by this pass -- these tests all use bot_risk=0.0.


def _evaluate(event_id, **dim_overrides_and_rank):
    rank = dim_overrides_and_rank.pop("internal_rank_score", 0.6)
    recommendation = _recommendation(
        event_id, internal_rank_score=rank, **dim_overrides_and_rank
    )
    result = PolicyEngine().evaluate(
        recommendation, _community(event_id, bot_risk=0.0), domain="stocks"
    )
    return result


def _route(result):
    return result.decision_trace[0].rule.split("watch_route=")[1].split(";")[0]


def test_strong_explicit_relevance_with_sufficient_quality_alerts_via_personal():
    event_id = uuid4()
    result = _evaluate(
        event_id,
        personal_relevance=PERSONAL_EXPLICIT_RELEVANCE_FLOOR,
        internal_rank_score=PERSONAL_RANK_SCORE_FLOOR,
        urgency=0.5,
        confidence=0.5,
    )
    assert result.communication_mode == "alert"
    assert _route(result) == "personal"


def test_moderate_urgency_and_confidence_are_enough_for_explicit_tier():
    """The explicit tier's own requirement is relevance + overall rank
    quality -- it does not need its own separate urgency/confidence floors
    the way the inferred tier does."""
    event_id = uuid4()
    result = _evaluate(
        event_id,
        personal_relevance=0.6,
        internal_rank_score=0.6,
        urgency=0.5,
        confidence=0.5,
    )
    assert result.communication_mode == "alert"
    assert _route(result) == "personal"


def test_same_moderate_dims_at_inferred_relevance_do_not_qualify():
    """Same urgency/confidence as the explicit-tier test above, but with
    inferred-tier relevance instead of explicit -- must NOT alert. This is
    the direct A/B proof that explicit relevance remains stronger than
    inferred: identical event quality, different outcome based only on
    relevance source."""
    event_id = uuid4()
    result = _evaluate(
        event_id,
        personal_relevance=PERSONAL_INFERRED_RELEVANCE_FLOOR,
        connection_strength=0.5,
        internal_rank_score=0.6,
        urgency=0.5,
        confidence=0.5,
    )
    assert result.communication_mode != "alert"
    assert _route(result) == "none"


def test_mature_inferred_relevance_can_contribute():
    """Inferred relevance, capped at PERSONAL_INFERRED_RELEVANCE_FLOOR, can
    still unlock the Personal route -- but only alongside its own materially
    higher urgency/confidence support, unlike the explicit tier."""
    event_id = uuid4()
    result = _evaluate(
        event_id,
        personal_relevance=PERSONAL_INFERRED_RELEVANCE_FLOOR,
        connection_strength=0.5,
        internal_rank_score=0.4,  # deliberately below the explicit tier's own bar
        urgency=PERSONAL_INFERRED_URGENCY_FLOOR,
        confidence=PERSONAL_INFERRED_CONFIDENCE_FLOOR,
    )
    assert result.communication_mode == "alert"
    assert _route(result) == "personal"


def test_inferred_relevance_alone_does_not_automatically_alert():
    """personal_relevance == 0.5 with a real connection but ordinary
    urgency/confidence (below the inferred tier's own floors) must not
    alert -- a single inferred interest cannot independently force a push."""
    event_id = uuid4()
    result = _evaluate(
        event_id,
        personal_relevance=PERSONAL_INFERRED_RELEVANCE_FLOOR,
        connection_strength=0.5,
        internal_rank_score=0.6,
        urgency=0.5,
        confidence=0.5,
        novelty=0.5,
    )
    assert result.communication_mode != "alert"
    assert _route(result) == "none"


def test_personal_relevance_0_5_without_a_real_connection_does_not_use_inferred_tier():
    """OpportunityEngine's "nothing connected, informational" default also
    floors personal_relevance at 0.5 (see ADR-046's FED example) --
    connection_strength == 0 must correctly exclude that generic default
    from the inferred tier, even though the raw relevance number is
    identical to a genuine inferred connection's floor."""
    event_id = uuid4()
    result = _evaluate(
        event_id,
        personal_relevance=PERSONAL_INFERRED_RELEVANCE_FLOOR,
        connection_strength=0.0,
        internal_rank_score=0.4,
        urgency=PERSONAL_INFERRED_URGENCY_FLOOR,
        confidence=PERSONAL_INFERRED_CONFIDENCE_FLOOR,
    )
    assert _route(result) != "personal"


def test_low_confidence_personally_relevant_item_does_not_alert():
    """internal_rank_score is set to reflect what OpportunityEngine's real
    formula would actually produce given weak confidence/urgency/
    actionability -- not hand-forced to 0.6 independent of the rest, since
    the explicit tier trusts internal_rank_score as its quality signal
    rather than re-deriving it from confidence directly."""
    event_id = uuid4()
    result = _evaluate(
        event_id,
        personal_relevance=0.8,
        internal_rank_score=0.4,
        urgency=0.5,
        confidence=0.2,
        actionability=0.2,
        opportunity_magnitude=0.1,
    )
    assert result.communication_mode != "alert"
    assert _route(result) == "none"


def test_low_urgency_personally_relevant_item_does_not_alert():
    """Real fixture regression: an explicitly-relevant event (personal_relevance
    at the explicit floor) with only "peak"-tier, non-actionable urgency (0.5,
    no actionable bonus) does not reliably clear the rank-score bar -- personal
    relevance alone is not "sufficient event quality." Constructed directly
    against a below-floor internal_rank_score rather than relying on the
    OpportunityEngine formula, matching this file's existing style of testing
    PolicyEngine in isolation."""
    event_id = uuid4()
    result = _evaluate(
        event_id,
        personal_relevance=0.6,
        internal_rank_score=0.59,
        urgency=0.5,
        confidence=0.6,
    )
    assert result.communication_mode != "alert"
    assert _route(result) == "none"


def test_non_personal_routine_event_stays_analysis_not_alert():
    event_id = uuid4()
    result = _evaluate(
        event_id,
        personal_relevance=0.2,
        connection_strength=0.0,
        internal_rank_score=0.3,
        urgency=0.3,
        confidence=0.4,
        novelty=0.2,
    )
    assert result.communication_mode == "analysis"
    assert _route(result) == "none"


def test_weak_personal_relevance_with_exceptional_event_quality_alerts():
    """FED-shaped scenario (ADR-046): no personal connection at all, but
    genuinely exceptional urgency/confidence/novelty -- must still alert,
    through the Exceptional route."""
    event_id = uuid4()
    result = _evaluate(
        event_id,
        personal_relevance=0.5,
        connection_strength=0.0,
        internal_rank_score=0.4,
        urgency=EXCEPTIONAL_URGENCY_FLOOR,
        confidence=EXCEPTIONAL_CONFIDENCE_FLOOR,
        novelty=EXCEPTIONAL_NOVELTY_FLOOR,
    )
    assert result.communication_mode == "alert"
    assert _route(result) == "exceptional"


def test_ordinary_high_urgency_event_does_not_become_exceptional():
    """The old single-gate threshold (urgency >= 0.7) no longer suffices on
    its own -- Exceptional requires urgency >= 0.8 specifically, plus
    confidence and novelty both also at their own high floors."""
    event_id = uuid4()
    result = _evaluate(
        event_id,
        personal_relevance=0.5,
        connection_strength=0.0,
        internal_rank_score=0.4,
        urgency=0.7,
        confidence=EXCEPTIONAL_CONFIDENCE_FLOOR,
        novelty=EXCEPTIONAL_NOVELTY_FLOOR,
    )
    assert result.communication_mode != "alert"
    assert _route(result) == "none"


def test_exceptional_requires_all_three_dimensions_simultaneously():
    event_id = uuid4()
    high = dict(
        personal_relevance=0.5,
        connection_strength=0.0,
        internal_rank_score=0.4,
        urgency=EXCEPTIONAL_URGENCY_FLOOR,
        confidence=EXCEPTIONAL_CONFIDENCE_FLOOR,
        novelty=EXCEPTIONAL_NOVELTY_FLOOR,
    )
    for missing_dim in ("urgency", "confidence", "novelty"):
        dims = dict(high)
        dims[missing_dim] = 0.4
        result = _evaluate(event_id, **dims)
        assert (
            result.communication_mode != "alert"
        ), f"should fail without {missing_dim}"


def test_exceptional_route_is_harder_to_satisfy_than_personal_route():
    """The same moderate urgency/confidence/novelty (0.5 each) that's
    sufficient to support Personal's explicit tier (given high relevance +
    rank) is nowhere near Exceptional's own floors -- the two routes are not
    interchangeable, and Exceptional demands more from the event itself,
    with zero credit for personal relevance."""
    event_id = uuid4()
    personal_case = _evaluate(
        event_id,
        personal_relevance=PERSONAL_EXPLICIT_RELEVANCE_FLOOR,
        internal_rank_score=PERSONAL_RANK_SCORE_FLOOR,
        urgency=0.5,
        confidence=0.5,
        novelty=0.5,
    )
    assert _route(personal_case) == "personal"

    exceptional_case = _evaluate(
        event_id,
        personal_relevance=0.0,
        connection_strength=0.0,
        internal_rank_score=0.4,
        urgency=0.5,
        confidence=0.5,
        novelty=0.5,
    )
    assert _route(exceptional_case) == "none"
    assert exceptional_case.communication_mode != "alert"


def test_watch_route_visible_in_decision_trace_for_all_three_outcomes():
    event_id = uuid4()
    personal = _evaluate(
        event_id,
        personal_relevance=PERSONAL_EXPLICIT_RELEVANCE_FLOOR,
        internal_rank_score=PERSONAL_RANK_SCORE_FLOOR,
    )
    exceptional = _evaluate(
        event_id,
        personal_relevance=0.5,
        connection_strength=0.0,
        internal_rank_score=0.4,
        urgency=EXCEPTIONAL_URGENCY_FLOOR,
        confidence=EXCEPTIONAL_CONFIDENCE_FLOOR,
        novelty=EXCEPTIONAL_NOVELTY_FLOOR,
    )
    neither = _evaluate(
        event_id,
        personal_relevance=0.2,
        connection_strength=0.0,
        internal_rank_score=0.3,
        urgency=0.3,
        confidence=0.4,
        novelty=0.2,
    )
    assert "watch_route=personal" in personal.decision_trace[0].rule
    assert "watch_route=exceptional" in exceptional.decision_trace[0].rule
    assert "watch_route=none" in neither.decision_trace[0].rule
    for result in (personal, exceptional, neither):
        evidence = result.decision_trace[0].evidence
        assert any(e.startswith("personal_relevance=") for e in evidence)
        assert any(e.startswith("urgency=") for e in evidence)
        assert any(e.startswith("confidence=") for e in evidence)
        assert any(e.startswith("novelty=") for e in evidence)
        assert any(e.startswith("connection_strength=") for e in evidence)


def test_not_recommended_stays_informational_regardless_of_dimensions():
    """recommend=False must short-circuit to "informational" without even
    consulting the route logic, unchanged from before this pass."""
    event_id = uuid4()
    result = _evaluate(
        event_id,
        recommend=False,
        personal_relevance=1.0,
        internal_rank_score=1.0,
        urgency=1.0,
        confidence=1.0,
        novelty=1.0,
    )
    assert result.communication_mode == "informational"
    assert "watch_route=none" in result.decision_trace[0].rule
