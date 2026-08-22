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

# Sprint 3.6.7 -- two more registered stocks codes (TRIGGER_REGISTRY_STOCKS.md),
# generalizing the same architecture across two more real, live-verified FMP
# endpoints (/quote, /grades) rather than one-off implementations. Every
# other code considered for this pass (STOCK_GUIDANCE_RAISED/LOWERED,
# STOCK_OPTIONS_FLOW_SURGE, an "unusual volume"/"volatility spike" code with
# no registry entry at all) was inspected and deferred for lack of reliable
# provider data or lack of a registry-defined confidence value -- see the
# Sprint 3.6.7 ADR for the full inspection record; not silently skipped.
STOCK_PRICE_MOVE_SIGNIFICANT = "STOCK_PRICE_MOVE_SIGNIFICANT"
STOCK_ANALYST_UPGRADE = "STOCK_ANALYST_UPGRADE"
STOCK_ANALYST_DOWNGRADE = "STOCK_ANALYST_DOWNGRADE"

_BEAT_PCT_THRESHOLD = 5.0
_MISS_PCT_THRESHOLD = 5.0
_IN_LINE_PCT_THRESHOLD = 2.0
_PRICE_MOVE_PCT_THRESHOLD = 5.0

# Registry-specified fixed constants (TRIGGER_REGISTRY_STOCKS.md) -- not
# computed, not learned. See contracts/trigger.py's confidence_contribution
# comment and docs/DECISIONS.md's Sprint 3.6.6D ADR (owner decision: reuse
# only registry-defined constants, never invent new ones).
_BEAT_CONFIDENCE_CONTRIBUTION = 0.22
_MISS_CONFIDENCE_CONTRIBUTION = 0.20
_IN_LINE_CONFIDENCE_CONTRIBUTION = 0.0
_PRICE_MOVE_CONFIDENCE_CONTRIBUTION = 0.10
_ANALYST_UPGRADE_CONFIDENCE_CONTRIBUTION = 0.08
_ANALYST_DOWNGRADE_CONFIDENCE_CONTRIBUTION = 0.08


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


def evaluate_price_move_condition(
    change_pct: Optional[float],
) -> tuple[bool, Optional[float], str]:
    """Pure, directly-testable core of the STOCK_PRICE_MOVE_SIGNIFICANT fire
    condition (TRIGGER_REGISTRY_STOCKS.md): `abs(price_change_pct) >= 5.0` in
    a single trading session. Direction-agnostic by design (registry fire
    condition uses abs()) -- direction is carried separately in the resulting
    TriggerEvent.direction, not folded into this pure predicate.
    """
    if change_pct is None:
        return False, None, "no fire: change_pct missing from provider data"
    if abs(change_pct) < _PRICE_MOVE_PCT_THRESHOLD:
        return (
            False,
            change_pct,
            f"no fire: |change_pct| ({abs(change_pct):.2f}) below the "
            f"{_PRICE_MOVE_PCT_THRESHOLD} threshold",
        )
    return (
        True,
        change_pct,
        f"fired: |change_pct| ({abs(change_pct):.2f}) >= {_PRICE_MOVE_PCT_THRESHOLD}",
    )


