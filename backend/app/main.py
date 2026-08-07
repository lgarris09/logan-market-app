from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .data import DEMO_OPPORTUNITIES
from .logan_demo import TeslaDemoResponse, run_tesla_demo
from .logan_feed import DemoFeedResponse, run_demo_feed
from .memory_engine import MemoryEngine
from .memory_models import (
    CategoryContext,
    MemoryConfirm,
    MemoryCreate,
    MemoryDecision,
    MemoryRecord,
)
from .models import AskRequest, AskResponse, BriefingResponse
from .opportunities import OpportunitiesResponse, run_opportunities

app = FastAPI(
    title="Logan Intelligence API",
    version="1.0.0",
    description="Mobile intelligence backend with branch-based user memory.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

memory_engine = MemoryEngine(
    Path(__file__).resolve().parent.parent / "data" / "logan_memory.db"
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "online", "service": "logan-intelligence-api", "version": "1.0.0"}


@app.get("/v1/briefing", response_model=BriefingResponse)
def briefing() -> BriefingResponse:
    return BriefingResponse(
        greeting="Good evening",
        headline="Three changes match the way you look for opportunity.",
        opportunities=DEMO_OPPORTUNITIES,
    )


@app.get("/v1/opportunities", response_model=OpportunitiesResponse)
def opportunities(category: str | None = None) -> OpportunitiesResponse:
    """Real, versioned opportunities API -- a thin adapter over `logan_core`
    (V3.1.4 BATCH-4). Runs the actual pipeline (simulated receptors, real scoring/
    policy/prioritization) rather than returning the static `DEMO_OPPORTUNITIES`
    fixture the old version of this route used. `internal_rank_score` is never
    serialized (ADR-029) -- only the resulting ordinal `rank` is public.
    """
    response = run_opportunities()
    if category is None:
        return response
    filtered = [item for item in response.items if item.category == category.lower()]
    return OpportunitiesResponse(items=filtered, generated_at=response.generated_at)


@app.post("/v1/memories", response_model=MemoryDecision)
def create_memory(request: MemoryCreate) -> MemoryDecision:
    return memory_engine.add_memory(
        content=request.content,
        active_category=request.active_category,
        source=request.source,
        user_confirmed=request.user_confirmed,
    )


@app.get("/v1/memories", response_model=list[MemoryRecord])
def list_memories(
    category: str | None = Query(default=None),
    inbox_only: bool = Query(default=False),
) -> list[MemoryRecord]:
    return memory_engine.list_memories(category=category, inbox_only=inbox_only)


@app.get("/v1/context/{category}", response_model=CategoryContext)
def category_context(category: str) -> CategoryContext:
    return CategoryContext(
        active_category=category,
        memories=memory_engine.list_memories(category=category),
    )


@app.post("/v1/memories/{memory_id}/confirm", response_model=MemoryRecord)
def confirm_memory(memory_id: str, request: MemoryConfirm) -> MemoryRecord:
    memory = memory_engine.confirm_memory(memory_id, request.confirmed)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory


@app.post("/v1/demo/tesla", response_model=TeslaDemoResponse, deprecated=True)
def demo_tesla() -> TeslaDemoResponse:
    """Runs the logan_core Tesla scenario (simulated data) end-to-end and returns the
    generated opportunity card, confidence, policy result, and an execution trace
    summary. Demo/proof-of-connectivity endpoint -- see ADR-022. Deprecated as of
    V3.1.4 BATCH-4: kept for single-entity debugging, superseded by `/v1/opportunities`
    for anything client-facing.
    """
    return run_tesla_demo()


@app.get("/v1/demo/feed", response_model=DemoFeedResponse, deprecated=True)
def demo_feed() -> DemoFeedResponse:
    """Runs all five simulated domain fixtures through logan_core on one shared
    Orchestrator and returns a multi-item feed, ranked by priority and annotated with
    cross-item ripple connections. Demo/proof-of-connectivity endpoint -- see ADR-022.
    Deprecated as of V3.1.4 BATCH-4 in favor of the versioned `/v1/opportunities`,
    which runs the identical pipeline (see `logan_feed._run_feed_pipeline`) behind a
    schema-versioned response. Kept only so existing callers don't break during the
    mobile migration window (BATCH-4 mobile task).
    """
    return run_demo_feed()


@app.post("/v1/ask", response_model=AskResponse)
def ask_logan(request: AskRequest) -> AskResponse:
    clean_message = request.message.strip()
    if not clean_message:
        return AskResponse(answer="Ask what changed or why something matters.")

    relevant = memory_engine.list_memories(category="markets")[:3]
    context_note = (
        f"I found {len(relevant)} relevant stored memories to use as context. "
        if relevant
        else "I do not have enough confirmed memory yet, so this answer is generic. "
    )

    return AskResponse(
        answer=(
            context_note
            + "V1 is now structured to retrieve category-linked memories before reasoning. "
            + f'Your question was: "{clean_message}"'
        )
    )
