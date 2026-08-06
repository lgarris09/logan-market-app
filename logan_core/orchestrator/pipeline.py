import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional, TypeVar
from uuid import UUID, uuid4

from logan_core.active_context import ActiveContextBuilder
from logan_core.community_intelligence import CommunityIntelligenceEngine, EngagementSample
from logan_core.conclusion_confidence import ConclusionConfidenceEngine
from logan_core.contracts import (
    ActiveContext,
    AttentionRecommendation,
    CommunitySignal,
    ConclusionConfidence,
    DeliveredItem,
    EnrichedEvent,
    EvidenceTrust,
    ExecutionMetrics,
    ExecutionTrace,
    MentalModel,
    NormalizedSignal,
    PolicyResult,
    PrioritizedItem,
    RawSignal,
    ReasoningResult,
    UserModel,
)
from logan_core.evidence_trust import EvidenceTrustEngine
from logan_core.feedback import FeedbackEngine
from logan_core.learning import LearningEngine
from logan_core.memory import MemoryStore
from logan_core.mental_model import MentalModelEngine
from logan_core.normalization import Normalizer
from logan_core.opportunity import OpportunityEngine
from logan_core.policy import PolicyEngine
from logan_core.presentation import PresentationEngine
from logan_core.prioritization import PrioritizationEngine
from logan_core.reasoning import ReasoningEngine
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
    operational_history: OperationalHistoryStore = field(default_factory=OperationalHistoryStore)
    memory_store: MemoryStore = field(default_factory=MemoryStore)
    user_model_builder: UserModelBuilder = field(default_factory=UserModelBuilder)
    active_context_builder: ActiveContextBuilder = field(default_factory=ActiveContextBuilder)
    reasoning_engine: ReasoningEngine = field(default_factory=ReasoningEngine)
    mental_model_engine: MentalModelEngine = field(default_factory=MentalModelEngine)
    conclusion_confidence_engine: ConclusionConfidenceEngine = field(
        default_factory=ConclusionConfidenceEngine
    )
    opportunity_engine: OpportunityEngine = field(default_factory=OpportunityEngine)
    policy_engine: PolicyEngine = field(default_factory=PolicyEngine)
    prioritization_engine: PrioritizationEngine = field(default_factory=PrioritizationEngine)
    presentation_engine: PresentationEngine = field(default_factory=PresentationEngine)
    feedback_engine: FeedbackEngine = field(default_factory=FeedbackEngine)
    learning_engine: LearningEngine = field(init=False)

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


class Orchestrator:
    """Owns the execution pipeline. Contains no business logic of its own — coordinates
    layers, retries, and persists Operational History (ADR-016), which no other layer
    is permitted to write.
    """

    RETRY_LIMIT = 3

    def __init__(self, deps: Optional[PipelineDependencies] = None, retry_sleep: float = 0.0) -> None:
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
            except Exception as exc:  # noqa: BLE001 — critical failure halts the pipeline
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
        domain: str,
        current_question: Optional[str] = None,
    ) -> PipelineResult:
        """Runs the primary vertical-slice pipeline: Raw Signal through Presentation.
        Feedback and Learning are separate, explicit calls (run_feedback_loop) — see
        LOGAN_IMPLEMENTATION_PLAN.md's resolved first-operational-test scope.
        """
        pipeline_run_id = uuid4()
        trace = ExecutionTrace(
            pipeline_run_id=pipeline_run_id, started_at=datetime.now(timezone.utc), status="running"
        )

        normalized_signals: list[NormalizedSignal] = []
        event: Optional[EnrichedEvent] = None

        for raw in raw_signals:
            normalized = self._execute(trace, "normalization", lambda r=raw: self.deps.normalizer.normalize(r))
            normalized_signals.append(normalized)

            self._execute(
                trace,
                "orchestrator.operational_history",
                lambda n=normalized: self.deps.operational_history.record(
                    ref=n.signal_id, kind="normalized_signal", payload=n, domain=n.domain
                ),
            )

            event = self._execute(trace, "world_model", lambda n=normalized: self.deps.world_model.process(n))

        assert event is not None, "at least one raw_signal is required"

        self._execute(
            trace,
            "orchestrator.operational_history",
            lambda: self.deps.operational_history.record(
                ref=event.event_id, kind="enriched_event", payload=event, domain=event.domain
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
            trace, "memory", lambda: self.deps.memory_store.query(entities=[e.entity_id for e in event.entities]),
            event_id=event.event_id,
        )
        user_model = self._execute(
            trace,
            "user_model",
            lambda: self.deps.user_model_builder.build(user_id, memory_records, user_model),
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
            lambda: self.deps.reasoning_engine.reason(event, trust, user_model, active_context),
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
            lambda: self.deps.conclusion_confidence_engine.evaluate(reasoning, trust, mental_model),
            event_id=event.event_id,
        )

        recommendation = self._execute(
            trace,
            "opportunity",
            lambda: self.deps.opportunity_engine.evaluate(reasoning, confidence, community),
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
                user_id, domain, policy_result, recommendation
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
        )

    def run_feedback_loop(
        self,
        event_id: UUID,
        user_id: str,
        domain: str,
        entities: list[str],
        interaction_type: str,
        content: str,
        duration_ms: Optional[int] = None,
    ):
        """Second operational test scenario: Feedback -> Learning -> MemoryWrite,
        closing the loop the primary run intentionally leaves open. For ordinary
        interactions (view/click/dismiss/save/share) — use run_memory_inbox_confirm /
        run_memory_inbox_reject for the explicit ADR-019 confirm/reject path instead.
        """
        feedback = self.deps.feedback_engine.interpret(event_id, interaction_type, duration_ms)
        write = self.deps.learning_engine.process_feedback(feedback, user_id, domain, entities, content)
        return feedback, write

    def run_memory_inbox_confirm(
        self, event_id: UUID, user_id: str, domain: str, entities: list[str], content: str
    ):
        """Memory Inbox 'confirm' — routes through Learning as a maximum-confidence
        FeedbackSignal rather than writing to Memory directly (ADR-019).
        """
        feedback = self.deps.feedback_engine.confirm_memory_inbox(event_id)
        write = self.deps.learning_engine.process_feedback(feedback, user_id, domain, entities, content)
        return feedback, write

    def run_memory_inbox_reject(
        self, event_id: UUID, user_id: str, domain: str, entities: list[str], content: str
    ):
        """Memory Inbox 'reject' — see run_memory_inbox_confirm (ADR-019)."""
        feedback = self.deps.feedback_engine.reject_memory_inbox(event_id)
        write = self.deps.learning_engine.process_feedback(feedback, user_id, domain, entities, content)
        return feedback, write
