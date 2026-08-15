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
    - A real provider (e.g. Alpha Vantage/Finnhub) is NOT implemented this
      sprint: no credentials were available (Phase 4 instruction: build the
      abstraction, don't guess at an untested real integration). Adding one
      later means implementing this Protocol and mapping that provider's
      response into EarningsReport -- no other file needs to change.
    """

    def fetch_latest_earnings(self, entity_id: str) -> Optional[EarningsReport]:
        """Returns the most recent earnings report for entity_id, or None if
        the provider has nothing for it. Must not fabricate a report when the
        provider has no data -- return None, don't invent one.
        """
        ...
