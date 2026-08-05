# Logan Intelligence — TriggerEvent Registry: Prediction Markets Domain
**Version:** 3.1.3
*New in v3.1.2. No prior version.*
*Authoritative source for all Prediction Markets domain trigger codes. Global index: `TRIGGER_REGISTRY_GLOBAL.md`.*

---

## Domain: `prediction_markets`

This registry defines every trigger code that may be emitted by the Prediction Markets Domain Receptor or related detectors when operating on prediction market signals (Kalshi, Polymarket).

**Regulatory note:** Prediction market access and intelligence is subject to jurisdiction restrictions. See `27_SECURITY_PRIVACY_COMPLIANCE.md`.

---

## PM_CONTRACT_PRICE_MOVE_SIGNIFICANT

| Field | Value |
|-------|-------|
| **Code** | `PM_CONTRACT_PRICE_MOVE_SIGNIFICANT` |
| **Status** | ACTIVE |
| **Description** | A prediction market contract's price moved significantly (implying a meaningful change in probability) without an obvious public catalyst. Suggests informed positioning. |
| **Fire condition** | Contract price moves ≥ 8 cents (on a 0–100 cent scale, implying ≥ 8pp probability shift) in ≤ 2 hours AND no correlated public news event detected |
| **Confidence contribution** | +0.18 |

**Context shape:**
```json
{
  "contract_id": "NVDA-above-120-aug",
  "contract_title": "NVDA above $120 by Aug 31?",
  "prior_price_cents": 42,
  "current_price_cents": 61,
  "delta_cents": 19,
  "implied_prob_prior": 0.42,
  "implied_prob_current": 0.61,
  "time_window_hours": 1.5,
  "public_catalyst_detected": false
}
```

---

## PM_ASSET_CONVERGENCE_WITH_STOCK

| Field | Value |
|-------|-------|
| **Code** | `PM_ASSET_CONVERGENCE_WITH_STOCK` |
| **Status** | ACTIVE |
| **Description** | A prediction market contract about a stock (e.g., "NVDA above $120") is moving in the opposite direction from the underlying stock, creating a cross-domain divergence opportunity. The prediction market has not repriced to reflect new information in the stock. |
| **Fire condition** | Stock has moved ≥ 3% in one direction AND correlated prediction contract price has moved < 2 cents in the same implied direction within the same 4-hour window |
| **Confidence contribution** | +0.25 (cross-domain divergence; high signal) |
| **Note** | This is one of the highest-value triggers in the prediction market domain. Cross-domain price inefficiency is time-sensitive. |

**Context shape:**
```json
{
  "stock_entity_id": "entity_nvda",
  "contract_id": "NVDA-above-120-aug",
  "stock_move_pct": 7.4,
  "stock_direction": "up",
  "contract_price_change_cents": 1,
  "expected_contract_direction": "up",
  "inefficiency_score": 0.82,
  "time_window_hours": 3
}
```

---

## PM_CONTRACT_VOLUME_SURGE

| Field | Value |
|-------|-------|
| **Code** | `PM_CONTRACT_VOLUME_SURGE` |
| **Status** | ACTIVE |
| **Description** | Contract trading volume significantly exceeds its normal baseline, suggesting new interest or informed positioning. |
| **Fire condition** | Contract volume in a 1-hour window ≥ 4× the 30-day hourly average |
| **Confidence contribution** | +0.12 |

**Context shape:**
```json
{
  "contract_id": "fed-rate-cut-sept",
  "volume_current_hour": 48000,
  "volume_30d_avg_hourly": 9800,
  "volume_vs_baseline": 4.9,
  "direction_skew": "yes_contracts"
}
```

---

## PM_RESOLUTION_APPROACHING

| Field | Value |
|-------|-------|
| **Code** | `PM_RESOLUTION_APPROACHING` |
| **Status** | ACTIVE |
| **Description** | A prediction market contract the user holds (or Logan is watching) is approaching its resolution date. Urgent context for action window. |
| **Fire condition** | Contract resolution date within 72 hours |
| **Confidence contribution** | 0.0 (informational — used to trigger action_window stage for the opportunity) |

**Context shape:**
```json
{
  "contract_id": "fed-rate-cut-sept",
  "resolution_at": "2026-09-18T14:00:00Z",
  "hours_to_resolution": 48,
  "current_price_cents": 72,
  "user_holds_contract": true
}
```

---

## PM_MARKET_INEFFICIENCY_DETECTED

| Field | Value |
|-------|-------|
| **Code** | `PM_MARKET_INEFFICIENCY_DETECTED` |
| **Status** | ACTIVE |
| **Description** | A prediction market contract's implied probability diverges significantly from the probability implied by correlated assets (stock price, options market, news sentiment). |
| **Fire condition** | `inefficiency_score >= 0.60` (proprietary metric comparing contract implied prob vs. model-estimated fair value) |
| **Confidence contribution** | +0.20 |

**Context shape:**
```json
{
  "contract_id": "NVDA-above-120-aug",
  "contract_implied_prob": 0.42,
  "model_estimated_prob": 0.67,
  "inefficiency_score": 0.72,
  "supporting_signals": ["stock_price", "options_market"],
  "direction": "underpriced"
}
```

---

*Logan Intelligence TriggerEvent Registry: Prediction Markets — v3.1.2 | 2026-08-03*
*New in v3.1.2. 5 codes registered.*
