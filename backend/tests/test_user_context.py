"""Sprint 3.6.9 -- Persistent Mobile Identity + Beta Security Boundary.

Closes a real information-disclosure exposure found while implementing
this block: `LOCAL_FOUNDER_USER_ID` resolves to the fixed, publicly-visible
string "demo_user" (logan_core/contracts/common.py), and because
`X-Stratus-User-Id` is entirely client-asserted, any caller of the hosted
API could set that header explicitly (or omit it) and receive the
founder's own real, personalized data. This file proves the fix: in
beta/production mode, the founder constant is never reachable via a
client-supplied header, neither by omission nor by explicit spoofing; demo/
development mode is provably unchanged.
"""

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.user_context import BETA_ANONYMOUS_USER_ID, resolve_user_id
from logan_core.contracts import LOCAL_FOUNDER_USER_ID

client = TestClient(app)


# --- Pure unit tests on resolve_user_id() directly --------------------------


def test_demo_mode_missing_header_resolves_to_founder_unchanged(monkeypatch):
    monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)
    assert resolve_user_id(x_stratus_user_id=None) == LOCAL_FOUNDER_USER_ID


def test_demo_mode_explicit_header_honored_as_is(monkeypatch):
    monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)
    assert resolve_user_id(x_stratus_user_id="some-real-device-id") == (
        "some-real-device-id"
    )


def test_demo_mode_explicit_founder_header_still_honored_unchanged(monkeypatch):
    """Exact pre-Sprint-3.6.9 behavior, preserved for local dev/tests that
    deliberately pass LOCAL_FOUNDER_USER_ID as a real header value (several
    existing tests do exactly this)."""
    monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)
    assert resolve_user_id(x_stratus_user_id=LOCAL_FOUNDER_USER_ID) == (
        LOCAL_FOUNDER_USER_ID
    )


def test_beta_mode_missing_header_does_not_resolve_to_founder(monkeypatch):
    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "beta")
    result = resolve_user_id(x_stratus_user_id=None)
    assert result != LOCAL_FOUNDER_USER_ID
    assert result == BETA_ANONYMOUS_USER_ID


def test_beta_mode_explicit_founder_spoof_does_not_resolve_to_founder(monkeypatch):
    """The sharper half of the real exposure this pass closes: previously,
    a caller only had to know the fixed, public string "demo_user" -- no
    guessing, no brute force -- to receive the founder's own real data."""
    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "beta")
    result = resolve_user_id(x_stratus_user_id=LOCAL_FOUNDER_USER_ID)
    assert result != LOCAL_FOUNDER_USER_ID
    assert result == BETA_ANONYMOUS_USER_ID


def test_beta_mode_blank_whitespace_header_does_not_resolve_to_founder(monkeypatch):
    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "beta")
    result = resolve_user_id(x_stratus_user_id="   ")
    assert result == BETA_ANONYMOUS_USER_ID


def test_beta_mode_real_device_id_honored_as_is(monkeypatch):
    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "beta")
    result = resolve_user_id(x_stratus_user_id="a1b2c3d4-real-mobile-install-id")
    assert result == "a1b2c3d4-real-mobile-install-id"


def test_production_mode_treated_identically_to_beta_mode(monkeypatch):
    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "production")
    assert resolve_user_id(x_stratus_user_id=None) == BETA_ANONYMOUS_USER_ID
    assert resolve_user_id(x_stratus_user_id=LOCAL_FOUNDER_USER_ID) == (
        BETA_ANONYMOUS_USER_ID
    )


def test_oversized_header_treated_as_absent_in_beta_mode(monkeypatch):
    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "beta")
    result = resolve_user_id(x_stratus_user_id="x" * 500)
    assert result == BETA_ANONYMOUS_USER_ID


def test_oversized_header_treated_as_absent_in_demo_mode(monkeypatch):
    monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)
    result = resolve_user_id(x_stratus_user_id="x" * 500)
    assert result == LOCAL_FOUNDER_USER_ID


def test_header_at_exactly_the_length_cap_is_still_honored(monkeypatch):
    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "beta")
    exactly_at_cap = "x" * 128
    assert resolve_user_id(x_stratus_user_id=exactly_at_cap) == exactly_at_cap


# --- End-to-end proof through a real route -----------------------------------


def test_beta_mode_spoofed_founder_header_never_gets_founder_seeding(monkeypatch):
    """Integration-level proof, not just the pure function: a real request
    to /v1/opportunities claiming to be the founder (via the exact
    pre-existing exploit -- an explicit X-Stratus-User-Id: demo_user header)
    must never receive founder-seeded personalization in beta mode."""
    from backend.app.logan_feed import (
        _get_orchestrator,
        _get_user_model,
        reset_pipeline_state,
    )

    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "beta")
    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", "")
    monkeypatch.delenv("STRATUS_LIVE_NVDA_EARNINGS", raising=False)
    reset_pipeline_state()

    response = client.get(
        "/v1/opportunities", headers={"X-Stratus-User-Id": LOCAL_FOUNDER_USER_ID}
    )
    assert response.status_code == 200

    orchestrator = _get_orchestrator()
    from datetime import datetime, timezone

    anonymous_model = _get_user_model(
        orchestrator, BETA_ANONYMOUS_USER_ID, datetime.now(timezone.utc)
    )
    # The founder-only seed (NVDA holding, AI_SECTOR interest) must never
    # appear on the anonymous bucket a spoofed/missing header resolves to.
    assert anonymous_model.holdings == []
    assert not any(i.topic == "AI_SECTOR" for i in anonymous_model.interests)


def test_beta_mode_missing_header_route_also_never_gets_founder_seeding(monkeypatch):
    from datetime import datetime, timezone

    from backend.app.logan_feed import (
        _get_orchestrator,
        _get_user_model,
        reset_pipeline_state,
    )

    monkeypatch.setenv("STRATUS_RUNTIME_MODE", "beta")
    monkeypatch.setenv("STRATUS_LIVE_STOCK_TICKERS", "")
    monkeypatch.delenv("STRATUS_LIVE_NVDA_EARNINGS", raising=False)
    reset_pipeline_state()

    response = client.get("/v1/opportunities")
    assert response.status_code == 200

    orchestrator = _get_orchestrator()
    anonymous_model = _get_user_model(
        orchestrator, BETA_ANONYMOUS_USER_ID, datetime.now(timezone.utc)
    )
    assert anonymous_model.holdings == []


def test_demo_mode_route_still_seeds_founder_when_header_omitted(monkeypatch):
    """The converse -- proves this fix is genuinely mode-scoped, not a
    blanket behavior change that would have broken every existing local/demo
    caller."""
    from datetime import datetime, timezone

    from backend.app.logan_feed import (
        _get_orchestrator,
        _get_user_model,
        reset_pipeline_state,
    )

    monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)
    reset_pipeline_state()

    response = client.get("/v1/opportunities")
    assert response.status_code == 200

    orchestrator = _get_orchestrator()
    founder_model = _get_user_model(
        orchestrator, LOCAL_FOUNDER_USER_ID, datetime.now(timezone.utc)
    )
    assert any(h.entity_id == "NVDA" for h in founder_model.holdings)
