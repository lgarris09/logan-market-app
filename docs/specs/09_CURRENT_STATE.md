# Logan Intelligence System — Current State

Filled in 2026-08-01 as part of reconciling the v1.3 architecture package against the actual codebase.
This describes what exists **today**, against v1.0 (`docs/specs/LOGAN_ARCHITECTURE_v1.0.md` and friends),
not what v1.3 specifies. See `docs/DECISIONS.md` and today's session notes for the full gap analysis
between the two.

---

## Tech Stack

```
Language:           Python 3.13 (logan_core, backend), TypeScript (mobile)
Framework:          FastAPI (backend/app), Expo Router + React Native (mobile)
Database:           None. All stores (Operational History, Logan Memory, Attention State) are
                     in-memory, process-lifetime only. Historical prototype uses SQLite
                     (backend/data/logan_memory.db) but logan_core itself has no database — see ADR-006
                     (open decision).
Message queue:      None.
Frontend:           React Native / Expo (SDK 54), expo-router for navigation.
Deployment:         Local dev only. Expo tunnel for informal sharing. No hosting, no CI/CD.
Package manager:    pip (backend/logan_core, no lockfile — requirements.txt only), npm (mobile).
Test framework:     pytest (logan_core, 28 tests). No mobile test framework established yet.
```

---

## Repository Structure

```
logan_market_app_starter/
├── backend/app/          FastAPI process — historical prototype + logan_core demo bridge
│   ├── main.py             All routes
│   ├── memory_engine.py    Historical prototype: SQLite memory engine
│   ├── memory_models.py    Historical prototype: memory Pydantic models
│   ├── models.py           Historical prototype: Opportunity/briefing/ask models
│   ├── data.py             Historical prototype: demo seed data
│   ├── logan_demo.py       Bridge: single Tesla scenario through logan_core
│   ├── logan_feed.py       Bridge: 11 simulated entities through one shared Orchestrator
│   └── entity_registry.py  Bridge: canonical entity metadata (display name/category/ticker)
├── logan_core/            The v1.0 reasoning pipeline, one folder per layer (see below)
├── mobile/app/            Expo Router screens
│   ├── index.tsx            Opportunity Field (current home screen)
│   ├── classic.tsx           Pre-Field card-list briefing (preserved)
│   ├── ask.tsx, memory.tsx, demo.tsx   Preserved, unchanged
│   └── _layout.tsx
├── mobile/components/     EntitySymbol, OpportunityNode, LoganCore, OpportunityField,
│                          OpportunityCard, LoganOpportunityCard
├── mobile/lib/             symbolResolver.ts
├── mobile/types/          loganDemo.ts, loganFeed.ts
└── docs/                  PRODUCT.md, ARCHITECTURE.md, STANDARDS.md, ROADMAP.md, DECISIONS.md,
                           specs/ (both the v1.0 spec and this v1.3 package now live here — see
                           "Known Conflicts" below), sessions/
```

---

## What Is Built and Working

```
Component                              Status     File / Module
────────────────────────────────────────────────────────────────────────────────────
Domain Receptors (simulated, 6 domains) Working    logan_core/receptors/simulated.py
Normalization                          Working    logan_core/normalization/normalize.py
World Model (entity graph, dedup,      Working    logan_core/world_model/model.py
  sliding-window dedup, ripple map)
Evidence Trust                         Working    logan_core/evidence_trust/trust.py
Community Intelligence                 Working    logan_core/community_intelligence/community.py
Memory System (Logan Memory only)      Working    logan_core/memory/store.py
Operational History                    Working    logan_core/orchestrator/history.py (Orchestrator-owned)
User Model (seed + rebuild)            Working    logan_core/user_model/model.py
Active Context                         Working    logan_core/active_context/context.py
Reasoning Engine                       Working    logan_core/reasoning/engine.py
Mental Model Engine (V1 pass-through)  Working    logan_core/mental_model/engine.py
Conclusion Confidence                  Working    logan_core/conclusion_confidence/engine.py
Opportunity Engine (single             Working    logan_core/opportunity/engine.py
  priority_score, no Hit Quality/
  User Value split)
Policy & Safety (advice boundary,      Working    logan_core/policy/engine.py
  betting objectivity)
Prioritization & Attention State       Working    logan_core/prioritization/engine.py
Presentation (DeliveredItem)           Working    logan_core/presentation/engine.py
Feedback Layer                         Working    logan_core/feedback/engine.py
Learning System (immediate path only,  Working    logan_core/learning/engine.py
  no delayed OutcomeRecord scheduler)
System Orchestrator                    Working    logan_core/orchestrator/pipeline.py
Backend bridge (demo endpoints)        Working    backend/app/logan_demo.py, logan_feed.py
Canonical entity registry              Working    backend/app/entity_registry.py
Opportunity Field UI (radial layout,   Working,   mobile/components/OpportunityField.tsx +
  symbol resolver, ripple lines,       not yet    OpportunityNode/EntitySymbol/LoganCore,
  Logan core, entrance animation)      verified   mobile/lib/symbolResolver.ts
                                        on-device
Classic briefing / Ask / Memory /      Working    mobile/app/classic.tsx, ask.tsx, memory.tsx, demo.tsx
  Tesla-only demo (preserved)
```

