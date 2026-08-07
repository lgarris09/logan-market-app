# Logan Intelligence — Documentation Changelog v3.1 → v3.1.2
**Version:** 3.1.3
*New in v3.1.2.*
*Records every change from v3.1 to v3.1.2.*

---

## Overview of v3.1.2

v3.1.2 is a documentation and architecture update. No code was written or changed. This release:

1. **Adds the TriggerEvent framework** — 8 new files defining the first-class pipeline object, 6 domain registries with 46 registered codes, scoring rules, entity resolution, notification policy, and outcome evaluation
2. **Adds Culture and Personal Finance domains** — Logan's domain count grows from 5 to 7
3. **Locks multiple architectural rules** — LOCKED language replaces "permanent" and "non-negotiable" throughout; two new LOCKED decisions added (DECISION-015, DECISION-016)
4. **Expands the Opportunity Card** — 6 new fields, updated feedback buttons, 80-char headline
5. **Formalizes the community momentum rule** — community signals map to edge glow only; never node brightness, size, or proximity
6. **Updates data contracts** — TriggerEvent contract, CommunitySignal momentum_score rename, new card fields

---

## New Files in v3.1.2

| File | Description |
|------|-------------|
| `TRIGGER_EVENT_FRAMEWORK.md` | TriggerEvent architecture, contract, lifecycle, enforcement rules |
| `TRIGGER_REGISTRY_GLOBAL.md` | Master index of 46 trigger codes across 6 domains |
| `TRIGGER_REGISTRY_STOCKS.md` | 14 Stocks domain trigger codes |
| `TRIGGER_REGISTRY_SPORTS.md` | 7 Sports domain trigger codes |
| `TRIGGER_REGISTRY_PREDICTION_MARKETS.md` | 5 Prediction Markets domain trigger codes |
| `TRIGGER_REGISTRY_CRYPTO.md` | 6 Crypto domain trigger codes |
| `TRIGGER_REGISTRY_CULTURE.md` | 7 Culture domain trigger codes |
| `TRIGGER_REGISTRY_PERSONAL_FINANCE.md` | 7 Personal Finance domain trigger codes |
| `TRIGGER_SCORING_AND_CONFLICT_RULES.md` | Scoring rules, conflict pairs, multi-domain amplification |
| `ENTITY_RESOLUTION.md` | Cross-domain entity identity resolution |
| `NOTIFICATION_POLICY.md` | When Logan notifies; notification types; rate limits |
| `OUTCOME_EVALUATION.md` | How Logan evaluates whether an opportunity played out correctly |
| `DOCUMENTATION_REFERENCE_AUDIT.md` | Cross-reference check across all documents |
| `DOCUMENTATION_CHANGELOG_v3.1.2.md` | This file |

---

## Changes by File (v3.1 → v3.1.2)

### 00_MASTER_BRIEF.md
- Domain count updated from 5 to 7 (Culture and Personal Finance added)
- TriggerEvent framework listed as a new v3.1.2 addition
- 13 new TriggerEvent framework files listed in the new files section
- Version updated to 3.1.2

### 01_PRODUCT_SPECIFICATION.md
- Culture (music, entertainment, social trends) and Personal Finance (macro, housing, rates) added to domain list
- Culture domain use cases added: artist momentum, viral moment, chart breakout
- Personal Finance domain use cases added: Fed decision surprise, inflation shock, mortgage rate opportunity
- Version updated to 3.1.2

### 02_LOGAN_INTELLIGENCE_BRAIN.md
- TriggerEvent added as a first-class pipeline object (DECISION-015)
- Note added: Memory System, Feedback Layer, and Learning System are async infrastructure — NOT numbered pipeline layers
- TriggerEvent emitted by Domain Receptors and Detectors described in Layer 1–6 section
- Version updated to 3.1.2

### 03_MEMORY_ARCHITECTURE.md
- TriggerEvent outcome performance added as a distinct memory branch (alongside Opportunity, User, Market, and System memory)
- Version updated to 3.1.2

### 04_WORLD_MODEL.md
- `trigger_events` array added to WorldModel entity object
- Field definition: array of TriggerEvent objects associated with the entity, keyed by trigger_code
- Version updated to 3.1.2

