# Logan Intelligence System — Layer Interfaces
**Version:** 3.1.3

Each layer has a defined purpose, inputs, outputs, ownership rules, and forbidden behaviors.
Read this before implementing any layer.

**TriggerEvent status:** every TriggerEvent input/output/forbidden-behavior reference below is SPECIFIED — NOT IMPLEMENTED (V3.1.4 BATCH-3, OD-009). No layer in `logan_core/` emits, reads, or stores a TriggerEvent object as of V3.1.4; treat those references as the target interface, not the current one. See `TRIGGER_EVENT_FRAMEWORK.md`.

All object schemas are defined in `07_DATA_CONTRACTS.md`.
TriggerEvent contract and trigger codes: `TRIGGER_EVENT_FRAMEWORK.md` and “TRIGGER_REGISTRY_*.md” (historical label).

---

## System Orchestrator

```
Purpose
  Owns the execution pipeline. Contains no business logic.
  Coordinates layers, handles retries, manages concurrency,
  schedules delayed work, records execution traces.

Execution sequence
  1.  Receptors                (parallel, continuous)
  2.  Normalization
  3.  World Model
  4.  Evidence Trust       ┐
  5.  Community Intel      ├─  parallel
  6.  Hit Detection        ┘
  7.  Memory read
  8.  User Model + Active Context build
  9.  Domain Analysis
  10. Reasoning Engine
  11. Hypothesis Engine
  12. Mental Model Engine
  13. Conclusion Confidence
  14. Opportunity Engine
  15. Opportunity Lifecycle + Decay
  16. Policy + Safety
  17. Prioritization + Attention State
  18. Presentation + Delivery
  Supporting System A. Feedback Layer  (async, event-driven)
  Supporting System B. Learning System   (async, scheduled)

Retry policy
  Transient failures    retry up to 3 times, exponential backoff
  Layer timeout         skip layer, flag in ExecutionTrace, continue
  Critical failure      halt pipeline, emit alert, log trace

Does not own
  Business logic · scoring rules · memory · user state
```

---

## Layer 1 — Domain Receptors

```
Purpose
  Observe raw signals from external sources. Attach source metadata.
  Each receptor is domain-specific and stateless.
  On structured event detection, emit TriggerEvent as first-class object.

Inputs
  External feed data (prices, odds, contracts, social signals,
                      music charts, personal finance indicators)
  Source configuration (endpoints, credentials, polling intervals)

Outputs
  RawSignal {
    schema_version  "1.0"
    signal_id       uuid
    domain          "stocks" | "sports" | "poly" | "social" | "crypto" |
                    "culture" | "personal_finance"
    source_id       string
    source_name     string
    raw_value       any
    captured_at     ISO8601
    metadata        object
  }

  TriggerEvent {
    schema_version  "1.0"
    trigger_id      uuid
    trigger_code    string      registered code from TRIGGER_REGISTRY_*.md
    domain          string
    entity_id       string
    entity_type     string
    signal_ids      uuid[]
    fired_at        ISO8601
    payload         object      domain-specific trigger payload
    status          "active" | "expired" | "superseded" | "cancelled"
    ttl_hours       integer     trigger-specific TTL from registry
  }

Allowed
  Read external APIs
  Emit RawSignal objects
  Emit TriggerEvent objects on structured trigger code match

Forbidden
  Write to Memory
  Read User Model
  Apply trust, confidence, or scoring
  Send notifications
  Filter or rank signals

V1 scope
  Seven receptors: Stocks, Sports Betting, Prediction Markets,
                   Social Trends, Crypto, Culture/Music, Personal Finance
  Polling and webhook-based ingestion

Extension points
  Additional domain receptors added without touching existing layers
  Receptor priority tuning accepted from Orchestrator (tuning only)
```

---

## Layer 2 — Normalization

