import os
import time
from datetime import datetime, timezone
from typing import Callable, Optional

import httpx

from .base import CompanyProfile, EarningsReport, GradeChange, Quote

# Sprint 3.6.9 Remote STRATUS closeout -- provider-level TTL cache.
#
# Reconnaissance against the real hosted deployment (2026-08-23) measured
# ~10,080 real FMP calls/day from the background notification poller alone
# (3 tickers x an unconditional earnings check every 60s, plus quote/grade
# checks for any ticker currently showing a live earnings substitution) --
# already producing real HTTP 429s against FMP's 250-call/day free tier
# within ~25 minutes of the poller running, confirmed directly from logs.
# backend/app/logan_feed.py constructs a fresh FmpEarningsProvider/
# FmpMarketDataProvider instance on every single call (no persistent
# provider instance, unlike e.g. the shared Orchestrator) and had zero
# caching of any kind -- both the poller and every direct /v1/opportunities
# request independently re-fetched from FMP every time.
#
# Deliberately infrastructure-only, per the owner's explicit instruction:
# this wraps the raw HTTP fetch and nothing else -- trigger evaluation,
# qualification, confidence, and convergence never know a cache exists, and
# a cache hit produces byte-identical downstream behavior to a fresh fetch.
# Endpoint-appropriate TTLs, not one blanket value, per the owner's explicit
# guidance: earnings data changes quarterly (long TTL is free), analyst
# grades change infrequently (medium TTL), quotes are the one genuinely
# freshness-sensitive path (shorter TTL, still a large reduction from "every
# single call"). Only ever caches a real, successful provider response
# (including a real "no data" None -- see fetch_latest_earnings's own
# docstring on why that's not an error) -- FmpProviderError always
# propagates uncached, so a transient failure is retried on the very next
# call rather than being remembered as "no data" for a full TTL window.
EARNINGS_CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours -- quarterly-cadence data
GRADE_CACHE_TTL_SECONDS = 2 * 60 * 60  # 2 hours -- infrequent-change data
QUOTE_CACHE_TTL_SECONDS = 30 * 60  # 30 minutes -- the freshness-sensitive path
# Stock Opportunity Logic V2.2: sector/average-volume/beta change on the
# order of days-to-quarters, not intraday -- a long TTL is free and further
# reduces real FMP call volume (this is an *additional* endpoint call this
# block introduces; see the ADR's FMP capability audit).
PROFILE_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours
# V2.3A.1 field investigation (2026-08-28): a live production incident --
# NVDA's real earnings beat (reported 2026-08-26, correctly notification-
# worthy) intermittently vanished from the feed entirely ("Nothing to show
# yet") on polls where FMP's shared daily quota happened to be exhausted at
# the exact moment this entity's 6-hour earnings cache entry expired and a
# refetch was attempted. The report itself hadn't changed or gone stale --
# only the *refetch attempt* failed -- but get_or_fetch's original
# uncached-on-error behavior (correct for endpoints where staleness is
# actually misleading, e.g. quotes) meant a purely transient refetch failure
# was indistinguishable from "no qualifying earnings," dropping an entity
# that was still completely valid and recent. A quarterly earnings report
# does not become wrong 6 hours and 1 second after it was last confirmed --
# this grace window is what lets fetch_latest_earnings keep serving it
# through a provider outage instead of the opportunity silently
# disappearing. Deliberately NOT applied to quotes/grades (still fail
# immediately on a refetch error, no grace) -- those are the genuinely
# freshness-sensitive paths where serving stale data *would* be misleading.
EARNINGS_STALE_GRACE_SECONDS = 24 * 60 * 60  # 24 hours beyond the 6h TTL
# V2.2 hosted-validation follow-up (see fetch_benchmark_quote's own
# docstring): a market/sector benchmark quote is additional call volume on
# top of every live ticker's own quote/earnings/grades calls -- a long TTL
# here is what keeps that addition from meaningfully eating into FMP's
# free-tier daily quota. 4 hours is a deliberate middle ground: fresh enough
# for "is the market/sector up or down today" to stay meaningful, far
# cheaper than the 30-minute TTL an entity's own quote correctly needs.
BENCHMARK_QUOTE_CACHE_TTL_SECONDS = 4 * 60 * 60  # 4 hours

