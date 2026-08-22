"""Layer 7 direct unit tests (V3.1.4 BATCH-2 -- previously uncovered)."""

from datetime import datetime, timezone
from uuid import uuid4

from logan_core.active_context import ActiveContextBuilder
from logan_core.contracts import (
    EnrichedEvent,
    Entity,
    EvidenceTrust,
    Holding,
    Interest,
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
    # Sprint 3.6.6E: this layer only knows entity_id is present in
    # user_model.holdings -- today that's hardcoded seed data
    # (LOCAL_FOUNDER_USER_ID="demo_user"), not a real per-user holdings
    # store. Wording must describe what the system actually knows ("tracking
    # a holding"), never assert an externally-verified financial fact
    # ("you hold a position") it has no way to confirm.
    assert "tracking a holding" in result.personal_relevance_narrative
    assert "you hold a position" not in result.personal_relevance_narrative.lower()


def test_interest_connection_is_honest_about_tracking_not_following():
    """Sprint 3.6.6E: the interest-connected (not directly held) branch has
    the same truthfulness issue as the holds_directly branch -- 'which you
    follow' asserts a verified user behavior connected_entities (drawn from
    user_model.interests, hardcoded seed data today) cannot confirm."""
    event = _event(entity_id="AI_SECTOR")
    trust = _trust(event.event_id, trust_score=0.8)
    user_model = UserModel(
        user_id="demo_user",
        holdings=[],
        interests=[
            Interest(
                domain="social",
                topic="AI_SECTOR",
                weight=0.8,
                source="explicit",
                created_at=NOW,
                last_updated=NOW,
            )
        ],
        risk_tolerance="moderate",
        model_confidence=0.5,
        last_updated=NOW,
        version=1,
    )

    result = ReasoningEngine().reason(event, trust, user_model, _active_context())
    assert "AI_SECTOR" in result.connected_entities
    assert "you're tracking" in result.personal_relevance_narrative
    assert "which you follow" not in result.personal_relevance_narrative


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


def test_inferred_only_interest_is_a_separate_weaker_connection():
    """Behavioral-personalization pass: an Interest(source="inferred") that
    isn't also explicit/held must populate connected_entities_inferred, not
    connected_entities_explicit -- a genuinely separate, weaker signal (see
    OpportunityEngine.evaluate()'s "connect" step), not treated identically
    to an explicit connection."""
    event = _event(entity_id="AI_SECTOR")
    trust = _trust(event.event_id, trust_score=0.8)
    user_model = UserModel(
        user_id="demo_user",
        holdings=[],
        interests=[
            Interest(
                domain="social",
                topic="AI_SECTOR",
                weight=0.6,
                source="inferred",
                created_at=NOW,
                last_updated=NOW,
            )
        ],
        risk_tolerance="moderate",
        model_confidence=0.5,
        last_updated=NOW,
        version=1,
    )

    result = ReasoningEngine().reason(event, trust, user_model, _active_context())
    assert result.connected_entities_inferred == ["AI_SECTOR"]
    assert result.connected_entities_explicit == []
    assert result.connected_entities == ["AI_SECTOR"]
    assert result.decision_trace[0].evidence == [
        "explicit_connections=[]",
        "inferred_connections=['AI_SECTOR']",
    ]


def test_explicit_interest_is_the_stronger_connection():
    event = _event(entity_id="AI_SECTOR")
    trust = _trust(event.event_id, trust_score=0.8)
    user_model = UserModel(
        user_id="demo_user",
        holdings=[],
        interests=[
            Interest(
                domain="social",
                topic="AI_SECTOR",
                weight=0.8,
                source="explicit",
                created_at=NOW,
                last_updated=NOW,
            )
        ],
        risk_tolerance="moderate",
        model_confidence=0.5,
        last_updated=NOW,
        version=1,
    )

    result = ReasoningEngine().reason(event, trust, user_model, _active_context())
    assert result.connected_entities_explicit == ["AI_SECTOR"]
    assert result.connected_entities_inferred == []


def test_entity_both_explicit_and_inferred_counts_only_as_explicit():
    """An entity that's both an inferred and explicit interest is the
    stronger (explicit) signal only -- not double-counted as both."""
    event = _event(entity_id="AI_SECTOR")
    trust = _trust(event.event_id, trust_score=0.8)
    user_model = UserModel(
        user_id="demo_user",
        holdings=[],
        interests=[
            Interest(
                domain="social",
                topic="AI_SECTOR",
                weight=0.8,
                source="explicit",
                created_at=NOW,
                last_updated=NOW,
            ),
            Interest(
                domain="social",
                topic="AI_SECTOR",
                weight=0.6,
                source="inferred",
                created_at=NOW,
                last_updated=NOW,
            ),
        ],
        risk_tolerance="moderate",
        model_confidence=0.5,
        last_updated=NOW,
        version=1,
    )

    result = ReasoningEngine().reason(event, trust, user_model, _active_context())
    assert result.connected_entities_explicit == ["AI_SECTOR"]
    assert result.connected_entities_inferred == []
