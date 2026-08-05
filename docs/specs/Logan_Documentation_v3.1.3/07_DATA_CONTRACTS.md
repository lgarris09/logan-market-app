# Logan Intelligence System — Data Contracts
**Version:** 3.1.3

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

## TriggerEvent (new in v3.1.2)

```
Field           Type      Required   Constraints
────────────────────────────────────────────────────────────
schema_version  string    required   "1.0"
trigger_id      uuid      required   unique
trigger_code    string    required   registered code from TRIGGER_REGISTRY_*.md
domain          string    required
entity_id       string    required
entity_type     string    required
signal_ids      uuid[]    required   one or more source signal_ids
fired_at        ISO8601   required
payload         object    required   domain-specific (see registry for schema)
status          string    required   "active" | "expired" | "superseded" | "cancelled"
ttl_hours       integer   required   trigger-specific from registry; 0 = no expiry
superseded_by   uuid      optional   set if status = "superseded"
decision_trace  array     optional
```

See `TRIGGER_EVENT_FRAMEWORK.md` for the complete contract.
See “TRIGGER_REGISTRY_*.md” (historical label) for all registered trigger codes and their payloads.

---

## RawSignal

```
Field           Type      Required   Constraints
────────────────────────────────────────────────────────────
schema_version  string    required   "1.0"
signal_id       uuid      required   unique across all signals
domain          string    required   "stocks"|"sports"|"poly"|"social"|"crypto"|
                                     "culture"|"personal_finance"|"news"
                                     (news added in v3.1.3 — see ADR-037,
                                     TRIGGER_REGISTRY_NEWS.md; matches running
                                     code's logan_core/contracts/common.py)
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
entity_type     string    required   "ticker"|"team"|"contract"|"topic"|"person"|
                                     "artist"|"market_contract"
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
Stocks         price_change · volume_spike · news_event · earnings_signal
               analyst_change · technical_breakout · filing_event
               macro_event · rate_decision

Sports         odds_move · line_move · injury_report · weather_alert
               sharp_money · reverse_line_move · game_result

Poly           price_spike · sentiment_shift · volume_surge
               resolution_approaching · new_contract · resolution_event

Social         trend_emerging · velocity_spike · influencer_post
               viral_threshold · sentiment_flip · topic_spike

Crypto         price_change · volume_spike · on_chain_flow
               protocol_event · wallet_activity · exchange_flow

Culture        chart_move · album_release · tour_announcement
               viral_moment · genre_trend · artist_news · streaming_spike

Personal       rate_change · inflation_signal · employment_change
Finance        credit_condition · consumer_spending_signal · housing_signal

ODSE           hiring_signal · patent_filing · regulatory_filing
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
trigger_events  uuid[]      optional   TriggerEvent ids that fired for this event
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
entity_id     string    required   stable cross-domain identifier (see ENTITY_RESOLUTION.md)
entity_type   string    required   "ticker"|"team"|"contract"|"topic"|"person"|
                                   "artist"|"market_contract"
display_name  string    required
domain        string    required
attributes    object    optional   domain-specific properties
aliases       string[]  optional   alternate names (see ENTITY_RESOLUTION.md)
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
source_reliability_model_version  string  optional  default "deterministic-baseline"
                                     (added v3.1.3, reserved — see MODEL_CONTRACTS.md.
                                     Not populated by a trained model this release;
                                     source-reliability calibration is the approved
                                     first ML use case per ADR-032, not yet built)
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
**UI rule:** momentum_score maps to node edge glow only — never to node brightness or proximity.

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
trigger_event_ids   uuid[]    optional   TriggerEvents that contributed
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
trigger_adjustments object   optional   score adjustments from active TriggerEvents
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
user_id         string    required   added in v3.1.3 (ADR-033) — a required,
                                     non-empty, stable user identifier. Never
                                     an empty/anonymous value. The local/
                                     founder-only workflow uses a fixed local
                                     identifier (see implementation log). This
                                     is a schema/privacy-shape decision,
                                     independent of the ADR-006 database
                                     decision — see ML_PRIVACY_AND_DATA_SEPARATION.md
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
trigger_event_outcome
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
personal_relevance_narrative  string  required   given this user
                                     (renamed from personal_relevance in v3.1.3
                                     per ADR-021 — avoids colliding with the
                                     float-typed Dimensions.personal_relevance
                                     below; matches logan_core/contracts/reasoning.py,
                                     already correct in the running code)
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
confidence_model_version  string  optional  default "deterministic-baseline"
                                     (added v3.1.3, reserved — see MODEL_CONTRACTS.md.
                                     Confidence calibration is the likely second
                                     ML use case per ADR-032, not yet built)
calibrated_at           ISO8601 | null  optional   default null (added v3.1.3)
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
hit_quality_score     float       required   0.0-1.0 — objective. This and
                                   user_value_score are the two decision-making
                                   scores (ADR-029). Neither is ever collapsed
                                   into a single public score.
user_value_score      float       required   0.0-1.0 — personalized
dimensions            Dimensions  required
internal_rank_score   float       internal-only, NOT part of this public
                                   contract's returned surface — never exposed
                                   via any API response, DeliveredItem, or
                                   OpportunityCard; never used for recommend/
                                   suppress gating; never becomes Opportunity
                                   confidence; used solely for operational
                                   tie-breaking (e.g. notification queue
                                   ordering, see NOTIFICATION_POLICY.md).
                                   Renamed from priority_score in v3.1.3 per
                                   ADR-029 — priority_score is deprecated as a
                                   public/decision score. See MODEL_CONTRACTS.md
                                   for the formula status (RESEARCH REQUIRED for
                                   hit_quality_score's per-domain weights beyond
                                   Stocks — not invented here).
reasons               string[]    required   min one if recommend=true
why_not_explanation   string      required   always populated
competing_items       uuid[]      optional
trigger_event_ids     uuid[]      optional   TriggerEvents that influenced this
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
community_momentum      float   required   0.0-1.0 — raw value only, kept for
                                 observability/display. Per ADR-034, must never
                                 affect evidence, confidence, urgency, ranking,
                                 relevance, recommendation direction, brightness,
                                 size, or proximity; excluded from
                                 internal_rank_score below.
urgency                 float   required   0.0-1.0
confidence              float   required   0.0-1.0 from ConclusionConfidence
novelty                 float   required   0.0-1.0
opportunity_magnitude   float   required   0.0-1.0
risk                    float   required   0.0-1.0
actionability           float   required   0.0-1.0
connection_strength     float   required   0.0-1.0
```