```
Purpose
  Convert every RawSignal into a common schema.
  Stateless transformation only.

Input
  RawSignal

Output
  NormalizedSignal {
    schema_version  "1.0"
    signal_id       uuid        (inherited)
    domain          string
    entity_id       string
    entity_type     "ticker" | "team" | "contract" | "topic" | "person" |
                    "artist" | "market_contract"
    signal_type     string      (see Signal Type Registry in 07_DATA_CONTRACTS.md)
    value           any
    unit            string
    source_id       string
    source_name     string
    captured_at     ISO8601
    normalized_at   ISO8601
  }

Allowed
  Read domain schema mappings
  Emit NormalizedSignal objects

Forbidden
  Write to Memory
  Read User Model
  Apply trust or confidence scores
  Filter or rank signals
```

---

## Layer 3 — World Model

```
Purpose
  Logan's structured understanding of entities and relationships.
  Owns the entity graph.
  Matches incoming signals to TriggerEvent codes.

Input
  NormalizedSignal
  TriggerEvent[] (from Receptors, if fired)

Output
  EnrichedEvent {
    schema_version  "1.0"
    event_id        uuid
    signal_ids      uuid[]
    domain          string
    is_new          boolean
    prior_event_id  uuid | null
    entities        Entity[]
    change_delta    Delta[]
    supporting      uuid[]
    contradicting   uuid[]
    downstream      string[]
    trigger_events  TriggerEvent[]   (populated when trigger codes match)
    summary         string
    occurred_at     ISO8601
    enriched_at     ISO8601
  }

Data ownership
  Owns entity graph
  Owns relationship records
  Owns event deduplication index

Allowed
  Read and write entity graph
  Read Operational History
  Emit EnrichedEvent objects

Forbidden
  Read User Model
  Apply personal relevance
  Score or rank
  Send notifications
```

---

## Layer 4a — Evidence Trust

```
Purpose
  Evaluate source credibility before reasoning begins.
  Parallel with Community Intelligence and Hit Detection.

Input
  EnrichedEvent
  Source reputation registry

Output
  EvidenceTrust {
    schema_version      "1.0"
    event_id            uuid
    source_score        float   0.0-1.0
    corroboration       integer
    recency_score       float   0.0-1.0
    contradiction_flag  boolean
    manipulation_risk   "low" | "medium" | "high"
    completeness        float   0.0-1.0
    trust_score         float   0.0-1.0  (composite — never set manually)
    evaluated_at        ISO8601
  }

Composite trust_score formula (V1)
  trust_score = (
    source_score       * 0.35 +
    corroboration_norm * 0.25 +
    recency_score      * 0.20 +
    completeness       * 0.20
  ) * manipulation_penalty
  manipulation_penalty: low=1.0, medium=0.75, high=0.40

Allowed
  Read source reputation registry
  Write source reputation updates (from Learning System only)
  Emit EvidenceTrust objects

Forbidden
  Read User Model
  Apply personal relevance
  Modify event content
```

---

## Layer 4b — Community Intelligence

```
Purpose
  Measure aggregate community attention and momentum.
  Parallel with Evidence Trust and Hit Detection.
  Never substitutes for personal relevance.
  Community momentum and personal relevance MUST remain separate scores.

Input
  EnrichedEvent
  Engagement data streams

Output
  CommunitySignal {
    schema_version         "1.0"
    event_id               uuid
    engagement_volume      integer
    engagement_velocity    float
    unique_users           integer
    saves_shares           integer
    questions              integer
    lifecycle_state        "emerging" | "peak" | "fading" | "dormant"
    coordinated_risk       float   0.0-1.0
    bot_risk               float   0.0-1.0
    momentum_score         float   0.0-1.0  (composite — never set manually)
    measured_at            ISO8601
  }

UI rendering rule
  Community momentum → node edge glow (visually distinct from brightness)
  Personal relevance → node brightness and proximity
  These must NEVER be visually combined into a single indicator.
  See 11_UI_PHILOSOPHY.md for the UI contract.

Allowed
  Read engagement data streams
  Emit CommunitySignal objects

Forbidden
  Read User Model
  Apply personal relevance
  Modify event content or trust scores
```

---

## Layer 4c — Hit Detection System