# 2026-08-29 field investigation: a persistent provider failure (a real HTTP
# 429 during hosted quota exhaustion, or FMP's stable /quote endpoint
# rejecting the Technology sector benchmark symbol XLK with a permanent
# HTTP 402 "Premium Query Parameter") was retried on every single poll --
# get_or_fetch previously never cached a failure at all, only ever a
# success. At the poller's 60-second cadence that is up to 1,440 wasted
# calls/day for one entity/endpoint pair during a sustained outage, on top
# of whatever the successful-response TTLs above already budget for.
#
# Two separate, explicit, conservative suppression windows, mirroring the
# same "endpoint-appropriate, not one blanket value" principle the
# success-side TTLs already use:
#   - A transient failure (429 rate limit, network error, a malformed
#     response) is retried at most once per 15 minutes -- long enough to
#     stop hammering FMP during an active outage, short enough that a real
#     recovery is still noticed the same hour, not the next day.
#   - A permanent/entitlement failure (401/402/403/404 -- "this exact
#     request is not going to start working on its own," not "the server
#     is temporarily overloaded") is retried at most once per 24 hours --
#     there is nothing to gain from checking more often, and something to
#     lose (quota spent on a request known not to succeed).
# Neither window ever caches the failure AS data: get_or_fetch still raises
# FmpProviderError on every suppressed retry (see below) -- a suppressed
# retry is indistinguishable to every caller from a fresh failed fetch, so
# provider_degraded/provider_failed propagation is completely unchanged.
TRANSIENT_FAILURE_SUPPRESSION_SECONDS = 15 * 60  # 15 minutes
PERMANENT_FAILURE_SUPPRESSION_SECONDS = 24 * 60 * 60  # 24 hours
_PERMANENT_FAILURE_STATUS_CODES = frozenset({401, 402, 403, 404})


class _FmpCacheEntry:
    __slots__ = ("value", "cached_at")

    def __init__(self, value: object, cached_at: float) -> None:
        self.value = value
        self.cached_at = cached_at


class _FmpFailureEntry:
    """Records only that a fetch failed and when/why -- never a value, never
    treated as data by anything downstream. Exists purely to decide whether
    the *next* call gets to retry the network or must wait out its
    suppression window; see get_or_fetch."""

    __slots__ = ("failed_at", "message", "status_code")

    def __init__(
        self, failed_at: float, message: str, status_code: Optional[int]
    ) -> None:
        self.failed_at = failed_at
        self.message = message
        self.status_code = status_code


