# Logan Intelligence System — Data Contracts

Every object in the system is defined here.
Read this before defining any schema, type, or model.

---

## Conventions

**schema_version** — every object includes `"schema_version": "1.0"`
- Minor bump: additive changes only (new optional fields)
- Major bump: breaking changes (field removal, type changes)
- All layers must tolerate unknown optional fields gracefully

**decision_trace** — optional on every object, required in V2
```
DecisionTraceEntry {
  layer       string    required
  rule        string    required   plain language rule that fired
  confidence  float     optional   0.0-1.0
  evidence    string[]  optional
  timestamp   ISO8601   required
}
```

**ExecutionMetrics** — every layer emits on completion
```
ExecutionMetrics {
  schema_version   "1.0"
  layer            string    required
  pipeline_run_id  uuid      required
  event_id         uuid      optional
  latency_ms       integer   required
  success          boolean   required
  warnings         string[]  optional
  retries          integer   required   default 0
  confidence       float     optional
  recorded_at      ISO8601   required
}
```

---

## RawSignal

```
Field           Type      Required   Constraints
────────────────────────────────────────────────────────────
schema_version  string    required   "1.0"
signal_id       uuid      required   unique across all signals
domain          string    required   "stocks"|"sports"|"poly"|"social"|"crypto"
source_id       string    required   registered source identifier
source_name     string    required
raw_value       any       required   must not be null
captured_at     ISO8601   required   must not be in the future
metadata        object    optional   domain-specific key-value pairs
```

---

## NormalizedSignal

```
Field           Type      Required   Constraints
────────────────────────────────────────────────────────────
schema_version  string    required   "1.0"
signal_id       uuid      required   inherited from RawSignal
domain          string    required
entity_id       string    required   non-empty
entity_type     string    required   "ticker"|"team"|"contract"|"topic"|"person"
signal_type     string    required   must exist in Signal Type Registry
value           any       required   must match type for signal_type
unit            string    optional
source_id       string    required
source_name     string    required
captured_at     ISO8601   required
normalized_at   ISO8601   required   must be >= captured_at
decision_trace  array     optional
```

**Signal Type Registry (V1)**
```
Stocks    price_change · volume_spike · news_event · earnings_signal
          analyst_change · technical_breakout · filing_event

Sports    odds_move · line_move · injury_report · weather_alert
          sharp_money · reverse_line_move

Poly      price_spike · sentiment_shift · volume_surge
          resolution_approaching · new_contract

Social    trend_emerging · velocity_spike · influencer_post
          viral_threshold · sentiment_flip · topic_spike

Crypto    price_change · volume_spike · on_chain_flow
          protocol_event · wallet_activity · exchange_flow

ODSE      hiring_signal · patent_filing · regulatory_filing
          github_activity · app_ranking_change · search_anomaly
          supplier_change · executive_move · shipping_data
```

---

## EnrichedEvent

```
Field           Type        Required   Constraints
────────────────────────────────────────────────────────────
schema_version  string      required   "1.0"
event_id        uuid        required   new uuid from World Model
signal_ids      uuid[]      required   one or more source signal_ids
domain          string      required
is_new          boolean     required
prior_event_id  uuid        optional   set if is_new = false
entities        Entity[]    required
change_delta    Delta[]     optional
supporting      uuid[]      optional
contradicting   uuid[]      optional
downstream      string[]    optional   entity_ids potentially affected
summary         string      required   one sentence plain language
occurred_at     ISO8601     required
enriched_at     ISO8601     required
decision_trace  array       optional
```

---

## Entity

```
Field         Type      Required
──────────────────────────────────
entity_id     string    required   stable cross-domain identifier
entity_type   string    required   "ticker"|"team"|"contract"|"topic"|"person"
display_name  string    required
domain        string    required
attributes    object    optional   domain-specific properties
```

---

## Delta

```
Field         Type      Required
──────────────────────────────────
field         string    required
prior_value   any       optional   null if no prior state known
new_value     any       required
unit          string    optional
changed_at    ISO8601   required
```

---

## EvidenceTrust

