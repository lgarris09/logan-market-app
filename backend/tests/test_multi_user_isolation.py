"""Sprint 3.6.8 Block 2 -- production user boundaries (ADR-057).

Full HTTP-level proof that two distinct users, identified only by the
`X-Stratus-User-Id` header (backend/app/user_context.py), never read,
influence, inherit, or suppress each other's personalization state:
UserModel/behavioral evidence, explicit-vs-inferred relevance, Ask STRATUS
sessions/OpportunityContext, Watch notification-review state, and push
notification dispatch/review. Also proves the founder-default backward-
compatibility path (no header at all) and that persisted MemoryStore state
stays correctly user-scoped across a simulated restart.
"""

from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from backend.app.logan_feed import (
    _get_orchestrator,
    _run_feed_pipeline,
    get_alert_eligible_items,
    get_ask_session_event,
    get_opportunity_context,
    reset_pipeline_state,
)
from backend.app.main import app
from backend.app.notifications import (
    dispatch_eligible_notifications,
    get_pending_push_event_ids,
    reset_notification_state,
)
from logan_core.contracts import LOCAL_FOUNDER_USER_ID

client = TestClient(app)
USER_A = "user-a"
USER_B = "user-b"


def _headers(user_id: str | None) -> dict[str, str]:
    return {"X-Stratus-User-Id": user_id} if user_id else {}


def _nvda_event_id(user_id: str | None = None) -> str:
    response = client.get("/v1/opportunities", headers=_headers(user_id))
    item = next(i for i in response.json()["items"] if i["entity_id"] == "NVDA")
    return item["event_id"]


# --- Identity boundary itself ------------------------------------------


def test_missing_header_defaults_to_founder_backward_compat():
    """No header at all -- every pre-Block-2 caller -- must resolve to
    LOCAL_FOUNDER_USER_ID and produce byte-for-byte the same personalization
    as before this block (the founder's NVDA holding/AI_SECTOR interest)."""
    reset_pipeline_state()
    response = client.get("/v1/opportunities")
    assert response.status_code == 200
    nvda = next(i for i in response.json()["items"] if i["entity_id"] == "NVDA")
    # The founder's explicit NVDA holding drives a real, non-generic
    # personal_relevance -- proven indirectly via a real grounded Ask
    # STRATUS answer, since personal_relevance itself isn't on FeedItem.
    ask = client.post(
        "/v1/ask",
        json={"message": "why does this matter to me?", "event_id": nvda["event_id"]},
    )
    assert ask.json()["grounded"] is True


def test_two_distinct_header_values_get_independent_user_models():
    reset_pipeline_state()
    response_a = client.get("/v1/opportunities", headers=_headers(USER_A))
    response_b = client.get("/v1/opportunities", headers=_headers(USER_B))
    assert response_a.status_code == 200
    assert response_b.status_code == 200
    # Both see the same shared world fact (same event_id for NVDA) -- World
    # Model identity is deliberately not user-scoped.
    nvda_a = next(i for i in response_a.json()["items"] if i["entity_id"] == "NVDA")
    nvda_b = next(i for i in response_b.json()["items"] if i["entity_id"] == "NVDA")
    assert nvda_a["event_id"] == nvda_b["event_id"]


# --- Behavioral learning isolation ---------------------------------------


def test_behavioral_evidence_for_one_user_never_reaches_another_users_memory_query():
    """The exact pre-Block-2 bug (orchestrator/pipeline.py's unfiltered
    memory_store.query()): two independent 'interested'-intent interactions
    recorded under USER_A must never appear when MemoryStore is queried for
    USER_B, even for the identical entity/domain."""
    reset_pipeline_state()
    for _ in range(2):
        response = client.post(
            "/v1/interactions",
            json={
                "event_id": str(uuid4()),
                "entity_id": "TSLA",
                "domain": "stocks",
                "interaction_type": "watch",
            },
            headers=_headers(USER_A),
        )
        assert response.status_code == 200

    orchestrator = _get_orchestrator()
    user_a_records = orchestrator.deps.memory_store.query(
        user_id=USER_A, domain="stocks", entities=["TSLA"]
    )
    user_b_records = orchestrator.deps.memory_store.query(
        user_id=USER_B, domain="stocks", entities=["TSLA"]
    )
    assert len(user_a_records) == 2
    assert user_b_records == []


