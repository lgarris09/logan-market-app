"""Sprint 3.6.7 Block 4 -- deterministic grounded-answer classification
(backend/app/ask_engine.py). Pure unit tests: no orchestrator, no HTTP, no
network -- just OpportunityContext -> answer_question() -> real, grounded
text.
"""

from uuid import uuid4

from backend.app.ask_context import OpportunityContext
from backend.app.ask_engine import answer_question


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
        limiting_factors=["Only one independent source has corroborated this so far."],
        alternatives=[],
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        convergence_sources=[],
        personal_relevance=0.6,
        connection_basis="explicit",
        is_new_for_user=False,
    )
    defaults.update(overrides)
    return OpportunityContext(**defaults)


def test_what_changed_returns_what_happened():
    context = _context()
    answer = answer_question(context, "What changed here?")
    assert context.what_happened in answer


def test_why_now_returns_why_now_field():
    context = _context()
    answer = answer_question(context, "Why does this matter right now?")
    assert context.why_now in answer


def test_why_matters_returns_why_it_matters_field():
    context = _context()
    answer = answer_question(context, "Why does this matter?")
    assert context.why_it_matters in answer


def test_personal_relevance_question_uses_why_it_matters_to_me():
    context = _context(connection_basis="explicit")
    answer = answer_question(context, "Why does this matter to me personally?")
    assert context.why_it_matters_to_me in answer
    assert "explicit" in answer.lower()


def test_personal_relevance_question_notes_inferred_basis():
    context = _context(connection_basis="inferred", personal_relevance=0.55)
    answer = answer_question(context, "Is this relevant to me?")
    assert "0.55" not in answer
    assert "past engagement" in answer.lower()


def test_confidence_question_reports_label_not_raw_score():
    context = _context(confidence_score=0.72, confidence_label="Moderate")
    answer = answer_question(context, "How confident are you in this?")
    assert "0.72" not in answer
    assert "moderate" in answer.lower()


def test_confidence_question_includes_limiting_factors():
    context = _context(
        limiting_factors=["Only one independent source has corroborated this so far."]
    )
    answer = answer_question(context, "How sure are you?")
    assert "corroborated" in answer.lower()


def test_limiting_factors_question_returns_real_limiting_factors():
    context = _context(limiting_factors=["Some expected event details are missing."])
    answer = answer_question(context, "What would make this less interesting?")
    assert "missing" in answer.lower()


def test_limiting_factors_question_with_none_is_honest_not_fabricated():
    context = _context(limiting_factors=[], alternatives=[])
    answer = answer_question(context, "What would weaken this?")
    assert "nothing currently limits" in answer.lower()


def test_which_signals_question_lists_real_trigger_codes():
    context = _context(
        trigger_codes=["STOCK_EARNINGS_BEAT", "STOCK_PRICE_MOVE_SIGNIFICANT"]
    )
    answer = answer_question(context, "Which signals are driving this?")
    assert "earnings beat" in answer.lower()
    assert "price move" in answer.lower()


def test_which_signals_question_with_no_triggers_is_honest():
    context = _context(trigger_codes=[])
    answer = answer_question(context, "What signal is behind this?")
    assert "hasn't crossed" in answer.lower() or "general context" in answer.lower()


def test_convergence_question_reports_real_sources_when_present():
    context = _context(
        trigger_codes=[
            "STOCK_EARNINGS_BEAT",
            "STOCK_PRICE_MOVE_SIGNIFICANT",
            "STOCK_ANALYST_UPGRADE",
            "STOCK_CONVERGENCE_MULTI_SOURCE",
        ],
        convergence_sources=["earnings_signal", "price_change", "analyst_change"],
    )
    answer = answer_question(context, "Are multiple signals converging here?")
    assert "yes" in answer.lower()
    assert "earnings_signal" in answer
    assert "3" in answer


def test_convergence_question_is_honest_when_not_converging():
    context = _context(trigger_codes=["STOCK_EARNINGS_BEAT"], convergence_sources=[])
    answer = answer_question(context, "Is this converging with other signals?")
    assert (
        "no" in answer.lower() or "isn't a multi-signal convergence" in answer.lower()
    )
    assert "30-minute" in answer


def test_compare_signals_question_names_all_real_triggers():
    context = _context(trigger_codes=["STOCK_EARNINGS_BEAT", "STOCK_ANALYST_UPGRADE"])
    answer = answer_question(context, "Is this stronger than the earnings signal?")
    assert "earnings beat" in answer.lower()
    assert "analyst upgrade" in answer.lower()


