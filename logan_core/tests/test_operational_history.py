"""Operational History bounded retention (ADR-074) -- the in-memory store
keeps only the most recent entries, dropping the oldest first."""

from uuid import uuid4

import pytest

from logan_core.orchestrator import OperationalHistoryStore
from logan_core.orchestrator.history import OPERATIONAL_HISTORY_MAX_ENTRIES


def test_default_bound_is_the_documented_one():
    assert OPERATIONAL_HISTORY_MAX_ENTRIES == 2000
    store = OperationalHistoryStore()
    for index in range(OPERATIONAL_HISTORY_MAX_ENTRIES + 500):
        store.record(uuid4(), "normalized_signal", index, domain="stocks")
    assert len(store) == OPERATIONAL_HISTORY_MAX_ENTRIES
    assert len(store._by_ref) == OPERATIONAL_HISTORY_MAX_ENTRIES


def test_stays_bounded_under_many_times_the_bound():
    store = OperationalHistoryStore(max_entries=10)
    for index in range(10_000):
        store.record(uuid4(), "enriched_event", index)
        assert len(store) <= 10
        assert len(store._by_ref) <= 10
    assert len(store) == 10


def test_recent_history_survives_and_the_oldest_expires_first():
    store = OperationalHistoryStore(max_entries=3)
    refs = [uuid4() for _ in range(5)]
    for index, ref in enumerate(refs):
        store.record(ref, "normalized_signal", index)

    # Deterministic: exactly the two oldest are gone, in insertion order.
    assert store.get(refs[0]) is None
    assert store.get(refs[1]) is None
    kept_entries = [store.get(ref) for ref in refs[2:]]
    assert all(entry is not None for entry in kept_entries)
    assert [entry.payload for entry in kept_entries if entry is not None] == [2, 3, 4]
    assert [entry.payload for entry in store.by_kind("normalized_signal")] == [2, 3, 4]


def test_nothing_expires_below_the_bound():
    store = OperationalHistoryStore(max_entries=100)
    refs = [uuid4() for _ in range(100)]
    for index, ref in enumerate(refs):
        store.record(ref, "normalized_signal", index)
    assert len(store) == 100
    assert all(store.get(ref) is not None for ref in refs)


def test_repeated_polls_of_one_event_do_not_grow_without_bound():
    """The live case: the same event_id is recorded again on every poll."""
    store = OperationalHistoryStore(max_entries=50)
    event_ref = uuid4()
    for poll in range(5_000):
        store.record(event_ref, "enriched_event", poll, domain="stocks")
    assert len(store) == 50
    assert len(store._by_ref) == 1
    # The ref still resolves, to its newest recording.
    newest = store.get(event_ref)
    assert newest is not None
    assert newest.payload == 4_999


def test_a_ref_recorded_again_is_not_forgotten_when_its_older_entry_expires():
    store = OperationalHistoryStore(max_entries=3)
    kept, filler_a, filler_b = uuid4(), uuid4(), uuid4()
    store.record(kept, "enriched_event", "old")
    store.record(filler_a, "normalized_signal", "a")
    store.record(kept, "enriched_event", "new")
    store.record(filler_b, "normalized_signal", "b")  # expires the "old" entry
    kept_entry = store.get(kept)
    assert kept_entry is not None
    assert kept_entry.payload == "new"
    assert len(store) == 3


def test_by_kind_and_by_domain_read_only_retained_entries():
    store = OperationalHistoryStore(max_entries=4)
    for index in range(6):
        store.record(
            uuid4(),
            "normalized_signal" if index % 2 == 0 else "enriched_event",
            index,
            domain="stocks" if index < 3 else "sports",
        )
    assert [entry.payload for entry in store.by_kind("enriched_event")] == [3, 5]
    assert [entry.payload for entry in store.by_domain("stocks")] == [2]
    assert [entry.payload for entry in store.by_domain("sports")] == [3, 4, 5]


def test_a_bound_below_one_is_rejected():
    with pytest.raises(ValueError):
        OperationalHistoryStore(max_entries=0)
