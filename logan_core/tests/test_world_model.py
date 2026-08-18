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
from logan_core.world_model import WorldModel


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


def test_changed_content_from_same_source_still_counts_as_corroboration(now):
    """A corrected/revised report from the same source (different EPS
    numbers -- different signal.value text) is genuinely new information,
    not a duplicate poll, and should still be able to increase confidence."""
    normalizer = Normalizer()
    world_model = WorldModel()

    world_model.process(
        normalizer.normalize(_nvda_raw(now, actual_eps=1.87, consensus_eps=1.76))
    )
    revised = normalizer.normalize(
        _nvda_raw(now + timedelta(minutes=1), actual_eps=1.90, consensus_eps=1.76)
    )
    event = world_model.process(revised)

    assert revised.signal_id in event.supporting


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
