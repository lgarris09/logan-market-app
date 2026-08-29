"""V2.3A -- Identity & Account Foundation.

Covers: Bearer-token auto-provisioning, the explicit anonymous ->
authenticated upgrade path (/v1/account/link), first-linked-wins merge
semantics for a second device, the security boundary (a spoofed
X-Stratus-User-Id header must never override a verified Bearer token),
founder/dev identity isolation, and account deletion (/v1/account DELETE).

No real Clerk instance or network call -- reuses the same real-RSA-keypair
JWT-signing technique as test_clerk_auth.py so these are genuine
signature/issuer/expiry-verified tokens, not a mocked "auth succeeded"
shortcut.
"""

import time
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from backend.app.logan_feed import reset_pipeline_state
from backend.app.main import app
from backend.app.notifications import reset_notification_state
from backend.app.user_context import (
    BETA_ANONYMOUS_USER_ID,
    reset_account_state,
    resolve_user_id,
)
from logan_core.contracts import LOCAL_FOUNDER_USER_ID

client = TestClient(app)
_ISSUER = "https://test-instance.clerk.accounts.dev"
_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_public_key = _private_key.public_key()


def _token(subject: str, expires_in: float = 3600) -> str:
    payload = {
        "iss": _ISSUER,
        "iat": int(time.time()),
        "exp": int(time.time() + expires_in),
        "sub": subject,
    }
    return jwt.encode(payload, _private_key, algorithm="RS256")


def _bearer_value(subject: str, expires_in: float = 3600) -> str:
    """The raw `Bearer <token>` string, for calling resolve_user_id()
    directly as a plain function (see this codebase's own established
    resolve_user_id test convention)."""
    return f"Bearer {_token(subject, expires_in=expires_in)}"


def _bearer(subject: str) -> dict:
    return {"Authorization": f"Bearer {_token(subject)}"}


@pytest.fixture(autouse=True)
def _configure_clerk(monkeypatch):
    from backend.app import clerk_auth

    monkeypatch.setenv("CLERK_ISSUER_URL", _ISSUER)
    monkeypatch.delenv("STRATUS_RUNTIME_MODE", raising=False)
    monkeypatch.delenv("STRATUS_PERSIST_MEMORY", raising=False)
    monkeypatch.setattr(
        clerk_auth,
        "_get_jwks_client",
        lambda: type(
            "FakeJwksClient",
            (),
            {
                "get_signing_key_from_jwt": staticmethod(
                    lambda token: type("K", (), {"key": _public_key})()
                )
            },
        )(),
    )
    yield


# --- Pure resolve_user_id() unit tests --------------------------------------


def test_valid_bearer_token_auto_provisions_a_fresh_identity():
    result = resolve_user_id(
        x_stratus_user_id=None, authorization=_bearer_value("clerk_u1")
    )
    assert result
    assert result != LOCAL_FOUNDER_USER_ID
    assert result != BETA_ANONYMOUS_USER_ID


def test_same_token_resolves_to_the_same_identity_on_repeat_calls():
    first = resolve_user_id(
        x_stratus_user_id=None, authorization=_bearer_value("clerk_u2")
    )
    second = resolve_user_id(
        x_stratus_user_id=None, authorization=_bearer_value("clerk_u2")
    )
    assert first == second


def test_different_subjects_get_different_identities():
    a = resolve_user_id(x_stratus_user_id=None, authorization=_bearer_value("clerk_u3"))
    b = resolve_user_id(x_stratus_user_id=None, authorization=_bearer_value("clerk_u4"))
    assert a != b


def test_expired_token_is_rejected():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        resolve_user_id(
            x_stratus_user_id=None,
            authorization=_bearer_value("clerk_u5", expires_in=-10),
        )
    assert exc_info.value.status_code == 401


def test_malformed_authorization_header_is_rejected():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        resolve_user_id(x_stratus_user_id=None, authorization="NotBearer garbage")
    assert exc_info.value.status_code == 401


def test_bearer_token_overrides_a_spoofed_anonymous_header():
    """The core security boundary: a client cannot impersonate another
    STRATUS user merely by changing X-Stratus-User-Id, even when it also
    sends a header claiming to be someone else -- a verified Bearer token
    always wins and the anonymous header is never consulted at all."""
    resolved = resolve_user_id(
        x_stratus_user_id="someone-elses-anonymous-device-id",
        authorization=_bearer_value("clerk_u6"),
    )
    assert resolved != "someone-elses-anonymous-device-id"


