"""Layer 6b direct unit tests (V3.1.4 BATCH-2 -- previously uncovered).
Includes the ADR-033-style user_id isolation requirement added this batch.
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from logan_core.active_context import ActiveContextBuilder


def test_build_requires_user_id():
    builder = ActiveContextBuilder()
    context = builder.build(user_id="demo_user")
    assert context.user_id == "demo_user"


def test_build_rejects_empty_user_id():
    builder = ActiveContextBuilder()
    with pytest.raises(ValidationError):
        builder.build(user_id="")


def test_time_of_day_buckets():
    builder = ActiveContextBuilder()
    morning = builder.build(user_id="demo_user", now=datetime(2026, 8, 5, 7, 0, tzinfo=timezone.utc))
    night = builder.build(user_id="demo_user", now=datetime(2026, 8, 5, 23, 0, tzinfo=timezone.utc))
    assert morning.time_of_day == "morning"
    assert night.time_of_day == "night"


def test_session_expires_after_ttl():
    now = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
    builder = ActiveContextBuilder()
    context = builder.build(user_id="demo_user", now=now)
    assert context.expires_at > context.created_at


def test_current_question_and_recent_activity_carried_through():
    from logan_core.contracts import ActivityRecord

    now = datetime.now(timezone.utc)
    activity = [ActivityRecord(activity_type="view", detail="viewed NVDA", occurred_at=now)]
    builder = ActiveContextBuilder()
    context = builder.build(user_id="demo_user", current_question="what about NVDA?", recent_activity=activity)
    assert context.current_question == "what about NVDA?"
    assert context.recent_activity == activity
