from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from logan_core.contracts import (
    DecisionTraceEntry,
    NormalizedSignal,
    RawSignal,
    TriggerDirection,
    TriggerEvent,
)

# STOCK_EARNINGS_BEAT / STOCK_EARNINGS_MISS / STOCK_EARNINGS_IN_LINE, per
# TRIGGER_REGISTRY_STOCKS.md's registered specification. These three share one
# provider (actual_eps/consensus_eps) and are mutually exclusive by
# construction (>=5% up, >=5% down, or <2% either way -- the 2-5% band on
# either side is a deliberate registry-defined dead zone where none fire).
# Every other registered stocks code (STOCK_EARNINGS_QUALITY_WARNING,
# STOCK_GUIDANCE_RAISED/LOWERED, STOCK_OPTIONS_FLOW_SURGE, etc.) remains
# SPECIFIED — NOT IMPLEMENTED (OD-009): each needs data this FMP integration
# does not fetch today (one-time-item flags, prior-guidance history, options
# flow, filings, analyst ratings) -- see the Sprint 3.6.6D ADR for why those
# were not added alongside these three. Do not add more without a real
# evaluated need and without inspecting provider data availability first.
STOCK_EARNINGS_BEAT = "STOCK_EARNINGS_BEAT"
STOCK_EARNINGS_MISS = "STOCK_EARNINGS_MISS"
STOCK_EARNINGS_IN_LINE = "STOCK_EARNINGS_IN_LINE"

_BEAT_PCT_THRESHOLD = 5.0
_MISS_PCT_THRESHOLD = 5.0
_IN_LINE_PCT_THRESHOLD = 2.0

# Registry-specified fixed constants (TRIGGER_REGISTRY_STOCKS.md) -- not
# computed, not learned. See contracts/trigger.py's confidence_contribution
# comment and docs/DECISIONS.md's Sprint 3.6.6D ADR (owner decision: reuse
# only registry-defined constants, never invent new ones).
_BEAT_CONFIDENCE_CONTRIBUTION = 0.22
_MISS_CONFIDENCE_CONTRIBUTION = 0.20
_IN_LINE_CONFIDENCE_CONTRIBUTION = 0.0


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


def evaluate_earnings_miss_condition(
    actual_eps: Optional[float], consensus_eps: Optional[float]
) -> tuple[bool, Optional[float], str]:
    """Pure, directly-testable core of the STOCK_EARNINGS_MISS fire condition:
    `actual_eps < consensus_eps AND miss_pct >= 5.0`, where
    `miss_pct = ((consensus_eps - actual_eps) / abs(consensus_eps)) * 100`.
    Mirrors evaluate_earnings_beat_condition's structure and edge-case
    handling exactly (missing/zero consensus), per TRIGGER_REGISTRY_STOCKS.md.
    """
    if actual_eps is None:
        return False, None, "no fire: actual_eps missing from provider data"
    if consensus_eps is None:
        return False, None, "no fire: consensus_eps missing from provider data"
    if consensus_eps == 0:
        return (
            False,
            None,
            "no fire: consensus_eps is zero, miss_pct is undefined (division by zero guarded)",
        )
    if actual_eps >= consensus_eps:
        return (
            False,
            None,
            f"no fire: actual_eps ({actual_eps}) does not fall below consensus_eps ({consensus_eps})",
        )

    miss_pct = ((consensus_eps - actual_eps) / abs(consensus_eps)) * 100
    if miss_pct < _MISS_PCT_THRESHOLD:
        return (
            False,
            miss_pct,
            f"no fire: miss_pct ({miss_pct:.2f}) below the {_MISS_PCT_THRESHOLD} threshold",
        )
    return (
        True,
        miss_pct,
        f"fired: actual_eps ({actual_eps}) < consensus_eps ({consensus_eps}), "
        f"miss_pct ({miss_pct:.2f}) >= {_MISS_PCT_THRESHOLD}",
    )


