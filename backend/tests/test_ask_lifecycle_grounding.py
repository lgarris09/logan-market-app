"""Stock Opportunity Logic V2 -- LLM-assisted delta-aware interpretation.

Proves the grounding contract, not model behavior (no real network call
here -- see test_ask_llm.py's own discipline): the lifecycle fields a real
LifecycleDelta produces are (1) genuinely threaded through
build_opportunity_context() into OpportunityContext, (2) genuinely rendered
into the system prompt build_system_prompt() sends the model, and (3) the
prompt explicitly instructs the model to prefer a delta-oriented answer and
never invent a change beyond what these authoritative fields state. The
deterministic OpportunityLifecycleTracker remains the sole source of these
values -- the LLM only ever narrates a delta it was already handed.
"""

from typing import Callable
from uuid import uuid4

import httpx

from backend.app.ask_context import OpportunityContext
from backend.app.ask_llm_fixture import FixtureAskLlmProvider
from backend.app.ask_llm_provider import build_system_prompt
from backend.app.logan_feed import reset_pipeline_state, run_demo_feed
from logan_core.contracts import LOCAL_FOUNDER_USER_ID
from logan_core.receptors.providers import FmpEarningsProvider, FmpMarketDataProvider


def _context(**overrides) -> OpportunityContext:
    defaults = dict(
        event_id=uuid4(),
        entity_id="NVDA",
        display_name="NVIDIA",
        domain="stocks",
        headline="NVIDIA: earnings signal",
        what_happened="NVIDIA reported EPS of 1.87 vs. consensus 1.76",
        why_it_matters="This is a strong earnings beat.",
        why_it_matters_to_me="You're tracking a holding connected to NVDA.",
        why_now="This is moving quickly enough to flag right now.",
        confidence_score=0.72,
        confidence_label="Moderate",
        classification="inference",
        limiting_factors=[],
        alternatives=[],
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        convergence_sources=[],
        personal_relevance=0.6,
        connection_basis="explicit",
        is_new_for_user=False,
    )
    defaults.update(overrides)
    return OpportunityContext(**defaults)


# --- build_system_prompt: lifecycle section presence -----------------------


def test_system_prompt_omits_lifecycle_section_when_not_tracked():
    context = _context()  # lifecycle_state defaults to None
    prompt = build_system_prompt(context)
    assert "Lifecycle state:" not in prompt


def test_system_prompt_includes_lifecycle_section_when_tracked():
    context = _context(
        lifecycle_state="cooling",
        meaningful_change_type="aged_to_cooling",
        lifecycle_reason="No new evidence since the original signal.",
        thesis_age_hours=80.5,
        is_meaningful_update=True,
    )
    prompt = build_system_prompt(context)
    assert "Lifecycle state: cooling" in prompt
    assert "aged_to_cooling" in prompt
    assert "No new evidence since the original signal." in prompt
    assert "80.5" in prompt


def test_system_prompt_instructs_delta_oriented_answer_not_restating_card():
    context = _context(
        lifecycle_state="monitoring",
        meaningful_change_type="none",
        lifecycle_reason="No material change -- STRATUS is still monitoring.",
        thesis_age_hours=10.0,
        is_meaningful_update=False,
    )
    prompt = build_system_prompt(context)
    assert "delta-oriented answer" in prompt
    assert (
        "never invent a change" in prompt.lower() or "never invent a change" in prompt
    )


def test_system_prompt_never_fabricates_a_change_type_beyond_context():
    """The model is only ever given whatever change_type the deterministic
    tracker actually computed -- there is no path for the prompt itself to
    introduce a different one."""
    context = _context(
        lifecycle_state="high_attention",
        meaningful_change_type="convergence_formed",
        lifecycle_reason="Multiple independent signals have now converged.",
        thesis_age_hours=2.0,
        is_meaningful_update=True,
    )
    prompt = build_system_prompt(context)
    assert "convergence_formed" in prompt
    assert "confidence_increased" not in prompt
    assert "aged_to_stale" not in prompt


# --- End-to-end: real pipeline lifecycle delta reaches the LLM call --------


def _entries_for(by_symbol: dict) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        symbol = request.url.params.get("symbol")
        return httpx.Response(200, json=by_symbol.get(symbol, []))

    return handler


