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


class AskResponse(BaseModel):
    answer: str


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