```
Purpose
  Identify structured opportunity patterns independent of news.
  All four detectors produce OpportunityEvidence — same shape.
  Every detector also emits TriggerEvent on structured trigger code fire.

Detectors
  Convergence Detector    multiple signals, same entity, different domains
  Divergence Detector     market pricing differently than signals suggest
  Pattern Engine          known setups that historically precede moves
  ODSE                    weak signals reinforcing before headlines break

All detector output
  OpportunityEvidence {
    schema_version       "1.0"
    evidence_id          uuid
    source_detector      "convergence" | "divergence" | "pattern" | "odse"
    entity_id            string
    entity_type          string
    domain               string
    evidence_type        string
    strength             float   0.0-1.0
    supporting_signals   uuid[]
    narrative            string
    confidence           float   0.0-1.0
    trigger_event_ids    uuid[]  (TriggerEvents that contributed, if any)
    detected_at          ISO8601
    decision_trace       DecisionTraceEntry[]
  }

Allowed
  Read NormalizedSignal, EnrichedEvent, Operational History
  Emit OpportunityEvidence objects
  Emit TriggerEvent objects on registered trigger code match

Forbidden
  Write to Memory
  Read User Model
  Apply personal relevance
  Score against user interests
```

---

## Layer 5 — Domain Analysis Framework

```
Purpose
  Score every entity across five standard dimensions.
  Produces hit_quality_score — objective, same for every user.

Input
  EnrichedEvent
  OpportunityEvidence[]
  EvidenceTrust
  TriggerEvent[] (scoring adjustments from TRIGGER_SCORING_AND_CONFLICT_RULES.md)
  Domain dimension adapters (one set per domain)

Output
  DomainAnalysis {
    schema_version    "1.0"
    entity_id         string
    domain            string
    dimension_scores {
      fundamentals    float   0.0-1.0
      momentum        float   0.0-1.0
      community       float   0.0-1.0
      catalysts       float   0.0-1.0
      structural      float   0.0-1.0
    }
    hit_quality_score float   0.0-1.0  (weighted combination)
    dimension_weights object  (domain-specific, adjustable)
    trigger_adjustments object  (score modifiers from active TriggerEvents)
    analyzed_at       ISO8601
  }

Allowed
  Read EnrichedEvent, OpportunityEvidence, EvidenceTrust, TriggerEvent
  Read domain adapter configuration
  Read TRIGGER_SCORING_AND_CONFLICT_RULES.md modifiers
  Emit DomainAnalysis objects

Forbidden
  Read User Model (hit_quality is objective — no personalization here)
  Write to Memory
  Send notifications
```

---

## Memory System

```
Purpose
  Persistent store of retained evidence and references.
  Does not interpret. Does not decide.

Operational History (separate store)
  All raw signals, events, prices, outcomes — retained indefinitely
  Queryable by reference. Not loaded into active memory.

Logan Memory (active store)
  Selected evidence that may influence future reasoning:
  user statements · behavior records · feedback · outcomes
  source reliability · prior analyses · corrections · preferences
  trigger event outcome performance records

Output
  MemoryRecord {
    schema_version  "1.0"
    record_id       uuid
    user_id         string  required, non-empty (added v3.1.3, ADR-033)
    record_type     string  (see Memory Record Type Registry in 07_DATA_CONTRACTS.md)
    content         any
    domain          string | null
    entities        string[]
    source_layer    string  (must be "learning_system")
    created_at      ISO8601
    last_accessed   ISO8601
    decay_weight    float   0.0-1.0
  }

Data ownership
  Owns all Logan Memory records
  References (does not own) Operational History

Allowed
  Receive writes from Learning System only
  Serve reads to Reasoning Engine, User Model, Hypothesis Engine

Forbidden
  Self-modify from events or feedback directly
  All writes must route through Learning System
```

---

## User Model

