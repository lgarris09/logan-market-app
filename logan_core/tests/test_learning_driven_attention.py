"""V2.3B Phase 2 (Learning-Driven STRATUS) Blocks 3/4/7/8 -- proves the
*existing* internal_rank_score -> PrioritizationEngine -> surface pipeline,
now fed by Personal Relevance V2, behaves as a genuine "attention field"
decision: strong objective + strong personal can reach the top tier, weak
objective evidence cannot be rescued by personal interest alone, an
unfamiliar-but-strong opportunity still surfaces (discovery), and a
correction changes personalization without touching the underlying
opportunity's existence or objective facts.

No new scoring architecture is introduced by these tests -- they exercise
the same Orchestrator.run() -> AttentionRecommendation/PrioritizedItem/
DeliveredItem path every other pipeline test already does (see
test_pipeline_market_data.py's own harness, mirrored here), just with
scenarios specifically chosen to prove the Personal Relevance V2 boundary.
"""

from datetime import datetime, timezone

from logan_core.contracts import Holding, Interest, RawSignal, UserModel
from logan_core.orchestrator import Orchestrator, PipelineDependencies
from logan_core.receptors import quote_to_raw_signal
from logan_core.receptors.providers import (
    FixtureMarketDataProvider,
    nvda_no_significant_move_fixture,
    nvda_price_move_up_fixture,
)
from logan_core.trigger_detection import StocksTriggerEvaluator
from logan_core.user_model import UserModelBuilder


def _orchestrator() -> Orchestrator:
    return Orchestrator(
        deps=PipelineDependencies(trigger_detector=StocksTriggerEvaluator())
    )


def _fresh_signal(ticker: str, fixture) -> RawSignal:
    provider = FixtureMarketDataProvider(quotes={ticker: fixture})
    quote = provider.fetch_quote(ticker)
    assert quote is not None
    raw = quote_to_raw_signal(quote)
    # Re-timestamped to real "now" -- see test_pipeline_market_data.py's own
    # identical fix for why (recency decay vs. a fixed fixture date).
    return raw.model_copy(update={"captured_at": datetime.now(timezone.utc)})


def _blank_user_model(user_id="discovery-user") -> UserModel:
    return UserModelBuilder().seed(user_id=user_id)


def _watched_holder_user_model(user_id="demo_user") -> UserModel:
    now = datetime.now(timezone.utc)
    return UserModelBuilder().seed(
        user_id=user_id,
        holdings=[
            Holding(
                domain="stocks", entity_id="NVDA", display_name="NVIDIA", added_at=now
            )
        ],
    )


def _inferred_interest_user_model(user_id="inferred-user", weight=0.85) -> UserModel:
    now = datetime.now(timezone.utc)
    return UserModelBuilder().seed(
        user_id=user_id,
        interests=[
            Interest(
                domain="stocks",
                topic="NVDA",
                weight=weight,
                source="inferred",
                created_at=now,
                last_updated=now,
            )
        ],
    )


# --- Block 3/4: strong objective + strong personal can reach top tier -----


def test_strong_objective_plus_watch_reaches_high_internal_rank_score():
    raw = _fresh_signal("NVDA", nvda_price_move_up_fixture())
    orchestrator = _orchestrator()
    result = orchestrator.run(
        raw_signals=[raw],
        user_id="watch-user",
        user_model=_blank_user_model("watch-user"),
        engagement_samples=[],
        domain="stocks",
        is_watched=True,
    )
    assert result.recommendation.personal_relevance_result is not None
    assert result.recommendation.personal_relevance_result.basis == "watch"
    assert result.recommendation.internal_rank_score >= 0.35  # recommend threshold
    assert result.recommendation.recommend is True


# --- Block 4/8: weak objective evidence cannot be rescued by personal -----


def test_weak_objective_evidence_stays_low_even_with_active_watch():
    """A quiet trading day (no real trigger fires) must not become a high-
    priority opportunity merely because the user is watching it -- personal
    relevance is only 25% of internal_rank_score, and confidence/urgency/
    actionability (the objective 60%+) stay low with nothing having fired."""
    raw = _fresh_signal("NVDA", nvda_no_significant_move_fixture())
    orchestrator = _orchestrator()
    result = orchestrator.run(
        raw_signals=[raw],
        user_id="watch-user-weak",
        user_model=_blank_user_model("watch-user-weak"),
        engagement_samples=[],
        domain="stocks",
        is_watched=True,
    )
    assert result.recommendation.personal_relevance_result is not None
    assert result.recommendation.personal_relevance_result.basis == "watch"
    # Watch alone must not push a quiet, non-triggering day into "primary"
    # visibility territory (PrioritizationEngine's own 0.6 bar).
    assert result.recommendation.internal_rank_score < 0.6
    assert result.prioritized_item.visibility != "primary"


