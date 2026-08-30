"""Operational Beta Hardening Block 1 -- Diagnostic Fault Codes.

Stable, developer-facing fault codes so "Dave, I got DATA-302" immediately
narrows the subsystem, without reading logs or source code. Purely
diagnostic observability -- record_fault() never changes control flow,
never retries/suppresses/alters a response, and never turns an honest
product state (e.g. "nothing currently qualifies") into a fault. See
NOT_A_FAULT_NOTES below for the one this framework was built to explicitly
NOT catalog.

Lives in logan_core (not backend/app) because the DATA-3xx family's real
call sites are the FMP provider layer (logan_core/receptors/providers/
fmp.py) -- backend/app depends on logan_core, never the reverse, so this
had to sit here for both backend/app (AUTH/ASK/WATCH wiring) and
logan_core (DATA wiring) to import it the same, already-established
direction.

Families (stable -- extend with new codes, never renumber an existing one):
  AUTH-1xx   authentication / account-linking
  FEED-2xx   feed generation
  DATA-3xx   provider / data
  ASK-4xx    Ask STRATUS
  WATCH-5xx  Watch
  SYNC-6xx   identity sync / linking
  APP-9xx    startup / configuration

Every FaultOccurrence carries: code, timestamp, subsystem, safe_context
(secrets stripped -- see _sanitize_context), http/provider status where
available, runtime mode where available, and a correlation_id. Never an
API key, Clerk token, Anthropic key, password, or raw sensitive payload.
"""

import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True)
class FaultDefinition:
    code: str
    family: str
    summary: str
    wired: bool  # True iff a real code path actually calls record_fault()
    # with this code today -- False means "registered for a known failure
    # class, not yet reachable" (honest, not a stub pretending to be live).


# Registration order within a family doesn't matter -- format_fault_catalog()
# always sorts by code.
FAULT_CATALOG: dict[str, FaultDefinition] = {
    "AUTH-100": FaultDefinition(
        "AUTH-100",
        "AUTH",
        "Invalid or expired authentication (Bearer token failed verification)",
        wired=True,
    ),
    "AUTH-101": FaultDefinition(
        "AUTH-101",
        "AUTH",
        "Account-link rejected (conflicting or reserved identity)",
        wired=True,
    ),
    "FEED-200": FaultDefinition(
        "FEED-200",
        "FEED",
        "Feed generation failure (a real pipeline exception, never a "
        "qualification outcome -- see NOT_A_FAULT_NOTES)",
        wired=False,
    ),
    "FEED-201": FaultDefinition(
        "FEED-201",
        "FEED",
        "Universe membership reevaluation failure " "(Universe Manager V1a Blocks 2-6)",
        wired=True,
    ),
    "DATA-300": FaultDefinition(
        "DATA-300",
        "DATA",
        "Provider unavailable (construction/network failure)",
        wired=True,
    ),
    "DATA-301": FaultDefinition(
        "DATA-301", "DATA", "Provider rate limited (HTTP 429)", wired=True
    ),
    "DATA-302": FaultDefinition(
        "DATA-302", "DATA", "Invalid provider credentials (401/402/403)", wired=True
    ),
    "DATA-303": FaultDefinition(
        "DATA-303", "DATA", "Provider response malformed (unexpected shape)", wired=True
    ),
    "DATA-304": FaultDefinition(
        "DATA-304",
        "DATA",
        "Stale-data fallback engaged (serving a cached value past its "
        "normal TTL after a refetch failure)",
        wired=True,
    ),
    "DATA-305": FaultDefinition(
        "DATA-305",
        "DATA",
        "Universe candidate source unavailable or snapshot invalid "
        "(Universe Manager V1a)",
        wired=True,
    ),
    "DATA-306": FaultDefinition(
        "DATA-306",
        "DATA",
        "Provider scheduler saturated -- no capacity within wait budget "
        "(Universe Manager V1a Block 7)",
        wired=True,
    ),
    "DATA-307": FaultDefinition(
        "DATA-307",
        "DATA",
        "Freshness breach -- data unavailable even within its grace "
        "window (Universe Manager V1a Block 8)",
        wired=False,
    ),
    "ASK-400": FaultDefinition(
        "ASK-400",
        "ASK",
        "LLM provider unavailable (falls back to the deterministic path)",
        wired=True,
    ),
    "ASK-401": FaultDefinition(
        "ASK-401", "ASK", "Grounded Ask context construction failure", wired=False
    ),
    "WATCH-500": FaultDefinition(
        "WATCH-500", "WATCH", "Watch persistence failure", wired=True
    ),
    "WATCH-501": FaultDefinition(
        "WATCH-501", "WATCH", "Watch API transition failure", wired=False
    ),
    "SYNC-600": FaultDefinition(
        "SYNC-600",
        "SYNC",
        "Anonymous-to-authenticated linking/sync failure (an unexpected "
        "error during the link operation itself, distinct from AUTH-101's "
        "deliberate policy rejection)",
        wired=False,
    ),
    "APP-900": FaultDefinition(
        "APP-900", "APP", "Startup/configuration failure", wired=False
    ),
}