**`internal_rank_score` formula (V1 — adjustable; amended in v3.1.3, formerly `priority_score`):**

Per ADR-029 (deprecating `priority_score` as a public score) and ADR-034 (community momentum must never influence ranking or recommendation direction, at any coefficient), this formula is amended from its v3.1.2 form in two ways: renamed, and the `community_momentum` term removed rather than redistributed — dropped, not silently replaced with a different weighting scheme.

```
internal_rank_score = (
  personal_relevance    * 0.25 +
  urgency               * 0.20 +
  confidence            * 0.15 +
  actionability         * 0.15 +
  global_importance     * 0.10 +
  opportunity_magnitude * 0.08 +
  novelty               * 0.04 +
  connection_strength   * 0.01
) * (1 - risk * 0.20)
```

**This formula is internal-only** (see `AttentionRecommendation.internal_rank_score` above) — it is never returned via any public API, never used for recommend/suppress gating, and never becomes Opportunity confidence. The weights above remain V1/adjustable and unvalidated against outcome data (no calibration loop exists yet — see `LEARNING_AND_FEEDBACK_SPECIFICATION.md`); they are not re-derived or invented in this revision, only the `community_momentum` term is removed per the approved directions.

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
geographic_restriction  boolean   required
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
notification_eligible boolean required   per NOTIFICATION_POLICY.md
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
headline                  string    required   max 80 chars
why_it_matters_to_me      string    required   personalized — always rendered first
what_happened             string    required
why_now                   string    required
supporting_evidence       Evidence[] optional  source-linked, verified
contradicting_evidence    Evidence[] optional  explicitly shown — never hidden
sources                   Source[]  optional
how_long_watching         string    required   e.g. "Logan has been watching this for 8 days"
action_window_opens       ISO8601   optional
action_window_closes      ISO8601   optional
current_exposure          object    optional   user's current exposure to this entity
related_exposure          array     optional   exposure in other domains
invalidation_conditions   string[]  optional
suggested_next_step       string    optional   MUST be neutral/non-directive (ADR-030).
                                     Acceptable categories: review evidence, monitor
                                     a condition, compare scenarios, add to
                                     watchlist, set an alert, review exposure, open
                                     the original source. Prohibited: buy, sell,
                                     place a bet, increase/reduce a position, act
                                     before a move, or any directive financial or
                                     wagering language. No generation logic exists
                                     yet — this is a contract constraint on any
                                     future implementation, not a description of
                                     running behavior.
