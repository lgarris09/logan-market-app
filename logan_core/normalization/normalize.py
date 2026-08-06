from datetime import datetime, timezone
from uuid import uuid4

from logan_core.contracts import DecisionTraceEntry, NormalizedSignal, RawSignal

SIGNAL_TYPE_REGISTRY: dict[str, set[str]] = {
    "stocks": {
        "price_change",
        "volume_spike",
        "news_event",
        "earnings_signal",
        "analyst_change",
        "technical_breakout",
    },
    "sports": {
        "odds_move",
        "line_move",
        "injury_report",
        "weather_alert",
        "sharp_money",
        "reverse_line_move",
    },
    "poly": {
        "price_spike",
        "sentiment_shift",
        "volume_surge",
        "resolution_approaching",
        "new_contract",
    },
    "social": {
        "trend_emerging",
        "velocity_spike",
        "influencer_post",
        "viral_threshold",
        "sentiment_flip",
        "topic_spike",
    },
    # News added as a fifth domain per ADR-020.
    "news": {
        "breaking_news",
        "analysis_published",
        "correction_issued",
        "developing_story",
        "headline_shift",
    },
    # Crypto added as a sixth domain per ADR-024.
    "crypto": {
        "price_change",
        "volume_spike",
        "volatility_spike",
        "exchange_flow",
        "regulatory_news",
    },
}


class NormalizationError(ValueError):
    pass


class Normalizer:
    """Layer 2 — stateless conversion of RawSignal into NormalizedSignal.

    Forbidden per spec: writing to Memory, reading User Model, applying trust/confidence,
    filtering or ranking. This class does none of those.
    """

    def normalize(self, raw: RawSignal) -> NormalizedSignal:
        if not isinstance(raw.raw_value, dict):
            raise NormalizationError(
                "raw_value must be a dict with entity/signal fields for V1 mapping"
            )

        entity_id = raw.raw_value.get("entity_id")
        entity_type = raw.raw_value.get("entity_type")
        signal_type = raw.raw_value.get("signal_type")
        value = raw.raw_value.get("value")
        unit = raw.raw_value.get("unit")

        if not entity_id or not entity_type or not signal_type or value is None:
            raise NormalizationError(
                "raw_value must include entity_id, entity_type, signal_type, and value"
            )

        allowed = SIGNAL_TYPE_REGISTRY.get(raw.domain, set())
        if signal_type not in allowed:
            raise NormalizationError(
                f"signal_type '{signal_type}' is not registered for domain '{raw.domain}'"
            )

        now = datetime.now(timezone.utc)
        return NormalizedSignal(
            signal_id=uuid4(),
            domain=raw.domain,
            entity_id=entity_id,
            entity_type=entity_type,
            signal_type=signal_type,
            value=value,
            unit=unit,
            source_id=raw.source_id,
            source_name=raw.source_name,
            captured_at=raw.captured_at,
            normalized_at=now,
            decision_trace=[
                DecisionTraceEntry(
                    layer="normalization",
                    rule=f"signal_type '{signal_type}' validated against the '{raw.domain}' registry",
                    timestamp=now,
                )
            ],
        )