```
Field               Type      Required   Constraints
────────────────────────────────────────────────────────────
schema_version      string    required   "1.0"
event_id            uuid      required
source_score        float     required   0.0-1.0
corroboration       integer   required   >= 0
recency_score       float     required   0.0-1.0
contradiction_flag  boolean   required
manipulation_risk   string    required   "low"|"medium"|"high"
completeness        float     required   0.0-1.0
trust_score         float     required   composite — never manually set
evaluated_at        ISO8601   required
decision_trace      array     optional
```

**Composite formula:**
```
trust_score = (source_score*0.35 + corr_norm*0.25 + recency*0.20 + completeness*0.20)
              * manipulation_penalty
penalty: low=1.0, medium=0.75, high=0.40
corr_norm = min(corroboration/3, 1.0)
```

---

## CommunitySignal

```
Field                 Type      Required   Constraints
────────────────────────────────────────────────────────────
schema_version        string    required   "1.0"
event_id              uuid      required
engagement_volume     integer   required   >= 0
engagement_velocity   float     required   rate of change per hour
unique_users          integer   required   >= 0
saves_shares          integer   required   >= 0
questions             integer   required   >= 0
lifecycle_state       string    required   "emerging"|"peak"|"fading"|"dormant"
coordinated_risk      float     required   0.0-1.0
bot_risk              float     required   0.0-1.0
momentum_score        float     required   composite — never manually set
measured_at           ISO8601   required
decision_trace        array     optional
```

**Note:** bot_risk >= 0.7 → flag for Policy + Safety review

---

## OpportunityEvidence

```
Field               Type      Required   Constraints
────────────────────────────────────────────────────────────
schema_version      string    required   "1.0"
evidence_id         uuid      required
source_detector     string    required   "convergence"|"divergence"|"pattern"|"odse"
entity_id           string    required
entity_type         string    required
domain              string    required
evidence_type       string    required   detector-specific type
strength            float     required   0.0-1.0
supporting_signals  uuid[]    required   at least one
narrative           string    required   plain language — what was detected
confidence          float     required   0.0-1.0
detected_at         ISO8601   required
decision_trace      array     optional
```

---

## DomainAnalysis

```
Field              Type      Required   Constraints
────────────────────────────────────────────────────────────
schema_version     string    required   "1.0"
entity_id          string    required
domain             string    required
dimension_scores   object    required   all five fields required
  fundamentals     float     required   0.0-1.0
  momentum         float     required   0.0-1.0
  community        float     required   0.0-1.0
  catalysts        float     required   0.0-1.0
  structural       float     required   0.0-1.0
hit_quality_score  float     required   weighted combination — never manual
dimension_weights  object    required   domain-specific, must sum to 1.0
analyzed_at        ISO8601   required
```

**Default dimension weights (Stocks):**
```
fundamentals: 0.25, momentum: 0.20, community: 0.18
catalysts: 0.17, structural: 0.20
```

---

## MemoryRecord

```
Field           Type      Required   Constraints
────────────────────────────────────────────────────────────
schema_version  string    required   "1.0"
record_id       uuid      required
record_type     string    required   see Memory Record Type Registry
content         any       required
domain          string    optional
entities        string[]  optional
source_layer    string    required   must be "learning_system"
created_at      ISO8601   required
last_accessed   ISO8601   optional
decay_weight    float     required   0.0-1.0
operational_ref uuid      optional   reference to Operational History
```

**Memory Record Type Registry:**
```
user_statement · behavior_record · feedback_record · outcome_record
source_reliability · prior_analysis · preference_signal · correction_record
reaction_pattern · explanation_engagement · hypothesis_record
```

---

## UserModel

```
Field                   Type           Required
────────────────────────────────────────────────
schema_version          string         required   "1.0"
user_id                 string         required
interests               Interest[]     required
goals                   string[]       optional
holdings                Holding[]      optional
risk_tolerance           string         required   "conservative"|"moderate"|"aggressive"|"unknown"
inferred_expertise      Expertise[]    optional
domain_preferences      DomainPref[]   required
established_behaviors   BehaviorPattern[] optional
reaction_speed          string         required   "fast"|"measured"|"slow"|"unknown"
explanation_preference  string         required   "brief"|"detailed"|"unknown"
evidence_threshold      float          required   0.0-1.0
macro_micro_preference  string         required   "macro"|"micro"|"balanced"|"unknown"
model_confidence        float          required   0.0-1.0
last_updated            ISO8601        required
version                 integer        required   increments on each update
```

