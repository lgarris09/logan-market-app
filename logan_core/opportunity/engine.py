from datetime import datetime, timezone
from uuid import UUID

from logan_core.contracts import (
    AttentionRecommendation,
    CommunitySignal,
    ConclusionConfidence,
    DecisionTraceEntry,
    Dimensions,
    ReasoningResult,
)

RECOMMEND_THRESHOLD = 0.35

_LIFECYCLE_URGENCY = {"emerging": 0.8, "peak": 0.5, "fading": 0.2, "dormant": 0.1}
_STANCE_NOVELTY = {"new": 1.0, "contradicts": 0.7, "complicates": 0.6, "confirms": 0.2}
_ACTIONABILITY_SCORE = {"actionable": 1.0, "informational": 0.5, "ambiguous": 0.2}

# Sprint 3.6.7 Block 3: the achievable range for an inferred-only connection's
# personal_relevance contribution. INFERRED_RELEVANCE_FLOOR reuses this
# file's own pre-existing "informational" anchor (0.5, ADR-048's original
# flat floor) as the *minimum* once inferred-connected at all -- unchanged
# backward-compat baseline. INFERRED_RELEVANCE_CEILING is a new, deliberately
# reasoned constant: it must stay strictly below the explicit tier's 0.6 bump
# (ADR-048's own stated invariant, "deliberately less than the explicit bump,
# never equal") while still leaving real headroom for mature evidence to
# measurably outscore a just-qualified connection.
INFERRED_RELEVANCE_FLOOR = 0.5
INFERRED_RELEVANCE_CEILING = 0.59
# Interest.weight range a matched inferred connection can realistically carry
# -- UserModelBuilder.MIN_REPEAT_EVIDENCE-qualifying evidence requires
# FeedbackEngine's inferred_intent=="interested" specifically, whose weakest
# confidence tier ("remind") is 0.75; UserModelBuilder.
# MAX_INFERRED_INTEREST_WEIGHT (user_model/model.py) caps the strongest,
# most-matured case at 0.90. Reused here, not re-derived, so the two files'
# constants stay in lockstep by construction rather than by convention.
_INFERRED_WEIGHT_FLOOR = 0.75
_INFERRED_WEIGHT_CEILING = 0.90


def _scale_inferred_relevance(inferred_relevance_strength: float) -> float:
    """Maps a matched inferred Interest.weight onto the bounded
    [INFERRED_RELEVANCE_FLOOR, INFERRED_RELEVANCE_CEILING] personal_relevance
    range -- linear within the realistic weight range, clamped at both ends.
    `inferred_relevance_strength <= _INFERRED_WEIGHT_FLOOR` (including the
    0.0 default every pre-Block-3 caller/test supplies) returns exactly
    INFERRED_RELEVANCE_FLOOR -- the identical flat 0.5 this returned before
    Block 3, so nothing that doesn't populate the new field changes.
    """
    if inferred_relevance_strength <= _INFERRED_WEIGHT_FLOOR:
        return INFERRED_RELEVANCE_FLOOR
    span = _INFERRED_WEIGHT_CEILING - _INFERRED_WEIGHT_FLOOR
    fraction = min((inferred_relevance_strength - _INFERRED_WEIGHT_FLOOR) / span, 1.0)
    return INFERRED_RELEVANCE_FLOOR + fraction * (
        INFERRED_RELEVANCE_CEILING - INFERRED_RELEVANCE_FLOOR
    )