def evaluate_analyst_grade_condition(
    action: Optional[str],
) -> tuple[Optional[str], str]:
    """Pure, directly-testable core of the STOCK_ANALYST_UPGRADE/
    STOCK_ANALYST_DOWNGRADE fire condition (TRIGGER_REGISTRY_STOCKS.md):
    "rating changes in positive/negative direction." Trusts the provider's
    own `action` classification rather than re-deriving a direction by
    comparing rating text (see GradeChange's docstring, receptors/providers/
    base.py, for why) -- no invented rating-ordinal hierarchy. Returns the
    trigger_code that fired (or None) plus a reason -- a two-way, not
    three-way, outcome, so the shape differs slightly from the (fired: bool,
    magnitude, reason) tuple the earnings/price-move evaluators use, but the
    "reason is always populated, for both the fire and no-fire paths"
    contract is the same.
    """
    if not action:
        return None, "no fire: action missing from provider data"
    normalized_action = action.strip().lower()
    if normalized_action == "upgrade":
        return (
            STOCK_ANALYST_UPGRADE,
            f"fired: action={action!r} is a positive rating change",
        )
    if normalized_action == "downgrade":
        return (
            STOCK_ANALYST_DOWNGRADE,
            f"fired: action={action!r} is a negative rating change",
        )
    return (
        None,
        f"no fire: action={action!r} is not an upgrade/downgrade "
        "(e.g. maintain/initiate/reiterate)",
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

    Earnings-signal detection (STOCK_EARNINGS_BEAT, STOCK_EARNINGS_MISS,
    STOCK_EARNINGS_IN_LINE) -- mutually exclusive by their fire conditions,
    checked in that order (order doesn't affect correctness since the bands
    don't overlap, but keeps beat/miss as the higher-signal checks read
    first). Sprint 3.6.7 generalizes this same evaluator across two more
    signal_types sharing the identical dispatch/build pattern:
    STOCK_PRICE_MOVE_SIGNIFICANT ("price_change" signal_type) and
    STOCK_ANALYST_UPGRADE/STOCK_ANALYST_DOWNGRADE ("analyst_change" signal_type).
    Each signal_type's fire conditions are self-contained (never cross-check
    another signal_type's raw_value fields) -- new signal types plug in as a
    new `elif normalized.signal_type == ...` branch in `evaluate()` plus a
    dedicated `_evaluate_*`/pure-condition-function pair, not a rewrite of
    this class. `evaluate()` returns None for any signal_type without a
    branch here, and for any signal_type's own "nothing qualifies" band --
    not an error, just nothing to detect this poll.
    """

    def evaluate(
        self, raw: RawSignal, normalized: NormalizedSignal
    ) -> Optional[TriggerEvent]:
        if not isinstance(raw.raw_value, dict):
            return None
        if normalized.signal_type == "earnings_signal":
            return self._evaluate_earnings(raw, normalized)
        if normalized.signal_type == "price_change":
            return self._evaluate_price_move(raw, normalized)
        if normalized.signal_type == "analyst_change":
            return self._evaluate_analyst_grade(raw, normalized)
        return None

    def _evaluate_earnings(
        self, raw: RawSignal, normalized: NormalizedSignal
    ) -> Optional[TriggerEvent]:
        assert isinstance(raw.raw_value, dict)  # evaluate() already checked this
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

    def _evaluate_price_move(
        self, raw: RawSignal, normalized: NormalizedSignal
    ) -> Optional[TriggerEvent]:
        assert isinstance(raw.raw_value, dict)  # evaluate() already checked this
        change_pct = raw.raw_value.get("change_pct")

        fired, magnitude, reason = evaluate_price_move_condition(change_pct)
        if not fired:
            return None
        assert magnitude is not None

        now = datetime.now(timezone.utc)
        # Context shape per TRIGGER_REGISTRY_STOCKS.md's STOCK_PRICE_MOVE_SIGNIFICANT
        # entry, restricted to fields this receptor actually supplies --
        # session_open/volume_vs_avg are in the registry's example but not
        # available from this provider (no average-volume baseline, no
        # separate session-open field carried through Quote), so they are
        # omitted, never fabricated.
        context: dict = {
            "price_change_pct": round(magnitude, 2),
            "direction": "up" if magnitude >= 0 else "down",
        }
        for optional_field, raw_key in (
            ("price", "price"),
            ("previous_close", "previous_close"),
        ):
            if raw_key in raw.raw_value:
                context[optional_field] = raw.raw_value[raw_key]

        return TriggerEvent(
            trigger_id=uuid4(),
            trigger_code=STOCK_PRICE_MOVE_SIGNIFICANT,
            trigger_class="catalyst",
            trigger_type="price_move",
            trigger_status="confirmed",
            domain=raw.domain,
            affected_entity_id=normalized.entity_id,
            direction="positive" if magnitude >= 0 else "negative",
            raw_magnitude=magnitude,
            confidence_contribution=_PRICE_MOVE_CONFIDENCE_CONTRIBUTION,
            context=context,
            originating_signal_ids=[normalized.signal_id],
            source_id=raw.source_id,
            source_name=raw.source_name,
            event_timestamp=raw.captured_at,
            detected_timestamp=now,
            decision_trace=[
                DecisionTraceEntry(
                    layer="trigger_detection",
                    rule=f"{STOCK_PRICE_MOVE_SIGNIFICANT}: {reason}",
                    confidence=_PRICE_MOVE_CONFIDENCE_CONTRIBUTION,
                    timestamp=now,
                )
            ],
        )

    def _evaluate_analyst_grade(
        self, raw: RawSignal, normalized: NormalizedSignal
    ) -> Optional[TriggerEvent]:
        assert isinstance(raw.raw_value, dict)  # evaluate() already checked this
        action = raw.raw_value.get("action")

        trigger_code, reason = evaluate_analyst_grade_condition(action)
        if trigger_code is None:
            return None

        confidence_contribution = (
            _ANALYST_UPGRADE_CONFIDENCE_CONTRIBUTION
            if trigger_code == STOCK_ANALYST_UPGRADE
            else _ANALYST_DOWNGRADE_CONFIDENCE_CONTRIBUTION
        )
        direction: TriggerDirection = (
            "positive" if trigger_code == STOCK_ANALYST_UPGRADE else "negative"
        )

        now = datetime.now(timezone.utc)
        # Context shape per TRIGGER_REGISTRY_STOCKS.md's STOCK_ANALYST_UPGRADE/
        # STOCK_ANALYST_DOWNGRADE entries, restricted to fields this receptor
        # actually supplies -- price_target_prior/price_target_new are in the
        # registry's example but come from a different, aggregated FMP
        # endpoint (not per-event), so they are omitted, never fabricated.
        context: dict = {"analyst_firm": raw.raw_value.get("grading_firm", "unknown")}
        for optional_field, raw_key in (
            ("prior_rating", "previous_rating"),
            ("new_rating", "new_rating"),
        ):
            if raw_key in raw.raw_value:
                context[optional_field] = raw.raw_value[raw_key]

        return TriggerEvent(
            trigger_id=uuid4(),
            trigger_code=trigger_code,
            trigger_class="catalyst",
            trigger_type="analyst_rating_change",
            trigger_status="confirmed",
            domain=raw.domain,
            affected_entity_id=normalized.entity_id,
            direction=direction,
            # No numeric magnitude exists for a categorical rating change --
            # 1.0 marks "the qualifying condition fired," matching this
            # field's role for other binary/categorical fire conditions
            # rather than leaving a numeric field without real meaning.
            raw_magnitude=1.0,
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