# Explicitly NOT a fault -- documented so nobody "completes the matrix" by
# adding a code for this later. A healthy feed with zero currently-
# qualifying opportunities is a correct, honest product state.
NOT_A_FAULT_NOTES = [
    "A healthy feed with zero currently-qualifying opportunities is a "
    "correct, honest product state, never a fault -- see "
    "OpportunitiesResponse/FeedItem's own provider_degraded field for the "
    "real 'data was actually unreachable' signal, which is what genuinely "
    "deserves a DATA-3xx fault code.",
]

_SENSITIVE_KEY_PATTERN = re.compile(
    r"key|token|secret|password|credential|authorization|apikey", re.IGNORECASE
)
_MAX_CONTEXT_VALUE_LENGTH = 200


def _sanitize_context(context: Optional[dict]) -> dict:
    """Strips any key that looks like it could carry a credential/secret --
    never trusts a caller to have already done this. Values are also
    length-bounded so a caller can't smuggle a large/sensitive payload
    through an otherwise-innocuous-looking key."""
    if not context:
        return {}
    safe: dict = {}
    for key, value in context.items():
        if _SENSITIVE_KEY_PATTERN.search(key):
            continue
        text = str(value)
        safe[key] = (
            text
            if len(text) <= _MAX_CONTEXT_VALUE_LENGTH
            else text[:_MAX_CONTEXT_VALUE_LENGTH] + "...(truncated)"
        )
    return safe


@dataclass(frozen=True)
class FaultOccurrence:
    code: str
    family: str
    correlation_id: str
    occurred_at: datetime
    subsystem: str
    safe_context: dict
    http_status: Optional[int] = None
    provider_status: Optional[int] = None
    runtime_mode: Optional[str] = None


_MAX_RECENT_OCCURRENCES = 200
_recent_occurrences: list[FaultOccurrence] = []


def record_fault(
    code: str,
    subsystem: str,
    *,
    context: Optional[dict] = None,
    http_status: Optional[int] = None,
    provider_status: Optional[int] = None,
) -> FaultOccurrence:
    """Records one fault occurrence -- pure observability, never changes
    control flow or the caller's own response/exception. An unrecognized
    code is still recorded (never raises) so a typo at a call site is
    visible in the report/tests rather than silently swallowed, but its
    family is derived from the code string itself when not in the catalog.
    """
    definition = FAULT_CATALOG.get(code)
    family = definition.family if definition is not None else code.split("-")[0]
    occurrence = FaultOccurrence(
        code=code,
        family=family,
        correlation_id=str(uuid.uuid4()),
        occurred_at=datetime.now(timezone.utc),
        subsystem=subsystem,
        safe_context=_sanitize_context(context),
        http_status=http_status,
        provider_status=provider_status,
        runtime_mode=os.environ.get("STRATUS_RUNTIME_MODE"),
    )
    _recent_occurrences.append(occurrence)
    del _recent_occurrences[:-_MAX_RECENT_OCCURRENCES]
    print(
        f"[fault:{code}] {subsystem}: correlation_id={occurrence.correlation_id} "
        f"http_status={http_status} provider_status={provider_status} "
        f"context={occurrence.safe_context}"
    )
    return occurrence


def fault_lookup(code: str) -> str:
    """ "Dave, I got DATA-302" -> an immediate, precise answer."""
    definition = FAULT_CATALOG.get(code)
    if definition is None:
        return f"{code}: unrecognized fault code (not in the current catalog)"
    wired_note = (
        ""
        if definition.wired
        else " [registered, not yet triggered by any current code path]"
    )
    return f"{definition.code} ({definition.family}): {definition.summary}{wired_note}"


def recent_faults(limit: int = 20) -> list[FaultOccurrence]:
    return list(_recent_occurrences[-limit:])


def format_fault_catalog() -> str:
    lines = ["STRATUS Diagnostic Fault Codes", ""]
    families_in_order = ("AUTH", "FEED", "DATA", "ASK", "WATCH", "SYNC", "APP")
    for family in families_in_order:
        family_codes = [d for d in FAULT_CATALOG.values() if d.family == family]
        if not family_codes:
            continue
        lines.append(family)
        for d in sorted(family_codes, key=lambda d: d.code):
            suffix = "" if d.wired else " (registered, not yet triggered)"
            lines.append(f"  {d.code} -- {d.summary}{suffix}")
        lines.append("")
    lines.append("Explicitly NOT a fault:")
    for note in NOT_A_FAULT_NOTES:
        lines.append(f"  {note}")
    return "\n".join(lines).rstrip()


def format_recent_faults(limit: int = 20) -> str:
    occurrences = recent_faults(limit)
    if not occurrences:
        return "No faults recorded this process."
    lines = [f"Recent faults (most recent last, showing up to {limit})", ""]
    for occ in occurrences:
        lines.append(
            f"[{occ.occurred_at.isoformat()}] {occ.code} ({occ.subsystem}) "
            f"correlation_id={occ.correlation_id} "
            f"http_status={occ.http_status} provider_status={occ.provider_status} "
            f"context={occ.safe_context}"
        )
    return "\n".join(lines)


def reset_fault_state() -> None:
    """Test-only (and general-purpose "start over") hook, mirroring this
    codebase's existing reset_pipeline_state()/reset_notification_state()
    convention for process-lifetime state."""
    _recent_occurrences.clear()
