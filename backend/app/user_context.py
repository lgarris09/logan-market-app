"""Sprint 3.6.8 Block 2 -- the server-side user identity boundary.

Not authentication: there is no login, no session token, no verification of
who is actually making a request. This is the minimal mechanism required to
give `backend/app/` a real per-request identity to thread through, so the
process-lifetime state that was previously hardcoded to
`LOCAL_FOUNDER_USER_ID` everywhere (see docs/DECISIONS.md's Sprint 3.6.8
Block 2 ADR) can actually be scoped per caller.

A client identifies itself via the `X-Stratus-User-Id` request header.
Absent -- which is every existing caller today, since the mobile app has no
concept of a persistent per-device identity yet -- resolves to
`LOCAL_FOUNDER_USER_ID`, so every pre-Block-2 caller and every pre-Block-2
test is completely unaffected. Wiring the mobile app to generate and persist
a real per-device identifier is deliberately deferred (see the ADR's
consequences) -- it would require a new client-side storage dependency this
block does not add.
"""

from fastapi import Header

from logan_core.contracts import LOCAL_FOUNDER_USER_ID


def resolve_user_id(
    x_stratus_user_id: str | None = Header(default=None, alias="X-Stratus-User-Id"),
) -> str:
    stripped = (x_stratus_user_id or "").strip()
    return stripped or LOCAL_FOUNDER_USER_ID
