from datetime import datetime, timedelta, timezone
from uuid import uuid4

from logan_core.contracts import TriggerEvent
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


def test_trigger_confidence_bonus_defaults_zero(now):
    """Sprint 3.6.6: every event without an attached TriggerEvent (i.e. every
    event before this sprint) must be completely unaffected."""
    event, signals = _build_event_and_signals(now)
    engine = EvidenceTrustEngine()
    result = engine.evaluate(event, signals, now=now)
    assert result.trigger_confidence_bonus == 0.0


def test_trigger_confidence_bonus_reflects_attached_trigger(now):
    normalizer = Normalizer()
    world_model = WorldModel()
    evaluator = StocksTriggerEvaluator()

    raw = earnings_report_to_raw_signal(
        EarningsReport(
            entity_id="NVDA",
            actual_eps=1.05,
            consensus_eps=0.98,
            report_timestamp=now,
            source_id="fixture_earnings_provider",
            source_name="STRATUS Test Fixture (not live data)",
        )
    )
    normalized = normalizer.normalize(raw)
    trigger = evaluator.evaluate(raw, normalized)
    event = world_model.process(normalized, trigger_event=trigger)

    engine = EvidenceTrustEngine()
    result = engine.evaluate(event, [normalized], now=now)
    assert result.trigger_confidence_bonus == 0.22
    assert any(
        "trigger_confidence_bonus" in entry.rule for entry in result.decision_trace
    )


def _extra_trigger(trigger_code: str, confidence_contribution: float) -> TriggerEvent:
    now = datetime.now(timezone.utc)
    return TriggerEvent(
        trigger_id=uuid4(),
        trigger_code=trigger_code,
        trigger_class="catalyst",
        trigger_type="earnings_surprise",
        trigger_status="confirmed",
        domain="stocks",
        affected_entity_id="NVDA",
        direction="positive",
        raw_magnitude=1.0,
        confidence_contribution=confidence_contribution,
        source_id="test",
        source_name="test",
        event_timestamp=now,
        detected_timestamp=now,
    )


def test_multiple_triggers_use_strongest_not_sum(now):
    """Sprint 3.6.6D (ConvergenceDetector): EvidenceTrustEngine no longer
    sums every attached trigger's confidence_contribution -- proves the
    integration, not just ConvergenceDetector in isolation
    (test_convergence.py already covers the resolver's own logic)."""
    normalizer = Normalizer()
    world_model = WorldModel()
    evaluator = StocksTriggerEvaluator()

    raw = earnings_report_to_raw_signal(
        EarningsReport(
            entity_id="NVDA",
            actual_eps=1.05,
            consensus_eps=0.98,
            report_timestamp=now,
            source_id="fixture_earnings_provider",
            source_name="STRATUS Test Fixture (not live data)",
        )
    )
    normalized = normalizer.normalize(raw)
    beat_trigger = evaluator.evaluate(raw, normalized)
    assert beat_trigger is not None and beat_trigger.confidence_contribution == 0.22

    # A hand-attached second trigger on the same event, simulating a future
    # scenario where two independent trigger codes both fire for one entity
    # (not producible by today's earnings-only evaluator, since BEAT/MISS/
    # IN_LINE are mutually exclusive -- this is exactly the "foundation for
    # later" case ConvergenceDetector exists to handle correctly today).
    weaker_trigger = _extra_trigger("STOCK_GUIDANCE_RAISED", 0.15)
    event = world_model.process(normalized, trigger_event=beat_trigger)
    event = event.model_copy(
        update={"trigger_events": event.trigger_events + [weaker_trigger]}
    )

    engine = EvidenceTrustEngine()
    result = engine.evaluate(event, [normalized], now=now)

    # If summed: 0.22 + 0.15 = 0.37. Strongest-only: 0.22.
    assert result.trigger_confidence_bonus == 0.22
    assert result.trigger_confidence_bonus != 0.37
    assert any("dominant=STOCK_EARNINGS_BEAT" in e.rule for e in result.decision_trace)
