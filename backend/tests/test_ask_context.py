"""Sprint 3.6.7 Block 4 -- OpportunityContext rehydration and cache
(backend/app/ask_context.py). Builds a real PipelineResult through the full,
unmodified logan_core pipeline and proves the context snapshot faithfully
reflects it -- never internal-only fields (ADR-029).
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from backend.app.ask_context import OpportunityContextCache, build_opportunity_context
from logan_core.community_intelligence import EngagementSample
from logan_core.contracts import Holding
from logan_core.convergence import (
    STOCK_CONVERGENCE_MULTI_SOURCE,
    StockConvergenceTracker,
)
from logan_core.orchestrator import Orchestrator, PipelineDependencies
from logan_core.receptors import earnings_report_to_raw_signal
from logan_core.receptors.providers import nvda_earnings_beat_fixture
from logan_core.trigger_detection import StocksTriggerEvaluator
from logan_core.trigger_detection.stocks import STOCK_EARNINGS_BEAT
from logan_core.user_model import UserModelBuilder


@pytest.fixture
def now():
    return datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def user_model(now):
    return UserModelBuilder().seed(
        user_id="demo_user",
        holdings=[
            Holding(
                domain="stocks", entity_id="NVDA", display_name="NVIDIA", added_at=now
            )
        ],
        risk_tolerance="moderate",
    )


@pytest.fixture
def engagement_samples(now):
    return [
        EngagementSample(
            observed_at=now,
            volume_at_point=10,
            unique_users=8,
            saves_shares=1,
            questions=0,
        ),
        EngagementSample(
            observed_at=now,
            volume_at_point=40,
            unique_users=30,
            saves_shares=6,
            questions=3,
        ),
    ]


def _nvda_result(user_model, engagement_samples):
    deps = PipelineDependencies(
        trigger_detector=StocksTriggerEvaluator(),
        convergence_tracker=StockConvergenceTracker(),
    )
    orchestrator = Orchestrator(deps=deps)
    raw = earnings_report_to_raw_signal(nvda_earnings_beat_fixture())
    return orchestrator.run(
        raw_signals=[raw],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )


def test_build_opportunity_context_reflects_real_pipeline_output(
    user_model, engagement_samples
):
    result = _nvda_result(user_model, engagement_samples)
    context = build_opportunity_context(
        entity_id="NVDA",
        display_name="NVIDIA",
        result=result,
        is_new_for_user=True,
    )

    assert context.event_id == result.event.event_id
    assert context.entity_id == "NVDA"
    assert context.display_name == "NVIDIA"
    assert context.domain == "stocks"
    assert context.headline == result.delivered_item.headline
    assert context.what_happened == result.delivered_item.what_happened
    assert context.confidence_score == result.confidence.confidence_score
    assert context.confidence_label == result.delivered_item.confidence_label
    assert context.classification == result.confidence.classification
    assert context.limiting_factors == result.confidence.limiting_factors
    assert STOCK_EARNINGS_BEAT in context.trigger_codes
    assert context.is_new_for_user is True


def test_convergence_sources_empty_when_convergence_did_not_fire(
    user_model, engagement_samples
):
    result = _nvda_result(user_model, engagement_samples)
    context = build_opportunity_context(
        entity_id="NVDA", display_name="NVIDIA", result=result, is_new_for_user=False
    )
    assert STOCK_CONVERGENCE_MULTI_SOURCE not in context.trigger_codes
    assert context.convergence_sources == []


def test_connection_basis_reflects_explicit_holding(user_model, engagement_samples):
    """conftest's user_model fixture holds NVDA explicitly."""
    result = _nvda_result(user_model, engagement_samples)
    context = build_opportunity_context(
        entity_id="NVDA", display_name="NVIDIA", result=result, is_new_for_user=False
    )
    assert context.connection_basis == "explicit"


