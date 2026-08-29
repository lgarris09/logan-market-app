import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .account_lifecycle import purge_user_data
from .ask_engine import generate_grounded_answer, get_ask_llm_provider
from .ask_llm_provider import ConversationTurn
from .clerk_auth import ClerkClaims
from .config import cors_allowed_origins, legacy_memory_db_path, startup_config_summary
from .data import DEMO_OPPORTUNITIES
from .logan_demo import TeslaDemoResponse, run_tesla_demo
from .logan_feed import (
    DemoFeedResponse,
    append_ask_turn,
    get_ask_history,
    get_ask_session_event,
    get_opportunity_context,
    mark_notifications_reviewed,
    record_interaction,
    run_demo_feed,
    set_ask_session_event,
    should_record_ask_followup,
)
from .memory_engine import MemoryEngine
from .memory_models import (
    CategoryContext,
    MemoryConfirm,
    MemoryCreate,
    MemoryDecision,
    MemoryRecord,
)
from .models import (
    AskRequest,
    AskResponse,
    BriefingResponse,
    DeleteAccountResponse,
    LinkAccountRequest,
    LinkAccountResponse,
    NotificationsReviewRequest,
    NotificationsReviewResponse,
    RecordInteractionRequest,
    RecordInteractionResponse,
    RegisterPushTokenRequest,
    RegisterPushTokenResponse,
)
from .notifications import (
    NOTIFICATION_POLL_INTERVAL_SECONDS,
    dispatch_eligible_notifications,
    register_token,
)
from .opportunities import OpportunitiesResponse, run_opportunities
from .rate_limit import check_rate_limit
from .user_context import (
    AccountLinkConflictError,
    link_account,
    require_clerk_claims,
    resolve_user_id,
)

# Sprint 3.6.9 -- hosted attack-surface review: per-(route, user_id)
# fixed-window limits for this API's two most expensive/cost-sensitive
# routes (see rate_limit.py's own module docstring for the full reasoning).
# Generous enough that no legitimate single mobile client is ever affected
# (the app's own foreground poll is far below either limit) -- these exist
# to bound automated/scripted abuse, not to throttle real usage.
_OPPORTUNITIES_RATE_LIMIT = (30, 60.0)  # 30 requests / 60s
_ASK_RATE_LIMIT = (20, 300.0)  # 20 requests / 5 minutes
_NOTIFICATIONS_REGISTER_RATE_LIMIT = (10, 60.0)  # 10 requests / 60s
_ACCOUNT_LINK_RATE_LIMIT = (10, 60.0)  # 10 requests / 60s
_ACCOUNT_DELETE_RATE_LIMIT = (5, 300.0)  # 5 requests / 5 minutes


