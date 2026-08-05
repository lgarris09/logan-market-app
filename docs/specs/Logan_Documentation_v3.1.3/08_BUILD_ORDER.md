# Logan Intelligence — Build Order
**Version:** 3.1.3
*Source: Architecture v1.3 FINAL (2026-07-31). Original: `source_material/08_BUILD_ORDER.md`.*

---

Read this before writing any code.

Architecture is frozen at v1.3. The build order is designed to produce a working,
testable system at each phase — not a half-finished system that only works end-to-end
after everything is built.

**Each phase ends with a gate. Do not advance to the next phase without passing the gate.**

---

## ⚡ Sprint 2A — Vertical Slice First (Start Here)

> **OVERRIDE:** Sprint 2A occurs before broad Phase 1–6 work. Do not build all domains, receptors, detectors, providers, storage systems, or integrations before the first end-to-end slice passes.

### Slice 0 — Deterministic Fixture

Use a fixed, version-controlled fixture so architecture and contract failures are isolated from provider failures.

```
Fixed NVDA-style event fixture
→ Normalization
→ Trigger Detection
→ TriggerEvent identity + deduplication
→ Domain impacts
→ Evidence Trust
→ World Model
→ User relevance/exposure
→ Active Context
→ Reasoning + conflict resolution
→ Conclusion Confidence
→ Opportunity Engine
→ Policy + Prioritization
→ API response
→ Opportunity Field node
→ Opportunity Card
→ Feedback capture
```

**Slice 0 gate:** typed contracts validate; stable IDs and trace IDs persist; one Opportunity renders; all card fields are populated; feedback is captured; no live provider is required.

### Slice 1 — One Verified Live Receptor

Replace only the fixture input with one verified market/news receptor. All downstream contracts and UI behavior remain unchanged. “No mocks at the system boundary” applies to Slice 1.

**Slice 1 gate:** provider provenance, staleness, retry behavior, deduplication, one live opportunity, and failure fallback are verified.

### Three Confidence Checkpoints

1. **Pipeline integrity:** Every object matches `07_DATA_CONTRACTS.md`.
2. **Score independence:** `hit_quality_score` and `user_value_score` remain distinct.
3. **Learning-loop closure:** Feedback reaches Feedback/Learning support systems and a proposed MemoryWrite is logged.

---

## Phase Overview

```
Phase 1    Foundation — Data Contracts + Signal Pipeline
Phase 2    Detection — Hit Detection System
Phase 3    Scoring — Domain Analysis Framework
Phase 4    Intelligence Core — Reasoning, Memory, Hypotheses
Phase 5    Delivery — Opportunity Engine + Lifecycle + Decay
Phase 6    Experience — Presentation + Feedback + Learning
```

---

## Phase 1 — Foundation

**Goal:** Every downstream layer has a clean, validated input.
The pipeline carries signals from receptors to EnrichedEvents.
Nothing is scored yet. Nothing is surfaced yet.

### What to Build

```
1.1  Data contracts
     · Implement all objects from 07_DATA_CONTRACTS.md as typed schemas
     · TriggerEvent schema implemented and validated
     · Every object has schema_version = "1.0"
     · Validation: object rejects on missing required fields
     · ExecutionMetrics attached to every layer output
     · decision_trace array on every layer output

1.2  Domain Receptors (stateless, V1 domains)
     · Stocks receptor
     · Sports receptor
     · Prediction Markets receptor
     · Social Trends receptor
     · Crypto receptor
     · Culture/Music receptor
     · Personal Finance receptor
     · Each emits RawSignal with correct source metadata
     · Each emits TriggerEvent on structured trigger code match

1.3  Normalization Layer
     · RawSignal → NormalizedSignal
     · Common schema for all downstream layers
     · Signal Type Registry enforced (all domains including culture/personal_finance)

1.4  World Model
     · Entity deduplication
     · Signal grouping per entity
     · TriggerEvent code matching
     · EnrichedEvent emission (with trigger_events array populated)
     · Sliding time window (configurable, default 30 minutes)
     · ENTITY_RESOLUTION.md canonical ID map used for entity_id assignment

1.5  System Orchestrator
     · Wires layers 1–4
     · No business logic
     · ExecutionMetrics aggregation
```

### Phase 1 Gate

