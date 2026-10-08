"""ADR-084 -- SEC EDGAR as the single source for the Beta 1 company-filing
catalyst path.

Reads one structured endpoint, the per-company submissions index
(`https://data.sec.gov/submissions/CIK##########.json`), and maps recent
Form 8-K and 8-K/A rows into STRATUS's own `CompanyFiling` shape. Nothing
provider-specific leaves this module, and no filing text is fetched or read.

Fail closed:
- No User-Agent configured -> the provider cannot be constructed and no
  request is ever made. The SEC requires automated clients to identify
  themselves; the value is operator configuration, never hard-coded.
- A ticker without a verified CIK is never fetched.
- The issuer is cross-checked: a response whose own ticker list does not
  contain the requested ticker yields nothing.
"""

import re
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

import httpx

from .base import CompanyFiling

SEC_SOURCE_ID = "sec_filing"  # the existing SOURCE_REPUTATION_REGISTRY key
SEC_SOURCE_NAME = "SEC EDGAR"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}"

# Filings change a few times a quarter per company; the index is fetched at
# most this often per company. Provisional (REV4 2A.8).
SEC_FILINGS_CACHE_TTL_SECONDS = 30 * 60
# The SEC's fair-access limit is 10 requests per second across all clients
# of one operator. This stays far below it.
SEC_MIN_SECONDS_BETWEEN_REQUESTS = 0.25
SEC_REQUEST_TIMEOUT_SECONDS = 6.0

# Ticker -> CIK for the governed cohort. Each was verified on 2026-10-07 by
# fetching the company's submissions index and confirming the response's own
# `tickers` list contains the ticker. A ticker absent from this table is not
# fetched; extending the Universe means extending and re-verifying this.
CIK_BY_TICKER: dict[str, str] = {
    "AAPL": "0000320193",
    "ABBV": "0001551152",
    "ABT": "0000001800",
    "ACN": "0001467373",
    "ADBE": "0000796343",
    "AMGN": "0000318154",
    "AMT": "0001053507",
    "AMZN": "0001018724",
    "AXP": "0000004962",
    "BA": "0000012927",
    "BAC": "0000070858",
    "BKNG": "0001075531",
    "BLK": "0002012383",
    "CAT": "0000018230",
    "CL": "0000021665",
    "CMCSA": "0001166691",
    "COP": "0001163165",
    "COST": "0000909832",
    "CVX": "0000093410",
    "DE": "0000315189",
    "DIS": "0001744489",
    "DUK": "0001326160",
    "GM": "0001467858",
    "GOOGL": "0001652044",
    "KO": "0000021344",
    "LIN": "0001707925",
    "NEE": "0000753308",
    "PLD": "0001045609",
    "SHW": "0000089800",
    "SLB": "0000087347",
}


class SecProviderError(Exception):
    """Any failure to obtain a usable filings index. Callers treat it as
    "no filing signal this poll", never as a reason to fail the feed."""


_CONTACT_PATTERN = re.compile(r"contact=([^\s;<>@]+@[^\s;<>@]+\.[^\s;<>@]+)")


def validate_sec_user_agent(value: Optional[str]) -> str:
    """The SEC asks automated clients to identify the operator and give a
    contact address. A valid value names the operator and carries
    `contact=<address>`, for example
    `STRATUS Beta 1 / Garris Engineering LLC; contact=ops@example.com`.
    Anything else -- empty, no contact, or a placeholder left unfilled --
    is refused, and the provider then makes no request at all.
    """
    text = (value or "").strip()
    if not text:
        raise SecProviderError(
            "no SEC User-Agent configured; the SEC filings provider is disabled"
        )
    if "<" in text or ">" in text:
        raise SecProviderError("SEC User-Agent still contains a placeholder")
    match = _CONTACT_PATTERN.search(text)
    if match is None:
        raise SecProviderError("SEC User-Agent has no contact=<address>")
    operator = text[: match.start()].strip(" ;/")
    if len(operator) < 3:
        raise SecProviderError("SEC User-Agent does not name the operator")
    return text


