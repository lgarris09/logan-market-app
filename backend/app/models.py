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


class LinkAccountRequest(BaseModel):
    """V2.3A -- Identity & Account Foundation. The client's current
    anonymous per-install identity (mobile/lib/identity.ts's device id) --
    the thing this call is trying to carry forward into a newly-
    authenticated account. Sent explicitly in the body, not inferred from
    the X-Stratus-User-Id header, so this operation's intent is unambiguous
    regardless of what any other header on this same request happens to
    carry.
    """

    anonymous_user_id: str = Field(min_length=1, max_length=128)


class LinkAccountResponse(BaseModel):
    stratus_user_id: str
    # True: this device's own existing anonymous identity became the
    # canonical, now-authenticated identity -- its prior history is
    # preserved as-is under the same id, no client-side change needed
    # beyond knowing it's now authenticated.
    # False: this external account was already linked to a *different*
    # stratus_user_id (e.g. a second device signing into the same real
    # account) -- the client should adopt `stratus_user_id` above as its
    # active identity going forward; this device's own prior anonymous
    # history remains under its old id, not merged in (see ADR-069).
    upgraded_existing_identity: bool


class DeleteAccountResponse(BaseModel):
    deleted: bool
    stratus_user_id: str