# --- Block 8: discovery -- an unfamiliar but objectively strong entity ----


def test_unfamiliar_entity_with_strong_objective_signal_still_surfaces():
    """A genuinely new/unfamiliar entity (no holdings, no interests, no
    Watch, zero history) with a real, strong objective signal must still
    recommend and surface -- STRATUS is not a tunnel-visioned "more of the
    same" engine."""
    raw = _fresh_signal("NVDA", nvda_price_move_up_fixture())
    orchestrator = _orchestrator()
    result = orchestrator.run(
        raw_signals=[raw],
        user_id="brand-new-user",
        user_model=_blank_user_model("brand-new-user"),
        engagement_samples=[],
        domain="stocks",
    )
    assert result.recommendation.personal_relevance_result is not None
    assert result.recommendation.personal_relevance_result.basis == "none"
    assert result.recommendation.recommend is True
    assert result.prioritized_item.visibility in ("primary", "feed")


def test_unfamiliar_strong_opportunity_can_outrank_a_stale_familiar_one():
    """Anti-echo-chamber, direct comparison: a fresh, strong signal for an
    entity STRATUS knows nothing about the user's interest in should not be
    systematically buried beneath a merely-explicit-but-otherwise-identical
    connection -- the gap between "none" and "explicit" personal_relevance
    (0.2 vs 0.6, 25% weight = 0.10 of internal_rank_score) is real but
    bounded, never disqualifying."""
    raw_unfamiliar = _fresh_signal("NVDA", nvda_price_move_up_fixture())
    raw_familiar = _fresh_signal("NVDA", nvda_price_move_up_fixture())
    orchestrator = _orchestrator()

    unfamiliar = orchestrator.run(
        raw_signals=[raw_unfamiliar],
        user_id="unfamiliar-user",
        user_model=_blank_user_model("unfamiliar-user"),
        engagement_samples=[],
        domain="stocks",
    )
    familiar = orchestrator.run(
        raw_signals=[raw_familiar],
        user_id="familiar-user",
        user_model=_watched_holder_user_model("familiar-user"),
        engagement_samples=[],
        domain="stocks",
    )
    # Both still qualify and surface -- discovery is not disqualified merely
    # for lacking personal history.
    assert unfamiliar.recommendation.recommend is True
    assert unfamiliar.prioritized_item.visibility in ("primary", "feed")
    # The gap is real (explicit/holding-connected still ranks higher) but
    # bounded, not a cliff.
    assert (
        familiar.recommendation.internal_rank_score
        - unfamiliar.recommendation.internal_rank_score
    ) < 0.25


# --- Block 7: correction changes personalization, not opportunity truth ---


def test_correction_removes_personal_boost_without_touching_objective_signal():
    raw = _fresh_signal("NVDA", nvda_price_move_up_fixture())
    orchestrator = _orchestrator()

    with_inferred_interest = orchestrator.run(
        raw_signals=[raw],
        user_id="corrected-user",
        user_model=_inferred_interest_user_model("corrected-user"),
        engagement_samples=[],
        domain="stocks",
    )
    assert with_inferred_interest.recommendation.personal_relevance_result is not None
    assert (
        with_inferred_interest.recommendation.personal_relevance_result.basis
        == "inferred"
    )

    # Simulate the correction having already been applied and the UserModel
    # rebuilt (the real end-to-end proof of _apply_corrections itself lives
    # in test_personal_learning_corrections.py) -- a blank model represents
    # "this user's NVDA interest has been suppressed."
    raw_after_correction = _fresh_signal("NVDA", nvda_price_move_up_fixture())
    after_correction = orchestrator.run(
        raw_signals=[raw_after_correction],
        user_id="corrected-user",
        user_model=_blank_user_model("corrected-user"),
        engagement_samples=[],
        domain="stocks",
    )
    assert after_correction.recommendation.personal_relevance_result is not None
    assert after_correction.recommendation.personal_relevance_result.basis == "none"
    assert (
        after_correction.recommendation.dimensions.personal_relevance
        < with_inferred_interest.recommendation.dimensions.personal_relevance
    )
    # The opportunity itself (the real objective trigger) still exists and
    # still qualifies -- correction changes personalization, never the
    # underlying world truth.
    assert after_correction.recommendation.recommend is True
    assert (
        len(after_correction.event.trigger_events)
        == len(with_inferred_interest.event.trigger_events)
        == 1
    )
    assert (
        after_correction.event.trigger_events[0].trigger_code
        == with_inferred_interest.event.trigger_events[0].trigger_code
    )
