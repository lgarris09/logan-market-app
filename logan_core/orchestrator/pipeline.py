import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional, TypeVar
from uuid import UUID, uuid4

from logan_core.active_context import ActiveContextBuilder
from logan_core.community_intelligence import (
    CommunityIntelligenceEngine,
    EngagementSample,
)
from logan_core.conclusion_confidence import ConclusionConfidenceEngine
from logan_core.contracts import (
    ActiveContext,
    AttentionRecommendation,
    CommunitySignal,
    ConclusionConfidence,
    DecisionTraceEntry,
    DeliveredItem,
    Domain,
    EnrichedEvent,
    EvidenceTrust,
    ExecutionMetrics,
    ExecutionTrace,
    FeedbackSignal,
    InteractionType,
    LifecycleDelta,
    MarketEvidenceInput,
    MemoryWrite,
    MentalModel,
    NormalizedSignal,
    PolicyResult,
    PrioritizedItem,
    RawSignal,
    ReasoningResult,
    TriggerEvent,
    UserModel,
)
from logan_core.convergence import StockConvergenceTracker
from logan_core.evidence_trust import EvidenceTrustEngine
from logan_core.feedback import FeedbackEngine
from logan_core.learning import LearningEngine
from logan_core.memory import MemoryStore
from logan_core.mental_model import MentalModelEngine
from logan_core.normalization import Normalizer
from logan_core.opportunity import OpportunityEngine
from logan_core.opportunity_lifecycle import OpportunityLifecycleTracker
from logan_core.policy import PolicyEngine
from logan_core.presentation import PresentationEngine
from logan_core.prioritization import PrioritizationEngine
from logan_core.reasoning import ReasoningEngine
from logan_core.trigger_detection import StocksTriggerEvaluator
from logan_core.user_model import UserModelBuilder
from logan_core.world_model import WorldModel

from .history import OperationalHistoryStore

T = TypeVar("T")


class RetryableLayerError(RuntimeError):
    """A transient failure — the Orchestrator retries the layer call."""


class CriticalLayerError(RuntimeError):
    """An unrecoverable failure — the Orchestrator halts the pipeline."""


@dataclass
class PipelineDependencies:
    normalizer: Normalizer = field(default_factory=Normalizer)
    world_model: WorldModel = field(default_factory=WorldModel)
    evidence_trust: EvidenceTrustEngine = field(default_factory=EvidenceTrustEngine)
    community_intelligence: CommunityIntelligenceEngine = field(
        default_factory=CommunityIntelligenceEngine
    )
    operational_history: OperationalHistoryStore = field(
        default_factory=OperationalHistoryStore
    )
    memory_store: MemoryStore = field(default_factory=MemoryStore)
    user_model_builder: UserModelBuilder = field(default_factory=UserModelBuilder)
    active_context_builder: ActiveContextBuilder = field(
        default_factory=ActiveContextBuilder
    )
    reasoning_engine: ReasoningEngine = field(default_factory=ReasoningEngine)
    mental_model_engine: MentalModelEngine = field(default_factory=MentalModelEngine)
    conclusion_confidence_engine: ConclusionConfidenceEngine = field(
        default_factory=ConclusionConfidenceEngine
    )
    opportunity_engine: OpportunityEngine = field(default_factory=OpportunityEngine)
    policy_engine: PolicyEngine = field(default_factory=PolicyEngine)
    prioritization_engine: PrioritizationEngine = field(
        default_factory=PrioritizationEngine
    )
    presentation_engine: PresentationEngine = field(default_factory=PresentationEngine)
    feedback_engine: FeedbackEngine = field(default_factory=FeedbackEngine)
    learning_engine: LearningEngine = field(init=False)
    # Sprint 3.6.6 — None by default, so every existing caller (including
    # every test using the default `orchestrator` fixture) gets the exact
    # same pipeline behavior and ExecutionTrace layer sequence as before this
    # sprint: run() below only calls this (and only then does a
    # "trigger_detection" layer appear in the trace) when a caller
    # explicitly wires one in. Typed as StocksTriggerEvaluator specifically
    # (not a generic multi-domain dispatcher) -- this sprint implements one
    # domain's one trigger code; building a registry/dispatch system for
    # domains that don't have an evaluator yet would be speculative.
    trigger_detector: Optional[StocksTriggerEvaluator] = None
    # Sprint 3.6.7 Block 2 -- None by default, same opt-in discipline as
    # trigger_detector above: every existing caller/test that doesn't wire
    # one in gets identical behavior (no "convergence_tracker" trace layer,
    # no STOCK_CONVERGENCE_MULTI_SOURCE ever attached). Must be constructed
    # once and reused across calls (like world_model) for its 30-minute
    # window to observe anything real -- see StockConvergenceTracker's own
    # docstring and backend/app/logan_feed.py's process-lifetime Orchestrator.
    convergence_tracker: Optional[StockConvergenceTracker] = None
    # Sprint 3.6.9 Stock Opportunity Logic V2 -- None by default, identical
    # opt-in discipline to trigger_detector/convergence_tracker above: every
    # existing caller/test that doesn't wire one in gets byte-for-byte
    # unchanged behavior (no "opportunity_lifecycle" trace layer, no
    # lifecycle_delta on PipelineResult, changed_since_view keeps defaulting
    # to prioritize()'s own pre-existing True). Must be constructed once and
    # reused across calls (like world_model/convergence_tracker) -- its
    # entity-keyed history is meaningless if reconstructed per call. See
    # docs/DECISIONS.md's Sprint 3.6.9 Stock Opportunity Logic V2 ADR.
    lifecycle_tracker: Optional[OpportunityLifecycleTracker] = None

    def __post_init__(self) -> None:
        self.learning_engine = LearningEngine(self.memory_store)


