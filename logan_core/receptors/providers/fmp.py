import os
from datetime import datetime, timezone
from typing import Optional

import httpx

from .base import EarningsReport

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

        # Most recent report by date, not by list position -- FMP's stable
        # docs describe this endpoint as already ordered most-recent-first,
        # but selecting by the actual date field is a stronger guarantee at
        # negligible cost, and doesn't depend on that ordering assumption
        # holding.
        latest = max(entries, key=lambda e: e["date"])
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
