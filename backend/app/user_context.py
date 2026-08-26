"""The server-side user identity boundary.

Two identity tiers, both resolving to the same one thing every domain
service ever sees: a plain `stratus_user_id` string.

**Anonymous** (Sprint 3.6.8 Block 2 / Sprint 3.6.9): a client identifies
itself via the `X-Stratus-User-Id` request header -- the mobile app's own
persisted per-install identifier (see `mobile/lib/identity.ts`). This is
identity, not authentication: nothing verifies the value actually belongs to
whoever is presenting it. Zero-friction by design -- this is what lets a
brand-new install use the product immediately, with no registration wall.

**Authenticated** (V2.3A, Identity & Account Foundation, see
docs/DECISIONS.md's ADR-069): a client additionally presents a real, signed
Clerk session token via `Authorization: Bearer <token>`. When present, this
module verifies it (`clerk_auth.py`) and resolves it through the durable
`(provider, external_subject) -> stratus_user_id` mapping (`account_store.py`)
-- never trusting the client-supplied `X-Stratus-User-Id` header once a valid
authenticated identity exists. A verified-but-never-before-seen external
identity is auto-provisioned a fresh `stratus_user_id` here (the common case:
a brand-new device signing in with no prior anonymous history worth
preserving); *carrying forward* an existing anonymous identity's history into
a newly-authenticated account is a distinct, explicit action -- see
`link_account()` below, called by the dedicated `POST /v1/account/link` route,
never inferred automatically inside this dependency.

A present-but-invalid/expired Authorization header is a hard rejection
(401) -- a client that explicitly claims to be authenticated and fails
verification must be told so plainly, never silently downgraded to
anonymous (which would mask an expired-session bug behind an apparently
successful, just-differently-scoped, response).

Once `stratus_user_id` is resolved, every domain service downstream (Memory,
UserModel, PrioritizationEngine, OpportunityLifecycleTracker,
UserOpportunityKnowledge, ...) receives that one plain string and nothing
else -- no provider name, no external subject, no token. This is the whole
point of the mapping layer: STRATUS Core does not know or care whether a
user authenticated with Apple, Google, email, or hasn't authenticated at
all.
"""

import threading
import uuid

from fastapi import Header, HTTPException

from logan_core.contracts import LOCAL_FOUNDER_USER_ID

from .account_store import Account, AccountStore
from .clerk_auth import ClerkClaims, verify_clerk_session_token
from .config import (
    account_store_db_path,
    clerk_configured,
    live_data_only_mode,
    memory_persistence_enabled,
)

# Sprint 3.6.9: the safe, non-founder identity a beta/production request
# resolves to when it has no usable client-supplied identity (no header, or
# a header spoofing the founder constant -- see this module's own history).
# Seeded blank like any other non-founder user_id (see ADR-057's "new-user
# seeding is genuinely blank" rule, unchanged here) -- this constant carries
# no special data of its own, it only exists so these callers share one
# well-known, harmless bucket instead of each being silently treated as the
# founder.
BETA_ANONYMOUS_USER_ID = "beta_anonymous"

# Sprint 3.6.9 hosted attack-surface review: a real per-install identity
# (mobile/lib/identity.ts) is a UUID, 36 characters -- this cap is
# generously above any legitimate value while still bounding an
# oversized/abusive header from being accepted as a "valid" identity and
# propagated everywhere this value flows (SQLite rows, in-memory dict keys,
# rate-limit counters). An over-length value is treated exactly like an
# absent one, in both modes.
_MAX_USER_ID_LENGTH = 128

# V2.3A: the one provider this codebase knows about today. A future
# provider swap adds a new string here (and a new verifier module), never a
# change to account_store's schema or to any domain service.
_CLERK_PROVIDER = "clerk"

# --- Process-lifetime account/identity cache --------------------------------
#
# Mirrors backend/app/logan_feed.py's _lifecycle_tracker/_lifecycle_store and
# _user_knowledge_cache/_user_knowledge_store pattern exactly: an in-memory
# cache that always serves reads (so this module never blocks on SQLite for
# every request), optionally write-behind to a durable store when
# memory_persistence_enabled() is true. A `threading.Lock` guards mutation
# since FastAPI runs sync `def` routes in a worker thread pool by default.
_state_lock = threading.Lock()
_account_store: AccountStore | None = None
_identity_cache: dict[tuple[str, str], str] = {}
_account_cache: dict[str, Account] = {}


def _get_account_store() -> AccountStore | None:
    global _account_store
    if not memory_persistence_enabled():
        return None
    if _account_store is None:
        _account_store = AccountStore(account_store_db_path())
        _identity_cache.clear()
        _identity_cache.update(_account_store.load_all_identities())
        _account_cache.clear()
        _account_cache.update(_account_store.load_all_accounts())
    return _account_store