```
Purpose
  Logan's durable interpretation of who this user is.
  Updated only through Learning System — never from raw events.

Input
  MemoryRecord[] from Memory System

Output
  UserModel {
    schema_version          "1.0"
    user_id                 string
    interests               Interest[]
    goals                   string[]
    holdings                Holding[]
    risk_tolerance           "conservative" | "moderate" | "aggressive" | "unknown"
    inferred_expertise      Expertise[]
    domain_preferences      DomainPref[]
    established_behaviors   BehaviorPattern[]
    reaction_speed          "fast" | "measured" | "slow" | "unknown"
    explanation_preference  "brief" | "detailed" | "unknown"
    evidence_threshold      float   0.0-1.0
    macro_micro_preference  "macro" | "micro" | "balanced" | "unknown"
    model_confidence        float   0.0-1.0
    last_updated            ISO8601
    version                 integer
  }

Allowed
  Read Memory System
  Emit UserModel to Reasoning Engine and Opportunity Engine

Forbidden
  Update itself directly from feedback or events
  All updates route through Learning System → Memory → User Model rebuild
```

---

## Active Context

```
Purpose
  Describe the user's present moment.
  Temporary — expires at session end. Never overwrites User Model.

Output
  ActiveContext {
    schema_version      "1.0"
    session_id          uuid
    current_question    string | null
    time_of_day         "morning" | "midday" | "afternoon" | "evening" | "night"
    recent_activity     Activity[]
    temporary_intent    string | null
    upcoming_events     Event[]
    live_context        LiveState[]
    created_at          ISO8601
    expires_at          ISO8601
  }

Forbidden
  Write to Memory System
  Modify User Model
  Persist beyond session
```

---

## Reasoning Engine

```
Purpose
  Determine the meaning of an event in context.
  Understanding does not mean surfacing.

Inputs
  EnrichedEvent · EvidenceTrust · OpportunityEvidence[]
  DomainAnalysis · UserModel · ActiveContext · World Model (read-only)
  TriggerEvent[] (context for cross-domain reasoning)

Output
  ReasoningResult {
    schema_version      "1.0"
    event_id            uuid
    significance        string
    personal_relevance_narrative  string  (renamed from personal_relevance, ADR-021 —
                                 avoids colliding with Dimensions.personal_relevance)
    connected_entities  string[]
    prior_signal_links  uuid[]
    stance              "confirms" | "contradicts" | "complicates" | "new"
    actionability       "actionable" | "informational" | "ambiguous"
    explanation         string
    supporting_links    Reference[]
    reasoned_at         ISO8601
    decision_trace      DecisionTraceEntry[]
  }

Forbidden
  Write to Memory System
  Modify User Model
  Update trust scores
  Send notifications
```

---

## Hypothesis Engine

```
Purpose
  Generate and test hypotheses from evidence patterns.
  Different from Mental Model — Mental Model stores beliefs,
  Hypothesis Engine generates and tests them.

Flow
  Evidence accumulates
  → Hypothesis generated
  → Registered with confidence + required evidence
  → New evidence arrives
  → Hypothesis strengthened or weakened
  → Mental Model updated with confirmed hypotheses

Inputs
  ReasoningResult · MemoryRecord[] (prior hypotheses) · OpportunityEvidence[]

Output
  Hypothesis {
    schema_version        "1.0"
    hypothesis_id         uuid
    domain                string
    statement             string      plain language belief
    status                "forming" | "testing" | "confirmed" | "disproved" | "retired"
    confidence            float       0.0-1.0
    required_evidence     string[]    what would confirm
    confirming_evidence   string[]    what would strengthen
    disproving_evidence   string[]    what would disprove or kill
    supporting            evidence_id[]
    opposing              evidence_id[]
    created_at            ISO8601
    last_updated          ISO8601
  }

Allowed
  Read ReasoningResult, Memory, OpportunityEvidence
  Write Hypothesis records through Learning System
  Emit HypothesisUpdate to Mental Model Engine

Forbidden
  Write directly to Memory (must route through Learning System)
  Modify ReasoningResult
  Send notifications
```

---

## Mental Model Engine