external_execution_link   string    reserved, nullable, disabled and unrendered
                                     for V1 (ADR-030). Always null this release —
                                     no UI surface renders it, no API populates it.
                                     Field kept in the contract so downstream
                                     schema work isn't blocked; a dedicated
                                     execution-boundary ADR is required before
                                     this may ever be populated.
confidence_label          string    required
confidence_score          float     required   0.0-1.0
raising_factors           string[]  required
limiting_factors          string[]  optional
strengthening_signals     string[]  optional
invalidating_signals      string[]  optional
i_dont_know_yet           boolean   required
i_dont_know_reason        string    optional
lifecycle_stage           string    required
trending_indicator        object    optional   momentum signal — visually distinct
hit_quality_score         float     required
user_value_score          float     required
connected_items           uuid[]    optional
required_disclaimers      string[]  required   at least one disclaimer always present
decision_trace            array     optional   inspectable by user
correction_state          string    required   "original"|"updated"|"invalidated"
correction_note           string    optional   populated when correction_state != "original"
delivered_at              ISO8601   required
```

**Required disclaimer (always present):**
```
"Logan provides intelligence analysis only. This is not financial, investment, gambling,
or legal advice. Always verify information before making any financial decision.
Past signal accuracy does not guarantee future results."
```

---

## FeedbackSignal

```
Field               Type      Required   Constraints
────────────────────────────────────────────────────────────
schema_version      string    required   "1.0"
event_id            uuid      required
interaction_type    string    required   "view"|"click"|"dismiss"|"save"|"act"|
                                         "share"|"not_relevant"|"remind"|"already_acted"|
                                         "watch"
                                         ("watch" added in v3.1.3 — previously named
                                         only in prose ("Save / Watch") with no
                                         distinct contract value in either the repo
                                         or v3.1.2; see docs/DECISIONS.md)
inferred_intent     string    required   "interested"|"curious"|"dismissing"|"confused"|
                                         "accidental"|"researching"|"acting"|"unknown"
intent_confidence   float     required   0.0-1.0
duration_ms         integer   optional
raw_interaction     string    required
observed_at         ISO8601   required
```

**Rule:** inferred_intent never derived from interaction_type alone.
intent_confidence < 0.50 → inferred_intent = "unknown"
"not_relevant" signals the topic class is broadly uninteresting (broader than dismiss).
"already_acted" → positive engagement, suppresses further surfacing.

---

## OutcomeRecord

**Amended in v3.1.3 per ADR-036.** The shape below is superseded by the fuller structured Outcome Object defined in `OUTCOME_EVALUATION.md` (schema_version "2.0"), which is authoritative — this section is kept as the minimal typed-contract summary. The two must be read together; do not implement against this table alone.

```
Field             Type      Required   Constraints
────────────────────────────────────────────────────────────
schema_version      string    required   "2.0" (was "1.0" through v3.1.2)
outcome_id          uuid      required
opportunity_id      uuid      required   added v3.1.3
prediction_id       uuid      optional   added v3.1.3
user_id             string    required   added v3.1.3 (ADR-033) — never empty
event_id            uuid      required
entity_id           string    required   added v3.1.3
trigger_event_ids   uuid[]    optional   added v3.1.3
evidence_ids        uuid[]    optional   added v3.1.3
outcome_type        string    required   "signal_accuracy"|"source_reliability"|
                                         "user_value"|"market_resolution"|"event_resolution"|
                                         "trigger_accuracy"
prediction_or_claim_type  string  required   added v3.1.3 — see OUTCOME_EVALUATION.md
raw_predicted_value  object   required   added v3.1.3 — the full predicted claim,
                                         not just a direction/magnitude pair