```
✓  RawSignal → NormalizedSignal → EnrichedEvent pipeline runs end-to-end
✓  All object shapes validate against 07_DATA_CONTRACTS.md
✓  TriggerEvent emitted correctly on structured trigger code match
✓  schema_version present on all objects
✓  Entity deduplication works correctly for same entity across sources
✓  Canonical entity IDs used (per ENTITY_RESOLUTION.md)
✓  ExecutionMetrics emitted at every layer
✓  At least 11 simulated entities producing signals through the pipeline
```

---

## Phase 2 — Detection

**Goal:** The Hit Detection System fires correctly on known patterns.
All four detectors produce OpportunityEvidence.

### What to Build

```
2.1  Evidence Trust
     · Source credibility scoring
     · Corroboration scoring
     · Recency decay
     · Contradiction detection
     · Manipulation risk flag
     · EvidenceTrust object output

2.2  Community Intelligence
     · Runs in parallel with Evidence Trust
     · Volume, velocity, unique users
     · Lifecycle state tracking (building, peak, dispersing)
     · Bot/coordination risk detection
     · CommunitySignal object output
     · momentum_score mapped to edge glow only (not brightness)

2.3  Convergence Detector
     · CROSS_DOMAIN type (V1)
     · MULTI_SOURCE type (V1)
     · domain_count and source_count thresholds
     · OpportunityEvidence output
     · TriggerEvent emitted on registered convergence code match

2.4  Divergence Detector
     · PRICE_VS_SENTIMENT type (V1)
     · CONTRACT_VS_SOCIAL type (V1)
     · Domain-specific gap thresholds
     · historical_accuracy check
     · OpportunityEvidence output
     · TriggerEvent emitted on registered divergence code match

2.5  Pattern Engine
     · MOMENTUM_BREAK pattern (V1)
     · PRE_EVENT_SETUP pattern (V1)
     · Baseline comparison (rolling 30-day average)
     · pattern_confidence calculation
     · OpportunityEvidence output

2.6  ODSE
     · Hiring signal type (V1)
     · Patent signal type (V1)
     · GitHub activity signal type (V1)
     · Search anomaly signal type (V1)
     · Weak signal accumulation (14-day window)
     · reinforcement_count threshold (>= 3)
     · weighted_strength threshold (>= 0.60)
     · OpportunityEvidence output

2.7  Opportunity Evidence Assembler
     · Collects all detector outputs per entity
     · Multi-detector flag
     · Strength escalation (1.30×, 1.55×, 1.75× for 2, 3, 4 detectors)
     · Final OpportunityEvidence set per entity
```

### Phase 2 Gate

```
✓  Each detector fires correctly on simulated known setups
✓  No detector fires on flat/uninteresting simulated states
✓  All four detectors produce OpportunityEvidence with correct shape
✓  Multi-detector escalation applies correctly
✓  Assembler deduplicates correctly per entity per window
✓  ODSE 14-day window enforced correctly
✓  Divergence thresholds correct per domain
✓  Evidence Trust and Community Intelligence run in parallel
✓  TriggerEvent emitted correctly on detector trigger code match
```

---

## Phase 3 — Scoring

**Goal:** Every entity receives an objective hit_quality_score.
Hit Quality and User Value are separate scores from this point forward.

### What to Build

```
3.1  Domain Analysis Framework
     · All five dimensions implemented per domain
     · All 8 domains supported (incl. culture, personal_finance, and news)
     · TriggerEvent scoring adjustments applied (per TRIGGER_SCORING_AND_CONFLICT_RULES.md)
     · hit_quality_score calculation
     · DomainAnalysis object output

3.2  User Model (read-only in this phase)
     · User Model schema implemented
     · Loaded from Memory System (read only — Learning System writes)
     · user_interest_weight per domain per entity available
     · Active Context schema implemented

3.3  Hit Quality vs User Value calculation
     · hit_quality_score: objective, same for all users
     · user_value_score: derived from hit_quality × user factors
     · Both scores preserved separately — never collapsed here
```

### Phase 3 Gate

```
✓  hit_quality_score uses correct weights per domain
✓  Same entity scores same regardless of which user's pipeline
✓  hit_quality_score != user_value_score (separation confirmed — Checkpoint 2)
✓  DomainAnalysis object matches 07_DATA_CONTRACTS.md
✓  TriggerEvent score adjustments apply correctly
✓  User Model loads correctly from Memory System
✓  Active Context is session-scoped and does not persist
```

---

## Phase 4 — Intelligence Core

**Goal:** Logan reasons. Logan forms and tests hypotheses. Logan knows when it doesn't know.

### What to Build

