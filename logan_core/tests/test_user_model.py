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


def _feedback_record(
    entity_id="TSLA",
    domain="stocks",
    inferred_intent="interested",
    intent_confidence=0.85,
):
    return MemoryRecord(
        record_id=uuid4(),
        user_id="demo_user",
        record_type="feedback_record",
        content={
            "interaction_type": "watch",
            "entity_id": entity_id,
            "domain": domain,
            "inferred_intent": inferred_intent,
            "intent_confidence": intent_confidence,
            "duration_ms": None,
        },
        domain=domain,
        entities=[entity_id],
        source_layer="learning_system",
        created_at=NOW,
    )


def test_seed_derives_domain_preferences_from_holdings_and_interests():
    builder = UserModelBuilder()
    model = builder.seed(
        user_id="demo_user",
        holdings=[
            Holding(
                domain="stocks", entity_id="NVDA", display_name="NVIDIA", added_at=NOW
            )
        ],
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


def test_build_ignores_single_isolated_evidence():
    """MIN_REPEAT_EVIDENCE=2: one interested-intent interaction is a single
    occurrence, not a pattern -- must not create a behavior, domain
    preference, or inferred interest."""
    builder = UserModelBuilder()
    base = builder.seed(user_id="demo_user")
    updated = builder.build(
        user_id="demo_user", memory_records=[_feedback_record()], base=base
    )
    assert updated.established_behaviors == []
    assert updated.domain_preferences == []
    assert updated.interests == []


def test_build_folds_repeated_interested_evidence():
    """Two independent interested-intent records for the same (domain,
    entity_id) pair -- the minimal definition of "repeated" -- must produce
    an established_behaviors entry, an active DomainPref, and an
    Interest(source="inferred"), using the max intent_confidence among the
    qualifying records verbatim (not a new/invented number)."""
    builder = UserModelBuilder()
    base = builder.seed(user_id="demo_user")
    records = [
        _feedback_record(intent_confidence=0.65),
        _feedback_record(intent_confidence=0.85),
    ]
    updated = builder.build(user_id="demo_user", memory_records=records, base=base)

    assert [b.label for b in updated.established_behaviors] == ["engaged_with_TSLA"]
    assert updated.established_behaviors[0].confidence == 0.85

    stocks_pref = next(p for p in updated.domain_preferences if p.domain == "stocks")
    assert stocks_pref.active is True
    assert stocks_pref.weight == 0.5  # existing seed()-default neutral weight

    inferred = [i for i in updated.interests if i.source == "inferred"]
    assert len(inferred) == 1
    assert inferred[0].topic == "TSLA"
    assert inferred[0].weight == 0.85


def test_build_requires_interested_intent_specifically():
    """Repeated evidence with an inferred_intent other than "interested"
    (e.g. "curious" from a plain click) must not qualify -- only the
    strongest positive signal FeedbackEngine produces counts."""
    builder = UserModelBuilder()
    base = builder.seed(user_id="demo_user")
    records = [
        _feedback_record(inferred_intent="curious", intent_confidence=0.55),
        _feedback_record(inferred_intent="curious", intent_confidence=0.55),
    ]
    updated = builder.build(user_id="demo_user", memory_records=records, base=base)
    assert updated.established_behaviors == []
    assert updated.interests == []


def test_build_does_not_leak_evidence_across_entities_or_domains():
    """Evidence is grouped by (domain, entity_id) -- one entity/domain pair
    reaching MIN_REPEAT_EVIDENCE must not create a pattern for a different
    entity or domain, even with the same total record count."""
    builder = UserModelBuilder()
    base = builder.seed(user_id="demo_user")
    records = [
        _feedback_record(entity_id="TSLA", domain="stocks"),
        _feedback_record(entity_id="NVDA", domain="stocks"),
        _feedback_record(entity_id="BTC", domain="crypto"),
    ]
    updated = builder.build(user_id="demo_user", memory_records=records, base=base)
    assert updated.established_behaviors == []
    assert updated.interests == []


def test_build_preserves_explicit_holdings_and_interests():
    """Explicit holdings/interests are the stronger source of truth -- an
    entity already explicitly known never gets a competing inferred
    Interest, and existing explicit data is copied through unchanged."""
    builder = UserModelBuilder()
    base = builder.seed(
        user_id="demo_user",
        holdings=[
            Holding(
                domain="stocks", entity_id="TSLA", display_name="Tesla", added_at=NOW
            )
        ],
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
    records = [
        _feedback_record(entity_id="TSLA"),  # already an explicit holding
        _feedback_record(entity_id="TSLA"),
        _feedback_record(entity_id="NVDA"),  # already an explicit interest
        _feedback_record(entity_id="NVDA"),
    ]
    updated = builder.build(user_id="demo_user", memory_records=records, base=base)

    assert updated.holdings == base.holdings
    explicit = [i for i in updated.interests if i.source == "explicit"]
    assert explicit == base.interests
    # Behaviors still record the repeated engagement even for explicitly-
    # known entities; only the *interest* write is suppressed.
    assert {b.label for b in updated.established_behaviors} == {
        "engaged_with_TSLA",
        "engaged_with_NVDA",
    }
    assert [i for i in updated.interests if i.source == "inferred"] == []


def test_build_never_touches_inferred_expertise():
    """View/click/dwell evidence demonstrates attention, not expertise --
    inferred_expertise must be copied through from base unchanged."""
    builder = UserModelBuilder()
    base = builder.seed(user_id="demo_user")
    records = [_feedback_record(), _feedback_record()]
    updated = builder.build(user_id="demo_user", memory_records=records, base=base)
    assert updated.inferred_expertise == base.inferred_expertise == []
