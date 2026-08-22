from datetime import datetime, timezone
from typing import Literal

from logan_core.contracts import (
    AttentionRecommendation,
    CommunitySignal,
    DecisionTraceEntry,
    Domain,
    PolicyResult,
)

ANALYSIS_DISCLAIMER = "This is analysis and context, not financial or betting advice. You decide what to do next."
GAMBLING_DISCLAIMER = (
    "This is not gambling advice. Odds and markets can move quickly and unpredictably."
)

BOT_RISK_SUPPRESSION_THRESHOLD = 0.7

# Domains held to the stricter, objective-only language rule per ADR-013.
OBJECTIVE_ONLY_DOMAINS = {"sports", "poly"}

# STRATUS Watch eligibility (ADR-049): communication_mode="alert" is now
# decided by two explicit routes -- "personal" and "exceptional" -- instead
# of the old single `urgency >= 0.7` generic-urgency gate. Every threshold
# below reuses a value/semantic this codebase already established elsewhere
# rather than inventing a new one; see docs/DECISIONS.md ADR-049 for the
# full provenance of each.

# Personal route, explicit tier: OpportunityEngine's own "explicit relevance
# bump" (0.6, ADR-048) combined with the same internal_rank_score bar
# PrioritizationEngine already uses for "primary" visibility -- an event
# good enough to be the user's top item *and* meaningfully connected to
# something they explicitly hold or follow.
PERSONAL_EXPLICIT_RELEVANCE_FLOOR = 0.6
PERSONAL_RANK_SCORE_FLOOR = 0.6  # == PrioritizationEngine's "primary" visibility bar

# Personal route, inferred tier: OpportunityEngine's own inferred-only bound
# (0.5, ADR-048) may still qualify, but only alongside this file's own
# former single-gate alert threshold (urgency >= 0.7) and
# ConclusionConfidenceEngine's own "inference" classification bar
# (confidence >= 0.55) -- inferred relevance contributes, but needs
# materially more support from the event itself than an explicit connection
# does, matching the owner's "explicit remains stronger" decision.
#
# personal_relevance == 0.5 alone is NOT sufficient evidence of an inferred
# connection -- OpportunityEngine's "informational, nothing connected"
# default *also* floors at 0.5 (see ADR-046: FED previously qualified for
# push at exactly this generic, unconnected default). dims.connection_strength
# (> 0 only when reasoning.connected_entities is non-empty) is required
# alongside the relevance floor specifically to distinguish a real inferred
# connection from that coincidentally-identical generic default -- reusing
# an existing Dimensions field rather than adding a new one.
PERSONAL_INFERRED_RELEVANCE_FLOOR = 0.5
PERSONAL_INFERRED_URGENCY_FLOOR = 0.7  # this file's own former alert threshold
PERSONAL_INFERRED_CONFIDENCE_FLOOR = (
    0.55  # ConclusionConfidenceEngine's "inference" bar
)

# Exceptional route: no personal-relevance requirement at all -- qualifies
# purely on event quality, deliberately harder than either Personal tier
# (see _watch_route's docstring for why). EXCEPTIONAL_URGENCY_FLOOR reuses
# opportunity/engine.py's own `_LIFECYCLE_URGENCY["emerging"]` (0.8) -- the
# single highest urgency tier reachable without ReasoningEngine's
# holds_directly actionable bonus, which would itself imply a personal
# connection this route explicitly doesn't require. EXCEPTIONAL_CONFIDENCE_
# FLOOR and EXCEPTIONAL_NOVELTY_FLOOR both reuse 0.7, the same "high" bar
# this file already uses for BOT_RISK_SUPPRESSION_THRESHOLD above (and
# previously used for the old single urgency-only alert gate) -- novelty
# >= 0.7 corresponds to opportunity/engine.py's `_STANCE_NOVELTY` "contradicts"
# stance or higher (i.e. "new"), not merely "complicates" (0.6) or "confirms"
# (0.2) an existing event.
EXCEPTIONAL_URGENCY_FLOOR = 0.8
EXCEPTIONAL_CONFIDENCE_FLOOR = 0.7
EXCEPTIONAL_NOVELTY_FLOOR = 0.7