def test_context_never_exposes_internal_rank_score():
    """ADR-029: internal_rank_score must never reach any public surface --
    OpportunityContext's own field set is the check here (not just string
    matching serialized output)."""
    from backend.app.ask_context import OpportunityContext

    assert "internal_rank_score" not in OpportunityContext.model_fields
    assert "rank_score" not in OpportunityContext.model_fields


# --- OpportunityContextCache ------------------------------------------


def test_cache_returns_none_for_an_unknown_event_id():
    cache = OpportunityContextCache()
    assert cache.get(uuid4()) is None


def test_cache_replace_all_replaces_wholesale_not_merges(
    user_model, engagement_samples
):
    result = _nvda_result(user_model, engagement_samples)
    context = build_opportunity_context(
        entity_id="NVDA", display_name="NVIDIA", result=result, is_new_for_user=False
    )
    cache = OpportunityContextCache()
    cache.replace_all([context])
    assert cache.get(context.event_id) is context

    # A second replace_all with a different set must drop the first entirely.
    other_result = _nvda_result(user_model, engagement_samples)
    other_context = build_opportunity_context(
        entity_id="NVDA",
        display_name="NVIDIA",
        result=other_result,
        is_new_for_user=False,
    )
    cache.replace_all([other_context])
    assert cache.get(other_context.event_id) is other_context
    if context.event_id != other_context.event_id:
        assert cache.get(context.event_id) is None


# --- Cross-block provenance: Block 2 convergence -> Block 4 grounded answer


def test_convergence_provenance_survives_into_opportunity_context(
    user_model, engagement_samples, now
):
    """Full-path integration check (Sprint 3.6.7 Block 4 integration-
    hardening pass): three genuinely distinct signal types converging
    (Block 2) must show up as real convergence_sources on the resulting
    OpportunityContext, not just on the raw EnrichedEvent -- proving
    provenance survives Block 2's coherent-opportunity merge all the way
    through to what Ask STRATUS (Block 4) can ground an answer in.
    """
    from logan_core.receptors import grade_change_to_raw_signal, quote_to_raw_signal
    from logan_core.receptors.providers import (
        FixtureMarketDataProvider,
        nvda_analyst_upgrade_fixture,
        nvda_price_move_up_fixture,
    )

    deps = PipelineDependencies(
        trigger_detector=StocksTriggerEvaluator(),
        convergence_tracker=StockConvergenceTracker(),
    )
    orchestrator = Orchestrator(deps=deps)

    earnings = earnings_report_to_raw_signal(nvda_earnings_beat_fixture())
    earnings = earnings.model_copy(update={"captured_at": now})

    provider = FixtureMarketDataProvider(
        quotes={"NVDA": nvda_price_move_up_fixture()},
        grade_changes={"NVDA": nvda_analyst_upgrade_fixture()},
    )
    quote = provider.fetch_quote("NVDA")
    assert quote is not None
    price = quote_to_raw_signal(quote).model_copy(
        update={"captured_at": now + timedelta(minutes=1)}
    )
    grade_change = provider.fetch_latest_grade_change("NVDA")
    assert grade_change is not None
    grade = grade_change_to_raw_signal(grade_change).model_copy(
        update={"captured_at": now + timedelta(minutes=2)}
    )

    result = orchestrator.run(
        raw_signals=[earnings, price, grade],
        user_id="demo_user",
        user_model=user_model,
        engagement_samples=engagement_samples,
        domain="stocks",
    )

    context = build_opportunity_context(
        entity_id="NVDA", display_name="NVIDIA", result=result, is_new_for_user=False
    )

    assert STOCK_CONVERGENCE_MULTI_SOURCE in context.trigger_codes
    assert set(context.convergence_sources) == {
        "earnings_signal",
        "price_change",
        "analyst_change",
    }

    from backend.app.ask_engine import answer_question

    answer = answer_question(context, "Are multiple signals converging here?")
    assert "yes" in answer.lower()
    assert "earnings_signal" in answer