@dataclass
class PipelineResult:
    pipeline_run_id: UUID
    normalized_signals: list[NormalizedSignal]
    event: EnrichedEvent
    trust: EvidenceTrust
    community: CommunitySignal
    user_model: UserModel
    active_context: ActiveContext
    reasoning: ReasoningResult
    mental_model: MentalModel
    confidence: ConclusionConfidence
    recommendation: AttentionRecommendation
    policy_result: PolicyResult
    prioritized_item: PrioritizedItem
    delivered_item: DeliveredItem
    trace: ExecutionTrace
    # Sprint 3.6.9 Stock Opportunity Logic V2 -- None whenever no
    # lifecycle_tracker was wired in (every pre-existing caller/test).
    lifecycle_delta: Optional[LifecycleDelta] = None


def _collapse_duplicate_event_ids(events: list[EnrichedEvent]) -> list[EnrichedEvent]:
    """Collapses repeated `world_model.process()` results that resolved to the
    same underlying `event_id` (e.g. two same-signal_type raw_signals in one
    `run()` call, like TSLA's corroborating second signal -- World Model's own
    `(entity_id, signal_type)` dedup already merged those into one event, see
    world_model/model.py, unchanged by this) down to the single most
    up-to-date version of that event. This is exactly the value the old
    single-`event` loop variable always held whenever every raw_signal shared
    one signal_type -- preserved here byte-for-byte, not a new behavior.
    Preserves first-seen order, so the earliest-detected signal_type stays
    "primary" if a genuine cross-signal_type merge follows.
    """
    latest_by_id: dict[UUID, EnrichedEvent] = {}
    order: list[UUID] = []
    for event in events:
        if event.event_id not in latest_by_id:
            order.append(event.event_id)
        latest_by_id[event.event_id] = event
    return [latest_by_id[event_id] for event_id in order]