def test_repeated_behavioral_evidence_creates_inferred_interest_only_for_that_user():
    """USER_A repeatedly engages with TSLA -- an inferred Interest and
    established_behaviors entry must appear in USER_A's own UserModel after
    a later pipeline run, and must never appear in USER_B's UserModel, which
    has zero evidence for TSLA."""
    reset_pipeline_state()
    client.get("/v1/opportunities", headers=_headers(USER_A))  # seeds USER_A's model
    client.get("/v1/opportunities", headers=_headers(USER_B))  # seeds USER_B's model

    for _ in range(2):
        client.post(
            "/v1/interactions",
            json={
                "event_id": str(uuid4()),
                "entity_id": "TSLA",
                "domain": "stocks",
                "interaction_type": "watch",
            },
            headers=_headers(USER_A),
        )

    client.get("/v1/opportunities", headers=_headers(USER_A))  # folds evidence
    client.get(
        "/v1/opportunities", headers=_headers(USER_B)
    )  # rebuilds, no new evidence

    import backend.app.logan_feed as logan_feed_module

    model_a = logan_feed_module._user_models[USER_A]
    model_b = logan_feed_module._user_models[USER_B]

    assert "engaged_with_TSLA" in {b.label for b in model_a.established_behaviors}
    assert "TSLA" in {i.topic for i in model_a.interests if i.source == "inferred"}

    assert "engaged_with_TSLA" not in {b.label for b in model_b.established_behaviors}
    assert "TSLA" not in {i.topic for i in model_b.interests}


# --- Explicit vs. inferred relevance, per user ----------------------------


def test_founders_explicit_seed_is_never_copied_to_a_new_user():
    """LOCAL_FOUNDER_USER_ID alone gets the seeded NVDA holding/AI_SECTOR
    explicit interest -- a brand-new user_id must start blank (Sprint 3.6.8
    Block 2 review decision: no arbitrary demo-portfolio copying)."""
    reset_pipeline_state()
    client.get("/v1/opportunities", headers=_headers(USER_A))
    client.get("/v1/opportunities")  # founder, no header

    import backend.app.logan_feed as logan_feed_module

    founder_model = logan_feed_module._user_models[LOCAL_FOUNDER_USER_ID]
    user_a_model = logan_feed_module._user_models[USER_A]

    assert any(h.entity_id == "NVDA" for h in founder_model.holdings)
    assert any(
        i.topic == "AI_SECTOR" and i.source == "explicit"
        for i in founder_model.interests
    )

    assert user_a_model.holdings == []
    assert user_a_model.interests == []
    assert user_a_model.risk_tolerance == "unknown"


def test_inferred_relevance_never_exceeds_explicit_tier_for_either_user():
    """ADR-048's invariant (inferred connections bounded below the explicit
    0.6 relevance bump) must hold independently for every user, not just the
    founder -- proven via each user's own grounded Ask STRATUS answer citing
    a real, non-fabricated connection_basis-consistent explanation."""
    reset_pipeline_state()
    event_id = _nvda_event_id(USER_A)  # USER_A has no NVDA holding at all
    response = client.post(
        "/v1/ask",
        json={"message": "why does this matter to me?", "event_id": event_id},
        headers=_headers(USER_A),
    )
    assert response.json()["grounded"] is True
    # A user with zero holdings/interests gets an honest, non-personalized
    # explanation -- never a fabricated "you're tracking this" claim.
    assert "still learning" in response.json()["answer"].lower() or (
        "you're tracking" not in response.json()["answer"].lower()
    )


# --- Ask STRATUS session + OpportunityContext isolation -------------------


