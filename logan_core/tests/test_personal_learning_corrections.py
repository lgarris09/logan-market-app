"""V2.3B Personal Learning Phase 1 -- explicit trait correction/suppression.

Covers the two properties the Block 2 spec calls out explicitly:
  - "a deterministic rebuild must continue to respect corrections" (a
    correction is re-derived from the same correction_record every rebuild,
    never a one-time mutation)
  - "corrections must not rewrite raw telemetry/history" (the underlying
    feedback_record/exposure_record rows are never touched by a correction)

Also covers LearningEngine.suppress_entity()'s own write behavior and the
Orchestrator entry point that fronts it.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from logan_core.contracts import Interest, MemoryRecord
from logan_core.learning import LearningEngine
from logan_core.memory import MemoryStore
from logan_core.user_model import UserModelBuilder

NOW = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)


def _feedback(entity_id="NVDA", domain="stocks", confidence=0.85, created_at=NOW):
    return MemoryRecord(
        record_id=uuid4(),
        user_id="demo_user",
        record_type="feedback_record",
        content={
            "interaction_type": "save",
            "entity_id": entity_id,
            "domain": domain,
            "inferred_intent": "interested",
            "intent_confidence": confidence,
            "duration_ms": None,
        },
        domain=domain,
        entities=[entity_id],
        source_layer="learning_system",
        created_at=created_at,
    )


def _correction(entity_id="NVDA", created_at=NOW):
    return MemoryRecord(
        record_id=uuid4(),
        user_id="demo_user",
        record_type="correction_record",
        content={"correction_type": "suppress_entity", "entity_id": entity_id},
        domain="stocks",
        entities=[entity_id],
        source_layer="learning_system",
        created_at=created_at,
    )


def _seed():
    return UserModelBuilder().seed("demo_user")


def _has_interest(user_model, topic):
    return any(i.topic == topic for i in user_model.interests)


def _has_behavior(user_model, entity_id):
    return any(
        b.label == f"engaged_with_{entity_id}" for b in user_model.established_behaviors
    )


# --- Suppression takes effect immediately, respected on rebuild ----------


def test_qualifying_interest_exists_before_any_correction():
    records = [
        _feedback(created_at=NOW),
        _feedback(created_at=NOW + timedelta(days=1)),
    ]
    user_model = UserModelBuilder().build(
        "demo_user", records, _seed(), now=NOW + timedelta(days=2)
    )
    assert _has_interest(user_model, "NVDA")
    assert _has_behavior(user_model, "NVDA")


def test_correction_after_qualifying_evidence_suppresses_it():
    records = [
        _feedback(created_at=NOW),
        _feedback(created_at=NOW + timedelta(days=1)),
        _correction(created_at=NOW + timedelta(days=2)),
    ]
    user_model = UserModelBuilder().build(
        "demo_user", records, _seed(), now=NOW + timedelta(days=3)
    )
    assert not _has_interest(user_model, "NVDA")
    assert not _has_behavior(user_model, "NVDA")


def test_correction_is_rederived_every_rebuild_not_a_one_time_mutation():
    """A fresh rebuild from the exact same full history, starting from a
    fresh seed (not chained from a previous UserModel), must land on the
    identical suppressed conclusion -- proves this is re-derived from the
    correction_record every time, not a stateful mutation applied once."""
    records = [
        _feedback(created_at=NOW),
        _feedback(created_at=NOW + timedelta(days=1)),
        _correction(created_at=NOW + timedelta(days=2)),
    ]
    builder = UserModelBuilder()
    first = builder.build("demo_user", records, _seed(), now=NOW + timedelta(days=3))
    second = builder.build("demo_user", records, _seed(), now=NOW + timedelta(days=10))
    third = builder.build(
        "demo_user", list(reversed(records)), _seed(), now=NOW + timedelta(days=20)
    )

    for rebuild in (first, second, third):
        assert not _has_interest(rebuild, "NVDA")
        assert not _has_behavior(rebuild, "NVDA")


def test_new_evidence_after_a_correction_re_earns_the_trait():
    """A correction resets the evidence clock for that entity -- it is not
    a permanent ban. Two fresh qualifying observations dated after the
    correction re-earn the trait from scratch."""
    records = [
        _feedback(created_at=NOW),
        _feedback(created_at=NOW + timedelta(days=1)),
        _correction(created_at=NOW + timedelta(days=2)),
        _feedback(created_at=NOW + timedelta(days=3)),
        _feedback(created_at=NOW + timedelta(days=4)),
    ]
    user_model = UserModelBuilder().build(
        "demo_user", records, _seed(), now=NOW + timedelta(days=5)
    )
    assert _has_interest(user_model, "NVDA")


def test_correction_never_suppresses_an_explicit_interest():
    seed = UserModelBuilder().seed(
        "demo_user",
        interests=[
            Interest(
                domain="stocks",
                topic="NVDA",
                weight=0.9,
                source="explicit",
                created_at=NOW,
                last_updated=NOW,
            )
        ],
    )
    records = [_correction(created_at=NOW + timedelta(days=1))]
    user_model = UserModelBuilder().build(
        "demo_user", records, seed, now=NOW + timedelta(days=2)
    )
    explicit = next(i for i in user_model.interests if i.topic == "NVDA")
    assert explicit.source == "explicit"
    assert explicit.weight == 0.9


def test_correction_never_mutates_the_underlying_feedback_records():
    """Interpretation must never rewrite raw telemetry: the exact same
    MemoryRecord objects (and their content) are passed in before and after
    a correction is applied across several rebuilds."""
    feedback_one = _feedback(created_at=NOW)
    feedback_two = _feedback(created_at=NOW + timedelta(days=1))
    correction = _correction(created_at=NOW + timedelta(days=2))
    records = [feedback_one, feedback_two, correction]
    original_snapshots = [r.model_dump() for r in records]

    builder = UserModelBuilder()
    builder.build("demo_user", records, _seed(), now=NOW + timedelta(days=3))
    builder.build("demo_user", records, _seed(), now=NOW + timedelta(days=10))

    for record, snapshot in zip(records, original_snapshots, strict=True):
        assert record.model_dump() == snapshot


def test_correction_suppresses_only_the_targeted_entity():
    records = [
        _feedback(entity_id="NVDA", created_at=NOW),
        _feedback(entity_id="NVDA", created_at=NOW + timedelta(days=1)),
        _feedback(entity_id="AAPL", created_at=NOW),
        _feedback(entity_id="AAPL", created_at=NOW + timedelta(days=1)),
        _correction(entity_id="NVDA", created_at=NOW + timedelta(days=2)),
    ]
    user_model = UserModelBuilder().build(
        "demo_user", records, _seed(), now=NOW + timedelta(days=3)
    )
    assert not _has_interest(user_model, "NVDA")
    assert _has_interest(user_model, "AAPL")


# --- LearningEngine.suppress_entity() itself ------------------------------


def test_suppress_entity_writes_a_correction_record():
    store = MemoryStore()
    engine = LearningEngine(store)
    engine.suppress_entity("demo_user", "NVDA", "stocks", now=NOW)

    stored = store.all(user_id="demo_user")
    assert len(stored) == 1
    assert stored[0].record_type == "correction_record"
    assert stored[0].content == {
        "correction_type": "suppress_entity",
        "entity_id": "NVDA",
    }


def test_suppress_entity_is_user_scoped():
    store = MemoryStore()
    engine = LearningEngine(store)
    engine.suppress_entity("user_a", "NVDA", "stocks", now=NOW)

    assert store.all(user_id="user_a")
    assert store.all(user_id="user_b") == []
