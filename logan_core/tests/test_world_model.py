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
    assert "SMH" in event.downstream
