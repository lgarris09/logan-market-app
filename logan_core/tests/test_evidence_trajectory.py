"""Stock Opportunity Logic V2.2 -- Evidence + Trajectory Enrichment. Pure
unit tests against OpportunityLifecycleTracker.observe()'s new
market_evidence/trigger_directions parameters -- no backend/SQLite/FMP
involved. See backend/tests/test_evidence_trajectory_integration.py for the
wired-through-backend tests (real FMP profile/quote audit, persistence,
Ask STRATUS grounding).
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from logan_core.contracts import MarketEvidenceInput
from logan_core.opportunity_lifecycle import OpportunityLifecycleTracker

NOW = datetime(2026, 8, 24, 12, 0, 0, tzinfo=timezone.utc)


def _tracker() -> OpportunityLifecycleTracker:
    return OpportunityLifecycleTracker()


def _evidence(**overrides: Any) -> MarketEvidenceInput:
    defaults: dict[str, Any] = dict(
        price=100.0,
        change_pct=1.0,
        market_change_pct=0.0,
        sector="Technology",
        sector_change_pct=0.0,
        volume=1_000_000.0,
        average_volume=1_000_000.0,
        beta=1.5,
    )
    defaults.update(overrides)
    return MarketEvidenceInput(**defaults)


def _observe(
    tracker, evidence=None, directions=None, confidence=0.6, now=NOW, codes=None
):
    return tracker.observe(
        entity_id="NVDA",
        confidence_score=confidence,
        trigger_codes=codes or ["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.6,
        now=now,
        market_evidence=evidence,
        trigger_directions=directions,
    )


# --- Trigger price persists --------------------------------------------


def test_trigger_price_captured_on_first_evidence_bearing_poll():
    tracker = _tracker()
    delta = _observe(tracker, evidence=_evidence(price=100.0), directions=["positive"])
    assert delta.evidence is not None
    assert delta.evidence.trigger_price == 100.0
    assert delta.evidence.price_change_since_trigger_pct == 0.0


def test_trigger_price_persists_across_subsequent_evaluations():
    tracker = _tracker()
    _observe(tracker, evidence=_evidence(price=100.0), directions=["positive"])
    delta = _observe(
        tracker,
        evidence=_evidence(price=110.0),
        directions=["positive"],
        now=NOW + timedelta(hours=1),
    )
    assert delta.evidence is not None
    assert delta.evidence.trigger_price == 100.0  # unchanged, never overwritten
    assert delta.evidence.price_change_since_trigger_pct == 10.0


# --- Unchanged quote noise does not create a meaningful revision --------


def test_unchanged_quote_noise_does_not_create_meaningful_revision():
    tracker = _tracker()
    first = _observe(
        tracker,
        evidence=_evidence(price=100.0, change_pct=1.0),
        directions=["positive"],
    )
    second = _observe(
        tracker,
        evidence=_evidence(
            price=100.3, change_pct=1.1
        ),  # tiny move, same relative strength
        directions=["positive"],
        now=NOW + timedelta(hours=1),
    )
    assert second.is_meaningful is False
    assert second.new_revision == first.new_revision
    assert second.trajectory == "STEADY"
    assert second.change_type == "none"


# --- Strengthening evidence moves trajectory appropriately ---------------


def test_strengthening_relative_performance_moves_trajectory():
    tracker = _tracker()
    _observe(
        tracker,
        evidence=_evidence(
            price=100.0, change_pct=0.5, market_change_pct=0.5
        ),  # relative=0
        directions=["positive"],
    )
    delta = _observe(
        tracker,
        evidence=_evidence(
            price=103.0, change_pct=3.0, market_change_pct=0.5
        ),  # relative=+2.5
        directions=["positive"],
        now=NOW + timedelta(hours=1),
    )
    assert delta.trajectory == "STRENGTHENING"
    assert delta.previous_trajectory == "STEADY"
    assert delta.is_meaningful is True
    assert delta.change_type == "trajectory_strengthening"
    assert delta.new_revision == 2  # a real global revision was created


def test_reacceleration_while_remaining_strengthening_is_still_meaningful():
    tracker = _tracker()
    _observe(
        tracker,
        evidence=_evidence(price=100.0, change_pct=0.0, market_change_pct=0.0),
        directions=["positive"],
    )
    # First strengthening move (+1.5pp).
    first_move = _observe(
        tracker,
        evidence=_evidence(price=101.5, change_pct=1.5, market_change_pct=0.0),
        directions=["positive"],
        now=NOW + timedelta(hours=1),
    )
    assert first_move.trajectory == "STRENGTHENING"
    assert first_move.change_type == "trajectory_strengthening"

    # Reacceleration: a further, much bigger jump while already STRENGTHENING.
    reaccel = _observe(
        tracker,
        evidence=_evidence(price=110.0, change_pct=6.0, market_change_pct=0.0),
        directions=["positive"],
        now=NOW + timedelta(hours=2),
    )
    assert reaccel.trajectory == "STRENGTHENING"
    assert reaccel.change_type == "trajectory_reaccelerated"
    assert reaccel.is_meaningful is True
    assert reaccel.new_revision == 3


# --- Weakening relative performance weakens trajectory even when raw price is positive --


def test_weakening_relative_performance_weakens_trajectory_despite_positive_raw_price():
    tracker = _tracker()
    _observe(
        tracker,
        evidence=_evidence(
            price=100.0, change_pct=3.0, market_change_pct=0.0
        ),  # relative=+3
        directions=["positive"],
    )
    delta = _observe(
        tracker,
        # Raw price is UP 1% (positive) and still net outperforming the
        # market (relative=+1, still confirming) -- but relative strength
        # has dropped from +3 to +1, a genuine weakening of confirmation
        # that stays short of an outright reversal.
        evidence=_evidence(price=101.0, change_pct=1.0, market_change_pct=0.0),
        directions=["positive"],
        now=NOW + timedelta(hours=1),
    )
    assert delta.evidence is not None
    assert delta.evidence.price > delta.evidence.trigger_price  # raw price is positive
    assert delta.trajectory == "WEAKENING"
    assert delta.change_type == "trajectory_weakening"
    assert delta.is_meaningful is True


# --- Volume confirmation can strengthen evidence without inventing a new opportunity --


def test_volume_confirmation_strengthens_without_creating_new_opportunity():
    tracker = _tracker()
    first = _observe(
        tracker,
        evidence=_evidence(
            price=100.0,
            change_pct=0.3,
            market_change_pct=0.0,
            volume=900_000.0,
            average_volume=1_000_000.0,
        ),
        directions=["positive"],
    )
    delta = _observe(
        tracker,
        evidence=_evidence(
            price=100.5,
            change_pct=0.5,
            market_change_pct=0.0,  # relative strength barely moves (+0.2pp, below threshold)
            volume=1_800_000.0,
            average_volume=1_000_000.0,  # 1.8x average -- unusually high
        ),
        directions=["positive"],
        now=NOW + timedelta(hours=1),
    )
    assert delta.change_type == "trajectory_strengthening"
    assert delta.trajectory == "STRENGTHENING"
    assert delta.is_meaningful is True
    assert delta.change_type != "new_opportunity"
    assert delta.previous_state == first.new_state  # lifecycle_state itself untouched


# --- Contradictory evidence can weaken/reverse trajectory ---------------


def test_contradictory_evidence_reverses_trajectory():
    tracker = _tracker()
    _observe(
        tracker,
        evidence=_evidence(
            price=100.0, change_pct=2.0, market_change_pct=0.0
        ),  # relative=+2 (confirming)
        directions=["positive"],
    )
    delta = _observe(
        tracker,
        evidence=_evidence(
            price=97.0, change_pct=-3.0, market_change_pct=0.0
        ),  # relative=-3 (contradicting)
        directions=["positive"],
        now=NOW + timedelta(hours=1),
    )
    assert delta.trajectory == "REVERSING"
    assert delta.change_type == "trajectory_reversing"
    assert (
        delta.is_notification_worthy is True
    )  # reversal matches confidence_increased's precedent


# --- Objective trajectory is identical for different users --------------


def test_trajectory_is_identical_regardless_of_which_user_polls():
    tracker = _tracker()
    _observe(
        tracker,
        evidence=_evidence(price=100.0, change_pct=0.0, market_change_pct=0.0),
        directions=["positive"],
    )

    delta_user_a = tracker.observe(
        entity_id="NVDA",
        confidence_score=0.6,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.9,  # very high personal relevance for user A
        now=NOW + timedelta(hours=1),
        market_evidence=_evidence(price=103.0, change_pct=3.0, market_change_pct=0.0),
        trigger_directions=["positive"],
    )
    # Reset a fresh tracker so user B's poll doesn't inherit user A's prior
    # write of the same entity's shared snapshot -- but the SAME shared
    # snapshot must already reflect the identical objective trajectory
    # user B (personal_relevance=0.1) would also see.
    delta_user_b = tracker.observe(
        entity_id="NVDA",
        confidence_score=0.6,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-b",
        personal_relevance=0.1,  # very low personal relevance for user B
        now=NOW + timedelta(hours=1, minutes=1),
        market_evidence=_evidence(price=103.0, change_pct=3.0, market_change_pct=0.0),
        trigger_directions=["positive"],
    )
    assert delta_user_a.trajectory == delta_user_b.trajectory == "STRENGTHENING"
    assert delta_user_a.evidence is not None
    assert delta_user_b.evidence is not None
    assert (
        delta_user_a.evidence.relative_to_market_pct
        == delta_user_b.evidence.relative_to_market_pct
    )


def test_personal_relevance_alone_never_moves_trajectory():
    tracker = _tracker()
    _observe(
        tracker,
        evidence=_evidence(price=100.0, change_pct=0.0, market_change_pct=0.0),
        directions=["positive"],
    )
    delta = tracker.observe(
        entity_id="NVDA",
        confidence_score=0.6,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.9,  # crosses PERSONAL_RELEVANCE_THRESHOLD
        now=NOW + timedelta(hours=1),
        market_evidence=_evidence(
            price=100.0, change_pct=0.0, market_change_pct=0.0
        ),  # unchanged
        trigger_directions=["positive"],
    )
    assert delta.change_type == "personal_relevance_increased"
    assert delta.trajectory == "STEADY"  # unaffected by personal relevance


# --- Mixed/absent thesis direction takes no directional stance ----------


def test_mixed_trigger_directions_holds_trajectory_steady():
    tracker = _tracker()
    _observe(
        tracker,
        evidence=_evidence(price=100.0, change_pct=0.0, market_change_pct=0.0),
        directions=["positive", "negative"],
    )
    delta = _observe(
        tracker,
        evidence=_evidence(price=110.0, change_pct=10.0, market_change_pct=0.0),
        directions=["positive", "negative"],
        now=NOW + timedelta(hours=1),
    )
    assert delta.trajectory == "STEADY"
    assert delta.change_type == "none"


# --- No market evidence at all: byte-for-byte V2/V2.1 behavior ----------


def test_no_market_evidence_leaves_trajectory_and_evidence_inert():
    tracker = _tracker()
    delta = tracker.observe(
        entity_id="NVDA",
        confidence_score=0.6,
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        user_id="user-a",
        personal_relevance=0.6,
        now=NOW,
    )
    assert delta.trajectory == "STEADY"
    assert delta.previous_trajectory == "STEADY"
    assert delta.evidence is None
    assert delta.trajectory_reason is None
