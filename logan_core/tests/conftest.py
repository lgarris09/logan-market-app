from datetime import datetime, timezone

import pytest

from logan_core.community_intelligence import EngagementSample
from logan_core.contracts import Holding
from logan_core.orchestrator import Orchestrator
from logan_core.user_model import UserModelBuilder


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 7, 30, 15, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def user_model(now):
    return UserModelBuilder().seed(
        user_id="demo_user",
        holdings=[
            Holding(
                domain="stocks", entity_id="NVDA", display_name="NVIDIA", added_at=now
            )
        ],
        risk_tolerance="moderate",
    )


@pytest.fixture
def engagement_samples(now):
    return [
        EngagementSample(
            observed_at=now,
            volume_at_point=10,
            unique_users=8,
            saves_shares=1,
            questions=0,
        ),
        EngagementSample(
            observed_at=now,
            volume_at_point=40,
            unique_users=30,
            saves_shares=6,
            questions=3,
        ),
    ]


@pytest.fixture
def orchestrator():
    return Orchestrator()