---

## Interest

```
Field         Type      Required   Constraints
──────────────────────────────────────────────
domain        string    required
topic         string    required   entity_id or keyword
weight        float     required   0.0-1.0
source        string    required   "explicit"|"inferred"
created_at    ISO8601   required
last_updated  ISO8601   required
```

---

## Holding

```
Field         Type      Required
──────────────────────────────────
domain        string    required
entity_id     string    required
display_name  string    required
size          any       optional   intentionally flexible
added_at      ISO8601   required
```

---

## ActiveContext

```
Field               Type        Required   Constraints
────────────────────────────────────────────────────────────
schema_version      string      required   "1.0"
session_id          uuid        required
current_question    string      optional
time_of_day         string      required   "morning"|"midday"|"afternoon"|"evening"|"night"
recent_activity     Activity[]  optional
temporary_intent    string      optional
upcoming_events     Event[]     optional
live_context        LiveState[] optional
created_at          ISO8601     required
expires_at          ISO8601     required
```

---

## ReasoningResult

```
Field               Type        Required   Constraints
────────────────────────────────────────────────────────────
schema_version      string      required   "1.0"
event_id            uuid        required
significance        string      required   event in isolation
personal_relevance  string      required   given this user
connected_entities  string[]    optional
prior_signal_links  uuid[]      optional
stance              string      required   "confirms"|"contradicts"|"complicates"|"new"
actionability       string      required   "actionable"|"informational"|"ambiguous"
explanation         string      required   1-3 sentences plain language
supporting_links    Reference[] optional
reasoned_at         ISO8601     required
decision_trace      array       optional
```

---

## Hypothesis

```
Field                 Type      Required   Constraints
────────────────────────────────────────────────────────────
schema_version        string    required   "1.0"
hypothesis_id         uuid      required
domain                string    required
statement             string    required   plain language belief
status                string    required   "forming"|"testing"|"confirmed"|"disproved"|"retired"
confidence            float     required   0.0-1.0
required_evidence     string[]  optional   what would confirm
confirming_evidence   string[]  optional   what would strengthen
disproving_evidence   string[]  optional   what would disprove
supporting            string[]  optional   evidence_ids
opposing              string[]  optional   evidence_ids
created_at            ISO8601   required
last_updated          ISO8601   required
retired_at            ISO8601   optional
```

---

## MentalModel

```
Field           Type      Required   Constraints
────────────────────────────────────────────────────────────
schema_version  string    required   "1.0"
model_id        uuid      required
domain          string    required
hypothesis      string    required   plain language
confidence      float     required   0.0-1.0
supporting      string[]  optional
opposing        string[]  optional
trend           string    required   "strengthening"|"weakening"|"stable"|"new"|"retired"
created_at      ISO8601   required
last_updated    ISO8601   required
retired_at      ISO8601   optional
```

---

## ConclusionConfidence

```
Field                   Type      Required   Constraints
────────────────────────────────────────────────────────────
schema_version          string    required   "1.0"
event_id                uuid      required
confidence_score        float     required   0.0-1.0
confidence_label        string    required   "Very High"|"High"|"Moderate"|"Low"|"Speculative"|"Unknown"
classification          string    required   "fact"|"inference"|"hypothesis"|"speculation"
raising_factors         string[]  required   minimum one entry
limiting_factors        string[]  optional
strengthening_signals   string[]  optional
invalidating_signals    string[]  optional
alternatives            string[]  optional
i_dont_know_yet         boolean   required
i_dont_know_reason      string    optional   required if i_dont_know_yet = true
evaluated_at            ISO8601   required
decision_trace          array     optional
```

**Confidence label mapping:**
```
>= 0.80   "Very High"
>= 0.65   "High"
>= 0.45   "Moderate"
>= 0.25   "Low"
<  0.25   "Speculative"
insufficient evidence → "Unknown" + i_dont_know_yet = true
```