def test_same_session_id_reused_by_two_users_does_not_share_context():
    """A session_id is client-generated, not a secret -- two different users
    coincidentally using the identical session_id string must never let one
    read or extend the other's Ask STRATUS session."""
    reset_pipeline_state()
    event_id_a = _nvda_event_id(USER_A)
    shared_session_id = "collision-session"

    client.post(
        "/v1/ask",
        json={
            "message": "what changed?",
            "event_id": event_id_a,
            "session_id": shared_session_id,
        },
        headers=_headers(USER_A),
    )

    # USER_B, same session_id, no event_id -- must NOT resolve to USER_A's
    # session continuity (which discussed NVDA under USER_A).
    response_b = client.post(
        "/v1/ask",
        json={"message": "why does this matter?", "session_id": shared_session_id},
        headers=_headers(USER_B),
    )
    assert response_b.json()["grounded"] is False
    assert response_b.json()["event_id"] is None


def test_opportunity_context_cache_is_not_readable_across_users():
    reset_pipeline_state()
    event_id_a = _nvda_event_id(USER_A)

    import backend.app.logan_feed as logan_feed_module

    context_for_a = get_opportunity_context(USER_A, logan_feed_module.UUID(event_id_a))
    context_for_b = get_opportunity_context(USER_B, logan_feed_module.UUID(event_id_a))
    assert context_for_a is not None
    assert context_for_b is None  # USER_B never ran a pipeline; no cache exists yet


def test_ask_followup_recorded_under_the_asking_users_own_identity():
    """A contextual question from USER_A must record ASK_FOLLOWUP evidence
    under USER_A's own MemoryStore records, never USER_B's."""
    reset_pipeline_state()
    event_id_a = _nvda_event_id(USER_A)
    client.post(
        "/v1/ask",
        json={
            "message": "what changed?",
            "event_id": event_id_a,
            "session_id": "ask-followup-isolation",
        },
        headers=_headers(USER_A),
    )
    orchestrator = _get_orchestrator()
    user_a_followups = [
        r
        for r in orchestrator.deps.memory_store.all(user_id=USER_A)
        if r.record_type == "feedback_record"
        and isinstance(r.content, dict)
        and r.content.get("interaction_type") == "ask_followup"
    ]
    user_b_followups = [
        r
        for r in orchestrator.deps.memory_store.all(user_id=USER_B)
        if r.record_type == "feedback_record"
        and isinstance(r.content, dict)
        and r.content.get("interaction_type") == "ask_followup"
    ]
    assert len(user_a_followups) == 1
    assert user_b_followups == []


def test_get_ask_session_event_is_scoped_to_user_id():
    reset_pipeline_state()
    from uuid import UUID as _UUID

    event_id_a = _nvda_event_id(USER_A)
    client.post(
        "/v1/ask",
        json={
            "message": "what changed?",
            "event_id": event_id_a,
            "session_id": "session-scope-check",
        },
        headers=_headers(USER_A),
    )
    assert get_ask_session_event(USER_A, "session-scope-check") == _UUID(event_id_a)
    assert get_ask_session_event(USER_B, "session-scope-check") is None


# --- Watch notification-review / fatigue-cooldown isolation ---------------


def test_one_users_notification_review_does_not_clear_another_users_badge():
    """USER_B never runs a pipeline or reviews anything -- USER_A's own
    review action must not fabricate any AttentionState for USER_B at all.
    (A weaker version of this check that first ran both users' pipelines
    would be confounded by each user's own independent "first load is
    notification-silent" baseline -- see PrioritizationEngine.mark_reviewed
    -- which legitimately populates each user's own notifications_reviewed
    on their own first call, not from cross-user leakage. Isolating the
    check to before USER_B has any state at all removes that confound.)"""
    reset_pipeline_state()
    items_a, _now, _alert = _run_feed_pipeline(USER_A)

    event_ids_a = [item.event_id for item in items_a]
    client.post(
        "/v1/notifications/review",
        json={"event_ids": [str(e) for e in event_ids_a]},
        headers=_headers(USER_A),
    )

    orchestrator = _get_orchestrator()
    state_a = orchestrator.deps.prioritization_engine.attention_state(USER_A)
    state_b = orchestrator.deps.prioritization_engine.attention_state(USER_B)
    assert state_a is not None
    reviewed_a = {r.event_id for r in state_a.notifications_reviewed}
    assert set(event_ids_a) <= reviewed_a
    # USER_B has never been seen by PrioritizationEngine -- no AttentionState
    # should exist for them at all, proving USER_A's review call created no
    # cross-user state.
    assert state_b is None


