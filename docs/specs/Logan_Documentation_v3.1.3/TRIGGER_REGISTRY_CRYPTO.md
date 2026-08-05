# Logan Intelligence — TriggerEvent Registry: Crypto Domain
**Version:** 3.1.3
*New in v3.1.2. No prior version.*
*Authoritative source for all Crypto domain trigger codes. Global index: `TRIGGER_REGISTRY_GLOBAL.md`.*

---

## Domain: `crypto`

This registry defines every trigger code that may be emitted by the Crypto Domain Receptor or related detectors when operating on cryptocurrency signals.

---

## CRYPTO_PRICE_MOVE_SIGNIFICANT

| Field | Value |
|-------|-------|
| **Code** | `CRYPTO_PRICE_MOVE_SIGNIFICANT` |
| **Status** | ACTIVE |
| **Description** | Cryptocurrency price moved significantly in a session, indicating a notable event or shift in momentum. |
| **Fire condition** | `abs(price_change_pct) >= 8.0` in a 24-hour window (higher threshold than stocks due to normal crypto volatility) |
| **Confidence contribution** | +0.10 |

**Context shape:**
```json
{
  "asset": "BTC",
  "price_change_pct": 11.2,
  "direction": "up",
  "price_24h_open": 62000,
  "price_24h_close": 68944,
  "volume_vs_avg": 2.1
}
```

---

## CRYPTO_VOLUME_SURGE

| Field | Value |
|-------|-------|
| **Code** | `CRYPTO_VOLUME_SURGE` |
| **Status** | ACTIVE |
| **Description** | Trading volume significantly exceeds the 30-day average, suggesting unusual market activity. |
| **Fire condition** | Volume in 24-hour window ≥ 3× 30-day daily average |
| **Confidence contribution** | +0.12 |

**Context shape:**
```json
{
  "asset": "ETH",
  "volume_24h": 24500000000,
  "volume_30d_avg": 7200000000,
  "volume_vs_avg": 3.4
}
```

---

## CRYPTO_WALLET_ACCUMULATION

| Field | Value |
|-------|-------|
| **Code** | `CRYPTO_WALLET_ACCUMULATION` |
| **Status** | ACTIVE |
| **Description** | On-chain data shows one or more large wallets (whales) accumulating a significant position over a short period. Historical correlation with price moves. |
| **Fire condition** | One or more wallets in the top 1000 by balance increases holdings by ≥ 2% of circulating supply within 7 days |
| **Confidence contribution** | +0.18 |

**Context shape:**
```json
{
  "asset": "BTC",
  "wallet_count": 3,
  "total_accumulated_pct_supply": 2.8,
  "accumulation_window_days": 5,
  "on_chain_source": "blockchain_data_provider"
}
```

---

## CRYPTO_EXCHANGE_FLOW_SIGNIFICANT

| Field | Value |
|-------|-------|
| **Code** | `CRYPTO_EXCHANGE_FLOW_SIGNIFICANT` |
| **Status** | ACTIVE |
| **Description** | Unusual inflow or outflow of assets to/from major centralized exchanges. Large inflows can indicate selling pressure; large outflows can indicate accumulation. |
| **Fire condition** | Net exchange flow ≥ 2× 30-day daily average in a 24-hour period |
| **Confidence contribution** | +0.14 |

**Context shape:**
```json
{
  "asset": "BTC",
  "flow_direction": "outflow",
  "net_flow_btc": 28000,
  "flow_vs_avg": 2.4,
  "historical_interpretation": "accumulation_signal",
  "major_exchanges": ["Coinbase", "Binance", "Kraken"]
}
```

---

## CRYPTO_REGULATORY_EVENT

| Field | Value |
|-------|-------|
| **Code** | `CRYPTO_REGULATORY_EVENT` |
| **Status** | ACTIVE |
| **Description** | A significant regulatory announcement, ruling, court decision, or enforcement action affecting the crypto market. High impact, often with binary outcomes. |
| **Fire condition** | News classifier detects regulatory event above confidence threshold for crypto-relevant jurisdiction (US, EU, major Asian markets) |
| **Confidence contribution** | +0.20 |

**Context shape:**
```json
{
  "event_type": "enforcement_action",
  "jurisdiction": "US",
  "regulator": "SEC",
  "target": "exchange",
  "sentiment": "negative",
  "headline": "SEC files suit against major exchange",
  "source": "NewsAPI"
}
```

---

## CRYPTO_NETWORK_METRIC_ANOMALY

| Field | Value |
|-------|-------|
| **Code** | `CRYPTO_NETWORK_METRIC_ANOMALY` |
| **Status** | ACTIVE |
| **Description** | An on-chain network health metric (hash rate, active addresses, transaction count, miner revenue) crosses a historically significant threshold or shows anomalous behavior. |
| **Fire condition** | Network metric deviates ≥ 2.5 standard deviations from its 90-day rolling mean |
| **Confidence contribution** | +0.10 |

**Context shape:**
```json
{
  "metric": "active_addresses",
  "asset": "BTC",
  "current_value": 1100000,
  "rolling_mean_90d": 780000,
  "std_deviations": 3.1,
  "direction": "above",
  "historical_significance": "prior instances preceded 15%+ moves in 60 days"
}
```

---

*Logan Intelligence TriggerEvent Registry: Crypto — v3.1.2 | 2026-08-03*
*New in v3.1.2. 6 codes registered.*