def test_compare_question_with_single_signal_is_honest():
    context = _context(trigger_codes=["STOCK_EARNINGS_BEAT"])
    answer = answer_question(context, "Is this stronger than yesterday's move?")
    assert "only one real signal" in answer.lower()


def test_unrecognized_question_falls_back_to_overview_never_fabricates():
    context = _context()
    answer = answer_question(context, "asdkjfh qwoeiru random gibberish")
    assert context.headline in answer
    assert context.confidence_label.lower() in answer.lower()


def test_answer_never_mentions_internal_rank_score():
    """ADR-029: internal_rank_score must never reach any public surface,
    including a generated Ask STRATUS answer."""
    context = _context()
    for question in [
        "what changed",
        "why now",
        "how confident",
        "what would weaken this",
        "which signals",
        "converging",
        "stronger than",
        "random",
    ]:
        answer = answer_question(context, question)
        assert "internal_rank_score" not in answer
        assert "rank_score" not in answer


def test_no_answer_ever_states_a_raw_confidence_or_relevance_decimal():
    """2026-08-29 Ask STRATUS copy audit: device validation found raw
    decimals ("confidence 0.59", "personal relevance 0.20") leaking into
    consumer-facing answers. None of the deterministic answers should ever
    state one, for any routed question type."""
    context = _context(confidence_score=0.5950000373143596, personal_relevance=0.1987)
    for question in [
        "what changed",
        "why now",
        "why does this matter",
        "how confident are you",
        "is this relevant to me",
        "what would weaken this",
        "what would make this more important",
        "what could invalidate this",
        "what should i watch next",
        "which signals",
        "what evidence is strongest",
        "converging",
        "stronger than",
        "how is this different from last time",
        "random gibberish",
    ]:
        answer = answer_question(context, question)
        assert "0.59" not in answer
        assert "0.20" not in answer
        assert "0.1987" not in answer


# --- New question categories (2026-08-29: "make Ask materially smarter") --


def test_strengthen_answer_reframes_limiting_factors_positively():
    context = _context(
        limiting_factors=["Only one independent source has corroborated this so far."]
    )
    answer = answer_question(context, "What would make this more important?")
    assert "another independent source" in answer.lower()


def test_strengthen_answer_includes_alternatives_as_what_could_invalidate():
    context = _context(
        limiting_factors=["Some expected event details are missing."],
        alternatives=["This could also reflect noise, a single-source report."],
    )
    answer = answer_question(context, "What could invalidate this?")
    assert "noise" in answer.lower()


def test_strengthen_answer_with_no_limiting_factors_is_honest():
    context = _context(limiting_factors=[], alternatives=[])
    answer = answer_question(context, "What should I watch next?")
    assert "nothing currently limits" in answer.lower()


def test_evidence_quality_answer_names_strongest_and_weakest():
    context = _context(
        trigger_codes=["STOCK_EARNINGS_BEAT"],
        limiting_factors=["Only one independent source has corroborated this so far."],
    )
    answer = answer_question(context, "What evidence is strongest here?")
    assert "earnings beat" in answer.lower()
    assert "corroborated" in answer.lower()


def test_evidence_quality_answer_with_no_limiting_factors_is_honest():
    context = _context(trigger_codes=["STOCK_EARNINGS_BEAT"], limiting_factors=[])
    answer = answer_question(context, "What's the weakest evidence here?")
    assert "doesn't currently flag" in answer.lower()


def test_since_last_looked_answer_uses_sync_summary_when_present():
    context = _context(
        user_sync_status="UPDATED_SINCE_SEEN", sync_summary="Real sync summary text."
    )
    answer = answer_question(
        context, "How is this different from the last time I looked?"
    )
    assert answer == "Real sync summary text."


def test_since_last_looked_answer_falls_back_to_lifecycle_reason():
    context = _context(
        sync_summary=None, lifecycle_reason="Real lifecycle reason text."
    )
    answer = answer_question(context, "What's different since last time?")
    assert answer == "Real lifecycle reason text."


def test_since_last_looked_answer_falls_back_to_what_happened_when_nothing_tracked():
    context = _context(sync_summary=None, lifecycle_reason=None)
    answer = answer_question(context, "How is this different from before?")
    assert answer == context.what_happened
