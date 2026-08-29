"""V2.3B Personal Learning Phase 1 -- build_learning_report(). Pure,
read-only tests: no orchestrator, no HTTP -- MemoryRecord[] + UserModel ->
LearningReport, exactly mirroring the same UserModelBuilder.build() output
the real pipeline already produces."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from logan_core.contracts import Interest, MemoryRecord
from logan_core.learning import build_learning_report
from logan_core.user_model import UserModelBuilder

NOW = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)


def _feedback(
    entity_id="NVDA", interaction_type="save", confidence=0.85, created_at=NOW
):
    return MemoryRecord(
        record_id=uuid4(),
        user_id="demo_user",
        record_type="feedback_record",
        content={
            "interaction_type": interaction_type,
            "entity_id": entity_id,
            "domain": "stocks",
            "inferred_intent": "interested" if confidence >= 0.5 else "unknown",
            "intent_confidence": confidence,
            "duration_ms": None,
        },
        domain="stocks",
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


def test_observed_section_summarizes_real_interaction_counts():
    records = [
        _feedback(entity_id="NVDA", interaction_type="view", created_at=NOW),
        _feedback(
            entity_id="NVDA",
            interaction_type="view",
            created_at=NOW + timedelta(hours=1),
        ),
        _feedback(entity_id="NVDA", interaction_type="ask_followup", created_at=NOW),
    ]
    user_model = UserModelBuilder().build("demo_user", records, _seed(), now=NOW)
    report = build_learning_report("demo_user", user_model, records, now=NOW)

    descriptions = [o.description for o in report.observed]
    assert "Opened NVDA 2 times" in descriptions
    assert "Asked a follow-up question about NVDA 1 time" in descriptions


def test_learned_section_reports_a_qualifying_inferred_interest():
    records = [
        _feedback(created_at=NOW),
        _feedback(created_at=NOW + timedelta(days=1)),
    ]
    user_model = UserModelBuilder().build(
        "demo_user", records, _seed(), now=NOW + timedelta(days=2)
    )
    report = build_learning_report(
        "demo_user", user_model, records, now=NOW + timedelta(days=2)
    )

    nvda = next(
        t for t in report.learned if t.entity_id == "NVDA" and t.kind == "interest"
    )
    assert nvda.source == "inferred"
    assert nvda.evidence_count == 2
    assert "2 qualifying engagement" in nvda.why
    assert "fades" in nvda.what_would_change_this.lower()


def test_learned_section_labels_explicit_interest_correctly():
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
    user_model = UserModelBuilder().build("demo_user", [], seed, now=NOW)
    report = build_learning_report("demo_user", user_model, [], now=NOW)

    nvda = next(t for t in report.learned if t.entity_id == "NVDA")
    assert nvda.source == "explicit"
    assert "explicitly declared" in nvda.why.lower()
    assert "does not decay" in nvda.what_would_change_this.lower()


def test_not_learned_reports_insufficient_evidence_with_real_count():
    records = [_feedback(created_at=NOW)]  # only one -- below MIN_REPEAT_EVIDENCE
    user_model = UserModelBuilder().build("demo_user", records, _seed(), now=NOW)
    report = build_learning_report("demo_user", user_model, records, now=NOW)

    assert not any(t.entity_id == "NVDA" for t in report.learned)
    nvda = next(t for t in report.not_learned if t.candidate == "NVDA")
    assert "Only 1 qualifying observation" in nvda.reason


def test_not_learned_reports_a_real_suppression_with_its_date():
    records = [
        _feedback(created_at=NOW),
        _feedback(created_at=NOW + timedelta(days=1)),
        _correction(created_at=NOW + timedelta(days=2)),
    ]
    user_model = UserModelBuilder().build(
        "demo_user", records, _seed(), now=NOW + timedelta(days=3)
    )
    report = build_learning_report(
        "demo_user", user_model, records, now=NOW + timedelta(days=3)
    )

    assert not any(t.entity_id == "NVDA" for t in report.learned)
    nvda = next(t for t in report.not_learned if t.candidate == "NVDA")
    assert "Suppressed by an explicit correction" in nvda.reason
    assert (NOW + timedelta(days=2)).date().isoformat() in nvda.reason


def test_report_states_the_min_repeat_evidence_rule_honestly():
    user_model = UserModelBuilder().build("demo_user", [], _seed(), now=NOW)
    report = build_learning_report("demo_user", user_model, [], now=NOW)
    assert any(
        "does not generalize" in n or "does not yet generalize" in n
        for n in report.architecture_notes
    )


def test_report_never_reports_holdings_as_a_learned_trait():
    """Holdings are a stated fact, not something STRATUS concluded from
    behavior -- this report is about Learning's own inferred output."""
    from logan_core.contracts import Holding

    seed = UserModelBuilder().seed(
        "demo_user",
        holdings=[
            Holding(
                domain="stocks", entity_id="TSLA", display_name="Tesla", added_at=NOW
            )
        ],
    )
    user_model = UserModelBuilder().build("demo_user", [], seed, now=NOW)
    report = build_learning_report("demo_user", user_model, [], now=NOW)
    assert not any(t.entity_id == "TSLA" for t in report.learned)


def test_report_model_confidence_matches_the_real_user_model():
    user_model = UserModelBuilder().build("demo_user", [], _seed(), now=NOW)
    report = build_learning_report("demo_user", user_model, [], now=NOW)
    assert report.model_confidence == user_model.model_confidence
