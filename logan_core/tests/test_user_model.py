"""Layer 6a direct unit tests (V3.1.4 BATCH-2 -- previously uncovered)."""

from datetime import datetime, timezone
from uuid import uuid4

from logan_core.contracts import Holding, Interest, MemoryRecord
from logan_core.user_model import UserModelBuilder

NOW = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)


def _preference_record():
    return MemoryRecord(
        record_id=uuid4(),
        user_id="demo_user",
        record_type="preference_signal",
        content="likes AI stocks",
        source_layer="learning_system",
        created_at=NOW,
    )


def test_seed_derives_domain_preferences_from_holdings_and_interests():
    builder = UserModelBuilder()
    model = builder.seed(
        user_id="demo_user",
        holdings=[Holding(domain="stocks", entity_id="NVDA", display_name="NVIDIA", added_at=NOW)],
        interests=[
            Interest(domain="social", topic="AI_SECTOR", weight=0.8, source="explicit", created_at=NOW, last_updated=NOW)
        ],
    )
    domains = {p.domain for p in model.domain_preferences}
    assert domains == {"stocks", "social"}
    assert model.version == 1
    assert model.model_confidence == 0.5


def test_seed_with_no_holdings_or_interests():
    builder = UserModelBuilder()
    model = builder.seed(user_id="demo_user")
    assert model.holdings == []
    assert model.interests == []
    assert model.domain_preferences == []


def test_build_increases_confidence_with_evidence():
    builder = UserModelBuilder()
    base = builder.seed(user_id="demo_user")
    records = [_preference_record() for _ in range(3)]
    updated = builder.build(user_id="demo_user", memory_records=records, base=base)
    assert updated.model_confidence > base.model_confidence
    assert updated.version == base.version + 1


def test_build_ignores_unrelated_record_types():
    builder = UserModelBuilder()
    base = builder.seed(user_id="demo_user")
    records = [
        MemoryRecord(
            record_id=uuid4(),
            user_id="demo_user",
            record_type="correction_record",
            content="not preference evidence",
            source_layer="learning_system",
            created_at=NOW,
        )
    ]
    updated = builder.build(user_id="demo_user", memory_records=records, base=base)
    assert updated.model_confidence == base.model_confidence
