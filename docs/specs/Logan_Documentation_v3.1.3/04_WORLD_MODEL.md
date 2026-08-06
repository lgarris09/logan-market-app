# Logan Intelligence — World Model
**Version:** 3.1.3
**TriggerEvent status:** all TriggerEvent code matching, `active_triggers`, and `trigger_events` array behavior described below is SPECIFIED — NOT IMPLEMENTED (V3.1.4 BATCH-3, OD-009). `logan_core/world_model/model.py` does not match, attach, or store TriggerEvent codes as of V3.1.4.

---

## Purpose

The World Model is Logan's continuously updated, structured representation of reality — independent of any individual user.

It is not a database. It is not a cache. It is a **living knowledge graph** that connects entities, relationships, events, and causal links across all domains Logan monitors.

Nothing in the World Model is personalized. Personalization happens downstream in the Reasoning Engine, User Model, and Opportunity Engine. The World Model answers: *What is true about the world right now?*

---

## Core Concept

The World Model maintains a graph where:
- **Nodes** are entities (stocks, teams, contracts, topics, people, organizations)
- **Edges** are relationships (causal links, correlations, ownership, industry membership, event influence)
- **Events** are changes to the state of any node
- **TriggerEvents** are structured, named signal firings that attach to events and link to registered trigger codes. See `TRIGGER_EVENT_FRAMEWORK.md`.

```
Entity: NVIDIA (ticker)
  ├── Industry: Semiconductors
  ├── Theme: AI Infrastructure
  ├── Correlated with: AMD, TSMC, SMCI
  ├── Downstream effects: AI software companies, data center REITs
  ├── Upcoming event: Earnings 2026-08-14
  └── Current state: Price +4.2% pre-market, volume 2.3× average

Entity: DraftKings (ticker)
  ├── Industry: Online Gambling
  ├── Correlated with: FanDuel parent (Flutter), sports media stocks
  ├── Downstream effects: Sports broadcasting, stadium REITs
  └── Cross-domain link: NFL season start → user betting activity → DraftKings revenue
```

---

## Domains

The World Model maintains separate subgraphs per domain, with cross-domain edges where relationships exist.

### Stocks
Entities: tickers, companies, ETFs, indices
Relationships: industry membership, sector, correlated movers, supply chain, customer/supplier
Events: price moves, volume spikes, earnings, filings, analyst changes, leadership changes
TriggerEvent registry: see `TRIGGER_REGISTRY_STOCKS.md`

### Sports Betting
Entities: teams, players, leagues, events, matchups
Relationships: division/conference, historical head-to-head, player-team, coaching staff
Events: injury reports, odds moves, line moves, weather, sharp money movement
TriggerEvent registry: see `TRIGGER_REGISTRY_SPORTS.md`

### Prediction Markets
Entities: contracts, resolution conditions, market categories
Relationships: related contracts (same underlying event), opposing contracts
Events: price spikes, volume surges, sentiment shifts, approaching resolution dates
TriggerEvent registry: see `TRIGGER_REGISTRY_PREDICTION_MARKETS.md`

### Economics
Entities: economic indicators, central banks, policy tools, currencies
Relationships: leading/lagging indicators, policy transmission mechanisms
Events: Fed decisions, CPI releases, jobs reports, GDP revisions
TriggerEvent registry: see `TRIGGER_REGISTRY_STOCKS.md` (macro section)

### News / Social
Entities: topics, narratives, entities mentioned, sentiment themes
Relationships: topic clustering, entity co-mention, narrative amplification
Events: trend emergence, viral threshold, influencer impact, sentiment flips
TriggerEvent registry: see `TRIGGER_REGISTRY_CULTURE.md`

### Crypto
Entities: protocols, tokens, wallets, exchanges
Relationships: token correlation, chain dependencies, exchange exposure
Events: price moves, on-chain flows, protocol events, exchange activity
TriggerEvent registry: see `TRIGGER_REGISTRY_CRYPTO.md`

### Music & Culture (new in v3.1.2)
Entities: artists, labels, genres, events, platforms
Relationships: artist-label, genre-trend, culture-market correlation
Events: chart movements, album drops, tour announcements, viral moments
TriggerEvent registry: see `TRIGGER_REGISTRY_CULTURE.md`

### Personal Finance (new in v3.1.2)
Entities: economic indicators, interest rates, policy changes, consumer categories
Relationships: rate-to-consumer-spending, inflation-to-purchasing-power
Events: Fed rate decisions, CPI shifts, employment changes, credit condition changes
TriggerEvent registry: see `TRIGGER_REGISTRY_PERSONAL_FINANCE.md`

---

## Entity Types

```
entity_type      Examples
─────────────────────────────────────────────────────────
ticker           NVDA, AAPL, BTC-USD
team             Kansas City Chiefs, Manchester City
contract         "Fed cuts rates by >25bps in September"
topic            "AI regulation", "semiconductor shortage"
person           CEO, analyst, coach, player
organization     Federal Reserve, OPEC, SEC
index            S&P 500, Nasdaq 100
commodity        Oil, gold, natural gas
artist           musician, band, label
market_contract  Kalshi / Polymarket contract
```