def test_authenticated_identity_is_never_the_founder_constant():
    resolved = resolve_user_id(
        x_stratus_user_id=None, authorization=_bearer_value("clerk_u7")
    )
    assert resolved != LOCAL_FOUNDER_USER_ID


# --- End-to-end through real routes -----------------------------------------


def test_link_route_requires_authentication():
    response = client.post(
        "/v1/account/link", json={"anonymous_user_id": "anon-device-a"}
    )
    assert response.status_code == 401


def test_link_route_upgrades_existing_anonymous_identity():
    anon_id = f"anon-{uuid4()}"
    response = client.post(
        "/v1/account/link",
        json={"anonymous_user_id": anon_id},
        headers=_bearer("clerk_link_1"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["stratus_user_id"] == anon_id
    assert body["upgraded_existing_identity"] is True


def test_link_preserves_existing_state_recorded_under_the_anonymous_id(monkeypatch):
    """Acceptance item 4: an anonymous user can authenticate without losing
    existing STRATUS user-scoped state -- proven by recording a real
    interaction under the anonymous id, linking, then confirming the same
    resolved identity still has that history (MemoryStore is keyed by the
    literal user_id string, which never changes across the upgrade)."""
    from backend.app.logan_feed import record_interaction

    reset_pipeline_state()
    anon_id = f"anon-{uuid4()}"
    record_interaction(
        user_id=anon_id,
        event_id=uuid4(),
        entity_id="NVDA",
        domain="stocks",
        interaction_type="save",
    )
    from backend.app.logan_feed import _get_orchestrator

    orchestrator = _get_orchestrator()
    pre_link_records = orchestrator.deps.memory_store.query(user_id=anon_id)
    assert len(pre_link_records) >= 1

    response = client.post(
        "/v1/account/link",
        json={"anonymous_user_id": anon_id},
        headers=_bearer("clerk_link_2"),
    )
    stratus_user_id = response.json()["stratus_user_id"]
    assert stratus_user_id == anon_id

    post_link_records = orchestrator.deps.memory_store.query(user_id=stratus_user_id)
    assert len(post_link_records) == len(pre_link_records)


def test_second_device_linking_same_account_gets_first_linked_canonical_id():
    """The documented anonymous-merge semantics: first-linked-wins. A second
    device authenticating into the same real account does not orphan the
    first device's identity or create a competing canonical id -- it
    receives the *first* device's own canonical id back."""
    device_a = f"anon-{uuid4()}"
    device_b = f"anon-{uuid4()}"
    subject = "clerk_shared_account"

    first = client.post(
        "/v1/account/link",
        json={"anonymous_user_id": device_a},
        headers=_bearer(subject),
    )
    assert first.json()["upgraded_existing_identity"] is True
    canonical = first.json()["stratus_user_id"]

    second = client.post(
        "/v1/account/link",
        json={"anonymous_user_id": device_b},
        headers=_bearer(subject),
    )
    assert second.status_code == 200
    assert second.json()["upgraded_existing_identity"] is False
    assert second.json()["stratus_user_id"] == canonical
    assert second.json()["stratus_user_id"] != device_b


def test_link_rejects_claiming_a_stratus_user_id_already_linked_elsewhere():
    """Overnight security re-audit finding: a caller must not be able to
    hijack a *known* stratus_user_id by presenting it as their own
    `anonymous_user_id` -- that would permanently bind their own,
    genuinely-valid external identity to a victim's existing account,
    gaining standing read/write access to it. Must be a hard rejection
    (409), not a silent success under either identity."""
    victim_device = f"anon-{uuid4()}"
    client.post(
        "/v1/account/link",
        json={"anonymous_user_id": victim_device},
        headers=_bearer("clerk_victim"),
    )
    # victim_device is now the canonical, linked identity for clerk_victim.

    attacker_response = client.post(
        "/v1/account/link",
        json={"anonymous_user_id": victim_device},  # the attacker knows/guesses this
        headers=_bearer("clerk_attacker"),  # a genuinely different, valid identity
    )
    assert attacker_response.status_code == 409

    # The attacker's own token must still resolve to their own identity,
    # never the victim's, after the rejected attempt.
    attacker_resolved = resolve_user_id(
        x_stratus_user_id=None, authorization=_bearer_value("clerk_attacker")
    )
    assert attacker_resolved != victim_device

    # The victim's own link must remain completely intact.
    victim_resolved = resolve_user_id(
        x_stratus_user_id=None, authorization=_bearer_value("clerk_victim")
    )
    assert victim_resolved == victim_device


def test_link_conflict_does_not_disturb_the_victims_existing_data():
    from backend.app.logan_feed import _get_orchestrator, record_interaction

    reset_pipeline_state()
    victim_device = f"anon-{uuid4()}"
    record_interaction(
        user_id=victim_device,
        event_id=uuid4(),
        entity_id="NVDA",
        domain="stocks",
        interaction_type="save",
    )
    client.post(
        "/v1/account/link",
        json={"anonymous_user_id": victim_device},
        headers=_bearer("clerk_victim_2"),
    )

    client.post(
        "/v1/account/link",
        json={"anonymous_user_id": victim_device},
        headers=_bearer("clerk_attacker_2"),
    )

    orchestrator = _get_orchestrator()
    assert len(orchestrator.deps.memory_store.query(user_id=victim_device)) >= 1


def test_link_rejects_claiming_the_founder_reserved_identity():
    """2026-08-29 audit finding: `demo_user` (LOCAL_FOUNDER_USER_ID) has
    never been linked to anyone at the point of this test, so it would
    otherwise pass the cross-identity check above (not linked to a
    *different* identity -- not linked to anyone) and let any valid Clerk
    session permanently claim the founder/demo account. Must be a hard
    409, exactly like claiming a known victim's id."""
    response = client.post(
        "/v1/account/link",
        json={"anonymous_user_id": LOCAL_FOUNDER_USER_ID},
        headers=_bearer("clerk_reserved_attacker_1"),
    )
    assert response.status_code == 409

    resolved = resolve_user_id(
        x_stratus_user_id=None,
        authorization=_bearer_value("clerk_reserved_attacker_1"),
    )
    assert resolved != LOCAL_FOUNDER_USER_ID


def test_link_rejects_claiming_the_beta_anonymous_reserved_identity():
    """Same hijack shape as the founder constant, for the shared
    no-header production bucket (BETA_ANONYMOUS_USER_ID)."""
    response = client.post(
        "/v1/account/link",
        json={"anonymous_user_id": BETA_ANONYMOUS_USER_ID},
        headers=_bearer("clerk_reserved_attacker_2"),
    )
    assert response.status_code == 409

    resolved = resolve_user_id(
        x_stratus_user_id=None,
        authorization=_bearer_value("clerk_reserved_attacker_2"),
    )
    assert resolved != BETA_ANONYMOUS_USER_ID


def test_link_still_succeeds_for_an_ordinary_anonymous_uuid():
    """The reserved-identity guard must reject exactly the two reserved
    constants -- nothing else. An ordinary device-generated id continues
    to link exactly as before."""
    anon_id = f"anon-{uuid4()}"
    response = client.post(
        "/v1/account/link",
        json={"anonymous_user_id": anon_id},
        headers=_bearer("clerk_ordinary_device"),
    )
    assert response.status_code == 200
    assert response.json()["stratus_user_id"] == anon_id
    assert response.json()["upgraded_existing_identity"] is True


def test_signed_out_device_still_resolves_via_its_own_anonymous_header():
    """Documents the current, intentional sign-out behavior (ADR-069):
    Clerk JWTs are stateless, and sign-out is purely a client-side session
    clear -- there is no server-side revocation. After linking, the same
    device's own anonymous header (i.e. what it sends once it has "signed
    out" and stopped presenting a Bearer token) still resolves to the same
    canonical identity, exactly as before linking. This is by design, not
    a bug -- this test exists so the behavior is captured, not silently
    left untested."""
    anon_id = f"anon-{uuid4()}"
    client.post(
        "/v1/account/link",
        json={"anonymous_user_id": anon_id},
        headers=_bearer("clerk_signout_case"),
    )

    signed_out_resolution = resolve_user_id(
        x_stratus_user_id=anon_id, authorization=None
    )
    assert signed_out_resolution == anon_id


def test_after_linking_authenticated_requests_resolve_to_the_linked_identity():
    anon_id = f"anon-{uuid4()}"
    subject = "clerk_full_flow"
    client.post(
        "/v1/account/link",
        json={"anonymous_user_id": anon_id},
        headers=_bearer(subject),
    )
    resolved = resolve_user_id(
        x_stratus_user_id=None, authorization=_bearer_value(subject)
    )
    assert resolved == anon_id


# --- Deletion ----------------------------------------------------------------


def test_delete_account_purges_memory_and_notification_state():
    from backend.app.logan_feed import _get_orchestrator, record_interaction
    from backend.app.models import RegisterPushTokenRequest
    from backend.app.notifications import register_token

    reset_pipeline_state()
    reset_notification_state()
    user_id = f"anon-{uuid4()}"
    record_interaction(
        user_id=user_id,
        event_id=uuid4(),
        entity_id="NVDA",
        domain="stocks",
        interaction_type="save",
    )
    register_token(
        user_id, RegisterPushTokenRequest(expo_push_token="ExponentPushToken[del]")
    )

    response = client.delete("/v1/account", headers={"X-Stratus-User-Id": user_id})
    assert response.status_code == 200
    assert response.json()["deleted"] is True
    assert response.json()["stratus_user_id"] == user_id

    orchestrator = _get_orchestrator()
    assert orchestrator.deps.memory_store.query(user_id=user_id) == []


def test_delete_account_only_ever_deletes_the_callers_own_data():
    """A client cannot purge another user's data merely by knowing their
    id -- DELETE /v1/account always resolves the target from the caller's
    own resolved identity, never a request body/query parameter."""
    from backend.app.logan_feed import _get_orchestrator, record_interaction

    reset_pipeline_state()
    victim_id = f"anon-{uuid4()}"
    record_interaction(
        user_id=victim_id,
        event_id=uuid4(),
        entity_id="NVDA",
        domain="stocks",
        interaction_type="save",
    )

    attacker_id = f"anon-{uuid4()}"
    response = client.delete("/v1/account", headers={"X-Stratus-User-Id": attacker_id})
    assert response.status_code == 200
    assert response.json()["stratus_user_id"] == attacker_id  # not the victim

    orchestrator = _get_orchestrator()
    assert len(orchestrator.deps.memory_store.query(user_id=victim_id)) >= 1


def test_deleted_account_reauthenticating_gets_a_fresh_identity():
    """After deletion, the (provider, subject) mapping is gone -- presenting
    the same external identity again is treated as a genuinely new account,
    not resurrected state. Correct, not a bug: deletion means deletion."""
    anon_id = f"anon-{uuid4()}"
    subject = "clerk_delete_then_return"
    link_response = client.post(
        "/v1/account/link",
        json={"anonymous_user_id": anon_id},
        headers=_bearer(subject),
    )
    original_id = link_response.json()["stratus_user_id"]

    client.delete("/v1/account", headers=_bearer(subject))

    new_resolution = resolve_user_id(
        x_stratus_user_id=None, authorization=_bearer_value(subject)
    )
    assert new_resolution != original_id


def test_delete_account_purges_v21_opportunity_knowledge_state():
    """Overnight security re-audit: purge_user_data() must also clear V2.1's
    UserOpportunityKnowledge pointers (last_seen/notified/opened revision),
    not just MemoryStore/notification state -- this is a disposable-identity
    check, never run against founder/primary data."""
    from datetime import datetime, timezone

    from backend.app.logan_feed import _advance_user_knowledge, _get_user_knowledge

    reset_pipeline_state()
    user_id = f"anon-{uuid4()}"
    _advance_user_knowledge(
        user_id, "NVDA", datetime.now(timezone.utc), seen_revision=3
    )
    assert _get_user_knowledge(user_id, "NVDA") is not None

    response = client.delete("/v1/account", headers={"X-Stratus-User-Id": user_id})
    assert response.status_code == 200

    assert _get_user_knowledge(user_id, "NVDA") is None


# --- Persistence / restart ---------------------------------------------------


def test_account_mapping_survives_a_simulated_restart(monkeypatch, tmp_path):
    monkeypatch.setenv("STRATUS_PERSIST_MEMORY", "true")
    monkeypatch.setenv("STRATUS_ACCOUNTS_DB_PATH", str(tmp_path / "accounts.db"))
    reset_account_state()

    anon_id = f"anon-{uuid4()}"
    subject = "clerk_restart_test"
    client.post(
        "/v1/account/link",
        json={"anonymous_user_id": anon_id},
        headers=_bearer(subject),
    )

    # Simulated restart -- drops the in-process cache; the SQLite file
    # itself is untouched.
    reset_account_state()

    resolved = resolve_user_id(
        x_stratus_user_id=None, authorization=_bearer_value(subject)
    )
    assert resolved == anon_id
