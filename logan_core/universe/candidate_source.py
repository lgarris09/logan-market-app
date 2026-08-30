"""Universe Manager V1a Block 2 -- the versioned, replaceable candidate
source. A bounded candidate list only -- never an investment
recommendation, never STRATUS's preferred-stock list, never a signal of
opportunity quality on its own. Universe eligibility (eligibility.py)
still has to accept or reject each entry.

V1 canonical source: a versioned S&P 100 constituent snapshot. Honest V1a
scope note: this codebase has no licensed index-data provider integration
(that would be full index-ingestion infrastructure, explicitly out of
scope for V1a) -- `_SP100_V1` below is a STRATUS-curated approximation of
well-established S&P 100 constituent membership, not a live feed from an
index provider. It exists to prove the real mechanism this block actually
requires (a versioned, reproducible, metadata-complete candidate list a
downstream eligibility/cohort pass can consume) -- replacing it with a
real licensed snapshot later is a data change to this one file (or a new
version registered below), never a re-architecture.

Refresh cadence (Block 2): monthly, by convention -- registering a new
`source_version` here. An updated snapshot must never silently rewrite a
past version's membership: `_SNAPSHOT_REGISTRY` keeps every version its own
immutable entry, and `load_candidate_snapshot(version=...)` always returns
byte-identical data for a version that has already been published.
"""

from datetime import date, datetime, timezone

from logan_core.contracts import CandidateSecurity, CandidateSourceSnapshot

CANDIDATE_SOURCE_ID = "sp100_snapshot"

# (symbol, sector, market_cap_band) -- sector strings match CompanyProfile.
# sector's own established convention (a plain string, not a closed enum);
# market_cap_band is a coarse V1a diversity input, not a claim of precise
# valuation. "mega" here means "one of the largest ~25 names in this
# snapshot," "large" covers the rest -- every entry in this snapshot is
# large-cap-or-larger by construction (S&P 100 membership).
_SP100_V1_ENTRIES: tuple[tuple[str, str, str], ...] = (
    # Technology
    ("AAPL", "Technology", "mega"),
    ("MSFT", "Technology", "mega"),
    ("NVDA", "Technology", "mega"),
    ("AVGO", "Technology", "mega"),
    ("ORCL", "Technology", "mega"),
    ("CRM", "Technology", "large"),
    ("ADBE", "Technology", "large"),
    ("CSCO", "Technology", "large"),
    ("ACN", "Technology", "large"),
    ("AMD", "Technology", "large"),
    ("IBM", "Technology", "large"),
    ("INTC", "Technology", "large"),
    ("TXN", "Technology", "large"),
    ("QCOM", "Technology", "large"),
    ("NOW", "Technology", "large"),
    ("INTU", "Technology", "large"),
    ("AMAT", "Technology", "large"),
    ("MU", "Technology", "large"),
    # Communication Services
    ("GOOGL", "Communication Services", "mega"),
    ("META", "Communication Services", "mega"),
    ("NFLX", "Communication Services", "mega"),
    ("DIS", "Communication Services", "large"),
    ("CMCSA", "Communication Services", "large"),
    ("TMUS", "Communication Services", "large"),
    ("VZ", "Communication Services", "large"),
    ("T", "Communication Services", "large"),
    # Consumer Discretionary
    ("AMZN", "Consumer Discretionary", "mega"),
    ("TSLA", "Consumer Discretionary", "mega"),
    ("HD", "Consumer Discretionary", "mega"),
    ("MCD", "Consumer Discretionary", "large"),
    ("NKE", "Consumer Discretionary", "large"),
    ("LOW", "Consumer Discretionary", "large"),
    ("SBUX", "Consumer Discretionary", "large"),
    ("BKNG", "Consumer Discretionary", "large"),
    ("TJX", "Consumer Discretionary", "large"),
    ("GM", "Consumer Discretionary", "large"),
    # Consumer Staples
    ("WMT", "Consumer Staples", "mega"),
    ("PG", "Consumer Staples", "mega"),
    ("KO", "Consumer Staples", "mega"),
    ("PEP", "Consumer Staples", "large"),
    ("COST", "Consumer Staples", "mega"),
    ("PM", "Consumer Staples", "large"),
    ("MO", "Consumer Staples", "large"),
    ("CL", "Consumer Staples", "large"),
    # Financials
    ("JPM", "Financials", "mega"),
    ("V", "Financials", "mega"),
    ("MA", "Financials", "mega"),
    ("BAC", "Financials", "mega"),
    ("WFC", "Financials", "large"),
    ("GS", "Financials", "large"),
    ("MS", "Financials", "large"),
    ("AXP", "Financials", "large"),
    ("C", "Financials", "large"),
    ("SCHW", "Financials", "large"),
    ("BLK", "Financials", "large"),
    ("SPGI", "Financials", "large"),
    ("USB", "Financials", "large"),
    ("PNC", "Financials", "large"),
    ("TFC", "Financials", "large"),
    ("PYPL", "Financials", "large"),
    # Healthcare
    ("UNH", "Healthcare", "mega"),
    ("JNJ", "Healthcare", "mega"),
    ("LLY", "Healthcare", "mega"),
    ("ABBV", "Healthcare", "mega"),
    ("MRK", "Healthcare", "large"),
    ("PFE", "Healthcare", "large"),
    ("TMO", "Healthcare", "large"),
    ("ABT", "Healthcare", "large"),
    ("DHR", "Healthcare", "large"),
    ("BMY", "Healthcare", "large"),
    ("AMGN", "Healthcare", "large"),
    ("MDT", "Healthcare", "large"),
    ("GILD", "Healthcare", "large"),
    ("ISRG", "Healthcare", "large"),
    ("VRTX", "Healthcare", "large"),
    ("SYK", "Healthcare", "large"),
    # Energy
    ("XOM", "Energy", "mega"),
    ("CVX", "Energy", "mega"),
    ("COP", "Energy", "large"),
    ("SLB", "Energy", "large"),
    # Industrials
    ("BA", "Industrials", "large"),
    ("HON", "Industrials", "large"),
    ("UPS", "Industrials", "large"),
    ("CAT", "Industrials", "large"),
    ("RTX", "Industrials", "large"),
    ("LMT", "Industrials", "large"),
    ("GE", "Industrials", "large"),
    ("MMM", "Industrials", "large"),
    ("DE", "Industrials", "large"),
    ("UNP", "Industrials", "large"),
    ("EMR", "Industrials", "large"),
    ("ETN", "Industrials", "large"),
    ("NOC", "Industrials", "large"),
    # Materials
    ("LIN", "Materials", "large"),
    ("SHW", "Materials", "large"),
    # Real Estate
    ("AMT", "Real Estate", "large"),
    ("PLD", "Real Estate", "large"),
    # Utilities
    ("NEE", "Utilities", "large"),
    ("DUK", "Utilities", "large"),
    ("SO", "Utilities", "large"),
)