```
Purpose
  Store Logan's confirmed beliefs about the world.
  Updated by Hypothesis Engine. Read by Opportunity Engine.
  V1: stores and tracks. V2: confidence shifts become signals.

Output
  MentalModel {
    schema_version  "1.0"
    model_id        uuid
    domain          string
    hypothesis      string
    confidence      float   0.0-1.0
    supporting      string[]
    opposing        string[]
    trend           "strengthening" | "weakening" | "stable" | "new" | "retired"
    created_at      ISO8601
    last_updated    ISO8601
    retired_at      ISO8601 | null
  }

V2 addition
  MentalModelDelta {
    model_id            uuid
    prior_confidence    float
    new_confidence      float
    delta               float
    trigger_event_id    uuid
    delta_is_signal     boolean   (true if abs(delta) >= threshold)
  }
```

---

## Conclusion Confidence

```
Purpose
  Evaluate how strongly evidence supports the reasoning conclusion.
  Produces full confidence explanation including explicit uncertainty.

Inputs
  ReasoningResult · EvidenceTrust · MentalModel[] (relevant)

Output
  ConclusionConfidence {
    schema_version      "1.0"
    event_id            uuid
    confidence_score    float   0.0-1.0
    confidence_label    "Very High" | "High" | "Moderate" | "Low" | "Speculative" | "Unknown"
    classification      "fact" | "inference" | "hypothesis" | "speculation"
    raising_factors     string[]
    limiting_factors    string[]
    strengthening_signals string[]
    invalidating_signals  string[]
    alternatives        string[]
    i_dont_know_yet     boolean   (true when evidence is genuinely insufficient)
    i_dont_know_reason  string | null
    evaluated_at        ISO8601
    decision_trace      DecisionTraceEntry[]
  }

Classification thresholds
  fact          source_score >= 0.85, corroboration >= 2
  inference     logically follows from facts, not directly observed
  hypothesis    plausible but not yet well-supported
  speculation   low evidence base, high uncertainty

Forbidden
  Write to Memory
  Modify reasoning output
  Suppress events
```

---

## Opportunity Engine

```
Purpose
  Determine what deserves this user's attention now.
  Separates Hit Quality from User Value.
  Produces Why Not explanation for every entity.

Inputs
  ReasoningResult · ConclusionConfidence · DomainAnalysis
  CommunitySignal · UserModel · ActiveContext
  TriggerEvent[] (cross-domain opportunity detection)
  MentalModelDelta (V2)

Staged decision
  1. Validate      real and complete?
  2. Understand    what does it mean?
  3. Connect       does it matter to this user?
  4. Assess        how much and how soon?
  5. Constrain     confidence and risk limits
  6. Compare       what else competes for attention?
  7. Recommend     attention recommendation + reasons

Output
  AttentionRecommendation {
    schema_version        "1.0"
    event_id              uuid
    recommend             boolean
    hit_quality_score     float   objective — same for all users
    user_value_score      float   personalized to this user
    dimensions {
      personal_relevance      float
      global_importance       float
      community_momentum      float   (v3.1.3, ADR-034: never affects ranking/relevance/confidence)
      urgency                 float
      confidence              float
      novelty                 float
      opportunity_magnitude   float
      risk                    float
      actionability           float
      connection_strength     float
    }
    internal_rank_score  float   derived, internal-only — never set directly, never
                                 returned via any public API (renamed from
                                 priority_score in v3.1.3, ADR-029; see
                                 07_DATA_CONTRACTS.md)
    reasons               string[]
    why_not_explanation   string  (always populated — for every entity)
    competing_items       uuid[]
    trigger_event_ids     uuid[]  (TriggerEvents that influenced this recommendation)
    recommended_at        ISO8601
    decision_trace        DecisionTraceEntry[]
  }

user_value_score =
  hit_quality_score
  × personal_relevance_multiplier   (watchlist/history/unknown)
  × timing_multiplier               (now/today/week/informational)
  × risk_alignment_multiplier       (matches/above/far above tolerance)

Surface thresholds (by user_value_score)
  >= 0.80   Strong opportunity
  >= 0.60   Worth watching
  >= 0.40   Emerging signal
  >= 0.25   Weak signal
  <  0.25   suppressed

Forbidden
  Choose presentation format
  Write to Memory
  Suppress based on policy (Policy layer owns that)
```

---

## Policy and Safety

