# Logan Intelligence — TriggerEvent Registry: Stocks Domain
**Version:** 3.1.3
**Status:** SPECIFIED — NOT IMPLEMENTED (V3.1.4 BATCH-3, OD-009) — see `TRIGGER_EVENT_FRAMEWORK.md`.
*New in v3.1.2. No prior version.*
*Authoritative source for all Stocks domain trigger codes. Global index: `TRIGGER_REGISTRY_GLOBAL.md`.*

---

## Domain: `stocks`

This registry defines every trigger code that may be emitted by the Stocks Domain Receptor, Convergence Detector, Divergence Detector, or ODSE when operating on stocks domain signals.

---

## STOCK_EARNINGS_BEAT

| Field | Value |
|-------|-------|
| **Code** | `STOCK_EARNINGS_BEAT` |
| **Status** | ACTIVE |
| **Description** | Reported EPS exceeded analyst consensus estimate by a meaningful threshold. |
| **Fire condition** | `actual_eps > consensus_eps` AND `beat_pct >= 5.0` |
| **Does NOT fire when** | Beat is < 5%, or when the beat is later attributed to a one-time item (use `STOCK_EARNINGS_QUALITY_WARNING` as a companion) |
| **Confidence contribution** | +0.22 to opportunity confidence |

**Context shape:**
```json
{
  "actual_eps": 0.81,
  "consensus_eps": 0.69,
  "beat_pct": 17.4,
  "guidance_revised": true,
  "guidance_delta_pct": 6.7,
  "fiscal_quarter": "Q3 2026"
}
```

---

## STOCK_EARNINGS_MISS

| Field | Value |
|-------|-------|
| **Code** | `STOCK_EARNINGS_MISS` |
| **Status** | ACTIVE |
| **Description** | Reported EPS fell below analyst consensus estimate by a meaningful threshold. |
| **Fire condition** | `actual_eps < consensus_eps` AND `miss_pct >= 5.0` |
| **Confidence contribution** | +0.20 to opportunity confidence (downside opportunity) |

**Context shape:**
```json
{
  "actual_eps": 0.52,
  "consensus_eps": 0.68,
  "miss_pct": 23.5,
  "guidance_revised": false,
  "guidance_delta_pct": null,
  "fiscal_quarter": "Q3 2026"
}
```

---

## STOCK_EARNINGS_IN_LINE

| Field | Value |
|-------|-------|
| **Code** | `STOCK_EARNINGS_IN_LINE` |
| **Status** | ACTIVE |
| **Description** | EPS within ±2% of consensus; no meaningful surprise. Useful for clearing hypotheses. |
| **Fire condition** | `abs(beat_pct) < 2.0` |
| **Confidence contribution** | 0.0 (no positive contribution; used to close hypotheses) |

**Context shape:**
```json
{
  "actual_eps": 0.71,
  "consensus_eps": 0.70,
  "beat_pct": 1.4,
  "fiscal_quarter": "Q3 2026"
}
```

---

## STOCK_EARNINGS_QUALITY_WARNING

| Field | Value |
|-------|-------|
| **Code** | `STOCK_EARNINGS_QUALITY_WARNING` |
| **Status** | ACTIVE |
| **Description** | An earnings beat exists but is driven by one-time non-recurring items (tax benefit, asset sale, accounting adjustment). Companion to `STOCK_EARNINGS_BEAT`. |
| **Fire condition** | `STOCK_EARNINGS_BEAT` fires AND one-time item flag detected in earnings data |
| **Confidence contribution** | −0.15 (reduces confidence from STOCK_EARNINGS_BEAT) |
| **Note** | When both `STOCK_EARNINGS_BEAT` and `STOCK_EARNINGS_QUALITY_WARNING` fire together, net confidence contribution = +0.22 − 0.15 = +0.07. See `TRIGGER_SCORING_AND_CONFLICT_RULES.md`. |

**Context shape:**
```json
{
  "item_type": "tax_benefit",
  "item_description": "One-time deferred tax benefit of $0.09/share",
  "adjusted_beat_pct": 3.1,
  "adjusted_eps_ex_item": 0.72
}
```

---

## STOCK_GUIDANCE_RAISED

| Field | Value |
|-------|-------|
| **Code** | `STOCK_GUIDANCE_RAISED` |
| **Status** | ACTIVE |
| **Description** | Company raised forward revenue or EPS guidance above prior guidance or consensus. |
| **Fire condition** | New guidance midpoint > prior guidance midpoint by ≥ 3% |
| **Confidence contribution** | +0.15 |

**Context shape:**
```json
{
  "guidance_type": "revenue",
  "prior_guidance_midpoint": 35000000000,
  "new_guidance_midpoint": 37500000000,
  "delta_pct": 7.1,
  "fiscal_period": "Q4 2026"
}
```

---

## STOCK_GUIDANCE_LOWERED

| Field | Value |
|-------|-------|
| **Code** | `STOCK_GUIDANCE_LOWERED` |
| **Status** | ACTIVE |
| **Description** | Company lowered forward guidance below prior guidance or consensus. |
| **Fire condition** | New guidance midpoint < prior guidance midpoint by ≥ 3% |
| **Confidence contribution** | +0.15 (downside opportunity) |

**Context shape:**
```json
{
  "guidance_type": "revenue",
  "prior_guidance_midpoint": 35000000000,
  "new_guidance_midpoint": 32000000000,
  "delta_pct": -8.6,
  "fiscal_period": "Q4 2026"
}
```

---

## STOCK_OPTIONS_FLOW_SURGE

