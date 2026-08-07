# Logan Intelligence System — Opportunity Lifecycle & Decay Engine
**Version:** 3.1.3
**Status:** SPECIFIED — NOT IMPLEMENTED (V3.1.4 BATCH-3, OD-009). The `OpportunityLifecycle` object, its eight stages, stage transitions, stage velocity, the Opportunity Portfolio endpoint, and all four decay types (time, reaction, crowd, contradiction) described in this document are design-only. Zero lifecycle-stage or decay code exists anywhere in `logan_core/` as of V3.1.4 — the current `opportunity/engine.py` produces a single-pass `AttentionRecommendation` with no stage machine and no decay accumulation. Building this as running code is explicitly out of scope for V3.1.4 (OD-009).
*Source: Architecture v1.3 FINAL (2026-07-31). Original: “source_material/10_OPPORTUNITY_ENGINE.md” (historical label).*

---

# Part 1 — Opportunity Lifecycle

Every opportunity Logan tracks moves through a defined lifecycle.
The lifecycle is the difference between Logan and a feed.
A feed shows events. Logan tracks how situations develop over time.

---

## Why a Lifecycle

Without a lifecycle:
- Logan surfaces the same opportunity repeatedly
- There is no way to track conviction building
- There is no concept of an action window
- There is no learning from outcomes

With a lifecycle:
- Every opportunity has a stage and a history
- Users see what Logan is tracking, not just what just happened
- Conviction builds through stages — not through a single score jump
- Outcomes feed back into the learning system

---

## The Eight Stages

```
WATCHING
  │
  ▼
DETECTED
  │
  ▼
EMERGING
  │
  ▼
BUILDING CONVICTION
  │
  ▼
HIGH CONVICTION
  │
  ▼
ACTION WINDOW
  │
  ▼
OUTCOME
  │
  ▼
LEARNING (terminal — writes to Memory)
```

Stages can move backward (regression) under the Decay Engine.
See Part 2 of this file.

---

## Stage Definitions

### WATCHING
```
Definition    Logan is monitoring this entity. No hit has fired yet.
              Background surveillance state.

How entered   Entity is in a watched domain and has received at least
              one normalized signal in the last 30 days.

Confidence    < 0.30

User visible  In Opportunity Portfolio only (not the main Opportunity Field)

Typical stay  Days to weeks, or indefinitely if nothing develops

Exit to       DETECTED — when any detector fires with strength > 0.30
              (retirement) — if no signal activity for 60 days
```

---

### DETECTED
```
Definition    One or more detectors have fired. A pattern has been identified.
              Not yet confirmed by multiple signals.

How entered   Any single detector fires with strength >= 0.30

Confidence    0.30–0.49

User visible  Opportunity Field — low brightness, outer ring

Typical stay  Hours to days

Exit to       EMERGING — if second detector fires or supporting signals strengthen
              WATCHING — if initial evidence weakens below 0.30 threshold
```

---

### EMERGING
```
Definition    Multiple signals are reinforcing. Pattern is developing.
              Logan is building a case, not just reporting a detection.

How entered   Two or more detectors have fired
              OR single detector strength >= 0.55
              AND evidence is not contradicted

Confidence    0.50–0.64

User visible  Opportunity Field — moderate brightness, mid-ring

Typical stay  Hours to a few days

Exit to       BUILDING CONVICTION — if evidence continues to strengthen
              DETECTED — if one of the confirming signals reverses
              WATCHING — if evidence weakens significantly
```

---

### BUILDING CONVICTION
```
Definition    Evidence is accumulating consistently. Hypothesis Engine has
              generated and is actively testing a belief about this entity.
              Logan knows what would confirm or disprove it.

How entered   hit_quality_score >= 0.65
              AND at least two independent detector types have fired
              AND no strong contradiction evidence

Confidence    0.65–0.79

User visible  Opportunity Field — high brightness, mid-inner ring
              Hypothesis and "what would change this" explanation available

Typical stay  Hours to days — this stage tends to move quickly

Exit to       HIGH CONVICTION — if confirmation evidence arrives
              EMERGING — if one confirming leg weakens
              WATCHING — if strong contradiction fires
```

---