### 05_SYSTEM_ARCHITECTURE.md
- TriggerEvent registry module added to the pipeline architecture diagram
- Domain receptor count updated to 7 (Culture and Personal Finance added)
- Version updated to 3.1.2

### 07_DATA_CONTRACTS.md
- TriggerEvent data contract added (new object: trigger_code, schema_version, entity_id, domain, fired_at, source_event_id, context, confidence_contribution, execution_metrics, decision_trace)
- CommunitySignal object: `trending_score` → `momentum_score` (field rename)
- OpportunityCard object: 6 new fields added (why_it_matters_to_me, supporting_evidence, contradicting_evidence, sources, action_window_opens, action_window_closes, correction_state, correction_note)
- FeedbackSignal object: `interaction_type` enum expanded (not_relevant, remind, acted added)
- Version updated to 3.1.2

### 08_BUILD_ORDER.md
- TriggerEvent registry step added between Domain Receptors and Normalization Layer
- Culture Domain Receptor added to Phase 1
- Personal Finance Domain Receptor added to Phase 1
- Version updated to 3.1.2

### 09_READ_AND_SUGGEST.md
- "permanent and non-negotiable" language replaced with LOCKED throughout
- Sports betting account linking explicitly deferred to V2 (removed from V1 scope)
- User Controls section added: opt-in controls for account linking and cross-domain data association
- Data deletion on account disconnect documented
- Reference to `27_SECURITY_PRIVACY_COMPLIANCE.md` added for full privacy model
- Version updated to 3.1.2

### 10_OPPORTUNITY_ENGINE.md
- `action_window_opens` and `action_window_closes` fields added to OpportunityLifecycle object
- `action_window_opens` and `action_window_closes` documented in ACTION WINDOW stage definition
- "Permanent record" → "Long-term record" in OUTCOME stage
- TriggerEvent outcome performance added to LEARNING stage
- Culture domain decay modifier added: 1.4× (events resolve faster)
- Personal Finance domain decay modifier added: 0.7× (macro signals evolve slowly)
- All `source_material/03_DATA_CONTRACTS.md` references updated to `07_DATA_CONTRACTS.md`
- Version updated to 3.1.2

### 11_UI_PHILOSOPHY.md
- Community momentum/personal relevance visual separation rule added to Opportunity Field section (LOCKED)
- Edge glow added to node properties list with LOCKED note
- Culture (coral) and Personal Finance (green) color tints added to Node Geometry table
- Card hierarchy updated: 80-char headline, why_it_matters_to_me first, supporting/contradicting evidence, action window timestamps, correction state
- Accessibility section expanded with color-independent status encoding and VoiceOver/TalkBack requirements
- Version updated to 3.1.2

### 12_VISUAL_LANGUAGE.md
- Domain Colors table expanded to 8 entries: Culture/Music (coral `#FB7185`) and Personal Finance (green `#34D399`) added
- Sports color corrected to amber `#F59E0B`; Crypto added as teal `#2DD4BF`
- Edge glow row added to Node Specs with LOCKED note (community momentum → edge glow only)
- Headline max 80 chars added to Type Rules
- Reduced-motion mode note added to Animation Tokens
- Version updated to 3.1.2

### 13_BRANDING.md
- Consumer app name TBD note strengthened: "do not use candidate names as if final in code or external materials"
- Garris Engineering note added: "Do not use in external materials until DECISION-013 is LOCKED"
- "Advisory, not prescriptive" voice characteristic added to voice guidelines
- Correction state tone added to tone table
- 80-char headline max noted in content guidelines
- Version updated to 3.1.2

### 14_ENGINEERING_STANDARDS.md
- TriggerEvent Registry section added (all codes must be registered; no unregistered code may enter pipeline; V1 = manual registry only)
- Folder structure expanded with 7 domain receptors (culture.py, personal_finance.py added) and `trigger_registry/` module
- Tech stack table now has Status column (PROVISIONAL)
- Community Intelligence visual rule added to Layer Rules as rule 8 (LOCKED)
- TriggerEvent registry unit tests requirement added
- Decision status labels standard added (LOCKED / PROVISIONAL / RESEARCH REQUIRED / DEFERRED)
- Vertical slice PR rule added to Git Workflow
- Version updated to 3.1.2

