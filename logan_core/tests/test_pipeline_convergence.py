"""Sprint 3.6.7 Block 2 -- pipeline integration tests proving multiple
distinct-signal_type raw_signals for one entity (earnings + price move +
analyst grade) become one coherent opportunity, and that
STOCK_CONVERGENCE_MULTI_SOURCE fires through the full, unmodified downstream
pipeline (Evidence Trust, Reasoning, Opportunity, Policy, Prioritization,
Presentation) when the registered ≥3-distinct-source condition is met.

World Model's own `(entity_id, signal_type)` dedup/corroboration semantics
(world_model/model.py) are exercised here but never modified -- see
_merge_entity_events's docstring in orchestrator/pipeline.py for how the
coherent-opportunity fix sits one layer above World Model instead.
"""

from datetime import timedelta

from logan_core.convergence import (
    STOCK_CONVERGENCE_MULTI_SOURCE,
    StockConvergenceTracker,
)
from logan_core.orchestrator import Orchestrator, PipelineDependencies
from logan_core.receptors import (
    earnings_report_to_raw_signal,
    grade_change_to_raw_signal,
    quote_to_raw_signal,
)
from logan_core.receptors.providers import (
    FixtureMarketDataProvider,
    nvda_analyst_upgrade_fixture,
    nvda_earnings_beat_fixture,
    nvda_price_move_up_fixture,
)
from logan_core.trigger_detection import StocksTriggerEvaluator
from logan_core.trigger_detection.stocks import (
    STOCK_ANALYST_UPGRADE,
    STOCK_EARNINGS_BEAT,
    STOCK_PRICE_MOVE_SIGNIFICANT,
)


def _three_signal_raw_signals(now):
    """All three fixtures re-timestamped close together (`captured_at`,
    i.e. `event_timestamp` -- see below). Not what makes convergence fire:
    StockConvergenceTracker windows on `detected_timestamp` (real
    evaluation-time "now" -- see tracker.py's own comment on why), which
    naturally clusters within milliseconds for signals evaluated in the same
    test call regardless of `captured_at`. Re-timestamped anyway for realism
    elsewhere in the pipeline (World Model recency, EvidenceTrust decay) --
    the fixtures' own default timestamps (receptors/providers/fixture.py)
    span unrelated real calendar dates that would otherwise look like three
    signals about the same entity from wildly different points in time.
    """
    earnings = earnings_report_to_raw_signal(nvda_earnings_beat_fixture())
    earnings = earnings.model_copy(update={"captured_at": now})

    quote_provider = FixtureMarketDataProvider(
        quotes={"NVDA": nvda_price_move_up_fixture()},
        grade_changes={"NVDA": nvda_analyst_upgrade_fixture()},
    )
    quote = quote_provider.fetch_quote("NVDA")
    assert quote is not None
    price = quote_to_raw_signal(quote)
    price = price.model_copy(update={"captured_at": now + timedelta(minutes=5)})

    grade_change = quote_provider.fetch_latest_grade_change("NVDA")
    assert grade_change is not None
    grade = grade_change_to_raw_signal(grade_change)
    grade = grade.model_copy(update={"captured_at": now + timedelta(minutes=10)})

    return [earnings, price, grade]


def _orchestrator() -> Orchestrator:
    deps = PipelineDependencies(
        trigger_detector=StocksTriggerEvaluator(),
        convergence_tracker=StockConvergenceTracker(),
    )
    return Orchestrator(deps=deps)


# --- Coherent-opportunity merge (independent of whether convergence fires) --


def test_multiple_signal_types_in_one_call_merge_into_one_event(
    user_model, engagement_samples, now
):
    """The ADR-051-finding-5 regression: three raw_signals of three different
    signal_types for NVDA in one run() call must produce ONE EnrichedEvent
    carrying all three underlying triggers -- not just the last-processed
    signal_type's own event with the other two silently dropped."""
    orchestrator = _orchestrator()
    raw_signals = _three_signal_raw_signals(now)

    result = orchestrator.run(
        raw_signals=raw_signals,
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )

    trigger_codes = {t.trigger_code for t in result.event.trigger_events}
    assert {
        STOCK_EARNINGS_BEAT,
        STOCK_PRICE_MOVE_SIGNIFICANT,
        STOCK_ANALYST_UPGRADE,
    } <= (trigger_codes)
    # Provenance: every contributing signal's id is still visible.
    assert len(result.event.signal_ids) == 3
    assert set(result.event.signal_ids) == {
        n.signal_id for n in result.normalized_signals
    }
    # Still one entity (NVDA), not three separate entity records.
    assert [e.entity_id for e in result.event.entities] == ["NVDA"]


def test_single_signal_type_call_does_not_fire_convergence(
    user_model, engagement_samples, now
):
    """No-op guarantee: exactly one raw_signal (the overwhelmingly common
    case) never has enough distinct signal_types to converge, even with a
    convergence_tracker wired in -- the merge helper is a no-op when there's
    only one distinct event, and the tracker still runs (visible in the
    trace) but produces nothing."""
    orchestrator = _orchestrator()
    raw = earnings_report_to_raw_signal(nvda_earnings_beat_fixture())

    result = orchestrator.run(
        raw_signals=[raw],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )

    assert len(result.event.trigger_events) == 1
    assert result.event.trigger_events[0].trigger_code == STOCK_EARNINGS_BEAT
    assert "convergence_tracker" in [m.layer for m in result.trace.layers]