def purge_account_identity(stratus_user_id: str) -> None:
    """V2.3A: the identity-cache half of `purge_user_data()` (see
    account_lifecycle.py) -- removes this user's account row and every
    external-identity mapping pointing at it, in-memory and (when
    persistence is enabled) durably.
    """
    with _state_lock:
        # Ensure the cache reflects durable state before mutating it --
        # matters the first time this runs after a restart, when the cache
        # hasn't been lazily reloaded by any other call yet.
        store = _get_account_store()
        for key in [k for k, v in _identity_cache.items() if v == stratus_user_id]:
            del _identity_cache[key]
        _account_cache.pop(stratus_user_id, None)
        if store is not None:
            store.delete_account(stratus_user_id)


def reset_account_state() -> None:
    """Test-only (and general-purpose "start over") hook, mirroring
    logan_feed.reset_pipeline_state()/notifications.reset_notification_state().
    Drops every in-process singleton; the underlying SQLite file, if any, is
    left untouched -- this simulates a real process restart, not a data wipe.
    """
    global _account_store
    with _state_lock:
        if _account_store is not None:
            _account_store.close()
        _account_store = None
        _identity_cache.clear()
        _account_cache.clear()


def _create_account(stratus_user_id: str, *, is_anonymous: bool) -> None:
    _account_cache[stratus_user_id] = Account(
        stratus_user_id=stratus_user_id,
        created_at="",  # cache doesn't need the exact timestamp; store does
        is_anonymous=is_anonymous,
    )
    store = _get_account_store()
    if store is not None:
        store.create_account(stratus_user_id, is_anonymous=is_anonymous)


def _mark_authenticated(stratus_user_id: str) -> None:
    existing = _account_cache.get(stratus_user_id)
    if existing is not None:
        _account_cache[stratus_user_id] = existing._replace(is_anonymous=False)
    store = _get_account_store()
    if store is not None:
        store.mark_authenticated(stratus_user_id)


def _link_identity(provider: str, external_subject: str, stratus_user_id: str) -> None:
    _identity_cache[(provider, external_subject)] = stratus_user_id
    store = _get_account_store()
    if store is not None:
        store.link_external_identity(provider, external_subject, stratus_user_id)


def _lookup_identity(provider: str, external_subject: str) -> str | None:
    # `_get_account_store()` is the only place that lazily reloads
    # `_identity_cache` from durable storage after a restart (see its own
    # docstring) -- calling it here, before every cache read, is what makes
    # a lookup correct immediately after `reset_account_state()` simulates a
    # process restart, not just on whichever request happens to hit some
    # other mutating path first.
    _get_account_store()
    return _identity_cache.get((provider, external_subject))


def _provision_or_lookup_account(provider: str, external_subject: str) -> str:
    """The auto-provisioning path a verified-but-unmapped external identity
    takes inside `resolve_user_id()` -- a brand-new device signing in with
    no prior anonymous history worth carrying forward gets a fresh
    `stratus_user_id` immediately, with no separate "finish setting up your
    account" step required. Carrying forward *existing* anonymous history is
    the distinct, explicit `link_account()` path below.
    """
    with _state_lock:
        existing = _lookup_identity(provider, external_subject)
        if existing is not None:
            return existing
        new_id = str(uuid.uuid4())
        _create_account(new_id, is_anonymous=False)
        _link_identity(provider, external_subject, new_id)
        return new_id


class AccountLinkConflictError(Exception):
    """V2.3A overnight security-audit finding: raised by `link_account()`
    when the requested `anonymous_user_id` is already the canonical
    identity for a *different* external identity than the one presenting
    this request. Without this check, a caller with a valid-but-unrelated
    Clerk session could supply any other user's known `stratus_user_id` as
    `anonymous_user_id` and permanently bind their own external identity to
    that victim's existing account -- gaining standing read/write access to
    it, not merely one-time anonymous impersonation. `main.py`'s route maps
    this to `HTTPException(409)`.
    """


def _is_linked_to_a_different_identity(
    stratus_user_id: str, provider: str, external_subject: str
) -> bool:
    """Checks the process-lifetime identity cache (kept in sync with the
    durable store by every mutation in this module -- see `_get_account_
    store()`'s own lazy-reload docstring) for any *other* `(provider,
    external_subject)` pair already mapped to `stratus_user_id`. Legitimate
    multi-device sign-in never reaches this: `link_account()` returns via
    its own existing-mapping lookup first when the *same* `(provider,
    external_subject)` pair was already linked.
    """
    _get_account_store()  # ensure the cache reflects durable state first
    target = (provider, external_subject)
    return any(
        uid == stratus_user_id and key != target for key, uid in _identity_cache.items()
    )