### HIGH CONVICTION
```
Definition    Logan's strongest affirmative signal. Evidence is robust,
              multiple detectors confirm, Hypothesis Engine has tested the belief.
              This is Logan's signal that something is worth real attention.

How entered   hit_quality_score >= 0.80
              AND minimum 3 detectors fired OR 2 + strong ODSE evidence
              AND no unresolved contradictions
              AND Conclusion Confidence >= 0.75

Confidence    0.80–0.94

User visible  Opportunity Field — maximum brightness, inner ring
              Full explanation available: evidence, hypothesis, why now

Typical stay  Variable — some resolve quickly, some sustain
              Decay engine degrades this stage actively

Exit to       ACTION WINDOW — if time-sensitive catalyst is approaching
              BUILDING CONVICTION — if evidence partially weakens
              OUTCOME — if the expected event resolves
```

---

### ACTION WINDOW
```
Definition    A time-sensitive catalyst is approaching or has arrived.
              This is NOT a recommendation to act — it is a flag that
              the window for attention is now, not later.

How entered   HIGH CONVICTION
              AND catalyst_score spike (event approaching or arrived)
              AND user_value_score > user's configured threshold

Confidence    Inherits from HIGH CONVICTION stage

User visible  Opportunity Field — pulse animation, highest priority
              Time context visible: "Resolution in 4 hours", "Earnings tomorrow"
              action_window_opens and action_window_closes timestamps shown

Typical stay  Hours to days — time-bounded by catalyst

Exit to       OUTCOME — when the catalyst resolves or the window closes
              HIGH CONVICTION — if catalyst is delayed or cancelled
```

---

### OUTCOME
```
Definition    The expected event has resolved or the opportunity has closed.
              Logan records what happened relative to what it expected.

How entered   Catalyst resolved (price moved, game ended, contract resolved)
              OR opportunity decayed to zero
              OR user marks as resolved

Confidence    N/A — outcome is a factual record, not a probability

User visible  Opportunity Portfolio — outcome section
              Logan summarizes: what it expected, what happened, accuracy

Typical stay  Long-term record — does not expire

Exit to       LEARNING — automatic after outcome is recorded
```

---

### LEARNING (terminal)
```
Definition    Outcome data is processed. The Learning System writes to Memory.
              This stage is what closes the loop — Logan improves from
              what happened, not just from user feedback.

How entered   Automatic from OUTCOME stage

What happens
  · Compare predicted direction vs actual direction
  · Update hit_rate for each detector that contributed
  · Update pattern_confidence for Pattern Engine
  · Update source credibility for Evidence Trust
  · Update TriggerEvent outcome performance records
  · Update User Model if outcome reveals preference information
  · Write HypothesisUpdate to Memory

User visible  Not directly — shows as "Logan learned from this" in history

Exit to       Terminal — opportunity record is archived in Operational History
```

---

## Stage Velocity

Each opportunity tracks how fast it is moving through stages.

```
stage_velocity      current rate of movement (forward or backward)
                    measured as stage changes per 24-hour window

fast               >= 2 stage changes per day
normal             1 stage change per 1–3 days
slow               < 1 stage change per week
stalled            no stage change in 7+ days at non-terminal stage
```

Stage velocity is surfaced to the user when relevant:
- "This has moved from DETECTED to HIGH CONVICTION in 6 hours" → fast
- "Logan has been watching this for 3 weeks with no development" → stalled

Stage velocity as a signal input to the Opportunity Engine is deferred to V2.

---

## OpportunityLifecycle Object

```
OpportunityLifecycle {
  schema_version        "1.0"
  opportunity_id        string (unique, stable across sessions)
  entity_id             string
  domain                string
  current_stage         stage enum
  previous_stage        stage enum | null
  entered_current_at    ISO 8601
  stage_history         StageTransition[]
  stage_velocity        "fast"|"normal"|"slow"|"stalled"
  confidence_at_entry   0.0–1.0
  current_confidence    0.0–1.0
  action_window_opens   ISO 8601 | null
  action_window_closes  ISO 8601 | null
  outcome_record        OutcomeRecord | null
  learning_written      boolean
  decision_trace        string[]
  execution_metrics     ExecutionMetrics
}

StageTransition {
  from_stage            stage enum
  to_stage              stage enum
  transitioned_at       ISO 8601
  trigger               string (what caused the transition)
  confidence_delta      float (confidence change at transition)
}
```

---

## Opportunity Portfolio

The Opportunity Portfolio is the user-facing view of all lifecycle stages.

