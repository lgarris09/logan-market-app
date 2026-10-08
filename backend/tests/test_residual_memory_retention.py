"""Residual memory growth correction (ADR-074) -- proves, through the real
feed pipeline and its process-lifetime Orchestrator, that the two
structures that kept growing after v31 (in-memory Operational History and
MentalModel history lists) are now bounded, and that bounding them changes
nothing the pipeline outputs or persists.
"""

import gc

import pytest

import backend.app.logan_feed as feed
import logan_core.mental_model.engine as mental_model_engine
import logan_core.orchestrator.history as history_module
from backend.app.config import universe_daily_telemetry_db_path
from backend.app.universe_telemetry import (
    daily_telemetry_range,
    reset_universe_telemetry_state,
)
from logan_core.mental_model.engine import MAX_RECENT_HYPOTHESIS_HISTORY
from logan_core.orchestrator.history import OPERATIONAL_HISTORY_MAX_ENTRIES

USER = "demo_user"


def _retained() -> dict:
    deps = feed._get_orchestrator().deps
    hypotheses = deps.mental_model_engine._hypotheses
    return {
        "history_entries": len(deps.operational_history),
        "history_refs": len(deps.operational_history._by_ref),
        "hypotheses": len(hypotheses),
        "longest_trace": max(len(m.decision_trace) for m in hypotheses.values()),
        "longest_evidence": max(
            max(len(m.supporting), len(m.opposing)) for m in hypotheses.values()
        ),
    }


def _semantics(items) -> list[tuple]:
    """Everything a user could see change about an opportunity. The raw
    confidence float is rounded: it carries a pre-existing ~1e-7 wall-clock
    recency drift between any two polls, on any code."""
    return [
        (
            item.entity_id,
            item.rank,
            item.signal_type,
            item.confidence_label,
            round(item.confidence_score, 4),
            item.lifecycle_state,
            item.opportunity_revision,
            item.meaningful_change_type,
            item.trajectory,
            item.delivered_item.headline,
            item.delivered_item.why_now,
        )
        for item in items
    ]


def _run(polls: int) -> list[list[tuple]]:
    return [_semantics(feed._run_feed_pipeline(USER)[0]) for _ in range(polls)]


def test_operational_history_stays_bounded_through_the_real_pipeline():
    polls_to_fill = 0
    while len(feed._get_orchestrator().deps.operational_history) < (
        OPERATIONAL_HISTORY_MAX_ENTRIES
    ):
        feed._run_feed_pipeline(USER)
        polls_to_fill += 1
        assert polls_to_fill < 2_000, "history never reached its bound"

    at_bound = _retained()
    for _ in range(polls_to_fill):  # as many polls again, all past the bound
        feed._run_feed_pipeline(USER)
    later = _retained()

    assert at_bound["history_entries"] == OPERATIONAL_HISTORY_MAX_ENTRIES
    assert later["history_entries"] == OPERATIONAL_HISTORY_MAX_ENTRIES
    assert later["history_refs"] <= OPERATIONAL_HISTORY_MAX_ENTRIES


def test_mental_model_history_stays_bounded_through_the_real_pipeline():
    for _ in range(MAX_RECENT_HYPOTHESIS_HISTORY * 3):
        feed._run_feed_pipeline(USER)
    retained = _retained()
    assert retained["longest_trace"] == MAX_RECENT_HYPOTHESIS_HISTORY
    assert retained["longest_evidence"] <= MAX_RECENT_HYPOTHESIS_HISTORY
    hypotheses_before = retained["hypotheses"]
    for _ in range(MAX_RECENT_HYPOTHESIS_HISTORY):
        feed._run_feed_pipeline(USER)
    assert _retained()["hypotheses"] == hypotheses_before
    assert _retained()["longest_trace"] == MAX_RECENT_HYPOTHESIS_HISTORY