```
4.1  Memory System
     · Operational History store (all data, not retained between reasoning cycles)
     · Logan Memory store (retained knowledge)
     · Read interface for all layers
     · Write interface restricted to Learning System only (enforced at this phase)

4.2  Reasoning Engine
     · Takes EnrichedEvent + OpportunityEvidence + DomainAnalysis + EvidenceTrust
     · What does this event mean in isolation?
     · What does it mean for this user?
     · ReasoningResult output

4.3  Hypothesis Engine
     · Generate hypotheses from evidence patterns
     · Store active hypotheses in Memory
     · Track what would confirm or disprove each hypothesis
     · Test incoming evidence against active hypotheses
     · HypothesisUpdate output

4.4  Mental Model Engine
     · Store confirmed world understanding
     · Track entity-level beliefs and their confidence
     · V1: track and store (does not yet influence Opportunity Engine)
     · MentalModel read access for Reasoning Engine

4.5  Conclusion Confidence
     · Post-reasoning confidence evaluation
     · Explicit "I don't know yet" when evidence insufficient
     · raised_by, limited_by, would_strengthen_if, would_weaken_if fields
     · ConclusionConfidence output
```

### Phase 4 Gate

```
✓  Reasoning Engine produces ReasoningResult for all entity types
✓  Hypothesis Engine generates and updates hypotheses
✓  Mental Model stores confirmed beliefs across cycles
✓  Conclusion Confidence produces explicit uncertainty explanation
✓  "I don't know yet" surfaces when confidence < threshold
✓  Memory System read/write access correctly restricted
✓  No layer except Learning System can write to Memory (enforced — Checkpoint 3)
```

---

## Phase 5 — Delivery Pipeline

**Goal:** Logan decides what to surface, tracks it over time, and keeps the field current.

### What to Build

```
5.1  Opportunity Engine (staged 7-step decision)
     Step 1   Is the entity in the user's watched domains?
     Step 2   Does hit_quality_score meet minimum threshold?
     Step 3   Does user_value_score meet the user's configured threshold?
     Step 4   Is the opportunity already known to the user (suppress repeats)?
     Step 5   Is there a timing or cooldown constraint?
     Step 6   Does Community Intelligence indicate dangerous crowd conditions?
     Step 7   Does Policy + Safety allow communication?
     → AttentionRecommendation output
     → "Why Not" explanation for every suppressed entity

5.2  Policy + Safety
     · Analysis vs advice language enforcement
     · Gambling controls
     · Jurisdiction and geographic restriction rules
     · Manipulation prevention
     · Risk limit checks
     · PolicyDecision output

5.3  Opportunity Lifecycle
     · All 8 stages implemented
     · Stage transitions with logged triggers
     · stage_velocity calculation
     · action_window_opens / action_window_closes timestamps populated
     · OpportunityLifecycle object

5.4  Opportunity Decay Engine
     · All four decay types (time, reaction, crowd, contradiction)
     · Domain-specific time decay rate modifiers
     · Stage regression logic
     · Retirement triggers
     · DecayState object

5.5  Opportunity Portfolio
     · All lifecycle stage counts
     · Entity lists per stage
     · Portfolio endpoint for frontend consumption

5.6  Prioritization + Attention State
     · Rank by internal_rank_score (renamed from priority_score, ADR-029; internal-only)
     · Cooldown enforcement
     · Fatigue detection
     · Visibility vs Interruption separation
     · Notification eligibility per NOTIFICATION_POLICY.md
     · Deduplicate across similar opportunities
```

### Phase 5 Gate

```
✓  Opportunity Engine correctly suppresses low user_value items
✓  "Why Not" explanation available for every suppressed entity
✓  All 8 lifecycle stages transition correctly
✓  action_window_opens and action_window_closes populated correctly
✓  Stage regression fires at correct confidence thresholds
✓  Decay Engine reduces confidence over time without new signals
✓  Retirement triggers correctly after conditions are met
✓  Opportunity Portfolio returns correct counts per stage
✓  Policy + Safety blocks disallowed communication types
✓  internal_rank_score calculation matches 07_DATA_CONTRACTS.md formula (renamed from priority_score, ADR-029)
✓  Notification eligibility respects NOTIFICATION_POLICY.md rules
```

---

## Phase 6 — Experience + Learning

**Goal:** Logan delivers explanations. Logan learns from outcomes and behavior.

### What to Build

