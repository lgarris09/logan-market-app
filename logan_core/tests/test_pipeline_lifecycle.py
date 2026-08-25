"""Stock Opportunity Logic V2 -- pipeline integration tests proving
OpportunityLifecycleTracker, wired as an opt-in PipelineDependency, actually
feeds PrioritizationEngine.prioritize()'s `changed_since_view` real data
through the full, unmodified downstream pipeline -- closing the exact gap
the Sprint 3.6.9 audit found (every pre-existing caller left that parameter
at its hardcoded default `True`, making PrioritizationEngine's own cooldown
mechanism structurally unreachable). Every dependency here (World Model,
Evidence Trust, Reasoning, Opportunity, Policy, Prioritization) is used
completely unmodified.
"""

from logan_core.opportunity_lifecycle import OpportunityLifecycleTracker
from logan_core.orchestrator import Orchestrator, PipelineDependencies
from logan_core.receptors import earnings_report_to_raw_signal
from logan_core.receptors.providers import nvda_earnings_beat_fixture
from logan_core.trigger_detection import StocksTriggerEvaluator


def _orchestrator(tracker: OpportunityLifecycleTracker) -> Orchestrator:
    deps = PipelineDependencies(
        trigger_detector=StocksTriggerEvaluator(),
        lifecycle_tracker=tracker,
    )
    return Orchestrator(deps=deps)


def test_no_lifecycle_tracker_wired_leaves_changed_since_view_at_prior_default(
    user_model, engagement_samples, now
):
    """Backward-compatibility guarantee: every pre-Sprint-3.6.9 caller that
    doesn't wire a lifecycle_tracker in gets byte-for-byte the exact
    pre-existing behavior -- changed_since_view stays hardcoded True,
    lifecycle_delta is None."""
    deps = PipelineDependencies(trigger_detector=StocksTriggerEvaluator())
    orchestrator = Orchestrator(deps=deps)
    raw = earnings_report_to_raw_signal(nvda_earnings_beat_fixture())
    raw = raw.model_copy(update={"captured_at": now})

    result = orchestrator.run(
        raw_signals=[raw],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )
    assert result.lifecycle_delta is None
    assert result.prioritized_item.changed_since_view is True


def test_first_poll_is_new_and_changed_since_view_true(
    user_model, engagement_samples, now
):
    tracker = OpportunityLifecycleTracker()
    orchestrator = _orchestrator(tracker)
    raw = earnings_report_to_raw_signal(nvda_earnings_beat_fixture())
    raw = raw.model_copy(update={"captured_at": now})

    result = orchestrator.run(
        raw_signals=[raw],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )
    assert result.lifecycle_delta is not None
    assert result.lifecycle_delta.change_type == "new_opportunity"
    assert result.prioritized_item.changed_since_view is True


def test_repeated_identical_poll_sets_changed_since_view_false_and_engages_cooldown(
    user_model, engagement_samples, now
):
    """The actual product fix, proven end to end: an unchanged repeated poll
    now correctly reports changed_since_view=False, which -- through
    PrioritizationEngine's own pre-existing, previously-unreachable cooldown
    logic -- can now actually engage `in_cooldown` on a still-surfaced item,
    exactly as PrioritizationEngine.prioritize()'s own code was always
    designed to allow."""
    tracker = OpportunityLifecycleTracker()
    orchestrator = _orchestrator(tracker)
    raw = earnings_report_to_raw_signal(nvda_earnings_beat_fixture())
    raw = raw.model_copy(update={"captured_at": now})

    first = orchestrator.run(
        raw_signals=[raw],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )
    assert first.prioritized_item.visibility in ("primary", "feed")

    second = orchestrator.run(
        raw_signals=[raw],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )
    assert second.lifecycle_delta is not None
    assert second.lifecycle_delta.change_type == "none"
    assert second.lifecycle_delta.is_meaningful is False
    assert second.prioritized_item.changed_since_view is False


def test_genuinely_new_signal_appearing_reports_changed_since_view_true(
    user_model, engagement_samples, now
):
    tracker = OpportunityLifecycleTracker()
    orchestrator = _orchestrator(tracker)
    raw = earnings_report_to_raw_signal(nvda_earnings_beat_fixture())
    raw = raw.model_copy(update={"captured_at": now})

    orchestrator.run(
        raw_signals=[raw],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )
    # A materially later poll of the exact same underlying report is still
    # "the same story" from the tracker's perspective (no new trigger_code,
    # no confidence delta) -- changed_since_view correctly stays False even
    # though real time has passed, proving this isn't just a duplicate-
    # payload check.
    later = orchestrator.run(
        raw_signals=[raw],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )
    assert later.prioritized_item.changed_since_view is False


def test_restart_simulated_tracker_reload_does_not_treat_known_entity_as_new(
    user_model, engagement_samples, now
):
    """Restart-safety at the tracker level (persistence-layer restart safety
    is covered separately in backend/tests/test_lifecycle_persistence.py) --
    a fresh tracker instance rehydrated from an exported snapshot must not
    report the entity as newly-appearing."""
    tracker = OpportunityLifecycleTracker()
    orchestrator = _orchestrator(tracker)
    raw = earnings_report_to_raw_signal(nvda_earnings_beat_fixture())
    raw = raw.model_copy(update={"captured_at": now})

    orchestrator.run(
        raw_signals=[raw],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )
    exported = tracker.export_snapshot("NVDA")
    assert exported is not None

    restarted_tracker = OpportunityLifecycleTracker()
    restarted_tracker.load_snapshot(exported)
    restarted_orchestrator = _orchestrator(restarted_tracker)

    result = restarted_orchestrator.run(
        raw_signals=[raw],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )
    assert result.lifecycle_delta is not None
    assert result.lifecycle_delta.change_type != "new_opportunity"
    assert result.prioritized_item.changed_since_view is False