def test_repeated_identical_polls_reach_a_steady_retained_state():
    """Once every bound is reached, more polls retain nothing more."""
    for _ in range(250):
        feed._run_feed_pipeline(USER)
    gc.collect()
    first = _retained()
    for _ in range(250):
        feed._run_feed_pipeline(USER)
    gc.collect()
    assert _retained() == first


def test_recent_history_is_still_available_for_diagnostics():
    for _ in range(200):
        items, _now, _alerts, _degraded = feed._run_feed_pipeline(USER)
    history = feed._get_orchestrator().deps.operational_history
    # The poll that just ran is fully inspectable: every delivered event,
    # by reference, with its payload.
    for item in items:
        entry = history.get(item.event_id)
        assert entry is not None
        assert entry.kind == "enriched_event"
        assert entry.payload.event_id == item.event_id  # type: ignore[attr-defined]
    assert history.by_kind("normalized_signal")
    assert history.by_kind("enriched_event")


def test_opportunity_output_is_identical_with_and_without_the_bounds(monkeypatch):
    """The same poll sequence, run once with the real bounds (which are
    reached and exceeded) and once with bounds too large to ever apply,
    produces the same opportunities, ranks, labels, lifecycle states and
    revisions at every poll."""
    polls = 140  # past both bounds: 50 hypothesis updates, 2,000 history entries

    bounded = _run(polls)
    assert _retained()["history_entries"] == OPERATIONAL_HISTORY_MAX_ENTRIES
    assert _retained()["longest_trace"] == MAX_RECENT_HYPOTHESIS_HISTORY

    feed.reset_pipeline_state()
    monkeypatch.setattr(history_module, "OPERATIONAL_HISTORY_MAX_ENTRIES", 10**9)
    monkeypatch.setattr(
        history_module.OperationalHistoryStore.__init__,
        "__defaults__",
        (10**9,),
    )
    monkeypatch.setattr(mental_model_engine, "MAX_RECENT_HYPOTHESIS_HISTORY", 10**9)
    unbounded = _run(polls)
    assert _retained()["history_entries"] > OPERATIONAL_HISTORY_MAX_ENTRIES
    assert _retained()["longest_trace"] > MAX_RECENT_HYPOTHESIS_HISTORY

    assert bounded == unbounded


def test_lifecycle_and_revision_behavior_is_unchanged_by_long_polling():
    """Polling an unchanged world past every bound must not manufacture a
    lifecycle change or a new revision."""
    runs = _run(160)
    settled = runs[5]
    for later in runs[6:]:
        assert [(row[0], row[5], row[6], row[7]) for row in later] == [
            (row[0], row[5], row[6], row[7]) for row in settled
        ]


@pytest.fixture
def _isolated_persistence(monkeypatch, tmp_path):
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv("STRATUS_STATE_DB_PATH", str(tmp_path / "stratus_state.db"))
    monkeypatch.setenv(
        "STRATUS_LEGACY_MEMORY_DB_PATH", str(tmp_path / "logan_memory.db")
    )
    feed.reset_pipeline_state()
    reset_universe_telemetry_state()
    yield tmp_path
    feed.reset_pipeline_state()
    reset_universe_telemetry_state()


def test_durable_telemetry_is_unaffected_by_the_in_memory_bounds(_isolated_persistence):
    """The bounds apply to two in-memory structures only. Every poll is
    still recorded in the durable daily telemetry, including the polls
    whose in-memory history has since expired."""
    polls = 130  # more than the in-memory history holds
    for _ in range(polls):
        _items, now, _alerts, _degraded = feed._run_feed_pipeline(USER)
    assert _retained()["history_entries"] == OPERATIONAL_HISTORY_MAX_ENTRIES

    assert universe_daily_telemetry_db_path().parent == _isolated_persistence
    rows = daily_telemetry_range(now.date(), now.date())
    assert sum(row.observation_count for row in rows) == polls
    assert all(row.distinct_thesis_keys for row in rows)
