import sys
from pathlib import Path

import pytest

# backend/app's own modules do this too (see logan_demo.py, ADR-022) -- repeated
# here so the test suite doesn't depend on import order pulling one of them in
# first.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


@pytest.fixture(autouse=True)
def _reset_logan_feed_pipeline_state():
    """`backend/app/logan_feed.py` now keeps a process-lifetime Orchestrator
    (the fix for event_ids randomizing on every request -- see the owner
    conversation this shipped from) instead of a fresh one per call. Without
    this, tests that call into the pipeline would see state (World Model
    dedup, Prioritization AttentionState/notifications_reviewed) leak across
    test functions and even test files, depending on execution order. Reset
    before every test, not just the ones that obviously touch the pipeline --
    cheap, and removes an entire class of order-dependent flakiness.

    Sprint 3.6.9 Remote STRATUS closeout: also resets logan_core's shared
    FmpEarningsProvider/FmpMarketDataProvider TTL cache (see
    receptors/providers/fmp.py's FmpResponseCache) -- that cache is a
    process-lifetime module singleton, so without this reset, one test's
    live-FMP-path result (real or mocked) could silently leak into another
    test's expectations for the same ticker, in this file's suite or
    logan_core's, whichever ran first in this process.
    """
    from backend.app.logan_feed import reset_pipeline_state
    from backend.app.notifications import reset_notification_state
    from backend.app.rate_limit import reset_rate_limits
    from logan_core.receptors.providers.fmp import reset_fmp_cache

    reset_pipeline_state()
    reset_notification_state()
    reset_fmp_cache()
    reset_rate_limits()
    yield
    reset_pipeline_state()
    reset_notification_state()
    reset_fmp_cache()
    reset_rate_limits()
