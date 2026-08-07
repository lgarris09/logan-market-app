# Logan Intelligence — Roadmap
**Version:** 3.1.3
*Source: Architecture v1.3 FINAL (2026-07-31). Original: “source_material/16_ROADMAP.md” (historical label).*

---

## Current State

**Architecture:** v1.3 FINAL — frozen and fully documented
**Documentation:** v3.1.2 complete
**Code:** React Native starter app exists; backend implementation beginning

---

## Sprint 1 — Complete

**Goal:** Define Logan's intelligence architecture completely before writing production code.

Accomplished:
- Architecture v1.3 designed through iterative critique cycles and declared frozen
- Full specification package created — all layers, data contracts, build order
- Brain v2.0 written — philosophy, all 18 layers, Read & Suggest framework
- Documentation v3.1.2 package created (28 core files + 13 TriggerEvent framework files)
- React Native starter app scaffolded
- TriggerEvent framework designed and fully specified

---

## Sprint 2 — Backend Implementation (Current)

**Goal:** Prove the pipeline end-to-end with one complete vertical slice before expanding breadth.

**Read before starting:** `17_CLAUDE_ENGINEERING_GUIDE.md`, then `08_BUILD_ORDER.md`.

### Sprint 2A — Vertical Slice First (Required Before Phase 1 Broad Build)

Before implementing all 8 domains and all 18 layers in breadth, prove the pipeline works end-to-end with a single, constrained signal path:

```
One stock signal (e.g. NVIDIA earnings beat)
  → Domain Receptor fires, emits TriggerEvent (STOCK_EARNINGS_BEAT)
  → Normalization → World Model (single entity)
  → One detector (Convergence, CROSS_DOMAIN)
  → Domain Analysis (Stocks only)
  → Reasoning Engine → Opportunity Engine decision
  → AttentionRecommendation → /v1/opportunities endpoint
  → React Native: single node in Opportunity Field
  → Tap → Opportunity Card (all required fields populated)
  → Dismiss → FeedbackSignal captured
  → Learning System receives signal
```

**Sprint 2A gate:** Full end-to-end vertical slice confirmed working. All Checkpoint criteria from `08_BUILD_ORDER.md` passed:
1. Pipeline integrity — all objects match `07_DATA_CONTRACTS.md`
2. Score independence — `hit_quality_score` ≠ `user_value_score` for same event with different user models
3. Learning loop closure — FeedbackSignal → Learning System → MemoryWrite logged

### Why vertical slice first

- Validates that the architecture actually works end-to-end before building breadth
- Produces something demonstrable earlier
- Identifies integration surprises (API rate limits, schema mismatches, rendering performance) early
- Easier to debug when the system is narrow and observable

---

### Phase 1 — Foundation
- Data contracts as Pydantic/TypeScript schemas (including TriggerEvent)
- Domain Receptors (8 domains — including Culture, Personal Finance, and News)
- Normalization Layer (Signal Type Registry expanded for all domains)
- World Model (with TriggerEvent code matching)
- System Orchestrator

Gate: Pipeline carries signals from receptors to EnrichedEvents (with trigger_events populated). All objects validate.

### Phase 2 — Detection
- Evidence Trust
- Community Intelligence
- All 4 detectors (Convergence, Divergence, Pattern, ODSE) — with TriggerEvent emission
- Evidence Assembler

Gate: All detectors fire correctly on simulated setups. TriggerEvents emitted correctly.

### Phase 3 — Scoring
- Domain Analysis Framework (8 domains including Culture, Personal Finance, and News)
- User Model (read-only for now)
- Hit Quality vs. User Value separation
- TriggerEvent scoring adjustments applied

Gate: Same entity scores the same regardless of user pipeline. Scores are separate.

### Phase 4 — Intelligence Core
- Memory System (both stores)
- Reasoning Engine
- Hypothesis Engine
- Mental Model Engine
- Conclusion Confidence

Gate: Logan reasons, forms hypotheses, and says "I don't know yet" correctly.

