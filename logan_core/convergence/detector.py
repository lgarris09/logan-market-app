from dataclasses import dataclass, field
from typing import Optional

from logan_core.contracts import TriggerEvent


@dataclass(frozen=True)
class ConvergenceResolution:
    """Result of resolving every TriggerEvent attached to one EnrichedEvent
    down to a single confidence contribution. Not a pipeline data contract
    (07_DATA_CONTRACTS.md) -- an internal computation result consumed only by
    EvidenceTrustEngine, structured enough to carry which trigger won and why
    for decision_trace purposes.
    """

    confidence_bonus: float
    dominant_trigger: Optional[TriggerEvent]
    trigger_codes: list[str] = field(default_factory=list)


class ConvergenceDetector:
    """Sprint 3.6.6D — smallest real foundation for associating multiple
    TriggerEvents that already live on one EnrichedEvent with that single
    underlying entity/event, instead of letting their confidence
    contributions silently combine into an inflated or double-counted
    opportunity.

    NOT the full canonical Convergence Detector described in
    docs/specs/Logan_Documentation_v3.1.4/source_material/04_HIT_DETECTION.md
    and TRIGGER_REGISTRY_STOCKS.md's STOCK_CONVERGENCE_MULTI_SOURCE. That is
    a Hit-Detection-layer component: it watches independent raw signal
    sources across domains *before* trigger detection, within a time window,
    and itself emits a TriggerEvent with its own OpportunityEvidence output.
    Neither OpportunityEvidence nor the Hit Detection layer exist in this
    codebase (SPECIFIED — NOT IMPLEMENTED, OD-009), and building them is a
    separate, larger decision, not made this sprint. This component instead
    solves a narrower, already-real problem one layer downstream: World
    Model already merges signals sharing the same (entity_id, signal_type)
    within its dedup window onto one EnrichedEvent (see world_model/model.py)
    -- so multiple TriggerEvents can legitimately already coexist on a single
    event today (e.g. a corrected/duplicate report, or in the future,
    distinct trigger codes on the same signal_type). Widening World Model's
    merge key to associate *different* signal_types for the same entity into
    one event (true cross-signal-type convergence) is also a separate,
    larger decision -- not made this sprint; see docs/DECISIONS.md's Sprint
    3.6.6D ADR.

    Owner decision, 2026-08-18: when more than one TriggerEvent is attached
    to one event, do not sum their confidence_contribution values (that
    silently double-counts correlated evidence) and do not drop any of them
    either (every fired TriggerEvent must remain visible for auditability,
    on EnrichedEvent.trigger_events -- this resolver only picks which single
    contribution feeds EvidenceTrust.trigger_confidence_bonus, it never
    removes evidence). Use the single strongest applicable trigger's
    contribution instead.

    Known limitation, not solved here: this "pick the max" rule assumes
    every trigger's contribution is independently additive-or-nothing. It
    does not yet handle *companion* triggers designed to net against another
    (e.g. STOCK_EARNINGS_QUALITY_WARNING's registered -0.15, meant to reduce
    STOCK_EARNINGS_BEAT's +0.22 specifically, not compete with it as a
    separate "strongest signal" candidate) -- that trigger code is not
    implemented yet, so this is a documented gap to revisit if/when it is,
    not a bug in what's built today.
    """

    def resolve(self, trigger_events: list[TriggerEvent]) -> ConvergenceResolution:
        if not trigger_events:
            return ConvergenceResolution(confidence_bonus=0.0, dominant_trigger=None)

        dominant = max(trigger_events, key=lambda t: t.confidence_contribution)
        confidence_bonus = max(0.0, min(1.0, dominant.confidence_contribution))
        return ConvergenceResolution(
            confidence_bonus=confidence_bonus,
            dominant_trigger=dominant,
            trigger_codes=[t.trigger_code for t in trigger_events],
        )
