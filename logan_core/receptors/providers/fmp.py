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


class _FmpCacheEntry:
    __slots__ = ("value", "cached_at")

    def __init__(self, value: object, cached_at: float) -> None:
        self.value = value
        self.cached_at = cached_at


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
        self._clock = clock

    def get_or_fetch(
        self,
        endpoint: str,
        entity_id: str,
        ttl_seconds: float,
        fetch: Callable[[], object],
    ) -> object:
        key = (endpoint, entity_id)
        now = self._clock()
        entry = self._entries.get(key)
        if entry is not None and (now - entry.cached_at) < ttl_seconds:
            return entry.value

        # Deliberately not try/except-wrapped: a raised FmpProviderError
        # propagates straight out, uncached, so it is never mistaken for a
        # real "no data" response and never poisons the cache for other
        # callers sharing it.
        value = fetch()
        self._entries[key] = _FmpCacheEntry(value=value, cached_at=now)
        return value

    def clear(self) -> None:
        self._entries.clear()


_shared_fmp_cache = FmpResponseCache()


def reset_fmp_cache() -> None:
    """Test-only (and general-purpose "start over") hook, mirroring this
    codebase's existing reset_pipeline_state()/reset_notification_state()
    convention for process-lifetime state.
    """
    _shared_fmp_cache.clear()


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
    """


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

    def fetch_latest_earnings(self, entity_id: str) -> Optional[EarningsReport]:
        return self._cache.get_or_fetch(
            "earnings",
            entity_id,
            EARNINGS_CACHE_TTL_SECONDS,
            lambda: self._fetch_latest_earnings_uncached(entity_id),
        )  # type: ignore[return-value]

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
                f"(HTTP 429): {_redact(response.text[:200], self._api_key)}"
            )
        if response.status_code != 200:
            raise FmpProviderError(
                f"FMP request failed for {entity_id!r}: HTTP {response.status_code} "
                f"{_redact(response.text[:200], self._api_key)}"
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
                f"(HTTP 429): {_redact(response.text[:200], self._api_key)}"
            )
        if response.status_code != 200:
            raise FmpProviderError(
                f"FMP request failed for {entity_id!r}: HTTP {response.status_code} "
                f"{_redact(response.text[:200], self._api_key)}"
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
                f"(HTTP 429): {_redact(response.text[:200], self._api_key)}"
            )
        if response.status_code != 200:
            raise FmpProviderError(
                f"FMP request failed for {entity_id!r}: HTTP {response.status_code} "
                f"{_redact(response.text[:200], self._api_key)}"
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
                f"(HTTP 429): {_redact(response.text[:200], self._api_key)}"
            )
        if response.status_code != 200:
            raise FmpProviderError(
                f"FMP request failed for {entity_id!r}: HTTP {response.status_code} "
                f"{_redact(response.text[:200], self._api_key)}"
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
