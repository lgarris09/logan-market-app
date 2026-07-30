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

    def emit(self, source_id: str, source_name: str, raw_value: dict, captured_at: datetime) -> RawSignal:
        return RawSignal(
            domain=self.domain,
            source_id=source_id,
            source_name=source_name,
            raw_value=raw_value,
            captured_at=captured_at,
        )


def tesla_ai_partnership_signal(now: datetime | None = None) -> RawSignal:
    """The first operational test scenario: 'Tesla announces a major AI chip partnership.'"""
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
    """One representative RawSignal per domain, for broader receptor coverage beyond
    the primary Tesla test scenario.
    """
    now = now or datetime.now(timezone.utc)
    return {
        "stocks": tesla_ai_partnership_signal(now),
        "sports": SimulatedReceptor("sports").emit(
            source_id="sportsbook_feed",
            source_name="Simulated Sportsbook Feed",
            raw_value={
                "entity_id": "NFL_TEAM_A",
                "entity_type": "team",
                "signal_type": "line_move",
                "value": "Spread moved from -3.5 to -5.0",
                "unit": "points",
            },
            captured_at=now,
        ),
        "poly": SimulatedReceptor("poly").emit(
            source_id="polymarket_api",
            source_name="Simulated Polymarket Feed",
            raw_value={
                "entity_id": "ELECTION_CONTRACT_1",
                "entity_type": "contract",
                "signal_type": "price_spike",
                "value": "Contract price moved from 0.42 to 0.51",
                "unit": "probability",
            },
            captured_at=now,
        ),
        "social": SimulatedReceptor("social").emit(
            source_id="social_aggregator",
            source_name="Simulated Social Aggregator",
            raw_value={
                "entity_id": "AI_INFRA_ETF",
                "entity_type": "topic",
                "signal_type": "trend_emerging",
                "value": "AI infrastructure discussion volume rising",
                "unit": None,
            },
            captured_at=now,
        ),
        "news": SimulatedReceptor("news").emit(
            source_id="reuters_wire",
            source_name="Reuters",
            raw_value={
                "entity_id": "NVDA",
                "entity_type": "ticker",
                "signal_type": "breaking_news",
                "value": "NVIDIA supply constraints reported ahead of earnings",
                "unit": None,
            },
            captured_at=now,
        ),
    }
