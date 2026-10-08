from datetime import timedelta

from logan_core.evidence_trust import EvidenceTrustEngine
from logan_core.normalization import Normalizer
from logan_core.receptors import (
    earnings_report_to_raw_signal,
    tesla_ai_partnership_corroboration,
    tesla_ai_partnership_signal,
)
from logan_core.receptors.providers import EarningsReport
from logan_core.trigger_detection import StocksTriggerEvaluator
from logan_core.world_model import DEDUP_WINDOW, MAX_RECENT_EVENT_HISTORY, WorldModel


def test_corroborating_signal_dedupes_into_same_event(now):
    normalizer = Normalizer()
    world_model = WorldModel()

    n1 = normalizer.normalize(tesla_ai_partnership_signal(now))
    n2 = normalizer.normalize(tesla_ai_partnership_corroboration(now))

    first_event = world_model.process(n1)
    second_event = world_model.process(n2)

    assert first_event.is_new is True
    assert second_event.is_new is False
    assert second_event.event_id == first_event.event_id
    assert n2.signal_id in second_event.supporting
    assert set(second_event.signal_ids) == {n1.signal_id, n2.signal_id}


def test_signal_outside_dedup_window_is_a_new_event(now):
    normalizer = Normalizer()
    world_model = WorldModel()

    n1 = normalizer.normalize(tesla_ai_partnership_signal(now))
    later_raw = tesla_ai_partnership_corroboration(now + timedelta(hours=3))
    n2 = normalizer.normalize(later_raw)

    first_event = world_model.process(n1)
    second_event = world_model.process(n2)

    assert second_event.is_new is True
    assert second_event.event_id != first_event.event_id


def test_downstream_ripple_includes_related_entities(now):
    normalizer = Normalizer()
    world_model = WorldModel()
    n1 = normalizer.normalize(tesla_ai_partnership_signal(now))
    event = world_model.process(n1)

    assert "NVDA" in event.downstream
    assert "MARKETS" in event.downstream


def test_decision_trace_populated_for_new_and_corroborating_events(now):
    normalizer = Normalizer()
    world_model = WorldModel()

    n1 = normalizer.normalize(tesla_ai_partnership_signal(now))
    assert n1.decision_trace, "Normalizer must populate NormalizedSignal.decision_trace"

    first_event = world_model.process(n1)
    assert len(first_event.decision_trace) == 1
    assert "new event" in first_event.decision_trace[0].rule

    n2 = normalizer.normalize(tesla_ai_partnership_corroboration(now))
    second_event = world_model.process(n2)
    assert len(second_event.decision_trace) == 2
    assert "corroboration" in second_event.decision_trace[1].rule


def test_contradicting_is_reserved_not_populated(now):
    """V3.1.4 BATCH-2: contradicting is intentionally never populated in V1 --
    see world_model/model.py's note on process(). This test documents that as
    current, deliberate behavior rather than leaving it unverified.
    """
    normalizer = Normalizer()
    world_model = WorldModel()
    n1 = normalizer.normalize(tesla_ai_partnership_signal(now))
    event = world_model.process(n1)
    assert event.contradicting == []


def _earnings_report(now, actual_eps=1.05, consensus_eps=0.98):
    return EarningsReport(
        entity_id="NVDA",
        actual_eps=actual_eps,
        consensus_eps=consensus_eps,
        fiscal_quarter="Q2 2026",
        report_timestamp=now,
        source_id="fixture_earnings_provider",
        source_name="STRATUS Test Fixture (not live data)",
    )


def test_trigger_event_attaches_on_new_event(now):
    """Sprint 3.6.6: WorldModel.process()'s optional trigger_event param."""
    normalizer = Normalizer()
    world_model = WorldModel()
    evaluator = StocksTriggerEvaluator()

    raw = earnings_report_to_raw_signal(_earnings_report(now))
    normalized = normalizer.normalize(raw)
    trigger = evaluator.evaluate(raw, normalized)
    assert trigger is not None  # sanity: this fixture is a qualifying beat

    event = world_model.process(normalized, trigger_event=trigger)
    assert event.trigger_events == [trigger]