### 15_DECISIONS.md
- DECISION-015 added: TriggerEvent framework as first-class pipeline object (LOCKED)
- DECISION-016 added: Community momentum maps to edge glow only (LOCKED)
- Status label legend updated: "permanent" removed, LOCKED defined clearly as an irreversible decision
- `07_DATA_CONTRACTS.md` referenced consistently throughout
- Version updated to 3.1.2

### 16_ROADMAP.md
- Sprint 2A updated to include TriggerEvent in the path (STOCK_EARNINGS_BEAT example)
- Phase 1 updated to 7 domains (Culture and Personal Finance added)
- Phase 5 updated: action_window_opens/closes and NOTIFICATION_POLICY.md
- Phase 6 updated: all new card fields, new FeedbackSignal types
- Sprint 3 updated: opt-in controls for cross-domain data
- V2 section: ML trigger code discovery deferred
- Version updated to 3.1.2

### 17_CLAUDE_ENGINEERING_GUIDE.md
- LOCKED rules expanded from 9 to 12:
  - Rule 10: TriggerEvent registry enforcement (no unregistered codes)
  - Rule 11: Community momentum maps to edge glow only
  - Rule 12: why_it_matters_to_me is always the first rendered field
- TriggerEvent registry check added to ambiguity handling protocol
- Community momentum UI coding rule added (LOCKED)
- Reduced-motion fallback requirement added
- Common mistakes expanded: 3 new items (registering trigger without test, wiring momentum_score to node brightness, rendering why_it_matters_to_me below other fields)
- Sprint 2A check added to session start protocol
- Version updated to 3.1.2

### 18_SESSION_LOG.md
- New entry added at top for 2026-08-03 v3.1.2 session documenting all key changes, all new files, recovery context, and what's next
- All prior session history preserved
- Version updated to 3.1.2

### 19_FUTURE_IDEAS.md
- ML-Based Trigger Code Discovery idea added to Intelligence Features (V2 target)
- Trigger Code Performance Dashboard idea added to Product Features (V2 target)
- Counterfactual Engine note updated: extension point already reserved in V1 architecture
- 3D Orbital Field note updated: V1 uses 2D with depth illusion
- Version updated to 3.1.2

### 20_LOGAN_PRINCIPLES.md
- Principle 3 expanded: why_it_matters_to_me always first (before any other explanation field); supporting AND contradicting evidence both shown
- Principle 4 expanded: explicitly states contradicting evidence is shown when it exists, never hidden
- Principle 11 expanded: user deletion right explicitly stated
- **Principle 13 added (new):** "Community momentum is not personal relevance" — formalizes DECISION-016 at the principles level
- Version updated to 3.1.2

### 21_TRENDING_ENGAGEMENT.md
- LOCKED rule added at top: community momentum → edge glow only; does NOT map to node brightness, size, or proximity to center
- CommunitySignal field renamed `trending_score` → `momentum_score` throughout
- "Trending does not control node brightness or proximity" added to "What Trending Does NOT Do" section
- Note explaining why the field is named `momentum_score` (aligns with visual rule)
- Version updated to 3.1.2

### 22_OPPORTUNITY_CARD_SPEC.md
- Headline max changed: 120 → 80 characters. Enforced at Presentation layer.
- `WHY IT MATTERS TO ME` marked LOCKED: always the first rendered field; always personalized
- `SUPPORTING EVIDENCE` section added: bullet list of confirming evidence, shown from Emerging stage
- `CONTRADICTING EVIDENCE` section added: shown when present; never hidden when Logan has contrary evidence
- `ACTION WINDOW` section added: shows action_window_opens and action_window_closes timestamps
- `SOURCES` section added: compact data source list
- `CORRECTION STATE` section added: shown when correction_state ≠ "none"; values: updated, reversed
- Card structure diagram updated with all new sections
- Domain badge expanded to include Culture and Personal Finance
- Feedback action buttons expanded: `[NOT RELEVANT]` and `[REMIND ME]` added alongside existing buttons
- FeedbackSignal interaction_type values documented on each button
- Empty fields table updated to include Supporting Evidence column
- Version updated to 3.1.2

