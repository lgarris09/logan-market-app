"""Sprint 3.6.8 Block 4 -- beta-readiness hardening (ADR-059).

Three things this file proves that no prior block's test suite explicitly
covered end-to-end:

1. The restart-safety matrix: exactly which process-lifetime state survives
   a simulated backend restart (with STRATUS_PERSIST_MEMORY enabled) and
   which does not -- documented as an explicit, testable contract, not left
   implicit across several other files.
2. Multi-user isolation guarantees (Block 2, ADR-057) re-proven through the
   fully integrated Block 3 conversational stack, not just the original
   single-turn surface Block 2 shipped against.
3. The full integrated acceptance path named in the Block 4 spec: no
   explicit holding -> a real opportunity surfaces -> limited initial
   Personal relevance -> a real conversational Ask STRATUS exchange ->
   ASK_FOLLOWUP recorded once, within bounds -> a simulated restart ->
   behavioral evidence survives correctly scoped -> continued engagement
   matures relevance, still bounded -> a second user is provably unaffected
   throughout.
"""

from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.ask_llm_fixture import FixtureAskLlmProvider
from backend.app.logan_feed import (
    _get_orchestrator,
    get_ask_history,
    reset_pipeline_state,
)
from backend.app.main import app
from backend.app.notifications import reset_notification_state
from logan_core.contracts import LOCAL_FOUNDER_USER_ID

client = TestClient(app)
USER_A = "hardening-user-a"
USER_B = "hardening-user-b"


def _headers(user_id: str | None) -> dict[str, str]:
    return {"X-Stratus-User-Id": user_id} if user_id else {}


def _event_id(entity_id: str, user_id: str | None = None) -> str:
    response = client.get("/v1/opportunities", headers=_headers(user_id))
    item = next(i for i in response.json()["items"] if i["entity_id"] == entity_id)
    return item["event_id"]


# --- Restart-safety matrix -------------------------------------------------


def test_restart_safety_matrix(monkeypatch, tmp_path):
    """Documents, as a real executable contract, exactly what survives a
    simulated backend restart when STRATUS_PERSIST_MEMORY is enabled and
    what does not. Anything not explicitly asserted here should be treated
    as undocumented -- extend this test, don't leave a gap silent."""
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv("STRATUS_STATE_DB_PATH", str(tmp_path / "state.db"))
    monkeypatch.delenv("STRATUS_LIVE_NVDA_EARNINGS", raising=False)
    reset_pipeline_state()
    reset_notification_state()

    event_id = _event_id("NVDA")
    provider = FixtureAskLlmProvider(answer="Answer.")
    with patch("backend.app.main.get_ask_llm_provider", return_value=provider):
        client.post(
            "/v1/ask",
            json={
                "message": "What changed?",
                "event_id": event_id,
                "session_id": "restart-matrix",
            },
        )
    client.post(
        "/v1/interactions",
        json={
            "event_id": str(uuid4()),
            "entity_id": "NVDA",
            "domain": "stocks",
            "interaction_type": "save",
        },
    )
    client.post(
        "/v1/notifications/register",
        json={"expo_push_token": "ExponentPushToken[restart-test]"},
    )
    orchestrator_before = _get_orchestrator()
    fatigue_state_before = (
        orchestrator_before.deps.prioritization_engine.attention_state(
            LOCAL_FOUNDER_USER_ID
        )
    )
    assert fatigue_state_before is not None  # real AttentionState exists pre-restart

    records_before = orchestrator_before.deps.memory_store.all(
        user_id=LOCAL_FOUNDER_USER_ID
    )
    assert len(records_before) >= 2  # ask_followup + the explicit save interaction

    # --- Simulated restart: drops every in-process singleton. The SQLite
    # file itself is untouched -- exactly what a real process exit/restart
    # would do.
    reset_pipeline_state()
    reset_notification_state()

    orchestrator_after = _get_orchestrator()

    # SURVIVES: MemoryStore's durable behavioral records (the actual point
    # of STRATUS_PERSIST_MEMORY).
    records_after = orchestrator_after.deps.memory_store.all(
        user_id=LOCAL_FOUNDER_USER_ID
    )
    assert len(records_after) == len(records_before)

    # DOES NOT SURVIVE: PrioritizationEngine's AttentionState (Watch fatigue/
    # cooldown/notification-review) -- always a fresh, empty per-user dict on
    # every new Orchestrator, persistence flag or not.
    fatigue_state_after = orchestrator_after.deps.prioritization_engine.attention_state(
        LOCAL_FOUNDER_USER_ID
    )
    assert fatigue_state_after is None

    # DOES NOT SURVIVE: Ask STRATUS conversation history -- never persisted
    # to SQLite by design (ADR-055/058); a session_id from before a restart
    # resolves to no history at all.
    assert get_ask_history(LOCAL_FOUNDER_USER_ID, "restart-matrix") == []

    # SURVIVES (Sprint 3.6.9 Block 1): registered push tokens and dispatch/
    # review dedup state, when STRATUS_PERSIST_MEMORY is enabled -- see
    # notification_store.py. This test enables STRATUS_PERSIST_MEMORY (same
    # flag as MemoryStore's own durability above), so the pre-restart
    # registration is expected to still be there; see
    # test_notification_persistence.py for the dedicated disabled-vs-enabled
    # contrast and the dispatch-dedup-survives-restart correctness case.
    response = client.post(
        "/v1/notifications/register",
        json={"expo_push_token": "ExponentPushToken[post-restart]"},
    )
    assert response.json()["token_count"] == 2  # old registration persisted + new one


