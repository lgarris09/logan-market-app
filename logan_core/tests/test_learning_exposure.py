"""Sprint 3.6.7 Block 3 -- LearningEngine.process_exposure() (deterministic
exposure/impression facts) and process_feedback()'s new short-window
duplicate protection.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from logan_core.contracts import FeedbackSignal
from logan_core.learning import LearningEngine
from logan_core.memory import MemoryStore

NOW = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)


def _feedback_signal(
    event_id, interaction_type="save", intent_confidence=0.85, observed_at=NOW
):
    return FeedbackSignal(
        event_id=event_id,
        interaction_type=interaction_type,
        inferred_intent="interested",
        intent_confidence=intent_confidence,
        raw_interaction=interaction_type,
        observed_at=observed_at,
    )


# --- process_exposure ------------------------------------------------


def test_first_exposure_creates_a_new_exposure_record():
    store = MemoryStore()
    engine = LearningEngine(store)
    event_id = uuid4()

    write = engine.process_exposure(event_id, "demo_user", "stocks", "NVDA", now=NOW)

    assert write.write_type == "new_record"
    assert write.confidence == 1.0
    records = store.all(user_id="demo_user")
    assert len(records) == 1
    assert records[0].record_type == "exposure_record"
    assert records[0].operational_ref == event_id
    content = records[0].content
    assert isinstance(content, dict)
    assert content["impression_count"] == 1
    assert records[0].entities == ["NVDA"]


def test_repeated_exposure_updates_the_same_record_not_a_duplicate():
    store = MemoryStore()
    engine = LearningEngine(store)
    event_id = uuid4()

    engine.process_exposure(event_id, "demo_user", "stocks", "NVDA", now=NOW)
    write2 = engine.process_exposure(
        event_id, "demo_user", "stocks", "NVDA", now=NOW + timedelta(minutes=1)
    )

    assert write2.write_type == "update_record"
    records = store.all(user_id="demo_user")
    assert len(records) == 1
    content = records[0].content
    assert isinstance(content, dict)
    assert content["impression_count"] == 2


def test_exposure_records_do_not_grow_unbounded_over_many_impressions():
    store = MemoryStore()
    engine = LearningEngine(store)
    event_id = uuid4()

    for i in range(50):
        engine.process_exposure(
            event_id, "demo_user", "stocks", "NVDA", now=NOW + timedelta(minutes=i)
        )

    records = store.all(user_id="demo_user")
    assert len(records) == 1
    content = records[0].content
    assert isinstance(content, dict)
    assert content["impression_count"] == 50


def test_exposure_for_different_events_creates_independent_records():
    store = MemoryStore()
    engine = LearningEngine(store)

    engine.process_exposure(uuid4(), "demo_user", "stocks", "NVDA", now=NOW)
    engine.process_exposure(uuid4(), "demo_user", "stocks", "NVDA", now=NOW)

    assert len(store.all(user_id="demo_user")) == 2


def test_exposure_never_creates_a_feedback_record():
    """Impressions must never be readable by UserModelBuilder's existing
    "interested"-intent feedback_record folding -- structurally impossible
    since this writes a different record_type entirely."""
    store = MemoryStore()
    engine = LearningEngine(store)
    engine.process_exposure(uuid4(), "demo_user", "stocks", "NVDA", now=NOW)

    assert all(
        r.record_type == "exposure_record" for r in store.all(user_id="demo_user")
    )


# --- process_feedback short-window dedup -------------------------------


def test_duplicate_feedback_within_window_does_not_create_a_second_record():
    store = MemoryStore()
    engine = LearningEngine(store)
    event_id = uuid4()

    write1 = engine.process_feedback(
        _feedback_signal(event_id, "save", observed_at=NOW),
        "demo_user",
        "stocks",
        ["NVDA"],
        {"interaction_type": "save"},
    )
    write2 = engine.process_feedback(
        _feedback_signal(event_id, "save", observed_at=NOW + timedelta(minutes=1)),
        "demo_user",
        "stocks",
        ["NVDA"],
        {"interaction_type": "save"},
    )

    assert write1.write_type == "new_record"
    assert write2.write_type == "update_record"
    assert len(store.all(user_id="demo_user")) == 1


def test_feedback_outside_dedup_window_creates_a_genuinely_new_record():
    """A later, separate session viewing the same card again is real
    repeated evidence, not a duplicate -- must still create a new record."""
    store = MemoryStore()
    engine = LearningEngine(store)
    event_id = uuid4()

    engine.process_feedback(
        _feedback_signal(event_id, "save", observed_at=NOW),
        "demo_user",
        "stocks",
        ["NVDA"],
        {"interaction_type": "save"},
    )
    engine.process_feedback(
        _feedback_signal(event_id, "save", observed_at=NOW + timedelta(hours=1)),
        "demo_user",
        "stocks",
        ["NVDA"],
        {"interaction_type": "save"},
    )

    assert len(store.all(user_id="demo_user")) == 2


def test_different_interaction_type_on_same_event_is_not_deduped():
    """A "view" moments after a "save" on the same card are two real,
    distinct signals, not a duplicate."""
    store = MemoryStore()
    engine = LearningEngine(store)
    event_id = uuid4()

    engine.process_feedback(
        _feedback_signal(event_id, "save", observed_at=NOW),
        "demo_user",
        "stocks",
        ["NVDA"],
        {"interaction_type": "save"},
    )
    engine.process_feedback(
        _feedback_signal(event_id, "view", intent_confidence=0.65, observed_at=NOW),
        "demo_user",
        "stocks",
        ["NVDA"],
        {"interaction_type": "view"},
    )

    assert len(store.all(user_id="demo_user")) == 2


def test_memory_inbox_paths_are_never_deduped():
    """Explicit, deliberate confirm/reject actions are never fired by
    passive polling/retries -- the dedup window is scoped to ordinary
    feedback_record writes only."""
    store = MemoryStore()
    engine = LearningEngine(store)
    event_id = uuid4()
    signal = FeedbackSignal(
        event_id=event_id,
        interaction_type="act",
        inferred_intent="interested",
        intent_confidence=1.0,
        raw_interaction="memory_inbox_confirm",
        observed_at=NOW,
    )

    engine.process_feedback(signal, "demo_user", "stocks", ["NVDA"], "confirmed once")
    engine.process_feedback(signal, "demo_user", "stocks", ["NVDA"], "confirmed again")

    assert len(store.all(user_id="demo_user")) == 2
