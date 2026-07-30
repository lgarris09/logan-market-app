from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from logan_core.contracts import DeliveredItem, FeedbackSignal, PolicyResult


def test_policy_result_requires_suppressed_when_not_permitted():
    with pytest.raises(ValidationError):
        PolicyResult(
            event_id=uuid4(),
            permitted=False,
            communication_mode="analysis",
            evaluated_at=datetime.now(timezone.utc),
        )


def test_policy_result_allows_suppressed_when_not_permitted():
    result = PolicyResult(
        event_id=uuid4(),
        permitted=False,
        communication_mode="suppressed",
        evaluated_at=datetime.now(timezone.utc),
    )
    assert result.communication_mode == "suppressed"


def test_feedback_signal_low_confidence_must_be_unknown():
    with pytest.raises(ValidationError):
        FeedbackSignal(
            event_id=uuid4(),
            interaction_type="view",
            inferred_intent="interested",
            intent_confidence=0.2,
            raw_interaction="view",
            observed_at=datetime.now(timezone.utc),
        )


def test_feedback_signal_low_confidence_unknown_is_valid():
    signal = FeedbackSignal(
        event_id=uuid4(),
        interaction_type="view",
        inferred_intent="unknown",
        intent_confidence=0.2,
        raw_interaction="view",
        observed_at=datetime.now(timezone.utc),
    )
    assert signal.inferred_intent == "unknown"


def test_delivered_item_rejects_long_headline():
    with pytest.raises(ValidationError):
        DeliveredItem(
            event_id=uuid4(),
            surface="feed_card",
            headline="x" * 121,
            what_happened="a",
            why_it_matters="a",
            why_it_matters_to_me="a",
            why_now="a",
            confidence_label="High",
            confidence_score=0.9,
            delivered_at=datetime.now(timezone.utc),
        )


def test_schema_version_defaults_present():
    signal = FeedbackSignal(
        event_id=uuid4(),
        interaction_type="save",
        inferred_intent="interested",
        intent_confidence=0.9,
        raw_interaction="save",
        observed_at=datetime.now(timezone.utc),
    )
    assert signal.schema_version == "1.0"