def test_trigger_event_omitted_leaves_list_empty(now):
    """Every existing caller (trigger_event not passed) is unaffected."""
    normalizer = Normalizer()
    world_model = WorldModel()
    n1 = normalizer.normalize(tesla_ai_partnership_signal(now))
    event = world_model.process(n1)
    assert event.trigger_events == []


def test_duplicate_trigger_does_not_double_count(now):
    """Phase 5's 'duplicate polling results' edge case: the same report
    re-observed within the dedup window must not accumulate two entries for
    the same trigger_code (a duplicate would still inflate ConvergenceDetector's
    trigger_codes list and audit trail even though it wouldn't change
    trigger_confidence_bonus itself, since it resolves to the strongest
    single trigger, not a sum -- see convergence/detector.py)."""
    normalizer = Normalizer()
    world_model = WorldModel()
    evaluator = StocksTriggerEvaluator()

    raw = earnings_report_to_raw_signal(_earnings_report(now))
    normalized = normalizer.normalize(raw)
    trigger = evaluator.evaluate(raw, normalized)

    world_model.process(normalized, trigger_event=trigger)
    # Re-poll of the identical report a moment later, still in-window.
    raw2 = earnings_report_to_raw_signal(_earnings_report(now + timedelta(minutes=2)))
    normalized2 = normalizer.normalize(raw2)
    trigger2 = evaluator.evaluate(raw2, normalized2)
    event = world_model.process(normalized2, trigger_event=trigger2)

    assert len(event.trigger_events) == 1


def test_corrected_earnings_replaces_prior_trigger_for_same_code(now):
    """Phase 5's 'provider corrections/revisions' edge case: a revised report
    with different numbers replaces the prior trigger for that trigger_code
    rather than stacking (no revision history in this minimal contract --
    see world_model/model.py's comment on why this isn't the full
    TRIGGER_EVENT_FRAMEWORK.md revision model)."""
    normalizer = Normalizer()
    world_model = WorldModel()
    evaluator = StocksTriggerEvaluator()

    raw = earnings_report_to_raw_signal(_earnings_report(now, actual_eps=1.05))
    normalized = normalizer.normalize(raw)
    trigger = evaluator.evaluate(raw, normalized)
    world_model.process(normalized, trigger_event=trigger)

    corrected_raw = earnings_report_to_raw_signal(
        _earnings_report(now + timedelta(minutes=5), actual_eps=1.10)
    )
    corrected_normalized = normalizer.normalize(corrected_raw)
    corrected_trigger = evaluator.evaluate(corrected_raw, corrected_normalized)
    event = world_model.process(corrected_normalized, trigger_event=corrected_trigger)

    assert len(event.trigger_events) == 1
    assert event.trigger_events[0].context["actual_eps"] == 1.10


# --- Sprint 3.6.6E: repeated polling must not inflate corroboration/confidence ---


def _nvda_raw(now, actual_eps=1.87, consensus_eps=1.76, source_id="fmp"):
    return earnings_report_to_raw_signal(
        EarningsReport(
            entity_id="NVDA",
            actual_eps=actual_eps,
            consensus_eps=consensus_eps,
            fiscal_quarter="Q1 2027",
            report_timestamp=now,
            source_id=source_id,
            source_name="Financial Modeling Prep",
        )
    )


def test_duplicate_poll_same_source_same_content_does_not_grow_supporting(now):
    """Reproduces the reported bug: the live NVDA path re-fetches the same
    unchanged FMP report on every /v1/opportunities request. A repeated poll
    of identical evidence must not be counted as new corroborating evidence."""
    normalizer = Normalizer()
    world_model = WorldModel()

    n1 = normalizer.normalize(_nvda_raw(now))
    first_event = world_model.process(n1)
    assert first_event.supporting == []

    n2 = normalizer.normalize(_nvda_raw(now + timedelta(minutes=1)))
    second_event = world_model.process(n2)

    assert second_event.supporting == []
    # Provenance is still preserved -- signal_ids records that the poll happened.
    assert set(second_event.signal_ids) == {n1.signal_id, n2.signal_id}
    assert "duplicate observation" in second_event.decision_trace[-1].rule


def test_repeated_duplicate_polls_stay_flat(now):
    normalizer = Normalizer()
    world_model = WorldModel()

    world_model.process(normalizer.normalize(_nvda_raw(now)))
    event = None
    for minute in range(1, 6):
        event = world_model.process(
            normalizer.normalize(_nvda_raw(now + timedelta(minutes=minute)))
        )
    assert event is not None
    assert event.supporting == []