def _merge_entity_events(events: list[EnrichedEvent]) -> EnrichedEvent:
    """Sprint 3.6.7 Block 2 fix: combines multiple genuinely distinct
    per-signal_type EnrichedEvents for one entity (produced because World
    Model's `(entity_id, signal_type)` dedup key -- deliberately left
    unchanged -- gives each distinct signal_type its own event) into one
    coherent opportunity, instead of letting only the last-processed
    raw_signal's event silently survive (ADR-051 finding 5).

    Unions rather than replaces: every contributing signal's entities/
    signal_ids/supporting/downstream/trigger_events remain visible on the
    result -- convergence (or any multi-signal entity) enriches the entity's
    opportunity, it never displaces the individual signals that fed it. A
    no-op returning `events[0]` unchanged whenever there's only one distinct
    event, so every existing single-signal-type caller/test is byte-for-byte
    unaffected.

    `is_new`/`occurred_at`/`summary`/`event_id` are deliberately taken only
    from the primary (first-processed) event, not combined -- these describe
    "is this specific signal new," which stays well-defined per signal_type;
    OR-ing `is_new` across siblings would wrongly mark an entity's whole
    opportunity as new merely because one of several signal_types happened to
    be new this poll while others were pure corroboration.
    """
    if len(events) == 1:
        return events[0]

    primary = events[0]
    entities = list(primary.entities)
    entity_ids = {e.entity_id for e in entities}
    signal_ids = list(primary.signal_ids)
    supporting = list(primary.supporting)
    downstream = list(primary.downstream)
    trigger_events = list(primary.trigger_events)
    trigger_codes = {t.trigger_code for t in trigger_events}
    decision_trace = list(primary.decision_trace)
    enriched_at = primary.enriched_at

    for other in events[1:]:
        for entity in other.entities:
            if entity.entity_id not in entity_ids:
                entities.append(entity)
                entity_ids.add(entity.entity_id)
        signal_ids.extend(sid for sid in other.signal_ids if sid not in signal_ids)
        supporting.extend(sid for sid in other.supporting if sid not in supporting)
        for downstream_id in other.downstream:
            if downstream_id not in downstream:
                downstream.append(downstream_id)
        for trigger in other.trigger_events:
            if trigger.trigger_code not in trigger_codes:
                trigger_events.append(trigger)
                trigger_codes.add(trigger.trigger_code)
        decision_trace.append(
            DecisionTraceEntry(
                layer="orchestrator",
                rule=(
                    f"merged sibling event {other.event_id} "
                    f"(signal_ids={[str(s) for s in other.signal_ids]}) into "
                    "this entity's coherent opportunity"
                ),
                timestamp=other.enriched_at,
            )
        )
        if other.enriched_at > enriched_at:
            enriched_at = other.enriched_at

    return primary.model_copy(
        update={
            "entities": entities,
            "signal_ids": signal_ids,
            "supporting": supporting,
            "downstream": downstream,
            "trigger_events": trigger_events,
            "decision_trace": decision_trace,
            "enriched_at": enriched_at,
        }
    )


def _attach_trigger(event: EnrichedEvent, trigger: TriggerEvent) -> EnrichedEvent:
    """Attaches (replace-by-trigger_code, not append/stack) a synthetically
    computed TriggerEvent -- currently only StockConvergenceTracker's
    STOCK_CONVERGENCE_MULTI_SOURCE -- onto an already-resolved coherent
    event. Mirrors WorldModel.process()'s own replace-by-trigger_code
    discipline (world_model/model.py) so a still-active convergence episode
    re-describing itself on a later poll replaces its own prior entry rather
    than accumulating duplicates.
    """
    return event.model_copy(
        update={
            "trigger_events": [
                t
                for t in event.trigger_events
                if t.trigger_code != trigger.trigger_code
            ]
            + [trigger]
        }
    )