| Field | Value |
|-------|-------|
| **Code** | `STOCK_OPTIONS_FLOW_SURGE` |
| **Status** | ACTIVE |
| **Description** | Unusual options buying activity in near-term expiry (calls or puts), suggesting informed positioning. |
| **Fire condition** | Options volume ≥ 3× 30-day average AND skewed to calls or puts (>65% directional) AND expiry ≤ 21 days |
| **Confidence contribution** | +0.12 |

**Context shape:**
```json
{
  "direction": "calls",
  "volume_vs_avg": 4.2,
  "volume_30d_avg": 12000,
  "current_volume": 50400,
  "expiry_days": 7,
  "implied_move_pct": 8.3
}
```

---

## STOCK_PRICE_MOVE_SIGNIFICANT

| Field | Value |
|-------|-------|
| **Code** | `STOCK_PRICE_MOVE_SIGNIFICANT` |
| **Status** | ACTIVE |
| **Description** | Stock price moved ≥ threshold in a session, indicating a significant event. |
| **Fire condition** | `abs(price_change_pct) >= 5.0` in a single trading session |
| **Confidence contribution** | +0.10 |

**Context shape:**
```json
{
  "price_change_pct": 7.4,
  "direction": "up",
  "session_open": 118.50,
  "session_close": 127.27,
  "volume_vs_avg": 2.8
}
```

---

## STOCK_DIVERGENCE_PRICE_VS_SENTIMENT

| Field | Value |
|-------|-------|
| **Code** | `STOCK_DIVERGENCE_PRICE_VS_SENTIMENT` |
| **Status** | ACTIVE |
| **Description** | Price and social sentiment are diverging — price moving in one direction while sentiment moves in the opposite direction. |
| **Fire condition** | `gap_score >= 0.65` (see Divergence Detector) AND divergence sustained ≥ 2 trading days |
| **Confidence contribution** | +0.18 |

**Context shape:**
```json
{
  "gap_score": 0.71,
  "price_direction": "down",
  "sentiment_direction": "positive",
  "price_change_3d_pct": -8.2,
  "sentiment_score": 0.68,
  "days_sustained": 3
}
```

---

## STOCK_CONVERGENCE_MULTI_SOURCE

| Field | Value |
|-------|-------|
| **Code** | `STOCK_CONVERGENCE_MULTI_SOURCE` |
| **Status** | ACTIVE |
| **Description** | 3 or more independent signal sources fire on the same entity within a 30-minute window. |
| **Fire condition** | ≥ 3 distinct source types (price, news, social, options, etc.) emit signals within 30 minutes |
| **Confidence contribution** | +0.20 |

**Context shape:**
```json
{
  "source_count": 4,
  "sources": ["price_move", "news_article", "reddit_mentions", "options_flow"],
  "window_minutes": 30,
  "convergence_strength": 0.72
}
```

---

## STOCK_ODSE_ACCUMULATION

| Field | Value |
|-------|-------|
| **Code** | `STOCK_ODSE_ACCUMULATION` |
| **Status** | ACTIVE |
| **Description** | ODSE (On-Domain Signal Evaluation) weak signal accumulation threshold reached. Multiple weak signals have built up over a 14-day window. |
| **Fire condition** | `reinforcement_count >= 3` AND `weighted_strength >= 0.60` within 14-day window |
| **Confidence contribution** | +0.14 |

**Context shape:**
```json
{
  "reinforcement_count": 4,
  "weighted_strength": 0.67,
  "window_days": 14,
  "signals": [
    {"type": "job_postings", "count": 3, "weight": 0.20},
    {"type": "patent_filing", "count": 1, "weight": 0.25},
    {"type": "github_activity", "delta_pct": 40, "weight": 0.15},
    {"type": "search_volume_anomaly", "delta_pct": 28, "weight": 0.07}
  ]
}
```

---

## STOCK_INSIDER_ACTIVITY

| Field | Value |
|-------|-------|
| **Code** | `STOCK_INSIDER_ACTIVITY` |
| **Status** | ACTIVE |
| **Description** | Registered insider (officer, director, 10%+ holder) filed a buy or sell above a meaningful threshold. |
| **Fire condition** | Transaction value ≥ $500,000 AND filed within SEC deadline |
| **Confidence contribution** | +0.10 (buy) or +0.08 (sell — sells are less informative) |

**Context shape:**
```json
{
  "transaction_type": "buy",
  "insider_role": "CEO",
  "transaction_value_usd": 2400000,
  "shares": 20000,
  "price_per_share": 120.00,
  "filing_date": "2026-08-02"
}
```

---

## STOCK_ANALYST_UPGRADE

| Field | Value |
|-------|-------|
| **Code** | `STOCK_ANALYST_UPGRADE` |
| **Status** | ACTIVE |
| **Description** | Analyst firm upgrades the stock's rating (e.g., Hold → Buy, Sell → Hold). |
| **Fire condition** | Rating changes in positive direction |
| **Confidence contribution** | +0.08 |

**Context shape:**
```json
{
  "analyst_firm": "Goldman Sachs",
  "prior_rating": "Hold",
  "new_rating": "Buy",
  "price_target_prior": 110,
  "price_target_new": 145
}
```

---

## STOCK_ANALYST_DOWNGRADE

| Field | Value |
|-------|-------|
| **Code** | `STOCK_ANALYST_DOWNGRADE` |
| **Status** | ACTIVE |
| **Description** | Analyst firm downgrades the stock's rating. |
| **Fire condition** | Rating changes in negative direction |
| **Confidence contribution** | +0.08 (downside opportunity) |

**Context shape:**
```json
{
  "analyst_firm": "Morgan Stanley",
  "prior_rating": "Buy",
  "new_rating": "Hold",
  "price_target_prior": 145,
  "price_target_new": 110
}
```

---

*Logan Intelligence TriggerEvent Registry: Stocks — v3.1.2 | 2026-08-03*
*New in v3.1.2. 14 codes registered.*