### 23_CURRENT_IMPLEMENTATION_STATE.md
- TriggerEvent registry row added to backend table (NOT BUILT)
- All 18 backend layers listed individually in the table
- Domain Receptors row updated: 7 domains noted (Culture, Personal Finance)
- Reduced-motion mode added to mobile table (NOT BUILT — Required)
- Sprint 2A target state expanded: STOCK_EARNINGS_BEAT TriggerEvent, World Model trigger_events population, all three Confidence Checkpoints documented
- Version updated to 3.1.2

### 24_API_SPECIFICATION.md
- `interaction_type` enum expanded: `not_relevant`, `remind`, `acted` added; `dismissed` renamed to `dismiss`; `acted_on` renamed to `acted`
- All `interaction_type` values documented with signal strength
- Opportunity detail response expanded: `why_it_matters_to_me`, `supporting_evidence`, `contradicting_evidence`, `sources`, `action_window_opens`, `action_window_closes`, `correction_state`, `correction_note`, `trigger_events` fields added
- `momentum_score` added to list response (renamed from `trending_score`)
- Domain filter values updated to include `culture` and `personal_finance`
- `trigger_event_fired` WebSocket message type added
- Version updated to 3.1.2

### 25_INTEGRATION_FEASIBILITY.md
- Culture domain section added: Spotify API, Apple Music/iTunes Charts, YouTube Data API, Billboard/Chartmetric (deferred)
- Personal Finance domain section added: Federal Reserve/FRED, Bureau of Labor Statistics (BLS), Bureau of Economic Analysis (BEA), Mortgage/Housing Data
- Sports betting account linking note updated: explicitly deferred to V2
- Integration Build Priority table expanded to include culture (Priority 7: Spotify, Priority 8: YouTube) and personal finance (Priority 9: FRED, Priority 10: BLS) providers
- 7-domain note added to overview
- Version updated to 3.1.2

### 26_GOLDEN_TEST_SCENARIOS.md
- Total scenarios expanded from 11 to 13
- Scenario 11 added: TriggerEvent Pipeline (Earnings Beat)
- Scenario 12 added: Correction State
- Scenario 13 (previously 11): full end-to-end updated to 7 domains, includes action_window_opens/closes, all new card fields, TriggerEvent presence, personalized why_it_matters_to_me
- Scenario 09: `trending_score` renamed to `momentum_score`
- Data contracts reference updated from `source_material/03_DATA_CONTRACTS.md` to `07_DATA_CONTRACTS.md`
- TriggerEvent emitted noted in Scenarios 01, 02, 03, 04
- `contradicting_evidence` check added to Scenario 05
- `why_it_matters_to_me` personalization check added to Scenario 06
- Version updated to 3.1.2

### 27_SECURITY_PRIVACY_COMPLIANCE.md
- User Controls section added:
  - Opt-in controls table (account linking, cross-domain association, behavioral learning, domain toggles)
  - Account disconnect data deletion procedure documented
  - Cross-domain data deletion behavior documented
- Data Classification table expanded: TriggerEvent performance data row; cross-domain data associations row added
- Principle 5 added to Core Privacy Principles: user controls are real
- Cross-domain association consent language added to Consent and Transparency section
- Compliance Status legal review item 4 added: cross-domain association disclosures
- Version updated to 3.1.2

### 28_PACKAGE_MANIFEST.md
- All 29 core document entries updated to v3.1.2 with change summaries
- TriggerEvent Framework section added: 12 new files
- DOCUMENTATION_REFERENCE_AUDIT.md added to Supporting Files
- Total count updated from 40 to 55
- TRIGGER_REGISTRY_GLOBAL.md added to regularly-updated files list
- Version updated to 3.1.2

---

*Logan Intelligence Documentation Changelog v3.1.2 — 2026-08-03*


---
## v3.1.2 Patch Summary

- Corrected 18-layer/support-system terminology.
- Removed “radius.md” (historical label) phantom reference.
- Added Slice 0 deterministic fixture and Slice 1 live receptor.
- Replaced minimal TriggerEvent object with stable event identity, revisions, domain impacts, temporal context, provenance, policy, notification, and correction fields.
- Added operational scoring/conflict/override rules.
- Relabeled implementation state UNVERIFIED.
- Expanded Opportunity Card, Trending UI, API, contracts, golden tests, integration verification, decisions, engineering guide, and branding status.
- Rebuilt reference audit after automated scan.
