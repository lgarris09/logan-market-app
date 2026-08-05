# Logan Intelligence — TriggerEvent Registry: Global Index
**Version:** 3.1.3
*New in v3.1.2. No prior version.*

*This is a READ-ONLY index. Domain registry files are the authoritative source. Add new codes to the domain registry file first, then update this index.*

---

## How to Read This Index

- **Code** — The exact string used in the `trigger_code` field
- **Domain** — Domain of origin
- **Registry File** — Where the full definition lives
- **Status** — ACTIVE, DEPRECATED, or PLANNED

---

## Master Index

### Stocks

| Code | Description | Status | Registry |
|------|-------------|--------|----------|
| `STOCK_EARNINGS_BEAT` | Reported EPS exceeded consensus estimate by threshold | ACTIVE | `TRIGGER_REGISTRY_STOCKS.md` |
| `STOCK_EARNINGS_MISS` | Reported EPS fell below consensus estimate by threshold | ACTIVE | `TRIGGER_REGISTRY_STOCKS.md` |
| `STOCK_EARNINGS_IN_LINE` | EPS within ±2% of consensus; no surprise | ACTIVE | `TRIGGER_REGISTRY_STOCKS.md` |
| `STOCK_EARNINGS_QUALITY_WARNING` | Beat driven by one-time items (tax benefit, asset sale, etc.) | ACTIVE | `TRIGGER_REGISTRY_STOCKS.md` |
| `STOCK_GUIDANCE_RAISED` | Forward guidance revised upward | ACTIVE | `TRIGGER_REGISTRY_STOCKS.md` |
| `STOCK_GUIDANCE_LOWERED` | Forward guidance revised downward | ACTIVE | `TRIGGER_REGISTRY_STOCKS.md` |
| `STOCK_OPTIONS_FLOW_SURGE` | Unusual call or put buying volume in near-term expiry | ACTIVE | `TRIGGER_REGISTRY_STOCKS.md` |
| `STOCK_PRICE_MOVE_SIGNIFICANT` | Price moved ≥ threshold % in a session | ACTIVE | `TRIGGER_REGISTRY_STOCKS.md` |
| `STOCK_DIVERGENCE_PRICE_VS_SENTIMENT` | Price and social sentiment diverging by gap_score threshold | ACTIVE | `TRIGGER_REGISTRY_STOCKS.md` |
| `STOCK_CONVERGENCE_MULTI_SOURCE` | 3+ independent signals on same entity within time window | ACTIVE | `TRIGGER_REGISTRY_STOCKS.md` |
| `STOCK_ODSE_ACCUMULATION` | ODSE weak signal accumulation threshold reached | ACTIVE | `TRIGGER_REGISTRY_STOCKS.md` |
| `STOCK_INSIDER_ACTIVITY` | Registered insider buy or sell above threshold | ACTIVE | `TRIGGER_REGISTRY_STOCKS.md` |
| `STOCK_ANALYST_UPGRADE` | Analyst rating upgraded (e.g., Hold → Buy) | ACTIVE | `TRIGGER_REGISTRY_STOCKS.md` |
| `STOCK_ANALYST_DOWNGRADE` | Analyst rating downgraded | ACTIVE | `TRIGGER_REGISTRY_STOCKS.md` |

### Sports

| Code | Description | Status | Registry |
|------|-------------|--------|----------|
| `SPORTS_LINE_MOVEMENT_SIGNIFICANT` | Odds line moved ≥ threshold points without clear public catalyst | ACTIVE | `TRIGGER_REGISTRY_SPORTS.md` |
| `SPORTS_INJURY_KEY_PLAYER` | Starting or key player reported injured/questionable | ACTIVE | `TRIGGER_REGISTRY_SPORTS.md` |
| `SPORTS_WEATHER_CONDITION_IMPACT` | Weather forecast indicates significant game-day impact | ACTIVE | `TRIGGER_REGISTRY_SPORTS.md` |
| `SPORTS_PUBLIC_SHARP_DIVERGENCE` | Public betting percentage diverges significantly from line movement | ACTIVE | `TRIGGER_REGISTRY_SPORTS.md` |
| `SPORTS_CONSENSUS_PICK_EXTREME` | >75% of picks on one side (extreme public consensus) | ACTIVE | `TRIGGER_REGISTRY_SPORTS.md` |
| `SPORTS_REVERSE_LINE_MOVEMENT` | Line moves against the majority of public money | ACTIVE | `TRIGGER_REGISTRY_SPORTS.md` |
| `SPORTS_GAME_STATUS_CHANGE` | Game postponed, cancelled, or rescheduled | ACTIVE | `TRIGGER_REGISTRY_SPORTS.md` |

### Prediction Markets

| Code | Description | Status | Registry |
|------|-------------|--------|----------|
| `PM_CONTRACT_PRICE_MOVE_SIGNIFICANT` | Contract price moved ≥ threshold without obvious catalyst | ACTIVE | `TRIGGER_REGISTRY_PREDICTION_MARKETS.md` |
| `PM_ASSET_CONVERGENCE_WITH_STOCK` | Prediction market contract and related stock moving in diverging directions | ACTIVE | `TRIGGER_REGISTRY_PREDICTION_MARKETS.md` |
| `PM_CONTRACT_VOLUME_SURGE` | Contract volume exceeds N× baseline in time window | ACTIVE | `TRIGGER_REGISTRY_PREDICTION_MARKETS.md` |
| `PM_RESOLUTION_APPROACHING` | Contract resolution date within threshold window | ACTIVE | `TRIGGER_REGISTRY_PREDICTION_MARKETS.md` |
| `PM_MARKET_INEFFICIENCY_DETECTED` | Contract price diverges significantly from implied probability of correlated asset | ACTIVE | `TRIGGER_REGISTRY_PREDICTION_MARKETS.md` |

