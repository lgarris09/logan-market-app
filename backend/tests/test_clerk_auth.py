"""V2.3A -- Identity & Account Foundation: Clerk JWT/JWKS verification.

No real network calls or real Clerk instance -- generates a real RSA
keypair once, signs real JWTs with the private key, and monkeypatches
`_get_jwks_client()` to return a stub whose `get_signing_key_from_jwt()`
hands back the real public key, exactly mirroring what a real
`jwt.PyJWKClient` would resolve from a real JWKS endpoint. This exercises
the real `jwt.decode()` signature/issuer/expiry verification path end to
end, not just a mocked "verification succeeded" boolean.
"""

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from backend.app import clerk_auth
from backend.app.clerk_auth import verify_clerk_session_token

_ISSUER = "https://test-instance.clerk.accounts.dev"

_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_public_key = _private_key.public_key()

_other_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _FakeSigningKey:
    def __init__(self, key) -> None:
        self.key = key


class _FakeJwksClient:
    def __init__(self, key) -> None:
        self._key = key

    def get_signing_key_from_jwt(self, token: str) -> _FakeSigningKey:
        return _FakeSigningKey(self._key)


@pytest.fixture(autouse=True)
def _configure_clerk(monkeypatch):
    monkeypatch.setenv("CLERK_ISSUER_URL", _ISSUER)
    monkeypatch.setattr(
        clerk_auth, "_get_jwks_client", lambda: _FakeJwksClient(_public_key)
    )
    yield


def _make_token(
    *,
    subject: str = "user_abc123",
    issuer: str = _ISSUER,
    private_key=_private_key,
    expires_in: float = 3600,
    include_exp: bool = True,
    include_sub: bool = True,
) -> str:
    payload: dict = {"iss": issuer, "iat": int(time.time())}
    if include_exp:
        payload["exp"] = int(time.time() + expires_in)
    if include_sub:
        payload["sub"] = subject
    return jwt.encode(payload, private_key, algorithm="RS256")


def test_valid_token_verifies_and_returns_subject():
    token = _make_token(subject="user_real_123")
    claims = verify_clerk_session_token(token)
    assert claims is not None
    assert claims.subject == "user_real_123"


def test_not_configured_returns_none(monkeypatch):
    monkeypatch.delenv("CLERK_ISSUER_URL", raising=False)
    token = _make_token()
    assert verify_clerk_session_token(token) is None


def test_expired_token_rejected():
    token = _make_token(expires_in=-3600)
    assert verify_clerk_session_token(token) is None


def test_wrong_issuer_rejected():
    token = _make_token(issuer="https://not-us.clerk.accounts.dev")
    assert verify_clerk_session_token(token) is None


def test_wrong_signing_key_rejected():
    """A token signed by a *different* private key -- the exact shape of an
    attacker-forged token, or a stale/rotated key -- must never verify
    against our configured JWKS key."""
    token = _make_token(private_key=_other_private_key)
    assert verify_clerk_session_token(token) is None


def test_missing_subject_rejected():
    token = _make_token(include_sub=False)
    assert verify_clerk_session_token(token) is None


def test_missing_exp_rejected():
    token = _make_token(include_exp=False)
    assert verify_clerk_session_token(token) is None


def test_malformed_token_rejected():
    assert verify_clerk_session_token("not-a-real-jwt-at-all") is None


def test_jwks_fetch_failure_rejected(monkeypatch):
    def _raise(*a, **kw):
        raise RuntimeError("simulated JWKS fetch failure")

    monkeypatch.setattr(
        clerk_auth,
        "_get_jwks_client",
        lambda: type("Broken", (), {"get_signing_key_from_jwt": _raise})(),
    )
    token = _make_token()
    assert verify_clerk_session_token(token) is None
