"""Behavioral-personalization foundation (Part A): tests for the new
POST /v1/interactions route and backend/app/logan_feed.record_interaction.

These prove the new route is a thin, faithful passthrough into the existing,
unmodified FeedbackSignal -> FeedbackEngine -> LearningEngine -> MemoryStore
path (see ADR-047) -- not a parallel personalization system. The dwell/
interaction-type interpretation thresholds themselves belong to
FeedbackEngine and are already covered by logan_core's own tests; these
tests only prove that a real interaction reaches that existing logic
unchanged and lands in MemoryStore via the existing single-writer gate.
"""

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.logan_feed import _get_orchestrator, record_interaction
from backend.app.main import app

client = TestClient(app)


def test_view_interaction_reaches_memory_store():
    event_id = uuid4()
    record_interaction(
        event_id=event_id,
        entity_id="NVDA",
        domain="stocks",
        interaction_type="view",
        duration_ms=9000,  # >= 8000ms -> interested/0.65 per FeedbackEngine
    )

    orchestrator = _get_orchestrator()
    records = orchestrator.deps.memory_store.query(domain="stocks", entities=["NVDA"])
    assert len(records) == 1
    assert records[0].entities == ["NVDA"]
    assert records[0].domain == "stocks"


def test_short_dwell_view_does_not_produce_a_high_confidence_interested_record():
    """A view under 2000ms is interpreted as accidental/0.55 by the existing,
    unmodified FeedbackEngine -- this must remain true through the new route,
    not just when FeedbackEngine.interpret() is called directly."""
    event_id = uuid4()
    feedback, _write = _get_orchestrator().run_feedback_loop(
        event_id=event_id,
        user_id="local-founder",
        domain="stocks",
        entities=["TSLA"],
        interaction_type="view",
        content="view on TSLA (stocks)",
        duration_ms=500,
    )
    assert feedback.inferred_intent == "accidental"
    assert feedback.intent_confidence == 0.55


def test_click_interaction_is_distinguishable_from_view():
    """Notification-open (click) must be a recognizably different interaction
    from a card-open/dwell (view), reusing the existing InteractionType
    rather than a new field."""
    event_id = uuid4()
    record_interaction(
        event_id=event_id,
        entity_id="FED",
        domain="stocks",
        interaction_type="click",
    )
    records = _get_orchestrator().deps.memory_store.query(
        domain="stocks", entities=["FED"]
    )
    assert len(records) == 1
    content = records[0].content
    assert isinstance(content, dict)
    assert content["interaction_type"] == "click"


def test_record_interaction_routes_through_orchestrator_ownership():
    """Behavioral-personalization pass (restoring ADR-047): record_interaction()
    must go through Orchestrator.run_feedback_loop(), never call
    feedback_engine.interpret()/learning_engine.process_feedback() directly --
    the Orchestrator remains the sole owner of that sequencing."""
    event_id = uuid4()
    orchestrator = _get_orchestrator()
    with patch.object(
        orchestrator, "run_feedback_loop", wraps=orchestrator.run_feedback_loop
    ) as spy:
        record_interaction(
            event_id=event_id,
            entity_id="NVDA",
            domain="stocks",
            interaction_type="watch",
        )
    spy.assert_called_once()


def test_record_interaction_interprets_exactly_once():
    """The content-builder callable must not cause a second interpretation of
    the same interaction -- run_feedback_loop() calls interpret() exactly
    once and hands the same FeedbackSignal to both the content builder and
    LearningEngine.process_feedback()."""
    event_id = uuid4()
    feedback_engine = _get_orchestrator().deps.feedback_engine
    with patch.object(
        feedback_engine, "interpret", wraps=feedback_engine.interpret
    ) as spy:
        record_interaction(
            event_id=event_id,
            entity_id="NVDA",
            domain="stocks",
            interaction_type="watch",
        )
    spy.assert_called_once()


def test_record_interaction_content_carries_real_inferred_intent_and_confidence():
    """Structured Memory content must reflect FeedbackEngine's own
    interpretation (not a re-derived or throwaway value) -- "watch" is
    deterministically interested/0.85 per FeedbackEngine.interpret()."""
    event_id = uuid4()
    record_interaction(
        event_id=event_id,
        entity_id="AAPL",
        domain="stocks",
        interaction_type="watch",
    )
    records = _get_orchestrator().deps.memory_store.query(
        domain="stocks", entities=["AAPL"]
    )
    assert len(records) == 1
    content = records[0].content
    assert content == {
        "interaction_type": "watch",
        "entity_id": "AAPL",
        "domain": "stocks",
        "inferred_intent": "interested",
        "intent_confidence": 0.85,
        "duration_ms": None,
    }


def test_route_records_interaction_end_to_end():
    event_id = uuid4()
    response = client.post(
        "/v1/interactions",
        json={
            "event_id": str(event_id),
            "entity_id": "AI_SECTOR",
            "domain": "stocks",
            "interaction_type": "view",
            "duration_ms": 3000,
        },
    )
    assert response.status_code == 200
    assert response.json() == {"recorded": True}

    records = _get_orchestrator().deps.memory_store.query(
        domain="stocks", entities=["AI_SECTOR"]
    )
    assert len(records) == 1


def test_route_rejects_invalid_domain():
    response = client.post(
        "/v1/interactions",
        json={
            "event_id": str(uuid4()),
            "entity_id": "NVDA",
            "domain": "not-a-real-domain",
            "interaction_type": "view",
        },
    )
    assert response.status_code == 422


def test_route_rejects_invalid_interaction_type():
    response = client.post(
        "/v1/interactions",
        json={
            "event_id": str(uuid4()),
            "entity_id": "NVDA",
            "domain": "stocks",
            "interaction_type": "not-a-real-type",
        },
    )
    assert response.status_code == 422


def test_duration_ms_is_optional_for_non_view_interactions():
    """click/dismiss/save/etc. don't need a duration -- must not be forced to
    supply one just to satisfy the contract."""
    response = client.post(
        "/v1/interactions",
        json={
            "event_id": str(uuid4()),
            "entity_id": "NVDA",
            "domain": "stocks",
            "interaction_type": "dismiss",
        },
    )
    assert response.status_code == 200


@pytest.mark.parametrize(
    "domain", ["stocks", "sports", "poly", "social", "news", "crypto"]
)
def test_all_domains_accepted(domain):
    response = client.post(
        "/v1/interactions",
        json={
            "event_id": str(uuid4()),
            "entity_id": "X",
            "domain": domain,
            "interaction_type": "view",
            "duration_ms": 100,
        },
    )
    assert response.status_code == 200