```
Purpose
  Control how Logan may communicate any conclusion.
  Opportunity Engine decides if it matters.
  Policy decides how it may be said.

Output
  PolicyResult {
    schema_version          "1.0"
    event_id                uuid
    permitted               boolean
    communication_mode      "analysis" | "alert" | "informational" | "suppressed"
    language_constraints    string[]
    required_disclaimers    string[]
    policy_rules_applied    string[]
    geographic_restriction  boolean
    evaluated_at            ISO8601
  }

Forbidden
  Modify reasoning or scoring
  Write to Memory
  Change Opportunity Engine dimensions
```

---

## Prioritization and Attention State

```
Purpose
  Manage competition and repetition across all pending items.
  Separate visibility from interruption.
  Apply notification eligibility rules from NOTIFICATION_POLICY.md.

Output
  PrioritizedItem {
    schema_version        "1.0"
    event_id              uuid
    visibility            "primary" | "feed" | "background" | "hidden"
    interruption          "alert" | "digest" | "none"
    rank                  integer
    cooldown_until        ISO8601 | null
    changed_since_view    boolean
    notification_eligible boolean   (per NOTIFICATION_POLICY.md rules)
    prioritized_at        ISO8601
  }

Attention State maintained
  surfaced[] · dismissed[] · alerted[] · cooldowns[] · fatigue[]

Forbidden
  Modify reasoning, scores, or policy decisions
  Write to Memory System directly
```

---

## Presentation and Delivery

```
Purpose
  Choose actual surface and format. Deliver full explanation.
  Handle correction states when evidence changes after delivery.

Output
  DeliveredItem {
    schema_version            "1.0"
    event_id                  uuid
    surface                   "primary" | "feed_card" | "alert" | "digest" | "background"
    headline                  string  (max 80 chars)
    why_it_matters_to_me      string  (personalized — always first)
    what_happened             string
    why_now                   string
    supporting_evidence       Evidence[]  (source-linked, verified)
    contradicting_evidence    Evidence[]  (explicitly shown — never hidden)
    sources                   Source[]
    how_long_watching         string
    action_window_opens       ISO8601 | null
    action_window_closes      ISO8601 | null
    current_exposure          ExposureDetail | null
    related_exposure          ExposureDetail[] | null
    invalidation_conditions   string[]
    suggested_next_step       string | null
    external_execution_link   string | null   (null if geographic restriction)
    confidence_label          string
    confidence_score          float
    confidence_explanation    ConclusionConfidence (raising/limiting)
    i_dont_know_yet           boolean
    i_dont_know_reason        string | null
    lifecycle_stage           string
    trending_indicator        TrendingIndicator | null  (visually distinct from relevance)
    hit_quality_score         float
    user_value_score          float
    connected_items           uuid[]
    required_disclaimers      string[]
    decision_trace            DecisionTraceEntry[]  (inspectable)
    correction_state          "original" | "updated" | "invalidated"
    correction_note           string | null
    delivered_at              ISO8601
  }

Correction handling
  If new evidence changes a delivered item materially:
    · Update correction_state to "updated" or "invalidated"
    · Set correction_note explaining what changed
    · If action window changes materially → re-eligible for notification
    · If user already acted → surface post-action risk guidance

Forbidden
  Modify scores, policy, or priority order
  Write to Memory System
```

---

## Feedback Layer

```
Purpose
  Observe user responses. Interpret their meaning.
  Click is not confirmation. Intent must be inferred.

Output
  FeedbackSignal {
    schema_version      "1.0"
    event_id            uuid
    interaction_type    "view" | "click" | "dismiss" | "save" | "act" |
                        "share" | "not_relevant" | "remind" | "already_acted"
    inferred_intent     "interested" | "curious" | "dismissing" | "confused" |
                        "accidental" | "researching" | "acting" | "unknown"
    intent_confidence   float   0.0-1.0
    duration_ms         integer
    raw_interaction     string
    observed_at         ISO8601
  }

Rules
  inferred_intent never derived from interaction_type alone
  intent_confidence < 0.50 → inferred_intent should be "unknown"
  Gradual weight updates only
  "not_relevant" → signals this topic class is uninteresting (broader signal than dismiss)
  "already_acted" → positive signal but no further surfacing needed

Forbidden
  Write to Memory System directly
  Modify User Model directly
  All writes route through Learning System
```

