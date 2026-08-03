# Logan Intelligence System — Opportunity Decay Engine

The Opportunity Decay Engine ensures the Opportunity Field reflects the present — not history.
Every opportunity loses strength unless evidence actively refreshes it.

Without decay, Logan would accumulate noise. High-confidence opportunities from last week
would crowd the field with stale signals. The user would stop trusting the field.

---

## Core Principle

Confidence is not permanent. Evidence decays. The world moves on.

```
An opportunity that was HIGH CONVICTION yesterday
but has received no new supporting signals today
should be BUILDING CONVICTION — or lower.

An opportunity where crowd sentiment has reversed
should lose confidence immediately, not drift.

An opportunity where the catalyst passed without event
should transition to OUTCOME, not sit frozen.
```

Decay is not punishment — it is accurate modeling of uncertainty over time.

---

## The Four Decay Types

### 1. TIME DECAY

Every opportunity loses a small amount of confidence passively, with no activity.

```
Mechanism
  · Base decay rate: configurable per domain and lifecycle stage
  · Applied every N hours regardless of other signals
  · Represents: "the longer since new evidence, the less certain we are"

Decay rates (V1 defaults)
  Stage               Rate per 24h
  ─────────────────────────────────
  DETECTED            -0.05
  EMERGING            -0.04
  BUILDING CONVICTION -0.03
  HIGH CONVICTION     -0.02
  ACTION WINDOW       -0.01  (lowest — time-sensitive catalysts are fresh)

Domain modifiers
  Sports              1.5×  (opportunities resolve fast)
  Crypto              1.3×  (market moves fast)
  Stocks              1.0×  (base rate)
  Poly Markets        0.9×  (contract prices are sticky)
  Social              1.2×  (attention cycles faster)

Stopped by
  Any new supporting signal resets time decay accumulation
  New detector fire pauses time decay for 24h
```

---

### 2. REACTION DECAY

When a user sees an opportunity and does not engage, confidence adjusts.

```
Mechanism
  · Logan tracks whether a delivered opportunity received user attention
  · Delivered but ignored: decay applied (user not interested)
  · Delivered and engaged: confidence slightly boosted, decay paused
  · Never delivered: no reaction decay

Decay amounts
  Seen but ignored (1st time)       -0.03
  Seen but ignored (2nd time)       -0.05
  Seen but ignored (3rd+ time)      -0.08
  Dismissed explicitly              -0.15

Ceiling
  Reaction decay cannot reduce confidence below 0.30
  (WATCHING floor — Logan keeps monitoring even when user ignores)

Important
  Reaction decay informs User Model, not Hit Quality.
  The objective opportunity score does not change because a user ignored it.
  What changes is the user_value_score for that entity.
```

---

### 3. CROWD DECAY

When community sentiment reverses, confidence decays faster.

```
Mechanism
  · Community Intelligence continuously updates community_momentum
  · If community_momentum reverses direction while opportunity is active:
      immediate decay applied proportional to reversal speed
  · If community disperses (volume drops sharply without reversal):
      moderate decay applied

Decay amounts
  Sharp sentiment reversal           -0.10 to -0.20 depending on speed
  Volume collapse without reversal   -0.05 to -0.10
  Gradual sentiment softening        -0.02 to -0.05 per day

Does not apply when
  · Divergence was the basis of the opportunity
    (crowd reversing is expected and may be confirming, not disconfirming)
  · Structural detector fired — crowd momentum not the primary evidence
```

---

### 4. CONTRADICTION DECAY

When incoming signals directly contradict the evidence base, confidence decays hard.