# --- Multi-user regression through the full Block 3 conversational stack --


def test_conversational_stack_end_to_end_multi_user_isolation():
    """Re-proves every Block 2 guarantee (ADR-057), but through Block 3's
    actual conversational path (multiple turns, real history, an anchor
    switch) rather than the single-turn surface Block 2's own tests used."""
    reset_pipeline_state()
    event_id_a = _event_id("NVDA", USER_A)
    event_id_b_aapl = _event_id("AAPL", USER_B)

    provider = FixtureAskLlmProvider(answer="Answer.")
    with patch("backend.app.main.get_ask_llm_provider", return_value=provider):
        for question in ["What changed?", "Why?", "Which signal is strongest?"]:
            response = client.post(
                "/v1/ask",
                json={
                    "message": question,
                    "event_id": event_id_a,
                    "session_id": "shared-name",
                },
                headers=_headers(USER_A),
            )
            assert response.json()["grounded"] is True

        for question in ["What changed?", "How confident are you?"]:
            response = client.post(
                "/v1/ask",
                json={
                    "message": question,
                    "event_id": event_id_b_aapl,
                    "session_id": "shared-name",
                },
                headers=_headers(USER_B),
            )
            assert response.json()["grounded"] is True

    history_a = get_ask_history(USER_A, "shared-name")
    history_b = get_ask_history(USER_B, "shared-name")
    assert len(history_a) == 6  # 3 real turns
    assert len(history_b) == 4  # 2 real turns
    assert "AAPL" not in " ".join(t.text for t in history_a)
    assert "NVDA" not in " ".join(t.text for t in history_b)

    orchestrator = _get_orchestrator()
    followups_a = [
        r
        for r in orchestrator.deps.memory_store.all(user_id=USER_A)
        if isinstance(r.content, dict)
        and r.content.get("interaction_type") == "ask_followup"
    ]
    followups_b = [
        r
        for r in orchestrator.deps.memory_store.all(user_id=USER_B)
        if isinstance(r.content, dict)
        and r.content.get("interaction_type") == "ask_followup"
    ]
    assert len(followups_a) == 1  # bounded despite 3 real conversational turns
    assert len(followups_b) == 1
    assert all(r.user_id == USER_A for r in followups_a)
    assert all(r.user_id == USER_B for r in followups_b)


# --- Full integrated acceptance path ----------------------------------------


