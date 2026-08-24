"""Sprint 3.6.8 Block 2 -- the server-side user identity boundary.

Not authentication: there is no login, no session token, no verification of
who is actually making a request. This is the minimal mechanism required to
give `backend/app/` a real per-request identity to thread through, so the
process-lifetime state that was previously hardcoded to
`LOCAL_FOUNDER_USER_ID` everywhere (see docs/DECISIONS.md's Sprint 3.6.8
Block 2 ADR) can actually be scoped per caller.

A client identifies itself via the `X-Stratus-User-Id` request header.

Sprint 3.6.9 (Persistent Mobile Identity + Beta Security Boundary, see
docs/DECISIONS.md's Sprint 3.6.9 ADR): the mobile app now generates and
persists a real per-install identifier and sends it on every request (see
mobile/lib/identity.ts), so an absent header is no longer the *expected*
case for a real client the way it was when this header didn't exist yet --
it now means either an older, not-yet-updated build, or a caller other than
the STRATUS mobile app entirely (a script, a bot, a browser).

Real, found-in-this-pass exposure this file used to have: `LOCAL_FOUNDER_USER_ID`
resolves to the fixed, publicly-documented string `"demo_user"` (see
logan_core/contracts/common.py) -- and because `X-Stratus-User-Id` is
entirely client-asserted with no verification, *any* caller of the hosted
API could set `X-Stratus-User-Id: demo_user` explicitly (or simply omit the
header, which resolved to the same constant) and receive the founder's own
real, personalized data -- their actual holdings, interests, and behavioral
history. Harmless when this backend was reachable only from the founder's
own machine; a real information-disclosure exposure the moment it became a
hosted, internet-reachable beta (Sprint 3.6.9 Block 1). Fixed below: in
beta/production mode (`config.live_data_only_mode()`), the founder constant
is never honored from a client-supplied header at all -- not via an absent
header (the pre-existing default), and not via a header that explicitly
claims to *be* the founder constant (the sharper, previously-open half of
this gap). Demo/development mode is completely unchanged -- every existing
local caller, script, and test that relies on the pre-Sprint-3.6.9 default
continues to work identically.
"""

from fastapi import Header

from logan_core.contracts import LOCAL_FOUNDER_USER_ID

from .config import live_data_only_mode

# Sprint 3.6.9: the safe, non-founder identity a beta/production request
# resolves to when it has no usable client-supplied identity (no header, or
# a header spoofing the founder constant -- see this module's own docstring).
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


def resolve_user_id(
    x_stratus_user_id: str | None = Header(default=None, alias="X-Stratus-User-Id"),
) -> str:
    stripped = (x_stratus_user_id or "").strip()
    if len(stripped) > _MAX_USER_ID_LENGTH:
        stripped = ""

    if live_data_only_mode():
        # Beta/production: the founder constant must never be reachable via
        # an unauthenticated, client-controlled header -- neither by
        # omitting the header (the old default) nor by supplying it
        # explicitly (the sharper gap this pass closes). Any other
        # non-empty value -- in practice, the mobile app's own persisted
        # per-install identity -- is honored as-is; this is still identity,
        # not authentication, but it is no longer possible for a request to
        # land on the founder's real data without the founder's own device
        # actually presenting the founder's own real header value.
        if not stripped or stripped == LOCAL_FOUNDER_USER_ID:
            return BETA_ANONYMOUS_USER_ID
        return stripped

    # Demo/development mode: unchanged, exact pre-Sprint-3.6.9 behavior.
    return stripped or LOCAL_FOUNDER_USER_ID
