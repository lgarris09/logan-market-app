from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from logan_core.contracts import (
    DecisionTraceEntry,
    Domain,
    MentalModel,
    ReasoningResult,
)

# V1 confidence adjustment per stance — a shift itself is the signal, per spec.
_STANCE_DELTA: dict[str, float] = {
    "new": 0.0,
    "confirms": 0.10,
    "contradicts": -0.15,
    "complicates": -0.05,
}


# STRATUS reliability correction (residual memory growth, ADR-074): a
# hypothesis is updated on every poll of its entity, and each update appended
# one entry to `decision_trace` and one event id to `supporting`/`opposing`
# with no cap -- growth for the life of the process. Only the most recent
# entries are kept now, the same bound and the same keep-newest rule
# WorldModel uses for its own per-event history (MAX_RECENT_EVENT_HISTORY).
# `confidence` and `trend` are computed from the previous confidence value,
# never from these lists, so bounding them changes no computed result -- and
# nothing reads them in V1 (ADR-015: Mental Model output does not influence
# the Opportunity Engine or Conclusion Confidence).
MAX_RECENT_HYPOTHESIS_HISTORY = 50


def _bounded_history(history: list) -> list:
    if len(history) <= MAX_RECENT_HYPOTHESIS_HISTORY:
        return history
    return history[-MAX_RECENT_HYPOTHESIS_HISTORY:]


class MentalModelEngine:
    """Layer 8 — built in Phase 1 as a pass-through slot (ADR-015). Stores hypotheses
    and tracks confidence, but its output does NOT influence the Opportunity Engine in
    V1 — the Orchestrator must not wire MentalModelDelta into Opportunity Engine yet.
    """

    def __init__(self) -> None:
        self._hypotheses: dict[str, MentalModel] = {}

    def process(
        self, reasoning: ReasoningResult, domain: Domain
    ) -> tuple[ReasoningResult, MentalModel]:
        key = f"{domain}:{reasoning.significance.split(':')[0].strip()}"
        now = datetime.now(timezone.utc)
        existing = self._hypotheses.get(key)

        delta = _STANCE_DELTA.get(reasoning.stance, 0.0)

        if existing is None:
            model = MentalModel(
                model_id=uuid4(),
                domain=domain,
                hypothesis=reasoning.significance,
                confidence=max(0.0, min(1.0, 0.5 + delta)),
                supporting=[str(reasoning.event_id)] if delta >= 0 else [],
                opposing=[str(reasoning.event_id)] if delta < 0 else [],
                trend="new",
                created_at=now,
                last_updated=now,
                decision_trace=[
                    DecisionTraceEntry(
                        layer="mental_model",
                        rule=f"new hypothesis for key={key!r}, stance={reasoning.stance} "
                        f"(delta={delta:+.2f})",
                        timestamp=now,
                    )
                ],
            )
        else:
            new_confidence = max(0.0, min(1.0, existing.confidence + delta))
            trend: Literal["strengthening", "weakening", "stable", "new", "retired"]
            if new_confidence > existing.confidence:
                trend = "strengthening"
            elif new_confidence < existing.confidence:
                trend = "weakening"
            else:
                trend = "stable"
            supporting = list(existing.supporting)
            opposing = list(existing.opposing)
            (supporting if delta >= 0 else opposing).append(str(reasoning.event_id))
            model = existing.model_copy(
                update={
                    "confidence": new_confidence,
                    "trend": trend,
                    "supporting": _bounded_history(supporting),
                    "opposing": _bounded_history(opposing),
                    "last_updated": now,
                    "decision_trace": _bounded_history(
                        existing.decision_trace
                        + [
                            DecisionTraceEntry(
                                layer="mental_model",
                                rule=f"trend={trend} from stance={reasoning.stance} (delta={delta:+.2f})",
                                confidence=new_confidence,
                                timestamp=now,
                            )
                        ]
                    ),
                }
            )

        self._hypotheses[key] = model
        # V1: ReasoningResult passes through unchanged.
        return reasoning, model