### Phase 5 — Delivery Pipeline
- Opportunity Engine (7-step decision)
- Policy + Safety
- Opportunity Lifecycle (8 stages, with action_window_opens/closes)
- Decay Engine (4 decay types, all domain modifiers)
- Opportunity Portfolio
- Prioritization + Attention State (per NOTIFICATION_POLICY.md)

Gate: Full delivery pipeline produces ranked, explained, lifecycle-tracked opportunities.

### Phase 6 — Experience + Learning
- Presentation (all card fields — why_it_matters_to_me first, supporting/contradicting evidence, sources, action window, correction state)
- Feedback Layer (all interaction types including not_relevant, remind, already_acted)
- Personal Learning Loop
- Learning System (sole writer to Memory)
- Opportunity Field API endpoint

Gate: Full end-to-end pipeline passes with 11+ simulated entities. All phase gate criteria from `08_BUILD_ORDER.md` passed.

---

## Sprint 3 — Read & Suggest

**Goal:** Account linking and portfolio intelligence.

- Plaid integration (brokerage account linking)
- Kalshi / Polymarket direct API integration
- Portfolio concentration analysis
- Cross-domain conflict detection
- Behavioral pattern detection (V1)
- Read & Suggest mobile screens
- User opt-in controls for cross-domain data use

Gate: User can link a brokerage account and see personalized portfolio intelligence in the app.

---

## Beta

**Goal:** Working app with all 8 core domains, Read & Suggest, and the Opportunity Field experience.

- All 8 domain receptors stable and pulling live data
- Read & Suggest fully functional
- Opportunity Field mobile UI complete (Skia rendering)
- Opportunity Portfolio screen
- User onboarding flow
- Settings (account linking, preferences, opt-in controls)
- Performance targets met (see `14_ENGINEERING_STANDARDS.md`)
- Closed beta: 10–50 users

---

## V1 Launch

**Goal:** Public release.

- All Beta items stable
- App Store / Google Play submission
- Consumer app name decided and registered (DECISION-012)
- Legal entity established (DECISION-013)
- Privacy policy, terms of service
- Marketing site
- Basic analytics (outcome tracking, user engagement)
- Crash reporting and monitoring
- Support contact

---

## V2 — Depth and Learning

- Mental Model Engine V2 (richer representation, influences Opportunity Engine)
- Automated outcome detection (price targets hit, game results, contract resolution)
- Sports betting account linking (DraftKings, FanDuel — platform API dependent)
- Advanced behavioral learning (time-of-day patterns, sentiment-based decision quality)
- Stage velocity as signal input to Opportunity Engine
- Counterfactual Engine ("what would have happened if...")
- Portfolio analytics (Logan's historical accuracy visible to user)
- 3D orbital Opportunity Field view
- ML-based trigger code discovery (manual registry only in V1)

---

## V3 — Platform Expansion

- Projects module (career, real estate, business decisions)
- Intelligence Feed (browsable context, not just Opportunity Field)
- Chat with Logan's reasoning layer
- Enterprise version (company-licensed, shared intelligence, team memory)
- Web/desktop companion app
- API for third-party integrations

---

## Long-Term Vision

- Logan as a personal reasoning engine for all major life decisions
- Hardware: ambient intelligence device (always-on, ambient awareness)
- Logan learns across users (aggregate, anonymized patterns) to improve domain intelligence
- The intelligence operating system for how people make decisions

---

*Logan Intelligence Roadmap — v3.1.2 | 2026-08-03*
*v3.1.2 changes: Sprint 2A vertical slice updated to include TriggerEvent in the path. Phase 1 updated to 7 domains (Culture + Personal Finance added). Phase 3 updated to 7 domains + TriggerEvent scoring. Phase 5 updated with action_window_opens/closes and NOTIFICATION_POLICY.md. Phase 6 updated with all card fields and new FeedbackSignal types. Sprint 3 updated with opt-in controls. Beta updated to 7 domains. V1 Launch: consumer name and legal entity decision requirements added. V2: ML trigger discovery deferred noted.*
*v3.1.3 changes (ADR-037): Domain counts corrected from 7 to 8 throughout (Sprint 2A intro, Phase 1, Phase 3, Beta) — News restored alongside Culture and Personal Finance, matching ADR-020 and the running code's Domain literal.*
