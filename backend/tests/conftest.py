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
    """
    from backend.app.logan_feed import reset_pipeline_state
    from backend.app.notifications import reset_notification_state

    reset_pipeline_state()
    reset_notification_state()
    yield
    reset_pipeline_state()
    reset_notification_state()
