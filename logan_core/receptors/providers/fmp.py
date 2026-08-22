import os
from datetime import datetime, timezone
from typing import Optional

import httpx

from .base import EarningsReport, GradeChange, Quote

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

    def fetch_latest_earnings(self, entity_id: str) -> Optional[EarningsReport]:
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
                f"(HTTP 429): {response.text[:200]}"
            )
        if response.status_code != 200:
            raise FmpProviderError(
                f"FMP request failed for {entity_id!r}: HTTP {response.status_code} "
                f"{response.text[:200]}"
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

    def fetch_quote(self, entity_id: str) -> Optional[Quote]:
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
                f"(HTTP 429): {response.text[:200]}"
            )
        if response.status_code != 200:
            raise FmpProviderError(
                f"FMP request failed for {entity_id!r}: HTTP {response.status_code} "
                f"{response.text[:200]}"
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
        )

    def fetch_latest_grade_change(self, entity_id: str) -> Optional[GradeChange]:
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
                f"(HTTP 429): {response.text[:200]}"
            )
        if response.status_code != 200:
            raise FmpProviderError(
                f"FMP request failed for {entity_id!r}: HTTP {response.status_code} "
                f"{response.text[:200]}"
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
