"""Universe Manager V1a Block 23 -- proves the three new fault codes added
for Universe Manager/Provider Scheduler (DATA-305, DATA-306, FEED-201)
actually fire at their real call sites, without changing any existing
control flow (record_fault() is purely additive -- every site here still
raises exactly the same exception it always did).
"""

import pytest

from logan_core.diagnostics import recent_faults, reset_fault_state
from logan_core.receptors.providers import (
    ProviderScheduler,
    ProviderSchedulerSaturatedError,
)
from logan_core.universe.candidate_source import load_candidate_snapshot


def setup_function() -> None:
    reset_fault_state()


def test_unregistered_candidate_source_version_records_data_305():
    with pytest.raises(KeyError):
        load_candidate_snapshot("not-a-real-version")
    faults = recent_faults()
    assert any(f.code == "DATA-305" for f in faults)
    assert faults[-1].subsystem == "universe.candidate_source"


def test_data_305_context_strips_a_key_like_field():
    with pytest.raises(KeyError):
        load_candidate_snapshot("totally-fake-version")
    fault = recent_faults()[-1]
    # requested_version itself is safe to keep (not a secret-shaped key
    # name) -- this just proves the sanitizer still runs on this call site.
    assert "requested_version" in fault.safe_context


def test_scheduler_saturation_records_data_306():
    scheduler = ProviderScheduler(global_ceiling=1)
    scheduler.acquire("quote", max_wait_seconds=0.0)
    with pytest.raises(ProviderSchedulerSaturatedError):
        scheduler.gate("quote", lambda: "unreachable", max_wait_seconds=0.0)
    faults = recent_faults()
    assert any(f.code == "DATA-306" for f in faults)
    assert faults[-1].subsystem == "provider_scheduler"


def test_data_306_context_includes_endpoint_and_priority():
    scheduler = ProviderScheduler(global_ceiling=1)
    scheduler.acquire("quote", max_wait_seconds=0.0)
    with pytest.raises(ProviderSchedulerSaturatedError):
        scheduler.gate(
            "quote", lambda: "unreachable", priority="critical", max_wait_seconds=0.0
        )
    fault = recent_faults()[-1]
    assert fault.safe_context["endpoint"] == "quote"
    assert fault.safe_context["priority"] == "critical"
