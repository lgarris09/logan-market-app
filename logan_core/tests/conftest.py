from datetime import datetime, timezone

import pytest

from logan_core.community_intelligence import EngagementSample
from logan_core.contracts import Holding
from logan_core.orchestrator import Orchestrator
from logan_core.receptors.providers.fmp import reset_fmp_cache
from logan_core.user_model import UserModelBuilder


@pytest.fixture(autouse=True)
def _reset_fmp_cache():
    """Sprint 3.6.9 Remote STRATUS closeout: FmpEarningsProvider/
    FmpMarketDataProvider now share one process-lifetime TTL cache by
    default (see receptors/providers/fmp.py's FmpResponseCache) -- without
    this, two different test functions both fetching "NVDA" through
    different mock clients would have the second one silently receive the
    first one's cached result instead of exercising its own mock. Mirrors
    this codebase's existing reset_pipeline_state()/reset_notification_state()
    convention for process-lifetime state.
    """
    reset_fmp_cache()
    yield
    reset_fmp_cache()


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