def test_different_source_after_duplicate_polls_still_counts_as_corroboration(now):
    """Independent corroborating evidence must still be able to increase
    confidence later -- only same-source/same-content repeats are excluded."""
    normalizer = Normalizer()
    world_model = WorldModel()

    world_model.process(normalizer.normalize(_nvda_raw(now)))
    world_model.process(
        normalizer.normalize(_nvda_raw(now + timedelta(minutes=1)))
    )  # duplicate, no growth expected

    different_source = normalizer.normalize(
        _nvda_raw(now + timedelta(minutes=2), source_id="bloomberg_terminal")
    )
    event = world_model.process(different_source)

    assert different_source.signal_id in event.supporting
    assert "corroboration" in event.decision_trace[-1].rule
    assert "duplicate observation" not in event.decision_trace[-1].rule


def test_changed_content_from_same_source_is_absorbed_not_corroboration(now):
    """ADR-076 reversed the earlier rule here. A corrected/revised report
    from the same source is genuinely new information and is absorbed (its
    signal is recorded, and a corrected trigger replaces the prior one --
    see test_corrected_earnings_replaces_prior_trigger_for_same_code), but
    one source cannot corroborate itself: `supporting` does not grow."""
    normalizer = Normalizer()
    world_model = WorldModel()

    first = world_model.process(
        normalizer.normalize(_nvda_raw(now, actual_eps=1.87, consensus_eps=1.76))
    )
    revised = normalizer.normalize(
        _nvda_raw(now + timedelta(minutes=1), actual_eps=1.90, consensus_eps=1.76)
    )
    event = world_model.process(revised)

    assert event.event_id == first.event_id
    assert event.supporting == []
    assert revised.signal_id in event.signal_ids
    assert "already counted" in event.decision_trace[-1].rule
    assert "corroboration: merged" not in event.decision_trace[-1].rule


def test_a_source_reporting_ever_changing_content_never_corroborates_itself(now):
    """The live case: a quote whose value moves on every refresh."""
    normalizer = Normalizer()
    world_model = WorldModel()
    event = None
    for step in range(500):
        event = world_model.process(
            normalizer.normalize(
                _nvda_raw(
                    now + timedelta(seconds=step),
                    actual_eps=1.87 + step / 1000,
                    consensus_eps=1.76,
                )
            )
        )
    assert event is not None
    assert event.supporting == []


def test_supporting_counts_each_independent_source_once(now):
    normalizer = Normalizer()
    world_model = WorldModel()
    world_model.process(normalizer.normalize(_nvda_raw(now)))

    event = None
    for step in range(1, 41):
        # Two other sources alternate, each changing its content every time.
        source = "bloomberg_terminal" if step % 2 else "reuters_wire"
        event = world_model.process(
            normalizer.normalize(
                _nvda_raw(
                    now + timedelta(seconds=step),
                    actual_eps=1.87 + step / 100,
                    consensus_eps=1.76,
                    source_id=source,
                )
            )
        )
    assert event is not None
    assert len(event.supporting) == 2  # one per independent source, not 40


def test_a_new_source_still_corroborates_after_same_source_updates(now):
    normalizer = Normalizer()
    world_model = WorldModel()
    world_model.process(normalizer.normalize(_nvda_raw(now, actual_eps=1.87)))
    world_model.process(
        normalizer.normalize(_nvda_raw(now + timedelta(minutes=1), actual_eps=1.90))
    )
    independent = normalizer.normalize(
        _nvda_raw(now + timedelta(minutes=2), source_id="bloomberg_terminal")
    )
    event = world_model.process(independent)
    assert event.supporting == [independent.signal_id]
    assert "corroboration: merged" in event.decision_trace[-1].rule


