# Logan Intelligence System — Opportunity Lifecycle

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
See `07_OPPORTUNITY_DECAY.md`.

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

Typical stay  Permanent record — does not expire

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
Node pulse = ACTION WINDOW state

---

## V1 Build Scope

```
Build in V1
  · All 8 lifecycle stages defined and enforced
  · Stage transitions with logged triggers
  · stage_velocity calculation
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
  · Opportunity Portfolio returns correct counts per stage
  · LEARNING stage correctly marks learning_written = true
  · OpportunityLifecycle object matches 03_DATA_CONTRACTS.md exactly
  · Terminal stages (LEARNING) cannot transition forward
```