def test_without_convergence_tracker_wired_behaves_exactly_as_before_block_2(
    user_model, engagement_samples, now
):
    """True backward-compatibility guarantee, mirroring the earnings/market-
    data suites' own: a caller that wires trigger_detector but not
    convergence_tracker (every pre-Block-2 caller, and every Block 1 test)
    must not gain a "convergence_tracker" trace layer or any
    STOCK_CONVERGENCE_MULTI_SOURCE trigger, and a single raw_signal's
    resulting event must be exactly what World Model produced."""
    deps = PipelineDependencies(trigger_detector=StocksTriggerEvaluator())
    orchestrator = Orchestrator(deps=deps)
    raw = earnings_report_to_raw_signal(nvda_earnings_beat_fixture())

    result = orchestrator.run(
        raw_signals=[raw],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )

    assert len(result.event.trigger_events) == 1
    assert result.event.trigger_events[0].trigger_code == STOCK_EARNINGS_BEAT
    assert "convergence_tracker" not in [m.layer for m in result.trace.layers]


# --- STOCK_CONVERGENCE_MULTI_SOURCE firing end-to-end -----------------------


def test_three_distinct_signals_fire_convergence_end_to_end(
    user_model, engagement_samples, now
):
    orchestrator = _orchestrator()
    raw_signals = _three_signal_raw_signals(now)

    result = orchestrator.run(
        raw_signals=raw_signals,
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )

    convergence_triggers = [
        t
        for t in result.event.trigger_events
        if t.trigger_code == STOCK_CONVERGENCE_MULTI_SOURCE
    ]
    assert len(convergence_triggers) == 1
    convergence = convergence_triggers[0]
    assert convergence.context["source_count"] == 3
    assert set(convergence.context["sources"]) == {
        "earnings_signal",
        "price_change",
        "analyst_change",
    }

    # Convergence enriches the opportunity -- it doesn't replace the
    # individual signals that produced it. The strongest underlying trigger
    # (STOCK_EARNINGS_BEAT, +0.22) still drives the bonus over convergence's
    # own +0.20, matching ConvergenceDetector's existing "strongest, not
    # summed" rule (convergence/detector.py) -- unmodified by this sprint.
    assert result.trust.trigger_confidence_bonus == 0.22
    assert result.delivered_item.headline
    assert result.trace.status == "complete"


def test_only_two_distinct_signals_does_not_fire_convergence(
    user_model, engagement_samples, now
):
    orchestrator = _orchestrator()
    raw_signals = _three_signal_raw_signals(now)[:2]  # earnings + price only

    result = orchestrator.run(
        raw_signals=raw_signals,
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )

    trigger_codes = {t.trigger_code for t in result.event.trigger_events}
    assert STOCK_CONVERGENCE_MULTI_SOURCE not in trigger_codes


# Window-boundary behavior (a signal aging out of the 30-minute window,
# relative to `detected_timestamp`) is covered directly and controllably at
# the tracker unit level -- see test_convergence_tracker.py's
# test_signal_outside_window_does_not_count_toward_convergence and
# test_episode_lapses_and_can_reform_after_window_expires. Not re-tested
# here: detected_timestamp is real wall-clock "now" at trigger-evaluation
# time (trigger_detection/stocks.py), not something a pipeline-level test can
# control without monkeypatching datetime.now() inside that module.


# --- Repeated-episode suppression across separate poll-like run() calls ----


def test_repeated_polls_of_an_active_episode_do_not_mint_new_alerts(
    user_model, engagement_samples, now
):
    """Simulates two successive /v1/opportunities-style polls sharing one
    persistent Orchestrator (as backend/app/logan_feed.py's process-lifetime
    instance does) -- the second poll re-observing the same already-converged
    signal types must describe the same episode, not fire a second, distinct
    STOCK_CONVERGENCE_MULTI_SOURCE trigger_id."""
    orchestrator = _orchestrator()
    raw_signals = _three_signal_raw_signals(now)

    first_result = orchestrator.run(
        raw_signals=raw_signals,
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )
    first_convergence = next(
        t
        for t in first_result.event.trigger_events
        if t.trigger_code == STOCK_CONVERGENCE_MULTI_SOURCE
    )

    # Re-poll: the same price quote, checked again a minute later (a
    # duplicate observation of a still-active price move) -- World Model's
    # own duplicate-observation handling (world_model/model.py) already
    # prevents this from inflating corroboration; convergence must likewise
    # not treat it as a fresh episode.
    _, price_raw, _ = raw_signals
    repeated_price = price_raw.model_copy(
        update={"captured_at": price_raw.captured_at + timedelta(minutes=1)}
    )

    second_result = orchestrator.run(
        raw_signals=[repeated_price],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )
    second_convergence = next(
        t
        for t in second_result.event.trigger_events
        if t.trigger_code == STOCK_CONVERGENCE_MULTI_SOURCE
    )
    assert second_convergence.trigger_id == first_convergence.trigger_id
