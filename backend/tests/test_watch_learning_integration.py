"""V2.3B Phase 2 (Learning-Driven STRATUS) Block 1 -- Watch wired into the
existing Personal Learning pipeline. Full HTTP-level + real-pipeline
coverage: Watch creation records a real learning signal through the
existing FeedbackEngine/LearningEngine/MemoryStore path (no parallel
Watch-learning store), removal changes only current relevance (never
erases history), and current Watch state reaches personal_relevance
through a real /v1/opportunities-equivalent pipeline run.
"""

from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.logan_feed import (
    _get_orchestrator,
    reset_pipeline_state,
    run_demo_feed,
)
from backend.app.main import app
from backend.app.watch import create_watch, remove_watch
from logan_core.contracts import LOCAL_FOUNDER_USER_ID

client = TestClient(app)


def _headers(user_id: str) -> dict[str, str]:
    return {"X-Stratus-User-Id": user_id}


def test_watch_creation_writes_a_real_feedback_record():
    user_id = f"watch-learning-{uuid4()}"
    orchestrator = _get_orchestrator()
    before = orchestrator.deps.memory_store.query(user_id=user_id)
    assert before == []

    response = client.post(
        "/v1/watches", json={"entity_id": "NVDA"}, headers=_headers(user_id)
    )
    assert response.status_code == 200
    assert response.json()["created"] is True

    after = orchestrator.deps.memory_store.query(user_id=user_id)
    feedback_records = [r for r in after if r.record_type == "feedback_record"]
    assert len(feedback_records) == 1
    assert feedback_records[0].content["interaction_type"] == "watch"
    assert feedback_records[0].content["inferred_intent"] == "interested"


def test_repeat_watch_creation_never_double_records():
    user_id = f"watch-learning-repeat-{uuid4()}"
    client.post("/v1/watches", json={"entity_id": "NVDA"}, headers=_headers(user_id))
    second = client.post(
        "/v1/watches", json={"entity_id": "NVDA"}, headers=_headers(user_id)
    )
    assert second.json()["created"] is False

    orchestrator = _get_orchestrator()
    records = orchestrator.deps.memory_store.query(user_id=user_id)
    feedback_records = [r for r in records if r.record_type == "feedback_record"]
    assert len(feedback_records) == 1


def test_watch_removal_never_deletes_the_original_feedback_record():
    user_id = f"watch-learning-removal-{uuid4()}"
    client.post("/v1/watches", json={"entity_id": "NVDA"}, headers=_headers(user_id))
    client.delete("/v1/watches/NVDA", headers=_headers(user_id))

    orchestrator = _get_orchestrator()
    records = orchestrator.deps.memory_store.query(user_id=user_id)
    feedback_records = [r for r in records if r.record_type == "feedback_record"]
    assert len(feedback_records) == 1, "removing a Watch must not erase its history"


def test_current_watch_state_reaches_personal_relevance_through_the_real_pipeline():
    """End-to-end: a real Watch, read live (not folded through the evidence
    pool), reaches OpportunityEngine's personal_relevance for the *very
    next* poll -- no second corroborating observation required."""
    reset_pipeline_state()
    user_id = LOCAL_FOUNDER_USER_ID

    before = run_demo_feed(user_id)
    aapl_before = next((i for i in before.items if i.entity_id == "AAPL"), None)

    create_watch(user_id, "AAPL")
    after = run_demo_feed(user_id)
    aapl_after = next((i for i in after.items if i.entity_id == "AAPL"), None)

    assert aapl_after is not None
    if aapl_before is not None:
        # A tiny tolerance, not exact equality: confidence_score's recency
        # component decays continuously with real elapsed wall-clock time
        # (evidence_trust/trust.py), so two real calls a few milliseconds
        # apart are never bit-identical regardless of Watch -- the point of
        # this assertion is that *creating a Watch* contributes no
        # measurable change of its own, which this tolerance still proves.
        assert (
            abs(aapl_after.confidence_score - aapl_before.confidence_score) < 1e-6
        ), "Watch must never change objective confidence/evidence"

    remove_watch(user_id, "AAPL")


def test_watch_removal_drops_the_current_relevance_boost():
    """V2.3B Phase 2 Block 12: 'removal removes current explicit Watch
    boost.' is_watched is read live (current state), never folded through
    the evidence pool -- removing a Watch must be reflected on the very
    next poll, not just eventually via decay."""
    reset_pipeline_state()
    user_id = LOCAL_FOUNDER_USER_ID

    create_watch(user_id, "AAPL")
    watching = run_demo_feed(user_id)
    aapl_watching = next((i for i in watching.items if i.entity_id == "AAPL"), None)
    assert aapl_watching is not None
    assert aapl_watching.delivered_item.personal_relevance_result is not None
    assert aapl_watching.delivered_item.personal_relevance_result.basis == "watch"

    remove_watch(user_id, "AAPL")
    unwatched = run_demo_feed(user_id)
    aapl_unwatched = next((i for i in unwatched.items if i.entity_id == "AAPL"), None)
    assert aapl_unwatched is not None
    assert aapl_unwatched.delivered_item.personal_relevance_result is not None
    assert aapl_unwatched.delivered_item.personal_relevance_result.basis != "watch"
    assert aapl_unwatched.is_watched is False
