"""Canonical entity registry -- the "Canonical Entity" step in the symbol
resolution pipeline (Signal -> Canonical Entity -> Symbol Resolver -> EntitySymbol
-> Opportunity Node).

This is deliberately a backend/API-bridge concern, not something logan_core itself
knows about: display names, categories, and tickers are presentation metadata, and
per the architecture's own separation rules only Presentation decides how something
is shown -- the reasoning core shouldn't be coupled to frontend rendering concerns.
The actual logo/icon asset resolution happens client-side (mobile/lib/symbolResolver.ts)
using the category/ticker this registry provides.
"""

from typing import NamedTuple, Optional


class CanonicalEntity(NamedTuple):
    entity_id: str
    display_name: str
    category: str
    ticker: Optional[str]


ENTITY_REGISTRY: dict[str, CanonicalEntity] = {
    "TSLA": CanonicalEntity("TSLA", "Tesla", "stocks", "TSLA"),
    "NVDA": CanonicalEntity("NVDA", "NVIDIA", "stocks", "NVDA"),
    "AAPL": CanonicalEntity("AAPL", "Apple", "stocks", "AAPL"),
    "MARKETS": CanonicalEntity("MARKETS", "Markets", "markets", None),
    "OIL": CanonicalEntity("OIL", "Oil", "commodities", None),
    "BTC": CanonicalEntity("BTC", "Bitcoin", "crypto", "BTC"),
    "FED": CanonicalEntity("FED", "Federal Reserve", "macro", None),
    "NFL": CanonicalEntity("NFL", "NFL", "sports", None),
    "MUSIC": CanonicalEntity("MUSIC", "Music", "culture", None),
    "POLY": CanonicalEntity("POLY", "Polymarket", "prediction-markets", None),
    "AI_SECTOR": CanonicalEntity("AI_SECTOR", "AI", "technology", None),
}


def resolve(entity_id: str, fallback_display_name: str, fallback_domain: str) -> CanonicalEntity:
    """Looks up the canonical entity, falling back to whatever logan_core already
    knows (its own entity display name / domain) for anything not yet registered --
    the frontend never needs a code change when a new entity appears; worst case it
    falls further back to ticker/initials/category-icon in the symbol resolver.
    """
    return ENTITY_REGISTRY.get(
        entity_id,
        CanonicalEntity(entity_id, fallback_display_name, fallback_domain, None),
    )