class OpportunityEngine:
    """Layer 10 — determines what deserves this user's attention now. Recommends
    attention; does not execute financial actions or issue directives (ADR-002,
    ADR-010). Does not choose presentation format or suppress by policy — those belong
    to Presentation and Policy respectively. V1: does not read MentalModelDelta (V2 only).
    """

    def evaluate(
        self,
        reasoning: ReasoningResult,
        confidence: ConclusionConfidence,
        community: CommunitySignal,
        competing_items: list[UUID] | None = None,
    ) -> AttentionRecommendation:
        now = datetime.now(timezone.utc)
        trace: list[DecisionTraceEntry] = []

        # 1. Validate
        trace.append(
            DecisionTraceEntry(
                layer="opportunity_engine",
                rule="validate: event has a reasoning result",
                timestamp=now,
            )
        )

        # 2. Understand (already done by Reasoning Engine upstream)
        trace.append(
            DecisionTraceEntry(
                layer="opportunity_engine",
                rule=f"understand: stance={reasoning.stance}",
                timestamp=now,
            )
        )

        # 3. Connect. Owner decision (behavioral-personalization pass):
        # explicit interests/holdings remain the stronger source of truth --
        # an explicit connection keeps the original 0.6 bump unchanged.
        # A connection that exists *only* through an inferred interest
        # (reasoning.connected_entities_explicit is empty for that entity)
        # is bounded below that -- deliberately less than the explicit bump,
        # never equal (ADR-048). Sprint 3.6.7 Block 3: within that bounded
        # range, an inferred connection's contribution now scales with how
        # mature the underlying behavioral evidence actually is (see
        # _scale_inferred_relevance), instead of a flat 0.5 floor regardless
        # of evidence strength. reasoning.inferred_relevance_strength==0.0
        # (every pre-Block-3 caller/test) reproduces the exact old flat 0.5
        # floor -- see that function's own docstring.
        personal_relevance = _ACTIONABILITY_SCORE.get(reasoning.actionability, 0.2)
        connect_basis = "none"
        if reasoning.actionability != "actionable":
            if reasoning.connected_entities_explicit:
                personal_relevance = max(personal_relevance, 0.6)
                connect_basis = "explicit"
            elif reasoning.connected_entities_inferred:
                personal_relevance = max(
                    personal_relevance,
                    _scale_inferred_relevance(reasoning.inferred_relevance_strength),
                )
                connect_basis = "inferred"
        trace.append(
            DecisionTraceEntry(
                layer="opportunity_engine",
                rule=f"connect: personal_relevance={personal_relevance:.2f} "
                f"(basis={connect_basis})",
                confidence=personal_relevance,
                evidence=[
                    f"connected_entities_explicit={reasoning.connected_entities_explicit}",
                    f"connected_entities_inferred={reasoning.connected_entities_inferred}",
                ],
                timestamp=now,
            )
        )

        # 4. Assess
        trace.append(
            DecisionTraceEntry(
                layer="opportunity_engine",
                rule="assess: scoring dimensions from inputs",
                timestamp=now,
            )
        )
        # ADR-034 / V3.1.4 BATCH-1 Stage 2: global_importance is confidence-only.
        # community.momentum_score must never contribute to ranking, confidence,
        # urgency, or relevance — directly or indirectly through this dimension.
        global_importance = confidence.confidence_score
        # Retained as contextual/presentation information only (e.g. a future
        # "trending" badge) — see the scoring formula below, which excludes it.
        community_momentum = community.momentum_score
        urgency = min(
            _LIFECYCLE_URGENCY.get(community.lifecycle_state, 0.1)
            + (0.2 if reasoning.actionability == "actionable" else 0.0),
            1.0,
        )
        novelty = _STANCE_NOVELTY.get(reasoning.stance, 0.5)
        opportunity_magnitude = min(personal_relevance * global_importance * 1.4, 1.0)
        connection_strength = min(len(reasoning.connected_entities) / 3, 1.0)
        actionability_score = _ACTIONABILITY_SCORE.get(reasoning.actionability, 0.2)

        # 5. Constrain
        risk = min(community.bot_risk * 0.5 + community.coordinated_risk * 0.5, 1.0)
        if confidence.classification == "speculation":
            risk = min(risk + 0.2, 1.0)
        trace.append(
            DecisionTraceEntry(
                layer="opportunity_engine",
                rule=f"constrain: risk={risk:.2f}",
                timestamp=now,
            )
        )

        dimensions = Dimensions(
            personal_relevance=personal_relevance,
            global_importance=global_importance,
            community_momentum=community_momentum,
            urgency=urgency,
            confidence=confidence.confidence_score,
            novelty=novelty,
            opportunity_magnitude=opportunity_magnitude,
            risk=risk,
            actionability=actionability_score,
            connection_strength=connection_strength,
        )

        # ADR-034: community_momentum is excluded from this formula, not
        # redistributed into the remaining weights — dropped, not silently
        # replaced with a different weighting scheme. Weights below therefore
        # sum to 0.98 of the pre-risk-penalty maximum, not 1.00; this is
        # intentional and must not be "corrected" by rebalancing without a new
        # ADR (see docs/DECISIONS.md ADR-034 and 07_DATA_CONTRACTS.md).
        internal_rank_score = (
            dimensions.personal_relevance * 0.25
            + dimensions.urgency * 0.20
            + dimensions.confidence * 0.15
            + dimensions.actionability * 0.15
            + dimensions.global_importance * 0.10
            + dimensions.opportunity_magnitude * 0.08
            + dimensions.novelty * 0.04
            + dimensions.connection_strength * 0.01
        ) * (1 - dimensions.risk * 0.20)
        internal_rank_score = max(0.0, min(1.0, internal_rank_score))

        # 6. Compare
        trace.append(
            DecisionTraceEntry(
                layer="opportunity_engine",
                rule=f"compare: {len(competing_items or [])} competing items",
                timestamp=now,
            )
        )

        recommend = internal_rank_score >= RECOMMEND_THRESHOLD

        reasons: list[str] = []
        if dimensions.personal_relevance >= 0.6:
            reasons.append("This connects directly to what you follow or hold.")
        if dimensions.urgency >= 0.6:
            reasons.append("Community attention on this is still building.")
        if dimensions.confidence >= 0.6:
            reasons.append("Multiple signals support this conclusion.")
        if dimensions.novelty >= 0.8:
            reasons.append(
                "This is a new development, not a repeat of something already surfaced."
            )
        if recommend and not reasons:
            reasons.append(
                "This crosses the attention threshold on balance of the scored dimensions."
            )

        # 7. Recommend
        trace.append(
            DecisionTraceEntry(
                layer="opportunity_engine",
                rule=(
                    f"recommend: internal_rank_score={internal_rank_score:.2f} >= {RECOMMEND_THRESHOLD}"
                    if recommend
                    else f"recommend: internal_rank_score={internal_rank_score:.2f} below threshold"
                ),
                confidence=internal_rank_score,
                timestamp=now,
            )
        )

        return AttentionRecommendation(
            event_id=reasoning.event_id,
            recommend=recommend,
            dimensions=dimensions,
            internal_rank_score=internal_rank_score,
            reasons=reasons,
            competing_items=competing_items or [],
            recommended_at=now,
            decision_trace=trace,
        )
