# Logan Intelligence System — Hit Detection System

The Hit Detection System identifies structured opportunity patterns independent of news.
All four detectors produce the same `OpportunityEvidence` object.
Logan reasons over evidence — not over raw detector outputs.

---

## Why Hit Detection Exists

Traditional systems wait for something obvious:
```
News → Analyze → Notify
```

Logan detects before the headline:
```
Weak signal → Weak signal → Weak signal → Pattern → Opportunity
```

This is how experienced analysts work — connecting subtle clues before there is a story.

---

## Architecture

```
EnrichedEvent + NormalizedSignal[]
                    │
     ┌──────────────┼──────────────┬──────────────┐
     ▼              ▼              ▼              ▼
Convergence    Divergence      Pattern         ODSE
Detector       Detector        Engine          Opportunity
                                               Discovery &
                                               Early Signal
                                               Engine
     │              │              │              │
     └──────────────┴──────────────┴──────────────┘
                          │
                          ▼
              Opportunity Evidence Assembler
              (all detectors → OpportunityEvidence)
                          │
                          ▼
                  to Reasoning Engine
```

---

## Detector 1 — Convergence Detector

### Purpose
Watch for multiple independent signals pointing at the same entity from different domains or sources within a time window.

### What Triggers It

| Type | Description | Example |
|------|-------------|---------|
| CROSS_DOMAIN | 2+ signals same entity, different domains | NVDA gets technical breakout + social spike + analyst mention |
| MULTI_SOURCE | Same direction from independent source types | Wire service + options flow + insider filing |
| MACRO_TO_MICRO | Macro → sector → individual entity all aligned | Fed signal → tech sector → individual stock |
| TEMPORAL | Same entity hit across platforms before clear catalyst | Three platforms signal same entity within 20 minutes |

### Detection Logic
```
For each entity in the signal window:
  · Group signals by domain and source type
  · Count unique domains: domain_count
  · Count unique source types: source_count
  · Check temporal clustering: all within N minutes?
  · Calculate convergence strength

Minimum thresholds to fire:
  CROSS_DOMAIN    domain_count >= 2
  MULTI_SOURCE    source_count >= 3
  MACRO_TO_MICRO  3-level chain confirmed
  TEMPORAL        3+ platforms within 20 minutes
```

### Output Fields (OpportunityEvidence)
```
source_detector     "convergence"
evidence_type       "cross_domain"|"multi_source"|"macro_to_micro"|"temporal"
strength            weighted by domain_count and source independence
supporting_signals  all contributing signal_ids
narrative           "NVDA shows convergence across technical, social, and analyst signals
                     from 3 independent sources within 18 minutes"
confidence          0.0-1.0
```

---

## Detector 2 — Divergence Detector

### Purpose
Identify when a market, odds line, or contract is pricing something differently than other signals suggest it should. This is where edges live.

### Divergence Types

| Type | Description |
|------|-------------|
| PRICE_VS_SENTIMENT | Sentiment shifting but price has not followed |
| ODDS_VS_NEWS | News event that historically moves lines has not moved them |
| CONTRACT_VS_SOCIAL | Poly market contract out of step with community sentiment |
| SECTOR_DIVERGENCE | Index moving but component not — or vice versa |
| CORRELATION_BREAK | Two entities that normally track each other have decoupled |

### Detection Logic
```
For each entity:
  1. Calculate expected_value from signal basket
     (what do the non-price signals suggest value should be?)
  2. Compare to actual_value (current market price/odds/contract)
  3. Calculate gap_magnitude = |expected - actual| / expected
  4. Check historical_accuracy of this divergence pattern
  5. Fire if gap_magnitude > domain_threshold AND historical_accuracy > 0.50

Domain thresholds (V1)
  Stocks      gap_magnitude > 0.05  (5%)
  Sports      gap_magnitude > 0.08  (8% of line value)
  Poly        gap_magnitude > 0.10  (10 percentage points)
```

### Output Fields (OpportunityEvidence)
```
source_detector     "divergence"
evidence_type       divergence type from registry
strength            based on gap_magnitude and historical_accuracy
narrative           "Tesla sentiment up 34% over 5 days but price unchanged.
                     Historical accuracy of this setup: 71%."
confidence          historical_accuracy * gap_significance_score
```

### Key Insight
Divergence is not directional prediction. It surfaces an inefficiency. Logan reports the gap and its historical context. The Reasoning Engine determines what it means.

---

## Detector 3 — Pattern Engine

### Purpose
Recognize known setups and structural conditions that have historically preceded significant moves. Pattern recognition — not prediction.

### Pattern Types

**MOMENTUM_BREAK**
```
Trigger:  Rate of change accelerating or decelerating sharply
          Volume confirming the break
Signal:   Stock drifting for 3 weeks, volume suddenly 3x normal
```

**PRE_EVENT_SETUP**
```
Trigger:  Known catalyst approaching — earnings, game, resolution date,
          Fed meeting — with signals building toward it
Signal:   Setup quality scored against prior similar setups
```

**HISTORICAL_ANALOG**
```
Trigger:  Current signal cluster matches prior cluster that preceded a move
Signal:   Similarity scored, prior outcome surfaced as context (not prediction)
V2:       Requires outcome history to train — Phase 2 feature
```

**QUIET_BEFORE_MOVE**
```
Trigger:  Unusually low volatility or engagement on entity that historically
          precedes significant events
Signal:   Absence of noise is itself a signal
```

