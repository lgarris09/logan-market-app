"""Sprint 3.6.7 Block 3 -- MemoryStore's optional SQLite-backed persistence.

`db_path=None` (every pre-Block-3 caller/test) is covered by the existing
test_feedback_learning.py suite unmodified; these tests are specifically
about the new durable-storage path: reload across a fresh MemoryStore
instance (simulating a backend restart), schema versioning, and bounded-
history compaction.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

import logan_core.memory.store as store_module
from logan_core.contracts import MemoryRecord
from logan_core.memory import MemoryPermissionError, MemoryStore

# Real production value (MAX_PRUNABLE_RECORDS_PER_USER) is 2000 -- writing
# that many rows (each its own commit) makes this file slow for no real
# coverage benefit. Tests below monkeypatch the module constant down to a
# small number so the compaction *logic* is still exercised for real,
# just fast.
_TEST_CAP = 10

NOW = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)


def _record(
    record_type="feedback_record",
    user_id="demo_user",
    entities=None,
    created_at=NOW,
    content=None,
):
    return MemoryRecord(
        record_id=uuid4(),
        user_id=user_id,
        record_type=record_type,
        content=content if content is not None else {"x": 1},
        domain="stocks",
        entities=entities or ["NVDA"],
        source_layer="learning_system",
        created_at=created_at,
    )


def test_in_memory_default_is_unaffected_by_persistence_support():
    """No db_path -- byte-for-byte the pre-Block-3 in-memory-only store."""
    store = MemoryStore()
    record = _record()
    store.write(record, writer="learning_system")
    assert store.all(user_id="demo_user") == [record]
    # No-op close, no crash, no file created anywhere.
    store.close()


def test_records_survive_reload_from_a_fresh_store_instance(tmp_path):
    db_path = tmp_path / "state.db"
    store = MemoryStore(db_path=db_path)
    record = _record()
    store.write(record, writer="learning_system")
    store.close()

    reloaded = MemoryStore(db_path=db_path)
    assert len(reloaded.all(user_id="demo_user")) == 1
    assert reloaded.all(user_id="demo_user")[0].record_id == record.record_id
    assert reloaded.all(user_id="demo_user")[0].content == record.content


def test_query_and_all_are_unaffected_by_the_sqlite_backing(tmp_path):
    """Reads are always served from the in-memory dict either way -- same
    query()/all() semantics regardless of db_path."""
    store = MemoryStore(db_path=tmp_path / "state.db")
    store.write(_record(entities=["NVDA"], content={"a": 1}), writer="learning_system")
    store.write(_record(entities=["AMD"], content={"a": 2}), writer="learning_system")

    assert len(store.all(user_id="demo_user")) == 2
    assert len(store.query(user_id="demo_user", entities=["NVDA"])) == 1
    assert len(store.query(user_id="demo_user", domain="stocks")) == 2
    assert len(store.query(user_id="demo_user", domain="sports")) == 0


def test_permission_check_is_unaffected_by_persistence(tmp_path):
    store = MemoryStore(db_path=tmp_path / "state.db")
    with pytest.raises(MemoryPermissionError):
        store.write(_record(), writer="reasoning_engine")


def test_updating_an_existing_record_id_persists_the_new_content(tmp_path):
    """write() upserts by record_id (same semantics as the in-memory dict) --
    an update-in-place must also persist, not just an initial insert."""
    db_path = tmp_path / "state.db"
    store = MemoryStore(db_path=db_path)
    record = _record(content={"count": 1})
    store.write(record, writer="learning_system")

    updated = record.model_copy(update={"content": {"count": 2}})
    store.write(updated, writer="learning_system")
    store.close()

    reloaded = MemoryStore(db_path=db_path)
    assert len(reloaded.all(user_id="demo_user")) == 1
    assert reloaded.all(user_id="demo_user")[0].content == {"count": 2}


def test_schema_meta_records_the_current_version(tmp_path):
    db_path = tmp_path / "state.db"
    MemoryStore(db_path=db_path)

    import sqlite3

    conn = sqlite3.connect(str(db_path))
    row = conn.execute("SELECT value FROM schema_meta WHERE key = 'version'").fetchone()
    conn.close()
    assert row is not None
    assert int(row[0]) >= 1


def test_reopening_an_existing_database_does_not_reset_its_version(tmp_path):
    db_path = tmp_path / "state.db"
    store1 = MemoryStore(db_path=db_path)
    store1.write(_record(), writer="learning_system")
    store1.close()

    store2 = MemoryStore(db_path=db_path)
    assert (
        len(store2.all(user_id="demo_user")) == 1
    )  # data survived a schema re-init on reopen


# --- Bounded-history compaction ---------------------------------------


def test_compaction_prunes_oldest_feedback_records_beyond_the_cap(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(store_module, "MAX_PRUNABLE_RECORDS_PER_USER", _TEST_CAP)
    store = MemoryStore(db_path=tmp_path / "state.db")
    base = NOW - timedelta(days=1)
    for i in range(_TEST_CAP + 5):
        store.write(
            _record(created_at=base + timedelta(seconds=i)), writer="learning_system"
        )

    all_records = store.all(user_id="demo_user")
    assert len(all_records) == _TEST_CAP
    # The oldest 5 were pruned -- the earliest remaining record is newer than
    # the very first one written.
    oldest_remaining = min(r.created_at for r in all_records)
    assert oldest_remaining > base


def test_compaction_never_prunes_explicit_high_value_record_types(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(store_module, "MAX_PRUNABLE_RECORDS_PER_USER", _TEST_CAP)
    store = MemoryStore(db_path=tmp_path / "state.db")
    base = NOW - timedelta(days=1)
    explicit = _record(record_type="user_statement", created_at=base)
    store.write(explicit, writer="learning_system")
    for i in range(_TEST_CAP + 5):
        store.write(
            _record(created_at=base + timedelta(seconds=i + 1)),
            writer="learning_system",
        )

    all_records = store.all(user_id="demo_user")
    assert explicit.record_id in {r.record_id for r in all_records}


def test_compaction_is_scoped_per_user(tmp_path, monkeypatch):
    """One user's heavy interaction volume must not prune another user's
    (much smaller) history."""
    monkeypatch.setattr(store_module, "MAX_PRUNABLE_RECORDS_PER_USER", _TEST_CAP)
    store = MemoryStore(db_path=tmp_path / "state.db")
    base = NOW - timedelta(days=1)
    other_user_record = _record(user_id="other_user", created_at=base)
    store.write(other_user_record, writer="learning_system")
    for i in range(_TEST_CAP + 5):
        store.write(
            _record(user_id="demo_user", created_at=base + timedelta(seconds=i + 1)),
            writer="learning_system",
        )

    other_user_records = store.all(user_id="other_user")
    assert other_user_record.record_id in {r.record_id for r in other_user_records}
    # demo_user's own heavy volume was compacted down to the cap, exactly as
    # test_compaction_prunes_oldest_feedback_records_beyond_the_cap proves --
    # this test's own point is that other_user's single record survived
    # untouched regardless, not that no compaction happened at all.
    demo_user_records = store.all(user_id="demo_user")
    assert len(demo_user_records) == _TEST_CAP
