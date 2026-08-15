import math
from datetime import datetime, timezone
from typing import Literal

from logan_core.contracts import (
    DecisionTraceEntry,
    EnrichedEvent,
    EvidenceTrust,
    NormalizedSignal,
)

# V1 static source reputation registry (0.0-1.0). Extension point: dynamic
# reputation learning, updated only by the Learning System per the spec.
SOURCE_REPUTATION_REGISTRY: dict[str, float] = {
    "reuters_wire": 0.95,
    "company_press_release": 0.90,
    "bloomberg_terminal": 0.93,
    "sec_filing": 0.98,
    "sportsbook_feed": 0.85,
    "polymarket_api": 0.80,
    "social_aggregator": 0.55,
    "unverified_forum": 0.30,
}

RECENCY_HALF_LIFE_HOURS = 6.0

MANIPULATION_PENALTY = {"low": 1.0, "medium": 0.75, "high": 0.40}


class EvidenceTrustEngine:
    """Layer 4a — evaluates credibility of an EnrichedEvent. Runs in parallel with
    Community Intelligence. Forbidden per spec: reading User Model, applying personal
    relevance, modifying event content.
    """

    def __init__(self, registry: dict[str, float] | None = None) -> None:
        self._registry = (
            registry if registry is not None else SOURCE_REPUTATION_REGISTRY
        )

    def _recency_score(self, occurred_at: datetime, now: datetime) -> float:
        hours_elapsed = max((now - occurred_at).total_seconds() / 3600.0, 0.0)
        return math.exp(-hours_elapsed / RECENCY_HALF_LIFE_HOURS)

    def evaluate(
        self,
        event: EnrichedEvent,
        signals: list[NormalizedSignal],
        now: datetime | None = None,
    ) -> EvidenceTrust:
        now = now or datetime.now(timezone.utc)
        occurred_at = event.occurred_at
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=timezone.utc)

        source_scores = [self._registry.get(s.source_id, 0.5) for s in signals] or [0.5]
        source_score = sum(source_scores) / len(source_scores)

        distinct_sources = {s.source_id for s in signals}
        corroboration = len(distinct_sources) - 1 if len(distinct_sources) > 0 else 0
        corroboration = max(corroboration, len(event.supporting))
        corroboration_norm = min(corroboration / 3, 1.0)

        recency_score = self._recency_score(occurred_at, now)

        contradiction_flag = bool(event.contradicting)

        completeness_fields = [event.summary, event.entities, event.occurred_at]
        completeness = sum(1 for f in completeness_fields if f) / len(
            completeness_fields
        )

        manipulation_risk: Literal["low", "medium", "high"] = "low"
        if corroboration == 0 and completeness < 1.0:
            manipulation_risk = "medium"

        trust_score = (
            source_score * 0.35
            + corroboration_norm * 0.25
            + recency_score * 0.20
            + completeness * 0.20
        ) * MANIPULATION_PENALTY[manipulation_risk]
        trust_score = max(0.0, min(1.0, trust_score))

        # Sprint 3.6.6: sum of any attached TriggerEvent.confidence_contribution
        # values -- a deterministic pass-through of the fixed registry constant
        # (e.g. +0.22, STOCK_EARNINGS_BEAT), not a new scoring formula computed
        # here. Empty event.trigger_events (every event before this sprint, and
        # every event without a real trigger) yields exactly 0.0, so trust_score
        # itself and every existing caller/test is unaffected.
        trigger_confidence_bonus = max(
            0.0, min(1.0, sum(t.confidence_contribution for t in event.trigger_events))
        )

        decision_trace = [
            DecisionTraceEntry(
                layer="evidence_trust",
                rule=f"trust_score={trust_score:.2f} "
                f"(source={source_score:.2f}, corroboration={corroboration}, "
                f"recency={recency_score:.2f}, manipulation_risk={manipulation_risk})",
                confidence=trust_score,
                timestamp=now,
            )
        ]
        if event.trigger_events:
            decision_trace.append(
                DecisionTraceEntry(
                    layer="evidence_trust",
                    rule=f"trigger_confidence_bonus={trigger_confidence_bonus:.2f} "
                    f"from {len(event.trigger_events)} attached trigger(s): "
                    f"{', '.join(t.trigger_code for t in event.trigger_events)}",
                    confidence=trigger_confidence_bonus,
                    timestamp=now,
                )
            )

        return EvidenceTrust(
            event_id=event.event_id,
            source_score=source_score,
            corroboration=corroboration,
            recency_score=recency_score,
            contradiction_flag=contradiction_flag,
            manipulation_risk=manipulation_risk,
            completeness=completeness,
            trust_score=trust_score,
            trigger_confidence_bonus=trigger_confidence_bonus,
            evaluated_at=now,
            decision_trace=decision_trace,
        )