class Orchestrator:
    """Owns the execution pipeline. Contains no business logic of its own — coordinates
    layers, retries, and persists Operational History (ADR-016), which no other layer
    is permitted to write.
    """

    RETRY_LIMIT = 3

    def __init__(
        self, deps: Optional[PipelineDependencies] = None, retry_sleep: float = 0.0
    ) -> None:
        self.deps = deps or PipelineDependencies()
        self._retry_sleep = retry_sleep

    def _execute(
        self,
        trace: ExecutionTrace,
        layer: str,
        func: Callable[[], T],
        event_id: Optional[UUID] = None,
    ) -> T:
        retries = 0
        warnings: list[str] = []
        started = time.perf_counter()
        while True:
            try:
                result = func()
                latency_ms = int((time.perf_counter() - started) * 1000)
                trace.layers.append(
                    ExecutionMetrics(
                        layer=layer,
                        pipeline_run_id=trace.pipeline_run_id,
                        event_id=event_id,
                        latency_ms=latency_ms,
                        success=True,
                        warnings=warnings,
                        retries=retries,
                        recorded_at=datetime.now(timezone.utc),
                    )
                )
                return result
            except RetryableLayerError as exc:
                retries += 1
                warnings.append(str(exc))
                if retries > self.RETRY_LIMIT:
                    latency_ms = int((time.perf_counter() - started) * 1000)
                    trace.layers.append(
                        ExecutionMetrics(
                            layer=layer,
                            pipeline_run_id=trace.pipeline_run_id,
                            event_id=event_id,
                            latency_ms=latency_ms,
                            success=False,
                            warnings=warnings,
                            retries=retries,
                            recorded_at=datetime.now(timezone.utc),
                        )
                    )
                    trace.status = "partial"
                    raise CriticalLayerError(
                        f"{layer} failed after {self.RETRY_LIMIT} retries: {exc}"
                    ) from exc
                if self._retry_sleep:
                    time.sleep(self._retry_sleep)
            except (
                Exception
            ) as exc:  # noqa: BLE001 — critical failure halts the pipeline
                latency_ms = int((time.perf_counter() - started) * 1000)
                trace.layers.append(
                    ExecutionMetrics(
                        layer=layer,
                        pipeline_run_id=trace.pipeline_run_id,
                        event_id=event_id,
                        latency_ms=latency_ms,
                        success=False,
                        warnings=warnings,
                        retries=retries,
                        recorded_at=datetime.now(timezone.utc),
                    )
                )
                trace.status = "failed"
                trace.error = str(exc)
                raise CriticalLayerError(f"{layer} failed: {exc}") from exc

    def run(
        self,
        raw_signals: list[RawSignal],
        user_id: str,
        user_model: UserModel,
        engagement_samples: list[EngagementSample],
        domain: Domain,
        current_question: Optional[str] = None,
        market_evidence: Optional[MarketEvidenceInput] = None,
        is_watched: bool = False,
    ) -> PipelineResult:
        """Runs the primary vertical-slice pipeline: Raw Signal through Presentation.

        `market_evidence` (Stock Opportunity Logic V2.2, Optional, default
        None) is forwarded to `lifecycle_tracker.observe()` unchanged when a
        tracker is wired in -- every pre-V2.2 caller that never passes it
        gets byte-for-byte unchanged behavior (trajectory stays "STEADY",
        evidence stays None). `trigger_directions` is never a caller
        parameter -- it's derived here from this event's own
        `TriggerEvent.direction` values, already real, already implemented
        data (contracts/trigger.py), not a new input surface.
        Feedback and Learning are separate, explicit calls (run_feedback_loop) — see
        LOGAN_IMPLEMENTATION_PLAN.md's resolved first-operational-test scope.
        """
        pipeline_run_id = uuid4()
        trace = ExecutionTrace(
            pipeline_run_id=pipeline_run_id,
            started_at=datetime.now(timezone.utc),
            status="running",
        )

        normalized_signals: list[NormalizedSignal] = []
        # Sprint 3.6.7 Block 2: every raw_signal's own resulting EnrichedEvent
        # is now kept (not just the last one) so multiple distinct
        # signal_types for the same entity can be combined into one coherent
        # opportunity after the loop -- see _collapse_duplicate_event_ids/
        # _merge_entity_events below and ADR-051 finding 5.
        entity_events: list[EnrichedEvent] = []
        convergence_trigger: Optional[TriggerEvent] = None

        # NOTE (applies to the three `# type: ignore[misc]` lambdas below): mypy
        # can't infer T through a default-arg-capture closure (`lambda r=raw: ...`),
        # even though it's genuinely Callable[[], T] at runtime. The default-arg
        # capture itself is deliberate: it snapshots each loop iteration's
        # `raw`/`normalized` by value, avoiding the classic late-binding closure
        # bug where every lambda would otherwise see the loop's final value.
        for raw in raw_signals:
            normalized = self._execute(
                trace,
                "normalization",
                lambda r=raw: self.deps.normalizer.normalize(r),  # type: ignore[misc]
            )
            normalized_signals.append(normalized)

            self._execute(
                trace,
                "orchestrator.operational_history",
                lambda n=normalized: self.deps.operational_history.record(  # type: ignore[misc]
                    ref=n.signal_id,
                    kind="normalized_signal",
                    payload=n,
                    domain=n.domain,
                ),
            )

            # Sprint 3.6.6: deterministic trigger detection sits at the
            # signal/normalization/event-resolution boundary, before World
            # Model -- reads the same raw+normalized pair normalization just
            # produced, decides nothing about ranking/confidence/
            # presentation (StocksTriggerEvaluator's own docstring), and only
            # runs at all when a caller explicitly wired trigger_detector in
            # PipelineDependencies. No detector configured (every existing
            # caller) means this step -- and its ExecutionTrace layer entry
            # -- doesn't exist, not that it silently no-ops.
            trigger_event = None
            if self.deps.trigger_detector is not None:
                trigger_event = self._execute(
                    trace,
                    "trigger_detection",
                    lambda r=raw, n=normalized: self.deps.trigger_detector.evaluate(  # type: ignore[misc]
                        r, n
                    ),
                )

            signal_event = self._execute(
                trace,
                "world_model",
                lambda n=normalized, t=trigger_event: self.deps.world_model.process(  # type: ignore[misc]
                    n, trigger_event=t
                ),
            )
            entity_events.append(signal_event)

            # Sprint 3.6.7 Block 2: observes the same trigger_event World
            # Model was just handed, independently of it -- see
            # StockConvergenceTracker's own docstring for why this doesn't
            # touch World Model's dedup semantics at all. Only runs when both
            # a trigger fired this round and a caller explicitly wired a
            # tracker in, mirroring trigger_detector's own opt-in gating
            # immediately above.
            if trigger_event is not None and self.deps.convergence_tracker is not None:
                observed = self._execute(
                    trace,
                    "convergence_tracker",
                    lambda t=trigger_event, n=normalized: self.deps.convergence_tracker.observe(  # type: ignore[misc]
                        t, n.signal_type
                    ),
                )
                if observed is not None:
                    convergence_trigger = observed

        assert entity_events, "at least one raw_signal is required"

        # Sprint 3.6.7 Block 2: collapse same-signal_type repeats (World
        # Model already merged those into one event_id) down to the single
        # up-to-date version each represents, then merge genuinely distinct
        # signal_type events for this entity into one coherent opportunity
        # instead of letting only the last-processed one survive
        # (ADR-051 finding 5). A no-op whenever every raw_signal shared one
        # signal_type -- see both helpers' own docstrings.
        event = _merge_entity_events(_collapse_duplicate_event_ids(entity_events))
        if convergence_trigger is not None:
            event = _attach_trigger(event, convergence_trigger)

        self._execute(
            trace,
            "orchestrator.operational_history",
            lambda: self.deps.operational_history.record(
                ref=event.event_id,
                kind="enriched_event",
                payload=event,
                domain=event.domain,
            ),
            event_id=event.event_id,
        )

        trust = self._execute(
            trace,
            "evidence_trust",
            lambda: self.deps.evidence_trust.evaluate(event, normalized_signals),
            event_id=event.event_id,
        )
        community = self._execute(
            trace,
            "community_intelligence",
            lambda: self.deps.community_intelligence.measure(event, engagement_samples),
            event_id=event.event_id,
        )

        memory_records = self._execute(
            trace,
            "memory",
            lambda: self.deps.memory_store.query(
                user_id=user_id, entities=[e.entity_id for e in event.entities]
            ),
            event_id=event.event_id,
        )
        user_model = self._execute(
            trace,
            "user_model",
            lambda: self.deps.user_model_builder.build(
                user_id, memory_records, user_model
            ),
            event_id=event.event_id,
        )
        active_context = self._execute(
            trace,
            "active_context",
            lambda: self.deps.active_context_builder.build(
                user_id=user_id, current_question=current_question
            ),
            event_id=event.event_id,
        )

        reasoning = self._execute(
            trace,
            "reasoning",
            lambda: self.deps.reasoning_engine.reason(
                event, trust, user_model, active_context, is_watched=is_watched
            ),
            event_id=event.event_id,
        )
        reasoning, mental_model = self._execute(
            trace,
            "mental_model",
            lambda: self.deps.mental_model_engine.process(reasoning, domain),
            event_id=event.event_id,
        )
        confidence = self._execute(
            trace,
            "conclusion_confidence",
            lambda: self.deps.conclusion_confidence_engine.evaluate(
                reasoning, trust, mental_model
            ),
            event_id=event.event_id,
        )

        recommendation = self._execute(
            trace,
            "opportunity",
            lambda: self.deps.opportunity_engine.evaluate(
                reasoning, confidence, community
            ),
            event_id=event.event_id,
        )

        # Sprint 3.6.9 Stock Opportunity Logic V2: compares this poll's
        # authoritative facts (confidence, active trigger_codes, this user's
        # personal_relevance) against the last stored snapshot for this
        # entity, before Prioritization runs -- this is what finally gives
        # `changed_since_view` real data instead of the hardcoded default
        # `True` every pre-existing caller left it at (see
        # PrioritizationEngine.prioritize()'s own signature and the Sprint
        # 3.6.9 audit in docs/DECISIONS.md). Only runs when a caller
        # explicitly wired a lifecycle_tracker in, mirroring
        # trigger_detector/convergence_tracker's identical opt-in gating
        # above -- every pre-existing caller/test is byte-for-byte
        # unaffected.
        lifecycle_delta = None
        lifecycle_tracker = self.deps.lifecycle_tracker
        if lifecycle_tracker is not None:
            lifecycle_delta = self._execute(
                trace,
                "opportunity_lifecycle",
                lambda: lifecycle_tracker.observe(
                    entity_id=event.entities[0].entity_id,
                    confidence_score=confidence.confidence_score,
                    trigger_codes=[t.trigger_code for t in event.trigger_events],
                    user_id=user_id,
                    personal_relevance=recommendation.dimensions.personal_relevance,
                    now=datetime.now(timezone.utc),
                    market_evidence=market_evidence,
                    trigger_directions=[t.direction for t in event.trigger_events],
                ),
                event_id=event.event_id,
            )

        policy_result = self._execute(
            trace,
            "policy",
            lambda: self.deps.policy_engine.evaluate(recommendation, community, domain),
            event_id=event.event_id,
        )
        prioritized_item = self._execute(
            trace,
            "prioritization",
            lambda: self.deps.prioritization_engine.prioritize(
                user_id,
                domain,
                policy_result,
                recommendation,
                changed_since_view=(
                    lifecycle_delta.is_meaningful
                    if lifecycle_delta is not None
                    else True
                ),
            ),
            event_id=event.event_id,
        )
        delivered_item = self._execute(
            trace,
            "presentation",
            lambda: self.deps.presentation_engine.deliver(
                prioritized_item, reasoning, confidence, policy_result
            ),
            event_id=event.event_id,
        )

        trace.completed_at = datetime.now(timezone.utc)
        trace.status = "complete"
        trace.final_output = delivered_item.event_id

        return PipelineResult(
            pipeline_run_id=pipeline_run_id,
            normalized_signals=normalized_signals,
            event=event,
            trust=trust,
            community=community,
            user_model=user_model,
            active_context=active_context,
            reasoning=reasoning,
            mental_model=mental_model,
            confidence=confidence,
            recommendation=recommendation,
            policy_result=policy_result,
            prioritized_item=prioritized_item,
            delivered_item=delivered_item,
            trace=trace,
            lifecycle_delta=lifecycle_delta,
        )

    def run_feedback_loop(
        self,
        event_id: UUID,
        user_id: str,
        domain: Domain,
        entities: list[str],
        interaction_type: InteractionType,
        content: object | Callable[[FeedbackSignal], object],
        duration_ms: Optional[int] = None,
    ):
        """Second operational test scenario: Feedback -> Learning -> MemoryWrite,
        closing the loop the primary run intentionally leaves open. For ordinary
        interactions (view/click/dismiss/save/share) — use run_memory_inbox_confirm /
        run_memory_inbox_reject for the explicit ADR-019 confirm/reject path instead.

        `content` accepts either a plain value (existing callers, unchanged) or a
        callable that receives the just-computed `FeedbackSignal` and returns the
        content to store -- lets a caller build Memory content from
        inferred_intent/intent_confidence without interpreting the interaction a
        second time or reaching around this method to call feedback_engine/
        learning_engine directly (behavioral-personalization pass).
        """
        feedback = self.deps.feedback_engine.interpret(
            event_id, interaction_type, duration_ms
        )
        resolved_content = content(feedback) if callable(content) else content
        write = self.deps.learning_engine.process_feedback(
            feedback, user_id, domain, entities, resolved_content
        )
        return feedback, write

    def run_exposure_loop(
        self,
        event_id: UUID,
        user_id: str,
        domain: Domain,
        entity_id: str,
    ) -> MemoryWrite:
        """Sprint 3.6.7 Block 3 — records a real exposure/impression fact:
        this opportunity was actually shown to the user. A separate entry
        point from run_feedback_loop(), not a special case inside it --
        there is no ambiguous user behavior for FeedbackEngine to interpret
        here (see LearningEngine.process_exposure's own docstring), so this
        skips straight to LearningEngine, mirroring run_memory_inbox_confirm/
        reject's own "skip interpretation, go straight to Learning" shape for
        a deterministic signal. Orchestrator remains the sole caller of
        LearningEngine from outside logan_core, exactly as run_feedback_loop
        already established.
        """
        return self.deps.learning_engine.process_exposure(
            event_id, user_id, domain, entity_id
        )

    def run_memory_inbox_confirm(
        self,
        event_id: UUID,
        user_id: str,
        domain: Domain,
        entities: list[str],
        content: str,
    ):
        """Memory Inbox 'confirm' — routes through Learning as a maximum-confidence
        FeedbackSignal rather than writing to Memory directly (ADR-019).
        """
        feedback = self.deps.feedback_engine.confirm_memory_inbox(event_id)
        write = self.deps.learning_engine.process_feedback(
            feedback, user_id, domain, entities, content
        )
        return feedback, write

    def run_memory_inbox_reject(
        self,
        event_id: UUID,
        user_id: str,
        domain: Domain,
        entities: list[str],
        content: str,
    ):
        """Memory Inbox 'reject' — see run_memory_inbox_confirm (ADR-019)."""
        feedback = self.deps.feedback_engine.reject_memory_inbox(event_id)
        write = self.deps.learning_engine.process_feedback(
            feedback, user_id, domain, entities, content
        )
        return feedback, write

    def run_suppress_entity_learning(
        self,
        user_id: str,
        entity_id: str,
        domain: Optional[Domain] = None,
    ) -> MemoryWrite:
        """V2.3B Personal Learning Phase 1 -- explicit trait correction/
        suppression ("stop treating this as a preference"). Orchestrator
        remains the sole caller of LearningEngine from outside logan_core,
        exactly as every other Learning entry point above."""
        return self.deps.learning_engine.suppress_entity(user_id, entity_id, domain)