def test_full_acceptance_path_no_holding_to_matured_bounded_relevance(
    monkeypatch, tmp_path
):
    """The Block 4 acceptance scenario, using fixtures throughout (never
    manipulating live-market thresholds to force a result): a user with no
    explicit AAPL holding sees the AAPL opportunity, engages with it across
    a real conversational Ask exchange plus repeated meaningful interactions,
    a simulated restart occurs with durable persistence enabled, evidence
    survives correctly scoped, and a rebuild afterward shows genuinely
    matured -- but still bounded -- relevance, while a second user and
    Watch's fatigue/cooldown machinery remain completely unaffected
    throughout.
    """
    from logan_core.learning.engine import FEEDBACK_DEDUP_WINDOW
    from logan_core.user_model import UserModelBuilder

    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv("STRATUS_STATE_DB_PATH", str(tmp_path / "state.db"))
    monkeypatch.delenv("STRATUS_LIVE_NVDA_EARNINGS", raising=False)
    reset_pipeline_state()
    reset_notification_state()

    # 1. No explicit holding: AAPL is a real fixture entity with no seeded
    # explicit interest for LOCAL_FOUNDER_USER_ID (unlike NVDA/AI_SECTOR).
    aapl_id = _event_id("AAPL")

    # 2 & 3. Real opportunity is presented; initial personal_relevance is
    # limited (no explicit connection) -- proven via an honest, non-
    # personalized-claim Ask STRATUS answer (deterministic path, no LLM
    # needed for this assertion).
    with patch("backend.app.main.get_ask_llm_provider", return_value=None):
        first_answer = client.post(
            "/v1/ask",
            json={"message": "why does this matter to me?", "event_id": aapl_id},
        ).json()["answer"]
    assert "you're tracking a holding" not in first_answer.lower()

    # 4 & 5. A real conversational Ask exchange, grounded (fixture LLM).
    provider = FixtureAskLlmProvider(answer="STRATUS's grounded read on AAPL.")
    with patch("backend.app.main.get_ask_llm_provider", return_value=provider):
        for question in ["What changed?", "Why does that matter?"]:
            response = client.post(
                "/v1/ask",
                json={
                    "message": question,
                    "event_id": aapl_id,
                    "session_id": "acceptance-session",
                },
            )
            assert response.json()["grounded"] is True

    # 6. ASK_FOLLOWUP recorded once, within bounds, despite two real turns.
    orchestrator = _get_orchestrator()
    followups = [
        r
        for r in orchestrator.deps.memory_store.all(user_id=LOCAL_FOUNDER_USER_ID)
        if isinstance(r.content, dict)
        and r.content.get("interaction_type") == "ask_followup"
    ]
    assert len(followups) == 1

    # Additional real, meaningful engagement, spaced beyond the short-window
    # dedup so each independently qualifies (the same fixture-timing
    # technique test_ask_route.py's own acceptance test already established).
    for _ in range(3):
        client.post(
            "/v1/interactions",
            json={
                "event_id": str(uuid4()),
                "entity_id": "AAPL",
                "domain": "stocks",
                "interaction_type": "save",
            },
        )
        records = orchestrator.deps.memory_store.all(user_id=LOCAL_FOUNDER_USER_ID)
        latest = max(
            (
                r
                for r in records
                if isinstance(r.content, dict)
                and r.content.get("interaction_type") == "save"
            ),
            key=lambda r: r.created_at,
        )
        rewound = latest.model_copy(
            update={"created_at": latest.created_at - FEEDBACK_DEDUP_WINDOW * 2}
        )
        orchestrator.deps.memory_store.write(rewound, writer="learning_system")

    # 7. Simulated restart where durable state matters -- persistence is
    # enabled, so this is a real exercise of the SQLite-backed reload path,
    # not just an in-process reset.
    reset_pipeline_state()
    orchestrator = _get_orchestrator()

    # 8. Behavioral evidence remains correctly scoped after the restart.
    survived_records = orchestrator.deps.memory_store.all(user_id=LOCAL_FOUNDER_USER_ID)
    assert len(survived_records) >= 4  # 1 ask_followup + 3 spaced save interactions

    # 9. A rebuild from the survived records shows genuinely matured, but
    # still bounded, relevance -- the same invariant ADR-053/055's own
    # acceptance tests already established, re-proven here as part of the
    # full integrated path rather than in isolation.
    base = UserModelBuilder().seed(user_id=LOCAL_FOUNDER_USER_ID)
    rebuilt = UserModelBuilder().build(
        user_id=LOCAL_FOUNDER_USER_ID,
        memory_records=orchestrator.deps.memory_store.query(
            user_id=LOCAL_FOUNDER_USER_ID
        ),
        base=base,
    )
    aapl_interest = next((i for i in rebuilt.interests if i.topic == "AAPL"), None)
    assert aapl_interest is not None
    assert aapl_interest.source == "inferred"
    assert 0.0 < aapl_interest.weight <= 1.0  # matured, but never unbounded

    # 10. Watch fatigue/cooldown remains authoritative -- AttentionState is
    # a fresh, empty per-user dict after the restart (never persisted, by
    # design -- see the restart-safety matrix test above), so no leftover
    # fatigue/cooldown state could have silently suppressed anything here.
    assert (
        orchestrator.deps.prioritization_engine.attention_state(LOCAL_FOUNDER_USER_ID)
        is None
    )

    # 11. A second user is provably unaffected by any of the above.
    user_b_response = client.get("/v1/opportunities", headers=_headers(USER_B))
    assert user_b_response.status_code == 200
    user_b_records = orchestrator.deps.memory_store.all(user_id=USER_B)
    assert user_b_records == []
