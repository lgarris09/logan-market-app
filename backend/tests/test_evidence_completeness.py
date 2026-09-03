"""V1a Final Proof-Readiness Closeout, item 1 -- the approved, deterministic
evidence-completeness definition (compute_thesis_evidence_completeness())
and its day-level rate (complete_evidence_payload_rate()). Every scenario
uses real DeliveredItem/ConclusionConfidence/TriggerEvent objects, never
mocks -- this is a pure function over real contract instances.
"""

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from backend.app.universe_telemetry import (
    complete_evidence_payload_rate,
    compute_thesis_evidence_completeness,
)
from backend.app.universe_telemetry_store import (
    DailyObservationDelta,
    UniverseDailyTelemetryStore,
)
from logan_core.contracts import ConclusionConfidence, DeliveredItem, TriggerEvent

NOW = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)


def _delivered_item(
    *,
    headline="AAPL beat earnings",
    what_happened="AAPL reported EPS above consensus.",
    why_it_matters="Signals continued margin strength.",
    why_now="Reported this morning.",
) -> DeliveredItem:
    return DeliveredItem(
        event_id=uuid4(),
        surface="feed_card",
        headline=headline,
        what_happened=what_happened,
        why_it_matters=why_it_matters,
        why_it_matters_to_me="You hold AAPL.",
        why_now=why_now,
        confidence_label="High",
        confidence_score=0.8,
        delivered_at=NOW,
    )


def _confidence(*, score=0.8) -> ConclusionConfidence:
    return ConclusionConfidence(
        event_id=uuid4(),
        confidence_score=score,
        classification="inference",
        evaluated_at=NOW,
    )


def _trigger_event() -> TriggerEvent:
    return TriggerEvent(
        trigger_id=uuid4(),
        trigger_code="STOCK_EARNINGS_BEAT",
        trigger_class="catalyst",
        trigger_type="earnings",
        trigger_status="confirmed",
        domain="stocks",
        affected_entity_id="AAPL",
        direction="positive",
        raw_magnitude=0.05,
        confidence_contribution=0.22,
        event_timestamp=NOW,
        detected_timestamp=NOW,
        source_id="fmp",
        source_name="FMP",
    )


# --- compute_thesis_evidence_completeness() -----------------------------------


def test_fully_complete():
    assert (
        compute_thesis_evidence_completeness(
            delivered_item=_delivered_item(),
            confidence=_confidence(),
            trigger_events=[_trigger_event()],
            freshness_state="FRESH",
        )
        is True
    )


@pytest.mark.parametrize(
    "field",
    ["headline", "what_happened", "why_it_matters", "why_now"],
)
def test_missing_narrative_component_is_incomplete(field):
    kwargs = {field: "   "}  # whitespace-only -- must count as empty
    assert (
        compute_thesis_evidence_completeness(
            delivered_item=_delivered_item(**kwargs),
            confidence=_confidence(),
            trigger_events=[_trigger_event()],
            freshness_state="FRESH",
        )
        is False
    )


def test_zero_real_evidence_is_incomplete():
    assert (
        compute_thesis_evidence_completeness(
            delivered_item=_delivered_item(),
            confidence=_confidence(),
            trigger_events=[],
            freshness_state="FRESH",
        )
        is False
    )


def test_missing_confidence_is_incomplete():
    assert (
        compute_thesis_evidence_completeness(
            delivered_item=_delivered_item(),
            confidence=None,
            trigger_events=[_trigger_event()],
            freshness_state="FRESH",
        )
        is False
    )


def test_unavailable_evidence_is_incomplete_via_no_value_at_all():
    """UNAVAILABLE reached via freshness.py's "no value at all" path."""
    assert (
        compute_thesis_evidence_completeness(
            delivered_item=_delivered_item(),
            confidence=_confidence(),
            trigger_events=[_trigger_event()],
            freshness_state="UNAVAILABLE",
        )
        is False
    )


def test_stale_beyond_grace_is_incomplete():
    """UNAVAILABLE reached via freshness.py's "past even the grace window"
    path -- a conceptually distinct real scenario from "no value at all,"
    both honestly classified UNAVAILABLE by classify_freshness() and both
    must fail completeness identically."""
    from logan_core.receptors.providers.freshness import (
        classify_freshness,
        signal_family_contract,
    )

    contract = signal_family_contract("quote")
    state = classify_freshness(
        has_value=True,
        age_seconds=contract.target_ttl_seconds + contract.grace_seconds + 1.0,
        contract=contract,
    )
    assert state == "UNAVAILABLE"  # confirms this really is the "beyond grace" path
    assert (
        compute_thesis_evidence_completeness(
            delivered_item=_delivered_item(),
            confidence=_confidence(),
            trigger_events=[_trigger_event()],
            freshness_state=state,
        )
        is False
    )