```
Portfolio shows:
  WATCHING            count of entities in surveillance
  DETECTED            count + entity list
  EMERGING            count + entity list + brief summary
  BUILDING CONVICTION count + entity list + hypothesis summary
  HIGH CONVICTION     count + entity list + full detail
  ACTION WINDOW       count + entity list + time context
  OUTCOME (recent)    last 30 days of resolved opportunities
  LEARNING            confirmation that Logan processed the outcome
```

The Portfolio answers: "What is Logan tracking right now, and where is each item?"
Not just "what is Logan surfacing right now."

---

## Lifecycle and the Opportunity Field

Lifecycle stage maps directly to Opportunity Field visual representation.

```
Stage                 Field Appearance
─────────────────────────────────────────────────────────────
WATCHING              Not shown in main field (Portfolio only)
DETECTED              Outer ring, dim, small node
EMERGING              Mid ring, moderate brightness, medium node
BUILDING CONVICTION   Inner-mid ring, bright, medium-large node
HIGH CONVICTION       Inner ring, maximum brightness, large node
ACTION WINDOW         Inner ring, maximum brightness, pulse animation
OUTCOME               Fades to outer ring, dim (receding)
LEARNING              Not shown (terminal, archived)
```

Node proximity to center = importance × user value
Node brightness = lifecycle stage
Node pulse = ACTION WINDOW state only

---

## V1 Build Scope

```
Build in V1
  · All 8 lifecycle stages defined and enforced
  · Stage transitions with logged triggers
  · stage_velocity calculation
  · action_window_opens and action_window_closes populated at ACTION WINDOW entry
  · OpportunityLifecycle object production
  · Opportunity Portfolio endpoint
  · Lifecycle stage → Opportunity Field visual mapping

Defer to V2
  · Automated outcome detection (price target hit, game ended, etc.)
  · stage_velocity used as a signal input to Opportunity Engine
  · Cross-opportunity correlation tracking
  · Portfolio analytics (hit rate by stage, average velocity)
```

---

## Testing Requirements

```
Before shipping, verify:
  · All 8 stages transition correctly on simulated signal sequences
  · Forward and backward transitions both work
  · Stage cannot skip (WATCHING → HIGH CONVICTION disallowed)
  · stage_velocity calculates correctly over rolling 24h window
  · action_window_opens and action_window_closes populated correctly
  · Opportunity Portfolio returns correct counts per stage
  · LEARNING stage correctly marks learning_written = true
  · OpportunityLifecycle object matches 07_DATA_CONTRACTS.md exactly
  · Terminal stages (LEARNING) cannot transition forward
```

---
---

# Part 2 — Opportunity Decay Engine

The Opportunity Decay Engine ensures the Opportunity Field reflects the present — not history.
Every opportunity loses strength unless evidence actively refreshes it.

Without decay, Logan would accumulate noise. High-confidence opportunities from last week
would crowd the field with stale signals. The user would stop trusting the field.

---

## Core Principle

Confidence is perishable. Evidence decays. The world moves on.

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
  Prediction Markets  0.9×  (contract prices are sticky)
  Social              1.2×  (attention cycles faster)
  Culture             1.4×  (viral cycles are short)
  Personal Finance    0.7×  (macro changes are slow)

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
  Single credible contradiction          -0.10 to -0.15
  Multiple aligned contradictions        -0.20 to -0.35
  High-credibility source contradiction  decay × 1.5 multiplier

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
Strong contradiction                Node visibly dims, moves to outer ring
Stage regression                    Visual transition to new stage appearance
Retirement                          Node fades out and disappears
```

---

## V1 Build Scope

```
Build in V1
  · All four decay types
  · Domain-specific time decay rate modifiers (including culture and personal finance)
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
  · DecayState object matches 07_DATA_CONTRACTS.md exactly
  · Divergence-based opportunities are exempt from crowd decay correctly
```

---

*Logan Intelligence Opportunity Lifecycle & Decay Engine — v3.1.2 | 2026-08-03*
*v3.1.2 changes: action_window_opens and action_window_closes added to ACTION WINDOW stage and OpportunityLifecycle object. "Permanent record" language changed to "Long-term record". TriggerEvent outcome performance added to LEARNING stage. Culture and Personal Finance domain decay modifiers added. Data contracts reference updated to 07_DATA_CONTRACTS.md throughout. Stage velocity as signal input confirmed deferred to V2.*