Entity resolution — canonical IDs, aliases, and cross-domain entity linking: see `ENTITY_RESOLUTION.md`.

---

## Relationship Types

```
relationship_type   Description
────────────────────────────────────────────────────────
causal              A directly causes B
correlated          A and B move together historically
opposing            A and B tend to move inversely
amplifying          A increases attention on B
sector              A and B are in the same sector/industry
supply_chain        A depends on B for inputs
customer_of         A buys from B
downstream_of       Events in A typically affect B later
same_event          A and B both resolve based on the same underlying event
news_linked         A and B are co-mentioned frequently in current coverage
cross_domain        A (one domain) is meaningfully correlated with B (another domain)
```

---

## World Model vs. Raw Signals

Raw signals from receptors are messy, duplicated, and unconnected. The World Model's job is to structure them.

```
Before World Model (raw):
  signal_1: NVDA price +4.2%
  signal_2: NVDA volume 2.3× average
  signal_3: Article: "NVIDIA beats estimates on data center demand"
  signal_4: SMCI price +2.1%
  signal_5: AMD price +1.8%

After World Model (enriched):
  EnrichedEvent {
    entity: NVIDIA
    is_new: false (extending prior event)
    entities_affected: [NVDA, SMCI, AMD, AI-themed ETFs]
    change_delta: price +4.2%, volume 2.3×
    supporting_signals: [signal_1, signal_2, signal_3]
    downstream: [SMCI, AMD, AI sector broadly]
    summary: "NVIDIA earnings beat with data center demand driver; correlated AI infrastructure names moving in sympathy"
    trigger_events: [{ code: "STOCK_EARNINGS_BEAT", entity: "NVDA", fired_at: "..." }]
  }
```

---

## Causal Link Detection

The World Model actively maintains and updates causal link confidence scores between entities.

A causal link is not just "these things correlate" — it is a directional belief: *When A happens, B tends to follow.*

```
Causal link example:
  A: Fed raises rates unexpectedly
  B: Growth stocks sell off
  Confidence: 0.82
  Typical delay: 0–2 trading days
  Historical accuracy: 79% of events in past 5 years
  Contradicting conditions: When market already priced in the move
```

These causal links are what allow Logan to reason about downstream effects — not just what happened, but what is likely to happen next.

---

## Entity State

Every entity in the World Model has a current state snapshot.

```
EntityState {
  entity_id         string
  entity_type       string
  last_updated      ISO8601
  current_values    object     domain-specific (price, odds, contract price, etc.)
  recent_events     uuid[]     last N EnrichedEvents involving this entity
  active_patterns   string[]   patterns currently active for this entity
  downstream_alerts string[]   entities currently flagged as affected
  active_triggers   string[]   TriggerEvent codes currently active for this entity
  trend             string     "rising" | "falling" | "stable" | "volatile" | "unknown"
}
```

---

## Knowledge Graph Updates

The World Model updates continuously as new signals arrive.

**On new signal arrival:**
1. Identify entities mentioned or affected
2. Check if this is a new event or continuation of prior event
3. Update entity state with new values
4. Check for TriggerEvent code matches (see `TRIGGER_EVENT_FRAMEWORK.md`)
5. Check for new causal links or amplification of existing ones
6. Identify downstream entities that should be flagged
7. Emit EnrichedEvent (with trigger_events array populated) for downstream processing

**On contradiction:**
If a new signal directly contradicts the current entity state, the World Model flags the contradiction and emits it in the EnrichedEvent — it does not silently overwrite.

---

## What the World Model Does NOT Do

- It does not personalize. No user-specific weighting happens here.
- It does not score opportunities. Hit quality scoring is Domain Analysis.
- It does not surface alerts. That is the Opportunity Engine.
- It does not remember the user. That is the User Model.
- It does not reason about meaning. That is the Reasoning Engine.

The World Model is ground truth about the world. Nothing more.

---

## V1 Build Scope

**Build in V1:**
- Entity graph for all 8 domains (including culture and personal finance)
- Basic relationship types (correlated, sector, causal where known, cross_domain)
- Entity state snapshots
- TriggerEvent code matching on signal arrival
- EnrichedEvent production with downstream identification and trigger_events array
- Contradiction flagging

**Defer to V2:**
- ML-based causal link discovery
- Dynamic relationship weight updates from outcome data
- Natural language knowledge graph queries
- User-visible "Logan's understanding of X" view

---

*Logan Intelligence World Model — v3.1.2 | 2026-08-03*
*v3.1.2 changes: TriggerEvent integration added (entity state, knowledge graph update flow, EnrichedEvent). Culture and Personal Finance domains added. cross_domain relationship type added. entity_resolution.md reference added.*
