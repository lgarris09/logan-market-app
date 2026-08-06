from datetime import timedelta

from logan_core.normalization import Normalizer
from logan_core.receptors import tesla_ai_partnership_signal, tesla_ai_partnership_corroboration
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