---

## AttentionRecommendation

```
Field                 Type        Required   Constraints
────────────────────────────────────────────────────────────
schema_version        string      required   "1.0"
event_id              uuid        required
recommend             boolean     required
hit_quality_score     float       required   0.0-1.0 — objective
user_value_score      float       required   0.0-1.0 — personalized
dimensions            Dimensions  required
priority_score        float       required   derived — never set directly
reasons               string[]    required   min one if recommend=true
why_not_explanation   string      required   always populated
competing_items       uuid[]      optional
recommended_at        ISO8601     required
decision_trace        array       optional
```

---

## Dimensions

```
Field                   Type    Required   Constraints
──────────────────────────────────────────────────────────
personal_relevance      float   required   0.0-1.0
global_importance       float   required   0.0-1.0
community_momentum      float   required   0.0-1.0
urgency                 float   required   0.0-1.0
confidence              float   required   0.0-1.0 from ConclusionConfidence
novelty                 float   required   0.0-1.0
opportunity_magnitude   float   required   0.0-1.0
risk                    float   required   0.0-1.0
actionability           float   required   0.0-1.0
connection_strength     float   required   0.0-1.0
```

**Priority score formula (V1 — adjustable):**
```
priority_score = (
  personal_relevance    * 0.25 +
  urgency               * 0.20 +
  confidence            * 0.15 +
  actionability         * 0.15 +
  global_importance     * 0.10 +
  opportunity_magnitude * 0.08 +
  novelty               * 0.04 +
  community_momentum    * 0.02 +
  connection_strength   * 0.01
) * (1 - risk * 0.20)
```

---

## OpportunityLifecycle

```
Field                   Type      Required   Constraints
────────────────────────────────────────────────────────────
schema_version          string    required   "1.0"
hit_id                  uuid      required
entity_id               string    required
current_stage           string    required   see Stage Registry
stage_history           array     required   StageRecord[]
first_detected_at       ISO8601   required
action_window_opens     ISO8601   optional
action_window_closes    ISO8601   optional
outcome_recorded_at     ISO8601   optional
outcome_summary         string    optional
days_in_pipeline        integer   required
stage_velocity          string    required   "accelerating"|"stable"|"stalling"|"reversing"
```

**Stage Registry:**
```
watching          internal only — user never sees
detected          below surface threshold
emerging          dim node at outer edge
building_conviction brightening node
high_conviction   prominent node
action_window     pulsing node — time sensitive
outcome           fading — resolving
learning          archived
```

---

## PolicyResult

```
Field                   Type      Required   Constraints
────────────────────────────────────────────────────────────
schema_version          string    required   "1.0"
event_id                uuid      required
permitted               boolean   required
communication_mode      string    required   "analysis"|"alert"|"informational"|"suppressed"
language_constraints    string[]  optional
required_disclaimers    string[]  optional
policy_rules_applied    string[]  required
evaluated_at            ISO8601   required
```

**Rule:** permitted=false → communication_mode must be "suppressed"

---

## PrioritizedItem

```
Field               Type      Required   Constraints
────────────────────────────────────────────────────────────
schema_version      string    required   "1.0"
event_id            uuid      required
visibility          string    required   "primary"|"feed"|"background"|"hidden"
interruption        string    required   "alert"|"digest"|"none"
rank                integer   required   >= 1
cooldown_until      ISO8601   optional
changed_since_view  boolean   required
prioritized_at      ISO8601   required
```

---

## DeliveredItem

```
Field                     Type      Required   Constraints
────────────────────────────────────────────────────────────
schema_version            string    required   "1.0"
event_id                  uuid      required
surface                   string    required   "primary"|"feed_card"|"alert"|"digest"|"background"
headline                  string    required   max 120 chars
what_happened             string    required
why_it_matters            string    required
why_it_matters_to_me      string    required
why_now                   string    required
how_long_watching         string    required   e.g. "Logan has been watching this for 8 days"
confidence_label          string    required
confidence_score          float     required   0.0-1.0
raising_factors           string[]  required
limiting_factors          string[]  optional
strengthening_signals     string[]  optional
invalidating_signals      string[]  optional
i_dont_know_yet           boolean   required
i_dont_know_reason        string    optional
hit_quality_score         float     required
user_value_score          float     required
connected_items           uuid[]    optional
required_disclaimers      string[]  optional
decision_trace            array     optional   inspectable by user
delivered_at              ISO8601   required
```

