"""Universe Manager V1a Block 9 -- thesis market-driver metadata. A small,
fixed, deterministic taxonomy -- explicitly not embeddings, not semantic
vector clustering, not LLM classification, not a giant thematic taxonomy.
Every tag is derived purely from this codebase's own existing trigger-code
provenance (trigger_detection/stocks.py, convergence/tracker.py); an LLM is
never asked to infer a V1a driver tag.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .lifecycle import LifecycleState

MarketDriverTag = str  # closed set enforced by classify_market_driver(); see below

# The eight recognized tags (Block 9's own list). Not a typing.Literal
# because three of them (CAPITAL_RETURN, CORPORATE_ACTION,
# SECTOR_WIDE_MOVE) have no current trigger-code provenance in this
# codebase at all -- there is no buyback/dividend/M&A/sector-index trigger
# yet -- so no real code path can produce them today. They're listed here
# for a complete, forward-compatible taxonomy (mirrors
# logan_core/diagnostics/fault_codes.py's own "registered, not yet
# triggered" precedent), not left out of the type, but also not claimed as
# reachable.
MARKET_DRIVER_TAGS = (
    "EARNINGS_RESULT",
    "EARNINGS_GUIDANCE",
    "PRICE_DISLOCATION",
    "ANALYST_REASSESSMENT",
    "CAPITAL_RETURN",
    "CORPORATE_ACTION",
    "SECTOR_WIDE_MOVE",
    "UNCLASSIFIED",
)

# Trigger codes with no current market_driver_tag provenance at all.
UNWIRED_MARKET_DRIVER_TAGS = ("CAPITAL_RETURN", "CORPORATE_ACTION", "SECTOR_WIDE_MOVE")


class ThesisMetadata(BaseModel):
    """One coherent opportunity's diversity-relevant metadata -- computed
    once per (user-agnostic) event, consumed by thesis_diversity.py's
    top-band cap enforcement (Block 10). Never a second opportunity
    computation: every field here is either copied from, or deterministically
    derived from, data OpportunityEngine/TriggerDetection already produced.
    """

    schema_version: str = "1.0"
    event_id: UUID
    primary_entity_id: str
    sector: Optional[str] = None
    primary_signal_family: str
    secondary_signal_families: list[str] = Field(default_factory=list)
    market_driver_tag: str
    # Reuses the existing opportunity lifecycle state machine
    # (OpportunityLifecycleTracker/LifecycleSnapshot) -- never a second,
    # parallel "thesis state" concept.
    thesis_state: LifecycleState
    material_revision_at: Optional[datetime] = None