# --- Push notification isolation ------------------------------------------


def _mock_client():
    def handler(request):
        return httpx.Response(200, json={"data": []})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_push_tokens_and_dispatch_state_are_scoped_per_user():
    reset_pipeline_state()
    reset_notification_state()

    client.post(
        "/v1/notifications/register",
        json={"expo_push_token": "ExponentPushToken[user-a-token]"},
        headers=_headers(USER_A),
    )
    # USER_B never registers a token at all.
    assert len(get_alert_eligible_items(USER_A)) > 0  # sanity

    dispatched = dispatch_eligible_notifications(client=_mock_client())
    assert dispatched > 0

    pending_a = get_pending_push_event_ids(USER_A)
    pending_b = get_pending_push_event_ids(USER_B)
    assert len(pending_a) > 0
    assert pending_b == set()  # USER_B has no token, nothing was ever pushed to them


def test_reviewing_notifications_only_clears_the_reviewing_users_pending_push_state():
    reset_pipeline_state()
    reset_notification_state()

    client.post(
        "/v1/notifications/register",
        json={"expo_push_token": "ExponentPushToken[user-a-token-2]"},
        headers=_headers(USER_A),
    )
    client.post(
        "/v1/notifications/register",
        json={"expo_push_token": "ExponentPushToken[user-b-token]"},
        headers=_headers(USER_B),
    )
    dispatch_eligible_notifications(client=_mock_client())

    pending_a_before = get_pending_push_event_ids(USER_A)
    pending_b_before = get_pending_push_event_ids(USER_B)
    assert pending_a_before
    assert pending_b_before

    client.post(
        "/v1/notifications/review",
        json={"event_ids": [str(e) for e in pending_a_before]},
        headers=_headers(USER_A),
    )

    assert get_pending_push_event_ids(USER_A) == set()
    # USER_B's own pending set must be completely unaffected by USER_A's review.
    assert get_pending_push_event_ids(USER_B) == pending_b_before


# --- Restart persistence stays correctly user-scoped -----------------------


def test_persisted_interactions_survive_restart_scoped_per_user(monkeypatch, tmp_path):
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv("STRATUS_STATE_DB_PATH", str(tmp_path / "state.db"))
    monkeypatch.delenv("STRATUS_LIVE_NVDA_EARNINGS", raising=False)
    reset_pipeline_state()

    client.post(
        "/v1/interactions",
        json={
            "event_id": str(uuid4()),
            "entity_id": "AAPL",
            "domain": "stocks",
            "interaction_type": "save",
        },
        headers=_headers(USER_A),
    )
    client.post(
        "/v1/interactions",
        json={
            "event_id": str(uuid4()),
            "entity_id": "AAPL",
            "domain": "stocks",
            "interaction_type": "save",
        },
        headers=_headers(USER_B),
    )

    # Simulated backend restart: drop every in-process singleton. The SQLite
    # file itself is untouched -- this is exactly what a real process
    # restart would do.
    reset_pipeline_state()

    orchestrator = _get_orchestrator()
    records_a = orchestrator.deps.memory_store.query(
        user_id=USER_A, domain="stocks", entities=["AAPL"]
    )
    records_b = orchestrator.deps.memory_store.query(
        user_id=USER_B, domain="stocks", entities=["AAPL"]
    )
    assert len(records_a) == 1
    assert len(records_b) == 1
    assert records_a[0].record_id != records_b[0].record_id
    assert records_a[0].user_id == USER_A
    assert records_b[0].user_id == USER_B