class FmpResponseCache:
    """Process-lifetime TTL cache, shared across every FmpEarningsProvider/
    FmpMarketDataProvider instance by default (see `_shared_fmp_cache` below)
    -- this is what makes the background poller and direct /v1/opportunities
    requests genuinely share one cache rather than each maintaining their
    own, since backend/app/logan_feed.py constructs a fresh provider
    instance per call. `clock` is injectable (real callers use
    `time.monotonic`; tests inject a fake, controllable clock) so cache
    expiry is deterministically testable without real sleeping.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._entries: dict[tuple[str, str], _FmpCacheEntry] = {}
        self._failures: dict[tuple[str, str], _FmpFailureEntry] = {}
        self._clock = clock

    def get_or_fetch(
        self,
        endpoint: str,
        entity_id: str,
        ttl_seconds: float,
        fetch: Callable[[], object],
        stale_grace_seconds: float = 0.0,
    ) -> object:
        key = (endpoint, entity_id)
        now = self._clock()
        entry = self._entries.get(key)
        if entry is not None and (now - entry.cached_at) < ttl_seconds:
            return entry.value

        # 2026-08-29: a known-recent failure for this exact (endpoint,
        # entity_id) suppresses the network attempt entirely until its own
        # window elapses -- this is what stops a persistent 429/402 from
        # being retried every single poll (see the module-level constants'
        # docstring above `_FmpFailureEntry`). This is a decision about
        # whether to call `fetch()` at all, never a substitute for its
        # result: the two outcomes below are byte-identical to what this
        # function already did on a fresh failure -- serve a still-in-grace
        # stale value, or raise -- just without spending a real HTTP call to
        # get there again.
        failure = self._failures.get(key)
        if failure is not None:
            suppression_seconds = (
                PERMANENT_FAILURE_SUPPRESSION_SECONDS
                if failure.status_code in _PERMANENT_FAILURE_STATUS_CODES
                else TRANSIENT_FAILURE_SUPPRESSION_SECONDS
            )
            if (now - failure.failed_at) < suppression_seconds:
                if (
                    stale_grace_seconds > 0
                    and entry is not None
                    and (now - entry.cached_at) < ttl_seconds + stale_grace_seconds
                ):
                    return entry.value
                raise FmpProviderError(
                    f"[fmp-cache] {endpoint}/{entity_id}: suppressing retry of a "
                    f"known failure from {now - failure.failed_at:.0f}s ago "
                    f"(retries resume after {suppression_seconds:.0f}s total; "
                    f"last real attempt: {failure.message})",
                    status_code=failure.status_code,
                )

        # A raised FmpProviderError still propagates uncached-as-data by
        # default (stale_grace_seconds == 0, every pre-V2.3A.1 caller) --
        # never mistaken for a real "no data" response, never poisons the
        # cache for other callers sharing it. When a caller opts into a
        # grace window (see fetch_latest_earnings: a quarterly report
        # doesn't become wrong minutes after its TTL lapses) and a fetch
        # failure happens while a still-within-grace stale entry exists,
        # that entry is served instead -- its own `cached_at` is left
        # untouched, so the very next call still attempts a real refetch
        # rather than treating this as a fresh success.
        try:
            value = fetch()
        except FmpProviderError as exc:
            self._failures[key] = _FmpFailureEntry(
                failed_at=now,
                message=str(exc),
                status_code=getattr(exc, "status_code", None),
            )
            if (
                stale_grace_seconds > 0
                and entry is not None
                and (now - entry.cached_at) < ttl_seconds + stale_grace_seconds
            ):
                print(
                    f"[fmp-cache] {endpoint}/{entity_id}: refetch failed "
                    f"({exc}), serving stale cache (age={now - entry.cached_at:.0f}s) "
                    "rather than dropping a still-valid recent result"
                )
                return entry.value
            raise
        # A genuine success always clears any prior failure record -- the
        # negative state never outlives the condition that created it.
        self._failures.pop(key, None)
        self._entries[key] = _FmpCacheEntry(value=value, cached_at=now)
        return value

    def clear(self) -> None:
        self._entries.clear()
        self._failures.clear()

    def seed_stale_entry(
        self, endpoint: str, entity_id: str, value: object, age_seconds: float
    ) -> None:
        """V2.3A.1 field reliability work -- recovery-only primitive: pre-
        populates a cache entry as though it had been fetched `age_seconds`
        ago, without performing a fetch or touching TTL/grace decision logic
        itself (it only ever writes `self._entries`; `get_or_fetch`'s own
        comparisons are completely unmodified). Exists so a durably-
        persisted last-successful observation (see
        seed_earnings_from_durable_observation below) can seed this
        process-lifetime cache immediately after a fresh process start --
        before this existed, a caller with `stale_grace_seconds > 0` had
        nothing to fall back to until its own first successful fetch *this
        process*, meaning a provider outage spanning a restart was never
        bridgeable no matter how recent the real last observation actually
        was (confirmed live against the hosted deployment, 2026-08-29).

        `age_seconds` must be real wall-clock elapsed time since that
        original successful observation -- never this process's own uptime,
        a monotonic reading, or a file's mtime. This is the one place a
        durable, wall-clock timestamp is translated into this cache's
        internal monotonic `cached_at` bookkeeping, so every existing
        `(now - entry.cached_at) < ...` comparison downstream keeps working
        completely unchanged regardless of whether an entry came from a real
        fetch this process made or was recovered from durable storage.
        """
        self._entries[(endpoint, entity_id)] = _FmpCacheEntry(
            value=value, cached_at=self._clock() - age_seconds
        )


_shared_fmp_cache = FmpResponseCache()


def reset_fmp_cache() -> None:
    """Test-only (and general-purpose "start over") hook, mirroring this
    codebase's existing reset_pipeline_state()/reset_notification_state()
    convention for process-lifetime state.
    """
    _shared_fmp_cache.clear()


def seed_earnings_from_durable_observation(
    entity_id: str, report: EarningsReport, observed_at: datetime
) -> None:
    """V2.3A.1 field reliability work -- backend-startup-only recovery hook
    (see backend/app/earnings_cache_store.py and logan_feed.py's
    _get_orchestrator): seeds the shared, process-lifetime FmpResponseCache
    with the durably-persisted last-successful earnings observation for
    `entity_id`, so fetch_latest_earnings's stale-grace fallback has
    something to serve immediately after a fresh process start, even before
    any real fetch has been attempted this process's lifetime.

    `observed_at` must be the real wall-clock UTC moment the ORIGINAL fetch
    actually succeeded (see FmpEarningsProvider's own `on_successful_fetch`
    callback below, the only place that timestamp is captured) -- never this
    process's own start time. Age is computed fresh, right now, from that
    timestamp, which is what makes grace eligibility measure the true
    staleness of the underlying earnings data across any number of
    restarts, not "how long has this process happened to be running."
    """
    age_seconds = max((datetime.now(timezone.utc) - observed_at).total_seconds(), 0.0)
    _shared_fmp_cache.seed_stale_entry("earnings", entity_id, report, age_seconds)


# Sprint 3.6.6B — the first live market-data provider. Financial Modeling
# Prep's "stable" per-symbol earnings endpoint: historical earnings reports
# for one entity, most recent first, with actual-vs-estimated EPS already
# populated for reported quarters (unlike the broader earnings *calendar*
# endpoint, which is forward-looking and mostly null until a report lands).
FMP_BASE_URL = "https://financialmodelingprep.com/stable"
FMP_SOURCE_ID = "fmp"
FMP_SOURCE_NAME = "Financial Modeling Prep"
FMP_API_KEY_ENV_VAR = "FMP_API_KEY"

# Field-name note (Phase 1 research): FMP's officially documented field
# names for this endpoint are `epsActual`/`epsEstimated`, confirmed against
# multiple independent sources (site.financialmodelingprep.com's own
# "Earnings Report API" docs page and several third-party writeups quoting
# the same schema) -- the official docs page itself returns HTTP 403 to
# automated fetches, so this could not be verified against FMP's live docs
# directly. A different, older/legacy FMP endpoint (the earnings *calendar*,
# not this one) uses a plain `eps` key instead -- if FMP's actual response
# for this endpoint turns out to differ, EarningsReport.actual_eps/
# consensus_eps simply come back None (never a crash, never a fabricated
# value -- see _parse_entry below), and the live verification script makes
# that immediately visible. This is the one point of genuine external
# uncertainty in this implementation; see the Sprint 3.6.6B report.


def _redact(text: str, secret: str) -> str:
    """Sprint 3.6.8 Block 4 (beta-readiness hardening): the FMP API key is
    sent as a URL query param (`apikey=...`), not an auth header -- some
    APIs' error responses echo back an invalid credential verbatim in the
    error message (e.g. "Invalid API KEY: <key>"). Every error message this
    module builds from a real HTTP response body is passed through this
    first, so a real key can never end up in a raised exception's message
    (and therefore never in whatever a caller ends up logging/printing it
    to). A no-op when the secret doesn't appear in the text, which is the
    normal case.
    """
    if not secret:
        return text
    return text.replace(secret, "***REDACTED***")


class FmpProviderError(Exception):
    """Raised for any FMP request that didn't produce usable data: network
    failure, non-2xx HTTP status (including rate limiting), or a response
    shape that doesn't match what this adapter expects. Deliberately a
    raised exception, not a None return -- a caller must be able to tell
    "FMP has no earnings for this symbol" (a real None from
    fetch_latest_earnings) apart from "the FMP call itself failed" (this
    exception). No automatic fallback to fixture data happens anywhere in
    this class; a caller that wants one must do so explicitly and visibly.

    `status_code` is the real HTTP status that caused this (429, 402, ...)
    when one exists -- None for a network error or a malformed-response
    error, where there was no real response status to attach. FmpResponseCache
    reads this to decide how long to suppress a repeat of this exact failure
    (see TRANSIENT_FAILURE_SUPPRESSION_SECONDS/PERMANENT_FAILURE_SUPPRESSION_SECONDS
    above); nothing else in this module depends on it.
    """

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class FmpEarningsProvider:
    """Sprint 3.6.6B — the first live implementation of the EarningsProvider
    Protocol (see base.py). FMP-specific response structure terminates
    entirely inside this class: fetch_latest_earnings returns the same
    STRATUS-owned EarningsReport FixtureEarningsProvider does, and nothing
    downstream (receptors/stocks_earnings.py, trigger_detection/,
    world_model/, evidence_trust/, conclusion_confidence/) needs to know FMP
    exists.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = FMP_BASE_URL,
        client: Optional[httpx.Client] = None,
        cache: Optional[FmpResponseCache] = None,
        on_successful_fetch: Optional[
            Callable[[str, EarningsReport, datetime], None]
        ] = None,
    ) -> None:
        # API key comes only from environment configuration (explicit
        # `api_key` param is for tests to inject a fake one -- never a
        # hardcoded default, never read from source control). Resolved
        # eagerly (not lazily on first fetch) so a missing key fails loudly
        # at construction, not silently on the first real request.
        resolved_key = (
            api_key if api_key is not None else os.environ.get(FMP_API_KEY_ENV_VAR)
        )
        if not resolved_key:
            raise FmpProviderError(
                f"{FMP_API_KEY_ENV_VAR} is not set. FmpEarningsProvider requires a real "
                "API key from environment configuration -- see the Sprint 3.6.6B report "
                "for how to obtain one; there is no fixture/demo fallback for this provider."
            )
        self._api_key = resolved_key
        self._base_url = base_url
        # Callers may inject their own httpx.Client (tests use this to mock
        # transport -- see test_fmp_provider.py); defaults to a real client
        # with a bounded timeout so a hung connection can't block forever.
        self._client = client or httpx.Client(timeout=10.0)
        # Sprint 3.6.9 Remote STRATUS closeout: defaults to the shared,
        # process-lifetime module cache (see FmpResponseCache's own
        # docstring) -- every production caller gets real cross-instance
        # sharing without doing anything special. Tests inject an isolated
        # instance (often with a fake clock) so cache state/expiry never
        # leaks between test cases.
        self._cache = cache if cache is not None else _shared_fmp_cache
        # V2.3A.1 field reliability work: optional, backend-owned durable-
        # persistence hook (see backend/app/earnings_cache_store.py) -- never
        # None-checked by anything in this class beyond _fetch_and_observe
        # below, and every existing caller/test that doesn't pass it gets
        # byte-for-byte unchanged behavior.
        self._on_successful_fetch = on_successful_fetch

    def fetch_latest_earnings(self, entity_id: str) -> Optional[EarningsReport]:
        return self._cache.get_or_fetch(
            "earnings",
            entity_id,
            EARNINGS_CACHE_TTL_SECONDS,
            lambda: self._fetch_and_observe(entity_id),
            stale_grace_seconds=EARNINGS_STALE_GRACE_SECONDS,
        )  # type: ignore[return-value]

    def _fetch_and_observe(self, entity_id: str) -> Optional[EarningsReport]:
        """V2.3A.1 field reliability work: thin wrapper around
        `_fetch_latest_earnings_uncached` so `on_successful_fetch` fires
        exactly once per genuine, fresh, successful HTTP round-trip --
        never on a TTL cache hit (`get_or_fetch` returns early on those
        without ever calling this lambda at all -- see its own docstring)
        and never on a failure (an FmpProviderError raised inside
        `_fetch_latest_earnings_uncached` propagates from here before this
        method's own success path runs, so a failed response can never reach
        durable storage -- see EarningsCacheStore's own docstring on why
        that matters). A genuine "no earnings on file" result (`None`, not
        an error) deliberately does NOT invoke the callback either -- there
        is no payload to persist for restart-recovery purposes, matching
        earnings_cache_store.py's "minimum successful payload" scope.
        """
        report = self._fetch_latest_earnings_uncached(entity_id)
        if report is not None and self._on_successful_fetch is not None:
            self._on_successful_fetch(entity_id, report, datetime.now(timezone.utc))
        return report

    def _fetch_latest_earnings_uncached(
        self, entity_id: str
    ) -> Optional[EarningsReport]:
        try:
            response = self._client.get(
                f"{self._base_url}/earnings",
                params={"symbol": entity_id, "apikey": self._api_key},
            )
        except httpx.RequestError as exc:
            raise FmpProviderError(
                f"FMP request failed for {entity_id!r}: network error ({exc})"
            ) from exc

        if response.status_code == 429:
            raise FmpProviderError(
                f"FMP rate limit hit fetching earnings for {entity_id!r} "
                f"(HTTP 429): {_redact(response.text[:200], self._api_key)}",
                status_code=429,
            )
        if response.status_code != 200:
            raise FmpProviderError(
                f"FMP request failed for {entity_id!r}: HTTP {response.status_code} "
                f"{_redact(response.text[:200], self._api_key)}",
                status_code=response.status_code,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise FmpProviderError(
                f"FMP response for {entity_id!r} was not valid JSON: {exc}"
            ) from exc

        if not isinstance(payload, list):
            raise FmpProviderError(
                f"FMP response for {entity_id!r} was not a list as expected "
                f"(got {type(payload).__name__})"
            )
        if len(payload) == 0:
            # A real, legitimate "no data" case -- not an error. FMP has no
            # earnings history for this symbol.
            return None

        entries = [e for e in payload if isinstance(e, dict) and e.get("date")]
        if not entries:
            raise FmpProviderError(
                f"FMP response for {entity_id!r} contained no usable entries "
                f"(malformed items, or all missing a 'date' field)"
            )

        # Sprint 3.6.6B live verification finding: this endpoint returns both
        # already-reported AND upcoming/scheduled earnings dates for a
        # symbol in the same list (confirmed live against NVDA -- the
        # max-by-date entry was a future scheduled report with
        # epsEstimated populated but epsActual still null, since it hadn't
        # happened yet). "Latest earnings" for STOCK_EARNINGS_BEAT purposes
        # means the latest *reported* quarter, not the latest *scheduled*
        # one -- prefer the most recent entry that actually has epsActual;
        # only fall back to the overall most-recent-by-date entry if no
        # entry has been reported yet (an honest "nothing reported" result,
        # not a crash).
        reported = [e for e in entries if e.get("epsActual") is not None]
        candidates = reported if reported else entries
        latest = max(candidates, key=lambda e: e["date"])
        return self._parse_entry(entity_id, latest)

    def _parse_entry(self, entity_id: str, entry: dict) -> EarningsReport:
        try:
            report_date = datetime.strptime(entry["date"], "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except (KeyError, ValueError) as exc:
            raise FmpProviderError(
                f"FMP earnings entry for {entity_id!r} had an unparseable 'date': {exc}"
            ) from exc

        # See the module-level field-name note above: epsActual/epsEstimated
        # are the researched, but not officially-doc-confirmed, field names
        # for this endpoint. .get() (never direct indexing) means an
        # unexpected key name degrades to "missing," never a crash or a
        # fabricated value.
        return EarningsReport(
            entity_id=entry.get("symbol", entity_id),
            actual_eps=entry.get("epsActual"),
            consensus_eps=entry.get("epsEstimated"),
            fiscal_quarter=entry.get("fiscalDateEnding"),
            # FMP's earnings endpoint has no guidance data -- guidance_revised/
            # guidance_delta_pct stay at EarningsReport's own None default,
            # never fabricated.
            report_timestamp=report_date,
            source_id=FMP_SOURCE_ID,
            source_name=FMP_SOURCE_NAME,
        )


class FmpMarketDataProvider:
    """Sprint 3.6.7 -- generalizes FmpEarningsProvider's pattern (provider-
    specific structure terminates entirely inside this class) across two
    more stock signal types that share one authenticated client: real-time-ish
    quotes (price/change) and analyst rating changes. A separate class from
    FmpEarningsProvider, not a merge -- avoids touching that proven,
    live-verified class at all; the two share only the module-level
    constants (FMP_BASE_URL, FMP_SOURCE_ID/NAME, FMP_API_KEY_ENV_VAR) and
    FmpProviderError.

    Unlike EarningsReport's fields (legitimately sparse -- a company may
    genuinely have no guidance data yet), a quote's price/previous_close/
    change_pct and a grade change's action are expected on every valid
    response entry for a real symbol; a response missing them indicates a
    malformed/unexpected shape, not "no data yet" -- so those raise
    FmpProviderError loudly here rather than silently degrading to None,
    consistent with how this file already treats a malformed list/JSON shape
    elsewhere (never a fabricated value, but also never a silent no-op on a
    response that doesn't match what this adapter expects).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = FMP_BASE_URL,
        client: Optional[httpx.Client] = None,
        cache: Optional[FmpResponseCache] = None,
    ) -> None:
        resolved_key = (
            api_key if api_key is not None else os.environ.get(FMP_API_KEY_ENV_VAR)
        )
        if not resolved_key:
            raise FmpProviderError(
                f"{FMP_API_KEY_ENV_VAR} is not set. FmpMarketDataProvider requires a "
                "real API key from environment configuration -- there is no "
                "fixture/demo fallback for this provider."
            )
        self._api_key = resolved_key
        self._base_url = base_url
        self._client = client or httpx.Client(timeout=10.0)
        # See FmpEarningsProvider.__init__'s identical comment above.
        self._cache = cache if cache is not None else _shared_fmp_cache

    def fetch_quote(self, entity_id: str) -> Optional[Quote]:
        return self._cache.get_or_fetch(
            "quote",
            entity_id,
            QUOTE_CACHE_TTL_SECONDS,
            lambda: self._fetch_quote_uncached(entity_id),
        )  # type: ignore[return-value]

    def fetch_benchmark_quote(self, entity_id: str) -> Optional[Quote]:
        """Stock Opportunity Logic V2.2 (Evidence + Trajectory Enrichment):
        the SAME quote fetch/parse as `fetch_quote()`, cached separately
        under a much longer TTL. A market/sector benchmark (SPY, a sector
        ETF) doesn't need `fetch_quote()`'s 30-minute freshness the way an
        entity's *own* quote does for real-time trigger detection -- a
        benchmark's relative standing changes slowly enough that hours-old
        data is still meaningful context. Found live, 2026-08-25/26: adding
        SPY + sector-ETF fetches to every live-ticker poll under the tight
        30-minute TTL materially increased daily FMP call volume and
        contributed to exhausting the hosted deployment's free-tier daily
        quota (a real `HTTP 429` observed across every endpoint, not just
        quotes) -- this method exists specifically to undo that regression
        without touching the freshness of any entity's own price data.
        """
        return self._cache.get_or_fetch(
            "benchmark_quote",
            entity_id,
            BENCHMARK_QUOTE_CACHE_TTL_SECONDS,
            lambda: self._fetch_quote_uncached(entity_id),
        )  # type: ignore[return-value]

    def _fetch_quote_uncached(self, entity_id: str) -> Optional[Quote]:
        try:
            response = self._client.get(
                f"{self._base_url}/quote",
                params={"symbol": entity_id, "apikey": self._api_key},
            )
        except httpx.RequestError as exc:
            raise FmpProviderError(
                f"FMP request failed for {entity_id!r}: network error ({exc})"
            ) from exc

        if response.status_code == 429:
            raise FmpProviderError(
                f"FMP rate limit hit fetching quote for {entity_id!r} "
                f"(HTTP 429): {_redact(response.text[:200], self._api_key)}",
                status_code=429,
            )
        if response.status_code != 200:
            raise FmpProviderError(
                f"FMP request failed for {entity_id!r}: HTTP {response.status_code} "
                f"{_redact(response.text[:200], self._api_key)}",
                status_code=response.status_code,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise FmpProviderError(
                f"FMP quote response for {entity_id!r} was not valid JSON: {exc}"
            ) from exc

        if not isinstance(payload, list):
            raise FmpProviderError(
                f"FMP quote response for {entity_id!r} was not a list as expected "
                f"(got {type(payload).__name__})"
            )
        if len(payload) == 0:
            # A real, legitimate "no data" case -- FMP has no quote for this symbol.
            return None

        entry = payload[0]
        if not isinstance(entry, dict):
            raise FmpProviderError(
                f"FMP quote response for {entity_id!r} contained a non-dict entry"
            )

        price = entry.get("price")
        previous_close = entry.get("previousClose")
        change_pct = entry.get("changePercentage")
        timestamp = entry.get("timestamp")
        if (
            price is None
            or previous_close is None
            or change_pct is None
            or timestamp is None
        ):
            raise FmpProviderError(
                f"FMP quote response for {entity_id!r} was missing one of "
                "price/previousClose/changePercentage/timestamp"
            )

        return Quote(
            entity_id=entry.get("symbol", entity_id),
            price=price,
            previous_close=previous_close,
            change_pct=change_pct,
            quote_timestamp=datetime.fromtimestamp(timestamp, tz=timezone.utc),
            source_id=FMP_SOURCE_ID,
            source_name=FMP_SOURCE_NAME,
            volume=entry.get("volume"),
        )

    def fetch_latest_grade_change(self, entity_id: str) -> Optional[GradeChange]:
        return self._cache.get_or_fetch(
            "grades",
            entity_id,
            GRADE_CACHE_TTL_SECONDS,
            lambda: self._fetch_latest_grade_change_uncached(entity_id),
        )  # type: ignore[return-value]

    def _fetch_latest_grade_change_uncached(
        self, entity_id: str
    ) -> Optional[GradeChange]:
        try:
            response = self._client.get(
                f"{self._base_url}/grades",
                params={"symbol": entity_id, "apikey": self._api_key},
            )
        except httpx.RequestError as exc:
            raise FmpProviderError(
                f"FMP request failed for {entity_id!r}: network error ({exc})"
            ) from exc

        if response.status_code == 429:
            raise FmpProviderError(
                f"FMP rate limit hit fetching grades for {entity_id!r} "
                f"(HTTP 429): {_redact(response.text[:200], self._api_key)}",
                status_code=429,
            )
        if response.status_code != 200:
            raise FmpProviderError(
                f"FMP request failed for {entity_id!r}: HTTP {response.status_code} "
                f"{_redact(response.text[:200], self._api_key)}",
                status_code=response.status_code,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise FmpProviderError(
                f"FMP grades response for {entity_id!r} was not valid JSON: {exc}"
            ) from exc

        if not isinstance(payload, list):
            raise FmpProviderError(
                f"FMP grades response for {entity_id!r} was not a list as expected "
                f"(got {type(payload).__name__})"
            )
        if len(payload) == 0:
            return None

        entries = [e for e in payload if isinstance(e, dict) and e.get("date")]
        if not entries:
            raise FmpProviderError(
                f"FMP grades response for {entity_id!r} contained no usable entries"
            )

        # This endpoint's entries are already most-recent-first in practice
        # (live-verified, 2026-08-21), but sort explicitly rather than trust
        # response ordering -- the most recent rating action is the one that
        # matters for a fire condition keyed to "did this just change."
        latest = max(entries, key=lambda e: e["date"])
        return self._parse_grade_entry(entity_id, latest)

    def _parse_grade_entry(self, entity_id: str, entry: dict) -> GradeChange:
        try:
            action_date = datetime.strptime(entry["date"], "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except (KeyError, ValueError) as exc:
            raise FmpProviderError(
                f"FMP grades entry for {entity_id!r} had an unparseable 'date': {exc}"
            ) from exc

        action = entry.get("action")
        if not action:
            raise FmpProviderError(
                f"FMP grades entry for {entity_id!r} was missing 'action'"
            )

        return GradeChange(
            entity_id=entry.get("symbol", entity_id),
            grading_firm=entry.get("gradingCompany", "unknown"),
            previous_rating=entry.get("previousGrade"),
            new_rating=entry.get("newGrade"),
            action=action,
            action_date=action_date,
            source_id=FMP_SOURCE_ID,
            source_name=FMP_SOURCE_NAME,
        )

    def fetch_company_profile(self, entity_id: str) -> Optional[CompanyProfile]:
        """Stock Opportunity Logic V2.2: FMP's `/profile` endpoint, on the
        same base URL/API key/plan as `/quote` and `/grades` -- confirmed
        live, 2026-08-24/25, to already return `averageVolume`, `beta`,
        `sector`, and `industry` on the free tier this codebase already
        uses. No new vendor, no new paid tier, no new secret -- see the
        ADR's FMP capability audit for the full live-verified finding.
        """
        return self._cache.get_or_fetch(
            "profile",
            entity_id,
            PROFILE_CACHE_TTL_SECONDS,
            lambda: self._fetch_company_profile_uncached(entity_id),
        )  # type: ignore[return-value]

    def _fetch_company_profile_uncached(
        self, entity_id: str
    ) -> Optional[CompanyProfile]:
        try:
            response = self._client.get(
                f"{self._base_url}/profile",
                params={"symbol": entity_id, "apikey": self._api_key},
            )
        except httpx.RequestError as exc:
            raise FmpProviderError(
                f"FMP request failed for {entity_id!r}: network error ({exc})"
            ) from exc

        if response.status_code == 429:
            raise FmpProviderError(
                f"FMP rate limit hit fetching profile for {entity_id!r} "
                f"(HTTP 429): {_redact(response.text[:200], self._api_key)}",
                status_code=429,
            )
        if response.status_code != 200:
            raise FmpProviderError(
                f"FMP request failed for {entity_id!r}: HTTP {response.status_code} "
                f"{_redact(response.text[:200], self._api_key)}",
                status_code=response.status_code,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise FmpProviderError(
                f"FMP profile response for {entity_id!r} was not valid JSON: {exc}"
            ) from exc

        if not isinstance(payload, list):
            raise FmpProviderError(
                f"FMP profile response for {entity_id!r} was not a list as expected "
                f"(got {type(payload).__name__})"
            )
        if len(payload) == 0:
            # A real, legitimate "no data" case -- FMP has no profile for
            # this symbol.
            return None

        entry = payload[0]
        if not isinstance(entry, dict):
            raise FmpProviderError(
                f"FMP profile response for {entity_id!r} contained a non-dict entry"
            )

        # Every field here is genuinely optional -- unlike Quote/GradeChange
        # (where a missing core field indicates a malformed response), a
        # profile legitimately may not carry all of sector/averageVolume/
        # beta for every symbol (e.g. a newly-listed or thinly-covered
        # name). Never fabricated when absent.
        return CompanyProfile(
            entity_id=entry.get("symbol", entity_id),
            sector=entry.get("sector"),
            industry=entry.get("industry"),
            average_volume=entry.get("averageVolume"),
            beta=entry.get("beta"),
            source_id=FMP_SOURCE_ID,
            source_name=FMP_SOURCE_NAME,
        )