def test_same_source_updates_do_not_raise_the_trust_score(now):
    """What the fix is for: confidence must not rise because one source
    kept re-reporting. Compared at one fixed evaluation time so recency is
    identical on both sides."""
    from logan_core.evidence_trust import EvidenceTrustEngine

    normalizer = Normalizer()
    engine = EvidenceTrustEngine()
    evaluated_at = now + timedelta(minutes=30)

    single_model = WorldModel()
    single_signal = normalizer.normalize(_nvda_raw(now))
    single = engine.evaluate(
        single_model.process(single_signal), [single_signal], now=evaluated_at
    )

    repeated_model = WorldModel()
    signals, event = [], None
    for step in range(10):
        signal = normalizer.normalize(
            _nvda_raw(now, actual_eps=1.87 + step / 100, consensus_eps=1.76)
        )
        signals.append(signal)
        event = repeated_model.process(signal)
    assert event is not None
    repeated = engine.evaluate(event, signals, now=evaluated_at)

    assert single.corroboration == repeated.corroboration == 0
    assert repeated.trust_score == single.trust_score


def test_repeated_identical_fmp_evidence_does_not_inflate_confidence(now):
    """End-to-end regression test for the reported bug: World Model +
    EvidenceTrustEngine together, proving repeated /v1/opportunities-style
    polling of the same live NVDA report does not raise trust_score."""
    normalizer = Normalizer()
    world_model = WorldModel()
    engine = EvidenceTrustEngine()

    n1 = normalizer.normalize(_nvda_raw(now))
    event = world_model.process(n1)
    # A fixed evaluation instant for every call below -- isolates the
    # corroboration-driven inflation this test targets from ordinary (and
    # correct) recency decay, which is unrelated to the reported bug.
    first_trust = engine.evaluate(event, [n1], now=now)

    for minute in range(1, 4):
        n = normalizer.normalize(_nvda_raw(now + timedelta(minutes=minute)))
        event = world_model.process(n)
        repeated_trust = engine.evaluate(event, [n], now=now)
        assert repeated_trust.trust_score == first_trust.trust_score
        assert repeated_trust.corroboration == first_trust.corroboration
        assert repeated_trust.corroboration == 0


# --- STRATUS reliability correction (2026-10-04 OOM root-cause fix) ------
#
# Confirmed production root cause: the live stock feed runs the full
# pipeline roughly 1-3 times/minute, continuously, forever (the 60s
# notification poller and the mobile app's own foreground poll both call
# it independently against the same shared WorldModel). Every poll that
# corroborates into an already-known event used to append, unconditionally
# and without bound, to that event's `signal_ids`/`decision_trace` -- and
# the dedup window that decides "is this corroboration" never actually
# aged out for an unchanged provider report, because it compared the
# signal's own (frozen) `captured_at` against itself. These tests cover
# the two fixes together: bounded growth, and real-time-based dedup aging.


def test_signal_ids_and_decision_trace_remain_bounded_under_heavy_repeated_polling(
    now,
):
    """Reproduces the confirmed OOM root cause at scale: thousands of
    corroborating polls of one unchanged signal must not grow
    `signal_ids`/`decision_trace` without bound."""
    normalizer = Normalizer()
    world_model = WorldModel()

    event = world_model.process(normalizer.normalize(_nvda_raw(now)), observed_at=now)
    for i in range(1, 3000):
        event = world_model.process(
            normalizer.normalize(_nvda_raw(now + timedelta(seconds=i))),
            observed_at=now + timedelta(seconds=i),
        )

    assert len(event.signal_ids) <= MAX_RECENT_EVENT_HISTORY
    assert len(event.decision_trace) <= MAX_RECENT_EVENT_HISTORY
    # `supporting` semantics are completely untouched by the bound: these
    # are all identical-content duplicate polls, so it must stay exactly
    # as empty as it is today, regardless of the new cap.
    assert event.supporting == []
    assert event.is_new is False
    # The event identity itself is unaffected by bounding provenance --
    # this is still one continuously-corroborated event throughout.
    assert event.event_id == world_model.get_event(event.event_id).event_id