---

## What Is Partially Built

```
Component                    What Works                    What's Missing
────────────────────────────────────────────────────────────────────────────────────
Mental Model Engine          Stores/tracks hypotheses,      No separate Hypothesis Engine (generate/
                              confidence trend               test with required/confirming/disproving
                                                              evidence) — v1.0 conflates the two
Learning System               Immediate FeedbackSignal path  No OutcomeRecord delayed-resolution
                                                              scheduler
Conclusion Confidence         Single confidence_score +      No confidence_label, no raising_factors/
                              4-tier classification           strengthening/invalidating fields, no
                                                              explicit "i_dont_know_yet"
Opportunity Field UI          Full component pipeline built  Not yet seen on a physical device — visual
                                                              quality, spacing, motion feel unverified
```

---

## What Is Not Built Yet

```
Everything net-new in the v1.3 package:
  - Hit Detection System (Convergence, Divergence, Pattern, ODSE detectors) — Layer 4c
  - OpportunityEvidence object and the Opportunity Evidence Assembler
  - Domain Analysis Framework (5-dimension scoring: fundamentals/momentum/community/
    catalysts/structural) — Layer 5
  - hit_quality_score / user_value_score separation anywhere in the pipeline
  - Hypothesis Engine (as a layer distinct from Mental Model Engine)
  - Opportunity Lifecycle (8-stage state machine, stage_velocity)
  - Opportunity Decay Engine (time/reaction/crowd/contradiction decay)
  - Opportunity Portfolio (endpoint or UI)
  - Personal Learning Loop fields on UserModel (reaction_speed, explanation_preference,
    evidence_threshold, macro_micro_preference)
  - Why Not explanation
  - "I don't know yet" / explicit uncertainty surfacing
  - Real (non-simulated) receptors for any domain
  - Authentication, production hosting, real database
```

---

## Data Contract Alignment

Checked against this v1.3 package's `03_DATA_CONTRACTS.md`, not the v1.0 spec (which the current code
does match).

```
Object                  Aligned?    Notes
─────────────────────────────────────────────────────────────────────────────────
RawSignal               Partial     Current domain enum has 6 values (adds "news", drops
                                     nothing); v1.3 lists 5 and omits "news" entirely.
NormalizedSignal        Partial     Same domain mismatch. Signal Type Registry only partially
                                     overlaps (v1.3 adds filing_event, on_chain_flow,
                                     protocol_event, wallet_activity, plus an entire ODSE
                                     signal-type set not present in current registry).
EnrichedEvent           Yes         Shape matches.
EvidenceTrust           Yes         Shape and formula match exactly.
CommunitySignal         Yes         Shape matches.
OpportunityEvidence     No          Object does not exist in current implementation — Hit
                                     Detection System is entirely unbuilt.
DomainAnalysis          No          Object does not exist — Domain Analysis Framework is
                                     entirely unbuilt. Current scoring folds everything
                                     directly into AttentionRecommendation.dimensions instead.
UserModel                No         Missing reaction_speed, explanation_preference,
                                     evidence_threshold, macro_micro_preference entirely.
ReasoningResult          Partial    Current field is personal_relevance_narrative (renamed
                                     from personal_relevance per ADR-021, to avoid colliding
                                     with the float-typed Dimensions field of the same name).
                                     v1.3 reverts to personal_relevance as a string field name,
                                     recreating that exact collision risk against Dimensions.
ConclusionConfidence     No         Missing confidence_label, raising_factors,
                                     strengthening_signals, invalidating_signals,
                                     i_dont_know_yet, i_dont_know_reason entirely.
AttentionRecommendation  No         Missing hit_quality_score, user_value_score,
                                     why_not_explanation entirely.
OpportunityLifecycle     No         Object and layer do not exist.
DecayState               No         Object and layer do not exist.
FeedbackSignal           Yes        Shape matches.
```

---

## Known Conflicts with v1.3 Spec

```
- Domain list: current has 6 domains (stocks, sports, poly, social, news, crypto — ADR-020,
  ADR-024). v1.3 lists 5 and omits "news" entirely. The Federal Reserve entity in the current
  11-entity demo set lives in the "news" domain and would be orphaned by a literal v1.3 adoption.

- Scoring architecture: v1.3's Hit Quality / User Value separation is not additive — it changes
  where personalization enters the pipeline. Current Opportunity Engine computes a single
  priority_score with personal_relevance already mixed in via Dimensions. Adopting v1.3 as
  written requires moving objective scoring into a new Domain Analysis Framework layer that
  currently doesn't exist, and reworking what Reasoning/Opportunity Engine each own.

- docs/specs/ now contains two co-existing "locked" architecture packages: the v1.0 spec
  (LOGAN_ARCHITECTURE_v1.0.md, LOGAN_DATA_CONTRACTS_v1.0.md, LOGAN_IMPLEMENTATION_PLAN.md,
  matching current code) and this v1.3 package (00_MASTER_BRIEF.md through 11_UI_SYSTEM.md).
  Both directories claim canonical status. Needs an explicit resolution before docs/specs/ can
  be trusted as unambiguous source of truth again — flagged for the user, not resolved here.

- Mental Model Engine vs Hypothesis Engine: current code has one layer (Mental Model Engine)
  doing what v1.3 splits into two (Hypothesis Engine generates/tests; Mental Model Engine stores
  confirmed beliefs). Not a blocking conflict, but a real refactor if adopted.
```

