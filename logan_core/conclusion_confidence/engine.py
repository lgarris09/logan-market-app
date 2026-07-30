from datetime import datetime, timezone
from typing import Literal, Optional

from logan_core.contracts import ConclusionConfidence, EvidenceTrust, MentalModel, ReasoningResult


class ConclusionConfidenceEngine:
    """Layer 9 — evaluates how strongly evidence supports the reasoning conclusion.
    Separate from Evidence Trust: a trustworthy source does not guarantee a trustworthy
    conclusion. Forbidden per spec: writing to Memory, modifying reasoning output,
    suppressing events.
    """

    def evaluate(
        self,
        reasoning: ReasoningResult,
        trust: EvidenceTrust,
        mental_model: Optional[MentalModel] = None,
    ) -> ConclusionConfidence:
        mental_model_weight = mental_model.confidence if mental_model is not None else 0.5
        confidence_score = trust.trust_score * 0.75 + mental_model_weight * 0.25
        if trust.contradiction_flag:
            confidence_score *= 0.7
        confidence_score = max(0.0, min(1.0, confidence_score))

        classification: Literal["fact", "inference", "hypothesis", "speculation"]
        if trust.source_score >= 0.85 and trust.corroboration >= 2:
            classification = "fact"
        elif confidence_score >= 0.55:
            classification = "inference"
        elif confidence_score >= 0.35:
            classification = "hypothesis"
        else:
            classification = "speculation"

        alternatives: list[str] = []
        if classification in ("hypothesis", "speculation"):
            alternatives.append(
                "This could also reflect noise, a single-source report, or a temporary market reaction."
            )

        limiting_factors: list[str] = []
        if trust.corroboration < 2:
            limiting_factors.append("Only one independent source has corroborated this so far.")
        if trust.completeness < 1.0:
            limiting_factors.append("Some expected event details are missing.")
        if trust.contradiction_flag:
            limiting_factors.append("Contradicting signals exist for this event.")

        return ConclusionConfidence(
            event_id=reasoning.event_id,
            confidence_score=confidence_score,
            classification=classification,
            alternatives=alternatives,
            limiting_factors=limiting_factors,
            evaluated_at=datetime.now(timezone.utc),
        )