---

## Learning System

```
Purpose
  Determine what changes and what does not.
  The only layer permitted to write to Memory and User Model.

Inputs
  FeedbackSignal[] · OutcomeRecord[] (delayed)

Personal Learning Loop inputs
  reaction speed patterns · explanation read rates
  ignored opportunity patterns · macro vs micro preference signals
  evidence threshold behavior · lifecycle stage action patterns
  trigger event outcome accuracy

Output
  MemoryWrite {
    schema_version  "1.0"
    write_id        uuid
    write_type      "new_record" | "update_record" | "decay_update" |
                    "trust_update" | "hypothesis_update" | "trigger_outcome"
    target          "memory" | "user_model" | "trust_registry" | "mental_model"
    content         any
    confidence      float
    authorized_at   ISO8601
  }

Allowed
  Read FeedbackSignal, OutcomeRecord
  Write to Memory System
  Write User Model updates (including communication style preferences)
  Write trust score updates
  Write Hypothesis confidence updates
  Write decay rate recalibrations
  Write TriggerEvent outcome performance records

Forbidden
  Send notifications
  Modify active session
  Bypass decay or confidence constraints
```

---

## Dependency Map

```
Layer                      May read from
─────────────────────────────────────────────────────────────────
Receptors                  External world only
Normalization              Receptors
World Model                Normalization · Operational History · TriggerEvents
Evidence Trust             World Model · Source registry
Community Intelligence     World Model · Engagement streams
Hit Detection              World Model · Normalization
Domain Analysis            EnrichedEvent · OpportunityEvidence · EvidenceTrust
                           TriggerEvent (scoring adjustments)
Memory System              Learning System (writes only)
User Model                 Memory System
Active Context             Session · Live feeds
Reasoning Engine           World Model · Evidence Trust · OpportunityEvidence
                           DomainAnalysis · User Model · Active Context
                           TriggerEvent (cross-domain context)
Hypothesis Engine          Reasoning · Memory · OpportunityEvidence
Mental Model Engine        Hypothesis Engine · Learning System
Conclusion Confidence      Reasoning · Evidence Trust · Mental Model
Opportunity Engine         Reasoning · Conclusion Confidence · DomainAnalysis
                           Community Intelligence · User Model · Active Context
                           TriggerEvent · Mental Model (V2)
Policy + Safety            Opportunity Engine · Policy ruleset
Prioritization             Policy · Attention State · NOTIFICATION_POLICY.md
Presentation               Prioritization · Reasoning · Conclusion Confidence
Feedback Layer             User interactions
Learning System            Feedback · Outcomes → writes to Memory
```

---

## What No Layer May Do Without Authorization

```
Write to Memory System      Learning System only
Modify User Model           Learning System only
Send notifications          Presentation + Delivery only
Apply personal relevance    Reasoning Engine and below only
Score or rank               Opportunity Engine only
Suppress by policy          Policy + Safety only
Choose surface format       Presentation + Delivery only
Emit TriggerEvent           Receptors and Hit Detection only
```

---

*Logan Intelligence Layer Interface Specification — v3.1.2 | 2026-08-03*
*v3.1.2 changes: TriggerEvent added to Layer 1, 3, 4c, 5, and Opportunity Engine outputs. Culture and Personal Finance added to Layer 1 V1 scope. entity_type expanded. DeliveredItem field set updated. FeedbackSignal interaction_type expanded. NOTIFICATION_POLICY.md reference added. File reference updated to 07_DATA_CONTRACTS.md.*
*v3.1.3 changes: ReasoningResult.personal_relevance renamed to personal_relevance_narrative (ADR-021, previously unreconciled in this file). AttentionRecommendation.priority_score renamed to internal_rank_score, marked internal-only/never-public (ADR-029). Dimensions.community_momentum annotated per ADR-034. MemoryRecord gains required user_id (ADR-033).*