def test_real_pipeline_lifecycle_delta_reaches_the_llm_provider_call(monkeypatch):
    """Full vertical proof: a real pipeline run's LifecycleDelta ends up on
    the OpportunityContext the LLM provider actually receives -- not a
    hand-built test double standing in for the real wiring."""
    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", "NVDA")
    monkeypatch.delenv("STRATUS_LIVE_NVDA_EARNINGS", raising=False)
    monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)
    earnings_entries = {
        "NVDA": [
            {
                "symbol": "NVDA",
                "date": "2026-05-20",
                "epsActual": 1.87,
                "epsEstimated": 1.76,
            }
        ]
    }
    transport = httpx.MockTransport(_entries_for(earnings_entries))
    client = httpx.Client(transport=transport)
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda *a, **kw: FmpEarningsProvider(
            api_key="test-key-not-real", client=client
        ),
    )
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        lambda *a, **kw: FmpMarketDataProvider(
            api_key="test-key-not-real",
            client=httpx.Client(transport=httpx.MockTransport(_entries_for({}))),
        ),
    )
    reset_pipeline_state()

    from backend.app.logan_feed import get_opportunity_context

    first = run_demo_feed(LOCAL_FOUNDER_USER_ID)
    nvda_event_id = next(i.event_id for i in first.items if i.entity_id == "NVDA")
    context = get_opportunity_context(LOCAL_FOUNDER_USER_ID, nvda_event_id)
    assert context is not None
    assert context.lifecycle_state == "new"
    assert context.meaningful_change_type == "new_opportunity"

    provider = FixtureAskLlmProvider(answer="Fixture answer.")
    result = provider.generate(context, "What changed?")
    assert result.text == "Fixture answer."
    passed_context = provider.calls[0][0]
    assert passed_context.lifecycle_state == "new"
    assert passed_context.is_meaningful_update is True

    # Second, unchanged poll -- the SAME event_id's context should now
    # reflect a non-meaningful delta, proving the LLM would receive the
    # "no material change" framing rather than the original "new" one.
    second = run_demo_feed(LOCAL_FOUNDER_USER_ID)
    nvda_event_id_2 = next(i.event_id for i in second.items if i.entity_id == "NVDA")
    context_2 = get_opportunity_context(LOCAL_FOUNDER_USER_ID, nvda_event_id_2)
    assert context_2 is not None
    assert context_2.meaningful_change_type == "none"
    assert context_2.is_meaningful_update is False


# --- Stock Opportunity Logic V2.1 (User Sync Gap) -- sync-aware grounding --


def test_system_prompt_omits_sync_section_when_not_tracked():
    context = _context()  # user_sync_status defaults to None
    prompt = build_system_prompt(context)
    assert "User sync status:" not in prompt


def test_system_prompt_includes_sync_section_and_grounds_up_to_date():
    context = _context(
        current_revision=2,
        last_seen_revision=2,
        user_sync_status="UP_TO_DATE",
        sync_summary="This user has already seen the latest update -- nothing is new since they last looked.",
    )
    prompt = build_system_prompt(context)
    assert "User sync status: UP_TO_DATE" in prompt
    assert "already seen the latest update" in prompt
    assert "do not manufacture novelty" in prompt


def test_system_prompt_grounds_notified_but_unseen():
    context = _context(
        current_revision=1,
        user_sync_status="NOTIFIED_BUT_UNSEEN",
        sync_summary=(
            "STRATUS notified this user about revision 1, but they have not "
            "opened or seen it yet."
        ),
    )
    prompt = build_system_prompt(context)
    assert "NOTIFIED_BUT_UNSEEN" in prompt
    assert "notified this user about revision 1" in prompt


def test_real_pipeline_sync_status_reaches_the_llm_provider_call(monkeypatch):
    """Full vertical proof: a real UserSyncDelta computed from actual
    knowledge pointers ends up on the OpportunityContext the LLM provider
    receives -- proving "what changed since I last looked" can be answered
    from a real, authoritative field, not just the objective V2 delta."""
    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", "NVDA")
    monkeypatch.delenv("STRATUS_LIVE_NVDA_EARNINGS", raising=False)
    monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)
    earnings_entries = {
        "NVDA": [
            {
                "symbol": "NVDA",
                "date": "2026-05-20",
                "epsActual": 1.87,
                "epsEstimated": 1.76,
            }
        ]
    }
    transport = httpx.MockTransport(_entries_for(earnings_entries))
    client = httpx.Client(transport=transport)
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpEarningsProvider",
        lambda *a, **kw: FmpEarningsProvider(
            api_key="test-key-not-real", client=client
        ),
    )
    monkeypatch.setattr(
        "backend.app.logan_feed.FmpMarketDataProvider",
        lambda *a, **kw: FmpMarketDataProvider(
            api_key="test-key-not-real",
            client=httpx.Client(transport=httpx.MockTransport(_entries_for({}))),
        ),
    )
    reset_pipeline_state()

    from backend.app.logan_feed import get_opportunity_context, record_interaction

    first = run_demo_feed(LOCAL_FOUNDER_USER_ID)
    nvda_event_id = next(i.event_id for i in first.items if i.entity_id == "NVDA")
    context = get_opportunity_context(LOCAL_FOUNDER_USER_ID, nvda_event_id)
    assert context is not None
    assert context.user_sync_status == "NEW_TO_USER"  # never seen yet

    record_interaction(
        user_id=LOCAL_FOUNDER_USER_ID,
        event_id=nvda_event_id,
        entity_id="NVDA",
        domain="stocks",
        interaction_type="view",
        duration_ms=9000,
    )
    second = run_demo_feed(LOCAL_FOUNDER_USER_ID)
    nvda_event_id_2 = next(i.event_id for i in second.items if i.entity_id == "NVDA")
    context_2 = get_opportunity_context(LOCAL_FOUNDER_USER_ID, nvda_event_id_2)
    assert context_2 is not None
    assert context_2.user_sync_status == "UP_TO_DATE"

    provider = FixtureAskLlmProvider(
        answer="Nothing has changed since you last looked."
    )
    result = provider.generate(context_2, "What changed since yesterday?")
    assert result.text == "Nothing has changed since you last looked."
    passed_context = provider.calls[0][0]
    assert passed_context.user_sync_status == "UP_TO_DATE"
