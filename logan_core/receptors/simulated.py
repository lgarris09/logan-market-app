from datetime import datetime, timedelta, timezone

from logan_core.contracts import Domain, RawSignal


class SimulatedReceptor:
    """Layer 1 (V1: simulated data only, per the implementation plan). Stateless —
    reads from a fixture instead of a live external API and emits RawSignal objects.
    Forbidden per spec: writing to or reading from Memory or User Model, sending
    notifications, modifying World Model.
    """

    def __init__(self, domain: Domain) -> None:
        self.domain = domain

    def emit(
        self, source_id: str, source_name: str, raw_value: dict, captured_at: datetime
    ) -> RawSignal:
        return RawSignal(
            domain=self.domain,
            source_id=source_id,
            source_name=source_name,
            raw_value=raw_value,
            captured_at=captured_at,
        )


def tesla_ai_partnership_signal(now: datetime | None = None) -> RawSignal:
    """The original operational test scenario: 'Tesla announces a major AI chip
    partnership.' Kept as its own function since it's referenced directly by tests
    and the single-event Tesla demo endpoint, in addition to being entity_fixtures()'s
    "stocks:TSLA" entry.
    """
    now = now or datetime.now(timezone.utc)
    receptor = SimulatedReceptor("stocks")
    return receptor.emit(
        source_id="company_press_release",
        source_name="Tesla Investor Relations",
        raw_value={
            "entity_id": "TSLA",
            "entity_type": "ticker",
            "signal_type": "news_event",
            "value": "Tesla announces a major AI chip partnership",
            "unit": None,
        },
        captured_at=now,
    )


def tesla_ai_partnership_corroboration(now: datetime | None = None) -> RawSignal:
    """A second, independent source corroborating the same event, a few minutes later."""
    now = (now or datetime.now(timezone.utc)) + timedelta(minutes=4)
    receptor = SimulatedReceptor("stocks")
    return receptor.emit(
        source_id="reuters_wire",
        source_name="Reuters",
        raw_value={
            "entity_id": "TSLA",
            "entity_type": "ticker",
            "signal_type": "news_event",
            "value": "Tesla confirms AI chip partnership with major supplier",
            "unit": None,
        },
        captured_at=now,
    )


def simulated_fixtures(now: datetime | None = None) -> dict[str, RawSignal]:
    """One representative RawSignal per entity_id, for demo/feed purposes. Keyed by
    entity_id (not domain) since several entities share a domain (five different
    stocks entities, for example).
    """
    now = now or datetime.now(timezone.utc)
    return {
        "TSLA": tesla_ai_partnership_signal(now),
        "NVDA": SimulatedReceptor("stocks").emit(
            source_id="bloomberg_terminal",
            source_name="Bloomberg",
            raw_value={
                "entity_id": "NVDA",
                "entity_type": "ticker",
                "signal_type": "earnings_signal",
                "value": "NVIDIA data-center demand guidance raised",
                "unit": None,
            },
            captured_at=now,
        ),
        "AAPL": SimulatedReceptor("stocks").emit(
            source_id="bloomberg_terminal",
            source_name="Bloomberg",
            raw_value={
                "entity_id": "AAPL",
                "entity_type": "ticker",
                "signal_type": "earnings_signal",
                "value": "Apple earnings call scheduled, analysts watching services growth",
                "unit": None,
            },
            captured_at=now,
        ),
        "MARKETS": SimulatedReceptor("stocks").emit(
            source_id="bloomberg_terminal",
            source_name="Bloomberg",
            raw_value={
                "entity_id": "MARKETS",
                "entity_type": "ticker",
                "signal_type": "technical_breakout",
                "value": "Broad market breadth turns bullish across sectors",
                "unit": None,
            },
            captured_at=now,
        ),
        "OIL": SimulatedReceptor("stocks").emit(
            source_id="bloomberg_terminal",
            source_name="Bloomberg",
            raw_value={
                "entity_id": "OIL",
                "entity_type": "ticker",
                "signal_type": "price_change",
                "value": "Crude supply tightens on refinery outages",
                "unit": "USD/barrel",
            },
            captured_at=now,
        ),
        "BTC": SimulatedReceptor("crypto").emit(
            source_id="social_aggregator",
            source_name="Simulated Crypto Feed",
            raw_value={
                "entity_id": "BTC",
                "entity_type": "ticker",
                "signal_type": "volatility_spike",
                "value": "Bitcoin volatility spikes on ETF flow data",
                "unit": None,
            },
            captured_at=now,
        ),
        "FED": SimulatedReceptor("news").emit(
            source_id="reuters_wire",
            source_name="Reuters",
            raw_value={
                "entity_id": "FED",
                "entity_type": "topic",
                "signal_type": "breaking_news",
                "value": "Federal Reserve rate decision expected this week",
                "unit": None,
            },
            captured_at=now,
        ),
        "NFL": SimulatedReceptor("sports").emit(
            source_id="sportsbook_feed",
            source_name="Simulated Sportsbook Feed",
            raw_value={
                "entity_id": "NFL",
                "entity_type": "team",
                "signal_type": "line_move",
                "value": "Week 7 spreads moving sharply across the board",
                "unit": "points",
            },
            captured_at=now,
        ),
        "MUSIC": SimulatedReceptor("social").emit(
            source_id="social_aggregator",
            source_name="Simulated Social Aggregator",
            raw_value={
                "entity_id": "MUSIC",
                "entity_type": "topic",
                "signal_type": "viral_threshold",
                "value": "New single crosses viral engagement threshold",
                "unit": None,
            },
            captured_at=now,
        ),
        "POLY": SimulatedReceptor("poly").emit(
            source_id="polymarket_api",
            source_name="Simulated Polymarket Feed",
            raw_value={
                "entity_id": "POLY",
                "entity_type": "contract",
                "signal_type": "price_spike",
                "value": "Contract price moved from 0.42 to 0.51",
                "unit": "probability",
            },
            captured_at=now,
        ),
        "AI_SECTOR": SimulatedReceptor("social").emit(
            source_id="social_aggregator",
            source_name="Simulated Social Aggregator",
            raw_value={
                "entity_id": "AI_SECTOR",
                "entity_type": "topic",
                "signal_type": "trend_emerging",
                "value": "AI infrastructure discussion volume rising",
                "unit": None,
            },
            captured_at=now,
        ),
    }
