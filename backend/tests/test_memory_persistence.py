"""Sprint 3.6.7 Block 3 -- backend-level persistence: memory_persistence_enabled()
gating, and the full "learned behavioral relevance survives a backend
restart" acceptance scenario, using STRATUS_STATE_DB_PATH to point at an
isolated temp file (never the real local database).
"""

from uuid import uuid4

from backend.app.logan_feed import _get_orchestrator, reset_pipeline_state


def test_disabled_by_default_orchestrator_has_in_memory_store(monkeypatch):
    monkeypatch.delenv("STRATUS_PERSIST_MEMORY", raising=False)
    reset_pipeline_state()
    orchestrator = _get_orchestrator()
    # In-memory MemoryStore has no underlying SQLite connection.
    assert orchestrator.deps.memory_store._conn is None  # noqa: SLF001


def test_enabled_mode_orchestrator_has_a_sqlite_connection(monkeypatch, tmp_path):
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv("STRATUS_STATE_DB_PATH", str(tmp_path / "state.db"))
    reset_pipeline_state()
    orchestrator = _get_orchestrator()
    assert orchestrator.deps.memory_store._conn is not None  # noqa: SLF001


def test_interactions_survive_a_simulated_backend_restart(monkeypatch, tmp_path):
    from backend.app.logan_feed import record_interaction

    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv("STRATUS_STATE_DB_PATH", str(tmp_path / "state.db"))
    monkeypatch.delenv("STRATUS_LIVE_NVDA_EARNINGS", raising=False)
    reset_pipeline_state()

    event_id = uuid4()
    record_interaction(
        event_id=event_id, entity_id="AMD", domain="stocks", interaction_type="save"
    )
    record_interaction(
        event_id=uuid4(), entity_id="AMD", domain="stocks", interaction_type="save"
    )

    orchestrator_before = _get_orchestrator()
    assert len(orchestrator_before.deps.memory_store.all()) == 2

    # Simulate a real backend restart: drop all in-process state (this is
    # exactly what reset_pipeline_state() does -- the SQLite file itself is
    # untouched, matching what a real process exit/restart would do).
    reset_pipeline_state()

    orchestrator_after = _get_orchestrator()
    records = orchestrator_after.deps.memory_store.all()
    assert len(records) == 2
    assert all(r.entities == ["AMD"] for r in records)


def test_matured_behavioral_relevance_survives_a_simulated_restart(
    monkeypatch, tmp_path
):
    """The Block 3 acceptance target: no explicit AMD holding, several
    meaningful engagements recorded, a simulated restart, and the inferred
    behavioral relevance is still present and explainable afterward."""
    from backend.app.logan_feed import record_interaction
    from logan_core.contracts import LOCAL_FOUNDER_USER_ID
    from logan_core.user_model import UserModelBuilder

    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv("STRATUS_STATE_DB_PATH", str(tmp_path / "state.db"))
    monkeypatch.delenv("STRATUS_LIVE_NVDA_EARNINGS", raising=False)
    reset_pipeline_state()

    for _ in range(4):
        record_interaction(
            event_id=uuid4(),
            entity_id="AMD",
            domain="stocks",
            interaction_type="save",
        )

    # Simulated restart.
    reset_pipeline_state()
    orchestrator = _get_orchestrator()

    base = UserModelBuilder().seed(user_id=LOCAL_FOUNDER_USER_ID)
    rebuilt = UserModelBuilder().build(
        user_id=LOCAL_FOUNDER_USER_ID,
        memory_records=orchestrator.deps.memory_store.query(),
        base=base,
    )
    amd_interest = next((i for i in rebuilt.interests if i.topic == "AMD"), None)
    assert amd_interest is not None
    assert amd_interest.source == "inferred"
    assert amd_interest.weight > 0.85  # matured past a single save's own 0.85

    behavior = next(
        b for b in rebuilt.established_behaviors if b.label == "engaged_with_AMD"
    )
    assert behavior.evidence_count == 4