def _watch_route(
    recommendation: AttentionRecommendation,
) -> Literal["personal", "exceptional", "none"]:
    """STRATUS Watch eligibility (ADR-049): "should this interrupt the user
    right now" answered as two explicit routes rather than one blended
    score, so the reason an alert qualified stays legible (see the
    DecisionTraceEntry this feeds). Only meaningful once
    recommendation.recommend is already True (Opportunity's own bar) --
    this only decides *how* an already-recommended item may communicate,
    matching this layer's existing responsibility split with Opportunity.

    Personal is checked first and, if it qualifies, wins outright --
    Exceptional is deliberately harder to satisfy (all three of very-high
    urgency/confidence/novelty simultaneously, with no relevance credit at
    all) and exists only to catch a genuinely major event a Personal route
    would otherwise miss, not to offer an easier second path once Personal
    already qualifies.

    The explicit and inferred tiers prove "meaningful combination" two
    different ways rather than sharing one gate: explicit relevance is
    strong enough on its own to lean on internal_rank_score's existing
    holistic blend (personal_relevance + urgency + confidence + actionability
    + ... in one already-computed number) as its quality bar. Inferred
    relevance is capped lower (ADR-048) and never carries an actionable/
    explicit-connect boost, so requiring it to *also* clear rank_score's
    aggregate on top of its own urgency/confidence floors made it
    practically unreachable even when genuinely well-evidenced (verified
    against live simulated fixtures, not assumed) -- its own four
    conditions (real connection, relevance, urgency, confidence) are the
    "meaningful combination" for that tier, standing on their own.
    """
    dims = recommendation.dimensions
    explicit_tier = (
        dims.personal_relevance >= PERSONAL_EXPLICIT_RELEVANCE_FLOOR
        and recommendation.internal_rank_score >= PERSONAL_RANK_SCORE_FLOOR
    )
    inferred_tier = (
        dims.personal_relevance >= PERSONAL_INFERRED_RELEVANCE_FLOOR
        and dims.connection_strength > 0
        and dims.urgency >= PERSONAL_INFERRED_URGENCY_FLOOR
        and dims.confidence >= PERSONAL_INFERRED_CONFIDENCE_FLOOR
    )
    if explicit_tier or inferred_tier:
        return "personal"

    if (
        dims.urgency >= EXCEPTIONAL_URGENCY_FLOOR
        and dims.confidence >= EXCEPTIONAL_CONFIDENCE_FLOOR
        and dims.novelty >= EXCEPTIONAL_NOVELTY_FLOOR
    ):
        return "exceptional"

    return "none"


class PolicyEngine:
    """Layer 11 — controls how Logan is permitted to communicate a conclusion. The
    Opportunity Engine determines whether something matters; Policy determines how
    Logan may say it. Forbidden per spec: modifying reasoning/scoring, writing to
    Memory, changing Opportunity Engine dimensions.
    """

    def evaluate(
        self,
        recommendation: AttentionRecommendation,
        community: CommunitySignal,
        domain: Domain,
    ) -> PolicyResult:
        now = datetime.now(timezone.utc)
        policy_rules_applied = ["advice_boundary_v1"]
        language_constraints = ["no_directive_language"]
        required_disclaimers = [ANALYSIS_DISCLAIMER]

        if domain in OBJECTIVE_ONLY_DOMAINS:
            policy_rules_applied.append("betting_objectivity_v1")
            language_constraints += [
                "objective_data_forward_only",
                "no_urgency_framing",
            ]
            required_disclaimers.append(GAMBLING_DISCLAIMER)

        if community.bot_risk >= BOT_RISK_SUPPRESSION_THRESHOLD:
            policy_rules_applied.append("bot_risk_suppression")
            return PolicyResult(
                event_id=recommendation.event_id,
                permitted=False,
                communication_mode="suppressed",
                language_constraints=language_constraints,
                required_disclaimers=required_disclaimers,
                policy_rules_applied=policy_rules_applied,
                evaluated_at=now,
                decision_trace=[
                    DecisionTraceEntry(
                        layer="policy",
                        rule=f"suppressed: bot_risk={community.bot_risk:.2f} >= "
                        f"{BOT_RISK_SUPPRESSION_THRESHOLD} threshold",
                        timestamp=now,
                    )
                ],
            )

        communication_mode: Literal["analysis", "alert", "informational", "suppressed"]
        watch_route: Literal["personal", "exceptional", "none"] = "none"
        if not recommendation.recommend:
            communication_mode = "informational"
        else:
            watch_route = _watch_route(recommendation)
            communication_mode = "alert" if watch_route != "none" else "analysis"

        return PolicyResult(
            event_id=recommendation.event_id,
            permitted=True,
            communication_mode=communication_mode,
            language_constraints=language_constraints,
            required_disclaimers=required_disclaimers,
            policy_rules_applied=policy_rules_applied,
            evaluated_at=now,
            decision_trace=[
                DecisionTraceEntry(
                    layer="policy",
                    rule=f"communication_mode={communication_mode}; watch_route={watch_route}; "
                    f"rules_applied={policy_rules_applied}",
                    evidence=[
                        f"personal_relevance={recommendation.dimensions.personal_relevance:.2f}",
                        f"urgency={recommendation.dimensions.urgency:.2f}",
                        f"confidence={recommendation.dimensions.confidence:.2f}",
                        f"novelty={recommendation.dimensions.novelty:.2f}",
                        f"connection_strength={recommendation.dimensions.connection_strength:.2f}",
                        # internal_rank_score deliberately excluded (ADR-029):
                        # INTERNAL-ONLY, never returned via any public API
                        # response, and DecisionTraceEntry.evidence here is
                        # serialized as part of the full pipeline result.
                    ],
                    timestamp=now,
                )
            ],
        )
