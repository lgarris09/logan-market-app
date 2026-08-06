"""Layer 7 direct unit tests (V3.1.4 BATCH-2 -- previously uncovered)."""

from datetime import datetime, timezone
from uuid import uuid4

from logan_core.active_context import ActiveContextBuilder
from logan_core.contracts import (
    EnrichedEvent,
    Entity,
    EvidenceTrust,
    Holding,
    UserModel,
)
from logan_core.reasoning import ReasoningEngine

NOW = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)


def _event(entity_id="NVDA", downstream=None, is_new=True, change_delta=None):
    entity = Entity(
        entity_id=entity_id,
        entity_type="ticker",
        display_name="NVIDIA",
        domain="stocks",
    )
    return EnrichedEvent(
        event_id=uuid4(),
        signal_ids=[uuid4()],
        domain="stocks",
        is_new=is_new,
        entities=[entity],
        change_delta=change_delta or [],
        downstream=downstream or [],
        summary=f"{entity.display_name}: test signal",
        occurred_at=NOW,
        enriched_at=NOW,
    )


def _trust(event_id, trust_score=0.7, contradiction_flag=False):
    return EvidenceTrust(
        event_id=event_id,
        source_score=0.8,
        corroboration=1,
        recency_score=0.9,
        contradiction_flag=contradiction_flag,
        manipulation_risk="low",
        completeness=1.0,
        trust_score=trust_score,
        evaluated_at=NOW,
    )


def _user_model(holdings=None):
    return UserModel(
        user_id="demo_user",
        holdings=holdings or [],
        risk_tolerance="moderate",
        model_confidence=0.5,
        last_updated=NOW,
        version=1,
    )


def _active_context():
    return ActiveContextBuilder().build(user_id="demo_user", now=NOW)


def test_direct_holding_is_actionable_and_directly_relevant():
    event = _event(entity_id="NVDA")
    trust = _trust(event.event_id, trust_score=0.8)
    user_model = _user_model(
        holdings=[
            Holding(
                domain="stocks", entity_id="NVDA", display_name="NVIDIA", added_at=NOW
            )
        ]
    )

    result = ReasoningEngine().reason(event, trust, user_model, _active_context())
    assert result.actionability == "actionable"
    assert "NVDA" in result.connected_entities
    assert "directly relevant" in result.personal_relevance_narrative


def test_no_connection_is_informational_and_unconnected():
    event = _event(entity_id="OIL")
    trust = _trust(event.event_id, trust_score=0.8)
    user_model = _user_model(holdings=[])

    result = ReasoningEngine().reason(event, trust, user_model, _active_context())
    assert result.connected_entities == []
    assert "Nothing in your current holdings" in result.personal_relevance_narrative


def test_low_trust_is_ambiguous_regardless_of_holdings():
    event = _event(entity_id="NVDA")
    trust = _trust(event.event_id, trust_score=0.2)
    user_model = _user_model(
        holdings=[
            Holding(
                domain="stocks", entity_id="NVDA", display_name="NVIDIA", added_at=NOW
            )
        ]
    )

    result = ReasoningEngine().reason(event, trust, user_model, _active_context())
    assert result.actionability == "ambiguous"


def test_new_event_has_new_stance():
    event = _event(is_new=True)
    trust = _trust(event.event_id)
    result = ReasoningEngine().reason(event, trust, _user_model(), _active_context())
    assert result.stance == "new"


def test_decision_trace_populated():
    event = _event()
    trust = _trust(event.event_id)
    result = ReasoningEngine().reason(event, trust, _user_model(), _active_context())
    assert len(result.decision_trace) == 1
    assert "stance=" in result.decision_trace[0].rule