```
6.1  Presentation + Delivery
     · All explanation fields per delivered item (per 06_LAYER_INTERFACE_SPECIFICATION.md)
     · headline max 80 chars enforced
     · why_it_matters_to_me rendered first (always)
     · supporting_evidence and contradicting_evidence both shown
     · sources section populated
     · action_window_opens / action_window_closes rendered
     · correction_state handling implemented
     · Hit Quality score visible
     · User Value score visible
     · Lifecycle stage visible
     · "I don't know yet" surfaced when evidence insufficient
     · Why Not available on request for any entity
     · Required disclaimer on every card

6.2  Feedback Layer
     · Capture explicit user feedback (all interaction_type values including not_relevant, remind, already_acted)
     · Infer implicit signals from behavior (reaction speed, engagement)
     · Interpret behavior — never literal translation
     · FeedbackSignal output

6.3  Personal Learning Loop
     · reaction_speed calibration
     · explanation_depth preference
     · evidence_threshold preference
     · macro_vs_micro preference
     · Updates User Model via Learning System only

6.4  Learning System (sole writer to Memory + User Model)
     · Receives FeedbackSignal + OutcomeRecord
     · Compares predicted vs actual outcomes
     · Updates detector hit rates
     · Updates pattern confidence scores
     · Updates TriggerEvent outcome performance records
     · Updates source credibility
     · Writes HypothesisUpdate to Memory
     · Updates User Model
     · All writes logged

6.5  Opportunity Field endpoint
     · Ranked list of AttentionRecommendation items
     · Lifecycle stage per item
     · Dual scores (Hit Quality + User Value) per item
     · Explanation fields per item
     · community_momentum → edge glow only
     · Opportunity Portfolio summary
```

### Phase 6 Gate

```
✓  All explanation fields populated per delivered item
✓  headline max 80 chars enforced
✓  why_it_matters_to_me is always the first rendered field
✓  contradicting_evidence shown when present (not hidden)
✓  Hit Quality and User Value both visible per item
✓  Personal Learning Loop updates User Model correctly over simulated sessions
✓  Learning System is sole writer to Memory and User Model (confirmed)
✓  Outcome records feed back into detector confidence scores
✓  TriggerEvent outcome records written correctly
✓  Opportunity Field endpoint returns ranked, explained, lifecycle-tracked items
✓  Why Not query returns explanation for any requested entity
✓  Full pipeline end-to-end test passes with 11+ simulated entities
```

---

## Always — Throughout All Phases

```
Every phase:
  · No layer except Learning System writes to Memory or User Model
  · Every object carries schema_version = "1.0"
  · Every layer emits ExecutionMetrics
  · Every layer appends to decision_trace
  · Hit Quality and User Value never collapsed before Opportunity Engine decision
  · All layer interfaces match 06_LAYER_INTERFACE_SPECIFICATION.md
  · All object shapes match 07_DATA_CONTRACTS.md
  · TriggerEvent codes come only from registered TRIGGER_REGISTRY_*.md entries
  · Community momentum never displayed as personal relevance
```

---

## What Is Not in V1

```
Historical analog matching (Phase 2 deferred)
Accumulation pattern detector (Phase 2 deferred)
Quiet-before-move detector (Phase 2 deferred)
ML-based pattern confidence scoring (Phase 3+)
ODSE shipping data, academic citations (Phase 2 deferred)
Automated outcome detection (Phase 5 deferred)
stage_velocity as signal input (Phase 5 deferred)
V2 Mental Model influence on Opportunity Engine (Phase 4 deferred)
Counterfactual Engine (Phase 3 extension point reserved)
Sports betting direct linking (Phase 3 — platform API availability dependent)
Banking account context (Phase 3 deferred)
ML-based trigger code discovery (deferred — manual registry only in V1)
```

---

*Logan Intelligence Build Order — v3.1.2 | 2026-08-03*
*v3.1.2 changes: Sprint 2A vertical slice section added at top (required before Phase 1 broad build). Three confidence checkpoints added. TriggerEvent added to Phase 1 and Phase 2 build steps. Culture/Music and Personal Finance receptors added to Phase 1.2. ENTITY_RESOLUTION.md referenced in Phase 1.4. NOTIFICATION_POLICY.md referenced in Phase 5.6. Phase 6.1 updated with full card field list. File reference updated to 07_DATA_CONTRACTS.md throughout.*
*v3.1.3 changes (ADR-037): Phase 3.1 domain count corrected from 7 to 8 — News restored alongside Culture and Personal Finance, matching ADR-020 and the running code's Domain literal.*
