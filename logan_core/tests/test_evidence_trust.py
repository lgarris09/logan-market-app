from datetime import timedelta

from logan_core.contracts import NormalizedSignal
from logan_core.evidence_trust import EvidenceTrustEngine
from logan_core.normalization import Normalizer
from logan_core.receptors import tesla_ai_partnership_signal, tesla_ai_partnership_corroboration
from logan_core.world_model import WorldModel


def _build_event_and_signals(now):
    normalizer = Normalizer()
    world_model = WorldModel()
    raw1 = tesla_ai_partnership_signal(now)
    raw2 = tesla_ai_partnership_corroboration(now)
    n1 = normalizer.normalize(raw1)
    n2 = normalizer.normalize(raw2)
    world_model.process(n1)
    event = world_model.process(n2)
    return event, [n1, n2]


def test_corroborating_sources_increase_trust_score(now):
    event, signals = _build_event_and_signals(now)
    engine = EvidenceTrustEngine()

    single_source = engine.evaluate(event, [signals[0]], now=now)
    both_sources = engine.evaluate(event, signals, now=now)

    assert both_sources.corroboration >= single_source.corroboration
    assert both_sources.trust_score >= single_source.trust_score


def test_trust_score_bounded_zero_to_one(now):
    event, signals = _build_event_and_signals(now)
    engine = EvidenceTrustEngine()
    result = engine.evaluate(event, signals, now=now)
    assert 0.0 <= result.trust_score <= 1.0


def test_recency_decays_with_age(now):
    event, signals = _build_event_and_signals(now)
    engine = EvidenceTrustEngine()

    fresh = engine.evaluate(event, signals, now=now)
    stale = engine.evaluate(event, signals, now=now + timedelta(hours=24))

    assert stale.recency_score < fresh.recency_score
    assert stale.trust_score < fresh.trust_score


def test_evidence_trust_reserves_deterministic_baseline_model_version(now):
    event, signals = _build_event_and_signals(now)
    engine = EvidenceTrustEngine()
    result = engine.evaluate(event, signals, now=now)
    assert result.source_reliability_model_version == "deterministic-baseline"


def test_evidence_trust_populates_decision_trace(now):
    event, signals = _build_event_and_signals(now)
    engine = EvidenceTrustEngine()
    result = engine.evaluate(event, signals, now=now)
    assert len(result.decision_trace) == 1
    assert "trust_score" in result.decision_trace[0].rule


def test_unknown_source_gets_default_score(now):
    normalizer = Normalizer()
    world_model = WorldModel()
    raw = tesla_ai_partnership_signal(now)
    normalized = normalizer.normalize(raw)
    normalized = normalized.model_copy(update={"source_id": "unregistered_source"})
    event = world_model.process(normalized)

    engine = EvidenceTrustEngine()
    result = engine.evaluate(event, [normalized], now=now)
    assert result.source_score == 0.5