def test_genuine_corroboration_still_recorded_after_bound_is_exceeded(now):
    """The fixed-size history bound trims provenance bookkeeping only --
    genuinely new corroborating evidence arriving after the bound has
    already been exceeded must still be recognized and still raise
    `supporting`, exactly as before this fix."""
    normalizer = Normalizer()
    world_model = WorldModel()
    total_duplicate_polls = MAX_RECENT_EVENT_HISTORY + 20

    event = world_model.process(normalizer.normalize(_nvda_raw(now)), observed_at=now)
    for i in range(1, total_duplicate_polls):
        event = world_model.process(
            normalizer.normalize(_nvda_raw(now + timedelta(seconds=i))),
            observed_at=now + timedelta(seconds=i),
        )
    assert event.supporting == []
    assert len(event.signal_ids) <= MAX_RECENT_EVENT_HISTORY

    # A genuinely different source, still well within DEDUP_WINDOW of the
    # last touch -- real corroboration, not a duplicate.
    next_t = total_duplicate_polls
    different_source = normalizer.normalize(
        _nvda_raw(now + timedelta(seconds=next_t), source_id="bloomberg_terminal")
    )
    event = world_model.process(
        different_source, observed_at=now + timedelta(seconds=next_t)
    )

    assert different_source.signal_id in event.supporting
    assert "corroboration" in event.decision_trace[-1].rule
    assert len(event.signal_ids) <= MAX_RECENT_EVENT_HISTORY
    assert len(event.decision_trace) <= MAX_RECENT_EVENT_HISTORY


def test_dedup_ages_out_by_processing_time_even_when_provider_timestamp_is_frozen(
    now,
):
    """The actual bug: a provider report whose own captured_at never
    advances between polls (the live case -- FMP keeps returning the
    identical earnings report every ~60s) must not stay inside the dedup
    window forever purely because `signal.captured_at - recent[0]` always
    evaluated to zero. Two touches of the SAME unchanged captured_at,
    separated by more than DEDUP_WINDOW of real processing time, must now
    correctly age out into a new event."""
    normalizer = Normalizer()
    world_model = WorldModel()

    raw = earnings_report_to_raw_signal(_earnings_report(now))
    first_event = world_model.process(normalizer.normalize(raw), observed_at=now)

    # Same unchanged report (captured_at == now, exactly as before) but
    # processed more than DEDUP_WINDOW of real wall-clock time later.
    same_raw = earnings_report_to_raw_signal(_earnings_report(now))
    second_event = world_model.process(
        normalizer.normalize(same_raw),
        observed_at=now + DEDUP_WINDOW + timedelta(minutes=1),
    )

    assert second_event.is_new is True
    assert second_event.event_id != first_event.event_id
    # Genuinely new events/signals are still retained -- a dedup rollover
    # is additive, never destructive: the original event must still be
    # retrievable by its own event_id.
    retained = world_model.get_event(first_event.event_id)
    assert retained is not None
    assert retained.event_id == first_event.event_id
    assert retained.is_new is True


def test_dedup_still_merges_within_processing_time_window_when_provider_timestamp_is_frozen(
    now,
):
    """Companion regression: continuous real-time polling of the same
    unchanged report -- the correct, intended, steady-state production
    behavior -- must keep merging into the same event exactly as before.
    This fix must never make STRATUS invent a new opportunity every poll."""
    normalizer = Normalizer()
    world_model = WorldModel()

    raw = earnings_report_to_raw_signal(_earnings_report(now))
    first_event = world_model.process(normalizer.normalize(raw), observed_at=now)

    same_raw = earnings_report_to_raw_signal(_earnings_report(now))
    second_event = world_model.process(
        normalizer.normalize(same_raw), observed_at=now + timedelta(minutes=1)
    )

    assert second_event.is_new is False
    assert second_event.event_id == first_event.event_id


def test_dedup_aging_is_unaffected_when_observed_at_is_omitted(now):
    """Every existing/production caller never passes `observed_at` (the
    orchestrator calls `world_model.process(n, trigger_event=t)` with no
    third argument) -- confirms the default (real `datetime.now(timezone.
    utc)`) still correctly merges two calls made moments apart in real
    time, with no explicit observed_at needed."""
    normalizer = Normalizer()
    world_model = WorldModel()

    n1 = normalizer.normalize(tesla_ai_partnership_signal(now))
    n2 = normalizer.normalize(tesla_ai_partnership_corroboration(now))

    first_event = world_model.process(n1)
    second_event = world_model.process(n2)

    assert second_event.is_new is False
    assert second_event.event_id == first_event.event_id


def test_get_event_returns_none_for_unknown_event_id(now):
    """The new read-only accessor is a plain, total lookup -- never raises
    for an event_id this instance never produced."""
    from uuid import uuid4

    world_model = WorldModel()
    assert world_model.get_event(uuid4()) is None
