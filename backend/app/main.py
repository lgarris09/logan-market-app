from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .data import DEMO_OPPORTUNITIES
from .logan_demo import TeslaDemoResponse, run_tesla_demo
from .memory_engine import MemoryEngine
from .memory_models import CategoryContext, MemoryConfirm, MemoryCreate, MemoryDecision, MemoryRecord
from .models import AskRequest, AskResponse, BriefingResponse, Opportunity


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

memory_engine = MemoryEngine(Path(__file__).resolve().parent.parent / "data" / "logan_memory.db")


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


@app.get("/v1/opportunities", response_model=list[Opportunity])
def opportunities(category: str | None = None) -> list[Opportunity]:
    if category is None:
        return DEMO_OPPORTUNITIES
    return [item for item in DEMO_OPPORTUNITIES if item.category == category.lower()]


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


@app.post("/v1/demo/tesla", response_model=TeslaDemoResponse)
def demo_tesla() -> TeslaDemoResponse:
    """Runs the logan_core Tesla scenario (simulated data) end-to-end and returns the
    generated opportunity card, confidence, policy result, and an execution trace
    summary. Demo/proof-of-connectivity endpoint -- see ADR-022.
    """
    return run_tesla_demo()


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