created_at          ISO8601   required   added v3.1.3 — when the prediction was made
evaluation_horizon  object    required   added v3.1.3 — {value, unit}, see
                                         OUTCOME_EVALUATION.md's timeline table
resolvability       string    required   added v3.1.3 — "resolved"|
                                         "unresolved_pending"|
                                         "unresolvable_data_unavailable"|
                                         "unresolvable_ambiguous". NOT a bare
                                         win/loss field — see ADR-036.
observed_result     object    optional   added v3.1.3 — populated only when
                                         resolvability = "resolved"
invalidation_status  string   required   added v3.1.3 — "none"|
                                         "invalidated_before_resolution"|
                                         "invalidated_at_resolution"
invalidation_conditions  string[]  optional   added v3.1.3
verification_quality  object  required   added v3.1.3 — {level, method,
                                         confidence_in_verification}
source_contribution  array    optional   added v3.1.3 — per-trigger contribution
                                         records, not a win/loss tally
result              any       deprecated — superseded by observed_result
expected            any       deprecated — superseded by raw_predicted_value
accuracy            float     optional   0.0-1.0 — retained, now derived only
                                         from resolved+verified records
resolved_at         ISO8601   required
delay_window        string    required   "immediate"|"hours"|"days"|"months" —
                                         retained; evaluation_horizon supersedes
                                         it for new domain-specific timing
decision_trace_ref  string    optional   added v3.1.3
learning_applied    boolean   required   false until Learning System processes.
                                         As of v3.1.3, always false — Learning's
                                         process_outcome() is a non-functional
                                         stub, see LEARNING_AND_FEEDBACK_SPECIFICATION.md
trigger_code        string    optional   set when outcome_type = "trigger_accuracy"
```

---

## MemoryWrite

```
Field           Type      Required   Constraints
────────────────────────────────────────────────────────────
schema_version  string    required   "1.0"
write_id        uuid      required
write_type      string    required   "new_record"|"update_record"|"decay_update"|
                                     "trust_update"|"hypothesis_update"|"trigger_outcome"
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
TriggerEvent              Receptors, Hit Detection  World Model, Domain Analysis,
                                                    Opportunity Engine, Learning
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

---

*Logan Intelligence Data Contracts — v3.1.3 | 2026-08-04*
*v3.1.2 changes: TriggerEvent object added. Signal Type Registry expanded (culture, personal_finance). DeliveredItem updated: headline max 80 chars, supporting_evidence, contradicting_evidence, sources, action_window fields, correction_state, trending_indicator, external_execution_link. FeedbackSignal: added not_relevant, remind, already_acted interaction types. OutcomeRecord: added trigger_accuracy type. MemoryWrite: added trigger_outcome write type. Entity: added artist, market_contract types and aliases field.*
*v3.1.3 changes (see docs/DECISIONS.md ADR-021, 029, 030, 033, 036, 037 and ML review): domain enum +"news". MemoryRecord gains required user_id. ReasoningResult.personal_relevance renamed to personal_relevance_narrative. AttentionRecommendation.priority_score renamed to internal_rank_score, marked internal-only/never-public, community_momentum term removed from its formula. suggested_next_step constrained to neutral/non-directive language; external_execution_link reserved/nullable/disabled for V1. FeedbackSignal interaction_type gains "watch". EvidenceTrust and ConclusionConfidence gain reserved, "deterministic-baseline"-defaulted model-version metadata fields. OutcomeRecord redesigned as a structured evaluation object (schema_version "2.0") — see OUTCOME_EVALUATION.md.*


---
## v3.1.2 TriggerEvent Contract Expansion

Implementation must include typed `TriggerEvent`, `TriggerRevision`, `DomainImpact`, `TemporalContext`, `RecommendationContribution`, `NotificationDecision`, `ProvenanceEntry`, `EntityReference`, and `OutcomeEvaluation` models. `trigger_id` and `underlying_event_key` are stable; revisions are immutable snapshots linked by revision number. Python and TypeScript types should be generated from one versioned schema source with valid/invalid examples and contract tests. See `TRIGGER_EVENT_FRAMEWORK.md`.
