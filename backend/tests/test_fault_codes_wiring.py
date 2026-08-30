"""Operational Beta Hardening Block 1 -- proves each backend/app call site
that wires into logan_core.diagnostics.record_fault() actually fires with
the right code, on the right condition, without changing any existing
control flow (a caught fault is always still raised/returned exactly as
before -- record_fault() is purely additive observability). The framework's
own unit tests live in logan_core/tests/test_diagnostics_fault_codes.py.
"""

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from backend.app import ask_engine, user_context, watch
from backend.app.ask_llm_provider import AskLlmProviderError
from backend.app.user_context import AccountLinkConflictError, link_account
from logan_core.diagnostics import recent_faults, reset_fault_state


def setup_function() -> None:
    reset_fault_state()
    watch.reset_watch_state()


# --- AUTH-100 (user_context._verify_bearer_header) --------------------------


def test_malformed_bearer_header_records_auth_100():
    with pytest.raises(HTTPException):
        user_context._verify_bearer_header("not-a-bearer-token")
    faults = recent_faults()
    assert any(f.code == "AUTH-100" for f in faults)
    assert faults[-1].subsystem == "user_context"


def test_clerk_not_configured_records_auth_100(monkeypatch):
    monkeypatch.setattr(user_context, "clerk_configured", lambda: False)
    with pytest.raises(HTTPException):
        user_context._verify_bearer_header("Bearer sometoken")
    assert any(f.code == "AUTH-100" for f in recent_faults())


def test_invalid_session_records_auth_100(monkeypatch):
    monkeypatch.setattr(user_context, "clerk_configured", lambda: True)
    monkeypatch.setattr(user_context, "verify_clerk_session_token", lambda token: None)
    with pytest.raises(HTTPException):
        user_context._verify_bearer_header("Bearer sometoken")
    assert any(f.code == "AUTH-100" for f in recent_faults())


def test_auth_100_context_never_carries_the_raw_token():
    with pytest.raises(HTTPException):
        user_context._verify_bearer_header("Bearer super-secret-session-token")
    for fault in recent_faults():
        assert "super-secret-session-token" not in str(fault.safe_context)


# --- AUTH-101 (user_context.link_account) ------------------------------------


def test_reserved_identity_link_records_auth_101():
    from logan_core.contracts import LOCAL_FOUNDER_USER_ID

    with pytest.raises(AccountLinkConflictError):
        link_account("clerk", "some-external-subject", LOCAL_FOUNDER_USER_ID)
    faults = recent_faults()
    assert any(f.code == "AUTH-101" for f in faults)
    assert faults[-1].subsystem == "account_link"


def test_cross_identity_conflict_records_auth_101():
    link_account("clerk", "external-subject-a", "anon-user-1")
    with pytest.raises(AccountLinkConflictError):
        link_account("clerk", "external-subject-b", "anon-user-1")
    assert any(f.code == "AUTH-101" for f in recent_faults())


# --- ASK-400 (ask_engine) ----------------------------------------------------


def test_get_ask_llm_provider_construction_failure_records_ask_400(monkeypatch):
    import backend.app.ask_llm_anthropic as anthropic_module
    from backend.app import config as config_module

    ask_engine.reset_ask_llm_provider()
    monkeypatch.setattr(config_module, "llm_ask_enabled", lambda: True)

    def _raising_constructor(*args, **kwargs):
        raise AskLlmProviderError("construction failed")

    monkeypatch.setattr(
        anthropic_module, "AnthropicAskLlmProvider", _raising_constructor
    )

    ask_engine.get_ask_llm_provider()
    assert any(f.code == "ASK-400" for f in recent_faults())
    ask_engine.reset_ask_llm_provider()


def test_generate_grounded_answer_provider_failure_records_ask_400():
    from uuid import uuid4

    from backend.app.ask_context import OpportunityContext

    class _FailingProvider:
        def generate(self, context, message, history):
            raise AskLlmProviderError("timeout")

    context = OpportunityContext(
        event_id=uuid4(),
        entity_id="AAPL",
        display_name="Apple",
        domain="stocks",
        headline="Apple: earnings signal",
        what_happened="Apple reported results.",
        why_it_matters="Notable move.",
        why_it_matters_to_me="You hold this.",
        why_now="Timely.",
        confidence_score=0.6,
        confidence_label="Moderate",
        classification="inference",
        limiting_factors=[],
        alternatives=[],
        trigger_codes=[],
        convergence_sources=[],
        personal_relevance=0.6,
        connection_basis="explicit",
        is_new_for_user=False,
    )
    ask_engine.generate_grounded_answer(context, "why?", _FailingProvider(), history=())
    assert any(f.code == "ASK-400" for f in recent_faults())


# --- WATCH-500 (watch.py, only reachable when persistence is enabled) -------


def test_create_watch_store_failure_records_watch_500_and_still_raises(monkeypatch):
    monkeypatch.setattr(watch, "memory_persistence_enabled", lambda: True)

    class _FailingStore:
        def load_all(self):
            return []

        def save(self, w):
            raise RuntimeError("disk full")

    monkeypatch.setattr(watch, "_get_store", lambda: _FailingStore())

    with pytest.raises(RuntimeError):
        watch.create_watch("user-1", "AAPL")
    faults = recent_faults()
    assert any(f.code == "WATCH-500" for f in faults)


def test_remove_watch_store_failure_records_watch_500_and_still_raises(monkeypatch):
    watch._watches[("user-1", "AAPL")] = watch.Watch(
        user_id="user-1",
        entity_id="AAPL",
        created_at=datetime.now(timezone.utc),
    )

    class _FailingStore:
        def load_all(self):
            return []

        def delete(self, user_id, entity_id):
            raise RuntimeError("disk full")

    monkeypatch.setattr(watch, "_get_store", lambda: _FailingStore())

    with pytest.raises(RuntimeError):
        watch.remove_watch("user-1", "AAPL")
    assert any(f.code == "WATCH-500" for f in recent_faults())