def evaluate_earnings_in_line_condition(
    actual_eps: Optional[float], consensus_eps: Optional[float]
) -> tuple[bool, Optional[float], str]:
    """Pure, directly-testable core of the STOCK_EARNINGS_IN_LINE fire
    condition: `abs(beat_pct) < 2.0`, where `beat_pct` is the same signed
    percentage evaluate_earnings_beat_condition computes, just measured
    regardless of direction (unlike that function, this does not require
    actual_eps > consensus_eps first). Registry field name for the context
    magnitude is `beat_pct` even here (TRIGGER_REGISTRY_STOCKS.md's own
    example) since it's the same signed measure, just close to zero.
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

    beat_pct = ((actual_eps - consensus_eps) / abs(consensus_eps)) * 100
    if abs(beat_pct) >= _IN_LINE_PCT_THRESHOLD:
        return (
            False,
            beat_pct,
            f"no fire: |beat_pct| ({abs(beat_pct):.2f}) at or above the "
            f"{_IN_LINE_PCT_THRESHOLD} in-line threshold",
        )
    return (
        True,
        beat_pct,
        f"fired: actual_eps ({actual_eps}) within {_IN_LINE_PCT_THRESHOLD}% of "
        f"consensus_eps ({consensus_eps}), beat_pct ({beat_pct:.2f})",
    )


class StocksTriggerEvaluator:
    """Sprint 3.6.6 (extended Sprint 3.6.6D) — deterministic trigger detection
    for the stocks domain. Sits at the signal/normalization/event-resolution
    boundary (per the Orchestrator's wiring in orchestrator/pipeline.py):
    reads the same RawSignal a receptor emitted, decides whether a registered
    trigger code fires, and returns a TriggerEvent for World Model to attach
    -- it does not rank, score confidence, or touch presentation (those stay
    owned by Opportunity Engine / Evidence Trust+Conclusion Confidence /
    Presentation respectively, per this sprint's explicit layer-ownership
    instructions).

    Only earnings-signal detection is implemented: STOCK_EARNINGS_BEAT,
    STOCK_EARNINGS_MISS, STOCK_EARNINGS_IN_LINE -- mutually exclusive by
    their fire conditions, checked in that order (order doesn't affect
    correctness since the bands don't overlap, but keeps beat/miss as the
    higher-signal checks read first). `evaluate()` returns None for every
    other signal_type, and for the 2-5% dead zone where none of the three
    fire -- not an error, just nothing to detect yet for this narrow slice.
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

        beat_fired, beat_pct, beat_reason = evaluate_earnings_beat_condition(
            actual_eps, consensus_eps
        )
        if beat_fired:
            assert beat_pct is not None
            assert actual_eps is not None and consensus_eps is not None
            return self._build_trigger_event(
                trigger_code=STOCK_EARNINGS_BEAT,
                trigger_class="catalyst",
                direction="positive",
                magnitude_field="beat_pct",
                magnitude=beat_pct,
                confidence_contribution=_BEAT_CONFIDENCE_CONTRIBUTION,
                reason=beat_reason,
                raw=raw,
                normalized=normalized,
                actual_eps=actual_eps,
                consensus_eps=consensus_eps,
            )

        miss_fired, miss_pct, miss_reason = evaluate_earnings_miss_condition(
            actual_eps, consensus_eps
        )
        if miss_fired:
            assert miss_pct is not None
            assert actual_eps is not None and consensus_eps is not None
            return self._build_trigger_event(
                trigger_code=STOCK_EARNINGS_MISS,
                trigger_class="catalyst",
                direction="negative",
                magnitude_field="miss_pct",
                magnitude=miss_pct,
                confidence_contribution=_MISS_CONFIDENCE_CONTRIBUTION,
                reason=miss_reason,
                raw=raw,
                normalized=normalized,
                actual_eps=actual_eps,
                consensus_eps=consensus_eps,
            )

        in_line_fired, in_line_pct, in_line_reason = (
            evaluate_earnings_in_line_condition(actual_eps, consensus_eps)
        )
        if in_line_fired:
            assert in_line_pct is not None
            assert actual_eps is not None and consensus_eps is not None
            return self._build_trigger_event(
                trigger_code=STOCK_EARNINGS_IN_LINE,
                trigger_class="confirmation",
                direction="neutral",
                magnitude_field="beat_pct",
                magnitude=in_line_pct,
                confidence_contribution=_IN_LINE_CONFIDENCE_CONTRIBUTION,
                reason=in_line_reason,
                raw=raw,
                normalized=normalized,
                actual_eps=actual_eps,
                consensus_eps=consensus_eps,
            )

        return None

    def _build_trigger_event(
        self,
        *,
        trigger_code: str,
        trigger_class: str,
        direction: TriggerDirection,
        magnitude_field: str,
        magnitude: float,
        confidence_contribution: float,
        reason: str,
        raw: RawSignal,
        normalized: NormalizedSignal,
        actual_eps: float,
        consensus_eps: float,
    ) -> TriggerEvent:
        assert isinstance(raw.raw_value, dict)  # re-narrowed: evaluate() already
        # checked this, but that narrowing doesn't cross the method boundary.
        now = datetime.now(timezone.utc)
        # Context shape per TRIGGER_REGISTRY_STOCKS.md's documented fields for
        # each trigger code -- only fields the provider actually supplied are
        # included (Phase 1/7 instruction: never fabricate an absent field).
        context: dict = {
            "actual_eps": actual_eps,
            "consensus_eps": consensus_eps,
            magnitude_field: round(magnitude, 2),
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
            trigger_code=trigger_code,
            trigger_class=trigger_class,  # type: ignore[arg-type]
            trigger_type="earnings_surprise",
            trigger_status="confirmed",
            domain=raw.domain,
            affected_entity_id=normalized.entity_id,
            direction=direction,
            raw_magnitude=magnitude,
            confidence_contribution=confidence_contribution,
            context=context,
            originating_signal_ids=[normalized.signal_id],
            source_id=raw.source_id,
            source_name=raw.source_name,
            event_timestamp=raw.captured_at,
            detected_timestamp=now,
            decision_trace=[
                DecisionTraceEntry(
                    layer="trigger_detection",
                    rule=f"{trigger_code}: {reason}",
                    confidence=confidence_contribution,
                    timestamp=now,
                )
            ],
        )