def test_stale_within_grace_with_honest_disclosure_is_still_complete():
    """The approved policy: STALE_WITHIN_GRACE does not automatically fail
    completeness, since the evidence is within the explicitly permitted
    grace policy and the state is always truthfully exposed (never hidden)
    -- disclosure is structural here, not a separate flag to set."""
    from logan_core.receptors.providers.freshness import (
        classify_freshness,
        signal_family_contract,
    )

    contract = signal_family_contract("quote")
    state = classify_freshness(
        has_value=True,
        age_seconds=contract.target_ttl_seconds + 1.0,  # past TTL, within grace
        contract=contract,
    )
    assert state == "STALE_WITHIN_GRACE"
    assert (
        compute_thesis_evidence_completeness(
            delivered_item=_delivered_item(),
            confidence=_confidence(),
            trigger_events=[_trigger_event()],
            freshness_state=state,
        )
        is True
    )


def test_no_registered_freshness_contract_does_not_by_itself_fail():
    """None (no contract for this item's signal type, e.g. a demo entity)
    is not "required evidence missing" -- freshness simply doesn't apply."""
    assert (
        compute_thesis_evidence_completeness(
            delivered_item=_delivered_item(),
            confidence=_confidence(),
            trigger_events=[_trigger_event()],
            freshness_state=None,
        )
        is True
    )


# --- complete_evidence_payload_rate() / polling-frequency independence -------


def test_complete_evidence_payload_rate_is_none_with_no_data(tmp_path):
    store = UniverseDailyTelemetryStore(str(tmp_path / "telemetry.db"))
    day = date(2026, 9, 3)
    store.record(day, DailyObservationDelta())
    row = store.get(day)
    store.close()
    assert row is not None
    assert complete_evidence_payload_rate(row) is None


def test_complete_evidence_payload_rate_computed_from_real_distinct_theses(tmp_path):
    store = UniverseDailyTelemetryStore(str(tmp_path / "telemetry.db"))
    day = date(2026, 9, 3)
    store.record(
        day,
        DailyObservationDelta(
            thesis_completeness_by_event_id={
                "event-1": True,
                "event-2": True,
                "event-3": False,
            }
        ),
    )
    row = store.get(day)
    store.close()
    assert row is not None
    assert complete_evidence_payload_rate(row) == pytest.approx(2 / 3)


def test_polling_frequency_independence_latest_observation_wins(tmp_path):
    """The core regression test: polling the SAME thesis repeatedly in one
    day, even with a completeness state that changes between polls, must
    never inflate the denominator -- one event_id is always one entry,
    and the rate reflects only its most recently observed state."""
    store = UniverseDailyTelemetryStore(str(tmp_path / "telemetry.db"))
    day = date(2026, 9, 3)

    # First poll: thesis is complete.
    store.record(
        day, DailyObservationDelta(thesis_completeness_by_event_id={"event-1": True})
    )
    # 49 more polls of the exact same real thesis, unchanged.
    for _ in range(49):
        store.record(
            day,
            DailyObservationDelta(thesis_completeness_by_event_id={"event-1": True}),
        )
    row = store.get(day)
    store.close()
    assert row is not None
    assert row.observation_count == 50
    # Still exactly one thesis, still complete -- polling 50x never
    # inflated the denominator or fabricated additional complete/incomplete
    # theses.
    assert len(row.thesis_completeness_by_event_id) == 1
    assert complete_evidence_payload_rate(row) == 1.0


def test_polling_frequency_independence_latest_state_overwrites_stale_one(tmp_path):
    store = UniverseDailyTelemetryStore(str(tmp_path / "telemetry.db"))
    day = date(2026, 9, 3)
    store.record(
        day, DailyObservationDelta(thesis_completeness_by_event_id={"event-1": True})
    )
    # A later poll the same day finds the same real thesis has degraded
    # (e.g. evidence went stale beyond grace) -- the latest state must win.
    store.record(
        day, DailyObservationDelta(thesis_completeness_by_event_id={"event-1": False})
    )
    row = store.get(day)
    store.close()
    assert row is not None
    assert row.thesis_completeness_by_event_id == {"event-1": False}
    assert complete_evidence_payload_rate(row) == 0.0
