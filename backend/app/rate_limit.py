"""Sprint 3.6.9 -- Persistent Mobile Identity + Beta Security Boundary:
minimal, in-memory, vendor-neutral rate limiting for the hosted beta's most
cost-sensitive/expensive routes.

Found during the hosted attack-surface review that motivated this pass: the
API had zero request throttling anywhere. The most concrete, quantifiable
risk is `/v1/ask` -- it can trigger a real, metered Anthropic API call per
grounded question (`STRATUS_LLM_ASK`, enabled on the hosted beta this same
session) -- with no limit, an automated caller could run up real external
cost with nothing to stop it. `/v1/opportunities` is the next most
expensive (a full pipeline run per call, even though the FMP-facing side is
now cached -- see ADR-062).

Deliberately simple: a fixed-window counter per (route, user_id),
process-lifetime, in-memory only -- no new infrastructure (no Redis, no
external rate-limiting service), matching this codebase's existing
in-memory-state precedent (AttentionState, notification dedup, etc.). This
is defensive-in-depth for the current beta's scale, not a hard scaling
requirement -- see docs/DECISIONS.md's Sprint 3.6.9 Mobile Identity + Beta
Security ADR for the full reasoning, including why per-`user_id` (not
per-IP) is the right key now that a real per-install identity exists: every
caller without a spoofed/legitimate identity collapses to the same shared
`BETA_ANONYMOUS_USER_ID` bucket (see user_context.py), so anonymous/
scripted traffic is collectively throttled together, while distinct real
installs each get their own independent budget.
"""

import time

from fastapi import HTTPException

RATE_LIMIT_DETAIL = "Too many requests -- please slow down and try again in a moment."


class _FixedWindowLimiter:
    def __init__(self) -> None:
        # (route, user_id) -> (window_start_monotonic, count_this_window)
        self._counters: dict[tuple[str, str], tuple[float, int]] = {}

    def check(
        self, route: str, user_id: str, max_requests: int, window_seconds: float
    ) -> None:
        key = (route, user_id)
        now = time.monotonic()
        window_start, count = self._counters.get(key, (now, 0))

        if now - window_start >= window_seconds:
            # Window has elapsed -- starts a fresh one, counting this request.
            self._counters[key] = (now, 1)
            return

        if count >= max_requests:
            raise HTTPException(status_code=429, detail=RATE_LIMIT_DETAIL)

        self._counters[key] = (window_start, count + 1)

    def reset(self) -> None:
        self._counters.clear()


_limiter = _FixedWindowLimiter()


def check_rate_limit(
    route: str, user_id: str, max_requests: int, window_seconds: float
) -> None:
    """Raises HTTPException(429) if `user_id` has exceeded `max_requests`
    within the current `window_seconds` window for `route`; otherwise
    records this request and returns normally. Call as the first line of a
    route body, after `user_id` is already resolved.
    """
    _limiter.check(route, user_id, max_requests, window_seconds)


def reset_rate_limits() -> None:
    """Test-only (and general-purpose "start over") hook, mirroring this
    codebase's existing reset_pipeline_state()/reset_notification_state()/
    reset_fmp_cache() convention for process-lifetime state.
    """
    _limiter.reset()