def link_account(
    provider: str, external_subject: str, anonymous_user_id: str
) -> tuple[str, bool]:
    """The explicit anonymous -> authenticated upgrade path (V2.3A), called
    by `POST /v1/account/link` immediately after a client's first successful
    sign-in on a device that has real anonymous history worth preserving.

    Returns `(stratus_user_id, upgraded_existing_identity)`:

    - First-ever link for this (provider, external_subject): the anonymous
      device's own existing id *becomes* the canonical, now-authenticated
      `stratus_user_id` -- zero data migration, since every store is already
      keyed by this same string. Returns `(anonymous_user_id, True)`.
    - This (provider, external_subject) was already linked to a different
      `stratus_user_id` (e.g. a second device signing into the same real
      account after a first device already linked): first-linked-wins is the
      canonical identity; this device's own prior anonymous history is
      *not* merged into it (see ADR-069's explicit, documented anonymous-
      merge scope). Returns `(existing_canonical_id, False)` -- the caller
      (the mobile client) is expected to adopt the returned id as its own
      active identity going forward.

    Raises `AccountLinkConflictError` when `anonymous_user_id` is already
    claimed by a *different* external identity -- see that exception's own
    docstring for the exact hijack scenario this closes.
    """
    with _state_lock:
        existing = _lookup_identity(provider, external_subject)
        if existing is not None:
            return existing, False

        if _is_linked_to_a_different_identity(
            anonymous_user_id, provider, external_subject
        ):
            raise AccountLinkConflictError(
                "This identity is already associated with a different account."
            )

        _create_account(anonymous_user_id, is_anonymous=False)
        _mark_authenticated(anonymous_user_id)
        _link_identity(provider, external_subject, anonymous_user_id)
        return anonymous_user_id, True


def _verify_bearer_header(authorization: str) -> ClerkClaims:
    """Shared verification logic for both `resolve_user_id()`'s
    authenticated path and `require_clerk_claims()` below -- parses the
    `Bearer <token>` shape and verifies it via Clerk's JWKS. Always raises
    `HTTPException(401)` on any failure (malformed header, auth not
    configured, invalid/expired token); never returns `None` -- the caller
    decides only *whether* to call this (i.e. whether an anonymous fallback
    exists), never *how* to interpret a failure once it does.
    """
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Malformed Authorization header.")
    if not clerk_configured():
        # Authentication isn't configured for this deployment at all -- a
        # client presenting a bearer token here is misconfigured, not
        # "anonymous"; failing loudly is more useful than pretending it
        # succeeded anonymously.
        raise HTTPException(status_code=401, detail="Authentication is not configured.")
    claims = verify_clerk_session_token(token)
    if claims is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")
    return claims


def require_clerk_claims(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> ClerkClaims:
    """A stricter sibling of `resolve_user_id()` used only by
    `POST /v1/account/link` (main.py): verifies a real Clerk session token
    and returns its raw claims -- deliberately *not* resolved through
    `_provision_or_lookup_account()`, since the whole point of the link
    route is to decide, explicitly, whether this external identity should
    become a *new* account or adopt an *existing* anonymous device's id.
    Auto-provisioning here first would silently consume the "first link"
    opportunity before the route body ever runs. Always requires a valid
    token -- there is no anonymous fallback for this route.
    """
    if not (isinstance(authorization, str) and authorization):
        raise HTTPException(status_code=401, detail="Authentication is required.")
    return _verify_bearer_header(authorization)


def resolve_user_id(
    x_stratus_user_id: str | None = Header(default=None, alias="X-Stratus-User-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> str:
    # --- Authenticated path (V2.3A) -----------------------------------
    #
    # A present Authorization header always takes priority over -- and is
    # never blended with -- the anonymous X-Stratus-User-Id header. Either
    # it resolves to a real, verified stratus_user_id, or the request is
    # rejected outright; it is never silently downgraded to anonymous.
    #
    # `isinstance(authorization, str)`, not just `if authorization:` --
    # this codebase's existing test convention calls resolve_user_id()
    # directly as a plain function (see test_user_context.py), which means
    # an omitted keyword argument evaluates to FastAPI's own `Header(...)`
    # marker object (truthy, but not a string) rather than the `None`
    # FastAPI's real request-handling dependency injection would supply --
    # this guard keeps both call styles correct.
    if isinstance(authorization, str) and authorization:
        claims = _verify_bearer_header(authorization)
        return _provision_or_lookup_account(_CLERK_PROVIDER, claims.subject)

    # --- Anonymous path (unchanged from Sprint 3.6.9) -------------------
    stripped = (x_stratus_user_id or "").strip()
    if len(stripped) > _MAX_USER_ID_LENGTH:
        stripped = ""

    if live_data_only_mode():
        # Beta/production: the founder constant must never be reachable via
        # an unauthenticated, client-controlled header -- neither by
        # omitting the header (the old default) nor by supplying it
        # explicitly. Any other non-empty value -- in practice, the mobile
        # app's own persisted per-install identity -- is honored as-is;
        # this is still identity, not authentication, but it is no longer
        # possible for a request to land on the founder's real data without
        # the founder's own device actually presenting the founder's own
        # real header value.
        if not stripped or stripped == LOCAL_FOUNDER_USER_ID:
            return BETA_ANONYMOUS_USER_ID
        return stripped

    # Demo/development mode: unchanged, exact pre-Sprint-3.6.9 behavior.
    return stripped or LOCAL_FOUNDER_USER_ID
