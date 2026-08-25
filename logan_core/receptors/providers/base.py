from datetime import datetime
from typing import Optional, Protocol

from pydantic import BaseModel


class EarningsReport(BaseModel):
    """STRATUS-owned shape a stocks earnings provider maps its response into.
    Provider-specific field names/response structure terminate here (Phase 4
    instruction) -- nothing downstream of this class (receptors/
    stocks_earnings.py, trigger_detection/, or any pipeline layer) ever sees
    a raw provider payload.

    Every field the provider didn't actually supply must be None, never a
    fabricated/estimated value (Phase 1/7 instruction) -- trigger_detection's
    evaluate_earnings_beat_condition() already handles None actual_eps/
    consensus_eps explicitly rather than assuming they're always present.
    """

    entity_id: str
    actual_eps: Optional[float] = None
    consensus_eps: Optional[float] = None
    fiscal_quarter: Optional[str] = None
    guidance_revised: Optional[bool] = None
    guidance_delta_pct: Optional[float] = None
    report_timestamp: datetime
    source_id: str
    source_name: str


class EarningsProvider(Protocol):
    """A source of real (or, for FixtureEarningsProvider, clearly-labeled
    deterministic test) earnings data for one entity at a time. Sprint 3.6.6
    scope: NVIDIA only, one provider call site (backend/app/logan_feed.py is
    NOT wired to this yet -- see the Sprint 3.6.6 ADR's "exact next step").

    Implementations:
    - FixtureEarningsProvider (fixture.py): deterministic, in-repo, used by
      tests. Never presented as live -- see its own docstring.
    - FmpEarningsProvider (fmp.py, Sprint 3.6.6B): the first live provider,
      backed by Financial Modeling Prep. Not wired into backend/app/
      logan_feed.py or /v1/opportunities yet -- see the Sprint 3.6.6B
      report for exactly what "live" means at this stage (provider-level
      verification only).
    """

    def fetch_latest_earnings(self, entity_id: str) -> Optional[EarningsReport]:
        """Returns the most recent earnings report for entity_id, or None if
        the provider has nothing for it. Must not fabricate a report when the
        provider has no data -- return None, don't invent one.
        """
        ...


class Quote(BaseModel):
    """STRATUS-owned shape a stock-quote provider maps its response into
    (Sprint 3.6.7). `change_pct` is the session's price change versus the
    prior close -- the real, provider-computed figure, not re-derived from
    price/previous_close here (avoids a second, possibly-inconsistent
    calculation of the same number a provider already supplies).

    `volume` (Stock Opportunity Logic V2.2, additive, Optional): the
    session's real, provider-reported share volume -- confirmed live in
    FMP's `/quote` response (2026-08-24/25) even though this codebase didn't
    read it into this contract before V2.2. Optional/None for any provider
    (or fixture) that doesn't supply it -- never estimated.
    """

    entity_id: str
    price: float
    previous_close: float
    change_pct: float
    quote_timestamp: datetime
    source_id: str
    source_name: str
    volume: Optional[float] = None


class QuoteProvider(Protocol):
    """A source of real-time-ish stock quote data for one entity at a time
    (Sprint 3.6.7) -- price, previous close, session change percentage. Same
    shape/pattern as EarningsProvider: implementations terminate all
    provider-specific structure, downstream code only ever sees `Quote`.
    """

    def fetch_quote(self, entity_id: str) -> Optional[Quote]:
        """Returns the current/latest quote for entity_id, or None if the
        provider has nothing for it. Must not fabricate a quote -- return
        None, don't invent one.
        """
        ...


class GradeChange(BaseModel):
    """STRATUS-owned shape an analyst-rating-change provider maps its
    response into (Sprint 3.6.7) -- the single most recent rating action for
    one entity. `action` is the provider's own classification (e.g.
    "upgrade"/"downgrade"/"maintain"/"initiate"), not re-derived from
    `previous_rating`/`new_rating` text here -- inferring "upgrade" vs.
    "downgrade" from rating strings ("Hold" vs. "Buy" vs. "Outperform", etc.)
    would require inventing a rating-ordinal hierarchy this system has no
    authoritative source for; trusting the provider's own pre-classified
    action is more honest and deterministic than guessing one.
    """

    entity_id: str
    grading_firm: str
    previous_rating: Optional[str] = None
    new_rating: Optional[str] = None
    action: str
    action_date: datetime
    source_id: str
    source_name: str


class AnalystGradesProvider(Protocol):
    """A source of real analyst rating-change data for one entity at a time
    (Sprint 3.6.7). Same shape/pattern as EarningsProvider/QuoteProvider.
    """

    def fetch_latest_grade_change(self, entity_id: str) -> Optional[GradeChange]:
        """Returns the single most recent rating-change entry for entity_id,
        or None if the provider has nothing for it. Must not fabricate one.
        """
        ...


class CompanyProfile(BaseModel):
    """STRATUS-owned shape a company-profile provider maps its response into
    (Sprint 3.6.9/Stock Opportunity Logic V2.2) -- the slower-changing
    reference data Quote alone doesn't carry: sector classification, a
    volume baseline, and beta. Every field Optional -- a real profile
    response may be missing any of these for a given symbol, and this must
    never be estimated/fabricated when absent.
    """

    entity_id: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    average_volume: Optional[float] = None
    beta: Optional[float] = None
    source_id: str
    source_name: str


class CompanyProfileProvider(Protocol):
    """A source of real, slower-changing company reference data for one
    entity at a time (Stock Opportunity Logic V2.2). Same shape/pattern as
    QuoteProvider/AnalystGradesProvider.
    """

    def fetch_company_profile(self, entity_id: str) -> Optional[CompanyProfile]:
        """Returns the current profile for entity_id, or None if the
        provider has nothing for it. Must not fabricate one.
        """
        ...