```
Mechanism
  · Evidence Trust evaluates each new signal for contradiction
  · If new signal contradicts primary supporting evidence:
      contradiction flag raised, decay applied
  · If multiple contradicting signals arrive within time window:
      compound contradiction decay applied

Decay amounts
  Single credible contradiction      -0.10 to -0.15
  Multiple aligned contradictions    -0.20 to -0.35
  High-credibility source contradiction  decay * 1.5 multiplier

Contradiction types
  PRICE_REVERSAL      Price moved strongly opposite to expected direction
  NEWS_CONTRADICTION  News directly counters the established hypothesis
  SIGNAL_REVERSAL     Previously strong signal has reversed
  EXPERT_CORRECTION   High-credibility source explicitly contradicts prior signal

Recovery
  Contradiction decay can be recovered if contradicting signal itself
  is later contradicted (and has not triggered stage regression yet)
```

---

## Decay Accumulation

All four decay types accumulate independently and sum.

```
total_decay_24h = time_decay
                + reaction_decay
                + crowd_decay
                + contradiction_decay

new_confidence = current_confidence - total_decay_24h
new_confidence = max(0.0, new_confidence)  ← floor at 0
```

A single strong contradiction can push an opportunity backward in a single cycle.
Time decay alone moves things slowly.

---

## Stage Regression

When confidence falls below the threshold for the current stage,
the opportunity regresses to the appropriate lower stage.

```
Confidence drops to    Stage becomes
─────────────────────────────────────
< 0.80                 HIGH CONVICTION  →  BUILDING CONVICTION
< 0.65                 BUILDING CONVICTION  →  EMERGING
< 0.50                 EMERGING  →  DETECTED
< 0.30                 DETECTED  →  WATCHING
< 0.10                 WATCHING  →  (retirement candidate)
```

Stage regression is logged in `stage_history` with trigger = "decay".

---

## Retirement

An opportunity is retired when:
- Confidence has been below 0.10 for 7+ consecutive days
- OR the catalyst has resolved (moves to OUTCOME stage)
- OR the entity has left the watched domains
- OR user explicitly dismisses permanently

Retired opportunities move to `OUTCOME` stage and then `LEARNING`.
They are archived in Operational History and never deleted.

---

## Decay Object

DecayState is attached to every OpportunityLifecycle record.

```
DecayState {
  schema_version            "1.0"
  opportunity_id            string
  time_decay_accumulated    float  (total time decay not yet offset by new signals)
  reaction_decay_count      int    (number of ignore events)
  crowd_decay_accumulated   float
  contradiction_count       int
  contradiction_decay_accumulated  float
  last_decay_applied_at     ISO 8601
  last_refreshed_at         ISO 8601  (when new signal reset time decay)
  retirement_candidate      boolean
  retirement_candidate_since  ISO 8601 | null
}
```

---

## Decay and the Opportunity Field

Decay is directly reflected in the visual field.

```
Decay state                         Field effect
──────────────────────────────────────────────────
Active, no significant decay        Normal brightness for stage
Time decay accumulating             Slight dimming
Reaction decay applied              Moves outward from center slightly
Crowd reversal detected             Pulse slows
Strong contradiction               Node visibly dims, moves to outer ring
Stage regression                    Visual transition to new stage appearance
Retirement                          Node fades out and disappears
```

---

## V1 Build Scope

```
Build in V1
  · All four decay types
  · Per-domain time decay rate modifiers
  · Stage regression logic
  · Retirement triggers and archival
  · DecayState object production and attachment to OpportunityLifecycle

Defer to V2
  · ML-based decay rate calibration from outcome data
  · User-specific decay rate learning (some users prefer slower/faster decay)
  · Cross-opportunity decay (one opportunity's outcome decays related ones)
  · Decay visualization analytics in Portfolio
```

---

## Testing Requirements

```
Before shipping, verify:
  · Time decay applies correctly per stage and domain modifier
  · Reaction decay accumulates correctly across multiple ignore events
  · Crowd reversal triggers correct decay amount
  · Contradiction decay applies with correct multipliers
  · Stage regression fires at correct confidence thresholds
  · Retirement triggers after correct conditions are met
  · New supporting signal correctly resets time decay accumulation
  · Decay cannot push confidence below 0.0 (floor enforced)
  · DecayState object matches 03_DATA_CONTRACTS.md exactly
  · Divergence-based opportunities are exempt from crowd decay correctly
```
