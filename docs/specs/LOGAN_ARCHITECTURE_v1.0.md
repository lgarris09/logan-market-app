# Logan Intelligence System — Architecture v1.0 (corrected)

Status: **Locked for Phase 1**, per [ADR-014](../DECISIONS.md#adr-014-adopt-the-logan-intelligence-system-v10-architecture-as-canonical-retire-the-fastapisqlite-sketch-as-historical).
This document consolidates and corrects the original architecture package (Architecture v1.0 + Layer
Interface Specification v1.0), reconciled against the rest of `docs/` on 2026-07-30. Corrections applied,
each tracked in [DECISIONS.md](../DECISIONS.md):

- News added as a fifth Domain Receptor ([ADR-020](../DECISIONS.md#adr-020-news-added-as-a-fifth-domain-receptor)) — appears throughout as `domain: "news"`.
- Crypto added as a sixth Domain Receptor ([ADR-024](../DECISIONS.md#adr-024-crypto-added-as-a-sixth-domain)) — appears throughout as `domain: "crypto"`.
- The Opportunity Wheel is renamed the Opportunity Field ([ADR-023](../DECISIONS.md#adr-023-opportunity-wheel-renamed-to-opportunity-field)) — read `"wheel"` surface values and prose below as the Field.
- `ReasoningResult.personal_relevance` renamed to `personal_relevance_narrative` ([ADR-021](../DECISIONS.md#adr-021-package-internal-documentation-fixes)).
- Operational History is written by the System Orchestrator, not left ownerless ([ADR-016](../DECISIONS.md#adr-016-orchestrator-owns-writing-operational-history)).
- Mental Model Engine is confirmed in Phase 1 build scope as a pass-through slot ([ADR-015](../DECISIONS.md#adr-015-mental-model-engine-built-as-a-v1-pass-through-slot-in-phase-1)).

Treat everything below as locked per the source package's own ground rules: don't merge layer
responsibilities, don't bypass ownership boundaries, don't remove versioning/explainability/observability.
If implementation reveals a genuine issue, document the rationale as a new ADR before changing an
interface or contract — do not silently drift from this document.

## Pipeline diagram

```text
┌────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL WORLD                            │
│  Markets · Sports · Prediction Markets · Social · News              │
│  Portfolios · Calendars · Connected Apps · User Activity            │
│  (V1 receptors only cover the first five; the rest are unbuilt      │
│   Phase 1+ inputs, not yet wired to any receptor)                   │
└────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────┐
│                        DOMAIN RECEPTORS (V1: five)                 │
│  Observe raw signals and attach source metadata                    │
│  Stocks · Sports Betting · Poly Markets · Social Trends · News      │
└────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────┐
│                          NORMALIZATION                              │
│  Convert every raw signal into a common schema                     │
│  domain · entity · signal_type · value · source · timestamp        │
└────────────────────────────────┬────────────────────────────────────┘
                                  │
                    ┌─────────────┴──────────────┐
                    │  ORCHESTRATOR persists      │
                    │  NormalizedSignal (and      │
                    │  later EnrichedEvent, etc.) │
                    │  to OPERATIONAL HISTORY      │
                    │  here — before World Model   │
                    │  runs. See ADR-016.          │
                    └─────────────┬──────────────┘
                                  ▼
┌────────────────────────────────────────────────────────────────────┐
│                          WORLD MODEL                                │
│  Logan's structured understanding of entities and relationships.   │
│  Owns the entity graph, relationship records, dedup index.         │
│  · Deduplicate — new signal or repeat of the same event?           │
│  · Extract entities — ticker, team, contract, person, topic        │
│  · Detect change — what is different from prior state?             │
│  · Merge signals — which support or contradict this?               │
│  · Connect effects — what downstream entities could this affect?   │
└──────────────┬───────────────────────────────────────┬──────────────┘
               │                                        │
               ▼                                        ▼
┌───────────────────────────┐            ┌──────────────────────────────┐
│  INITIAL EVIDENCE TRUST   │            │   COMMUNITY INTELLIGENCE     │
│  (parallel with Community │            │   (parallel with Evidence    │
│   Intelligence)           │            │    Trust)                    │
│  · source credibility     │            │  · engagement volume/velocity│
│  · corroboration          │            │  · unique users, saves,      │
│  · recency + decay        │            │    shares, questions         │
│  · contradiction          │            │  · lifecycle state           │
│  · manipulation risk      │            │  · coordinated/bot risk      │
│  · data completeness      │            │                              │
└──────────────┬─────────────┘            └──────────────┬───────────────┘
               │                                          │
               └───────────────────┬──────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────┐
│                          MEMORY SYSTEM                               │
│  OPERATIONAL HISTORY (owned by Orchestrator, see above)             │
│    Raw signals, events, prices, engagement, outcomes — retained     │
│    indefinitely, queryable by reference, not loaded into active     │
│    memory.                                                          │
│  LOGAN MEMORY (owned by Memory System)                              │
│    Selected evidence: user statements, behavior records, feedback   │
│    records, outcome records, source reliability log, prior          │
│    analyses, correction history, changing preference signals.       │
│    All writes route through the Learning System — no other layer   │
│    writes here, including direct user actions (see ADR-019).        │
└──────────────┬────────────────────────────────────────┬──────────────┘
               ▼                                         ▼
┌───────────────────────────┐            ┌──────────────────────────────┐
│        USER MODEL         │            │       ACTIVE CONTEXT         │
│  Durable interpretation   │            │  Temporary situation.        │
│  of retained evidence.    │            │  Never overwrites the        │
│  Updated only through     │            │  durable User Model.         │
│  Learning System.         │            │  Expires at session end.     │
│  · interests + weights    │            │  · current session/question  │
│  · goals · holdings       │            │  · time of day               │
│  · risk tolerance         │            │  · recent activity           │
│  · inferred expertise     │            │  · temporary intent           │
│  · domain preferences     │            │  · upcoming events            │
│  · established behaviors  │            │  · live market/event context  │
└──────────────┬─────────────┘            └──────────────┬───────────────┘
               └───────────────────┬──────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────┐
│                        REASONING ENGINE                             │
│  Answers: What does this event mean?                                │
│  · Significance in isolation                                        │
│  · Significance given who this user is now                          │
│  · Connection to what the user is already watching                  │
│  · Confirms, contradicts, or complicates prior signals?              │
│  · Actionable or informational?                                      │
│  · What explanation belongs with this if surfaced?                   │
│  Understanding an event does not mean surfacing it.                  │
└────────────────────────────────┬────────────────────────────────────┘
                                  ▼
┌────────────────────────────────────────────────────────────────────┐
│              MENTAL MODEL ENGINE  [ V1: pass-through, built now ]    │
│  Maintains evolving hypotheses about the state of the world.        │
│  V1: stores hypotheses, tracks confidence, passes ReasoningResult    │
│      through unchanged. Does NOT influence the Opportunity Engine.  │
│  V2: produces MentalModelDelta as an Opportunity Engine input;       │
│      confidence shifts above a threshold become signals themselves. │
│  Example: "AI infrastructure demand is accelerating", confidence    │
│  82%, strengthening — a confidence shift is valuable even when the  │
│  triggering event alone is not.                                     │
└────────────────────────────────┬────────────────────────────────────┘
                                  ▼
┌────────────────────────────────────────────────────────────────────┐
│                     CONCLUSION CONFIDENCE                            │
│  Evaluated after reasoning — separate from evidence trust.          │
│  A trustworthy source does not guarantee a trustworthy conclusion.  │
│  · How strongly does evidence support this conclusion?               │
│  · Classification: fact / inference / hypothesis / speculation       │
│  · Plausible alternative explanations present?                       │
└────────────────────────────────┬────────────────────────────────────┘
                                  │  (CommunitySignal arrives here too,
                                  │   as a parallel input)
                                  ▼
┌────────────────────────────────────────────────────────────────────┐
│                       OPPORTUNITY ENGINE                             │
│  Answers: Of everything Logan understands, what deserves this       │
│  user's attention now? Recommends attention — does not execute      │
│  financial actions or issue directives (see ADR-002, ADR-010).      │
│  1. Validate    2. Understand    3. Connect    4. Assess             │
│  5. Constrain   6. Compare       7. Recommend                        │
│  Dimensions: personal_relevance · global_importance ·                │
│  community_momentum · urgency · confidence · novelty ·              │
│  opportunity_magnitude · risk · actionability · connection_strength │
└────────────────────────────────┬────────────────────────────────────┘
                                  ▼
┌────────────────────────────────────────────────────────────────────┐
│                        POLICY + SAFETY                               │
│  Controls how Logan is permitted to communicate the conclusion.     │
│  · analysis vs. financial-advice language enforcement                │
│  · betting/gambling language controls — objective, data-forward     │
│    only for sports betting and prediction markets (ADR-013)         │
│  · jurisdiction restrictions · manipulation/false-urgency prevention │
│  · privacy boundaries · user-defined risk limits                     │
└────────────────────────────────┬────────────────────────────────────┘
                                  ▼
┌────────────────────────────────────────────────────────────────────┐
│                 PRIORITIZATION + ATTENTION STATE                     │
│  · Rank and diversify · Deduplicate across domains                   │
│  · Track surfaced/dismissed · Apply cooldowns · Detect fatigue       │
│  Visibility: wheel · feed card · background · hidden                 │
│  Interruption: push alert · digest · no interruption                 │
└────────────────────────────────┬────────────────────────────────────┘
                                  ▼
┌────────────────────────────────────────────────────────────────────┐
│                    PRESENTATION + DELIVERY                           │
│  What happened? · Why does it matter? · Why does it matter to me?   │
│  Why am I seeing it now? · How confident is Logan? · What else is   │
│  connected? Surfaces: wheel (simplified in Phase 1, see ADR-011) ·   │
│  feed card · alert · digest · background                             │
└────────────────────────────────┬────────────────────────────────────┘
                                  ▼
┌────────────────────────────────────────────────────────────────────┐
│                         USER EXPERIENCE                              │
│              Feed · Alerts · Cards · Decision Prompts                │
└────────────────────────────────┬────────────────────────────────────┘
                                  ▼
┌────────────────────────────────────────────────────────────────────┐
│                  FEEDBACK + OUTCOME LEARNING                         │
│  Feedback interprets behavior, not literal translation:              │
│  curious · disagrees · confused · accidental · dismissing · unknown  │
│  A click is not confirmation. Gradual weight updates only.           │
│  Outcome learning is delayed: signal accuracy · event resolution ·   │
│  source reliability · user value · noise-vs-signal in retrospect.   │
│  Delay window: hours to months, by domain.                           │
└────────────────────────────────┬────────────────────────────────────┘
                                  ▼
┌────────────────────────────────────────────────────────────────────┐
│           MEMORY SYSTEM · USER MODEL · TRUST UPDATES                 │
│  Evidence accumulates. User Model updates. Trust scores recalibrate │
│  as outcomes resolve. Mental Model confidences update (V2).          │
│  Temporary behavior never overwrites the durable User Model.         │
└────────────────────────────────────────────────────────────────────┘
```

## Build sequence

- **V1**: Event understanding → Trust → User Model → Opportunity Engine → Delivery. Mental Model Engine
  slot exists and runs, passing events through unchanged.
- **V2**: Mental Model Engine activates — maintains evolving hypotheses across all domains, confidence
  shifts become signals in their own right, Opportunity Engine reasons from world understanding rather
  than isolated events.

## Final responsibility chain

Receptors notice. Normalization standardizes. The Orchestrator captures history. The World Model
connects. Evidence Trust evaluates the inputs (parallel with Community Intelligence measuring collective
attention). Memory preserves retained knowledge. The User Model interprets the person over time. Active
Context describes the present moment. Reasoning determines meaning. The Mental Model Engine updates world
understanding (pass-through in V1). Conclusion Confidence evaluates the reasoning. The Opportunity Engine
recommends attention. Policy controls communication. Prioritization manages competition and repetition.
Delivery decides where and when it appears. Feedback reveals response. Learning determines what changes.

---

## Layer interface specifications

### Layer 1 — Domain Receptors

**Purpose**: Observe raw signals from external data sources and attach source metadata. Each receptor is
domain-specific and stateless.

**Input**: External feed data (market prices, odds, contract prices, social signals, news wire items).
Source configuration (API endpoints, credentials, polling intervals).

**Output** — `RawSignal`:
```
schema_version   "1.0"
domain           "stocks" | "sports" | "poly" | "social" | "news" | "crypto"
source_id        string
source_name      string
raw_value        any
captured_at      timestamp
metadata         { feed_type, region, asset_class, ... }
```

**Data ownership**: None. Receptors do not own or persist any data.

**Allowed**: Read external APIs. Emit `RawSignal` objects.

**Forbidden**: Write to Memory. Read from Memory. Read User Model. Send notifications. Modify World Model.

**V1 scope**: Six receptors — Stocks, Sports Betting, Poly Markets, Social Trends, News, Crypto. Phase 1 uses
**simulated data only**; polling/webhook ingestion against live APIs is explicitly deferred (see
[LOGAN_IMPLEMENTATION_PLAN.md](LOGAN_IMPLEMENTATION_PLAN.md)).

**Extension points**: Additional domain receptors added without touching existing layers. Receptor
priority hints accepted from the brain (tuning signal only, not data).

---

### Layer 2 — Normalization

**Purpose**: Convert every `RawSignal` into a common schema regardless of domain. All downstream layers
operate on `NormalizedSignal` only.

**Input**: `RawSignal`.

**Output** — `NormalizedSignal`:
```
schema_version   "1.0"
signal_id        uuid
domain           string
entity_id        string
entity_type      "ticker" | "team" | "contract" | "topic" | "person"
signal_type      string
value            number | string
unit             string
source_id        string
source_name      string
captured_at      timestamp
normalized_at    timestamp
```

**Data ownership**: None. Stateless transformation only.

**Allowed**: Read domain schema mappings. Emit `NormalizedSignal` objects.

**Forbidden**: Write to Memory. Read User Model. Apply trust or confidence scores. Filter or rank
signals.

**V1 scope**: Schema mappings for all six domains. Validation and null handling.

**Signal Type Registry (V1)**:
```
Stocks   price_change · volume_spike · news_event · earnings_signal ·
         analyst_change · technical_breakout
Sports   odds_move · line_move · injury_report · weather_alert ·
         sharp_money · reverse_line_move
Poly     price_spike · sentiment_shift · volume_surge ·
         resolution_approaching · new_contract
Social   trend_emerging · velocity_spike · influencer_post ·
         viral_threshold · sentiment_flip · topic_spike
News     breaking_news · analysis_published · correction_issued ·
         developing_story · headline_shift
Crypto   price_change · volume_spike · volatility_spike ·
         exchange_flow · regulatory_news
```
(News row added per [ADR-020](../DECISIONS.md#adr-020-news-added-as-a-fifth-domain-receptor); Crypto row
added per [ADR-024](../DECISIONS.md#adr-024-crypto-added-as-a-sixth-domain).)

**Extension points**: New domains added by registering a new schema mapping.

---

### Layer 3 — World Model

**Purpose**: Logan's structured understanding of entities and their relationships. Deduplicates signals,
extracts entities, detects state changes, merges supporting/contradicting signals, maps downstream
effects.

**Input**: `NormalizedSignal`.

**Output** — `EnrichedEvent`:
```
schema_version   "1.0"
event_id         uuid
signal_ids       uuid[]
domain           string
is_new           boolean
prior_event_id   uuid (optional, set if is_new = false)
entities         Entity[]
change_delta     Delta[]
supporting       signal_id[]
contradicting    signal_id[]
downstream       entity_id[]
summary          string
occurred_at      timestamp
enriched_at      timestamp
decision_trace   DecisionTraceEntry[] (optional)
```

**Data ownership**: Owns the entity graph, relationship records, event deduplication index.

**Allowed**: Read and write the entity graph. Read Operational History (owned by the Orchestrator, see
[ADR-016](../DECISIONS.md#adr-016-orchestrator-owns-writing-operational-history)). Emit `EnrichedEvent`
objects.

**Forbidden**: Read User Model. Apply personal relevance. Score or rank. Send notifications. **Does not
write Operational History** — that's the Orchestrator's responsibility, not World Model's.

**V1 scope**: Entity extraction for all five domains. Deduplication by entity + signal_type + time window.
Basic downstream effect mapping.

**Extension points**: Causal link inference. Timeline/dependency modeling. Cross-domain entity
resolution.

---

### Layer 4a — Initial Evidence Trust

**Purpose**: Evaluate the credibility of each enriched event before reasoning begins. Runs in parallel
with Community Intelligence.

**Input**: `EnrichedEvent`. Source reputation registry.

**Output** — `EvidenceTrust`:
```
schema_version      "1.0"
event_id            uuid
source_score        float (0.0-1.0)
corroboration       integer (>= 0)
recency_score       float (0.0-1.0)
contradiction_flag  boolean
manipulation_risk   "low" | "medium" | "high"
completeness        float (0.0-1.0)
trust_score         float (0.0-1.0, composite, never manually set)
evaluated_at        timestamp
decision_trace      DecisionTraceEntry[] (optional)
```

**Composite formula (V1)**:
```
trust_score = (source_score * 0.35 + corroboration_norm * 0.25 +
               recency_score * 0.20 + completeness * 0.20) * manipulation_penalty

manipulation_penalty:  low = 1.0, medium = 0.75, high = 0.40
corroboration_norm = min(corroboration / 3, 1.0)
```

**Data ownership**: Owns the source reputation registry. May update source scores based on Learning
System feedback only.

**Allowed**: Read source reputation registry. Write source reputation updates (from Learning System only).
Emit `EvidenceTrust`.

**Forbidden**: Read User Model. Apply personal relevance. Modify event content.

**V1 scope**: Static source reputation registry. Corroboration counting within a time window. Recency
decay function.

---

### Layer 4b — Community Intelligence

**Purpose**: Measure aggregate community attention and momentum around an event. Runs in parallel with
Evidence Trust. Never substitutes for personal relevance.

**Input**: `EnrichedEvent`. Engagement data streams.

**Output** — `CommunitySignal`:
```
schema_version       "1.0"
event_id             uuid
engagement_volume    integer (>= 0)
engagement_velocity  float (rate of change per hour)
unique_users         integer (>= 0)
saves_shares         integer (>= 0)
questions            integer (>= 0)
lifecycle_state      "emerging" | "peak" | "fading" | "dormant"
coordinated_risk     float (0.0-1.0)
bot_risk             float (0.0-1.0)
momentum_score       float (0.0-1.0, composite, never manually set)
measured_at          timestamp
decision_trace       DecisionTraceEntry[] (optional)
```

**Data ownership**: None persistent. Reads engagement streams, emits score only. `lifecycle_state` is
derived from the velocity trend within the engagement data stream's own time window, not from a
persisted history of prior `CommunitySignal` values.

**Allowed**: Read engagement data streams. Emit `CommunitySignal`.

**Forbidden**: Read User Model. Apply personal relevance. Modify event content or trust scores.

**V1 scope**: Volume/velocity measurement. Basic lifecycle state detection. Simple bot-risk heuristics.
`bot_risk >= 0.7` flags for Policy & Safety review.

---

### Layer 5 — Memory System

**Purpose**: Persistent store of retained evidence. Stores only what may influence future reasoning,
personalization, trust, or learning. Does not interpret. Does not decide.

**Two stores**:
- **Operational History** — owned and written by the **System Orchestrator**
  ([ADR-016](../DECISIONS.md#adr-016-orchestrator-owns-writing-operational-history)), immediately after
  Normalization. Raw signals, events, prices, engagement data, outcomes. Retained indefinitely, queryable
  by reference, not loaded into active memory. Memory System references but does not own this store.
- **Logan Memory** — owned by Memory System. Selected evidence: things the user said, past behavior
  records, feedback records (raw, uninterpreted), outcome records (delayed), source reliability log,
  prior analyses, correction history, changing preference signals.

**Output** — `MemoryRecord`:
```
schema_version   "1.0"
record_id        uuid
record_type      string (see registry below)
content          any
domain           string (optional, null if cross-domain)
entities         entity_id[] (optional)
source_layer     string ("learning_system" — no other layer may write)
created_at       timestamp
last_accessed    timestamp (optional)
decay_weight     float (0.0-1.0)
operational_ref  uuid (optional, reference to Operational History)
```

**Memory Record Type Registry (V1)**: `user_statement · behavior_record · feedback_record ·
outcome_record · source_reliability · prior_analysis · preference_signal · correction_record`.

**Data ownership**: Owns all Logan Memory records. References (does not own) Operational History.

**Allowed**: Receive writes from Learning System. Serve reads to Reasoning Engine, User Model, Mental
Model Engine. Apply decay weights over time.

**Forbidden**: Self-modify based on events or feedback directly — all writes route through the Learning
System, including the Memory Inbox confirm/reject action
([ADR-019](../DECISIONS.md#adr-019-memory-inbox-confirmation-routes-through-learning-as-a-feedbacksignal)).
Emit notifications.

---

### Layer 6a — User Model

**Purpose**: Logan's current durable interpretation of who this user is, built from retained memory
evidence. Updated only through the Learning System — never from raw events or clicks.

**Input**: `MemoryRecord[]` from Memory System.

**Output** — `UserModel`:
```
schema_version         "1.0"
user_id                string
interests              Interest[]
goals                  string[] (optional)
holdings               Holding[] (optional)
risk_tolerance         "conservative" | "moderate" | "aggressive" | "unknown"
inferred_expertise     Expertise[] (optional)
domain_preferences     DomainPref[]
established_behaviors  BehaviorPattern[] (optional)
model_confidence       float (0.0-1.0)
last_updated           timestamp
version                integer (increments on each update)
```

`Interest { domain, topic, weight (0.0-1.0), source: "explicit"|"inferred", created_at, last_updated }`
`Holding { domain, entity_id, display_name, size (any, intentionally flexible — not financial advice), added_at }`
`Expertise { domain, level (0.0-1.0), evidence (record_ids, optional), last_updated }`
`DomainPref { domain, active, weight (0.0-1.0), last_updated }`

**Data ownership**: Owns the `UserModel` record. Does not own Memory records.

**Allowed**: Read Memory System. Emit `UserModel` to Reasoning Engine and Opportunity Engine.

**Forbidden**: Update itself directly from feedback or events — all updates route through Learning
System → Memory System → User Model rebuild. Emit notifications.

**V1 scope**: Manual profile seeding on first session. Interest and domain weight tracking. Basic risk
tolerance inference.

---

### Layer 6b — Active Context

**Purpose**: Describe the user's present moment. Temporary. Never overwrites the durable User Model.
Expires at session end or explicit reset.

**Input**: Session data. Recent activity feed. Live market/event context.

**Output** — `ActiveContext`:
```
schema_version    "1.0"
session_id        uuid
current_question  string (optional)
time_of_day       "morning" | "midday" | "afternoon" | "evening" | "night"
recent_activity    Activity[] (optional)
temporary_intent   string (optional)
upcoming_events    Event[] (optional)
live_context       LiveState[] (optional)
created_at         timestamp
expires_at         timestamp
```

**Data ownership**: Owns session-scoped context only. Expires on session end.

**Allowed**: Read session signals and live market/event context. Emit `ActiveContext` to Reasoning Engine
and Opportunity Engine.

**Forbidden**: Write to Memory System. Modify User Model. Persist beyond session.

**V1 scope**: Session-scoped context capture. Time-of-day and recent-activity tracking.

---

### Layer 7 — Reasoning Engine

**Purpose**: Determine the meaning of an event in context, after trust evaluation, with full user context
available. Understanding an event does not mean surfacing it.

**Input**: `EnrichedEvent`, `EvidenceTrust`, `UserModel`, `ActiveContext`, World Model (read-only).

**Output** — `ReasoningResult`:
```
schema_version              "1.0"
event_id                    uuid
significance                string
personal_relevance_narrative string   (renamed from personal_relevance, see ADR-021 —
                                       do not confuse with Dimensions.personal_relevance, a float)
connected_entities          entity_id[] (optional)
prior_signal_links          uuid[] (optional)
stance                      "confirms" | "contradicts" | "complicates" | "new"
actionability               "actionable" | "informational" | "ambiguous"
explanation                 string (one to three sentences, plain language)
supporting_links            Reference[] (optional)
reasoned_at                 timestamp
decision_trace              DecisionTraceEntry[] (optional)
```

**Data ownership**: None. Produces output only.

**Allowed**: Read `EnrichedEvent`, `EvidenceTrust`, `UserModel`, `ActiveContext`, World Model. Emit
`ReasoningResult`.

**Forbidden**: Write to Memory. Modify User Model. Update trust scores. Send notifications.

**V1 scope**: Single-event significance assessment. Personal relevance connection to User Model. Plain
language explanation generation.

---

### Layer 8 — Mental Model Engine

**Status**: Built in Phase 1 as a **pass-through slot**
([ADR-015](../DECISIONS.md#adr-015-mental-model-engine-built-as-a-v1-pass-through-slot-in-phase-1)).

**Purpose**: Maintain evolving hypotheses about the state of the world. Update confidence as new evidence
arrives. A confidence shift on an existing model is itself a signal.

**V1 behavior**: Stores hypotheses, tracks confidence. Passes `ReasoningResult` through unchanged. Does
**not** yet influence the Opportunity Engine. Collects the data needed for V2 activation without a
migration.

**V2 behavior**: Produces `MentalModelDelta` as an Opportunity Engine input; confidence shifts above a
threshold surface as signals in their own right.

**Input**: `ReasoningResult`. `MemoryRecord[]` (prior hypotheses).

**Output (V1)** — `MentalModel`:
```
schema_version   "1.0"
model_id         uuid
domain           string
hypothesis       string
confidence       float (0.0-1.0)
supporting       string[] (optional)
opposing         string[] (optional)
trend            "strengthening" | "weakening" | "stable" | "new" | "retired"
created_at       timestamp
last_updated     timestamp
retired_at       timestamp (optional)
decision_trace   DecisionTraceEntry[] (optional)
```

**Output (V2 addition)** — `MentalModelDelta`:
```
schema_version    "2.0"
model_id          uuid
prior_confidence  float
new_confidence    float
delta             float
trigger_event_id  uuid
delta_is_signal   boolean
delta_threshold   float (default 0.10)
computed_at       timestamp
```

**Data ownership**: Owns `MentalModel` records. Writes to Memory System via Learning System.

**Allowed**: Read `ReasoningResult` and Memory (prior hypotheses). Write updated `MentalModel` records
through Learning System. Emit `MentalModelDelta` (V2).

**Forbidden (V1)**: Influence Opportunity Engine scoring. Emit signals to Presentation layer.

---

### Layer 9 — Conclusion Confidence

**Purpose**: Evaluate how strongly the evidence supports Logan's reasoning conclusion. Separate from
evidence trust — a trustworthy source does not guarantee a trustworthy conclusion.

**Input**: `ReasoningResult`, `EvidenceTrust`, `MentalModel[]` (relevant, V1 read-only).

**Output** — `ConclusionConfidence`:
```
schema_version     "1.0"
event_id           uuid
confidence_score   float (0.0-1.0)
classification     "fact" | "inference" | "hypothesis" | "speculation"
alternatives       string[] (optional)
limiting_factors   string[] (optional)
evaluated_at       timestamp
decision_trace     DecisionTraceEntry[] (optional)
```

**Classification definitions**:
- `fact` — directly observed, `source_score >= 0.85`, `corroboration >= 2`.
- `inference` — logically follows from facts, not directly observed.
- `hypothesis` — plausible but not yet well-supported.
- `speculation` — low evidence base, high uncertainty.

**Data ownership**: None. Produces output only.

**Allowed**: Read `ReasoningResult`, `EvidenceTrust`, `MentalModel`. Emit `ConclusionConfidence`.

**Forbidden**: Write to Memory. Modify reasoning output. Suppress events.

---

### Layer 10 — Opportunity Engine

**Purpose**: Determine what deserves this user's attention now. Produces an attention recommendation with
supporting reasons. Recommends attention — **does not execute financial actions or issue directives**
(see [ADR-002](../DECISIONS.md#adr-002-logan-personalizes-and-contextualizes--it-does-not-give-directive-advice-phase-1),
[ADR-010](../DECISIONS.md#adr-010-advice-boundary-reaffirmed-against-vision-language-confidently-decide-what-to-do-next)).
Does not decide presentation format.

**Input**: `ReasoningResult`, `ConclusionConfidence`, `CommunitySignal`, `UserModel`, `ActiveContext`,
`MentalModelDelta` (V2 only).

**Decision sequence**: 1. Validate — is the event real and complete? 2. Understand — what does it mean?
3. Connect — does it matter to this user? 4. Assess — how much and how soon? 5. Constrain — confidence
and risk limits. 6. Compare — what else is competing for attention? 7. Recommend — produce
`AttentionRecommendation` with reasons.

**Output** — `AttentionRecommendation`:
```
schema_version    "1.0"
event_id          uuid
recommend         boolean
dimensions        Dimensions
priority_score    float (0.0-1.0, derived, never set directly)
reasons           string[] (min 1 entry if recommend = true)
competing_items   event_id[] (optional)
recommended_at    timestamp
decision_trace    DecisionTraceEntry[] (optional)
```

`Dimensions { personal_relevance, global_importance, community_momentum, urgency, confidence, novelty,
opportunity_magnitude, risk, actionability, connection_strength }` — all floats 0.0-1.0.

**Priority score derivation (V1, adjustable, weights documented not hardcoded)**:
```
priority_score = (personal_relevance * 0.25 + urgency * 0.20 + confidence * 0.15 +
                   actionability * 0.15 + global_importance * 0.10 +
                   opportunity_magnitude * 0.08 + novelty * 0.04 +
                   community_momentum * 0.02 + connection_strength * 0.01)
                  * (1 - risk * 0.20)
```

**Data ownership**: None. Reads all inputs, emits recommendation only.

**Allowed**: Read all listed inputs. Emit `AttentionRecommendation`.

**Forbidden**: Write to Memory. Choose presentation format. Suppress based on policy (that's Policy's
job). Send notifications.

---

### Layer 11 — Policy and Safety

**Purpose**: Control how Logan is permitted to communicate any conclusion. The Opportunity Engine
determines whether something matters; Policy determines how Logan may say it.

**Input**: `AttentionRecommendation`. Policy ruleset (jurisdiction, user settings, platform config).

**Output** — `PolicyResult`:
```
schema_version          "1.0"
event_id                uuid
permitted               boolean
communication_mode      "analysis" | "alert" | "informational" | "suppressed"
language_constraints    string[] (optional)
required_disclaimers    string[] (optional)
policy_rules_applied    string[]
evaluated_at            timestamp
decision_trace          DecisionTraceEntry[] (optional)
```

Validation: `permitted = false` requires `communication_mode = "suppressed"`. `communication_mode` must
not be overridden downstream. `required_disclaimers` must appear verbatim in `DeliveredItem`.

**Data ownership**: Owns the policy ruleset.

**Allowed**: Read `AttentionRecommendation` and user-configured risk limits. Emit `PolicyResult`. Suppress
items that violate policy.

**Forbidden**: Modify reasoning or scoring. Write to Memory. Change Opportunity Engine dimensions.

**V1 scope**: Analysis-vs-financial-advice language enforcement. Betting/gambling language controls —
sports betting and prediction-market content must stay objective and data-forward, no urgency-driven or
persuasive framing ([ADR-013](../DECISIONS.md#adr-013-fomourgency-risk-tightened--betting-and-prediction-markets-must-stay-objective)).
User-defined risk-limit enforcement. Required disclaimer injection.

---

### Layer 12 — Prioritization and Attention State

**Purpose**: Manage competition and repetition across all pending items. Separate visibility from
interruption. Prevent the same event from repeatedly surfacing without meaningful change.

**Input**: `PolicyResult[]` (all items cleared by policy). `AttentionState` (what has already been shown).

**Output** — `PrioritizedItem` (within a `PrioritizedQueue`):
```
schema_version      "1.0"
event_id            uuid
visibility          "primary" | "feed" | "background" | "hidden"
interruption        "alert" | "digest" | "none"
rank                integer (>= 1, lower = higher priority)
cooldown_until      timestamp (optional)
changed_since_view  boolean
prioritized_at      timestamp
decision_trace      DecisionTraceEntry[] (optional)
```

`AttentionState { user_id, surfaced[], dismissed[], alerted[], cooldowns[], fatigue[], last_updated }`.

**Data ownership**: Owns `AttentionState`.

**Allowed**: Read `PolicyResult`, `AttentionState`. Write `AttentionState` updates. Emit
`PrioritizedQueue`.

**Forbidden**: Modify reasoning, scores, or policy decisions. Write to Memory System — fatigue signals
route through the Learning System.

**V1 scope**: Rank by priority score. Cooldown enforcement. Basic per-domain fatigue detection.
Visibility and interruption as separate decisions.

---

### Layer 13 — Presentation and Delivery

**Purpose**: Choose the actual surface and format for each prioritized item. Deliver each item with a
complete explanation.

**Input**: `PrioritizedQueue`, `ReasoningResult` (for explanation text), `ConclusionConfidence` (for
confidence display).

**Output** — `DeliveredItem`:
```
schema_version         "1.0"
event_id               uuid
surface                "wheel" | "feed_card" | "alert" | "digest" | "background"
headline               string (max 120 chars)
what_happened          string (factual, no editorializing)
why_it_matters         string (global significance)
why_it_matters_to_me   string (personal relevance from UserModel)
why_now                string (urgency justification)
confidence_label       "High" | "Moderate" | "Low" | "Speculative"
confidence_score       float (0.0-1.0)
connected_items        event_id[] (optional)
required_disclaimers   string[] (optional, from PolicyResult)
decision_trace         DecisionTraceEntry[] (optional)
delivered_at           timestamp
```

**Confidence label mapping**: `>= 0.80` High · `>= 0.55` Moderate · `>= 0.35` Low · `< 0.35` Speculative.

**Data ownership**: None. Reads and formats. Does not own content.

**Allowed**: Read `PrioritizedQueue`, `ReasoningResult`, `ConclusionConfidence`. Emit `DeliveredItem`.

**Forbidden**: Modify scores, policy, or priority order. Write to Memory System.

**V1 scope**: Five surface types implemented. All six explanation fields populated for every item.
Confidence label and score displayed. The `"wheel"` surface is a **technically simplified** version in
Phase 1 — no advanced ripple/physics animation yet
([ADR-011](../DECISIONS.md#adr-011-opportunity-wheel--living-ripple-ui-is-a-required-mvp-differentiator)).

---

### Layer 14 — Feedback Layer

**Purpose**: Observe user responses and interpret their meaning. A click is not confirmation. Behavior
must be interpreted before updating anything.

**Input**: User interaction events `{ event_id, interaction_type, duration, timestamp }`.

**Output** — `FeedbackSignal`:
```
schema_version      "1.0"
event_id            uuid
interaction_type    "view" | "click" | "dismiss" | "save" | "act" | "share"
inferred_intent     "interested" | "curious" | "dismissing" | "confused" |
                    "accidental" | "researching" | "unknown"
intent_confidence   float (0.0-1.0; < 0.50 → inferred_intent should be "unknown")
duration_ms         integer (optional)
raw_interaction     string
observed_at         timestamp
decision_trace      DecisionTraceEntry[] (optional)
```

The Memory Inbox confirm/reject action is a `FeedbackSignal` with `interaction_type: "act"` and
`intent_confidence: 1.0`, processed by Learning immediately rather than on the normal delayed cadence
([ADR-019](../DECISIONS.md#adr-019-memory-inbox-confirmation-routes-through-learning-as-a-feedbacksignal)).

**Data ownership**: None. Interprets and emits. Does not write.

**Allowed**: Read user interaction events. Emit `FeedbackSignal` to Learning System.

**Forbidden**: Write to Memory System directly. Modify User Model directly. Update weights directly.

**V1 scope**: Six interaction types. Intent inference with confidence score. Unknown intent preserved
rather than forced.

---

### Layer 15 — Learning System

**Purpose**: Determine what changes and what does not, based on feedback and outcomes. **The only layer
permitted to write to Memory System and User Model.** Controls the pace and magnitude of all updates.

**Input**: `FeedbackSignal[]`. `OutcomeRecord[]` (delayed — hours to months).

**Output** — `MemoryWrite`:
```
schema_version   "1.0"
write_id         uuid
write_type       "new_record" | "update_record" | "decay_update" |
                 "trust_update" | "hypothesis_update"
target           "memory" | "user_model" | "trust_registry" | "mental_model"
content          any
source_signal    uuid (optional)
confidence       float (0.0-1.0; < 0.40 flagged for review, not blocked)
authorized_at    timestamp
```

`OutcomeRecord { outcome_id, event_id, outcome_type: "signal_accuracy"|"source_reliability"|"user_value"|
"market_resolution"|"event_resolution", result, expected (optional), accuracy (optional), resolved_at,
delay_window, learning_applied }`.

**Data ownership**: Controls write authorization to Memory System. Owns the outcome record queue.

**Allowed**: Read `FeedbackSignal`, `OutcomeRecord`. Write to Memory System and User Model. Write trust
score updates to the Evidence Trust registry. Write `MentalModel` confidence updates (V1 passive, V2
active).

**Forbidden**: Send notifications. Modify active session. Bypass decay or confidence constraints.

**V1 scope**: Gradual weight updates with configurable learning rate. Outcome record queue with delayed
resolution. Source trust updates from outcome results. Immediate processing path for high-confidence
explicit feedback (Memory Inbox confirm/reject).

---

## Dependency map

| Layer | May read from |
|---|---|
| Receptors | External world only |
| Normalization | Receptors |
| Orchestrator (Operational History write) | Normalization output, prior to World Model |
| World Model | Normalization · Operational History (read-only) |
| Evidence Trust | World Model · Source registry |
| Community Intelligence | World Model · Engagement streams |
| Memory System | Learning System (writes only) |
| User Model | Memory System |
| Active Context | Session · Live feeds |
| Reasoning Engine | World Model · Evidence Trust · User Model · Active Context |
| Mental Model Engine | Reasoning · Memory (V1 read) · Learning System (V1 write via LS) |
| Conclusion Confidence | Reasoning · Evidence Trust · Mental Model |
| Opportunity Engine | Reasoning · Conclusion Confidence · Community Intelligence · User Model · Active Context · Mental Model (V2) |
| Policy + Safety | Opportunity Engine · Policy ruleset |
| Prioritization | Policy · Attention State |
| Presentation | Prioritization · Reasoning · Conclusion Confidence |
| Feedback Layer | User interactions |
| Learning System | Feedback · Outcomes → writes to Memory |

## What no layer may do without authorization

| Action | Authorized layer |
|---|---|
| Write to Memory System | Learning System only |
| Modify User Model | Learning System only |
| Write Operational History | System Orchestrator only |
| Send notifications | Presentation + Delivery only |
| Apply personal relevance | Reasoning Engine and below only |
| Score or rank | Opportunity Engine only |
| Suppress by policy | Policy + Safety only |
| Choose surface format | Presentation + Delivery only |

## Complete object index

| Object | Produced by | Consumed by |
|---|---|---|
| RawSignal | Receptors | Normalization |
| NormalizedSignal | Normalization | World Model, Orchestrator (→ Operational History) |
| EnrichedEvent | World Model | Evidence Trust, Community Intelligence, Reasoning Engine |
| EvidenceTrust | Evidence Trust Layer | Reasoning Engine, Conclusion Confidence |
| CommunitySignal | Community Intelligence | Opportunity Engine |
| MemoryRecord | Memory System | User Model, Reasoning Engine, Mental Model Engine |
| UserModel | User Model Layer | Reasoning Engine, Opportunity Engine |
| ActiveContext | Active Context Layer | Reasoning Engine, Opportunity Engine |
| ReasoningResult | Reasoning Engine | Mental Model Engine, Conclusion Confidence, Opportunity Engine, Presentation |
| MentalModel | Mental Model Engine | Conclusion Confidence, Opportunity Engine (V2) |
| MentalModelDelta | Mental Model Engine (V2) | Opportunity Engine (V2) |
| ConclusionConfidence | Conclusion Confidence | Opportunity Engine, Presentation |
| AttentionRecommendation | Opportunity Engine | Policy + Safety |
| PolicyResult | Policy + Safety | Prioritization |
| PrioritizedItem | Prioritization | Presentation |
| AttentionState | Prioritization | Prioritization (self) |
| DeliveredItem | Presentation | User surface, Feedback Layer |
| FeedbackSignal | Feedback Layer | Learning System |
| OutcomeRecord | External resolution | Learning System |
| MemoryWrite | Learning System | Memory System |
| ExecutionTrace | Orchestrator | Observability store |
| ExecutionMetrics | Every layer | Orchestrator |
| DecisionTraceEntry | Every layer | Orchestrator, Explainability queries |

See [LOGAN_DATA_CONTRACTS_v1.0.md](LOGAN_DATA_CONTRACTS_v1.0.md) for the System Orchestrator's own
responsibilities, versioning/explainability/observability conventions, and the remaining supporting
object definitions (`Entity`, `Delta`, `Reference`, `Interest`, `Holding`, `Expertise`, `DomainPref`).
