import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

# logan_core lives at the repo root, a sibling of backend/. It has no installable
# packaging yet, so this is a local-dev sys.path shim, not a real dependency
# declaration -- see ADR-022.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from logan_core.community_intelligence import EngagementSample  # noqa: E402
from logan_core.contracts import ConclusionConfidence, DeliveredItem, Holding, PolicyResult  # noqa: E402
from logan_core.orchestrator import Orchestrator  # noqa: E402
from logan_core.receptors import (  # noqa: E402
    tesla_ai_partnership_corroboration,
    tesla_ai_partnership_signal,
)
from logan_core.user_model import UserModelBuilder  # noqa: E402


class ExecutionTraceSummary(BaseModel):
    pipeline_run_id: UUID
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_layers: int
    layers: list[str]
    all_succeeded: bool
    total_latency_ms: int


class TeslaDemoResponse(BaseModel):
    delivered_item: DeliveredItem
    confidence: ConclusionConfidence
    policy_result: PolicyResult
    execution_trace: ExecutionTraceSummary


def run_tesla_demo() -> TeslaDemoResponse:
    """Runs the Logan Intelligence System's primary operational test scenario --
    'Tesla announces a major AI chip partnership' -- through the full logan_core
    pipeline on simulated data, and shapes the result for the demo endpoint.

    A fresh Orchestrator is used per call so repeated demo runs don't accumulate
    cooldown/fatigue state in AttentionState or grow the in-memory Memory Store.
    """
    now = datetime.now(timezone.utc)

    user_model = UserModelBuilder().seed(
        user_id="demo_user",
        holdings=[Holding(domain="stocks", entity_id="NVDA", display_name="NVIDIA", added_at=now)],
        risk_tolerance="moderate",
    )
    engagement_samples = [
        EngagementSample(observed_at=now, volume_at_point=10, unique_users=8, saves_shares=1, questions=0),
        EngagementSample(observed_at=now, volume_at_point=40, unique_users=30, saves_shares=6, questions=3),
    ]

    orchestrator = Orchestrator()
    result = orchestrator.run(
        raw_signals=[tesla_ai_partnership_signal(now), tesla_ai_partnership_corroboration(now)],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )

    trace = result.trace
    return TeslaDemoResponse(
        delivered_item=result.delivered_item,
        confidence=result.confidence,
        policy_result=result.policy_result,
        execution_trace=ExecutionTraceSummary(
            pipeline_run_id=trace.pipeline_run_id,
            status=trace.status,
            started_at=trace.started_at,
            completed_at=trace.completed_at,
            total_layers=len(trace.layers),
            layers=[m.layer for m in trace.layers],
            all_succeeded=all(m.success for m in trace.layers),
            total_latency_ms=sum(m.latency_ms for m in trace.layers),
        ),
    )