def _build_snapshot(
    source_version: str, effective_date: date, entries: tuple[tuple[str, str, str], ...]
) -> CandidateSourceSnapshot:
    securities = [
        CandidateSecurity(
            canonical_id=f"SYMBOL:{symbol}",
            symbol=symbol,
            sector=sector,
            market_cap_band=band,  # type: ignore[arg-type]
        )
        for symbol, sector, band in entries
    ]
    return CandidateSourceSnapshot(
        source_id=CANDIDATE_SOURCE_ID,
        source_version=source_version,
        effective_date=effective_date,
        retrieved_at=datetime.now(timezone.utc),
        securities=securities,
    )


# Every published version keeps its own permanent, reproducible entry --
# never overwritten in place. A monthly refresh adds a new key here; it
# never edits an existing one (Block 2's "must not silently rewrite past
# universe state" requirement).
_SNAPSHOT_REGISTRY: dict[str, tuple[date, tuple[tuple[str, str, str], ...]]] = {
    "sp100-v1-2026-08": (date(2026, 8, 1), _SP100_V1_ENTRIES),
}

LATEST_CANDIDATE_SOURCE_VERSION = "sp100-v1-2026-08"


def load_candidate_snapshot(
    version: str = LATEST_CANDIDATE_SOURCE_VERSION,
) -> CandidateSourceSnapshot:
    """Returns the exact, reproducible snapshot published under `version`.
    Raises KeyError for an unregistered version -- never silently falls
    back to a different one (an unknown version is a real configuration
    error, not something to paper over)."""
    effective_date, entries = _SNAPSHOT_REGISTRY[version]
    return _build_snapshot(version, effective_date, entries)


def registered_snapshot_versions() -> tuple[str, ...]:
    return tuple(_SNAPSHOT_REGISTRY.keys())
