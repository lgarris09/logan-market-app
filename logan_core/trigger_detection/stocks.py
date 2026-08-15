from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from logan_core.contracts import (
    DecisionTraceEntry,
    NormalizedSignal,
    RawSignal,
    TriggerEvent,
)

# STOCK_EARNINGS_BEAT, per TRIGGER_REGISTRY_STOCKS.md's registered
# specification. Only this one trigger code is implemented in Sprint 3.6.6 --
# STOCK_EARNINGS_MISS, STOCK_EARNINGS_IN_LINE, STOCK_EARNINGS_QUALITY_WARNING,
# STOCK_GUIDANCE_RAISED/LOWERED, and every other registered stocks code
# remain SPECIFIED — NOT IMPLEMENTED (OD-009). Do not add them here without a
# real evaluated need; see docs/DECISIONS.md's Sprint 3.6.6 ADR.
STOCK_EARNINGS_BEAT = "STOCK_EARNINGS_BEAT"
_BEAT_PCT_THRESHOLD = 5.0
# Registry-specified fixed constant (TRIGGER_REGISTRY_STOCKS.md) -- not
# computed, not learned. See contracts/trigger.py's confidence_contribution
# comment.
_BEAT_CONFIDENCE_CONTRIBUTION = 0.22


def evaluate_earnings_beat_condition(
    actual_eps: Optional[float], consensus_eps: Optional[float]
) -> tuple[bool, Optional[float], str]:
    """Pure, directly-testable core of the STOCK_EARNINGS_BEAT fire condition
    (Phase 5): `actual_eps > consensus_eps AND beat_pct >= 5.0`, where
    `beat_pct = ((actual_eps - consensus_eps) / abs(consensus_eps)) * 100`.

    Returns (fired, beat_pct_or_None, reason) -- reason is always populated,
    for both the fire and no-fire paths, so "why did/didn't this fire" is
    never a silent None. No LLM/heuristic involved; every branch below is a
    deterministic comparison Phase 5 requires be traceable.
    """
    if actual_eps is None:
        return False, None, "no fire: actual_eps missing from provider data"
    if consensus_eps is None:
        return False, None, "no fire: consensus_eps missing from provider data"
    if consensus_eps == 0:
        return (
            False,
            None,
            "no fire: consensus_eps is zero, beat_pct is undefined (division by zero guarded)",
        )
    if actual_eps <= consensus_eps:
        return (
            False,
            None,
            f"no fire: actual_eps ({actual_eps}) does not exceed consensus_eps ({consensus_eps})",
        )

    beat_pct = ((actual_eps - consensus_eps) / abs(consensus_eps)) * 100
    if beat_pct < _BEAT_PCT_THRESHOLD:
        return (
            False,
            beat_pct,
            f"no fire: beat_pct ({beat_pct:.2f}) below the {_BEAT_PCT_THRESHOLD} threshold",
        )
    return (
        True,
        beat_pct,
        f"fired: actual_eps ({actual_eps}) > consensus_eps ({consensus_eps}), "
        f"beat_pct ({beat_pct:.2f}) >= {_BEAT_PCT_THRESHOLD}",
    )


class StocksTriggerEvaluator:
    """Sprint 3.6.6 — deterministic trigger detection for the stocks domain.
    Sits at the signal/normalization/event-resolution boundary (per the
    Orchestrator's wiring in orchestrator/pipeline.py): reads the same
    RawSignal a receptor emitted, decides whether a registered trigger code
    fires, and returns a TriggerEvent for World Model to attach -- it does
    not rank, score confidence, or touch presentation (those stay owned by
    Opportunity Engine / Evidence Trust+Conclusion Confidence / Presentation
    respectively, per this sprint's explicit layer-ownership instructions).

    Only earnings-signal detection (STOCK_EARNINGS_BEAT) is implemented.
    `evaluate()` returns None for every other signal_type -- not an error,
    just nothing to detect yet for this narrow slice.
    """

    def evaluate(
        self, raw: RawSignal, normalized: NormalizedSignal
    ) -> Optional[TriggerEvent]:
        if normalized.signal_type != "earnings_signal":
            return None
        if not isinstance(raw.raw_value, dict):
            return None

        actual_eps = raw.raw_value.get("actual_eps")
        consensus_eps = raw.raw_value.get("consensus_eps")
        fired, beat_pct, reason = evaluate_earnings_beat_condition(
            actual_eps, consensus_eps
        )
        if not fired:
            return None
        assert (
            beat_pct is not None
        )  # fired=True guarantees this (see evaluate_earnings_beat_condition)

        now = datetime.now(timezone.utc)
        # Context shape per TRIGGER_REGISTRY_STOCKS.md's documented fields for
        # this trigger code -- only fields the provider actually supplied are
        # included (Phase 1 instruction: never fabricate an absent field).
        context: dict = {
            "actual_eps": actual_eps,
            "consensus_eps": consensus_eps,
            "beat_pct": round(beat_pct, 2) if beat_pct is not None else None,
        }
        for optional_field in (
            "guidance_revised",
            "guidance_delta_pct",
            "fiscal_quarter",
        ):
            if optional_field in raw.raw_value:
                context[optional_field] = raw.raw_value[optional_field]

        return TriggerEvent(
            trigger_id=uuid4(),
            trigger_code=STOCK_EARNINGS_BEAT,
            trigger_class="catalyst",
            trigger_type="earnings_surprise",
            trigger_status="confirmed",
            domain=raw.domain,
            affected_entity_id=normalized.entity_id,
            direction="positive",
            raw_magnitude=beat_pct,
            confidence_contribution=_BEAT_CONFIDENCE_CONTRIBUTION,
            context=context,
            originating_signal_ids=[normalized.signal_id],
            source_id=raw.source_id,
            source_name=raw.source_name,
            event_timestamp=raw.captured_at,
            detected_timestamp=now,
            decision_trace=[
                DecisionTraceEntry(
                    layer="trigger_detection",
                    rule=f"{STOCK_EARNINGS_BEAT}: {reason}",
                    confidence=_BEAT_CONFIDENCE_CONTRIBUTION,
                    timestamp=now,
                )
            ],
        )