---

## Simulated Entities

```
Current entity count:   11
Domains covered:        stocks (5), crypto (1), news (1), sports (1), social (2), poly (1)

Entities:
  TSLA (Tesla), NVDA (NVIDIA), AAPL (Apple), MARKETS (Markets), OIL (Oil) — stocks
  BTC (Bitcoin) — crypto
  FED (Federal Reserve) — news
  NFL — sports
  MUSIC, AI_SECTOR (AI) — social
  POLY (Polymarket) — poly

Connected cluster (via World Model DOWNSTREAM_EFFECTS): TSLA ↔ NVDA ↔ AI_SECTOR ↔ MARKETS ↔ FED ↔ BTC.
Standalone (no connections): AAPL, OIL, NFL, MUSIC, POLY.
```

---

## API Endpoints

```
Endpoint                Method    Status     Notes
─────────────────────────────────────────────────────────────────────────────
/health                 GET       Working    Historical prototype
/v1/briefing            GET       Working    Historical prototype, demo data
/v1/opportunities       GET       Working    Historical prototype, demo data
/v1/memories            GET/POST  Working    Historical prototype, SQLite-backed
/v1/context/{category}  GET       Working    Historical prototype
/v1/ask                 POST      Working    Historical prototype, stub (no LLM)
/v1/demo/tesla          GET       Working    logan_core bridge, single Tesla scenario
/v1/demo/feed           GET       Working    logan_core bridge, all 11 entities, ranked + connected
/api/opportunities      —         Not built  v1.3-shaped endpoint does not exist
/api/portfolio          —         Not built  Opportunity Portfolio does not exist
/api/opportunities/{id}/why-not  — Not built  Why Not explanation does not exist
```

---

## Test Coverage

```
Layer                                Test file                          Coverage
─────────────────────────────────────────────────────────────────────────────────
Contracts (validation rules)         tests/test_contracts.py            Pydantic validators only
Evidence Trust (formula, recency,    tests/test_evidence_trust.py       Core formula + edge cases
  unknown source)
World Model (dedup, ripple)          tests/test_world_model.py          Dedup window, downstream map
Opportunity Engine (priority_score,  tests/test_opportunity.py          Formula, bounds, thresholds
  recommend threshold)
Policy (advice boundary, betting     tests/test_policy.py               All domains, bot-risk suppression
  objectivity, bot-risk suppression)
Full pipeline (Tesla scenario,       tests/test_pipeline_tesla.py       End-to-end, 19-layer trace
  end-to-end)
Feedback → Learning (Memory Inbox    tests/test_feedback_learning.py    Confirm/reject, permission check
  confirm/reject, write permission)

Total: 28 tests, all passing. No tests exist for anything in "What Is Not Built Yet" above,
since none of it exists. No mobile tests exist.
```

---

## Questions for Architecture Review

```
Q: v1.3 drops the "news" domain that ADR-020 added and the current Federal Reserve entity
   depends on. Is that intentional (folding news into another domain) or an oversight?

A: [unanswered]

Q: v1.3 gives two different formulas for user_value_score in two different documents
   (05_DOMAIN_FRAMEWORK.md vs 02_LAYER_INTERFACES.md) — which is authoritative?

A: [unanswered]

Q: Does v1.3's priority_score (inherited verbatim from v1.0's Dimensions/AttentionRecommendation)
   still exist alongside the new hit_quality_score/user_value_score, or is it superseded? The
   package doesn't say.

A: [unanswered]

Q: Is ODSE a Layer 1 receptor/domain (as its Signal Type Registry entry implies) or a Layer 4c
   detector consuming other domains' signals (as its architectural placement implies)? These
   are structurally different things.

A: [unanswered]

Q: Should docs/specs/ hold both the v1.0 and v1.3 packages long-term (e.g. in versioned
   subdirectories), or should v1.3 supersede v1.0 in place once adopted?

A: [unanswered]
```

---

## Session Notes

```
2026-08-01 — v1.3 architecture package received and reconciled against current v1.0 implementation
  and live Opportunity Field UI. Full gap analysis and conflict list produced (see docs/DECISIONS.md
  and today's session notes). No implementation changes made — per explicit instruction, today's
  on-device Opportunity Field evaluation takes priority over any v1.3 adoption work. This file filled
  in as part of that reconciliation, since the v1.3 package's own process requires it before any
  implementation begins.
```