**ACCUMULATION_PATTERN**
```
Trigger:  Steady low-volume signal buildup without price response
Signal:   Consistent with informed activity before a catalyst
```

### Detection Logic
```
For each pattern type:
  1. Calculate current state metrics
  2. Compare against baseline (rolling 30-day average)
  3. Score deviation from baseline
  4. Match against pattern definition thresholds
  5. Calculate pattern_confidence from historical hit rate
  6. Fire if pattern_confidence > 0.45

pattern_confidence = historical_match_rate * signal_clarity_score
```

### Output Fields (OpportunityEvidence)
```
source_detector       "pattern"
evidence_type         pattern type from registry
strength              pattern_confidence * signal_clarity
narrative             "NVDA showing classic pre-earnings momentum buildup.
                       This pattern has preceded significant moves in
                       7 of the last 9 similar setups."
confidence            pattern_confidence
```

---

## Detector 4 — ODSE (Opportunity Discovery & Early Signal Engine)

### Purpose
Find opportunities before they appear in any feed. Not reacting to signals — discovering weak signals that are beginning to reinforce each other.

### What It Watches

```
HIRING SIGNALS
  · Unusual increase in job postings for specific roles
  · Executive hires from competitor companies
  · Engineering hires in areas before product announcements
  · Location-specific hiring suggesting facility expansion

FILING SIGNALS
  · Patent filings in new technology areas
  · Regulatory filings before announcements
  · SEC filings — insider purchases, ownership changes
  · Trademark filings suggesting new products

OPERATIONAL SIGNALS
  · Supplier expansion or contraction
  · Shipping data anomalies
  · App store ranking changes
  · GitHub repository activity — commits, contributors, stars
  · Domain registrations

SEARCH AND ATTENTION SIGNALS
  · Unusual search volume before news breaks
  · Academic paper citation velocity
  · Conference speaker announcements
  · Podcast appearance patterns

STRUCTURAL SIGNALS
  · Key person departures or arrivals
  · Board composition changes
  · Auditor changes
  · Customer concentration shifts
```

### Weak Signal Logic

No single signal is actionable alone. ODSE watches for weak signals that begin reinforcing each other.

```
Example — Discovery Hit forming:
  Day 1    unusual AI engineering hiring      strength: 0.18  (weak)
  Day 3    three patents filed in CV          strength: 0.22  (weak)
  Day 5    GitHub activity spike              strength: 0.19  (weak)
  Day 7    exec hire from leading AI lab      strength: 0.31  (weak)

Individual signals → below threshold, not acted on
Combined pattern   → reinforcement_count = 4, total_strength = 0.73
Result             → Discovery Hit fires

Before any news has broken.
```

### Detection Logic
```
For each entity being watched:
  1. Collect all weak signals (strength < 0.40 individually)
  2. Group by entity and time window (rolling 14 days)
  3. Count reinforcement_count (signals pointing same direction)
  4. Sum weighted_strength across signals
  5. Check signal diversity (different signal types = stronger)
  6. Fire discovery hit if:
     reinforcement_count >= 3
     AND weighted_strength >= 0.60
     AND at least 2 different signal types

discovery_score = weighted_strength * diversity_bonus * recency_weight
```

### Output Fields (OpportunityEvidence)
```
source_detector       "odse"
evidence_type         "weak_signal_convergence"
strength              discovery_score
supporting_signals    all weak signal ids
narrative             "Four weak signals reinforcing over 7 days:
                       unusual AI hiring, patent filings, GitHub activity,
                       executive hire. No news has broken yet.
                       Pattern age: 7 days."
confidence            discovery_score * 0.85  (discount for early stage)
```

---

## Opportunity Evidence Assembler

### Purpose
Combine all detector outputs per entity. Produce final OpportunityEvidence set for the Reasoning Engine.

### Logic
```
For each entity_id:
  1. Collect all OpportunityEvidence from all four detectors
  2. If no evidence exists → entity passes through without evidence
  3. If one detector fired → single evidence object
  4. If multiple detectors fired → evidence set with multi_detector flag

multi_detector hit types:
  CONVERGENCE + DIVERGENCE    → signals agree AND market hasn't moved → strongest
  CONVERGENCE + PATTERN       → structural setup confirmed by live signals
  DIVERGENCE + ODSE           → weak signals building toward a known gap
  FULL_HIT                    → all four detectors → rare, very high confidence
```

### Strength Escalation
```
Single detector     base strength from detector
Two detectors       strength * 1.30
Three detectors     strength * 1.55
Four detectors      strength * 1.75  (capped at 1.0)
```

---

## V1 Build Scope

```
Build in V1
  · Convergence Detector — cross-domain and multi-source types
  · Divergence Detector — price vs sentiment, contract vs social
  · Pattern Engine — momentum break, pre-event setup
  · ODSE — hiring, patent, GitHub, search anomaly signal types
  · Opportunity Evidence Assembler — all four types

Defer to V2
  · Historical analog matching (requires outcome history)
  · Accumulation pattern (requires longer time series)
  · Quiet-before-move detector (requires volatility baseline)
  · ML-based pattern confidence scoring
  · ODSE shipping data, academic citations
```

---

## Testing Requirements

```
Before shipping, verify:
  · Each detector fires correctly on known setups in simulation
  · No detector fires on flat/uninteresting simulated states
  · Multi-detector escalation applies correctly
  · OpportunityEvidence shape matches 03_DATA_CONTRACTS.md exactly
  · Assembler deduplicates correctly per entity per window
  · ODSE weak signal window correctly spans 14 days
  · Divergence thresholds correct per domain
```