async def _notification_poll_loop() -> None:
    while True:
        await asyncio.sleep(NOTIFICATION_POLL_INTERVAL_SECONDS)
        try:
            # Sprint 3.6.8 Block 4 (beta-readiness hardening): dispatch_eligible_
            # notifications() is synchronous and, per registered user, runs that
            # user's full pipeline -- including, when STRATUS_LIVE_NVDA_EARNINGS
            # is enabled, up to three sequential live FMP HTTP calls (bounded at
            # 10s each). Every other route in this app is a sync `def` handler,
            # which FastAPI/Starlette already runs in a threadpool automatically
            # -- but this poller is the one place calling that same synchronous
            # work directly from an `async def` coroutine, on the main event
            # loop. Without offloading it here, a slow live-data poll cycle
            # would stall every concurrent request this server is handling for
            # its duration, not just the poller itself.
            await asyncio.to_thread(dispatch_eligible_notifications)
        except Exception as exc:  # noqa: BLE001 -- see lifespan docstring below
            print(f"[notifications] poller error, will retry next cycle: {exc}")


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Sprint 3.6.6F -- STRATUS Watch. Starts the one piece of real
    infrastructure this slice adds: something that notices a newly-
    qualifying live opportunity on its own, independent of any client
    request. Without this, a "notification" can only ever be the in-app
    badge, which requires the app open and polling (see index.tsx's own 60s
    foreground poll) -- it would never arrive while the app is closed. Runs
    in-process (no new worker/deployment), reusing
    dispatch_eligible_notifications()'s own dedup so a slow poll cadence
    never double-sends. Never lets a dispatch failure kill the loop -- one
    bad cycle must not silently end all future notifications for the rest
    of the process's life.
    """
    # Sprint 3.6.9 Block 1: one loud, non-secret line stating this process's
    # effective configuration -- printed at startup so a hosted deployment's
    # logs always show which mode it actually came up in (demo vs.
    # live-data-only, which tickers, whether durable persistence/LLM Ask are
    # on, the active CORS policy) without requiring a code change to check.
    print(startup_config_summary())
    task = asyncio.create_task(_notification_poll_loop())
    yield
    task.cancel()


app = FastAPI(
    title="STRATUS API — Powered by LGI",
    version="1.0.0",
    description="Mobile intelligence backend with branch-based user memory.",
    lifespan=_lifespan,
)

# Sprint 3.6.9 Block 1: environment-configurable, see config.cors_allowed_origins()
# -- demo/development mode (the default) keeps the exact prior `["*"]`
# behavior; beta/production mode defaults to a safe empty allowlist unless
# STRATUS_CORS_ALLOWED_ORIGINS is explicitly set. This is a browser-only
# enforcement mechanism -- restricting it can never block the React Native
# app's own requests (native fetch is not subject to CORS).
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sprint 3.6.9 Block 1: path is now deployment-configurable (see
# config.legacy_memory_db_path()) rather than hardcoded to `backend/data/`,
# which is ephemeral container storage in a hosted deployment, not durable.
# Defaults to the exact pre-Block-1 path when unset -- local dev unaffected.
memory_engine = MemoryEngine(legacy_memory_db_path())


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
def opportunities(
    category: str | None = None, user_id: str = Depends(resolve_user_id)
) -> OpportunitiesResponse:
    """Real, versioned opportunities API -- a thin adapter over `logan_core`
    (V3.1.4 BATCH-4). Runs the actual pipeline (simulated receptors, real scoring/
    policy/prioritization) rather than returning the static `DEMO_OPPORTUNITIES`
    fixture the old version of this route used. `internal_rank_score` is never
    serialized (ADR-029) -- only the resulting ordinal `rank` is public.

    Sprint 3.6.8 Block 2: `user_id` resolves from the `X-Stratus-User-Id`
    header (see user_context.resolve_user_id), defaulting to the founder
    constant when absent -- every pre-Block-2 caller (which sends no such
    header) gets byte-for-byte the same response as before.

    Sprint 3.6.9: rate-limited per user_id -- see rate_limit.py.
    """
    check_rate_limit("opportunities", user_id, *_OPPORTUNITIES_RATE_LIMIT)
    response = run_opportunities(user_id)
    if category is None:
        return response
    filtered = [item for item in response.items if item.category == category.lower()]
    # V2.3A.1 fix: this reconstruction was dropping provider_degraded back to
    # its default False, so a genuine live-data outage would misreport as
    # "healthy" on a category-filtered request -- forward it from the
    # unfiltered response, same as generated_at already is.
    return OpportunitiesResponse(
        items=filtered,
        generated_at=response.generated_at,
        provider_degraded=response.provider_degraded,
    )


@app.post("/v1/notifications/review", response_model=NotificationsReviewResponse)
def review_notifications(
    request: NotificationsReviewRequest, user_id: str = Depends(resolve_user_id)
) -> NotificationsReviewResponse:
    """Marks event_ids as reviewed by `user_id` -- the only way an item's
    `is_new_for_user` clears on a later `/v1/opportunities` call. See
    `logan_feed.mark_notifications_reviewed` and
    `PrioritizationEngine.mark_reviewed` for why this is deliberately a
    separate concept from World Model event identity/dedup. In-memory,
    process-lifetime only -- resets on backend restart, same as the rest of
    this notification state.
    """
    mark_notifications_reviewed(user_id, request.event_ids)
    return NotificationsReviewResponse(reviewed_count=len(request.event_ids))


@app.post("/v1/notifications/register", response_model=RegisterPushTokenResponse)
def register_push_token(
    request: RegisterPushTokenRequest, user_id: str = Depends(resolve_user_id)
) -> RegisterPushTokenResponse:
    """Sprint 3.6.6F -- STRATUS Watch. Registers a device's Expo push token so
    the background poller (see _start_notification_poller above) can dispatch
    real pushes to it. In-memory, process-lifetime only -- Sprint 3.6.8 Block
    2 scopes token storage per `user_id` (see notifications.py); a durable
    per-user store surviving a restart remains an explicitly separate,
    not-yet-made decision.

    Sprint 3.6.9 (hosted attack-surface re-review): rate-limited per
    user_id, same pattern as /v1/opportunities and /v1/ask (see
    rate_limit.py) -- reusing the existing limiter rather than a new
    subsystem. Real usage registers once per app launch (mobile/lib/
    notifications.ts calls this unconditionally on every start, idempotent
    for an already-known token), so this limit is generous relative to that
    -- it exists to bound mass fake-token registration under one spoofed/
    anonymous identity, not to affect normal use.
    """
    check_rate_limit(
        "notifications-register", user_id, *_NOTIFICATIONS_REGISTER_RATE_LIMIT
    )
    return register_token(user_id, request)


@app.post("/v1/interactions", response_model=RecordInteractionResponse)
def record_interaction_route(
    request: RecordInteractionRequest, user_id: str = Depends(resolve_user_id)
) -> RecordInteractionResponse:
    """Behavioral-personalization foundation: the first live caller of the
    existing FeedbackSignal -> FeedbackEngine -> LearningEngine -> MemoryStore
    path (see logan_feed.record_interaction and ADR-047). Deliberately a thin
    passthrough -- `content` is derived server-side from structured fields
    only, never accepted as client text. `user_id` resolves from the request
    header (Sprint 3.6.8 Block 2), matching every other route's pattern.
    """
    record_interaction(
        user_id=user_id,
        event_id=request.event_id,
        entity_id=request.entity_id,
        domain=request.domain,
        interaction_type=request.interaction_type,
        duration_ms=request.duration_ms,
    )
    return RecordInteractionResponse(recorded=True)


@app.post("/v1/account/link", response_model=LinkAccountResponse)
def link_account_route(
    request: LinkAccountRequest, claims: ClerkClaims = Depends(require_clerk_claims)
) -> LinkAccountResponse:
    """V2.3A -- Identity & Account Foundation. The explicit anonymous ->
    authenticated upgrade path: called by the mobile client immediately
    after a first successful Clerk sign-in on a device that has real
    anonymous history worth carrying forward (see user_context.link_account's
    own docstring for the full first-link-wins semantics).

    Requires a valid Clerk session (`require_clerk_claims` -- there is no
    anonymous fallback for this route, unlike every other route in this
    file). Must be called before any other authenticated request from this
    same session, or `resolve_user_id()`'s own auto-provisioning may already
    have claimed a fresh identity for this external account -- see
    docs/DECISIONS.md's ADR-069 for the full ordering requirement.

    Rate-limited per external subject (not `user_id` -- this route
    deliberately never resolves one, see above), same defense-in-depth
    discipline as every other route here.

    Raises 409 when `request.anonymous_user_id` is already claimed by a
    *different* external identity -- see `user_context.AccountLinkConflictError`
    for the exact account-hijack scenario this rejects (found during the
    V2.3A overnight security re-audit).
    """
    check_rate_limit("account-link", claims.subject, *_ACCOUNT_LINK_RATE_LIMIT)
    try:
        stratus_user_id, upgraded = link_account(
            "clerk", claims.subject, request.anonymous_user_id
        )
    except AccountLinkConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return LinkAccountResponse(
        stratus_user_id=stratus_user_id, upgraded_existing_identity=upgraded
    )


@app.delete("/v1/account", response_model=DeleteAccountResponse)
def delete_account_route(
    user_id: str = Depends(resolve_user_id),
) -> DeleteAccountResponse:
    """V2.3A -- Identity & Account Foundation. Purges every piece of the
    *caller's own* user-scoped state (see account_lifecycle.purge_user_data)
    -- `user_id` always comes from `resolve_user_id()`, never a client-
    supplied target, so a caller can only ever delete their own data, never
    another user's. Available to both anonymous and authenticated callers --
    an anonymous user's local data is still their own to remove.
    """
    check_rate_limit("account-delete", user_id, *_ACCOUNT_DELETE_RATE_LIMIT)
    purge_user_data(user_id)
    return DeleteAccountResponse(deleted=True, stratus_user_id=user_id)


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
def demo_feed(user_id: str = Depends(resolve_user_id)) -> DemoFeedResponse:
    """Runs all five simulated domain fixtures through logan_core on one shared
    Orchestrator and returns a multi-item feed, ranked by priority and annotated with
    cross-item ripple connections. Demo/proof-of-connectivity endpoint -- see ADR-022.
    Deprecated as of V3.1.4 BATCH-4 in favor of the versioned `/v1/opportunities`,
    which runs the identical pipeline (see `logan_feed._run_feed_pipeline`) behind a
    schema-versioned response. Kept only so existing callers don't break during the
    mobile migration window (BATCH-4 mobile task).
    """
    return run_demo_feed(user_id)


@app.post("/v1/ask", response_model=AskResponse)
def ask_logan(
    request: AskRequest, user_id: str = Depends(resolve_user_id)
) -> AskResponse:
    """V3.1.4.2 brand correction pass: the returned copy was exposing internal
    implementation language ("confirmed memory", "V1", "category-linked
    memories") directly to consumers -- a wording-only fix, the underlying
    behavior (checking for related stored memories, branching on whether any
    exist) is unchanged. See docs/sessions for the session note covering this
    pass; the general principle -- translate limitations into natural
    consumer language, never expose version/architecture/pipeline terms -- is
    intended to apply anywhere else user-facing text is generated, not just
    here.

    Sprint 3.6.7 Block 4: gains a contextual path, alongside (not replacing)
    the generic one above -- see docs/DECISIONS.md's Sprint 3.6.7 Block 4 ADR
    for the full contract. `request.event_id` (or, for a follow-up in the
    same conversation, a previously-recorded `request.session_id`) resolves
    to a real `OpportunityContext` via `get_opportunity_context()` -- the
    client only ever supplies the reference, never opportunity facts
    directly (ADR-029-style discipline: the client cannot inject an
    intelligence claim into STRATUS's own response).

    Sprint 3.6.8 Block 1 (owner-approved, see docs/DECISIONS.md's Sprint
    3.6.8 Block 1 ADR): the contextual answer may now come from a real,
    grounded LLM call (`generate_grounded_answer()`, ask_engine.py) instead
    of the purely deterministic `answer_question()` -- controlled entirely
    by `get_ask_llm_provider()` (None when disabled or unconfigured, in
    which case this is byte-for-byte the pre-Block-1 deterministic
    behavior). `ASK_FOLLOWUP` is recorded exactly where it already was,
    exactly once per (session, opportunity), regardless of which path
    produced the answer -- the LLM is an interpretation layer over this
    same grounded context, never a second source of behavioral evidence.

    Sprint 3.6.8 Block 2 (ADR-057): `user_id` resolves from the request
    header (see user_context.resolve_user_id) and scopes every one of the
    above -- the OpportunityContext this question can be grounded in, the
    session continuity anchor, and the resulting ASK_FOLLOWUP behavioral
    evidence are all `user_id`-scoped, so one user's Ask STRATUS activity
    can never read or influence another's.

    Sprint 3.6.8 Block 3 (ADR-058): a session's bounded prior turns (see
    logan_feed.py's `_AskSession.history`) are fetched *after*
    `set_ask_session_event()` runs -- that call is what detects and clears
    history on a genuine opportunity-anchor change, so fetching history
    afterward guarantees a freshly-anchored turn never drags in a different
    opportunity's conversation. Every real, successfully-grounded turn
    (LLM or deterministic fallback -- both are true, non-fabricated answers)
    is appended to history exactly once; an unresolved event_id or an empty
    message never reaches that point at all.

    Sprint 3.6.9: rate-limited per user_id -- see rate_limit.py. The
    sharpest motivating risk for this specific route: a grounded question
    can trigger a real, metered Anthropic API call (STRATUS_LLM_ASK).
    """
    check_rate_limit("ask", user_id, *_ASK_RATE_LIMIT)
    clean_message = request.message.strip()
    if not clean_message:
        return AskResponse(
            answer="Ask what changed, why it matters, or what deserves your attention.",
            event_id=request.event_id,
            session_id=request.session_id,
        )

    target_event_id = request.event_id
    if target_event_id is None and request.session_id:
        target_event_id = get_ask_session_event(user_id, request.session_id)

    if target_event_id is not None:
        context = get_opportunity_context(user_id, target_event_id)
        if context is not None:
            history: list[ConversationTurn] = []
            if request.session_id:
                # Detects/clears history on a genuine anchor change (see
                # set_ask_session_event's own docstring) *before* history is
                # fetched for this turn's grounding -- a freshly-switched
                # opportunity always starts this turn with no prior context.
                set_ask_session_event(user_id, request.session_id, target_event_id)
                history = get_ask_history(user_id, request.session_id)

            grounded_answer = generate_grounded_answer(
                context, clean_message, get_ask_llm_provider(), history
            )
            answer = grounded_answer.text

            # Sprint 3.6.8 Block 4 (beta-readiness hardening): minimum viable
            # observability for which path actually answered -- a real,
            # documented gap in server logs before this (only LLM *failures*
            # were ever logged, never a success or a disabled/never-attempted
            # LLM). Deliberately routing metadata only -- never the question
            # or answer text itself (no raw conversational transcripts in
            # logs), and no secrets. Same print-based convention already used
            # throughout this module ([live-nvda], [notifications], [ask-llm]).
            path = (
                f"llm:{grounded_answer.llm_model}"
                if grounded_answer.used_llm
                else "deterministic"
            )
            print(
                f"[ask] user={user_id} entity={context.entity_id} path={path} "
                f"grounded=True"
            )

            if request.session_id:
                append_ask_turn(user_id, request.session_id, clean_message, answer)
                # Feedback-loop protection: at most one ASK_FOLLOWUP
                # behavioral-evidence contribution per (session, opportunity)
                # pair -- see should_record_ask_followup's own docstring.
                # Repeated follow-ups in the same session still get a real,
                # freshly-grounded answer every time; only the *behavioral
                # evidence* is capped -- conversational depth is not a second,
                # unbounded personalization lever (Sprint 3.6.8 Block 3).
                if should_record_ask_followup(
                    user_id, request.session_id, target_event_id
                ):
                    record_interaction(
                        user_id=user_id,
                        event_id=target_event_id,
                        entity_id=context.entity_id,
                        domain=context.domain,
                        interaction_type="ask_followup",
                    )
            else:
                # No session_id at all (e.g. a direct API caller) -- still a
                # real, single question about a real opportunity, recorded
                # once with no session-level cap to apply. No conversation
                # history to thread through either -- there's no session to
                # retain it in.
                record_interaction(
                    user_id=user_id,
                    event_id=target_event_id,
                    entity_id=context.entity_id,
                    domain=context.domain,
                    interaction_type="ask_followup",
                )

            return AskResponse(
                answer=answer,
                event_id=target_event_id,
                session_id=request.session_id,
                grounded=True,
            )

        # A real event_id was supplied (directly, or via session
        # continuity) but doesn't resolve to current context -- honest, not
        # fabricated. Never records ASK_FOLLOWUP for an opportunity STRATUS
        # cannot actually ground an answer in.
        return AskResponse(
            answer=(
                "I don't have current context for that opportunity -- it may be "
                "from before a restart, or may no longer be active. Ask me "
                "something else, or reopen the opportunity and ask again."
            ),
            event_id=request.event_id,
            session_id=request.session_id,
            grounded=False,
        )

    relevant = memory_engine.list_memories(category="markets")[:3]

    if relevant:
        context_note = "I'm drawing on what I've learned from your activity so far to help answer that. "
    else:
        context_note = (
            "I'm still learning what matters most to you. I can help you understand what changed, "
            "why it matters, or what deserves your attention. "
        )

    return AskResponse(
        answer=context_note + f'You asked: "{clean_message}"',
        session_id=request.session_id,
    )