def _parse_accepted(value: object) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def parse_submissions(payload: object, ticker: str, cik: str) -> list[CompanyFiling]:
    """Pure mapping of one submissions-index payload into CompanyFiling
    rows (8-K and 8-K/A only). Raises SecProviderError when the payload is
    not the expected shape or belongs to a different issuer."""
    if not isinstance(payload, dict):
        raise SecProviderError("submissions payload is not an object")
    tickers = payload.get("tickers")
    if not isinstance(tickers, list) or ticker not in tickers:
        raise SecProviderError(f"issuer mismatch for {ticker}")
    recent = (payload.get("filings") or {}).get("recent")
    if not isinstance(recent, dict):
        raise SecProviderError("submissions payload has no recent filings")
    forms = recent.get("form")
    if not isinstance(forms, list):
        raise SecProviderError("submissions payload has no form list")

    def column(name: str) -> list:
        values = recent.get(name)
        return values if isinstance(values, list) and len(values) == len(forms) else []

    accessions = column("accessionNumber")
    accepted = column("acceptanceDateTime")
    filing_dates = column("filingDate")
    report_dates = column("reportDate")
    items = column("items")
    documents = column("primaryDocument")

    filings: list[CompanyFiling] = []
    for index, form in enumerate(forms):
        if form not in ("8-K", "8-K/A"):
            continue
        accession = accessions[index] if accessions else None
        document = documents[index] if documents else None
        url = None
        if accession and document:
            url = SEC_ARCHIVE_URL.format(
                cik=int(cik), accession=accession.replace("-", ""), document=document
            )
        filings.append(
            CompanyFiling(
                entity_id=ticker,
                issuer_ticker=ticker,
                issuer_cik=cik,
                form=form,
                items=(items[index] if items else "") or "",
                accession_number=accession or None,
                accepted_at=_parse_accepted(accepted[index] if accepted else None),
                filing_date=(filing_dates[index] if filing_dates else None) or None,
                report_date=(report_dates[index] if report_dates else None) or None,
                filing_url=url,
                source_id=SEC_SOURCE_ID,
                source_name=SEC_SOURCE_NAME,
            )
        )
    return filings


class SecEdgarFilingsProvider:
    """One process-wide instance is intended: the cache and the pacing clock
    are per instance."""

    def __init__(
        self,
        *,
        user_agent: Optional[str],
        client: Optional[httpx.Client] = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._user_agent = validate_sec_user_agent(user_agent)
        self._client = client or httpx.Client(timeout=SEC_REQUEST_TIMEOUT_SECONDS)
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._cache: dict[str, tuple[float, list[CompanyFiling]]] = {}
        self._last_success: dict[str, float] = {}
        self._last_request_at: Optional[float] = None

    def last_successful_fetch_age_seconds(self, ticker: str) -> Optional[float]:
        """Seconds since this company's index was last fetched successfully,
        or None if it never has been -- the freshness clock (ADR-075)."""
        at = self._last_success.get(ticker)
        return None if at is None else max(self._clock() - at, 0.0)

    def fetch_recent_filings(self, ticker: str) -> list[CompanyFiling]:
        cik = CIK_BY_TICKER.get(ticker)
        if cik is None:
            raise SecProviderError(f"no verified CIK for {ticker}")
        with self._lock:
            cached = self._cache.get(ticker)
            now = self._clock()
            if cached is not None and now - cached[0] < SEC_FILINGS_CACHE_TTL_SECONDS:
                return list(cached[1])
            if self._last_request_at is not None:
                wait = SEC_MIN_SECONDS_BETWEEN_REQUESTS - (now - self._last_request_at)
                if wait > 0:
                    self._sleep(wait)
            self._last_request_at = self._clock()
            try:
                response = self._client.get(
                    SEC_SUBMISSIONS_URL.format(cik=cik),
                    headers={
                        "User-Agent": self._user_agent,
                        "Accept": "application/json",
                    },
                )
            except httpx.HTTPError as exc:
                raise SecProviderError(f"request failed: {type(exc).__name__}") from exc
            if response.status_code != 200:
                raise SecProviderError(f"unexpected status {response.status_code}")
            try:
                payload = response.json()
            except ValueError as exc:
                raise SecProviderError("response was not JSON") from exc
            filings = parse_submissions(payload, ticker, cik)
            stamp = self._clock()
            self._cache[ticker] = (stamp, filings)
            self._last_success[ticker] = stamp
            return list(filings)


def recent_window(filings: list[CompanyFiling], now: datetime, days: int) -> list:
    """Filings accepted within the last `days`, newest first."""
    cutoff = now - timedelta(days=days)
    kept = [f for f in filings if f.accepted_at is not None and f.accepted_at >= cutoff]
    return sorted(kept, key=lambda f: f.accepted_at, reverse=True)
