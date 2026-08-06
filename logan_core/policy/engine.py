from datetime import datetime, timezone

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

        if not recommendation.recommend:
            communication_mode = "informational"
        elif recommendation.dimensions.urgency >= 0.7:
            communication_mode = "alert"
        else:
            communication_mode = "analysis"

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
                    rule=f"communication_mode={communication_mode}; rules_applied={policy_rules_applied}",
                    timestamp=now,
                )
            ],
        )
