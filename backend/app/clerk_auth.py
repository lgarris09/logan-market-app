"""V2.3A -- Identity & Account Foundation: Clerk session-token verification.

Standard JWT/JWKS verification (PyJWT's built-in `PyJWKClient`), not a
Clerk-specific Python SDK -- Clerk issues RS256 JWTs verifiable against its
own published JWKS, the same mechanism any OIDC-style provider uses. This is
the one file in this codebase that knows Clerk's issuer-URL/JWKS shape;
everything downstream of `verify_clerk_session_token()` only ever sees a
plain `ClerkClaims.subject` string, mapped through `account_store.py` into a
STRATUS `stratus_user_id` -- domain logic never sees a Clerk-specific
identifier at all. Swapping auth providers later means replacing this one
module (and repointing `account_store`'s `provider` column at a new string),
not touching `logan_core/` or any route's business logic.

Deliberately fails closed and silently: any failure mode (missing config,
network error fetching JWKS, malformed token, bad signature, wrong issuer,
expired token) returns `None`, never raises -- the caller (`user_context.py`)
treats "not authenticated" uniformly regardless of cause, and a JWKS outage
degrades a request to 401 rather than crashing the server.
"""

from typing import Optional

import jwt
from jwt import PyJWKClient

from .config import clerk_configured, clerk_issuer_url

# Clerk issues RS256-signed session tokens -- the only algorithm this
# verifier accepts. Explicit allowlist (never `jwt.decode(..., algorithms=None)`)
# so a token cannot force verification down an unintended/weaker algorithm.
_ALGORITHM = "RS256"

_jwks_client: Optional[PyJWKClient] = None
_jwks_client_issuer: Optional[str] = None


class ClerkClaims:
    """The one fact this module ever hands to a caller: a verified Clerk
    subject id. Nothing else from the token payload is exposed -- callers
    have no legitimate use for Clerk-specific claims beyond the stable
    identifier used to look up (or provision) a `stratus_user_id`.
    """

    __slots__ = ("subject",)

    def __init__(self, subject: str) -> None:
        self.subject = subject


def _get_jwks_client() -> Optional[PyJWKClient]:
    """Lazily constructs (and caches) the JWKS client, rebuilding it if the
    configured issuer ever changes mid-process (tests toggle CLERK_ISSUER_URL
    via monkeypatch). PyJWKClient itself caches fetched keys in-process
    (cache_keys=True) so a real deployment doesn't refetch the JWKS on every
    request.
    """
    global _jwks_client, _jwks_client_issuer
    issuer = clerk_issuer_url()
    if issuer is None:
        return None
    if _jwks_client is None or _jwks_client_issuer != issuer:
        _jwks_client = PyJWKClient(f"{issuer}/.well-known/jwks.json", cache_keys=True)
        _jwks_client_issuer = issuer
    return _jwks_client


def reset_clerk_jwks_cache() -> None:
    """Test-only (and general-purpose "config changed") reset hook, mirroring
    this codebase's existing reset_fmp_cache()/reset_pipeline_state()
    convention for process-lifetime state.
    """
    global _jwks_client, _jwks_client_issuer
    _jwks_client = None
    _jwks_client_issuer = None


def verify_clerk_session_token(token: str) -> Optional[ClerkClaims]:
    """Verifies a real Clerk session JWT's signature, issuer, and expiry.
    Returns `None` -- never raises -- on any failure, including when
    clerk_configured() is False (authentication stays fully inert until a
    real Clerk issuer is configured).
    """
    if not clerk_configured():
        return None
    client = _get_jwks_client()
    if client is None:
        return None

    try:
        signing_key = client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=[_ALGORITHM],
            issuer=clerk_issuer_url(),
            options={"require": ["exp", "iat", "sub"]},
        )
    except Exception:
        # Deliberately broad: PyJWKClient/jwt.decode raise a variety of
        # exception types (jwt.exceptions.*, urllib/network errors fetching
        # the JWKS, KeyError on a malformed JWKS payload) -- every one of
        # them means "this token/config did not verify," never a server
        # crash. Never logs the token itself (a bearer credential).
        return None

    subject = payload.get("sub")
    if not subject or not isinstance(subject, str):
        return None
    return ClerkClaims(subject=subject)