### Crypto

| Code | Description | Status | Registry |
|------|-------------|--------|----------|
| `CRYPTO_PRICE_MOVE_SIGNIFICANT` | Price moved ≥ threshold % in session | ACTIVE | `TRIGGER_REGISTRY_CRYPTO.md` |
| `CRYPTO_VOLUME_SURGE` | Trading volume exceeds N× 30-day average | ACTIVE | `TRIGGER_REGISTRY_CRYPTO.md` |
| `CRYPTO_WALLET_ACCUMULATION` | On-chain large wallet accumulation detected | ACTIVE | `TRIGGER_REGISTRY_CRYPTO.md` |
| `CRYPTO_EXCHANGE_FLOW_SIGNIFICANT` | Unusual inflow or outflow to/from major exchange | ACTIVE | `TRIGGER_REGISTRY_CRYPTO.md` |
| `CRYPTO_REGULATORY_EVENT` | Regulatory announcement, ruling, or enforcement action | ACTIVE | `TRIGGER_REGISTRY_CRYPTO.md` |
| `CRYPTO_NETWORK_METRIC_ANOMALY` | On-chain network metric (hash rate, active addresses, etc.) exceeds threshold | ACTIVE | `TRIGGER_REGISTRY_CRYPTO.md` |

### Culture

| Code | Description | Status | Registry |
|------|-------------|--------|----------|
| `CULTURE_CHART_VELOCITY_SURGE` | Song or album chart velocity exceeds threshold (streams accelerating) | ACTIVE | `TRIGGER_REGISTRY_CULTURE.md` |
| `CULTURE_CHART_ENTRY_NEW` | Entity enters chart at threshold position or higher | ACTIVE | `TRIGGER_REGISTRY_CULTURE.md` |
| `CULTURE_VIDEO_VIEW_VELOCITY` | YouTube video view velocity exceeds N× expected rate | ACTIVE | `TRIGGER_REGISTRY_CULTURE.md` |
| `CULTURE_SOCIAL_SEARCH_SURGE` | Search volume for entity spikes above baseline | ACTIVE | `TRIGGER_REGISTRY_CULTURE.md` |
| `CULTURE_CROSS_PLATFORM_CONVERGENCE` | Entity trending simultaneously on 3+ platforms | ACTIVE | `TRIGGER_REGISTRY_CULTURE.md` |
| `CULTURE_ARTIST_ANNOUNCEMENT` | New release, tour, or major announcement detected | ACTIVE | `TRIGGER_REGISTRY_CULTURE.md` |
| `CULTURE_VIRAL_MOMENT` | Clip or moment going viral independent of release schedule | ACTIVE | `TRIGGER_REGISTRY_CULTURE.md` |

### Personal Finance

| Code | Description | Status | Registry |
|------|-------------|--------|----------|
| `PF_FED_RATE_DECISION_SURPRISE` | Fed rate decision deviates from market consensus expectation | ACTIVE | `TRIGGER_REGISTRY_PERSONAL_FINANCE.md` |
| `PF_FED_RATE_DECISION_INLINE` | Fed rate decision matches consensus | ACTIVE | `TRIGGER_REGISTRY_PERSONAL_FINANCE.md` |
| `PF_INFLATION_REPORT_SURPRISE` | CPI/PCE data surprises vs. consensus (high or low) | ACTIVE | `TRIGGER_REGISTRY_PERSONAL_FINANCE.md` |
| `PF_JOBS_REPORT_SURPRISE` | Non-farm payrolls significantly beat or miss consensus | ACTIVE | `TRIGGER_REGISTRY_PERSONAL_FINANCE.md` |
| `PF_MORTGAGE_RATE_THRESHOLD` | 30-year fixed mortgage rate crosses user-relevant threshold | ACTIVE | `TRIGGER_REGISTRY_PERSONAL_FINANCE.md` |
| `PF_GDP_REVISION_SIGNIFICANT` | GDP growth revised significantly from prior estimate | ACTIVE | `TRIGGER_REGISTRY_PERSONAL_FINANCE.md` |
| `PF_SAVINGS_RATE_ANOMALY` | Personal savings rate crosses historically significant threshold | ACTIVE | `TRIGGER_REGISTRY_PERSONAL_FINANCE.md` |

---

## Deprecated Codes

None in v3.1.2.

---

## Code Count Summary

| Domain | Active Codes |
|--------|-------------|
| Stocks | 14 |
| Sports | 7 |
| Prediction Markets | 5 |
| Crypto | 6 |
| Culture | 7 |
| Personal Finance | 7 |
| **Total** | **46** |

---

*Logan Intelligence TriggerEvent Registry: Global Index — v3.1.2 | 2026-08-03*
*New in v3.1.2. Initial registry: 46 trigger codes across 6 domains.*
*To add a code: update the domain registry file first, then update this index.*
