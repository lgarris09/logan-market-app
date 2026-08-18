"""Sprint 3.6.6D — ConvergenceDetector unit tests.

Covers the owner-decided resolution rule directly: multiple TriggerEvents
attached to one event resolve to the single strongest applicable
confidence_contribution, not a sum, while every fired TriggerEvent's code
remains visible in the resolution for auditability.
"""

from datetime import datetime, timezone
from uuid import uuid4

from logan_core.contracts import TriggerEvent
from logan_core.convergence import ConvergenceDetector


def _trigger(trigger_code: str, confidence_contribution: float) -> TriggerEvent:
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


def test_empty_trigger_list_resolves_to_zero():
    resolution = ConvergenceDetector().resolve([])
    assert resolution.confidence_bonus == 0.0
    assert resolution.dominant_trigger is None
    assert resolution.trigger_codes == []


def test_single_trigger_passes_through_unchanged():
    trigger = _trigger("STOCK_EARNINGS_BEAT", 0.22)
    resolution = ConvergenceDetector().resolve([trigger])
    assert resolution.confidence_bonus == 0.22
    assert resolution.dominant_trigger is trigger
    assert resolution.trigger_codes == ["STOCK_EARNINGS_BEAT"]


def test_multiple_triggers_use_strongest_not_sum():
    weaker = _trigger("STOCK_EARNINGS_IN_LINE", 0.0)
    stronger = _trigger("STOCK_EARNINGS_BEAT", 0.22)
    resolution = ConvergenceDetector().resolve([weaker, stronger])

    # If this were summed, confidence_bonus would be 0.22 too (0.0 + 0.22) --
    # use a genuinely distinguishing case below to prove it's max, not sum.
    assert resolution.confidence_bonus == 0.22
    assert resolution.dominant_trigger is stronger


def test_two_positive_contributions_do_not_add():
    a = _trigger("STOCK_EARNINGS_BEAT", 0.22)
    b = _trigger("STOCK_GUIDANCE_RAISED", 0.15)
    resolution = ConvergenceDetector().resolve([a, b])

    # Summed, this would be 0.37. The owner decision is explicit: strongest
    # only, never combined.
    assert resolution.confidence_bonus == 0.22
    assert resolution.confidence_bonus != 0.22 + 0.15
    assert resolution.dominant_trigger is a


def test_all_fired_trigger_codes_preserved_in_resolution():
    a = _trigger("STOCK_EARNINGS_BEAT", 0.22)
    b = _trigger("STOCK_GUIDANCE_RAISED", 0.15)
    resolution = ConvergenceDetector().resolve([a, b])
    assert set(resolution.trigger_codes) == {
        "STOCK_EARNINGS_BEAT",
        "STOCK_GUIDANCE_RAISED",
    }


def test_confidence_bonus_clamped_when_dominant_is_negative():
    # TriggerEvent.confidence_contribution is schema-bounded to [-1.0, 1.0]
    # (a companion/downside-only trigger like the unimplemented
    # STOCK_EARNINGS_QUALITY_WARNING's registered -0.15 could reach this
    # path on its own) -- the resolver still clamps the bonus to >= 0.0,
    # never a negative trigger_confidence_bonus.
    trigger = _trigger("HYPOTHETICAL_NEGATIVE_ONLY", -0.15)
    resolution = ConvergenceDetector().resolve([trigger])
    assert resolution.confidence_bonus == 0.0
    assert resolution.dominant_trigger is trigger
