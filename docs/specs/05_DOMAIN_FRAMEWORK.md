# Logan Intelligence System — Domain Analysis Framework

The Domain Analysis Framework scores every entity across five universal dimensions.
The same five dimensions apply to every domain. The implementation differs per domain.
This is what allows Logan to add new domains without redesigning the scoring system.

---

## Why a Framework (Not Fixed Categories)

The original hit scoring approach was stocks-centric:
- News & Catalyst
- Recent Fundamentals
- Historical Fundamentals
- Price & Momentum
- Buzz & Social
- Corporate Events

This cannot score a sports bet, a Polymarket contract, or a crypto token.

The Domain Analysis Framework replaces fixed categories with five universal dimensions,
each with a domain-specific implementation.

---

## The Five Dimensions

### 1. FUNDAMENTALS
**Question:** What does the underlying data say about quality, health, or value?

```
Stocks        Earnings, revenue, margins, guidance, analyst revisions
Sports        Team record, injury report, home/away splits, weather
Crypto        Network activity, developer commits, holder concentration, TVL
Poly Markets  Resolution criteria clarity, contract liquidity, creator history
Social        Account authenticity, engagement rate, growth trajectory
```

**What it measures:** The structural quality of the opportunity independent of recent noise.

---

### 2. MOMENTUM
**Question:** Is the situation moving, and in what direction?

```
Stocks        Price trend, volume trend, relative strength, options flow
Sports        Line movement, sharp money indicators, public bet percentage
Crypto        Price action, volume, whale movements, exchange inflows/outflows
Poly Markets  Contract price movement, volume trend, resolution proximity
Social        Engagement velocity, follower growth rate, share acceleration
```

**What it measures:** The direction and strength of current movement.
Not prediction — observation of trend.

---

### 3. COMMUNITY
**Question:** What is the aggregate attention and sentiment of the relevant crowd?

```
Stocks        Social mention volume, sentiment direction, unusual activity
Sports        Fan sentiment, media coverage weight, public money direction
Crypto        Discord/Telegram activity, Reddit mentions, Twitter volume
Poly Markets  Comment sentiment, platform discussion volume
Social        Cross-platform spread, creator community response
```

**What it measures:** The community signal — distinct from market movement.
Crowd and market can diverge. That divergence is information.

**Important:** Community dimension is objective aggregate data.
It never equals personal relevance. The User Model applies personal relevance.

---

### 4. CATALYSTS
**Question:** What known or emerging events could force a change in value?

```
Stocks        Earnings date, FDA decision, product launch, M&A filing,
              executive change, legal ruling
Sports        Injury report timing, lineup announcement, weather forecast,
              game schedule context
Crypto        Protocol upgrade, exchange listing, unlock event, regulatory news
Poly Markets  Resolution date, related real-world event timing
Social        Upcoming announcement, product drop, event appearance
```

**What it measures:** Time-sensitive trigger events that make the opportunity urgent or non-urgent.

---

### 5. STRUCTURAL
**Question:** Is there an unusual condition in the market or environment itself
that creates or destroys opportunity?

```
Stocks        Options flow asymmetry, short interest, insider activity,
              institutional positioning, sector rotation
Sports        Market inefficiency (line not updated after news),
              public bias creating value on one side
Crypto        Exchange liquidity conditions, smart contract risk,
              regulatory environment
Poly Markets  Contract design flaws, liquidity concentration, platform risk
Social        Platform algorithm changes, policy shifts, creator monetization risk
```

**What it measures:** The structural context of the opportunity —
conditions that affect whether the edge is real or illusory.

---

## Dimension Weights by Domain (V1)

Weights reflect how much each dimension contributes to hit_quality_score.

```
Dimension        Stocks   Sports   Crypto   Poly     Social
─────────────────────────────────────────────────────────
Fundamentals      0.25     0.20     0.20     0.15     0.10
Momentum          0.20     0.25     0.30     0.25     0.35
Community         0.15     0.20     0.20     0.25     0.35
Catalysts         0.25     0.25     0.15     0.25     0.10
Structural        0.15     0.10     0.15     0.10     0.10
─────────────────────────────────────────────────────────
Total             1.00     1.00     1.00     1.00     1.00
```

Weights are V1 defaults. They will be calibrated against outcome data in V2.

---

## Hit Quality Score

```
hit_quality_score = (
  fundamentals_score  * dimension_weight[fundamentals]  +
  momentum_score      * dimension_weight[momentum]      +
  community_score     * dimension_weight[community]     +
  catalyst_score      * dimension_weight[catalysts]     +
  structural_score    * dimension_weight[structural]
)
```

This is a single 0.0–1.0 score.

**Hit Quality is objective.** The same entity receives the same hit_quality_score
regardless of who is viewing it. Personalization does not enter here.

---

## User Value Score

User Value is computed from Hit Quality by the Opportunity Engine — not here.

```
user_value_score = hit_quality_score
  × user_interest_weight[domain][entity]
  × timing_alignment_score
  × risk_tolerance_alignment
  × portfolio_context_factor
```

**Hit Quality and User Value are always preserved separately.**
They are never collapsed into a single number before the Opportunity Engine decision.

Example:
```
Biotech hit:     hit_quality_score = 0.94
Same user:       user_value_score  = 0.18  → suppressed
                 (user has no biotech exposure or interest)
```

---

## DomainAnalysis Object

```
DomainAnalysis {
  schema_version        "1.0"
  entity_id             string
  domain                "stocks"|"sports"|"crypto"|"poly"|"social"
  fundamentals_score    0.0–1.0
  momentum_score        0.0–1.0
  community_score       0.0–1.0
  catalyst_score        0.0–1.0
  structural_score      0.0–1.0
  dimension_details     object   per-dimension supporting data
  hit_quality_score     0.0–1.0  (derived, not stored separately)
  scored_at             ISO 8601
  scoring_signals       signal_id[]  contributing signal ids
  decision_trace        string[]
  execution_metrics     ExecutionMetrics
}
```

---

## Adding a New Domain

To add a domain (e.g., Real Estate, Music):

1. Define how each of the five dimensions is measured in that domain
2. Set dimension weights (must sum to 1.0)
3. Register domain in the domain registry
4. Add a receptor for raw signal ingestion
5. Add normalization rules for the new signal types

No changes to the scoring framework, Opportunity Engine, or downstream layers.

---

## V1 Build Scope

```
Build in V1
  · All five dimensions for Stocks, Sports, Crypto, Poly Markets, Social
  · Domain-specific signal mappings per dimension
  · hit_quality_score calculation
  · DomainAnalysis object production

Defer to V2
  · Weight calibration from outcome history
  · ML-based dimension scoring
  · Cross-domain correlation scoring
  · Real Estate, Music, and additional domain definitions
```

---

## Testing Requirements

```
Before shipping, verify:
  · hit_quality_score uses correct weights per domain
  · Dimension scores are 0.0–1.0 and never negative
  · Same entity scores same regardless of user viewing it (objectivity)
  · hit_quality_score != user_value_score (separation preserved)
  · DomainAnalysis object matches 03_DATA_CONTRACTS.md exactly
  · New domain can be added without modifying existing domain logic
```