---

## FeedbackSignal

```
Field               Type      Required   Constraints
────────────────────────────────────────────────────────────
schema_version      string    required   "1.0"
event_id            uuid      required
interaction_type    string    required   "view"|"click"|"dismiss"|"save"|"act"|"share"
inferred_intent     string    required   "interested"|"curious"|"dismissing"|"confused"|
                                         "accidental"|"researching"|"unknown"
intent_confidence   float     required   0.0-1.0
duration_ms         integer   optional
raw_interaction     string    required
observed_at         ISO8601   required
```

**Rule:** inferred_intent never derived from interaction_type alone.
intent_confidence < 0.50 → inferred_intent = "unknown"

---

## OutcomeRecord

```
Field             Type      Required   Constraints
────────────────────────────────────────────────────────────
schema_version    string    required   "1.0"
outcome_id        uuid      required
event_id          uuid      required
outcome_type      string    required   "signal_accuracy"|"source_reliability"|
                                       "user_value"|"market_resolution"|"event_resolution"
result            any       required
expected          any       optional
accuracy          float     optional   0.0-1.0
resolved_at       ISO8601   required
delay_window      string    required   "immediate"|"hours"|"days"|"months"
learning_applied  boolean   required   false until Learning System processes
```

---

## MemoryWrite

```
Field           Type      Required   Constraints
────────────────────────────────────────────────────────────
schema_version  string    required   "1.0"
write_id        uuid      required
write_type      string    required   "new_record"|"update_record"|"decay_update"|
                                     "trust_update"|"hypothesis_update"
target          string    required   "memory"|"user_model"|"trust_registry"|"mental_model"
content         any       required
source_signal   uuid      optional
confidence      float     required   0.0-1.0
authorized_at   ISO8601   required
```

**Rule:** All writes must originate from Learning System.
confidence < 0.40 → flagged for review, not blocked.

---

## Complete Object Index

```
Object                    Produced by               Consumed by
──────────────────────────────────────────────────────────────────────
RawSignal                 Receptors                 Normalization
NormalizedSignal          Normalization             World Model, Hit Detection
EnrichedEvent             World Model               Evidence Trust, Community Intel,
                                                    Reasoning, Domain Analysis
EvidenceTrust             Evidence Trust            Reasoning, Conclusion Confidence
CommunitySignal           Community Intelligence    Opportunity Engine
OpportunityEvidence       Hit Detection (all 4)     Domain Analysis, Reasoning
DomainAnalysis            Domain Analysis           Opportunity Engine
MemoryRecord              Memory System             User Model, Reasoning,
                                                    Hypothesis Engine
UserModel                 User Model Layer          Reasoning, Opportunity Engine
ActiveContext             Active Context            Reasoning, Opportunity Engine
ReasoningResult           Reasoning Engine          Hypothesis Engine,
                                                    Conclusion Confidence,
                                                    Opportunity Engine, Presentation
Hypothesis                Hypothesis Engine         Mental Model Engine
MentalModel               Mental Model Engine       Conclusion Confidence,
                                                    Opportunity Engine (V2)
ConclusionConfidence      Conclusion Confidence     Opportunity Engine, Presentation
AttentionRecommendation   Opportunity Engine        Policy + Safety
PolicyResult              Policy + Safety           Prioritization
PrioritizedItem           Prioritization            Presentation
OpportunityLifecycle      Lifecycle layer           Opportunity Portfolio, Presentation
DeliveredItem             Presentation              User surface, Feedback Layer
FeedbackSignal            Feedback Layer            Learning System
OutcomeRecord             External resolution       Learning System
MemoryWrite               Learning System           Memory System
ExecutionMetrics          Every layer               Orchestrator
DecisionTraceEntry        Every layer               Orchestrator, Explainability queries
```
