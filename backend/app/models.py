import sys
from pathlib import Path
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# Same local-dev sys.path bridge as logan_demo.py -- see ADR-022. Repeated here
# (rather than imported) so this module doesn't depend on logan_demo's import
# order having already run it.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from logan_core.contracts import Domain, InteractionType  # noqa: E402

OpportunityCategory = Literal["stocks", "sports", "polymarket"]


class Opportunity(BaseModel):
    id: str
    category: OpportunityCategory
    title: str
    summary: str
    why_it_matters: str
    score: int = Field(ge=0, le=100)
    urgency: Literal["watch", "important", "now"]
    change_label: str
    source_label: str


class BriefingResponse(BaseModel):
    greeting: str
    headline: str
    opportunities: list[Opportunity]


class AskRequest(BaseModel):
    message: str
    # Sprint 3.6.7 Block 4 -- both additive/optional: every existing caller
    # (the generic Ask STRATUS entry point) omits both and is unaffected.
    # `event_id` is a stable opportunity reference the client already has
    # from a real FeedItem -- the backend rehydrates authoritative context
    # from it server-side (see backend/app/ask_context.py); the client never
    # supplies opportunity facts directly, only the reference. `session_id`
    # (client-generated, e.g. once per Ask STRATUS screen visit) lets a
    # follow-up question omit `event_id` and still resolve against the same
    # opportunity the session started with -- see ask_engine.py's session
    # continuity model.
    event_id: Optional[UUID] = None
    session_id: Optional[str] = None


class AskResponse(BaseModel):
    answer: str
    # Echoed back so the client can keep sending the same values on
    # follow-ups without re-deriving them -- None on the generic (no
    # opportunity context) path, unchanged from before this block.
    event_id: Optional[UUID] = None
    session_id: Optional[str] = None
    # Whether this answer was actually grounded in real opportunity context
    # (event_id resolved to a live cache entry) vs. the generic fallback --
    # lets the client distinguish "STRATUS answered using this opportunity's
    # real data" from "STRATUS answered generically" without parsing text.
    grounded: bool = False


class NotificationsReviewRequest(BaseModel):
    event_ids: list[UUID]


class NotificationsReviewResponse(BaseModel):
    reviewed_count: int


class RegisterPushTokenRequest(BaseModel):
    expo_push_token: str


class RegisterPushTokenResponse(BaseModel):
    registered: bool
    token_count: int


class RecordInteractionRequest(BaseModel):
    event_id: UUID
    entity_id: str
    domain: Domain
    interaction_type: InteractionType
    duration_ms: Optional[int] = None


class RecordInteractionResponse(BaseModel):
    recorded: bool
