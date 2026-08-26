# Decisions Log (ADR)

This file is the single source of truth for *why* Logan is built the way it is. It is a lightweight
Architecture Decision Record (ADR) log: append new entries, never rewrite history. If a decision is
reversed, add a new entry that supersedes the old one — don't delete the old one.

## How to add a decision

Copy the template below, give it the next sequential ID, and fill it in before (not after) the related
code lands. Every non-obvious technical, product, or process choice belongs here — not just big ones.

```
## ADR-XXX: <short title>
- Date: YYYY-MM-DD
- Status: Proposed | Accepted | Superseded by ADR-YYY
- Context: what problem or question forced this decision
- Decision: what we chose
- Consequences: what this makes easier, harder, or forecloses
```

---

## ADR-001: Free, growth-first MVP before monetization
- Date: 2026-07-29
- Status: Accepted
- Context: Logan needs a business model. The first job is proving people find the memory/personalization
  loop valuable enough to use regularly — not maximizing early revenue.
- Decision: Phase 1 ships free to end users. Monetization (premium tier, affiliate revenue, or other
  streams) is deferred to Phase 2+, once retention and usage data validate the product.
- Consequences: Architecture and infra choices in Phase 1 should optimize for iteration speed and
  learning, not for revenue infrastructure (billing, entitlements, paywalls). Revisit before Phase 2.
  See [PRODUCT.md](PRODUCT.md).

## ADR-002: Logan personalizes and contextualizes — it does not give directive advice (Phase 1)
- Date: 2026-07-29
- Status: Accepted — **open question flagged for future revisit**
- Context: Logan surfaces stock, sports-betting, and prediction-market (Polymarket) content. Directive
  recommendations ("buy Tesla now") carry financial-advice and gambling-adjacent regulatory exposure
  that is not yet scoped or resourced.
- Decision: Phase 1 Logan explains relevance and surfaces context ("Tesla announced an AI partnership;
  because you follow AI stocks and hold Nvidia, this may be relevant") but never issues a directive
  recommendation or call to action on a specific position or bet.
- Consequences: This is a hard product boundary, not a suggestion — new features must not cross it
  without a new ADR. Before Logan ever moves toward directive recommendations, we need a dedicated
  decision covering: user expectations, applicable regulatory obligations, required disclosures,
  confidence/uncertainty communication, and the analysis-vs-advice line. Until that ADR exists, treat
  this boundary as load-bearing. See [PRODUCT.md](PRODUCT.md) and [STANDARDS.md](STANDARDS.md#security-practices).

## ADR-003: Build process for a small team, even while solo
- Date: 2026-07-29
- Status: Accepted
- Context: Logan is currently built by one engineer working closely with AI assistants, but the explicit
  goal is scaling to a small team (2-5 engineers) without a painful process retrofit.
- Decision: Adopt team-grade process now — PR-based changes (even solo, self-reviewed), branch
  protection on `main`, Conventional Commits, and documented standards — rather than "move fast, formalize
  later."
- Consequences: Slightly more ceremony per change today, in exchange for onboarding future engineers
  without a process rewrite. See [STANDARDS.md](STANDARDS.md#git-workflow).

## ADR-004: Trunk-based development with Conventional Commits
- Date: 2026-07-29
- Status: Accepted
- Context: Needed a branching model that is simple enough for a solo engineer today and scales cleanly
  to a small team, without GitFlow's release-train ceremony that Logan doesn't need pre-launch.
- Decision: Trunk-based development — `main` is always deployable, work happens on short-lived
  `type/short-description` branches merged via squash-merge PRs. Commit and PR titles follow
  Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`).
- Consequences: Simple mental model, clean history, easy changelog generation later. Requires discipline
  to keep branches short-lived and `main` releasable at all times. See [STANDARDS.md](STANDARDS.md#git-workflow).

## ADR-005: Pragmatic testing bar during MVP/pre-launch
- Date: 2026-07-29
- Status: Accepted
- Context: Product direction is still shifting quickly pre-launch. A strict coverage gate on all code
  (including UI still being explored) would slow iteration without proportional risk reduction; no
  testing at all risks silent breakage in the memory engine, which is Logan's core asset.
- Decision: Tests are required for core business logic (memory classification, scoring, reinforcement,
  branch assignment) and API contracts. UI and exploratory code are tested pragmatically, not gated on
  coverage percentage.
- Consequences: Fast iteration on UI/product direction; the riskiest, hardest-to-debug logic (the memory
  engine) is protected. Revisit this bar — likely tightening it — before public launch. See
  [STANDARDS.md](STANDARDS.md#testing-expectations).

## ADR-006: Database and hosting — open decision
- Date: 2026-07-29
- Status: Proposed (open)
- Context: Logan currently runs on SQLite with local file storage and no deployed hosting target. This
  is adequate for prototyping but not for multi-user, always-on, or team-shared use.
- Decision: Not yet made. Continue with SQLite + local dev for Phase 1. A hosting provider and
  production-grade database (e.g. managed Postgres) must be chosen before Phase 2 (multi-user or public
  launch), via a follow-up ADR.
- Consequences: Do not build features that assume a specific cloud provider or that would be expensive
  to port off SQLite (e.g. SQLite-specific SQL, single-file assumptions in the memory engine) until this
  is resolved. See [ARCHITECTURE.md](ARCHITECTURE.md#open-questions).

## ADR-007: Industry-standard formatting, linting, and type-checking defaults
- Date: 2026-07-29
- Status: Accepted
- Context: No existing tooling preferences; needed a baseline that's familiar to any engineer joining
  later rather than a bespoke setup.
- Decision: Python (backend) — Black (formatting), Ruff (linting), type hints encouraged and checked
  with mypy. TypeScript (mobile) — strict mode in `tsconfig.json`, ESLint + Prettier.
- Consequences: Low-friction onboarding for future engineers; consistent style without bikeshedding.
  Adjustable later via a new ADR if a specific tool proves wrong for the project. See
  [STANDARDS.md](STANDARDS.md#coding-standards).

## ADR-008: AI collaboration model — propose, human approves everything
- Date: 2026-07-29
- Status: Accepted
- Context: AI assistants (Claude Code and others) are a core part of how Logan is built. Need explicit
  rules for what they may do autonomously versus what requires human sign-off, especially given Logan
  handles user financial/behavioral data and touches regulated-adjacent domains.
- Decision: AI assistants may research, plan, and draft code changes freely, but every commit, database
  migration, dependency change, and push requires explicit human confirmation before it happens. No
  autonomous merges to `main`.
- Consequences: Slower per-change velocity in exchange for a human checkpoint on everything that touches
  the codebase or data — appropriate given the product's current maturity and data sensitivity. Revisit
  as trust and test coverage grow. See [CLAUDE.md](../CLAUDE.md).

## ADR-009: FOMO/urgency design pattern — flagged as open regulatory/ethical risk
- Date: 2026-07-30
- Status: Superseded by [ADR-013](#adr-013-fomourgency-risk-tightened--betting-and-prediction-markets-must-stay-objective)
- Context: The product vision uses urgency/excitement ("FOMO as motivation") as a deliberate emotional
  driver, aimed at an 18-35 audience, across content that includes sports betting and prediction markets
  — domains where marketing urgency to young adults draws specific regulatory and ethical scrutiny
  (e.g. gambling-advertising rules, financial-promotion rules), independent of whether the tone is
  "excitement" rather than "fear."
- Decision: Proceed with FOMO-as-designed-emotional-driver as described in [PRODUCT.md](PRODUCT.md), but
  treat it explicitly as a tracked risk rather than a settled non-issue. A compliance/legal review of
  this pattern — specifically evaluating urgency messaging against gambling-marketing and
  financial-promotion regulations in target jurisdictions — is a required gate before Phase 2 (any use
  beyond the founder's own local/trusted use).
- Consequences: Phase 1 design is not constrained by this today. The Phase 2 gate in
  [ROADMAP.md](ROADMAP.md) must include this compliance review as a hard dependency, not optional
  polish.

## ADR-010: Advice boundary reaffirmed against vision language ("confidently decide what to do next")
- Date: 2026-07-30
- Status: Accepted — reaffirms [ADR-002](#adr-002-logan-personalizes-and-contextualizes--it-does-not-give-directive-advice-phase-1)
  unchanged
- Context: The product vision's mission language ("help people... confidently decide what to do next")
  reads closer to directive advice than ADR-002's analysis-only boundary. Needed to resolve whether this
  signals an intended loosening of that boundary before it propagated into PRODUCT.md as written.
- Decision: The boundary is unchanged — Logan remains analysis/context-only, never directive. ADR-002
  stands exactly as-is. The vision language is a wording issue, not a policy change: when PRODUCT.md is
  rewritten, "decide what to do next" is tightened to mean deciding *whether/how much attention*
  something deserves, not what action to take.
- Consequences: The PRODUCT.md rewrite must carry this precise distinction through its mission and
  "Opportunity First" language. Any future move toward more directive guidance requires a new ADR, not a
  wording drift.

## ADR-011: Opportunity Wheel / living ripple UI is a required MVP differentiator
- Date: 2026-07-30
- Status: Accepted
- Context: The wheel/ripple interface (information flowing from outer "world" to inner "what matters,"
  with ripple propagation between related opportunities) is central to Logan's intended identity —
  explicitly meant to avoid looking like a generic dashboard or feed. Needed to decide whether this ships
  in the first version or is a later visual evolution once the reasoning engine is proven.
- Decision: The wheel/ripple UI is required from the first shipped version, not deferred to a later
  phase.
- Consequences: This materially raises Phase 1 engineering scope and risk. Continuous, confidence-driven
  radial layout with propagating ripple animation is a hard mobile-rendering problem — default React
  Native animation APIs are unlikely to be sufficient; `react-native-reanimated` and/or
  `react-native-skia` are likely required. It also makes the reasoning engine's confidence/ranking output
  a real-time UI input, not just API data rendered into static cards. Recommended sequencing (see
  [ROADMAP.md](ROADMAP.md)): run a short, timeboxed technical spike validating the core interaction
  (confidence-driven radial position + ripple propagation) on the real Expo/React Native stack early in
  Phase 1, before committing a full roadmap around it, so scope reflects validated rather than assumed
  feasibility.

## ADR-012: Logan Core keeps clean API boundaries now; no multi-client platform tooling yet
- Date: 2026-07-30
- Status: Accepted
- Context: Long-term vision is for Logan Core to power mobile, web, desktop, and future clients. Needed
  to decide how much that should shape backend architecture today versus later.
- Decision: Continue enforcing the existing principle that business/reasoning logic lives server-side
  behind a versioned API with no client-specific assumptions (see
  [ARCHITECTURE.md](ARCHITECTURE.md#architecture-principles)) — but do not build SDKs, GraphQL, or other
  multi-client platform tooling until a second client is actually planned.
- Consequences: Cheap insurance now (discipline, not infrastructure); avoids speculative platform
  investment ahead of real need. Revisit with a dedicated ADR when a second client is actually scoped.

## ADR-013: FOMO/urgency risk tightened — betting and prediction markets must stay objective
- Date: 2026-07-30
- Status: Accepted — supersedes [ADR-009](#adr-009-fomourgency-design-pattern--flagged-as-open-regulatoryethical-risk)
- Context: ADR-009 flagged FOMO-as-motivation as a general open risk without constraining it. On review,
  the combination of urgency-driven framing with gambling-adjacent content (sports betting, prediction
  markets) aimed at an 18-35 audience is a specific enough risk to warrant a hard content-level rule, not
  just a compliance-review-later flag.
- Decision: Sports betting and prediction-market (Polymarket) content stays objective and data-forward —
  no urgency-driven or persuasive gambling framing. Excitement/curiosity/momentum framing remains
  available for other domains (stocks, business, tech, careers). A legal/compliance review remains a
  required milestone before real-user scale, per ADR-009's original intent.
- Consequences: This is now enforced at the architecture level, not just a copy guideline — see the
  Policy & Safety layer in [ARCHITECTURE.md](ARCHITECTURE.md), which is responsible for betting/gambling
  language controls. `docs/PRODUCT.md` and `CLAUDE.md` must reflect this narrower rule.

## ADR-014: Adopt the Logan Intelligence System v1.0 architecture as canonical; retire the FastAPI/SQLite sketch as historical
- Date: 2026-07-30
- Status: Accepted
- Context: The originally-documented FastAPI + SQLite monolith (`backend/app/{main,memory_engine,models}.py`)
  was a working prototype sketch, not a designed architecture. A complete, locked 18-layer specification
  (Architecture v1.0, Layer Interface Specification v1.0, Data Contracts v1.0, Engineering Specification
  v1.0, Engineering Manual v1.0) has since been produced and reviewed for internal consistency against
  the existing repo docs.
- Decision: The Logan Intelligence System v1.0 package is now the canonical Phase 1 architecture.
  `docs/ARCHITECTURE.md` is rewritten around it. The old FastAPI/SQLite description is preserved as a
  historical record (it's still the only code that runs) rather than deleted, and is clearly labeled as
  superseded.
- Consequences: New backend work happens in `logan_core/` (see [ADR-017](#adr-017-new-top-level-logan_core-directory-with-one-folder-per-layer)),
  not `backend/app/`. `backend/app/` is not deleted and keeps running until `logan_core/` reaches parity.
  Interfaces, ownership rules, and data contracts from the new package are treated as locked per its own
  ground rules — changes require documenting the rationale first, same discipline as any other ADR.

## ADR-015: Mental Model Engine built as a V1 pass-through slot in Phase 1
- Date: 2026-07-30
- Status: Accepted
- Context: The Layer Interface Specification (Layer 8) and the Orchestrator's execution sequence (step 9,
  in Data Contracts v1.0) both require Mental Model Engine as a pipeline stage. The two "Implementation
  Order" checklists (`PROJECT_STATUS.md`, `Logan_Claude_Implementation_Prompt.txt`) both omitted it —
  an internal inconsistency in the source package.
- Decision: Build it in Phase 1 as specified — a real pipeline stage that stores `MentalModel` hypotheses
  and passes `ReasoningResult` through unchanged, with no influence on the Opportunity Engine until V2.
- Consequences: V1→V2 activation later requires no new pipeline stage, only turning on existing logic —
  matches the spec's stated intent ("collects the data needed for V2 activation without a migration").

## ADR-016: Orchestrator owns writing Operational History
- Date: 2026-07-30
- Status: Accepted
- Context: No layer's "Allowed" list in the Layer Interface Specification includes writing to Operational
  History — a genuine gap in the source package. World Model may read it; Memory System explicitly
  disclaims ownership ("references, does not own").
- Decision: The System Orchestrator persists every `NormalizedSignal` (and subsequent `EnrichedEvent`,
  `EvidenceTrust`, `CommunitySignal`, etc.) to Operational History as part of pipeline execution,
  immediately after Normalization, before World Model runs. This is treated as pipeline infrastructure,
  not a layer's business logic.
- Consequences: World Model's responsibility stays limited to the entity graph and relationships, per its
  original spec. Operational History becomes an Orchestrator-owned, append-only store, independent of
  Memory System's Logan Memory store.

## ADR-017: New top-level `logan_core/` directory, with one folder per layer
- Date: 2026-07-30
- Status: Accepted
- Context: The source package's recommended repository blueprints (Engineering Specification §6,
  Engineering Manual §6) disagreed with each other and didn't assign every layer its own folder. Needed
  a single, unambiguous layout, and needed to decide where it lives relative to the existing
  `backend/` + `mobile/` monorepo.
- Decision: A new top-level `logan_core/` directory, sibling to `backend/` and `mobile/`, structured one
  folder per layer: `contracts/ orchestrator/ receptors/ normalization/ world_model/ evidence_trust/
  community_intelligence/ memory/ user_model/ active_context/ reasoning/ mental_model/
  conclusion_confidence/ opportunity/ policy/ prioritization/ presentation/ feedback/ learning/ tests/
  docs/` (Normalization is Layer 2 in the Layer Interface Specification and gets its own folder for the
  same reason every other layer does).
- Consequences: 1:1 mapping between spec layers and code folders — easy to navigate, easy to keep
  ownership boundaries enforced (e.g. import-linting rules can map directly to the "what no layer may do"
  table). `backend/app/` is untouched for now, per [ADR-014](#adr-014-adopt-the-logan-intelligence-system-v10-architecture-as-canonical-retire-the-fastapisqlite-sketch-as-historical).

## ADR-018: Stricter per-layer testing bar adopted for the `logan_core` pipeline
- Date: 2026-07-30
- Status: Accepted — narrows the scope of [ADR-005](#adr-005-pragmatic-testing-bar-during-mvppre-launch),
  does not repeal it
- Context: The source package's own testing strategy (unit tests per layer, contract validation tests,
  pipeline integration/replay tests, a regression suite before schema changes) is stricter than ADR-005's
  pragmatic MVP bar. Eighteen independently-owned, contract-bound layers are only maintainable if each
  one is independently verified.
- Decision: Inside `logan_core/`, adopt the source package's full testing strategy: unit tests per layer,
  contract validation tests for every typed object, an end-to-end pipeline integration test (the Tesla
  scenario), and a regression suite gate before any contract/schema change. ADR-005's pragmatic bar
  continues to govern `mobile/` and anything outside `logan_core/`.
- Consequences: Slower per-layer implementation now, in exchange for a pipeline that stays debuggable and
  safe to extend as more layers and domains are added. `docs/STANDARDS.md` is updated accordingly.

## ADR-019: Memory Inbox confirmation routes through Learning as a FeedbackSignal
- Date: 2026-07-30
- Status: Accepted
- Context: The product's Memory Inbox (user confirms/rejects an uncertain inference) implies a direct
  user-to-memory write path. The new architecture requires that only the Learning System may write to
  Memory or User Model — there is no path in the Layer Interface Specification for a direct user write.
- Decision: The Memory Inbox UI action emits a `FeedbackSignal` (`interaction_type: "act"`,
  `intent_confidence: 1.0`, an explicit confirmed/rejected intent) that Learning processes immediately
  rather than on its normal delayed cadence. The user-facing behavior is unchanged; the write path now
  correctly routes through Learning instead of bypassing it.
- Consequences: Preserves the Memory Inbox as Logan's core trust mechanism (see
  [PRODUCT.md](PRODUCT.md)) without violating the architecture's single-writer rule for Memory/User
  Model. Learning System's V1 scope must support immediate (not just delayed) processing for
  high-confidence explicit feedback.

## ADR-020: News added as a fifth Domain Receptor
- Date: 2026-07-30
- Status: Accepted
- Context: The source package's `domain` enum (`stocks | sports | poly | social`) had no representation
  for News, one of Logan's original six product categories. Folding it into `social` was proposed as a
  default and explicitly rejected.
- Decision: News is a fifth Domain Receptor with its own `domain` value (`"news"`), signal types, and
  entity/source mappings, alongside Stocks, Sports Betting, Poly Markets, and Social Trends.
- Consequences: `RawSignal.domain` and `NormalizedSignal.domain` gain a fifth allowed value. The Signal
  Type Registry in Data Contracts v1.0 needs a News section (e.g. `breaking_news · analysis_published ·
  correction_issued · developing_story`), defined during `logan_core/` contract implementation.

## ADR-021: Package-internal documentation fixes
- Date: 2026-07-30
- Status: Accepted
- Context: Two low-stakes but real inconsistencies were found reviewing the source package.
- Decision:
  1. `ReasoningResult.personal_relevance` (plain-language string) is renamed to
     `personal_relevance_narrative` to avoid colliding with `Dimensions.personal_relevance` (float score,
     unchanged) — same name, incompatible types, different layers, real risk of implementation bugs.
  2. The Engineering Manual's 8-phase Implementation Plan (Contracts+Orchestrator → World Model →
     Memory+User Model → Reasoning+Confidence → Opportunity+Policy+Presentation → Feedback+Learning →
     Live Integrations → Optimization) is adopted as authoritative over the Engineering Specification's
     6-phase version, which is marked superseded.
- Consequences: `docs/ROADMAP.md` uses the 8-phase breakdown. Contract code uses
  `personal_relevance_narrative`.

## ADR-023: "Opportunity Wheel" renamed to "Opportunity Field"
- Date: 2026-07-31
- Status: Accepted — supersedes the naming used in [ADR-011](#adr-011-opportunity-wheel--living-ripple-ui-is-a-required-mvp-differentiator)
- Context: The visual direction for the MVP differentiator evolved past a fixed circular menu into a
  looser, living node layout with a central "Logan core" and organic connections — a real reference
  render now exists. "Wheel" implies a rigid circular structure the design no longer matches.
- Decision: The feature is called the **Opportunity Field** everywhere going forward — code, docs, UI
  copy. ADR-011's substance (technically simplified for Phase 1, no advanced physics/particle animation)
  still holds; only the name changes.
- Consequences: New code uses `OpportunityField`/`field` naming, not `Wheel`. Historical references to
  "Wheel" in earlier ADRs are left as written (historical record) but should be read as referring to what
  is now the Opportunity Field.

## ADR-024: `crypto` added as a sixth domain
- Date: 2026-07-31
- Status: Accepted
- Context: Bitcoin is an explicit Phase 1 demo entity, and doesn't fit any existing domain
  (`stocks | sports | poly | social | news`) — it isn't a stock, a prediction-market contract, or news.
  Mistyping it under `stocks` would be inaccurate and would set a bad precedent for the next crypto asset.
- Decision: Add `crypto` as a sixth `Domain` value, following the same pattern as
  [ADR-020](#adr-020-news-added-as-a-fifth-domain-receptor) (News). Signal Type Registry gets a `crypto`
  row (e.g. `price_change · volume_spike · volatility_spike · exchange_flow · regulatory_news`).
- Consequences: `docs/specs/LOGAN_ARCHITECTURE_v1.0.md` and `LOGAN_DATA_CONTRACTS_v1.0.md` updated
  alongside the contract code change. A sixth simulated receptor is added for Phase 1 demo purposes.

## ADR-025: Frontend dependencies approved for the Opportunity Field UI
- Date: 2026-07-31
- Status: Accepted
- Context: Reproducing the reference render's connection lines, orbital rings, glow, glass panels, and
  sparklines with plain React Native `View`/`StyleSheet` would look noticeably flatter than the product
  direction calls for. `@expo/vector-icons` (already installed) covers icon/symbol needs without new
  dependencies, but line-drawing, gradients, and blur have no existing equivalent in the project.
- Decision: Add `react-native-svg` (connection lines, orbital rings, sparklines), `expo-linear-gradient`,
  and `expo-blur` (glow and glass-panel effects). All three are Expo-first-party or Expo-recommended,
  widely used, low-risk additions.
- Consequences: First UI-library dependency additions since the original prototype. No icon libraries
  were added — the existing `@expo/vector-icons` (FontAwesome5 brand + solid sets) covers the
  logo/ticker/initials/category-icon fallback chain in the symbol resolver.

## ADR-026: Opportunity Field ships Field-only for Phase 1; full tab bar deferred
- Date: 2026-07-31
- Status: Accepted
- Context: The reference render shows a 5-tab bottom bar (Field/Watchlist/Insights/Alerts/Profile), but
  the agreed Phase 1 deliverables only cover the Field screen itself plus preserving existing screens for
  comparison — Watchlist/Insights/Alerts/Profile have no defined content yet.
- Decision: Phase 1 ships the Opportunity Field as the home screen with a simple menu (behind the
  hamburger icon) linking to the preserved legacy screens (classic briefing, Ask Logan, Memory Inbox,
  Tesla-only demo) for comparison/fallback. The full 5-tab bottom bar is deferred until the other four
  tabs have real content, not built as inert placeholders.
- Consequences: Matches the mockup's core identity (the Field) without committing to unbuilt navigation
  surface area. Revisit once Watchlist/Insights/Alerts/Profile are actually scoped.

## ADR-022: `logan_core` bridged into the historical backend via a demo endpoint, not a real API design
- Date: 2026-07-31
- Status: Accepted
- Context: Needed to prove the `logan_core` pipeline end-to-end through the mobile app, without yet doing
  the real external API design that [ARCHITECTURE.md](ARCHITECTURE.md#known-gaps-tracked-not-yet-urgent)
  already flags as an open question, and without prematurely coupling `logan_core` to FastAPI/HTTP
  concerns it shouldn't own.
- Decision: `backend/app/logan_demo.py` adds `logan_core`'s repository root to `sys.path` at import time
  (a local-dev shim — `logan_core` has no installable packaging yet) and exposes a single
  `run_tesla_demo()` function that instantiates a fresh `Orchestrator` per call and runs the existing
  simulated Tesla scenario. `backend/app/main.py` wires this to `POST /v1/demo/tesla`. This is explicitly
  a demo/proof-of-connectivity endpoint, not the start of the real client-facing API contract.
- Consequences: Mobile can now render a real `logan_core` pipeline result end-to-end, which is valuable
  proof the architecture works beyond automated tests. The `sys.path` shim and per-request fresh
  Orchestrator (no persistence across calls) are known simplifications — proper packaging
  (`pyproject.toml` for `logan_core`) and the real API design remain open, tracked in
  [ARCHITECTURE.md](ARCHITECTURE.md#open-questions). Don't extend this endpoint into a general-purpose
  API by accretion; when the real API design happens, this demo route should likely be replaced, not
  grown.

## ADR-027: Opportunity Field's interaction model replaced — depth-of-focus "Attention Field" instead of a radial multi-node layout
- Date: 2026-08-03
- Status: Accepted — supersedes the interaction model (not the name — see open question below) described
  in [ADR-023](#adr-023-opportunity-wheel-renamed-to-opportunity-field)
- Context: The radial field (all entities visible at once around a central "Logan core," built
  2026-07-31) shipped and type-checked cleanly, but repeated design critique converged on a deeper
  problem than any single visual tweak could fix: showing every entity at equal visual weight
  simultaneously reads as a dashboard/graph, asks the user to scan and rank things themselves, and gives
  Logan no way to assert "this is what matters most right now" before any text is read.
- Decision: Replaced the radial layout with a depth-of-focus model — one entity held in clear focus at a
  time (large, legible, holding real content), everything else present only as soft, unlabeled ambient
  light, the way a camera holds one plane of a scene sharp while the rest recedes. Swiping or tapping a
  background entity shifts focus, with a real transition (the outgoing entity recedes into ambient
  presence, the incoming one clarifies), not a hard cut. Went through two further internal iterations
  after initial critique (a persistent `FocusSubject` card was tried and rejected as still feeling like "a
  modal sitting on top of the visualization" — see the 2026-08-03 session note for the full critique
  trail) before landing on the current architecture: every entity, focused or not, renders through one
  shared `Vessel` component with three disclosure states (dormant/glance/detail), so information visibly
  condenses out of and recedes back into the same material rather than a separate object appearing on top
  of a background.
- Consequences: `OpportunityField`/`OpportunityNode`/`LoganCore`/`fieldLayout.ts` are preserved unchanged
  at `app/field-legacy.tsx`, reachable via the menu — nothing was deleted, per the project's standing
  preserve-don't-delete pattern for superseded screens. New code lives in `AttentionField.tsx`,
  `Vessel.tsx`, `attentionLayout.ts`. **Open question, not resolved by this ADR** (whether the
  product-facing name should also change from "Opportunity Field" to "Attention Field"): resolved by
  [ADR-039](#adr-039-attention-field-ratified-as-the-product-facing-name-closing-adr-027s-open-naming-question) — ratified as "Attention Field."

## ADR-028: Atmosphere-first visual language adopted; rendering migrates to Skia for this component
- Date: 2026-08-03
- Status: Accepted
- Context: Following ADR-027's interaction redesign, an extended visual-language exploration (three
  divergent concepts, then roughly nine iterative passes on the chosen direction, all via disposable
  Artifact mockups — see the session note for the full trail) converged on: the medium itself is the
  interface, entities are regions where the atmosphere becomes coherent enough to hold information (not
  discrete objects placed on a background), no cards, no perfect circles, no hard boundaries, and —
  after an explicit correction mid-exploration — coherence (structured, ring-artifact density) rather than
  glow (additive light/brightness) as the visual expression of confidence and resolution. Reproducing this
  faithfully requires real fractal-noise turbulence and proper blur, neither of which `react-native-svg`
  (the existing dependency, approved in ADR-025) supports at all.
- Decision: Adopt `@shopify/react-native-skia` (paired with `react-native-reanimated` +
  `react-native-worklets`, its standard animation-driving companions) for the Sprint 1 "Atmosphere" layer
  and, presumptively, future rendering of this screen. This was explicitly decided with the user after
  laying out the real cost: Skia is a native module, so **Expo Go can no longer run this app** — testing
  moves to an EAS development-client build from this point forward. The user chose this over staying on
  the existing SVG+Animated stack (which could approximate the visual language but not the true turbulence
  texture, and carried real risk of not holding 60fps with many simultaneously-animated soft-blurred
  layers).
- Consequences: New dependencies: `@shopify/react-native-skia`, `react-native-reanimated`,
  `react-native-worklets`, `expo-dev-client`; new config: `babel.config.js` (didn't exist before, required
  for the Reanimated/Worklets babel transform), `eas.json`. Getting a working iOS development-client build
  additionally required enrolling in the paid Apple Developer Program ($99/year, Individual) — a real
  monetary cost and a multi-day Apple-side activation delay, not a technical blocker on our side. Day-to-
  day development workflow changes: `npx expo start --dev-client --tunnel` instead of plain `expo start`,
  and the dev client must be rebuilt via `eas build` whenever a native dependency changes (pure JS/TS
  changes still hot-reload normally). `OpportunityField`/`Vessel`-based screens are unaffected — this
  applies to the new `AtmosphereField` component and whatever supersedes the current screen once Sprint 2+
  wires real data into it.

## ADR-029: `priority_score` deprecated as a public/canonical decision score
- Date: 2026-08-04
- Status: Accepted
- Context: `AttentionRecommendation.priority_score` blended objective and personalized signal into one
  public number. That invites two failure modes: it reads as ground truth to anyone consuming the API
  (masking that it's a V1, unvalidated, unweighted-against-outcomes formula), and it duplicates
  `hit_quality_score` (objective) and `user_value_score` (personalized), which already exist as the
  system's real decision-making scores.
- Decision: `priority_score` is deprecated as a public/decision score. `hit_quality_score` and
  `user_value_score` remain the two decision-making scores and are never collapsed into a single public
  value. A clearly named, internal-only operational ranking value is permitted for pure operational
  ordering (e.g. notification queue tie-breaking) — renamed `internal_rank_score` — but it must never be
  returned via any public API, `DeliveredItem`, or `OpportunityCard`, never used for recommend/suppress
  gating, and never become Opportunity confidence.
- Consequences: `docs/specs/Logan_Documentation_v3.1.3/07_DATA_CONTRACTS.md`'s `AttentionRecommendation`
  and `Dimensions` sections reflect the rename and the internal-only constraint. Per-domain weight
  research for `hit_quality_score` beyond Stocks remains `RESEARCH REQUIRED` — not invented as part of
  this decision. See `MACHINE_LEARNING_ARCHITECTURE.md` and `MODEL_CONTRACTS.md`.

## ADR-030: `suggested_next_step` constrained to neutral language; `external_execution_link` disabled for V1
- Date: 2026-08-04
- Status: Accepted
- Context: `DeliveredItem` gained `suggested_next_step` and `external_execution_link` fields in v3.1.2.
  Left unconstrained, both risk crossing the analysis-vs-advice boundary this project has already twice
  affirmed as load-bearing ([ADR-002](#adr-002-logan-personalizes-and-contextualizes--it-does-not-give-directive-advice-phase-1),
  [ADR-010](#adr-010-advice-boundary-reaffirmed-against-vision-language-confidently-decide-what-to-do-next)):
  a "next step" can read as directive advice, and an execution link can turn analysis into a transaction
  surface.
- Decision: `suggested_next_step` is constrained to neutral, non-directive language only — acceptable
  categories are reviewing evidence, monitoring a condition, comparing scenarios, adding to a watchlist,
  setting an alert, reviewing exposure, or opening the original source. Directive financial or wagering
  language (buy, sell, place a bet, increase/reduce a position, act before a move) is prohibited.
  `external_execution_link` stays reserved, nullable, disabled, and unrendered for V1 — always null this
  release, no UI surface renders it, no API populates it.
- Consequences: `07_DATA_CONTRACTS.md`'s `DeliveredItem` section documents both constraints. A dedicated
  execution-boundary ADR is required before `external_execution_link` may ever be populated — this ADR
  does not open that door, only documents that it stays closed for V1.

## ADR-031: Machine learning is asynchronous supporting infrastructure, not a new synchronous pipeline layer
- Date: 2026-08-04
- Status: Accepted
- Context: Nothing in the locked architecture defined where ML capability fits. Left undecided, the
  natural drift is toward an ad hoc "ML layer" that breaks the locked 18-layer count and ownership rules
  from [ADR-017](#adr-017-new-top-level-logan_core-directory-with-one-folder-per-layer).
- Decision: Machine learning in Logan is asynchronous supporting infrastructure and typed input to
  existing layers — not a new synchronous pipeline layer, and it does not change the locked layer count.
  Every score ML could ever influence is already owned by an existing layer (Evidence Trust, Conclusion
  Confidence, Opportunity Engine, User Model); those layers gain one more typed, versioned input, they are
  not replaced or duplicated by a parallel ML layer. Policy remains deterministic and authoritative — no
  ML logic lives inside Policy & Safety, and a learned score is Policy's input, never its replacement or
  a means to bypass it. Models cannot authorize trades, wagers, orders, or execution.
- Consequences: New `logan_core/` folders (`calibration/`, `outcome_verification/`, and eventually
  `personal_learning/`) may be added under the same one-folder-per-responsibility convention ADR-017
  already established for `feedback/`/`learning/` — this amends ADR-017's folder list, it does not
  supersede it or renumber the 18 synchronous layers. See `MACHINE_LEARNING_ARCHITECTURE.md`.

## ADR-032: Source-reliability calibration is the approved first ML capability; no trained model implemented this release
- Date: 2026-08-04
- Status: Accepted
- Context: Multiple ML use cases were discussed (source-reliability calibration, confidence calibration,
  personalized ranking, notification-selection ML, outcome prediction, population-level learning). Without
  an explicit scope decision, any of these could be silently implied as already underway.
- Decision: Source-reliability calibration is the approved first future ML capability. No trained model
  is implemented as part of this task — this release only reserves the contract surface for it.
  Personalized ranking, notification-selection ML, outcome prediction, and population-level learning
  remain explicitly deferred, not started.
- Consequences: `EvidenceTrust.source_reliability_model_version` and
  `ConclusionConfidence.confidence_model_version` are reserved fields, default `"deterministic-baseline"`,
  unpopulated by any trained model this release (see `07_DATA_CONTRACTS.md`, `MODEL_CONTRACTS.md`). The
  Calibration/Training Service in `MACHINE_LEARNING_ARCHITECTURE.md` is a reserved, unimplemented folder,
  not running code.

## ADR-033: Required `user_id` isolation added to `MemoryRecord` ahead of the database decision
- Date: 2026-08-04
- Status: Accepted
- Context: `MemoryRecord` had no `user_id` field, and the reference `MemoryStore` implementation is a
  single global, unpartitioned store. This blocks both personal learning and any future privacy-safe
  population-level aggregation, and the retrofit cost only grows as real data accumulates unpartitioned.
- Decision: `MemoryRecord` gains a required, non-empty, stable `user_id` field this release. This is a
  schema-shape and privacy decision, independent of the storage-backend decision
  ([ADR-006](#adr-006-database-and-hosting--open-decision), still open) — it does not require choosing a
  database or building full multi-tenancy infrastructure. The current single-operator local workflow uses
  a fixed local identifier for this field rather than an empty or anonymous value.
- Consequences: `07_DATA_CONTRACTS.md`'s `MemoryRecord` section and `logan_core/contracts/memory.py`
  reflect the required field. See `ML_PRIVACY_AND_DATA_SEPARATION.md` for the full isolation rationale.

## ADR-034: DECISION-016 clarified — popularity and community momentum can never influence ranking or recommendation direction
- Date: 2026-08-04
- Status: Accepted
- Context: DECISION-016 (in the internal documentation package's own decision log), as literally worded
  through v3.1.2, locked only a UI-encoding rule — `momentum_score` maps to node edge glow, never
  brightness, size, or proximity. It said nothing about the Learning System or aggregated trigger/source
  accuracy. Separately, `21_TRENDING_ENGAGEMENT.md`'s "Trending as Signal Amplifier" mechanism let
  `momentum_score` multiply `priority_score` by up to 1.30×, a live violation of DECISION-016's own spirit
  even though not its literal text.
- Decision: Popularity, engagement, community momentum, and crowd behavior can never affect evidence,
  confidence, urgency, ranking, relevance, recommendation direction, brightness, size, or proximity, for
  any individual opportunity, under any mechanism, direct or amplified. The `momentum_score`→
  `priority_score` amplification mechanism is confirmed non-compliant and is removed — not silently
  replaced with another scoring influence. Privacy-safe population-level learning about verified accuracy,
  calibration, and source reliability remains separately permitted (computed from aggregated, anonymized
  outcomes) because accuracy is a track-record signal about correctness, structurally different from
  momentum, which is a popularity signal about attention; the two must never share a code path, a
  registry, or a scoring term.
- Consequences: `21_TRENDING_ENGAGEMENT.md`'s amplifier section is removed, not replaced.
  `internal_rank_score`'s formula (per [ADR-029](#adr-029-priority_score-deprecated-as-a-publiccanonical-decision-score))
  drops its `community_momentum` term entirely rather than redistributing it. See
  `ML_PRIVACY_AND_DATA_SEPARATION.md`.

## ADR-035: Every future ML-influenced output requires a deterministic fallback, traceability, validation, rollback, and an approval gate
- Date: 2026-08-04
- Status: Accepted
- Context: No model exists yet, which is exactly when a governance standard is cheapest to set — before
  there's a specific model's constraints to negotiate around. Two real, already-tested mechanisms in
  `logan_core/` — `PolicyEngine.evaluate()`'s deterministic bot-risk suppression and the Memory Inbox
  confirm/reject approval pattern ([ADR-019](#adr-019-memory-inbox-confirmation-routes-through-learning-as-a-feedbacksignal))
  — already demonstrate the required shape.
- Decision: Every ML-influenced output shipped in Logan must have, from the moment it ships: (1) a
  working deterministic fallback for when the model is unavailable, low-confidence, out-of-distribution,
  or rolled back, in place before the learned path ships, not added later; (2) version traceability, via
  a `*_model_version` field visible in the existing `decision_trace` mechanism; (3) validation against
  held-out verified outcomes before any promotion to production; (4) rollback to the immediately prior
  version without a code deploy; (5) a human approval gate — promotion is never automatic.
- Consequences: Formalized in `MODEL_GOVERNANCE_AND_EVALUATION.md`. `PolicyEngine.evaluate()` and the
  Memory Inbox pattern are the explicit templates for the fallback and approval-gate requirements,
  respectively — not hypothetical future work.

## ADR-036: `OutcomeRecord` redesigned — outcomes are not reduced to a win/loss framing
- Date: 2026-08-04
- Status: Accepted — approved as drafted 2026-08-05
- Context: `OutcomeRecord`'s v3.1.2 shape (`result`/`expected`/`accuracy`/`delay_window`) collapsed every
  outcome toward a binary-ish win/loss/accuracy framing. That framing has no way to represent a
  prediction that never became resolvable, was invalidated before resolution, or was verified with low
  confidence — all real outcomes, not edge cases, and all currently indistinguishable from a plain miss.
- Decision: `OutcomeRecord` is redesigned as a structured evaluation object (`schema_version "2.0"`) that
  preserves: evaluation horizon, observed result, resolvability (not a bare win/loss field — includes
  `unresolved_pending` and both unresolvable states), invalidation status, verification quality, source
  contribution (per-trigger, not a win/loss tally), claim/prediction type, creation and resolution
  timestamps, evidence references, and decision trace. The prior `result`/`expected` fields are kept as
  deprecated pointers to the new fields, not deleted outright.
- Consequences: Detailed in `OUTCOME_EVALUATION.md` and `07_DATA_CONTRACTS.md`'s `OutcomeRecord` section,
  which is authoritative and must be read together with the summary table there. `learning_applied` stays
  `false` this release — `LearningEngine.process_outcome()` is a non-functional stub (see
  `LEARNING_AND_FEEDBACK_SPECIFICATION.md`); this ADR defines the record shape, not a working learning
  loop. Final drafted text stands as reviewed in the 2026-08-04/05 session completion report.

## ADR-037: `news` restored as the eighth standalone domain; documentation reconciled to running code and ADR-020
- Date: 2026-08-04
- Status: Accepted — approved as drafted 2026-08-05
- Context: [ADR-020](#adr-020-news-added-as-a-fifth-domain-receptor) added News as a domain receptor, and
  the running code's `Domain` literal (`logan_core/contracts/common.py`) already includes `"news"`
  alongside `stocks`/`sports`/`poly`/`social`/`crypto`. Somewhere in the v3.1.2 documentation pass that
  added Culture and Personal Finance, prose and tables across the package drifted to describing "7
  domains" without consistently listing News — a documentation regression against ADR-020, not a code
  regression.
- Decision: News is restored in documentation as the eighth standalone domain: stocks, sports, poly,
  social, crypto, culture, personal_finance, news — matching ADR-020's original decision and the running
  code. `TRIGGER_REGISTRY_NEWS.md` is referenced in `07_DATA_CONTRACTS.md` but does not yet exist;
  authoring it (trigger codes, payload schemas, ttl values) is `RESEARCH REQUIRED` and explicitly not
  done as part of this decision — no trigger codes are invented here.
- Consequences: "7 domain(s)" counts and enumerations across the v3.1.3 package are corrected to 8 where
  they list domains. Separately noted, not resolved by this ADR: `culture` and `personal_finance` are
  documentation-only additions from v3.1.2 and are not present in `logan_core/contracts/common.py`'s
  `Domain` literal today — a pre-existing docs/code gap this ADR does not close. Final drafted text stands
  as reviewed in the 2026-08-04/05 session completion report.

## ADR-038: `17_CLAUDE_ENGINEERING_GUIDE.md` is not governing authority
- Date: 2026-08-04
- Status: Accepted — approved as drafted 2026-08-05
- Context: `docs/specs/Logan_Documentation_v3.1.3/17_CLAUDE_ENGINEERING_GUIDE.md` opens with "This document
  tells Claude how to think about, work on, and evolve Logan Intelligence. Read it before every session" —
  language that could be read as a second, competing operating contract alongside this repository's own
  root `CLAUDE.md`, especially for an AI assistant working across both the repo and the internal
  documentation package.
- Decision: `17_CLAUDE_ENGINEERING_GUIDE.md` is product/architecture orientation content, not governing
  authority. Root `CLAUDE.md`, accepted entries in this ADR log, and explicit owner instructions given in
  conversation remain the sole authoritative sources for how an AI assistant operates in this repository.
- Consequences: Where `17_CLAUDE_ENGINEERING_GUIDE.md`'s process guidance conflicts with `CLAUDE.md` or an
  accepted ADR here, `CLAUDE.md` and this log win. `17_CLAUDE_ENGINEERING_GUIDE.md` is not edited to add a
  disclaimer as part of this ADR — it stands as internal package content, superseded in authority only,
  not in substance. Final drafted text stands as reviewed in the 2026-08-04/05 session completion report.

## ADR-039: "Attention Field" ratified as the product-facing name, closing ADR-027's open naming question
- Date: 2026-08-06
- Status: Accepted (owner decision OD-005, V3.1.4 BATCH-3)
- Context: ADR-027 replaced the radial `OpportunityField` interaction model with the depth-of-focus
  `AttentionField` component but explicitly left the product-facing *name* unresolved — "Opportunity
  Field" was still the documented/spoken term, while the code, the component name, and the user's own
  reference mockups ("THE ATTENTION FIELD") already pointed to "Attention Field." That ambiguity was
  carried unresolved through the v3.1.3 documentation package, which still uses "Opportunity Field" as
  the active-screen term throughout.
- Decision: "Attention Field" is the product-facing term for the live depth-of-focus home screen, going
  forward from V3.1.4. "Opportunity Field" is retained only as a historical term for the superseded
  radial layout preserved at `app/field-legacy.tsx` (ADR-023, ADR-027) and in already-published historical
  changelog/session-log entries, which are not rewritten.
- Consequences: V3.1.4 BATCH-3 documentation updates describing the *active* UI use "Attention Field."
  Prior-version numbered docs (`docs/specs/Logan_Documentation_v3.1.3/*.md`) are not swept file-by-file to
  replace every historical "Opportunity Field" mention — that volume of terminology churn across
  ~30 files is out of proportion to a naming ADR and is deferred to the next full documentation pass;
  new/edited content in this pass uses the ratified name. Code identifiers (`AttentionField.tsx`,
  `attentionLayout.ts`) already matched this decision before it was ratified and are unchanged.

## ADR-040: `docs/specs/Logan_Documentation_v3.1.3/` ratified as the authoritative spec lineage; older `docs/specs/*.md` numbered files marked historical
- Date: 2026-08-06
- Status: Accepted (owner decision OD-010, V3.1.4 BATCH-3)
- Context: Two parallel documentation lineages exist under `docs/specs/`: the original numbered files
  (`00_MASTER_BRIEF.md`... `11_UI_SYSTEM.md`, `LOGAN_ARCHITECTURE_v1.0.md`, `LOGAN_DATA_CONTRACTS_v1.0.md`,
  `LOGAN_IMPLEMENTATION_PLAN.md`, `LOGAN_VISUALIZATION_PHILOSOPHY_v1.0.md`, `ENGINEERING_REVIEW_NOTES.md`)
  and the newer, more actively reconciled `docs/specs/Logan_Documentation_v3.1.3/` package (29 core files,
  TriggerEvent framework files, ML-foundation files). `CLAUDE.md` and `docs/ARCHITECTURE.md` pointed to
  the older lineage for required `logan_core/` reading, while the actual v3.1.2/v3.1.3 reconciliation work
  (ADR-020 through ADR-038) was all done against the newer package — creating a real risk that an AI
  assistant or contributor reads stale, unreconciled interface specs.
- Decision: `docs/specs/Logan_Documentation_v3.1.3/` is the authoritative, canonical specification lineage
  going forward. The older `docs/specs/*.md` numbered files (00-11), `LOGAN_ARCHITECTURE_v1.0.md`,
  `LOGAN_DATA_CONTRACTS_v1.0.md`, `LOGAN_IMPLEMENTATION_PLAN.md`, `LOGAN_VISUALIZATION_PHILOSOPHY_v1.0.md`,
  and `ENGINEERING_REVIEW_NOTES.md` are historical: preserved unchanged (not deleted, per the project's
  standing preserve-don't-delete pattern), but no longer read as current guidance.
- Consequences: `CLAUDE.md`'s required-reading pointers for `logan_core/` work updated to reference
  `Logan_Documentation_v3.1.3/06_LAYER_INTERFACE_SPECIFICATION.md`, `07_DATA_CONTRACTS.md`, and
  `08_BUILD_ORDER.md` instead of the `LOGAN_*_v1.0.md` files. `docs/ARCHITECTURE.md`'s reference updated
  similarly. The old lineage files are not individually annotated with a superseded-banner in this pass
  (out of proportion to the ADR); this entry is the authoritative record that they are historical. A
  future pass may add short pointer banners to the old files themselves if contributors are found reading
  them by habit. **Folder subsequently renamed** to `Logan_Documentation_v3.1.4/` — see
  [ADR-041](#adr-041-logan_documentation_v313-folder-renamed-to-logan_documentation_v314); this entry's
  prose is left as originally written (the folder was in fact named `_v3.1.3/` when this decision was
  made) rather than retroactively edited.

## ADR-041: `Logan_Documentation_v3.1.3/` folder renamed to `Logan_Documentation_v3.1.4/`
- Date: 2026-08-07
- Status: Accepted (post-V3.1.4 packaging cleanup, Phase 1)
- Context: ADR-040 ratified `docs/specs/Logan_Documentation_v3.1.3/` as the authoritative spec lineage.
  After the full V3.1.4 implementation pass, the folder still carried the `_v3.1.3` name while several of
  its files (`18_SESSION_LOG.md`, `23_CURRENT_IMPLEMENTATION_STATE.md`, `24_API_SPECIFICATION.md`,
  `27_SECURITY_PRIVACY_COMPLIANCE.md`, `28_PACKAGE_MANIFEST.md`, plus the new
  `V3.1.4_IMPLEMENTATION_SUMMARY.md`) now genuinely represented V3.1.4 content — a real risk of a reader
  assuming the whole package was still v3.1.3. A repository-wide reference check found the path used only
  in Markdown links and two code comments (`pyproject.toml`, `backend/app/opportunities.py`) — no
  functional/import dependency anywhere — confirming the rename was safe with no application-behavior risk.
- Decision: Rename the folder to `docs/specs/Logan_Documentation_v3.1.4/` (`git mv`, preserving history).
  Content lineage is unchanged — this is a packaging/naming fix, not a new reconciliation pass. Per-file
  `**Version:**` headers and `28_PACKAGE_MANIFEST.md`'s per-row Version column continue to reflect each
  file's actual last-touched version (most files remain honestly labeled 3.1.2/3.1.3, per the manifest's
  existing convention) — the rename does not bump every file to 3.1.4.
- Consequences: All functional/navigational path references updated (`CLAUDE.md`, `docs/ARCHITECTURE.md`,
  the two code comments, and the doc package's own current-state files: `18_SESSION_LOG.md`'s
  still-current BATCH-3/4/5 entries, `DOCUMENTATION_REFERENCE_AUDIT.md`, `V3.1.4_IMPLEMENTATION_SUMMARY.md`).
  Prior ADR bodies (ADR-029, ADR-038, ADR-040) that reference the old path in their own historical prose
  are **not** rewritten — decisions are treated as immutable once accepted (the same pattern used for
  ADR-027, superseded via ADR-039 rather than edited in place); those bodies accurately describe what was
  true when they were written. `docs/specs/Logan_Documentation_v3.1.3.zip` and `_v3.1.2.zip` (prior
  point-in-time archive snapshots) are untouched; `Logan_Documentation_v3.1.4.zip` is rebuilt from the
  renamed folder.

## ADR-042: Sprint 3.6.6 — minimal TriggerEvent implemented for one vertical slice (NVIDIA earnings -> STOCK_EARNINGS_BEAT); OD-009 partially superseded
- Date: 2026-08-14
- Status: Accepted
- Context: OD-009 (V3.1.4 BATCH-3) marked the entire TriggerEvent framework and every domain's trigger
  registry `SPECIFIED — NOT IMPLEMENTED`, explicitly out of scope for that release. Sprint 3.6.6's goal is
  STRATUS's first real (non-simulated-shaped) vertical slice: NVIDIA earnings data, deterministically
  evaluated against the already-registered `STOCK_EARNINGS_BEAT` fire condition
  (`TRIGGER_REGISTRY_STOCKS.md`), flowing through the existing, unmodified downstream pipeline to a
  delivered opportunity. Building the full ~60-field TriggerEvent contract, the revision/dedup model, or
  any other domain's trigger codes was explicitly out of scope for this sprint (see the sprint brief's
  "Explicitly out of scope for this slice"). Repository reconnaissance (Phase 1) confirmed OD-009's
  "NOT IMPLEMENTED" claim was still accurate before this sprint: zero TriggerEvent code existed anywhere
  in `logan_core/`, `Normalizer` only validates `signal_type` against a fixed registry (never computes
  one from numeric evidence), and every domain receptor remained simulated-only.
- Decision:
  1. A minimal `TriggerEvent` contract (`logan_core/contracts/trigger.py`) implements only the fields this
     one slice can truthfully populate — trigger identity/code/class/type/status, affected entity,
     direction, raw_magnitude, a fixed registry-specified `confidence_contribution`, a `context` dict
     containing only provider-supplied fields, originating signal ids, source/provenance, and
     decision_trace. Revision/dedup/identity machinery, `domain_impacts`, `lifecycle_effect`,
     `seasonal_context`, `causal_relationship`, `provider_disagreement_state`, `notification_eligibility`,
     and every other field the full framework specifies remain unimplemented and out of scope.
  2. Deterministic trigger detection (`logan_core/trigger_detection/stocks.py`) sits at the
     signal/normalization/event-resolution boundary, called by the Orchestrator between normalization and
     World Model, opt-in via `PipelineDependencies.trigger_detector` (defaults `None` — every existing
     caller, including `backend/app/logan_feed.py`'s current simulated-fixtures path, is unaffected; see
     `test_without_trigger_detector_wired_behaves_exactly_as_before`). Only `STOCK_EARNINGS_BEAT` is
     implemented; every other registered stocks code, and every other domain, remains SPECIFIED — NOT
     IMPLEMENTED.
  3. `TriggerEvent`s attach to `EnrichedEvent.trigger_events` (new, additive, default-empty field) via
     `WorldModel.process()`'s new optional `trigger_event` parameter. A duplicate poll of the same report
     is deduped by replacing (not appending) the entry for that `trigger_code`, so re-polling never
     double-counts; a corrected/revised report (different magnitude, same `trigger_code`) also replaces
     the prior entry rather than stacking — a deliberately simpler rule than the full framework's
     revision-history model.
  4. The trigger's `confidence_contribution` reaches `ConclusionConfidence.confidence_score` through two
     small, additive extensions: `EvidenceTrust` gains a `trigger_confidence_bonus` field (sum of attached
     triggers' contributions, defaulting 0.0), and `ConclusionConfidenceEngine.evaluate()` changes
     `confidence_score = trust.trust_score` to `confidence_score = trust.trust_score +
     trust.trigger_confidence_bonus` before the existing contradiction-penalty/clamp logic. This is a
     deterministic, rule-based addition — not a new ML capability, and not the ADR-032 ML-calibration
     surface (`*_model_version` fields on `EvidenceTrust`/`ConclusionConfidence` remain
     `"deterministic-baseline"`, untouched). It is also distinct from ADR-015's Mental Model exclusion:
     Mental Model is explicitly narrative/interpretive and still contributes nothing to confidence
     (enforced by the existing `test_mental_model_confidence_has_zero_scoring_effect`-style regressions,
     which still pass); a confirmed trigger is verified quantitative evidence, a different kind of input.
  5. Provider-specific structure terminates at a new receptor/provider boundary
     (`logan_core/receptors/providers/`): an `EarningsProvider` Protocol, a `FixtureEarningsProvider`
     (explicitly, unmistakably labeled non-live — `source_id="fixture_earnings_provider"`,
     `source_name="STRATUS Test Fixture (not live data)"`) used by tests, and
     `receptors/stocks_earnings.py`'s `earnings_report_to_raw_signal()` mapping into the existing,
     unmodified `RawSignal` contract. No real provider (e.g. Alpha Vantage/Finnhub) is implemented this
     sprint — no credentials were available; implementing one later means writing one class against the
     existing Protocol, no other file changes.
  6. `23_CURRENT_IMPLEMENTATION_STATE.md`'s TriggerEvent/receptor rows are updated to describe exactly
     this subset as BUILT, with the remainder of OD-009's scope still explicitly marked NOT IMPLEMENTED —
     OD-009 is partially superseded, not reversed.
- Consequences: `logan_core` test count rises from 100 to 126 (Phase 8: trigger-condition unit tests
  covering every edge case in the sprint brief — missing/zero/negative consensus, non-firing beats,
  duplicate polls, corrections; receptor/provider mapping tests; a full pipeline integration test proving
  the deterministic positive-fire case end-to-end through the unmodified downstream pipeline via
  `FixtureEarningsProvider`; and a backward-compatibility test proving the default/no-detector path is
  byte-for-byte unchanged). `backend/app/logan_feed.py` is **not** wired to the new trigger/provider code
  this sprint — the live `/v1/opportunities` demo continues serving simulated fixtures for every entity,
  NVDA included, exactly as before. Proving this same path against real NVIDIA earnings data is the
  explicit next step once a stocks-earnings provider and API credentials are chosen (a decision this ADR
  does not make).

## ADR-043: Sprint 3.6.6B — Financial Modeling Prep selected as the first live earnings provider
- Date: 2026-08-15
- Status: Accepted
- Context: ADR-042 built the `EarningsProvider` Protocol and left choosing a real provider as an explicit
  open decision, deliberately not made by that ADR (no credentials were available, and picking a paid/
  external provider is a decision this project's collaboration model reserves for the owner). The owner
  selected Financial Modeling Prep (FMP) for Sprint 3.6.6B. FMP's official API docs
  (`site.financialmodelingprep.com`) return HTTP 403 to automated fetches, so the endpoint shape was
  confirmed via multiple independent secondary sources (FMP's own third-party "how-to" articles, tutorial
  writeups quoting real example responses) rather than the canonical docs page directly — see the
  field-name uncertainty noted below.
- Decision:
  1. `FmpEarningsProvider` (`logan_core/receptors/providers/fmp.py`) implements the existing
     `EarningsProvider` Protocol exactly as specified in ADR-042 — no changes to the Protocol, to
     `EarningsReport`, or to any pipeline layer. FMP's per-symbol historical endpoint
     (`GET https://financialmodelingprep.com/stable/earnings?symbol={SYMBOL}`) was chosen over the
     broader earnings *calendar* endpoint because it returns already-reported actual-vs-estimated EPS for
     a specific company, not a forward-looking, mostly-null schedule.
  2. Researched field mapping: `symbol` → `entity_id`, `epsActual` → `actual_eps`, `epsEstimated` →
     `consensus_eps`, `fiscalDateEnding` → `fiscal_quarter`, `date` → `report_timestamp`. **Genuine
     uncertainty:** a related (older/legacy) FMP calendar endpoint uses a plain `eps` key instead of
     `epsActual` for the same concept, per one confirmed real example response; which name the *stable
     per-symbol* endpoint actually uses could not be independently verified against FMP's own docs due to
     the 403. This is accepted as a known risk, not silently papered over: `FmpEarningsProvider._parse_entry`
     uses `.get()` exclusively (never direct indexing), so a wrong field name degrades to
     `actual_eps=None`/`consensus_eps=None` (a real, honest "missing data" result the rest of the
     pipeline already handles safely) rather than a crash or a fabricated value. The live verification
     script (`logan_core/live_verification/nvda_earnings.py`) surfaces this immediately and explicitly the
     first time it's run against real credentials.
  3. `httpx` becomes a `logan_core` **runtime** dependency for the first time (`logan_core/requirements.txt`)
     — previously only a `backend`-side dev/test dependency (FastAPI's `TestClient`). Not a new library to
     this monorepo, just a new role for an already-vetted one; flagged here per the project's standing
     "any dependency addition requires visibility" rule rather than added silently.
  4. No automatic fallback from `FmpEarningsProvider` to `FixtureEarningsProvider` exists anywhere — a
     failed FMP call raises `FmpProviderError`; only a caller can decide what to do with that, and none of
     the existing pipeline call sites do so automatically.
  5. `backend/app/logan_feed.py` and `/v1/opportunities` remain unwired to FMP, per this sprint's explicit
     scope boundary — provider-level live verification only, not a live production data source yet.
- Consequences: `logan_core` test count rises from 126 to 141 (15 new `FmpEarningsProvider` contract tests,
  all `httpx.MockTransport`-mocked — the normal suite makes zero real network calls and never depends on
  `FMP_API_KEY` existing). A real `FMP_API_KEY` (owner-provided, environment-only, never committed) is
  required to run `logan_core/live_verification/nvda_earnings.py`; that script was not run this session
  pending that credential, and its result (fired vs. did-not-fire, and whether the field-name assumption
  in point 2 held) should be recorded in a follow-up session note or ADR once it is.

## ADR-044: Sprint 3.6.6C — proven live NVDA path wired into `GET /v1/opportunities`, config-gated and default-off
- Date: 2026-08-15
- Status: Accepted
- Context: ADR-042/ADR-043 built and live-verified `FmpEarningsProvider` and `STOCK_EARNINGS_BEAT` at the
  provider/pipeline level, but deliberately stopped short of wiring either into the production
  `/v1/opportunities` endpoint mobile actually consumes. This sprint's scope was the smallest safe wiring
  change to close that gap for NVDA only, without redesigning the pipeline, adding new triggers, or
  replacing the rest of the simulated feed.
- Decision:
  1. `backend/app/config.py` (new): `live_nvda_earnings_enabled()` reads `STRATUS_LIVE_NVDA_EARNINGS`
     (unset/false by default — existing simulated-only behavior is the safe default) and, as a side effect
     of import, `load_dotenv()`s `backend/.env` (gitignored, local-dev-only) so `FMP_API_KEY` reaches the
     real process environment the same way `logan_core/live_verification/nvda_earnings.py` already expected
     it to. No general settings framework was introduced — this is the minimal addition needed, and the
     first place `backend/app/` reads `.env` at all.
  2. `backend/app/logan_feed.py`: when the flag is on, `_live_nvda_raw_signal()` fetches NVDA's latest
     report via `FmpEarningsProvider` and, on success, substitutes it for the simulated NVDA fixture
     (dict-keyed by entity_id, so the two can never coexist — exactly one NVDA item either way). Every
     other simulated entity is untouched regardless of the flag.
  3. **Two architectural issues were found and fixed during implementation review, before this sprint's
     tests or live verification were considered complete** (both raised directly by the project owner
     reviewing the first draft, not self-discovered):
     - *Disabled-mode trace parity*: the first draft wired `PipelineDependencies.trigger_detector`
       unconditionally into the shared Orchestrator singleton. Because `Orchestrator.run()` appends a
       `"trigger_detection"` `ExecutionTrace` layer entry for *every* raw_signal whenever *any* detector is
       configured — regardless of whether it ultimately fires (see `orchestrator/pipeline.py`) — this would
       have silently changed the execution trace for every simulated entity (TSLA, AAPL, BTC, etc.), not
       just NVDA, even with the live path fully disabled. Fixed: `_get_orchestrator()` now only constructs
       `PipelineDependencies(trigger_detector=StocksTriggerEvaluator())` when
       `live_nvda_earnings_enabled()` is true at construction time; with the flag off, it builds the exact
       same bare `PipelineDependencies()` every pre-3.6.6C caller already gets, so disabled mode is
       byte-for-byte unchanged, not just "the NVDA row looks the same."
     - *Non-fire substitution*: the first draft substituted the live FMP report for the simulated fixture
       whenever FMP returned *any* usable report, whether or not it beat consensus by the required 5%. That
       meant a real-but-non-beating earnings report would still surface as an "opportunity" (with lower,
       unboosted confidence) rather than the intended semantics: a valid provider response is not itself an
       opportunity, and the live NVDA slice should surface a real opportunity only when the implemented
       `STOCK_EARNINGS_BEAT` trigger actually fires. Fixed: `_live_nvda_raw_signal()` now pre-checks the
       fetched report against `evaluate_earnings_beat_condition()` — the same pure function
       `StocksTriggerEvaluator.evaluate()` calls internally, reused rather than re-derived, so the pre-check
       and the orchestrator's own later trigger-detection layer can never disagree — and falls back to the
       simulated fixture (same as any other failure mode) when it doesn't fire.
  4. While validating the fix for point 3 together with the backend suite, a **pre-existing cross-suite
     test-isolation gap** was exposed (not introduced by this sprint, but only surfaced because
     `backend/app/config.py` now `load_dotenv()`s a real `FMP_API_KEY` at import time): running `backend`
     and `logan_core` tests in the same process leaked that real key into `logan_core/tests/
     test_fmp_provider.py::test_missing_api_key_raises_without_making_any_request`, which assumed an empty
     environment rather than explicitly isolating itself. Fixed in the test (added
     `monkeypatch.delenv("FMP_API_KEY", raising=False)`, matching the sibling test directly below it in the
     same file) rather than in `config.py` — two independent test suites' correctness should never depend on
     which one happens to import a dotenv-loading module first.
  5. No new trigger codes were added; this sprint stops here per its own scope boundary, so the owner can
     review the production wiring before intelligence breadth expands further.
  6. Public API contract unchanged: `internal_rank_score`, the FMP API key, and raw provider payloads are
     never serialized in the `FeedItem`/`/v1/opportunities` response; the field set is identical whether the
     NVDA item is live or simulated.
- Consequences: `backend` test count rises from 18 to 31 (13 new tests: disabled-mode trace parity,
  enabled+fired, enabled+not-fired-falls-back, provider/auth/no-data failure fallback, the exact
  scheduled-vs-reported selection-logic scenario from ADR-043 reproduced end-to-end through the backend
  wiring, and API-contract/no-secret-leak checks). `logan_core` test count unchanged at 143 (one existing
  test hardened for isolation, none weakened). Live-verified locally through the real `GET /v1/opportunities`
  route with `STRATUS_LIVE_NVDA_EARNINGS=true` and the real `FMP_API_KEY`: real EPS 1.87 vs. consensus 1.76
  (beat_pct 6.25%), `STOCK_EARNINGS_BEAT` fired, `confidence_score` 0.595 ("Moderate"), exactly one NVDA item
  in an 11-item response, all 10 other simulated entities untouched, HTTP 200, no `internal_rank_score` or
  key in the response body. The mobile app requires no changes to consume this — it already calls
  `/v1/opportunities` and renders whatever `FeedItem`s it receives.

## ADR-045: Sprint 3.6.6D — STOCK_EARNINGS_MISS, STOCK_EARNINGS_IN_LINE, and a ConvergenceDetector foundation
- Date: 2026-08-18
- Status: Accepted
- Context: With the live NVDA `STOCK_EARNINGS_BEAT` path proven and wired (ADR-042/043/044), the owner made
  two explicit decisions before further trigger expansion: (1) a confidence model — keep
  `STOCK_EARNINGS_BEAT`'s fixed `+0.22` unchanged, use fixed contributions only where a registry/spec already
  defines them, never invent new weights, and when multiple correlated triggers fire on one event, do not sum
  their contributions — use the single strongest applicable one, while preserving every fired `TriggerEvent`
  as evidence. No ML/calibration redesign yet, pending real outcome data (consistent with ADR-032). (2) an
  implementation scope — implement `STOCK_EARNINGS_MISS`; build the smallest real Convergence Detector
  foundation implementing decision (1); then, after inspecting current FMP/provider data support, add one
  more independent stock trigger implementable cleanly with data already available, preferring reuse over
  new provider complexity. No other domain to be touched.
- Decision:
  1. **`STOCK_EARNINGS_MISS`** (`logan_core/trigger_detection/stocks.py`): `evaluate_earnings_miss_condition`
     mirrors `evaluate_earnings_beat_condition`'s structure exactly — `actual_eps < consensus_eps AND
     miss_pct >= 5.0`, `+0.20` confidence contribution, both values taken verbatim from
     `TRIGGER_REGISTRY_STOCKS.md`, not invented. Uses the identical `actual_eps`/`consensus_eps` fields
     `FmpEarningsProvider` already fetches for `STOCK_EARNINGS_BEAT` — zero provider changes. `StocksTriggerEvaluator.evaluate()`
     now checks BEAT, then MISS, then IN_LINE in sequence; their fire conditions are mutually exclusive by
     construction (>=5% up, >=5% down, or <2% either way), so exactly zero or one fires per report.
  2. **`STOCK_EARNINGS_IN_LINE`** — the "next independent trigger," chosen after inspecting what's actually
     implementable without new provider work. Rejected alternatives and why: `STOCK_EARNINGS_QUALITY_WARNING`
     needs a one-time-item flag FMP's earnings endpoint doesn't return; `STOCK_GUIDANCE_RAISED`/`LOWERED` need
     prior-vs-new guidance midpoints — `EarningsReport.guidance_revised`/`guidance_delta_pct` exist on the
     contract but `FmpEarningsProvider` has never populated them because FMP's `/stable/earnings` endpoint
     doesn't return guidance data (would require a different, unvetted endpoint — real provider complexity);
     `STOCK_OPTIONS_FLOW_SURGE`, `STOCK_PRICE_MOVE_SIGNIFICANT`, `STOCK_DIVERGENCE_PRICE_VS_SENTIMENT`,
     `STOCK_INSIDER_ACTIVITY`, `STOCK_ANALYST_UPGRADE`/`DOWNGRADE`, `STOCK_ODSE_ACCUMULATION` all need entirely
     different data sources (options flow, price/session data, sentiment, SEC filings, analyst ratings) not
     fetched today. `STOCK_EARNINGS_IN_LINE` needs nothing beyond `actual_eps`/`consensus_eps` — true reuse.
     Fires on `abs(beat_pct) < 2.0`, per the registry's own `0.0` confidence contribution ("no positive
     contribution; used to close hypotheses") — it still attaches a real `TriggerEvent` (direction `"neutral"`,
     trigger_class `"confirmation"`) so the evidence is visible, it just doesn't move confidence.
  3. **`ConvergenceDetector`** (new `logan_core/convergence/` package): implements decision (1)'s
     strongest-not-summed rule. `EvidenceTrustEngine` now calls `ConvergenceDetector.resolve(event.trigger_events)`
     instead of summing every attached `TriggerEvent.confidence_contribution` directly — the result carries the
     single dominant trigger's contribution (clamped to `[0.0, 1.0]`) plus every fired trigger's code, for
     `decision_trace` auditability. With exactly one trigger attached (every real scenario today, since
     BEAT/MISS/IN_LINE are mutually exclusive on one report), `max` and `sum` are numerically identical — so
     this changes nothing observable yet, but is real, tested production code that resolves correctly the
     moment a second trigger code is ever attached to one event.
     **Explicitly not the canonical Convergence Detector** from
     `docs/specs/Logan_Documentation_v3.1.4/source_material/04_HIT_DETECTION.md` /
     `TRIGGER_REGISTRY_STOCKS.md`'s `STOCK_CONVERGENCE_MULTI_SOURCE` — that is a Hit-Detection-layer component
     that watches independent raw signals across domains/sources *before* trigger detection and itself emits a
     `TriggerEvent` with its own `OpportunityEvidence` output; neither `OpportunityEvidence` nor the Hit
     Detection layer exist in this codebase (still SPECIFIED — NOT IMPLEMENTED, OD-009), and building them is a
     separate, larger decision not made this sprint. This component instead resolves `TriggerEvent`s that are
     *already* attached to one `EnrichedEvent` — a narrower, already-real problem. World Model's dedup key
     (`entity_id`, `signal_type`) was **not** widened to merge different signal_types for the same entity
     (that would be genuine cross-signal-type convergence, and a much larger, riskier change to existing
     dedup semantics affecting every entity) — flagged as a separate future decision, not made tonight.
  4. **Known limitation, documented not solved**: the strongest-not-summed rule doesn't yet model *companion*
     triggers meant to net against another (e.g. `STOCK_EARNINGS_QUALITY_WARNING`'s registered `-0.15`, meant
     to reduce `STOCK_EARNINGS_BEAT`'s `+0.22` specifically, not compete with it as an independent "strongest
     signal" candidate). Not implemented, so not exercised — a real gap to revisit if/when it is.
  5. **Known duplication, deliberately not fixed this sprint**: `trigger_detection/stocks.py`'s six threshold/
     confidence constants (`_BEAT_PCT_THRESHOLD=5.0`, `_MISS_PCT_THRESHOLD=5.0`, `_IN_LINE_PCT_THRESHOLD=2.0`,
     `_BEAT_CONFIDENCE_CONTRIBUTION=0.22`, `_MISS_CONFIDENCE_CONTRIBUTION=0.20`,
     `_IN_LINE_CONFIDENCE_CONTRIBUTION=0.0`) are typed Python literals hand-copied from
     `TRIGGER_REGISTRY_STOCKS.md`'s markdown table, not read from it at runtime — verified consistent as of
     this sprint (2026-08-18), but nothing prevents the two from drifting apart as more trigger codes are
     added by hand. Owner decision: do not build a machine-readable registry loader yet, at only 3 trigger
     codes it would be premature infrastructure — but convert to one before trigger volume grows much
     further. Flagged here and in `23_CURRENT_IMPLEMENTATION_STATE.md` so it isn't silently forgotten.
- Consequences: `logan_core` test count rises from 143 to 162 (19 new: 13 `trigger_detection` unit/evaluator
  tests for MISS/IN_LINE/the dead zone, 6 `ConvergenceDetector` unit tests, plus 2 new pipeline-integration
  tests and 1 rewritten one in `test_pipeline_nvda_earnings.py`, plus 1 new `EvidenceTrustEngine` integration
  test proving strongest-not-summed end to end). One pre-existing test
  (`test_pipeline_nvda_earnings.py`'s non-qualifying-earnings case) was rewritten, not weakened: its old input
  (0.99 vs 0.98, ~1.02%) now correctly fires `STOCK_EARNINGS_IN_LINE`, so the "nothing fires" case moved to a
  genuine dead-zone value (~4.08%) and the old input became its own new IN_LINE test. Live-verified: the real
  FMP `/v1/opportunities` NVDA path (ADR-044) still returns the identical result after this refactor (EPS 1.87
  vs. 1.76, `STOCK_EARNINGS_BEAT` fired, confidence 0.595) — `StocksTriggerEvaluator`'s BEAT branch is
  unchanged in behavior, only restructured to share a `_build_trigger_event` helper with MISS/IN_LINE. MISS
  and IN_LINE are proven at the fixture/pipeline-integration level only, not yet against a live report that
  actually misses or lands in-line — consistent with the "don't force a fire" rule; real live proof for those
  two arrives whenever NVDA's next real report happens to land there, the same way BEAT's live proof arrived
  in Sprint 3.6.6B/C, not forced or simulated here to close the gap artificially.

## ADR-046: Sprint 3.6.6I — fixed a same-timestamp engagement fixture artifact inflating `lifecycle_state`
- Date: 2026-08-19
- Status: Accepted
- Context: A STRATUS Watch eligibility trace (owner request, tracing why FED/AI_SECTOR/NFL all qualified for
  push simultaneously) found that `backend/app/logan_feed.py`'s `_engagement_samples()` gave both simulated
  engagement readings the identical `observed_at=now` timestamp. `CommunityIntelligenceEngine.measure()`
  (unmodified, `logan_core/community_intelligence/community.py`) floors elapsed time at 0.25 hours as its own
  division-by-zero guard, then computes `engagement_velocity` as the raw point-delta divided by elapsed time.
  With two same-timestamp samples, every entity's real point-delta was silently multiplied by 4, pushing
  `lifecycle_state` to `"emerging"` for 10 of 11 simulated entities regardless of whether the underlying delta
  was a genuine spike — an artifact of fixture construction, not a real signal, and not something owner-facing
  documentation or code had previously called out.
- Decision:
  1. `_engagement_samples()` now spreads each entity's fixture points evenly across a new
     `ENGAGEMENT_SAMPLE_WINDOW = timedelta(hours=1)` ending at `now`, instead of stamping every point with
     `now`. The window length reuses `world_model/model.py`'s existing `DEDUP_WINDOW` (also 1 hour) as its
     reference rather than inventing a new arbitrary constant — an in-universe-consistent choice for "how long
     an observation window is" in this system, not a value tuned to produce a particular alert count. The
     underlying `(volume, unique_users, saves_shares, questions)` fixture data is untouched — this is a timing
     fix only.
  2. The spacing logic is a small, separately-testable pure function, `_spaced_timestamps(now, count, window)`,
     handling the general N-point case (today's fixtures always have exactly 2 points, but nothing hardcodes
     that).
  3. `CommunityIntelligenceEngine`, its lifecycle thresholds, `PolicyEngine`, `PrioritizationEngine`, and
     STRATUS Watch's dispatch/dedup logic are all unmodified — this ADR is scoped to fixture timing only, per
     explicit owner instruction. No personalization floor or push-count cap was added; those remain open,
     separately-tracked questions from the eligibility trace this fix responded to.
  4. Wording correction made before this ADR was written: an earlier internal trace and test comments
     described dispatch as happening on "the app's first load, then the poller's next cycle" as if that were a
     guaranteed two-step runtime order. It is not — it was the specific sequence *observed and reproduced* in
     testing (the app's own initial fetch and the background poller's first cycle can occur in either order in
     real deployment, and `get_pending_push_event_ids()` is deliberately written to be correct regardless of
     which happens first). Test comments were corrected to describe this as a scripted, representative test
     sequence, not a guaranteed ordering.
- Consequences: the corrected eligibility trace (real engagement deltas over a real hour, not the floor
  artifact) changes NFL from `emerging`/`velocity=16.0` (artifact) to `peak`/`velocity=4.0` (real) — it no
  longer clears the `urgency >= 0.7` alert bar and stops qualifying for push. FED (`velocity=14.0`) and
  AI_SECTOR (`velocity=25.0`) both still qualify — their deltas are genuinely large, not artifacts. TSLA/NVDA/
  AAPL still qualify on a first observation but never actually reach dispatch in practice, because stocks-
  domain fatigue (a separate, pre-existing mechanism, untouched here) trips before a real second pipeline call
  can dispatch them. Net effect: the realistic simultaneous-alert count drops from 3 (one of which was a
  measurement artifact) to 2, both now backed by real data. FED still qualifies with `personal_relevance=0.50`
  — the fully generic, unconnected default — confirming personalization is still not required for alert
  eligibility; that remains an open, separately-tracked question, not addressed by this timing-only pass.
  10 new tests (`test_engagement_fixture_timing.py`): window-span exactness, even N-point spacing, single-
  point safety, unchanged fixture values, the zero-elapsed precondition no longer being reachable for any real
  fixture, and two representative before/after cases (NFL's artifact-vs-real velocity, TSLA's genuine spike
  still correctly emerging). One existing test (`test_pending_push_notification_full_lifecycle`) updated to
  assert against the real dispatched count rather than a hardcoded value that depended on the artifact.
  `backend`/`logan_core` test count: 221 → 231. mypy/ruff/black clean.

## ADR-047: Behavioral-personalization foundation — first live callers of the existing FeedbackSignal -> FeedbackEngine -> LearningEngine -> MemoryStore path
- Date: 2026-08-19
- Status: Accepted
- Context: A prior design pass (owner request, no code) inventoried STRATUS's existing interaction-signal
  capture and found the key architectural fact this ADR builds on: `Orchestrator.run_feedback_loop()`
  (`logan_core/orchestrator/pipeline.py`) already chains `FeedbackEngine.interpret()` ->
  `LearningEngine.process_feedback()` -> `MemoryStore.write()` end-to-end, fully implemented and tested, but
  had zero live callers anywhere in `backend/` — only tests and `logan_core/live_verification/nvda_earnings.py`
  ever exercised it. Every real interaction signal (opening a card, how long it stayed open, tapping a
  notification) was either unobserved or observed and discarded. The owner asked for a bounded pass wiring
  real interaction capture through this existing path — explicitly not a parallel personalization system.
- Decision:
  1. New `POST /v1/interactions` route (`backend/app/main.py`), backed by `RecordInteractionRequest`/
     `RecordInteractionResponse` (`backend/app/models.py`) and `logan_feed.record_interaction()`. The route is
     a thin passthrough into `orchestrator.run_feedback_loop()` — `FeedbackEngine`'s dwell/interaction-type
     interpretation thresholds are completely unmodified. `content` for the resulting `MemoryRecord` is built
     server-side from already-known structured fields only (`f"{interaction_type} on {entity_id} ({domain})"`)
     — the client can never inject arbitrary text into Memory through this route. `user_id` is inferred as
     `LOCAL_FOUNDER_USER_ID`, matching `/v1/notifications/review`'s existing pattern, not accepted from the
     client, keeping the public contract minimal.
  2. Card open + dwell time is a single "view" interaction, submitted once at close (not open), with the
     measured `duration_ms` — the only point the real duration is knowable. Mobile-side,
     `lib/useCardDwellTracking.ts` derives its target from `AttentionField.tsx`'s existing `focusedId`/
     `disclosure` state (`disclosure === 1` is the only "card is open" condition — a focused-but-unopened
     vessel never counts) rather than adding a new open/close callback through `Vessel.tsx`. The effect
     depends only on the target's `event_id` (a stable primitive), never the target object itself, since a new
     object is constructed every render including on every ~60s poll refresh — depending on the object would
     fabricate a fresh "open" on every poll. A single `flush()` call, placed only in the effect's cleanup
     function, correctly submits exactly once for every one of: card closed, card replaced by a different
     card (no explicit close callback exists for this case — cleanup firing on a dependency change covers it),
     and component unmount. `AppState` backgrounding submits whatever was measured so far, then stops the
     clock; returning to foreground silently resumes the same still-open target's clock without ever emitting
     a signal, so background time is never counted and resuming is never mistaken for a fresh open.
  3. Notification-open is recorded separately from notification-review, reusing the existing `"click"`
     `InteractionType` rather than adding a new one — no contract expansion. `index.tsx`'s
     `openNotificationCard()` (the single choke point for both a real push tap and an in-app dropdown tap) now
     fires both the pre-existing `/v1/notifications/review` POST (badge-clearing, unchanged) and a
     `recordInteraction({..., interactionType: "click"})` call, looked up from the currently-loaded feed by
     `event_id` and silently skipped if not found (e.g. a stale/dev-only notification with no truthful
     entity_id/domain to attach). `openNotificationCard` reads feed state through a `stateRef` rather than a
     direct `state` dependency, specifically so its identity stays stable across polls — `useNotificationTapHandler`
     resubscribes its native listener whenever its callback's identity changes, and `state` updates roughly
     every 60s, so a direct dependency would have torn down and recreated the real push-tap subscription that
     often instead of once per mount.
  4. Explicitly deferred, not implemented here (per owner instruction): behavioral relevance scoring, Attention
     Profile weights/recency-decay, inferred-interest promotion thresholds, Personal/Exceptional Watch route
     eligibility, impression/exposure persistence (ownership not yet settled — see the companion design report
     delivered alongside this ADR), and any write into `UserModel`'s `established_behaviors`/`inferred_expertise`/
     `domain_preferences`/inferred `Interest` fields. This ADR only proves interactions reach `MemoryStore`
     through the existing single-writer gate; nothing yet reads them back into personalization.
- Consequences: `backend`/`logan_core` test count 231 → 244 (`backend/tests/test_interactions.py`, 13 new
  tests: view/click reaching `MemoryStore`, short-dwell interpretation unchanged end-to-end, route-level
  contract validation for domain/interaction_type, optional `duration_ms`, all six `Domain` values accepted).
  Mobile: 88 Jest tests passing (10 new, covering rendering-alone-is-not-an-interaction, single-submit on
  close/replace/unmount, no fabricated interactions from repeated polling, and background/foreground dwell
  behavior), `tsc --noEmit` and `eslint` clean, no regressions in the pre-existing `index.test.tsx` push/badge
  coverage. A local smoke test (real backend, real NVDA pipeline event) confirmed push registration,
  `/v1/interactions` (view+dwell and click), and `/v1/notifications/review` all coexist without error on the
  same event_id. No `logan_core` layer-ownership boundary was crossed: `record_interaction()` only calls the
  existing `Orchestrator.run_feedback_loop()`, never writes to `MemoryStore` or `UserModel` directly.

## ADR-048: UserModel persistence + source-aware behavioral learning — closing ADR-047's loop without touching Watch eligibility
- Date: 2026-08-21
- Status: Accepted
- Context: ADR-047 got real interaction signals (card-open/dwell, notification-tap) into `MemoryStore` but
  stopped there — nothing read them back into `UserModel`, and `UserModel` itself was rebuilt from scratch via
  `UserModelBuilder().seed()` on every single `_run_feed_pipeline()` call, so even a completed read-back would
  have had nothing to accumulate into. An initial inspection pass (documented in `SESSION_NOTES.md`,
  2026-08-19) found a real blocker before writing any code: `ReasoningEngine.reason()` read
  `user_model.interests` without filtering by `source`, so writing any `Interest(source="inferred")` would
  silently raise `personal_relevance` and therefore STRATUS Watch alert eligibility — explicitly out of scope
  for this pass. That inspection pass stopped there. This ADR covers the resumed pass that closes the loop,
  the blocker included, after a process restart recovered the in-progress (uncommitted) work for review.
- Decision:
  1. **Source-aware relevance, closing the blocker.** `ReasoningEngine.reason()`
     (`logan_core/reasoning/engine.py`) now splits `connected_entities` into `connected_entities_explicit`
     (holdings + `Interest(source="explicit")`) and `connected_entities_inferred` (`Interest(source="inferred")`
     only, minus anything already explicit — no double-counting an entity that's both).
     `ReasoningResult` (`logan_core/contracts/reasoning.py`) gains both as new, additive, default-empty fields;
     existing readers of `connected_entities` (unchanged, still the union of both) are unaffected.
     `OpportunityEngine.evaluate()`'s "connect" step (`logan_core/opportunity/engine.py`) keeps the original
     0.6 `personal_relevance` bump for an explicit connection unchanged, and bounds an inferred-only connection
     to 0.5 — reusing this file's own existing "informational" actionability anchor rather than inventing a
     new constant, deliberately less than the explicit bump, never equal. Both `ReasoningEngine` and
     `OpportunityEngine` log the explicit/inferred split into their `DecisionTraceEntry.evidence`, so a future
     Watch decision's reasoning is auditable back to which kind of connection drove it. This is the guard that
     makes it safe to ever write `Interest(source="inferred")` at all without moving Watch eligibility as an
     unreviewed side effect.
  2. **Behavioral evidence folded into `UserModel`.** `UserModelBuilder.build()` (`logan_core/user_model/model.py`)
     now also groups `feedback_record` memory records by `(domain, entity_id)` and, only for pairs with at
     least `MIN_REPEAT_EVIDENCE = 2` independent `inferred_intent == "interested"` records (the strongest
     positive signal `FeedbackEngine` produces — one occurrence is by definition not a pattern), writes an
     `established_behaviors` entry, an active `DomainPref` (new entries use `weight=0.5`, the same
     neutral/default value `UserModelBuilder.seed()` has always used for a domain preference — not a new or
     invented number), and an `Interest(source="inferred")`. `BehaviorPattern.confidence` and the inferred
     `Interest.weight` both reuse the max `intent_confidence` `FeedbackEngine.interpret()` already computed for
     that pair's qualifying records — no separate confidence model. An entity already covered by an explicit
     holding or explicit interest never gets a competing inferred `Interest` (though it still accrues an
     `established_behaviors` entry — the behavior-pattern record and the interest-priority decision are
     separate). `inferred_expertise` is deliberately left untouched: view/click/dwell evidences attention, not
     demonstrated expertise. Explicit `holdings`/`interests`/`risk_tolerance` are unchanged from `base` either
     way — `.build()` already had this property before this pass; behavioral folding only ever adds to the
     inferred/behavioral portions of the model.
  3. **Orchestrator ownership restored, `run_feedback_loop()` extended.** The interrupted pass had had
     `record_interaction()` (`backend/app/logan_feed.py`) call `feedback_engine.interpret()` and
     `learning_engine.process_feedback()` directly, bypassing `Orchestrator.run_feedback_loop()` — a real
     regression against ADR-047's own stated invariant ("`record_interaction()` only calls the existing
     `Orchestrator.run_feedback_loop()`, never writes to `MemoryStore` or `UserModel` directly"), done because
     `run_feedback_loop()`'s `content: str` parameter had to be supplied before the method's internal
     `interpret()` call, so a caller couldn't build content from `interpret()`'s own `inferred_intent`/
     `intent_confidence` output without interpreting the interaction a second time. Fixed at the root instead
     of routing around it: `run_feedback_loop()`'s `content` parameter (`logan_core/orchestrator/pipeline.py`)
     now accepts either a plain value (every existing caller, unchanged) or a callable receiving the
     just-computed `FeedbackSignal`, resolved after `interpret()` runs and before `process_feedback()` is
     called — Orchestrator remains the sole owner of that sequencing, and the interaction is still interpreted
     exactly once. `LearningEngine.process_feedback()`'s `content` parameter type was widened from `str` to
     `object` to match `MemoryRecord.content`/`MemoryWrite.content`, which were already untyped `object` — a
     type-correctness fix, not a behavior change. `record_interaction()` now passes a small closure that builds
     `{interaction_type, entity_id, domain, inferred_intent, intent_confidence, duration_ms}` from the
     `FeedbackSignal`, through `Orchestrator.run_feedback_loop()`.
  4. **Process-lifetime `UserModel` persistence.** `backend/app/logan_feed.py` gains `_get_user_model()`,
     mirroring the existing `_get_orchestrator()` singleton pattern (same in-memory-only, single-process
     limitation — a backend restart resets it, same as the Orchestrator and baseline tracking). Seeded once
     with the founder's explicit holdings/interests exactly as before; every later `_run_feed_pipeline()` call
     instead rebuilds it via `UserModelBuilder.build()` against the full accumulated `feedback_record` history
     in the shared Orchestrator's `MemoryStore` (`memory_store.query()` with no filters — correct for this
     pass's single-user `LOCAL_FOUNDER_USER_ID` scope; `MemoryStore` has no `user_id` filter to begin with).
     This is the piece that makes repeated card-open/dwell/notification-tap evidence recorded between requests
     actually compound instead of being discarded on the next request's reseed. `reset_pipeline_state()`
     clears the persisted model alongside the Orchestrator and baseline tracking, for test isolation.
     `Orchestrator.run()`'s own pre-existing internal `user_model_builder.build()` call (narrow, per-entity,
     scoped to that entity's own `memory_store.query(entities=[...])` records) is unrelated and untouched —
     its result was already discarded by `_run_feed_pipeline()` before this pass and still is.
  5. Explicitly out of scope, unchanged: Watch alert/interruption thresholds, Personal/Exceptional Watch
     routes, impression/exposure semantics, FIELD BIAS learning, Ask STRATUS linkage, any new ML, trigger/signal
     expansion, Attention Field work. This pass makes the learning *inputs* to a future Watch-personalization
     decision truthful, persistent, source-aware, and auditable — it does not make that decision itself.
- Consequences: `backend`/`logan_core` test count 244 → 264. New/updated coverage: `logan_core/tests/test_user_model.py`
  (repeated-vs-isolated evidence, `inferred_intent` specificity, no cross-entity/domain leakage, explicit
  holdings/interests preserved, `inferred_expertise` untouched), `logan_core/tests/test_reasoning.py` and
  `logan_core/tests/test_opportunity.py` (explicit connections keep the 0.6 bump, inferred-only connections are
  bounded to 0.5, an entity that's both counts only as explicit), `logan_core/tests/test_feedback_learning.py`
  (`run_feedback_loop()`'s content-builder path), `backend/tests/test_interactions.py` (orchestrator-ownership
  restored, interpretation happens exactly once, structured content carries real `inferred_intent`/
  `intent_confidence`), `backend/tests/test_logan_feed.py` (`UserModel` persists and accumulates across
  repeated live pipeline requests, one isolated interaction does not create a preference). mypy/ruff/black
  clean. Mobile untouched by this pass (no mobile files changed) — not re-validated.

## ADR-049: STRATUS Watch eligibility — Personal and Exceptional routes replace the single generic-urgency alert gate
- Date: 2026-08-21
- Status: Accepted
- Context: With ADR-048's behavioral-learning foundation in place (source-aware, persistent, auditable
  personal-relevance signal), the actual Watch alert gate (`PolicyEngine.evaluate()`) still used none of it —
  `communication_mode="alert"` was decided by a single `recommendation.dimensions.urgency >= 0.7` check,
  ignoring `personal_relevance`, `confidence`, `actionability`, and `novelty` entirely. This is the exact
  behavior ADR-046 had already flagged as an open question: "FED still qualifies with `personal_relevance=0.50`
  — the fully generic, unconnected default — confirming personalization is still not required for alert
  eligibility." This ADR closes that question: the owner asked for two explicit eligibility routes answering
  "should STRATUS interrupt this user about this event right now" — Personal (meaningfully relevant to this
  user) and Exceptional (important enough regardless of personalization) — deliberately as route logic, not a
  third blended score, so the reason an alert qualifies stays legible in `DecisionTrace`.
- Inspection findings (verified against the live repo, not assumed from prior traces):
  1. Live path confirmed unchanged: Opportunity → Policy → Prioritization → Presentation
     (`orchestrator/pipeline.py`). `PolicyEngine.evaluate()` receives the full `AttentionRecommendation`
     (all of `Dimensions` plus `internal_rank_score`) already — no input-contract change was needed to
     implement either route inside Policy, which remains the sole communication gate.
  2. Fatigue re-verified still owned entirely by `PrioritizationEngine.AttentionState`, still evaluated after
     Policy runs, exactly as previously found. Re-verifying the *consequence*, not just the ownership: because
     `prioritize()`'s `domain_fatigued` check is evaluated before the `communication_mode == "alert"` check and
     unconditionally forces `interruption="none"` when true, a fatigued domain already vetoes an alert
     regardless of what Policy decided — Prioritization's existing execution order already gives it final,
     correct veto power over interruption fatigue with no reordering, ownership move, or new shared-state
     contract required. The Personal/Exceptional routes were implemented entirely inside Policy without
     touching `prioritization/engine.py` at all.
  3. A second, previously-unnoted instance of the same pattern: `interruption == "alert"` is *also* only
     reachable when `recommendation.internal_rank_score >= 0.6` (Prioritization's own pre-existing "primary
     visibility" bar) — the `internal_rank_score` in `[0.35, 0.6)` "feed" branch only ever produces `"digest"`
     or `"none"`, never `"alert"`, regardless of `communication_mode`. This was already true before this ADR
     (the old single urgency-gate had the identical relationship to it) and is unchanged by this pass; it
     means `communication_mode="alert"` has always been necessary but not sufficient for a real push, and
     still is. See Consequences below for a live example this produces.
  4. A design hazard caught before finalizing thresholds, not merely assumed away: `OpportunityEngine`'s
     "nothing connected, informational" default and its "connected via an inferred interest" bound are the
     *same numeric value* (`personal_relevance = 0.5`, ADR-048) — FED's ADR-046 example is exactly this
     default, not an inferred connection. A naive `personal_relevance >= 0.5` check for an "inferred relevance"
     route condition would therefore have silently let FED-shaped generic-urgency events back in through a
     new door. Fixed by additionally requiring `dims.connection_strength > 0` (already an existing `Dimensions`
     field, `len(reasoning.connected_entities) / 3`) — non-zero only when `reasoning.connected_entities` is
     genuinely non-empty — to distinguish a real inferred connection from the coincidentally-identical generic
     default. Verified against the live simulated fixtures (see Consequences) rather than assumed correct from
     the numbers alone.
- Decision: `logan_core/policy/engine.py` gains a `_watch_route()` helper, called from `evaluate()` only when
  `recommendation.recommend` is already `True` (Opportunity's own bar, unchanged), returning
  `"personal" | "exceptional" | "none"`. `communication_mode = "alert"` iff the route is not `"none"`;
  otherwise `"analysis"` (`"informational"`/`"suppressed"` paths are entirely unchanged). Every threshold
  reuses a value/semantic already established elsewhere in this codebase — no new numeric policy was invented:
  - **Personal, explicit tier**: `personal_relevance >= 0.6` (OpportunityEngine's own "explicit relevance
    bump," ADR-048) **and** `internal_rank_score >= 0.6` (Prioritization's own existing "primary visibility"
    bar, reused here as Policy's "is this actually good enough" signal since it already blends
    urgency/confidence/actionability/novelty/personal_relevance/opportunity_magnitude/connection_strength in
    one number). Verified against live fixtures: `personal_relevance=0.6` alone is not sufficient — MARKETS
    (explicit-tier relevance, but only "peak"-non-actionable urgency=0.5) lands at `internal_rank_score=0.598`,
    just under the bar, and correctly stays `digest`, not `alert`.
  - **Personal, inferred tier**: `personal_relevance >= 0.5` **and** `connection_strength > 0` (the FED-hazard
    guard above) **and** `urgency >= 0.7` (this file's own former single-gate alert threshold) **and**
    `confidence >= 0.55` (`ConclusionConfidenceEngine`'s own "inference" classification bar). Deliberately does
    *not* also require `internal_rank_score >= 0.6` — verified against a live scenario (two repeated `"watch"`
    interactions on BTC building a real `Interest(source="inferred")`) that requiring both made this tier
    practically unreachable even when genuinely well-evidenced, since inferred relevance never carries the
    actionable/explicit-connect boost that makes the explicit tier's blend easy to clear. The tier's own four
    conditions are its "meaningful combination"; explicit remains structurally stronger because it needs only
    two conditions (relevance + the holistic rank bar) where inferred needs four independently-checked ones.
  - **Exceptional**: `urgency >= 0.8` (`opportunity/engine.py`'s own `_LIFECYCLE_URGENCY["emerging"]`) **and**
    `confidence >= 0.7` **and** `novelty >= 0.7` (both reusing the same "high" bar this file already uses for
    `BOT_RISK_SUPPRESSION_THRESHOLD` and previously used for the old urgency-only gate; `novelty >= 0.7`
    corresponds to `opportunity/engine.py`'s `_STANCE_NOVELTY` "contradicts" stance or higher) — all three
    required simultaneously, with zero personal-relevance credit. Checked only after Personal fails to
    qualify; if Personal already qualifies it wins outright, Exceptional is not a second, easier path.
  - `DecisionTraceEntry.rule` now reads `communication_mode=...; watch_route=personal|exceptional|none;
    rules_applied=[...]`, and `.evidence` carries `personal_relevance`, `urgency`, `confidence`, `novelty`,
    `connection_strength` (all rounded to 2 decimals) for every Policy decision, permitted or not.
    `internal_rank_score` is deliberately excluded from `.evidence` — it is ADR-029's INTERNAL-ONLY field
    (never returned via any public API response), and `DecisionTraceEntry.evidence` is serialized as part of
    the full pipeline result; including it broke `test_tesla_demo_response_has_no_internal_score_fields`
    during this pass's own validation and was removed before finalizing, not shipped and fixed later.
  - Explicitly unchanged: `PolicyEngine` remains the sole communication gate (no new scoring subsystem);
    `PrioritizationEngine`'s fatigue/cooldown/visibility/rank-score logic is untouched; digest/background
    behavior for non-alert items is untouched; notification dispatch still gates solely on
    `interruption == "alert"` (`get_alert_eligible_items()`, unchanged); `_fold_behavioral_evidence()`'s
    `MIN_REPEAT_EVIDENCE=2` and `DomainPref(weight=0.5)` (ADR-048) are untouched; no Watch Personal/Exceptional
    "route" concept exists anywhere except this Policy-layer decision — no new UserModel field, no new
    contract, no mobile/UI change.
- Consequences: live deterministic trace against the real simulated fixtures (11 entities, explicit seed:
  NVDA holding + AI_SECTOR interest), captured before/after a two-repeat "watch" interaction on BTC:

  | entity | personal_relevance | urgency | confidence | novelty | conn_strength | rank | route | interruption |
  |---|---|---|---|---|---|---|---|---|---|
  | NVDA (direct holding) | 1.00 | 1.00 | 0.73 | 1.00 | 0.67 | 0.908 | personal | alert |
  | AI_SECTOR (explicit interest) | 0.60 | 0.80 | 0.59 | 1.00 | 0.67 | 0.620 | personal | alert |
  | TSLA (downstream to explicit) | 0.60 | 0.80 | 0.81 | 1.00 | 0.67 | 0.688 | personal | alert |
  | FED (unconnected, ADR-046 case) | 0.50 | 0.80 | 0.73 | 1.00 | 0.00 | 0.624 | exceptional | alert |
  | AAPL (unconnected) | 0.50 | 0.80 | 0.73 | 1.00 | 0.00 | 0.622 | exceptional | alert |
  | MARKETS (explicit-tier relevance, weak urgency) | 0.60 | 0.50 | 0.73 | 1.00 | 0.33 | 0.598 | none | digest |
  | OIL/BTC/NFL/MUSIC/POLY (unconnected, ordinary) | 0.50 | ≤0.80 | ≤0.73 | 1.00 | 0.00 | ≤0.581 | none | digest |
  | BTC after 2× "watch" (mature inferred) | 0.50 | 0.80 | 0.59 | — | 0.33 | 0.585 | personal | digest |

  The BTC row is the clearest live proof both halves of this ADR work correctly: (1) the inferred `Interest`
  built up by ADR-048's behavioral-learning path is what flips `communication_mode` from `"analysis"` to
  `"alert"` for an event that would otherwise have qualified for neither route — genuine evidence "inferred
  relevance contributes" — and (2) `interruption` still stays `"digest"`, not `"alert"`, because
  Prioritization's separate, pre-existing `internal_rank_score >= 0.6` bar (inspection finding 3 above) is not
  met — an honest, verified limit of what this pass changes, not a bug. `backend`/`logan_core` test count
  264 → 279 (15 new tests, `logan_core/tests/test_policy.py`): explicit/inferred tier qualification and their
  A/B asymmetry, the FED-shaped connection_strength guard, low-confidence/low-urgency non-qualification,
  routine-event non-qualification, Exceptional's three-way requirement and its independence from personal
  relevance, Exceptional-vs-Personal difficulty, route visibility in `DecisionTrace`, and
  `recommend=False` short-circuiting unchanged. mypy/ruff/black clean. No mobile files touched — not
  re-validated. No Attention Field, impression/exposure, FIELD BIAS, trigger, or Ask STRATUS work touched.

## ADR-050: Personal-route rank-score authority rule — visibility/interruption decoupled in PrioritizationEngine

- Date: 2026-08-21
- Status: Accepted
- Context: ADR-049's final report flagged an unresolved gap: a Personal-route item (`PolicyEngine`
  `communication_mode="alert"`) could still land as `interruption="digest"` whenever
  `internal_rank_score` fell in `[0.35, 0.6)` ("feed" visibility tier), because `PrioritizationEngine`'s
  `prioritize()` only ever set `interruption="alert"` inside its `internal_rank_score >= 0.6` branch —
  `communication_mode` was read only as a secondary check *within* that branch, never independently. Sprint
  3.6.7's owner asked for an explicit, testable authority rule resolving this: strong mature Personal-route
  relevance should be able to produce a real alert without a blanket bypass of Prioritization, and without
  duplicating fatigue state.
- Decision: `PrioritizationEngine`'s own docstring already states its design principle — "separates visibility
  from interruption" — but the prior implementation nested `interruption` inside the `visibility` branching,
  coupling them. `prioritize()` (`logan_core/prioritization/engine.py`) now computes them independently once
  past the `not permitted`/`in_cooldown`/`domain_fatigued` vetoes (all three unchanged, still evaluated first,
  still fully authoritative): `visibility` remains purely `internal_rank_score`-driven (unchanged thresholds,
  0.6/0.35), governing feed prominence/ordering only; `interruption` is now `"alert"` whenever
  `policy_result.communication_mode == "alert"` (only reachable through one of ADR-049's Personal/Exceptional
  routes — Policy has already applied its own quality gate to reach that decision), `"digest"` for any other
  non-`"informational"` mode, `"none"` for `"informational"`. Because `communication_mode` can only be
  `"alert"`/`"analysis"` when `recommendation.recommend` is already `True` (Opportunity's own
  `internal_rank_score >= RECOMMEND_THRESHOLD` gate), this can never promote a background-tier
  (`rank < 0.35`) item — it only ever affects the previously-stuck "feed" tier (`[0.35, 0.6)`). Fatigue and
  cooldown are evaluated before this logic runs at all and are completely unaffected — "do not simply bypass
  prioritization everywhere" is satisfied by construction, not by a special case. No duplicate fatigue state
  was introduced; `AttentionState` ownership is unchanged.
- Consequences: the ADR-049 BTC live-trace case (mature inferred relevance, `internal_rank_score=0.585`) now
  produces `interruption="alert"`, not `"digest"` — verified in `logan_core/tests/test_pipeline_market_data.py`
  and directly in `test_prioritization.py`. 5 new tests
  (`test_alert_communication_mode_interrupts_even_at_feed_tier_rank`,
  `..._interrupts_at_primary_tier_rank_too`, `test_analysis_communication_mode_never_interrupts_regardless_of_rank`
  — the converse direction: high rank alone still never forces an alert — `test_domain_fatigue_still_overrides_alert_communication_mode`,
  `test_cooldown_still_overrides_alert_communication_mode`). All pre-existing `test_prioritization.py`/
  `test_policy.py` tests pass unmodified (they fix `internal_rank_score` at values where the old and new logic
  agree). `backend`/`logan_core` test count 279 → 284 within this change; see ADR-051 for the cumulative
  Sprint 3.6.7 total. mypy/ruff/black clean.

## ADR-051: Sprint 3.6.7 Block 1 — generalized multi-signal stock trigger architecture (price-move, analyst upgrade/downgrade)

- Date: 2026-08-21
- Status: Accepted
- Context: Sprint 3.6.6 proved one real vertical slice — NVIDIA earnings → `STOCK_EARNINGS_BEAT`/`MISS`/
  `IN_LINE` → the unmodified `logan_core` pipeline → a real opportunity (ADR-042/043/044/045). The owner asked
  Sprint 3.6.7 to generalize that architecture so new stock signal types plug in rather than becoming one-off
  implementations, and to implement a meaningful first expansion pack against real provider data, without
  breaking the existing earnings path, contracts, or Watch behavior.
- Inspection findings before writing code:
  1. `logan_core/normalization/normalize.py`'s `SIGNAL_TYPE_REGISTRY["stocks"]` already listed `price_change`
     and `analyst_change` (alongside `earnings_signal`) — anticipated in the original contract design but
     never implemented. No normalization contract change was needed for either new signal type.
  2. Live FMP endpoint recon (using the existing local `FMP_API_KEY`, same key already used for earnings)
     found `/stable/quote` (real-time price/change/previous-close) and `/stable/grades` (real per-firm rating
     actions with a pre-classified `action` field: upgrade/downgrade/maintain/initiate) both fully accessible
     on the current plan. `/stable/grades-consensus`, `/stable/price-target-summary`, and
     `/stable/analyst-estimates` were also reachable but offer only aggregated/forward-looking data, not
     verified against any registered trigger's fire condition.
  3. `TRIGGER_REGISTRY_STOCKS.md` already fully specifies `STOCK_PRICE_MOVE_SIGNIFICANT` (fire:
     `abs(price_change_pct) >= 5.0`, confidence `+0.10`) and `STOCK_ANALYST_UPGRADE`/`STOCK_ANALYST_DOWNGRADE`
     (fire: rating change in positive/negative direction, confidence `+0.08` each) — real, pre-defined
     constants requiring no new number to be invented, directly satisfying both the `/quote` and `/grades`
     data actually available.
  4. `STOCK_GUIDANCE_RAISED`/`LOWERED` and `STOCK_OPTIONS_FLOW_SURGE` remain SPECIFIED — NOT IMPLEMENTED,
     consistent with ADR-045's prior finding: FMP's stable-tier endpoints supply no forward-guidance or
     options-flow data. "Unusual volume" and "volatility spike" were considered and explicitly rejected for
     this pass: `/quote` carries no average-volume baseline (`volume_vs_avg` from the registry's own
     `STOCK_PRICE_MOVE_SIGNIFICANT` context example is not computable), and — more importantly — neither has
     its own registered trigger code with a registry-defined `confidence_contribution` at all; implementing
     either would mean inventing an unbacked confidence number, which Sprint 3.6.6D's standing rule ("reuse
     only registry-defined constants, never invent new ones") forbids. Not fabricated, not silently skipped —
     documented here as deferred.
  5. `WorldModel.process()`'s dedup key is `(entity_id, signal_type)` (`world_model/model.py`, unchanged) —
     *different* signal_types for the *same* entity within one `Orchestrator.run(raw_signals=[...])` call are
     **not** merged into one `EnrichedEvent`; each becomes its own event, and only the last-processed
     `raw_signals` entry's resulting event is what that `run()` call actually returns. This means feeding,
     say, NVDA's earnings signal *and* a live NVDA price-move signal in the same request would silently drop
     one of the two from that entity's single-opportunity-per-request result — a real architectural gap, not
     addressed here. See "Deferred" below and the Sprint 3.6.7 Block 2 recommendation in `SESSION_NOTES.md`.
- Decision: generalized the existing per-signal-type architecture (Provider → Receptor → deterministic
  Evaluator, all terminating provider-specific structure at the Provider boundary) across two new signal
  types, reusing every existing contract unchanged:
  - `receptors/providers/base.py` gains `Quote`/`QuoteProvider` and `GradeChange`/`AnalystGradesProvider` —
    same shape/Protocol pattern as `EarningsReport`/`EarningsProvider`. `GradeChange.action` deliberately
    trusts the provider's own upgrade/downgrade/maintain classification rather than re-deriving a direction
    from rating text (`"Hold"` vs. `"Buy"` vs. `"Outperform"`, etc.) — inferring that would require inventing
    a rating-ordinal hierarchy with no authoritative source.
  - `receptors/providers/fmp.py` gains `FmpMarketDataProvider` (`fetch_quote`, `fetch_latest_grade_change`) —
    a **separate** class from `FmpEarningsProvider`, not a merge, so that proven, live-verified class is
    untouched. Unlike `EarningsReport`'s legitimately-sparse fields, a quote's price/previous-close/change_pct
    and a grade's action are expected on every real response entry; missing ones raise `FmpProviderError`
    loudly (malformed-shape signal) rather than degrading to `None` (an earnings-specific "no data yet"
    convention that doesn't apply here).
  - `receptors/providers/fixture.py` gains `FixtureMarketDataProvider` plus six deterministic fixtures
    (price-move up/down/none, analyst upgrade/downgrade/maintain) — same non-live-data discipline as
    `FixtureEarningsProvider` (`FIXTURE_SOURCE_ID`/`NAME`).
  - `receptors/stocks_market_data.py` (new) maps `Quote`→`RawSignal` (`signal_type="price_change"`) and
    `GradeChange`→`RawSignal` (`signal_type="analyst_change"`), mirroring `stocks_earnings.py`'s
    `_truthful_summary` pattern — human-readable text built only from real supplied fields.
  - `trigger_detection/stocks.py`: `StocksTriggerEvaluator.evaluate()` now dispatches by `normalized.signal_type`
    to `_evaluate_earnings` (body unchanged, byte-identical, just extracted into its own method),
    `_evaluate_price_move`, or `_evaluate_analyst_grade` — a new signal type plugs in as one more `elif`
    branch plus a dedicated pure condition function, not a rewrite. New pure functions
    `evaluate_price_move_condition()` and `evaluate_analyst_grade_condition()` mirror the existing
    `evaluate_earnings_*_condition()` functions' "always return a reason, fire or not" contract.
    `STOCK_ANALYST_UPGRADE`/`DOWNGRADE`'s `raw_magnitude` is `1.0` (a categorical rating change has no natural
    numeric magnitude — marks "the qualifying condition fired," not an invented number).
  - Context fields follow the same "only what the provider actually supplied" discipline as earnings:
    `STOCK_PRICE_MOVE_SIGNIFICANT`'s context omits the registry example's `session_open`/`volume_vs_avg`
    (not available); `STOCK_ANALYST_UPGRADE`/`DOWNGRADE`'s context omits `price_target_prior`/`_new` (a
    different, aggregated FMP endpoint, not per-event data).
  - Deliberately deferred, not attempted this pass: wiring either new signal type into
    `backend/app/logan_feed.py`'s config-gated `/v1/opportunities` live path (mirroring how ADR-044 followed
    ADR-043 as a separate, later step for earnings). Doing so correctly for an entity that could have *both*
    a live earnings signal and a live price-move/analyst signal in the same request runs directly into
    inspection finding 5's dedup-key gap — wiring it now would either silently drop a signal or require
    informally half-solving signal convergence, which is Sprint 3.6.7 Block 2's own designated scope, not
    Block 1's.
- Consequences: full pipeline correctness proven two ways per new signal type. (1) Fixture-based integration
  tests (`logan_core/tests/test_pipeline_market_data.py`) prove determinism and, for
  `STOCK_PRICE_MOVE_SIGNIFICANT` specifically, a complete real alert: NVDA holding (explicit Personal-route
  relevance) + a qualifying 7.4% fixture price move → `communication_mode="alert"`, `watch_route=personal`,
  `interruption="alert"`, exercising ADR-049/050 end-to-end. (2) Live verification
  (`logan_core/live_verification/nvda_market_data.py`, human-run only, never pytest-collected, mirrors
  `nvda_earnings.py`) proves the real `FmpMarketDataProvider` → pipeline path against NVIDIA's actual current
  quote and most recent real analyst action (2026-08-21: change_pct -0.98% — did not fire, correctly; most
  recent grade action "maintain" from BMO Capital — did not fire, correctly) — an honest, unforced result on
  both counts, exactly matching the earnings script's own "never force an outcome" precedent. New/updated
  tests: `test_trigger_detection.py` (+22: pure condition functions for both new signal types plus
  `StocksTriggerEvaluator` dispatch, including a same-entity cross-signal-type isolation check),
  `test_stocks_market_data_receptor.py` (new, 8 tests), `test_fmp_market_data_provider.py` (new, 15 tests,
  `httpx.MockTransport`-mocked, no real network in the normal suite), `test_pipeline_market_data.py` (new, 6
  tests). Existing earnings tests (`test_trigger_detection.py`'s earnings cases, `test_pipeline_nvda_earnings.py`,
  `test_fmp_provider.py`) pass unmodified — the `_evaluate_earnings` extraction is a pure refactor, not a
  behavior change. `backend`/`logan_core` test count 284 → 330 (including ADR-050's 5). mypy/ruff/black clean.
  No Watch threshold, contract, or existing receptor/API was broken; `/v1/opportunities` and
  `backend/app/logan_feed.py` are completely untouched by this ADR.

## ADR-052: Sprint 3.6.7 Block 2 — signal convergence (STOCK_CONVERGENCE_MULTI_SOURCE) and coherent multi-signal opportunities

- Date: 2026-08-22
- Status: Accepted
- Context: ADR-051 finding 5 identified a real architectural gap: `WorldModel.process()`'s `(entity_id,
  signal_type)` dedup key means multiple *different* live signal types for the same entity within one
  `Orchestrator.run(raw_signals=[...])` call are not merged — each becomes its own `EnrichedEvent`, and only
  the last-processed `raw_signals` entry's resulting event survives into that call's single `PipelineResult`.
  This blocked two things: (1) `TRIGGER_REGISTRY_STOCKS.md`'s own registered `STOCK_CONVERGENCE_MULTI_SOURCE`
  code (confidence `+0.20`, fire condition "≥3 distinct source types emit signals within 30 minutes"), which
  was SPECIFIED — NOT IMPLEMENTED; and (2) wiring Block 1's price-move/analyst-grade live signals into
  `backend/app/logan_feed.py`'s live `/v1/opportunities` path alongside earnings, which ADR-051 deliberately
  deferred rather than half-solve. A PC crash interrupted the first Block 2 attempt at the reconnaissance
  stage; this session restarted clean from `6fe4fdd` and re-derived the same architecture question before
  building anything. Owner decision on approach: **Option 1 — a parallel convergence tracker**, not a widened
  World Model dedup key. Widening World Model's merge key to associate different `signal_type`s for one
  entity into one event was explicitly rejected — it would erase the per-signal-type dedup/corroboration
  semantics `world_model/model.py` already depends on (duplicate-poll suppression, corroboration counting,
  per-trigger_code replace-not-stack) and conflate two unrelated concerns (what the entity graph considers one
  underlying fact per signal source vs. what makes multiple independent sources newsworthy together).
- Decision: World Model's `(entity_id, signal_type)` dedup/corroboration semantics are **left completely
  unmodified** — same file, same behavior, same tests, verified unchanged by running `test_world_model.py`
  unmodified. Two new, additive pieces sit around it instead:
  1. **`StockConvergenceTracker`** (`logan_core/convergence/tracker.py`, new) — a persistent, process-lifetime
     component (constructed once and reused across polls, exactly like `WorldModel`/`Orchestrator` already
     are) that watches the same `TriggerEvent`s trigger detection already produces and independently tracks,
     per entity, which distinct `signal_type`s have fired a qualifying trigger within a 30-minute window
     (windowed on `detected_timestamp` — real evaluation-time "now" — not `event_timestamp`/`captured_at`,
     since an earnings report's date, a quote's real-time timestamp, and an analyst action's date are
     independently sourced and routinely diverge by far more than 30 minutes even when all three are detected
     as live opportunities in the same poll; "fire ... within a 30-minute window" is read as "detected
     together," matching a live-polling system). When ≥3 distinct signal_types are active, it returns a
     `STOCK_CONVERGENCE_MULTI_SOURCE` `TriggerEvent` carrying real, computed provenance (`source_count`,
     `sources`, `contributing_trigger_codes`, and the union of every contributing signal's
     `originating_signal_ids`) — never a fabricated `convergence_strength` field the registry's own example
     shows but this implementation has no honest formula for (same "never fabricate an unsupplied field"
     discipline as every other trigger evaluator in this codebase). An active episode (the same qualifying
     signal_type combination, observed again before it ages out) reuses the same `trigger_id`/`event_timestamp`
     rather than minting a new one every poll — the mechanism for "prevent repeated convergence alerts for the
     same active episode." A signal_type aging out of the window (or the qualifying combination genuinely
     changing) clears the active episode, so a later re-convergence is correctly treated as new. Because
     distinct source types are tracked as a *set*, not a counter, repeated polling of one already-observed
     signal_type can never manufacture a second or third "distinct" source on its own — the mechanism for
     "prevent repeated polling ... from falsely satisfying convergence."
  2. **Coherent-opportunity merge** (`logan_core/orchestrator/pipeline.py`, new module-level
     `_collapse_duplicate_event_ids`/`_merge_entity_events`/`_attach_trigger` helpers, called from
     `Orchestrator.run()`) — fixes the actual "silently drops all but one" bug at its root cause, one layer
     above World Model. Every raw_signal's own resulting `EnrichedEvent` is now kept during the loop instead of
     only the last one; after the loop, same-`event_id` repeats (World Model's own same-signal_type
     corroboration, e.g. TSLA's two-signal fixture) collapse to the single up-to-date version each already
     represented — an exact reproduction of the old single-`event`-variable behavior — and only then are
     genuinely distinct signal_type events unioned (entities/signal_ids/supporting/downstream/trigger_events)
     into one coherent per-entity opportunity. A deliberate no-op whenever only one distinct event exists
     (return `events[0]` unchanged), so every pre-Block-2 caller/test is byte-for-byte unaffected — verified by
     running the full pre-existing suite unmodified. `StockConvergenceTracker`'s output (if any) is attached
     onto the resulting coherent event via the same replace-by-`trigger_code` discipline `WorldModel.process()`
     already uses for duplicate triggers, not appended/stacked. `is_new`/`occurred_at`/`summary`/`event_id` are
     taken only from the primary (first-processed) signal, never OR'd/combined across siblings — deliberately,
     since a merged opportunity being "new" should track its primary signal's own dedup state, not become true
     merely because one of several converging signal_types happened to be new this particular poll.
  3. **`PipelineDependencies.convergence_tracker`** (new field, `Optional[StockConvergenceTracker] = None`) —
     same opt-in gating discipline as `trigger_detector`: every existing caller that doesn't wire one in gets
     identical behavior (no `"convergence_tracker"` `ExecutionTrace` layer, no `STOCK_CONVERGENCE_MULTI_SOURCE`
     ever attached).
  4. **Live wiring** (`backend/app/logan_feed.py`) — `_get_orchestrator()` now constructs a
     `StockConvergenceTracker` alongside the existing `StocksTriggerEvaluator` under the same
     `STRATUS_LIVE_NVDA_EARNINGS` flag (reused, not a new flag — this is still "is live NVDA data enabled,"
     now covering three signal types instead of one). Two new functions,
     `_live_nvda_price_move_raw_signal`/`_live_nvda_analyst_grade_raw_signal`, fetch Block 1's live
     `FmpMarketDataProvider` quote/grade data the same way `_live_nvda_raw_signal` already does for earnings —
     each independently gated on its own trigger actually firing (a valid provider response is not itself an
     opportunity, same standing rule), and each is *additive* to `raw_signals` rather than a fixture
     replacement (unlike earnings, there is no simulated price-move/analyst-grade fixture for NVDA to replace).
     `_run_feed_pipeline()` now passes all qualifying live NVDA signals (1–3, whatever genuinely fires this
     poll) into one `orchestrator.run()` call, relying on the coherent-opportunity merge above instead of
     silently dropping any of them. A quiet trading day with no rating change still contributes nothing extra —
     never a fabricated non-event, never a fabricated convergence.
- Consequences: `EvidenceTrustEngine`/`ConvergenceDetector` (Sprint 3.6.6D) are completely unmodified —
  `STOCK_CONVERGENCE_MULTI_SOURCE`'s `+0.20` contribution competes on the same "strongest trigger wins, never
  summed" rule as every other trigger on a coherent event; a real live NVDA case with earnings/price/analyst
  all qualifying still resolves its bonus from whichever single trigger has the highest registered
  `confidence_contribution` (currently `STOCK_EARNINGS_BEAT` at `+0.22`), with convergence itself remaining
  fully visible in `trigger_events`/`decision_trace` for auditability — "convergence enriches the opportunity,
  it never replaces the individual signals that produced it." New tests: `test_convergence_tracker.py` (new,
  11 tests — fire condition, window boundary, duplicate/repeated-polling suppression, repeated-active-episode
  suppression, provenance, decision trace), `test_pipeline_convergence.py` (new, 6 tests — coherent-opportunity
  merge, end-to-end convergence firing through the full unmodified downstream pipeline, sub-threshold
  non-firing, cross-call episode stability), `test_live_nvda_market_data.py` (new, 7 tests — live wiring,
  convergence-tracker gating, provider-failure isolation, API contract). One unrelated pre-existing flake
  found and fixed while running the full suite for this change (`test_pipeline_market_data.py`'s
  `test_nvda_significant_price_move_produces_delivered_opportunity`): its fixture's fixed quote timestamp lets
  `EvidenceTrustEngine`'s real-wall-clock recency decay push `internal_rank_score` below the test's own `>=
  0.6` assertion as real time passes, independent of any pipeline behavior — confirmed via `git stash` against
  clean `6fe4fdd` before touching it; re-timestamped to "now" in the test, no production code involved.
  `backend`/`logan_core` test count 330 → 354. mypy/ruff/black clean. No merge to main.

## ADR-053: Sprint 3.6.7 Block 3 — persistent behavioral personalization, exposure/impression semantics, and matured-relevance Watch integration

- Date: 2026-08-22
- Status: Accepted
- Context: ADR-047/048 built real interaction capture (card-open/dwell, notification-tap) reaching `MemoryStore`
  through the existing `Orchestrator.run_feedback_loop()` path, and process-lifetime `UserModel` persistence
  that folds repeated `feedback_record` evidence into `established_behaviors`/`domain_preferences`/inferred
  `Interest`. Both were explicitly scoped as foundations, not the full loop: `UserModel` reset on every backend
  restart (in-memory only), there was no concept of exposure/impression distinct from a card actually being
  opened, `OpportunityEngine`'s inferred-connection relevance was a flat `0.5` regardless of how much evidence
  backed it (no way for "matured" behavioral evidence to matter more than "just qualified"), and no protection
  existed against exposure-without-engagement inflating relevance. The owner asked for a substantial block
  closing this loop end-to-end: real exposure/impression semantics, durable persistence surviving a restart,
  a deterministic (non-LLM) behavioral relevance model with decay/maturity/authority rules and explicit
  feedback-loop protections, and wiring the result through Personal relevance, Prioritization, and STRATUS
  Watch — plus, as one acceptance item inside this block, the Block 2 live-convergence-verification carryover
  (see ADR-054).
- **Persistence authority decision (resolved before implementation, per explicit confirmation):** a new,
  dedicated local SQLite store, not an extension of the historical prototype's `backend/app/memory_engine.py`/
  `logan_memory.db` (different, unrelated schema; `backend/app/` is documented as a historical prototype not
  meant for new pipeline logic) and not a new bespoke file format. `UserModel` itself is never persisted
  directly — it remains derived state, rebuilt from persisted `MemoryRecord`s via the existing
  `UserModelBuilder.build()` pattern on every call, exactly as it already was in-process. Consistent with
  ADR-006 ("continue with SQLite + local dev for Phase 1").
- Decision (by area):
  1. **`MemoryStore` persistence** (`logan_core/memory/store.py`) — gains an optional `db_path` constructor
     parameter. `None` (every pre-Block-3 caller/test) is byte-for-byte the old in-memory-only dict; a real
     path opens a local SQLite file, creates `schema_meta` (a version-gated migration point, stamped at
     `MEMORY_STORE_SCHEMA_VERSION=1` today) and `memory_records` tables, loads every existing row into the
     in-memory dict at construction, and every `write()` both updates the dict and upserts into SQLite.
     Reads (`query()`/`all()`) are unmodified either way — SQLite is a durable write-behind/reload mechanism,
     never a second source of truth queried independently. Bounded-history compaction
     (`MAX_PRUNABLE_RECORDS_PER_USER=2000`) prunes only `feedback_record`/`exposure_record` rows beyond the cap,
     oldest first, per user — `user_statement`/`preference_signal`/`correction_record` are never pruned.
  2. **Exposure/impression semantics** — a real, canonical distinction between generation/serialization
     (already existed), actual exposure, and engagement. `InteractionType`
     (`logan_core/contracts/feedback.py`) gains `"impression"` (a deterministic system fact — this opportunity
     was actually shown/brought into the user's attention, not merely present in an API response — never
     interpreted by `FeedbackEngine`, which is specifically for *ambiguous user behavior*) and `"ask_followup"`
     (a genuine engagement action, interpreted normally at `0.80` confidence — between "remind" (0.75) and
     "save/share/watch" (0.85)). `RecordType` (`contracts/memory.py`) gains `"exposure_record"`, structurally
     separate from `"feedback_record"` so `UserModelBuilder`'s existing evidence-folding (which filters on
     `record_type == "feedback_record"` specifically) can never read an impression as positive engagement
     evidence — impressions alone cannot manufacture relevance, by construction, not by a runtime check.
     `LearningEngine.process_exposure()` (new) writes/updates `exposure_record`s directly, skipping
     `FeedbackEngine.interpret()` entirely (nothing ambiguous to interpret) — the single Learning-System-writes
     rule (ADR-016/047) is preserved. `Orchestrator.run_exposure_loop()` (new) is the sole entry point, mirroring
     `run_memory_inbox_confirm/reject`'s "skip interpretation, go straight to Learning" shape.
     "IGNORE"/non-engagement is deliberately never inferred from a mere absence of clicks — see the
     exposure-fatigue mechanism below, the only place exposure evidence has any negative effect at all, and
     even then only a weak, bounded one on an *already-established* interest, never manufactured from nothing.
     `OPEN`/`DWELL` are deliberately *not* split into separate event types — the existing `"view"` interaction
     (ADR-047, fired once at close with the measured `duration_ms`) already atomically captures both; splitting
     it would fragment one correctly-implemented signal the dwell-tracking hook doesn't naturally produce
     separately anyway.
  3. **Idempotency/duplicate protection.** `process_exposure` keeps one lifetime `exposure_record` per
     (user, event) — every later impression updates that same record's `impression_count`/`last_seen_at`
     rather than inserting a new row (naturally bounded storage; no "is this the same occasion" question for a
     plain running counter). `process_feedback` gained a new short-window (`FEEDBACK_DEDUP_WINDOW=5min`)
     duplicate check on `(user, event, interaction_type)` — a network retry or UI double-invoke within 5
     minutes updates the existing record rather than creating a second one; a genuinely later session (the
     actual case `MIN_REPEAT_EVIDENCE` is meant to detect) is far outside that window and still counts as new
     evidence. Fixed a related pre-existing correctness gap while wiring this: `process_feedback` computed its
     own `datetime.now()` a second time instead of reusing `FeedbackEngine.interpret()`'s already-computed
     `feedback.observed_at` — now reuses it (identical behavior in production, since these run synchronously
     back-to-back; makes the dedup window genuinely testable via `observed_at` instead of real wall-clock time).
  4. **Behavioral relevance model** (`logan_core/user_model/model.py`) — deterministic, not LLM-driven, built
     entirely from real evidence timestamps/counts:
     - **Maturity scaling**: an inferred `Interest.weight`/`BehaviorPattern.confidence` is no longer the flat
       `max(intent_confidence)` across qualifying records (pre-Block-3) — it grows by `MATURITY_STEP=0.02` per
       qualifying record beyond `MIN_REPEAT_EVIDENCE`, capped at `MAX_MATURITY_BONUS=0.10` (5 extra events) and
       `MAX_INFERRED_INTEREST_WEIGHT=0.90` overall. Bounded and slow-growing by design — see feedback-loop
       protection below.
     - **Time-based decay**: weighted against each pair's *most recent* qualifying evidence timestamp (not
       "time since this `UserModel` was last rebuilt," which happens on every pipeline poll and would make
       decay meaningless), half-life `BEHAVIORAL_HALF_LIFE_DAYS=14` — deliberately much slower than
       `EvidenceTrustEngine`'s 6-hour `RECENCY_HALF_LIFE_HOURS` (that answers "how stale is this market signal,"
       a faster-moving question than "does the user still care"). Below `DECAY_PRUNE_FLOOR=0.10`, an entry is
       pruned entirely rather than kept as a near-zero clutter record. A pair no longer represented in
       `memory_records` at all (e.g. compacted away) decays separately from its own `last_reinforced`/
       `last_updated` (`_decay_orphaned_entries`).
     - **Exposure-fatigue dampening**: an entity with an *existing* inferred interest, `>=
       EXPOSURE_FATIGUE_THRESHOLD=5` (reusing `PrioritizationEngine.FATIGUE_LIMIT`'s existing precedent, not a
       new number) impressions, whose most recent impression is `>= 1` day after its most recent engagement,
       has that interest dampened by a fixed `EXPOSURE_FATIGUE_PENALTY=0.05`, pruned below the same floor.
       Recency-gated deliberately (not a raw lifetime impression count, which — since `memory_records` is
       always full history — would eventually punish any actively-engaged entity too); never fires for an
       entity with no existing inferred interest at all (unobserved is not the same as ignored — "IGNORE" is
       never inferred from non-engagement alone), never touches explicit holdings/interests.
     - **Provenance**: `BehaviorPattern` gains `evidence_count`/`last_reinforced` (additive, defaulted);
       `UserModel` gains `decision_trace` (additive, defaulted) recording every maturity/decay/fatigue decision
       made on the last `build()` call, in the same `DecisionTraceEntry` shape used everywhere else in this
       pipeline.
     - `UserModelBuilder.build()` gained an optional `now` parameter (defaults to real time; every existing
       caller unaffected) so decay/maturity are deterministically testable against fixture timestamps rather
       than real wall-clock time passing between when a test is written and when it runs — the same lesson
       Sprint 3.6.7 Block 2 already learned the hard way (`test_pipeline_market_data.py`'s flake, ADR-052).
  5. **Feedback-loop protections**, stated explicitly since this is the block's most safety-critical property:
     impressions alone can never create or strengthen a behavior/interest (structural: different `record_type`,
     never read by the folding function that creates them); one burst of activity cannot dominate the profile
     (maturity bonus capped at `+0.10`, weight capped at `0.90`, decay continuously erodes anything not
     genuinely reinforced over time); repeated identical events are deduped, not double-counted
     (`FEEDBACK_DEDUP_WINDOW`); negative evidence is weak and bounded, never fabricated from mere non-engagement
     (exposure fatigue only dampens, only an existing interest, only after a real recency gap, by a small fixed
     step); explicit evidence remains strictly stronger and is never decayed, dampened, or overwritten by
     inferred evidence at any point in this pipeline (unchanged invariant from ADR-048, re-verified here).
     Diversity/no-filter-bubble is a pre-existing *structural* property, not new code: personalization here is
     purely additive relevance credit inside one of eight weighted `Dimensions` (`personal_relevance` at
     weight `0.25` of `~0.98`) — nothing in this pipeline ever suppresses or filters an event for *not*
     matching the user's history, so no combination of behavioral evidence can hide an objectively strong,
     unrelated opportunity.
  6. **Personal relevance now reflects evidence maturity, not just presence.** `ReasoningResult`
     (`contracts/reasoning.py`) gains `inferred_relevance_strength` (additive, default `0.0`) — the strongest
     matched inferred `Interest.weight` among `connected_entities_inferred`, computed in `ReasoningEngine.reason()`.
     `OpportunityEngine`'s "connect" step (`opportunity/engine.py`) replaces the old flat `0.5` floor for an
     inferred-only connection with `_scale_inferred_relevance()`: a linear map from the realistic
     `Interest.weight` range (`[0.75, 0.90]` — `0.75` is `FeedbackEngine`'s weakest "interested" confidence
     tier, `0.90` is `MAX_INFERRED_INTEREST_WEIGHT`, kept in lockstep with `user_model/model.py` by construction)
     onto `[INFERRED_RELEVANCE_FLOOR=0.5, INFERRED_RELEVANCE_CEILING=0.59]` — strictly below the explicit tier's
     `0.6` bump (ADR-048's own invariant, "deliberately less than the explicit bump, never equal"), still
     preserved exactly. `inferred_relevance_strength<=0.75` (including the `0.0` default every pre-Block-3
     caller/test supplies) returns exactly the old flat `0.5` — verified against the exact-value pre-existing
     test assertions before implementing, not discovered after breaking them.
  7. **STRATUS Watch integration is unmodified** — `PolicyEngine._watch_route()`'s Personal-route inferred tier
     (ADR-049) already reads `dims.personal_relevance`/`connection_strength`/`urgency`/`confidence`; because
     `personal_relevance` now genuinely varies with evidence maturity instead of being pinned at `0.5`, mature
     behavioral evidence can now measurably move an event closer to (or, combined with sufficient urgency/
     confidence, into) the inferred Watch tier — without any change to the route's own thresholds, and without
     weakening any existing fatigue/cooldown/`permitted` veto (`PrioritizationEngine`, untouched).
  8. **API/mobile wiring.** `POST /v1/interactions` (already generic over `InteractionType`) required no route
     change; `backend/app/logan_feed.record_interaction()` now special-cases `interaction_type=="impression"` to
     call `run_exposure_loop()` instead of `run_feedback_loop()`. Mobile: `useImpressionTracking.ts` (new)
     fires one `"impression"` interaction whenever `AttentionField.tsx`'s existing `focusedId` state changes to
     a new vessel — a real, honest "brought into the user's attention" signal distinct from both "present in
     `items`" (never itself an impression) and "opened" (`disclosure===1`, already `useCardDwellTracking`'s
     own signal) — reusing existing field-focus state rather than adding new viewport-tracking UI, per the
     block's own "minimal hook for an already-existing action" scope. `"ask_followup"` is implemented as a full
     backend/domain contract (interpreted, persisted, foldable into behavioral evidence) but deliberately not
     wired to the existing `/v1/ask` route, which is a disconnected legacy chat stub unrelated to any specific
     opportunity (predates this pass, reads from the historical `memory_engine`, has no `event_id` concept at
     all) — wiring real Ask-STRATUS-about-this-opportunity linkage remains its own, larger, explicitly deferred
     item (tracked since the Sprint 3.6.6 close-out), not silently done as a side effect here.
  9. **Backend persistence gating.** `memory_persistence_enabled()`/`memory_store_db_path()`
     (`backend/app/config.py`) — `STRATUS_PERSIST_MEMORY` (default disabled) and `STRATUS_STATE_DB_PATH`
     (default `backend/data/stratus_state.db`), following the exact same opt-in, disabled-by-default rollout
     pattern every other capability in this codebase's history uses (`STRATUS_LIVE_NVDA_EARNINGS`,
     `convergence_tracker`) — critically, this keeps the entire pre-existing backend test suite
     (`reset_pipeline_state()`, autouse) isolated to in-memory state; no test run reads or writes the real local
     database file unless it explicitly opts in via the env var, exactly like `test_memory_persistence.py`'s own
     tests do via `STRATUS_STATE_DB_PATH` pointed at an isolated temp file.
- Consequences: acceptance scenario proven end-to-end and covered by an automated test
  (`test_memory_persistence.py::test_matured_behavioral_relevance_survives_a_simulated_restart`): no explicit
  AMD holding, 4 recorded "save" interactions, a simulated backend restart (drops all in-process state, leaves
  the SQLite file untouched), and the inferred AMD interest is still present afterward with a weight that has
  genuinely matured past a single save's own `0.85`. New tests: `test_memory_store_persistence.py` (10),
  `test_learning_exposure.py` (9), `test_user_model_behavioral.py` (16), `test_opportunity.py` (+3),
  `test_feedback_learning.py` (+3), `test_interactions.py` (+6), `test_memory_persistence.py` (4, backend),
  `useImpressionTracking.test.ts` (6, mobile). One pre-existing test (`test_reasoning.py`) updated for the new,
  additive `inferred_relevance_strength` evidence line in its exact-list `decision_trace.evidence` assertion —
  additive, not a behavior regression. `logan_core`/`backend` test count 354 → 405 (mobile 88 → 94). mypy/ruff/
  black clean; `tsc --noEmit`/`eslint` clean. No merge to main. See ADR-054 for the companion live-convergence-
  verification result completed as one acceptance item inside this same block.

## ADR-054: Live verification script for STOCK_CONVERGENCE_MULTI_SOURCE

- Date: 2026-08-22
- Status: Accepted
- Context: Sprint 3.6.7 Block 2 (ADR-052) implemented `STOCK_CONVERGENCE_MULTI_SOURCE` and proved it
  deterministically against fixtures, but — unlike every other stocks trigger code this sprint added — never
  ran it against real FMP data end-to-end. Recommended as Block 2's own closeout follow-up, carried into Block
  3 as one acceptance item.
- Decision: `logan_core/live_verification/nvda_convergence.py` (new), mirroring `nvda_earnings.py`/
  `nvda_market_data.py`'s established pattern exactly (never pytest-collected, human-run only, no CI
  dependency on `FMP_API_KEY`). Fetches all three live NVDA signal types (earnings, price, analyst grade) from
  the real `FmpEarningsProvider`/`FmpMarketDataProvider`, evaluates each through the real, unmodified
  `StocksTriggerEvaluator`, feeds every fired trigger through a real `StockConvergenceTracker`, and reports
  qualification honestly — a `NOT QUALIFIED` result (fewer than 3 of the fetched signals actually fired) is
  printed as the expected, correct outcome on a quiet day, never forced, never fabricated, and the convergence
  threshold/window is never lowered to manufacture a result. Also runs the same signals through the full,
  unmodified `Orchestrator` pipeline (trigger_detector + convergence_tracker wired, exactly as
  `backend/app/logan_feed.py`'s live path does) to prove the resulting coherent opportunity end-to-end
  regardless of whether convergence itself qualifies. Deterministic mocked/fixture coverage for both the
  qualifying and non-qualifying convergence cases already exists and is unchanged
  (`logan_core/tests/test_pipeline_convergence.py`'s `test_three_distinct_signals_fire_convergence_end_to_end`/
  `test_only_two_distinct_signals_does_not_fire_convergence`, Sprint 3.6.7 Block 2) — not duplicated here,
  since this script's own purpose is specifically the *real-data* proof those fixture tests cannot provide.
- Consequences: run live against real FMP data on 2026-08-22 — honest result: earnings fetched (EPS 1.87 vs.
  consensus 1.76, `STOCK_EARNINGS_BEAT` fired), price fetched (change_pct -0.98%, did not fire), analyst grade
  fetched (BMO Capital maintained Outperform, did not fire). Only 1 of 3 signal types fired, so
  `STOCK_CONVERGENCE_MULTI_SOURCE` correctly did **not** qualify — an honest, unforced `NOT QUALIFIED` result,
  not a failure of the mechanism. The full pipeline still produced a real, valid opportunity from the earnings
  signal alone (`communication_mode="alert"`, `interruption="alert"`, `confidence_score=0.595`), proving the
  Block 2 coherent-opportunity/convergence machinery is live-data-correct end to end even on a day convergence
  itself doesn't fire. This is a script-only change; no application code was touched, and no new automated
  test was added (the script itself is deliberately not pytest-collected — see its own docstring).

## ADR-055: Sprint 3.6.7 Block 4 — contextual Ask STRATUS, ASK_FOLLOWUP high-intent behavioral evidence, and deterministic grounded answers

- Date: 2026-08-22
- Status: Accepted
- Context: `ask_followup` was added as a full `InteractionType`/behavioral-evidence path in Sprint 3.6.7 Block 3
  (ADR-053), but deliberately left unwired to any real UI action — the existing `/v1/ask` route
  (`backend/app/main.py`) predates `logan_core` entirely: it reads from the historical `memory_engine`
  (SQLite prototype, unrelated to the real pipeline), has no `event_id`/opportunity concept at all, and answers
  with a static template regardless of what was asked. The owner asked for a real, end-to-end connection: a
  user opens an opportunity, asks STRATUS a grounded contextual question, and that becomes real,
  appropriately-weighted, appropriately-bounded behavioral evidence — without a second chat subsystem, without
  breaking the pre-existing generic Ask STRATUS entry point, and without introducing a real-time NLU/LLM
  dependency this block was not asked to (and, per CLAUDE.md's dependency-addition confirmation rule, could
  not silently) add.
- **No LLM decision (confirmed by inspection, not assumed):** this codebase has never called an LLM anywhere —
  the pre-existing generic `/v1/ask` path is itself a static template/lookup over `memory_engine`, not a model
  call. Adding one now would be a new external dependency requiring its own explicit confirmation (CLAUDE.md's
  collaboration model) — a separate decision, not made here. Instead, Ask STRATUS answers are entirely
  deterministic: real, already-computed pipeline fields (`DeliveredItem`'s narrative text,
  `ConclusionConfidence`'s `classification`/`limiting_factors`/`alternatives`, the entity's attached
  `TriggerEvent`s, `Dimensions.personal_relevance`) matched against the question via keyword classification
  (`backend/app/ask_engine.py`). "Deterministic intelligence first, LLM interpretation second" — there is no
  second stage yet; this *is* the first stage, exposed directly to the user rather than only feeding a
  presentation template.
- Decision (by area):
  1. **Authoritative opportunity rehydration, not client-supplied facts.** The client sends only a stable
     `event_id` (already has it from a real `FeedItem`) — the backend rehydrates real context server-side via
     a new `OpportunityContext` snapshot (`backend/app/ask_context.py`), built from the exact same
     `PipelineResult` that already produced that request's `FeedItem` (not a second, independent computation).
     Populated wholesale into a process-lifetime `OpportunityContextCache` on every `_run_feed_pipeline()` call
     (same singleton pattern as `_orchestrator`/`_user_model`) — same limitation as everything else in that
     tier: a backend restart clears it, and a request for an `event_id` from before a restart gets an honest
     "I don't have current context for that opportunity" answer, never a fabricated one. `OpportunityContext`
     never carries `internal_rank_score` or any other internal-only field (ADR-029 discipline, checked directly
     against the model's field set in tests, not just string-matched in serialized output).
  2. **Contract: extends the existing `/v1/ask` route, not a second endpoint.** `AskRequest`/`AskResponse`
     (`backend/app/models.py`) gain additive, optional fields: `event_id`, `session_id` on the request;
     `event_id`, `session_id`, `grounded` (echoed/computed) on the response. Every existing generic caller
     (omits both) is completely unaffected — verified by the pre-existing behavior now finally having test
     coverage (`test_ask_route.py`; the generic path had zero automated tests before this block). One route
     dispatches on whether `event_id` (or session-continuity-resolved `event_id`) resolves to real context,
     rather than duplicating request/response handling across two endpoints — the "reconcile shared logic"
     instruction, satisfied by there genuinely being very little logic the two paths share (different data
     sources entirely) once the dispatch point is this thin.
  3. **`answer_question()` (`ask_engine.py`)** — ordered, specific-before-generic keyword classification
     (mirroring `policy/engine.py`'s existing `_watch_route` "explicit checked before inferred" precedent)
     routing a question to real fields: what changed → `what_happened`; why now/timing → `why_now`; why it
     matters (generic vs. "to me" specifically, the latter distinguishing explicit-vs-inferred connection basis
     per ADR-048) → `why_it_matters`/`why_it_matters_to_me`; which signals / convergence → real `trigger_codes`
     and, only when genuinely present, `STOCK_CONVERGENCE_MULTI_SOURCE`'s own `context["sources"]` (Sprint
     3.6.7 Block 2) — never implies convergence that didn't fire; confidence / "how sure" →
     `confidence_score`/`label`/`classification` plus real `limiting_factors`; "what would weaken this" →
     `limiting_factors`/`alternatives` verbatim, with an honest "nothing currently limits this" when both are
     empty rather than fabricating a caveat; a comparison question ("stronger than X") names every real
     attached trigger rather than inventing a ranking the pipeline doesn't compute. An unrecognized question
     falls through to a real-data overview (headline + what_happened + why_it_matters + confidence), never a
     fabricated answer.
  4. **ASK_FOLLOWUP wiring, and why it's a separate code path from record_interaction's other branches.**
     `backend/app/logan_feed.record_interaction()`'s existing `interaction_type=="impression"` special case
     (Block 3) is joined by contextual-`/v1/ask`'s own direct call into the same `record_interaction()` for
     `ask_followup` — reusing the identical `FeedbackEngine`-interpreted path every other real `InteractionType`
     already uses (Block 3's `0.80` confidence tier for `ask_followup`, unchanged, not re-derived here). Only
     ever recorded after a real `OpportunityContext` resolves and a real answer is generated — an invalid
     `event_id`, an empty message, or a generic (no-context) question never records engagement.
  5. **Session continuity — structural anchor only, not persisted chat transcripts.** A new, bounded,
     process-lifetime `_ask_sessions` store (`logan_feed.py`, capped at `_ASK_SESSION_LIMIT=500` with
     oldest-first eviction) keyed by a client-generated `session_id`, holding only `event_id` (which
     opportunity this session is discussing — lets a follow-up omit `event_id` and still resolve) and
     `ask_followup_recorded_event_ids` (the session-level cap below) — never raw question/answer text, which
     the deterministic `ask_engine` doesn't need to answer well anyway (each question is independently
     classified against the same real context, not against conversation history). Deliberately **not**
     persisted to SQLite: a single Ask STRATUS conversation is short-lived API/UI convenience state, not
     durable behavioral preference data, and doesn't belong in the same persistence tier as real `UserModel`
     evidence (Block 3's SQLite store) — the documented persistence-boundary fallback the block's own scope
     explicitly allowed ("session-local contextual continuity... document the persistence boundary").
  6. **Feedback-loop protection: at most one `ASK_FOLLOWUP` contribution per (session, opportunity).**
     `should_record_ask_followup()` checks/marks a session's `ask_followup_recorded_event_ids` set — repeated
     follow-up questions about the same opportunity in one session still get a real, freshly-grounded answer
     every time, but contribute behavioral evidence only once. This sits *on top of*, not instead of,
     `LearningEngine`'s pre-existing Block 3 short-window (`FEEDBACK_DEDUP_WINDOW=5min`) dedup, which is
     itself session-agnostic (a genuine duplicate/retry within 5 minutes is a duplicate regardless of which
     client session sent it) — verified as the correct, unmodified interaction between the two mechanisms, not
     assumed (`test_close_in_time_sessions_still_share_the_pre_existing_short_window_dedup`). No new weight/cap
     constants were invented beyond this session-scoped ceiling — `ask_followup`'s `0.80` confidence tier and
     every maturity/decay/exposure-fatigue rule from Block 3 apply completely unmodified once evidence reaches
     `UserModelBuilder`.
  7. **Mobile: minimal per-card entry point, not a redesign.** `Vessel.tsx` gains one bordered pill button
     ("Ask STRATUS about this," styled identically to `ask.tsx`'s own existing `starterRow` pattern) inside the
     already-expanded card, navigating to `/ask` with `eventId`/`entityId`/`displayName`/`domain` as Expo
     Router params — a new pattern for this app (no prior screen took params), but a standard, well-supported
     one. `ask.tsx` reads them via `useLocalSearchParams`, generates one `sessionId` per screen visit
     (`lib/ask.ts`'s `createAskSessionId`, not a real UUID — no such dependency exists in this app, just unique
     enough to key the server-side session map), shows a small honest "Discussing {entity}" chip only when a
     real `eventId` param was actually passed (never claims a connection the screen doesn't have), and swaps
     the first-state headline/starter prompts for opportunity-specific ones. The pre-existing generic entry
     point (drawer menu → `/ask` with no params) is completely unaffected — same screen, same route, contextual
     mode is purely additive based on whether params are present.
- Consequences: acceptance scenario proven end-to-end and covered by an automated test
  (`test_ask_route.py::test_matured_ask_followup_evidence_survives_restart_and_raises_relevance` — AAPL stands
  in for the task description's "AMD," since AMD isn't a real simulated-fixture entity in this codebase; AAPL
  is, and carries no explicit holding/interest in the seeded `UserModel`, matching the scenario's actual
  requirement): a user opens an opportunity with no explicit holding, asks real contextual follow-ups across
  several independent sessions, a simulated backend restart occurs, and the inferred relevance is still present
  afterward with a weight genuinely matured past a single `ask_followup`'s own `0.80`. New tests:
  `test_ask_engine.py` (17, deterministic classification, including "never mentions internal_rank_score" across
  every question category), `test_ask_context.py` (6, rehydration/cache), `test_ask_route.py` (18, full HTTP
  integration — generic-path regression coverage the pre-existing route never had, contextual grounding,
  invalid-opportunity/empty-message never recording engagement, session continuity, idempotency, the session
  cap, restart persistence, and a Watch-fatigue-untouched regression guard), `ask.test.ts` (6, mobile client).
  `logan_core`/`backend` test count 405 → 446 (+41). mobile test count 94 → 100 (+6). mypy/ruff/black clean;
  `tsc --noEmit`/`eslint` clean. No merge to main.

## ADR-056: Sprint 3.6.8 Block 1 — grounded LLM Ask STRATUS, provider abstraction, and deterministic fallback

- Date: 2026-08-22
- Status: Accepted
- Context: Sprint 3.6.7 Block 4 (ADR-055) gave Ask STRATUS a fully deterministic answer engine
  (`answer_question()`) over real, already-computed `OpportunityContext` fields — explicitly the first stage of
  "deterministic intelligence first, LLM interpretation second," with no second stage built yet. This block
  builds that second stage: an optional, config-gated LLM composition layer over the exact same authoritative
  context, never a replacement for it. Confirmed by inspection: no LLM call existed anywhere in this codebase
  before this block (`backend/`, `logan_core/`, `mobile/` all searched) — this is a genuine new external
  dependency and a genuine new secret, both requiring explicit owner confirmation under CLAUDE.md's
  collaboration model, and both were obtained before any implementation code was written (see Decision 1
  below).
- Decision (by area):
  1. **Vendor and model, owner-approved.** Official `anthropic` Python SDK (`backend/requirements.txt`,
     `anthropic>=1.0`), not raw REST — mirrors this codebase's existing discipline of using vetted
     provider libraries rather than hand-rolled HTTP where one exists. Model `claude-sonnet-5`, the owner's
     explicit choice over the higher-reasoning-tier default, on cost/latency grounds appropriate to this task
     (a short, few-sentence composition over data the pipeline already computed, not open-ended reasoning) —
     `DEFAULT_EFFORT="low"` in `ask_llm_anthropic.py` reflects the same judgment. `ANTHROPIC_API_KEY`
     owner-approved as a new local-dev secret (`backend/.env`, gitignored, never in source control) — not
     populated with a real value by this block; the live LLM path stays inert (falls back to deterministic,
     see Decision 4) until the owner adds their own key locally.
  2. **Vendor-agnostic provider abstraction, mirroring `receptors/providers/{base,fmp,fixture}.py`'s
     established pattern.** `AskLlmProvider` (`ask_llm_provider.py`) is a `Protocol` —
     `generate(context: OpportunityContext, question: str) -> AskLlmAnswer` — the only surface
     `ask_engine.py`'s orchestration ever sees. `AnthropicAskLlmProvider` (`ask_llm_anthropic.py`) is the one
     file in this codebase that imports the `anthropic` package or knows any Anthropic-specific type
     (`APITimeoutError`, `RateLimitError`, `stop_reason`, `stop_details.category`, response `.content` blocks)
     — every one of those is caught/mapped to the single domain error type, `AskLlmProviderError`, at the
     boundary. `FixtureAskLlmProvider` (`ask_llm_fixture.py`) is the deterministic test double (configured
     with either a canned `answer` or a canned `error`, records every call for assertion) — no test in this
     block's suite makes a real network call. Swapping vendors later means writing one new provider class, not
     touching `ask_engine.py`, `main.py`, or any test that isn't provider-specific.
  3. **Structured grounding: the model never sees anything but `OpportunityContext`, and is told not to invent
     beyond it.** `build_system_prompt()` (`ask_llm_provider.py`, vendor-agnostic — used by
     `AnthropicAskLlmProvider` but doesn't import `anthropic`) renders the same authoritative fields
     Block 4's deterministic engine already uses (headline, what happened, why it matters / why it matters to
     this user, why now, confidence score/label/classification, limiting factors, alternatives, real
     `trigger_codes`, and — only when `convergence_sources` is genuinely non-empty — real convergence sources;
     otherwise the prompt says plainly the opportunity "is not currently converging across sources," never
     implying a convergence that didn't fire, same discipline as `answer_question()`'s own comparison-question
     branch). The prompt explicitly instructs the model not to invent additional market facts, prices,
     earnings values, analyst actions, or confidence values, and not to contradict the given classification —
     STRATUS computes and scores; the model only composes prose over what STRATUS already concluded. The
     prompt also restates the ADR-002/010 advice boundary in the model's own instructions ("do not give
     financial or betting advice — do not tell the user to buy, sell, or bet on anything") — a second,
     independent enforcement point, not reliance on the model happening to already behave that way.
  4. **Deterministic fallback is the caller's responsibility, not the provider's.** `AskLlmProviderError` is
     never caught inside a provider implementation — `generate_grounded_answer()` (`ask_engine.py`, new,
     alongside the unchanged Block 4 `answer_question()`) is the single place that decides what happens on
     failure: `provider is None` (disabled or unavailable) or a raised `AskLlmProviderError` (network, timeout,
     rate limit, non-2xx, refusal, empty/malformed response) both fall through to the exact same
     `answer_question(context, message)` call Block 4 already had — never a partial answer, never an error
     surfaced to the user, never a broken Ask STRATUS experience. `GroundedAnswer.used_llm` records which path
     actually produced the text (for `AskResponse.grounded`, which already existed pre-Block-1 as "did a real
     answer get produced" — unchanged meaning, LLM vs. deterministic is an internal implementation detail the
     public contract doesn't need to expose, so `AskRequest`/`AskResponse` in `models.py` are untouched by this
     block).
  5. **Config gating, matching every other capability's rollout pattern in this codebase.**
     `config.llm_ask_enabled()` reads `STRATUS_LLM_ASK` via the existing `_env_flag()` helper — defaults to
     disabled, same as `STRATUS_LIVE_NVDA_EARNINGS` (ADR-046-adjacent) and `STRATUS_PERSIST_MEMORY` (ADR-053).
     `get_ask_llm_provider()` (`ask_engine.py`) is the single lazy, thread-safe (`threading.Lock`), memoized
     construction point: disabled → `None` without ever importing `ask_llm_anthropic` or constructing a real
     client; enabled but no API key or construction failure → catches `AskLlmProviderError` from the
     constructor, logs once, returns `None` — same "attempt, never crash" discipline as the runtime failure
     path. `reset_ask_llm_provider()` exists solely for test isolation (mirrors the existing
     `reset_pipeline_state()` pattern), not called from any production path.
  6. **Prompt-injection hygiene is structural, not instructional-only.** The user's question is never
     concatenated into the system prompt string at all — `AnthropicAskLlmProvider.generate()` sends it as a
     wholly separate `messages=[{"role": "user", "content": question}]` turn
     (`test_anthropic_provider_sends_question_as_separate_user_message_not_system` asserts this directly against
     a captured call, not just against prompt text). The system prompt additionally instructs the model that
     the next message is untrusted end-user input, not an instruction to the model, and that it must not reveal
     the system prompt or change its role in response to anything in it — a second layer on top of the
     structural separation, not a substitute for it.
  7. **Behavioral learning: `ASK_FOLLOWUP` recording is unchanged and decoupled from which path answered.**
     `main.py`'s `ask_logan()` still calls `should_record_ask_followup()`/`record_interaction()` exactly where
     Block 4 left it, now downstream of `generate_grounded_answer()` instead of `answer_question()` directly —
     recording depends only on "did a real `OpportunityContext` resolve and did a real answer get produced,"
     never on whether that answer came from the LLM or the deterministic fallback. Verified directly: an
     LLM-failure-then-fallback question records exactly one `ask_followup` feedback record, not zero (fallback
     still counts as a legitimate answer) and not two (there's no separate "LLM attempt" event) —
     `test_ask_followup_records_exactly_once_on_llm_failure_fallback`. The pre-existing per-(session,
     opportunity) cap (Block 3/4) and the `LearningEngine` short-window dedup both apply completely unmodified.
- Consequences: `backend/app/ask_llm_provider.py` (protocol, `AskLlmAnswer`, `build_system_prompt`),
  `ask_llm_fixture.py` (test double), `ask_llm_anthropic.py` (real provider) are new. `ask_engine.py` gains
  `GroundedAnswer`, `generate_grounded_answer()`, `get_ask_llm_provider()`/`reset_ask_llm_provider()`
  alongside Block 4's unchanged `answer_question()`. `config.py` gains `llm_ask_enabled()`. `main.py`'s
  `ask_logan()` now calls `generate_grounded_answer()` instead of `answer_question()` directly; no other
  route logic changed. `AskRequest`/`AskResponse` (`models.py`) are unchanged — no mobile contract impact,
  no mobile UI change in this block. New tests: `test_ask_llm.py` (38 — fixture provider, system-prompt
  grounding and injection-resistance, `generate_grounded_answer()` orchestration/fallback, config gating,
  `AnthropicAskLlmProvider` error-mapping/refusal/empty-response/success with an injected fake client (no real
  network call anywhere in the file), full `/v1/ask` route integration for LLM success/disabled/
  unavailable/timeout/malformed-response, and `ASK_FOLLOWUP` idempotency under every one of those paths).
  Every pre-existing Block 4 Ask STRATUS test (`test_ask_context.py`, `test_ask_engine.py`, `test_ask_route.py`)
  passes unchanged. `backend` test count 141 → 179 (+38); `logan_core` unaffected (306, untouched by this
  block). mypy/ruff/black clean on every new/changed file (two pre-existing mypy findings in
  `test_ask_engine.py`/`test_ask_route.py`, both predating this block, are unrelated `**dict[str, object]`
  kwargs-unpacking noise from Block 4's own test fixtures — not introduced or worsened here; this block's own
  test fixture follows the identical pre-existing pattern for consistency with those files). No merge to main.
- Deferred / flagged for the owner: `backend/.env` was not given a real `ANTHROPIC_API_KEY` value — this
  block has no real key to insert. `STRATUS_LLM_ASK` defaults off regardless, so the system is fully
  functional and behaves exactly as before this block until the owner both sets `STRATUS_LLM_ASK=true` and
  adds a real key locally; a missing key at that point degrades gracefully to the deterministic path rather
  than erroring (Decision 5).

## ADR-057: Sprint 3.6.8 Block 2 — production user boundaries: real per-request identity, user-scoped MemoryStore reads, and per-user process-lifetime state

- Date: 2026-08-22
- Status: Accepted
- Context: Every layer inside `logan_core` was already built to be multi-user-safe by construction —
  `MemoryRecord.user_id` is required and validated (ADR-033), `Orchestrator.run()`/`run_feedback_loop()`/
  `run_exposure_loop()` all take an explicit `user_id`, and `PrioritizationEngine`'s `AttentionState` was
  already stored in a `dict[user_id, AttentionState]` internally. The actual gap, confirmed by direct
  inspection before writing any code, was concentrated in two places: (1) `backend/app/logan_feed.py` never
  threaded any real per-request identity through — every one of 8 call sites hardcoded
  `user_id=LOCAL_FOUNDER_USER_ID`, and its process-lifetime singletons (`_user_model`, the
  `OpportunityContextCache`, `_ask_sessions`) were single global instances, not per-user; (2)
  `logan_core/orchestrator/pipeline.py`'s `run()` called `self.deps.memory_store.query(entities=...)` with
  **no `user_id` filter at all**, even though `user_id` was in scope two lines below — a genuine, real
  cross-user data leak (any user's `feedback_record`s for a shared entity fed directly into every other
  user's `UserModelBuilder.build()` rebuild), not just a wiring gap. `MemoryStore.query()`/`.all()`
  (`logan_core/memory/store.py`) had no `user_id` parameter at all despite the SQLite schema already having a
  required `user_id` column and index (Sprint 3.6.7 Block 3) — the isolation that column was built for was
  never actually enforced at the read path. `backend/app/notifications.py`'s registered-token/dispatched/
  reviewed-event-id state was also fully global — one user's push-token registration received every alert-
  eligible item regardless of whose personalization produced it, and one user reviewing a notification
  silenced the pending-push badge for everyone. This work explicitly supersedes
  `27_SECURITY_PRIVACY_COMPLIANCE.md`'s prior "auth and multi-user persistence are explicitly excluded from
  V3.1.4 scope" note — a deliberate, owner-directed scope change this sprint, not a silent reversal; that
  document is updated as part of this block's own consequences.
- Two review points raised and resolved before/during implementation, not treated as pre-decided:
  1. **`record_interaction()` ownership.** Reviewed whether this function bypasses `Orchestrator.run_feedback_loop()`/
     `run_exposure_loop()` in favor of calling `feedback_engine.interpret()`/`learning_engine.process_feedback()`
     directly. Confirmed by inspection (both a direct read of the function and a repo-wide grep for those two
     method names outside `orchestrator/pipeline.py`) that no such bypass exists anywhere in this codebase —
     `record_interaction()` has gone through the Orchestrator's content-builder-callable pattern (ADR-047)
     since Sprint 3.6.6, unchanged by this block. `user_id` is now the caller's real resolved identity instead
     of the hardcoded founder constant, but the orchestration path itself is untouched. No code change was
     needed for this point; documented here as reviewed-and-confirmed-clean rather than silently assumed.
  2. **`DomainPref(weight=0.5)`.** Reviewed whether this is an arbitrary invented behavioral weight.
     Confirmed by inspection: `DomainPref.weight` is a required contract field (`contracts/user_model.py`)
     with no documented semantic meaning anywhere in `07_DATA_CONTRACTS.md`/`06_LAYER_INTERFACE_SPECIFICATION.md`,
     and — checked directly, not assumed — **no consumer reads `domain_preferences[].weight` anywhere in
     Reasoning, OpportunityEngine, Policy, or Prioritization today**; it is never updated again after creation
     either (`_fold_behavioral_evidence` only ever flips `active`/`last_updated` on an existing entry). Unlike
     `model_confidence`'s own `0.5` (a documented, evidence-scaled floor with a real formula), this is an inert
     placeholder satisfying a required field, not a computed or reasoned behavioral signal — and it predates
     this block (Sprint 3.6.7 Block 3/ADR-048/053), not something introduced here. Resolution: left the value
     unchanged (removing it would require a contract change — making the field optional — which is out of this
     block's scope and not something to do silently) and added an explicit comment at both construction sites
     (`user_model/model.py`) documenting why it is inert and flagging that a real per-domain weighting design,
     if one is ever needed, is a separate future decision — not invented here.
- Decision (by area):
  1. **Identity transport, owner-approved.** A new `X-Stratus-User-Id` request header
     (`backend/app/user_context.py`'s `resolve_user_id()`, a FastAPI dependency), not authentication — no
     login, no verification of who is actually making a request, explicitly out of this block's scope per the
     owner's own instruction. Absent header → `LOCAL_FOUNDER_USER_ID`, so every existing caller (the mobile
     app sends no such header today) is completely unaffected. Wired into every user-facing route:
     `/v1/opportunities`, `/v1/notifications/review`, `/v1/notifications/register`, `/v1/interactions`,
     `/v1/ask`, and the deprecated `/v1/demo/feed`.
  2. **`MemoryStore.query()`/`.all()` now require `user_id` explicitly, owner-approved — no "all users" mode,
     no default.** Every call site (3 production: `orchestrator/pipeline.py`, `learning/engine.py`,
     `backend/app/logan_feed.py`; ~15 test) was migrated deliberately, not silently defaulted. This closes the
     real cross-user leak described above at its root: `orchestrator/pipeline.py`'s `run()` now passes
     `user_id=user_id` into its `memory_store.query()` call; `learning/engine.py`'s `_recent_record()` now
     calls `memory_store.all(user_id=user_id)` instead of filtering `user_id` in Python after fetching every
     user's records. No SQLite schema change — the `user_id` column and its index already existed
     (Sprint 3.6.7 Block 3); this is a Python interface-contract change only.
  3. **`backend/app/logan_feed.py`'s process-lifetime singletons converted to per-user dicts.** `_user_model`
     → `_user_models: dict[str, UserModel]`; `_opportunity_context_cache` → `_opportunity_context_caches:
     dict[str, OpportunityContextCache]` (closes the sharpest read-side leak: `OpportunityContext` carries
     personalized fields — `personal_relevance`, `connection_basis`, `is_new_for_user` — and a shared cache
     would have let any caller who knew an `event_id` read another user's personalization); `_ask_sessions` →
     keyed by `(user_id, session_id)` tuple, not `session_id` alone (a session_id is client-generated and not
     itself a secret — an unscoped store would let a guessed/predictable session_id from one user read or
     extend another user's Ask STRATUS session). `_baseline_established` was already a `set[user_id]` — no
     structural change, just real values flowing in now. The shared `_orchestrator` instance (one World Model,
     one MemoryStore) is deliberately **not** duplicated per user — two users seeing the identical `event_id`
     for the identical real-world fact (e.g. "NVIDIA beat earnings") is correct: World Model event identity is
     shared world state, not personalization state. What's user-scoped is the `UserModel` folded into each
     `orchestrator.run()` call, `PrioritizationEngine`'s `AttentionState` (already per-user internally, now
     receiving real `user_id`s), and the OpportunityContext/session state above.
  4. **New-user seeding, owner-approved: blank, never copied from the founder.** `_get_user_model()` seeds
     `LOCAL_FOUNDER_USER_ID` alone with the existing NVDA holding/AI_SECTOR interest (unchanged); any other
     `user_id` gets `UserModelBuilder().seed(user_id=user_id)`'s own blank/unknown defaults (no holdings, no
     explicit interests, `risk_tolerance="unknown"`). The founder's specific portfolio is founder-only demo
     data — copying it into every new user would be factually wrong, not a harmless placeholder.
  5. **`backend/app/notifications.py`'s token/dispatch/review state converted to per-`user_id` dicts.**
     `_registered_tokens`, `_dispatched_event_ids`, `_reviewed_pushed_event_ids` are now
     `dict[str, set[...]]`. `dispatch_eligible_notifications()` (the background poller's own function) now
     loops once per `user_id` with at least one registered token, computing that user's own
     `get_alert_eligible_items(user_id)` and dispatching only to that user's own tokens — a real behavior
     change (the poller now runs the full pipeline once per registered user per cycle, not once total), a
     necessary and correct consequence of per-user personalized alert eligibility, and an accepted cost at
     current local-dev scale (flagged, not a blocker). A push-service failure for one user's dispatch no
     longer stops dispatch for any other user (the retry/continue logic is now per-user-scoped).
- Consequences: `backend/app/user_context.py` is new. `backend/app/logan_feed.py`, `main.py`,
  `notifications.py`, `opportunities.py` all changed to thread `user_id` through every route/function.
  `logan_core/memory/store.py`, `orchestrator/pipeline.py`, `learning/engine.py` changed for the `user_id`-
  required `MemoryStore` contract. `logan_core/user_model/model.py` gained two documentation-only comments
  (Review point 2 above) — no behavior change. `AskRequest`/`AskResponse`/`RecordInteractionRequest`/
  `RegisterPushTokenRequest`/`NotificationsReviewRequest` (`models.py`) are **unchanged** — identity travels
  via header, not request body, so there is no mobile contract impact and no mobile UI change in this block.
  New tests: `test_multi_user_isolation.py` (14 — identity-boundary backward compatibility, two distinct
  `user_id`s getting independent UserModels while sharing the same World Model event identity, behavioral-
  evidence isolation, explicit-vs-inferred relevance isolation including the founder-seed-never-copied
  guarantee, Ask STRATUS session/OpportunityContext isolation including a deliberate session-id-collision
  case, ASK_FOLLOWUP recorded under the correct user, Watch notification-review isolation, push-token/
  dispatch/review isolation, and restart-persistence staying correctly user-scoped). Every pre-existing test
  across both `logan_core` and `backend` was migrated to the new required-`user_id` signatures (not skipped
  or weakened) and passes unchanged in intent — including `test_compaction_is_scoped_per_user`
  (`logan_core/tests/test_memory_store_persistence.py`), rewritten to check each user's own `.all(user_id=...)`
  view directly now that a global "all users" read no longer exists, rather than the pattern it used before
  this block. `backend` test count 179 → 193 (+14, `test_multi_user_isolation.py`); `logan_core` unchanged at
  306; combined 485 → 499. mypy/ruff/black clean on every new/changed file — the same 14 pre-existing
  `**dict[str, object]` mypy findings from Block 1 (`test_ask_engine.py`, `test_ask_route.py`,
  `test_ask_llm.py`) are unchanged in count and location, not introduced or worsened by this block. Mobile
  test suite not run — no mobile-facing contract changed. No merge to main; this commit is not pushed pending
  review (per explicit instruction).
- Deferred / flagged for the owner: (1) wiring the mobile app to generate and persist a real per-device
  `user_id` (so `X-Stratus-User-Id` is ever actually sent by a real client) is explicitly not done in this
  block — it would require a new client-side storage dependency (e.g. `expo-secure-store`) that doesn't exist
  in this app today, a separate dependency-addition decision; until then, every real request still resolves
  to the founder default, and the isolation this block proves is exercised only via the header directly (as
  the new tests do), not yet by any real second user. (2) `DomainPref.weight`'s "inert placeholder, no
  consumer" status (review point 2) is now explicitly documented but not resolved — a real per-domain
  weighting design remains a genuinely separate future decision. (3) Push-token/dispatch/review state remains
  in-memory, process-lifetime only per user — a durable, per-user token store surviving a backend restart is
  still an ADR-006-scale decision, unmade. (4) The single process-wide `_state_lock` remains coarse-grained
  (one lock across every user's pipeline runs) — correct, not a regression, but a real scalability limit at
  higher concurrent-user counts; not addressed here per the block's own "no broad observability/performance
  work" scope boundary. (5) `docs/specs/.../27_SECURITY_PRIVACY_COMPLIANCE.md`'s prior "multi-user persistence
  explicitly excluded from V3.1.4 scope" note needs a follow-up edit reflecting this block's real, if partial,
  multi-user isolation work — flagged for the next docs pass, not done as part of this commit's diff.

## ADR-058: Sprint 3.6.8 Block 3 — bounded conversational Ask STRATUS

- Date: 2026-08-23
- Status: Accepted
- Context: Every pre-Block-3 `/v1/ask` call was answered in isolation — the LLM path (ADR-056) sent one
  question against one `OpportunityContext` with no memory of anything asked earlier in the same session,
  so a natural follow-up ("Why?", "Which of those signals is strongest?") had nothing to resolve against and
  fell through to a generic overview. Recon before writing code found the mobile client (`mobile/app/ask.tsx`)
  already renders a real, accumulating multi-turn conversation client-side and already resends the same
  `session_id` on every turn in one screen visit — the gap was entirely server-side: nothing retained prior
  turns to ground a follow-up in, and nothing threaded them into the LLM call.
- Decision (by area):
  1. **Bounded conversation storage, in `backend/app/logan_feed.py`'s existing per-`(user_id, session_id)`
     `_AskSession` (Block 2/ADR-057), not a new store.** Adds `history: list[ConversationTurn]`. Two explicit,
     reasoned bounds, in this codebase's existing small-integer-with-a-reason convention (`FATIGUE_LIMIT=5`,
     `MIN_REPEAT_EVIDENCE=2`), not values tuned against real usage data: `_MAX_ASK_HISTORY_TURNS=6` (question,
     answer) pairs retained (12 messages) — generous enough for the full "why? / why does that matter? /
     which signal? / what would weaken this?" chain the block's own acceptance examples describe, never
     unbounded; `_MAX_ASK_HISTORY_CHARS=4000` — a secondary defensive bound so a handful of unusually long
     turns can't blow past a reasonable prompt-size budget before hitting the turn cap. Eviction is always a
     full `(user, assistant)` pair at once (`_trim_ask_history()`), never a partial pair — required so
     retained history always starts on a "user" turn and strictly alternates, which both `AskLlmProvider`'s
     own contract and Anthropic's Messages API depend on. Session lifetime, eviction, and process-lifetime-
     only persistence are otherwise unchanged from Block 4's original `_AskSession`/`_ASK_SESSION_LIMIT=500`
     design — no durable raw-chat database was introduced, matching the explicit instruction not to add one
     without approval; conversation text remains out of SQLite exactly as it always has been.
  2. **User/session/opportunity boundaries carried forward from Block 2, not re-derived.** `_AskSession` was
     already keyed by `(user_id, session_id)` tuple (ADR-057) — `history` inherits that isolation for free;
     two users reusing the identical `session_id` string get independent histories, and `OpportunityContext`
     resolution stays per-user (a stale/invalid `event_id`, or one that only exists in a different user's
     cache, still never creates or reveals history). **New this block:** opportunity-anchor-change detection.
     `set_ask_session_event()` now clears a session's history whenever its `event_id` changes to a genuinely
     different opportunity — a deliberate, deterministic reset (not a silent carryover), because letting a
     "why?" resolve against a different opportunity's prior exchange would be a real correctness bug, not a
     convenience. Repeatedly resending the *same* `event_id` every turn (exactly what the mobile client
     already does) is correctly a no-op, not a reset.
  3. **Authoritative grounding wins over conversation history — made an explicit, testable invariant, not an
     assumption.** `build_system_prompt()` (`ask_llm_provider.py`, vendor-agnostic) gained new text: current
     `OpportunityContext` always wins over anything implied by an earlier turn, from either party; the model
     must not let its own earlier reply drift the current answer away from it. Structurally reinforced, not
     just asserted: `build_system_prompt(context)` still takes only `context` as an argument — conversation
     history can never be concatenated into the system prompt at all, by construction, regardless of what a
     malicious earlier turn said. History only ever reaches the model as ordinary `user`/`assistant` messages
     (see Decision 5), ranked no differently in trust than the current question.
  4. **No invented signal ranking, made explicit in the prompt.** The deterministic path
     (`answer_question()`'s `_dominant_signal_answer`) already refused to rank contributing signals against
     each other absent a genuine `STOCK_CONVERGENCE_MULTI_SOURCE` firing — unchanged this block. Added the
     equivalent instruction to `build_system_prompt()` for the LLM path: if asked which signal is strongest,
     say the available data doesn't support a definitive ranking unless real convergence fired, rather than
     inventing one. The LLM interprets STRATUS's own deterministic evidence; it does not manufacture new
     comparative intelligence STRATUS itself never computed.
  5. **Provider abstraction evolved additively, not replaced.** New vendor-neutral `ConversationTurn` (role +
     text) in `ask_llm_provider.py`. `AskLlmProvider.generate()` gained a `history: Sequence[ConversationTurn]
     = ()` parameter — defaulted, so every pre-Block-3 caller (a single-turn question) is unaffected.
     `AnthropicAskLlmProvider.generate()` is the only place in this codebase that translates `ConversationTurn`
     into Anthropic's own alternating `{"role", "content"}` message-list shape (`list[anthropic.types.
     MessageParam]`) — no Anthropic SDK type reaches `ask_engine.py`, `logan_feed.py`, or `main.py`.
     `FixtureAskLlmProvider.calls` grew from `(context, question)` 2-tuples to `(context, question, history)`
     3-tuples — the one small, deliberate breaking change to an existing test double, migrated across its 2
     existing call sites in `test_ask_llm.py`.
  6. **Deterministic fallback mid-conversation: the safest policy, reasoned explicitly.**
     `generate_grounded_answer()` gained a `history` parameter but deliberately does **not** pass it to
     `answer_question()` — the deterministic path answers the current question standalone, exactly as it
     always has; teaching it to parse conversational references would be a materially larger, separate
     change, and an honest, non-fabricated single-turn answer on fallback already satisfies the actual
     requirement ("no LLM failure should break the experience"), not "the fallback must also be
     conversationally fluent." Whichever path actually produced an answer — LLM or deterministic fallback —
     is what gets appended to history (`main.py`'s `append_ask_turn()` call): both are real, true, grounded
     responses to the user's actual question, so both are legitimate context for a later turn. History is
     only ever appended after a real `OpportunityContext` resolved and a real answer was produced — an
     unresolved `event_id` or an empty message never reaches that point, so history can never contain a
     fabricated or ungrounded exchange.
  7. **ASK_FOLLOWUP / personalization bound: unchanged, verified, not re-derived.** The existing Block 4
     `should_record_ask_followup()` per-`(session, opportunity)` cap already made conversational depth
     independent of personalization strength — repeated questions in one session already only ever
     contributed once. No code change was needed here; this block adds an explicit test proving 12 real,
     distinct conversational turns still produce exactly one `ask_followup` `feedback_record`, and a second
     test proving switching between two opportunities mid-session correctly earns at most one contribution
     *per opportunity*, never more.
  8. **Mobile: zero code changes.** `mobile/app/ask.tsx` already renders an accumulating multi-turn
     conversation, already resends the same `session_id` for every turn in one screen visit, already resends
     the same `eventId` from its route params every turn (so an anchor-change scenario cannot occur from
     normal mobile use), and already handles loading/timeout/error states. The request/response contract
     (`AskRequest`/`AskResponse`, `models.py`) is completely unchanged — conversational continuity is a purely
     server-side capability the existing screen benefits from automatically. `lib/__tests__/ask.test.ts`'s 6
     existing tests remain valid unchanged; the full mobile suite (100 tests), `tsc --noEmit`, and `eslint`
     were re-run and are clean, confirming no regression from a change this codebase's own client code never
     touched.
- Consequences: `ask_llm_provider.py` gains `ConversationTurn` and an extended grounding-priority system
  prompt; `ask_llm_fixture.py` and `ask_llm_anthropic.py` gained the `history` parameter (one small breaking
  change to the fixture's `.calls` shape, migrated); `ask_engine.py`'s `generate_grounded_answer()` gained
  `history`; `logan_feed.py` gained bounded history storage/eviction/anchor-reset on the existing `_AskSession`;
  `main.py`'s `ask_logan()` reordered to detect anchor changes and fetch history *before* generating this
  turn's answer, then append the real produced answer to history afterward. New tests:
  `test_ask_conversation.py` (30 — first/second/third-turn continuity, pronoun/reference resolution, bounded
  turn/char eviction with alternating-role invariant proof, same-session-id-two-users isolation,
  same-user-two-sessions isolation, opportunity-anchor-change reset and no-op-on-same-anchor, invalid/stale
  anchor cross-user isolation, authoritative-context-wins system-prompt assertions, no-invented-ranking
  assertions, first/later/retained-history injection resistance at both the structural system-prompt level
  and the wire-message-shape level, provider failure on first and later turns, deterministic-fallback-answer
  entering history correctly, malformed-response fallback, LLM-disabled multi-turn behavior, ASK_FOLLOWUP
  bounded across 12 turns and across an opportunity switch, and existing single-turn paths still working).
  Every pre-existing Ask STRATUS test (`test_ask_context.py`, `test_ask_engine.py`, `test_ask_route.py`,
  `test_ask_llm.py`) passes unchanged; 2 of `test_ask_llm.py`'s own assertions were mechanically updated for
  the fixture's new 3-tuple `.calls` shape, not weakened. `backend` test count 193 → 223 (+30).
  `logan_core` unaffected (306, untouched by this block). mypy/ruff/black clean on every
  new/changed file (the pre-existing `**dict[str, object]` mypy pattern from Blocks 1/2/4's own test fixtures
  now appears in a 4th file, `test_ask_conversation.py`, for internal consistency with those files — not a
  new class of issue, flagged as worth a real fix in a future pass rather than left unexplained). Mobile:
  100/100 Jest tests, `tsc --noEmit`, and `eslint` all clean with zero code changes. No merge to main.
- Deferred / flagged for the owner: the deterministic fallback path does not attempt conversational reference
  resolution (Decision 6) — an accepted, documented scope boundary, not an oversight; a user whose follow-up
  hits an LLM outage gets an honest overview answer, not a broken one, but not a conversationally sharp one
  either. `DomainPref(weight=0.5)`'s dead-consumer status (ADR-057) remains unresolved, unrelated to this
  block. The pre-existing `**dict[str, object]` mypy pattern across Ask STRATUS test fixtures (now 4 files)
  is worth a real fix — a small typed builder function instead of `**overrides` dict-unpacking — in a future
  pass, not urgent enough to block this one.

## ADR-059: Sprint 3.6.8 Block 4 — beta-readiness hardening: integrated-path fixes, observability, and a corrected security posture

- Date: 2026-08-23
- Status: Accepted
- Context: with grounded LLM Ask STRATUS (Block 1), user-scoped state isolation (Block 2), and bounded
  conversation (Block 3) all shipped, this block's job was to harden the fully integrated backend/mobile
  path toward controlled family/beta readiness — not a redesign, a recon-driven pass to find and fix real
  issues in the loop from provider data through to the mobile experience, then report honestly on what
  still blocks a genuinely live-data beta. Mid-block, the owner stated an explicit, governing rule: production
  opportunity generation must be live-data-first; demo fixtures/hardcoded events/synthetic qualifying
  conditions belong only in deterministic tests and acceptance scenarios, never the real app path, and no
  threshold may ever be lowered or a signal fabricated to force a live check to pass. This block's own
  recon findings are organized against that rule explicitly, not folded in as an afterthought.
- Decision (by area):
  1. **Notification dispatch: real per-user failure isolation bug, fixed.** `dispatch_eligible_notifications()`
     (`backend/app/notifications.py`, Block 2) already documented "a failure for one user must not stop
     dispatch for any other user" — but only the actual push send was guarded against that; the per-user
     call to `get_alert_eligible_items(user_id)` (which runs that user's full pipeline) was not. An
     exception there — a pipeline bug, an unexpected live-provider failure — propagated straight out of the
     per-user loop and silently skipped every *other* registered user for that entire poll cycle, directly
     contradicting the function's own documented contract. Fixed: the whole per-user body is now guarded,
     not just the send. New test proves one user's simulated pipeline failure does not stop a second user's
     dispatch in the same call.
  2. **Notification poller: real event-loop-blocking bug, fixed.** `_notification_poll_loop()`
     (`backend/app/main.py`) is an `async def` coroutine that called the fully synchronous
     `dispatch_eligible_notifications()` directly, unlike every HTTP route in this app (plain sync `def`
     handlers, which FastAPI/Starlette already runs in a threadpool automatically). Since that function runs
     a full pipeline per registered user — including, when `STRATUS_LIVE_NVDA_EARNINGS` is enabled, up to
     three sequential live FMP calls bounded at 10s each — a slow poll cycle would have stalled the main
     asyncio event loop, freezing every other concurrent request this server was handling, for its duration.
     Fixed: wrapped in `asyncio.to_thread()`. Currently inert at default configuration (the live flag is off
     by default) but a real, latent hazard the moment it's enabled or the poller does more work.
  3. **FMP provider: API-key redaction in error messages, added defensively.** `FmpEarningsProvider`/
     `FmpMarketDataProvider` (`logan_core/receptors/providers/fmp.py`) send the API key as a URL query
     param and construct error messages from up to 200 characters of the raw HTTP response body — some
     APIs' error responses echo an invalid credential verbatim (e.g. "Invalid API KEY: <key>"). A new
     `_redact()` helper strips the real key from every such error message before it's ever raised (and
     therefore before any caller could print/log it) — a no-op in the normal case where the key never
     appears in a response body, satisfying the "never log API keys" requirement defensively rather than
     only by observed absence of the problem.
  4. **Minimum viable observability for Ask STRATUS routing, added.** Before this block, server logs only
     ever recorded an LLM *failure* — there was no way to tell from logs alone whether a given `/v1/ask`
     request was answered by the LLM or the deterministic path, or which user/entity it concerned, unless it
     happened to fail. `main.py`'s `ask_logan()` now logs one line per successfully-grounded turn:
     `user_id`, `entity_id`, and which path answered (`deterministic` or `llm:<model>`) — deliberately
     routing metadata only, never the question or answer text (no raw conversational transcripts in logs,
     per the explicit requirement), using the same `print(f"[tag] ...")` convention already established
     throughout this module rather than introducing a new logging framework or SaaS vendor.
  5. **Restart-safety matrix: made an explicit, executable contract.** Prior blocks each tested their own
     slice of restart behavior in isolation (Block 3's persisted-interactions test, Block 4's own review).
     `test_beta_hardening.py::test_restart_safety_matrix` now proves, in one place: MemoryStore's durable
     behavioral records survive a simulated restart under `STRATUS_PERSIST_MEMORY`; `PrioritizationEngine`'s
     `AttentionState` (Watch fatigue/cooldown/notification-review) does **not**, regardless of that flag —
     always a fresh, empty per-user dict on every new `Orchestrator`; Ask STRATUS conversation history does
     **not** (by design, ADR-055/058, never written to SQLite); registered push tokens/dispatch-review state
     does **not**. Nothing here changed behavior — this documents and locks in what was already true.
  6. **Multi-user regression re-proven through the actual integrated stack.** Block 2's isolation guarantees
     were originally tested against the single-turn Ask surface that existed at the time. New tests exercise
     the same guarantees through Block 3's real conversational path (multiple turns, retained history, a
     shared `session_id` string between two distinct users) and confirm ASK_FOLLOWUP stays bounded at
     exactly one per (user, session, opportunity) even across a multi-turn exchange for each user
     independently.
  7. **A full integrated acceptance path, using fixtures throughout, never forcing a result.** New test
     proves the complete arc named in this block's own spec end-to-end: no explicit holding on a real fixture
     entity → the opportunity surfaces with limited, honest initial personal relevance → a real multi-turn
     conversational Ask exchange (fixture LLM, not a live call) → `ASK_FOLLOWUP` recorded exactly once →
     additional real, correctly-spaced interactions → a simulated restart with durable persistence actually
     enabled (not simulated in name only) → behavioral evidence survives, correctly scoped to the one user →
     a rebuild shows genuinely matured but still-bounded inferred relevance → Watch's `AttentionState`
     confirmed absent post-restart (see Decision 5) → a second user is provably unaffected throughout.
     No live-market threshold was touched to make this pass, consistent with the owner's live-data-first
     rule — this is exactly the kind of scenario that rule reserves fixtures for.
  8. **The live-data-first rule applied to this codebase: a precise inventory, not a guess.** Confirmed by
     direct inspection: exactly one production (non-test) call site of `simulated_fixtures()` exists
     anywhere in this codebase — `backend/app/logan_feed.py`'s `_run_feed_pipeline()`, the function backing
     the real `/v1/opportunities` endpoint. It always runs 11 hardcoded entities across 6 domains
     (stocks: TSLA/NVDA/AAPL/MARKETS/OIL; crypto: BTC; news: FED; sports: NFL; social: MUSIC/AI_SECTOR;
     poly: POLY). Exactly one of those eleven — NVDA — has *any* live-provider path at all
     (`FmpEarningsProvider`/`FmpMarketDataProvider`, Sprint 3.6.6B/3.6.7), and that path is itself
     config-gated off by default (`STRATUS_LIVE_NVDA_EARNINGS`). A meaningful nuance found during this
     inventory, not previously written down anywhere: TSLA and AAPL are real, valid stock tickers the
     *existing* FMP integration could plausibly serve without any new vendor — `logan_feed.py`'s live-data
     wiring is simply hardcoded to the symbol `"NVDA"` specifically rather than parameterized by entity;
     extending live coverage to those two would be parameterization of proven code, not a new integration.
     MARKETS and OIL represent aggregate/commodity concepts, not single tickers, and would need an explicit
     product decision about what real instrument each should track before any live wiring makes sense. The
     remaining six entities (BTC, FED, NFL, MUSIC, POLY, AI_SECTOR) span five different domains — crypto,
     news/macro, sports, social/culture, and prediction markets — for which this codebase has zero existing
     provider integration of any kind; making any of them live is a genuine new external vendor decision per
     domain, exactly the category this block's own stop condition names. No such vendor was added or even
     selected — this is reported as the single largest, most concrete beta-readiness blocker, not
     silently worked around.
  9. **Mobile beta-readiness: a real, confirmed distribution blocker found, not fixed.** `mobile/eas.json`
     declares `development`/`preview`/`production` build profiles with **no `env` configuration at all**.
     `constants/config.ts`'s `API_BASE_URL` falls back to a hardcoded local Wi-Fi IP
     (`DEV_FALLBACK_API_BASE_URL`) when `EXPO_PUBLIC_API_BASE_URL` isn't set — already documented in-code as
     a local-`expo start`-only convenience. Because EAS Build runs on Expo's remote build servers (never the
     local machine, and never reading the gitignored local `.env`), a `preview` or `production` EAS build
     today would silently bundle that stale local IP into the shipped binary, unreachable for any real
     tester outside the developer's home network. Not fixed here: the correct value depends on where the
     backend will actually be hosted for a beta, which is ADR-006's own still-open decision — setting a
     guessed or placeholder URL would be actively misleading (looks configured, isn't), so this is reported
     as a required owner action, matching the same discipline as not attempting Apple signing/credentials.
  10. **Security/privacy posture corrected precisely, not just softened.** `27_SECURITY_PRIVACY_COMPLIANCE.md`
      previously stated "the only value ever supplied in this codebase is the hardcoded `LOCAL_FOUNDER_USER_ID`
      constant... no way for a second distinct user to exist" — stale since Block 2. Corrected precisely per
      the owner's own explicit instruction: STRATUS now has real, tested backend user-scoped *state
      isolation* (MemoryStore reads, UserModel, AttentionState, OpportunityContext cache, Ask session/
      conversation state all genuinely scoped by `user_id`) — but this is **not** authentication or
      authorization. `resolve_user_id()` trusts the `X-Stratus-User-Id` header outright; nothing verifies a
      caller's claimed identity, so any process reaching the backend can claim to be any `user_id`. The
      isolation protects honest, cooperating identities from leaking into each other — it is not a security
      boundary against an adversarial caller impersonating someone else. Updated: the tag-table's
      `REQUIRED — TRUSTED ALPHA` description, Core Privacy Principle 5, the "Current State" section's
      user-identity bullets (the most load-bearing correction), the Authentication and Authorization
      section's opening line, and the pre-trusted-alpha-distribution checklist. No other section was
      touched — every other FUTURE/target-design section remains accurately unbuilt.
- Consequences: `backend/app/notifications.py` (dispatch isolation fix), `backend/app/main.py` (event-loop
  offload + Ask routing observability), `logan_core/receptors/providers/fmp.py` (key redaction) all changed.
  New tests: `test_push_notifications.py` (+1, per-user dispatch-failure isolation), `test_beta_hardening.py`
  (3 — the restart-safety matrix, multi-user regression through the full conversational stack, and the full
  integrated acceptance path). `backend` test count 223 → 227 (+4). `logan_core` unchanged (306, only the
  FMP redaction helper touched, behavior-neutral, all 306 pre-existing tests re-verified passing unchanged).
  Combined 529 → 533. mypy/ruff/black clean (same 20-error pre-existing baseline pattern, unchanged in count
  and location). Mobile: zero code changes; full suite (100 tests), `tsc --noEmit`, `eslint` all re-run
  clean. `docs/specs/.../27_SECURITY_PRIVACY_COMPLIANCE.md` corrected as described in Decision 10. No merge
  to main; commit not pushed pending review.
- Deferred / flagged for the owner — the actual beta-readiness blockers, not resolved here by design:
  1. **Live-data coverage is the single biggest gap.** 10 of 11 production entities are simulated-only,
     always; only NVDA has any live path, off by default. TSLA/AAPL could plausibly extend the *existing*
     FMP integration (parameterization, not a new vendor) — a real, comparatively small next step if wanted.
     MARKETS/OIL need a product decision about what instrument each represents. BTC/FED/NFL/MUSIC/POLY each
     need a genuine new external vendor decision, one per domain — none selected, none added.
  2. **`eas.json` has no `EXPO_PUBLIC_API_BASE_URL` for any build profile** — a real EAS `preview`/
     `production` build today would ship with an unreachable, stale local IP baked in. Blocked on ADR-006's
     open hosting decision; not fixed with a guessed value.
  3. Push notification credentials, Apple Developer account access, and any other signing/credential setup
     required for a real TestFlight build were not attempted, per the standing instruction not to perform
     irreversible external actions.
  4. `_user_models`/`_opportunity_context_caches` (per-user dicts, Block 2) grow without bound across
     distinct `user_id`s ever seen by the process, never evicted (unlike `_ask_sessions`'s own
     `_ASK_SESSION_LIMIT`). Immaterial at controlled-beta scale (a handful of known testers); flagged, not
     fixed, since adding real eviction machinery for a non-problem at current scale would be exactly the
     kind of premature hardening this block's own "no broad cosmetic refactors" boundary excludes.
  5. Advisory-only disclaimer copy (already specified in `27_SECURITY_PRIVACY_COMPLIANCE.md`) has still not
     been added to any mobile screen — required before any non-operator sees the app, unrelated to this
     block's own scope but worth restating as a real pre-distribution blocker.

## ADR-060: Sprint 3.6.8 Block 5 — live-data transition foundation: generalized live equities path, production-vs-demo runtime boundary

- Date: 2026-08-23
- Status: Accepted
- Context: Block 4's own inventory found exactly one production fixture call site
  (`_run_feed_pipeline()`'s `simulated_fixtures()`) and exactly one entity — NVDA — with any live-provider
  path at all, hardcoded throughout `backend/app/logan_feed.py`. Governed by an explicit owner rule this
  block operationalizes: production opportunity generation must be live-data-first; fixtures belong only in
  tests/demo mode/acceptance scenarios; a provider failure or a non-qualifying condition must never be
  silently dressed up as a real result. Recon confirmed the NVDA coupling was entirely a `backend/app/`
  wiring artifact, not an architectural constraint: `logan_core`'s receptor-mapping layer
  (`earnings_report_to_raw_signal`/`quote_to_raw_signal`/`grade_change_to_raw_signal`), `FmpEarningsProvider`/
  `FmpMarketDataProvider`, `StocksTriggerEvaluator`, and `StockConvergenceTracker` were already fully
  entity-generic (a repo-wide grep found zero hardcoded "NVDA" logic anywhere in `logan_core/`) —
  `StockConvergenceTracker` in particular was already keyed internally by `entity_id` (`_observations`/
  `_active_episode` dicts), so entity isolation for convergence required no code change, only a test proving
  it under the newly-generalized multi-ticker path. `entity_registry.py` already had canonical display
  metadata for TSLA/AAPL. The entire NVDA-only coupling was three private functions and one config flag in
  `backend/app/logan_feed.py`/`config.py`.
- Decision (by area):
  1. **`config.live_stock_tickers()`, backward-compatible with the original single-ticker flag.** New
     `STRATUS_LIVE_STOCK_TICKERS` (comma-separated, e.g. `"NVDA,TSLA,AAPL"`) is the new canonical
     configuration surface — deterministic parsing, no network call, upper-cased/stripped/validated against
     a plausible ticker shape (1-10 letters), invalid entries dropped with a log line rather than crashing
     the whole list, duplicates silently de-duplicated. When unset (or parses to nothing), falls back to the
     original `STRATUS_LIVE_NVDA_EARNINGS` flag exactly (`("NVDA",)` when true, `()` otherwise) — every
     existing deployment/test using only the old flag is completely unaffected, verified by the full
     pre-existing test suite passing unchanged with zero modifications. Setting the new flag at all takes
     over entirely — no merging of both sources, one clear source of truth per configuration.
  2. **Generalized the three NVDA-hardcoded functions to accept any ticker**, mirroring the receptor layer's
     own existing genericism: `_live_nvda_raw_signal`/`_live_nvda_price_move_raw_signal`/
     `_live_nvda_analyst_grade_raw_signal` → `_live_earnings_raw_signal(ticker, now)`/
     `_live_price_move_raw_signal(ticker, now)`/`_live_analyst_grade_raw_signal(ticker, now)`. Same exact
     failure-mode discipline as before (every `FmpProviderError` caught, never raised past this boundary; a
     valid response is not itself an opportunity; log tag renamed `[live-nvda]` → `[live-stocks]` to reflect
     what it now covers). Deliberately preserves the pre-Block-5 substitution semantics exactly — only
     `STOCK_EARNINGS_BEAT` triggers substitution, not the also-real, also-registered `STOCK_EARNINGS_MISS`/
     `STOCK_EARNINGS_IN_LINE` (ADR-045) — rather than silently broadening what "goes live" means as a
     side effect of generalizing *which ticker* it applies to. See the deferred items below: this was found
     to be a real, live-verified gap (TSLA genuinely missed its most recent earnings during this block's own
     live verification — see Decision 6 — and correctly, honestly fell back to its simulated fixture rather
     than surfacing the real miss), not a hypothetical one, but expanding the substitution condition is a
     separate, deliberate decision, not an incidental one bundled into a ticker-generalization block.
  3. **Two real bugs found and fixed while generalizing the `_run_feed_pipeline()` wiring — both instances of
     exactly the "simulated intelligence silently entering a live-labeled opportunity" pattern the owner's
     rule forbids.** (a) TSLA's simulated corroborating signal (`tesla_ai_partnership_corroboration`) was
     previously appended unconditionally whenever `entity_id == "TSLA"`, regardless of whether TSLA's own
     primary signal that poll was genuinely live — meaning a real live TSLA earnings beat would have been
     silently joined by a fabricated "Reuters confirms AI chip partnership" corroborating signal. Fixed: the
     guard is now `entity_id == "TSLA" and entity_id not in live_substituted` — the simulated corroboration
     only ever joins a simulated primary signal, never a live one. (b) Price-move/analyst-grade fetches were
     previously gated only on the *flag* being enabled for NVDA, independent of whether NVDA's own earnings
     fetch that poll actually succeeded live — meaning a live price-move signal could have been spliced onto
     a *simulated* primary earnings signal when the live earnings fetch failed or didn't qualify, producing a
     genuinely blended simulated+live opportunity (World Model's narrative is driven by the first/primary
     signal in the list). Fixed: gated on `entity_id in live_substituted` — an opportunity is now always
     either fully live-sourced (primary signal live, any additional signals also live) or fully simulated
     (primary signal simulated, TSLA's own simulated corroboration included where applicable), never a blend
     of the two. `live_substituted: set[str]` (tracking exactly which tickers got a genuine live earnings
     signal this poll) is the single source of truth both fixes share. Both bugs pre-date this block (they
     existed in the original NVDA-only wiring too, just narrower in blast radius with only one ticker) —
     found and fixed here because generalizing to multiple tickers made the risk concrete enough to
     prioritize, matching the block's own "obvious bug fixes... fixture/live mode separation" pre-approved
     category.
  4. **`config.live_data_only_mode()` — the production-vs-demo runtime boundary, owner-approved concept,
     implementation judged mechanical.** New `STRATUS_RUNTIME_MODE` (`live`/`beta`/`production`, treated
     identically for now — this codebase does not yet distinguish trusted-beta from public production, see
     `27_SECURITY_PRIVACY_COMPLIANCE.md`). Default (unset) is demo/development mode — `_run_feed_pipeline()`
     seeds `fixtures` from the full simulated 11-entity set exactly as before, completely unchanged. In
     live-data-only mode, `fixtures` starts **empty** — an entity only ever appears in that poll's results if
     a genuine live fetch actually substituted it. This single, small change (`fixtures = {} if
     live_data_only_mode() else simulated_fixtures(now)`) is what makes every one of the block's live/demo
     requirements true simultaneously: unsupported domains (no live provider exists for them at all)
     contribute nothing, honestly absent; a configured live ticker whose fetch fails or doesn't qualify is
     *also* honestly absent (no fixture sitting there to fall back to); and demo mode's existing, intentional
     fixture-rich behavior is completely undisturbed — fixtures were not deleted, isolated, or made
     unreachable, only gated on which mode is active.
  5. **Data provenance: the existing `source_id` field already served this purpose — nothing new was
     built.** Confirmed by inspection: `RawSignal`/`TriggerEvent.source_id` already distinguishes live
     (`FMP_SOURCE_ID = "fmp"`) from simulated (`"bloomberg_terminal"`, `"reuters_wire"`, etc.) end to end, and
     the existing `print(f"[live-stocks] ...")` observability convention (Block 4) already surfaces, per
     poll, which tickers went live vs. fell back — the log line's own text (`source=fmp` vs. `source=fixture`)
     is now the audit trail this requirement asked for. No new parallel metadata architecture, no new
     contract field, no mobile-facing exposure — server-side auditability only, exactly as scoped.
  6. **Live verification, run for real, no threshold touched to manufacture a result.** New
     `logan_core/live_verification/live_equities.py` generalizes the existing per-ticker verification
     scripts into one that accepts any ticker list (default NVDA/TSLA/AAPL), run against the real FMP API
     with a real `FMP_API_KEY`. Actual results, 2026-08-23: **NVDA** — real earnings beat fired
     (EPS 1.87 vs. 1.76 consensus, confidence_contribution 0.22); real price move (-0.98%) and analyst grade
     (maintain) both correctly did not fire. **TSLA** — real earnings *miss* fired (EPS 0.33 vs. 0.50
     consensus) and real price move (+5.14%) fired; neither analyst-grade nor convergence fired (2 distinct
     signal types, below the 3-source threshold). Through the real, unmodified `_run_feed_pipeline()` wiring
     specifically (not just the standalone verification script), this miss correctly did **not** go live —
     directly, empirically confirming Decision 2's documented, deliberate gap with real data, not a
     hypothetical. **AAPL** — real earnings beat fired (EPS 2.02 vs. 1.89) and a real analyst downgrade
     fired; combined correctly into one coherent live opportunity (2 real trigger events, confidence 0.595).
     No convergence fired for any ticker (none reached 3 distinct qualifying signal types) — an honest
     result, not forced. Confirms the generalized path works end-to-end against real, current market data,
     not just fixtures.
- Consequences: `backend/app/config.py` gains `live_stock_tickers()`/`live_data_only_mode()`.
  `backend/app/logan_feed.py`'s three NVDA-specific functions generalized; `_get_orchestrator()`'s gate and
  `_run_feed_pipeline()`'s wiring updated with the `live_substituted`-based fully-live-or-fully-simulated
  guarantee. New `logan_core/live_verification/live_equities.py`. New tests: `test_config_live_stocks.py`
  (17 — parsing/validation/backward-compatibility/runtime-mode), `test_live_equities.py` (23 — NVDA/TSLA/
  AAPL individually and together, provider-failure isolation, the TSLA-corroboration-leak regression test,
  live-mode absence semantics, convergence entity isolation, personalization separation, provenance).
  `backend` test count 227 → 267 (+40). `logan_core` unchanged (306, no logan_core files touched — the
  generalization lived entirely in `backend/app/`, confirming the recon finding that logan_core was already
  fully entity-generic). Combined 533 → 573. mypy/ruff/black clean (one real new mypy fix: `Callable` instead
  of bare `callable` as a type annotation in a new test helper). Mobile: 100/100 Jest, `tsc --noEmit`,
  `eslint` re-run and confirmed clean with zero code changes (this block never touched the mobile-facing
  contract). No merge to main; commit not pushed pending review.
- Deferred / flagged for the owner — real, now live-verified gaps, not resolved here by design:
  1. **`STOCK_EARNINGS_MISS`/`STOCK_EARNINGS_IN_LINE` do not yet trigger live substitution** — only
     `STOCK_EARNINGS_BEAT` does, preserving exact pre-Block-5 semantics rather than silently broadening them.
     Live-verified as a real, current gap (TSLA's actual most recent earnings report is a miss). Both are
     already real, registered triggers (ADR-045) — closing this gap is parameterization of an existing
     condition check, not a new vendor or a new threshold, but is a deliberate, separate decision, not
     bundled into this block.
  2. **Price-move/analyst-grade-only live opportunities (no live earnings trigger) are not currently
     possible** — Decision 3(b)'s fix, while closing a real simulated/live blending bug, also means a ticker
     whose earnings didn't go live never gets a live price-move/grade signal attached either, even though
     that signal independently qualified. A real, deliberately narrower behavior than what was theoretically
     possible before the fix; flagged as a candidate future enhancement, not silently dropped.
  3. **Live coverage remains limited to NVDA/TSLA/AAPL (or whatever tickers are explicitly configured) among
     stocks-domain entities** — MARKETS/OIL represent aggregate/commodity concepts, not single tickers, and
     need a product decision about what real instrument each should track before any live wiring makes
     sense; not addressed here.
  4. **BTC/FED/NFL/MUSIC/POLY/AI_SECTOR remain entirely simulated** — no vendor was selected or added for
     crypto, news/macro, sports, social/culture, or prediction markets, per the explicit instruction not to
     choose providers for those domains autonomously. See the fixture-backed runtime inventory
     (`23_CURRENT_IMPLEMENTATION_STATE.md`) for the complete, current-as-of-this-block picture.
  5. **`STRATUS_RUNTIME_MODE` is not yet wired into any deployment** — the mechanism exists and is tested,
     but no real beta/production deployment configuration exists yet (see Block 4's own flagged `eas.json`/
     hosting gaps, unrelated to this block, still open).

## ADR-061: Sprint 3.6.9 Block 1 — remote STRATUS: Fly.io hosting, durable notification state, mobile release-URL invariant

- Date: 2026-08-23
- Status: Accepted
- Context: The post-3.6.8 gap analysis identified two CRITICAL beta blockers: no hosted backend (ADR-006
  remains open) and no way for a real EAS `preview`/`production` build to reach a hosted backend without
  silently falling back to a hardcoded LAN address baked into `constants/config.ts`. Owner decisions made
  before this block, per the Block 1 reconnaissance report: hosting target is **Fly.io**; persistence stays
  **SQLite on a durable Fly Volume** for this beta stage (no PostgreSQL migration); `STRATUS_PERSIST_MEMORY`
  is enabled for the hosted configuration; mobile API configuration is in-scope for this block; no external
  account, payment method, or secret is created without the owner doing so directly. Reconnaissance also
  surfaced a correctness gap the owner explicitly asked to be evaluated for a contained fix: registered Expo
  push tokens and dispatch/review dedup state (`backend/app/notifications.py`) were process-memory only,
  unrelated to `STRATUS_PERSIST_MEMORY` — meaning every hosted redeploy would silently drop every tester's
  push registration and dedup history, requiring the app be reopened just to restore delivery.
- Decision (by area):
  1. **Fly.io deployment made repository-ready, not deployed.** New root-level `Dockerfile` (build context is
     the repo root, not `backend/`, because `backend/app/*.py`'s existing `sys.path` bridge to `logan_core`
     — ADR-022 — requires both directories present as siblings; this preserves that pattern rather than
     refactoring imports, per the block's "operationalize the existing architecture, don't replace it"
     constraint), `.dockerignore` (excludes `backend/.env` and any local `*.db` file from the image — a real
     secret-leak risk if omitted, since `backend/.env` holds the real `FMP_API_KEY`/`ANTHROPIC_API_KEY`), and
     `fly.toml`. `fly.toml` deliberately sets `auto_stop_machines = false` / `min_machines_running = 1` — the
     existing in-process `_notification_poll_loop()` asyncio task (Sprint 3.6.6F) only notices a newly-
     qualifying opportunity while the server process is actually running, so Fly's default scale-to-zero
     behavior would silently break real-world push delivery. No Fly account, app, volume, or secret was
     created — `fly.toml`'s `app`/`primary_region` are explicit placeholders.
  2. **Persistence: SQLite kept, made deployment-configurable, not migrated.** `config.legacy_memory_db_path()`
     (new) makes the historical `memory_engine.py` prototype's database path configurable via
     `STRATUS_LEGACY_MEMORY_DB_PATH` — it was hardcoded to `backend/data/logan_memory.db`, which is ephemeral
     container storage in a hosted deployment, not the durable volume. `memory_store_db_path()` (existing,
     Sprint 3.6.7 Block 3) is unchanged. `fly.toml` points both at the durable `/data` mount. No changes to
     `MemoryStore`'s schema or abstraction — the owner's "preserve the existing persistence abstractions so a
     later PostgreSQL migration remains possible" instruction is satisfied by construction, not by new code.
  3. **Notification-state persistence: implemented, scoped narrowly, using the same durability flag.** New
     `backend/app/notification_store.py` (`NotificationStore`) durably backs exactly three things:
     registered push tokens, dispatched-event dedup, and reviewed-event dedup — the minimum state whose loss
     causes either lost delivery or a duplicate push after a redeploy, matching the owner's explicit "at
     minimum" scope. Deliberately reuses `memory_persistence_enabled()` (`STRATUS_PERSIST_MEMORY`) rather
     than inventing a second toggle — "durable state persistence is on for this deployment" is one operator
     decision, not two independent ones to keep synchronized. Stored in its own SQLite file (a sibling of
     `memory_store_db_path()`, see `config.notification_store_db_path()`), not a shared connection to
     MemoryStore's file — keeps the two abstractions and their schemas/lifecycles fully independent. A real
     bug was found and fixed while wiring this in: `dispatch_eligible_notifications()` (the background
     poller's own function) checked `if not _registered_tokens: return 0` *before* anything had triggered
     the store's lazy load — on the very first poll cycle after a real restart, with no client having
     re-registered yet, this would have silently short-circuited to "nothing to do" every cycle, defeating
     the entire point of the persistence being added. Fixed by calling `_get_store()` (which hydrates the
     three dicts from disk on first use) at the very top of that function, before the empty check.
  4. **STRATUS Watch fatigue/cooldown state (Prioritization's `AttentionState`) — evaluated, deliberately not
     persisted in this block.** Judgment call per the owner's explicit instruction ("if restart loss can
     cause harmful/repetitive notifications... and it is straightforward, persist; otherwise document
     clearly"): fatigue/cooldown loss on restart makes Watch *momentarily more willing* to re-surface
     something it would otherwise have suppressed as recently-seen — an over-notification risk bounded by
     the existing per-event dispatch dedup (Decision 3) which independently prevents an actual duplicate
     *push* for the same event_id regardless of fatigue state. It is not a "straightforward" persist:
     `AttentionState` is keyed by `(user_id, entity_id)` with several time-windowed counters
     (`FATIGUE_LIMIT`, cooldown timestamps) owned internally by `PrioritizationEngine`, a genuinely different
     shape of data than the three flat dedup sets in Decision 3, and persisting it correctly would mean
     either exposing `PrioritizationEngine`'s internals to a new persistence boundary or duplicating its
     state machine — a materially larger change than "reuse the existing durable-volume architecture without
     creating a major new subsystem" permits. Documented here as a known, bounded beta-stage gap rather than
     silently left unaddressed: a backend redeploy can very occasionally cause an alert-eligible item to be
     evaluated as fresh from Watch's fatigue perspective sooner than it otherwise would have been, but never
     a literal duplicate push of the same opportunity.
  5. **CORS: replaced the hardcoded wildcard with an environment-configurable, mode-aware default.** New
     `config.cors_allowed_origins()`: an explicit `STRATUS_CORS_ALLOWED_ORIGINS` always wins; otherwise demo/
     development mode (the default) keeps the exact prior `allow_origins=["*"]` behavior, and beta/production
     mode (`live_data_only_mode()`) defaults to an empty allowlist instead of silently inheriting the
     wildcard into a hosted deployment nobody explicitly configured. CORS is a browser-enforced mechanism
     (preflight + `Origin` header checks) that React Native's `fetch` is never subject to — restricting this
     list cannot block the mobile app's own requests under any configuration, only a hypothetical future
     browser-based client from an unlisted origin. Evaluated once at process startup (same "flip requires a
     restart, not a mid-process toggle" convention already used by `live_stock_tickers()`), not per-request.
  6. **Mobile release-URL invariant: a preview/production build must never silently use a hardcoded LAN
     address.** New `EXPO_PUBLIC_APP_ENV` (set per EAS build profile in `eas.json`: `development`/`preview`/
     `production`) and `constants/config.ts`'s new `resolveApiBaseUrl()`/`isLanOrLocalUrl()` (pure, unit-
     tested functions, not inline module code, specifically so this invariant is independently testable).
     `development` (the default when unset — every pre-Block-1 local `expo start` is unaffected) keeps the
     existing LAN-fallback behavior exactly. `preview`/`production` require `EXPO_PUBLIC_API_BASE_URL` to be
     set, not LAN/loopback-shaped, and HTTPS — otherwise the module throws at load time with a message naming
     exactly what's wrong and where to fix it. This is a deliberate loud-crash-over-silent-failure choice: a
     release build silently pointing at an unreachable LAN address is indistinguishable from "the app is
     broken," with no diagnostic short of reading source code. `eas.json`'s `preview`/`production` profiles
     do not yet set `EXPO_PUBLIC_API_BASE_URL` (no Fly URL exists yet) — building either profile today
     correctly throws until the owner adds the real hosted URL once it exists, which is the intended,
     correct behavior for this stage rather than a gap to silently paper over with a placeholder value.
  7. **Startup configuration visibility.** New `config.startup_config_summary()`, printed once at process
     startup (`main.py`'s `_lifespan`) — states effective runtime mode, configured live tickers, whether
     durable persistence/LLM Ask are on, and the active CORS policy. Never includes a secret value (tested
     explicitly). Not a validation/hard-fail mechanism — a deployment's logs always show what it actually
     came up as, which is the practical form "fail clearly rather than silently degrade" takes here, since
     this codebase has no way to detect "invalid" configuration from inside the process (an unset
     `STRATUS_RUNTIME_MODE` is a legitimate, safe default, not an error condition).
- Consequences: New `Dockerfile`, `.dockerignore`, `fly.toml` (repo root). `backend/app/config.py` gains
  `legacy_memory_db_path()`, `notification_store_db_path()`, `cors_allowed_origins()`,
  `startup_config_summary()`. New `backend/app/notification_store.py`. `backend/app/notifications.py` and
  `backend/app/main.py` wired to use them; `main.py`'s CORS middleware and `memory_engine` construction
  updated; `dispatch_eligible_notifications()`'s empty-check ordering bug fixed. `mobile/constants/config.ts`
  gains `resolveApiBaseUrl()`/`isLanOrLocalUrl()`/`APP_ENV`; `mobile/eas.json` gains per-profile
  `EXPO_PUBLIC_APP_ENV`; `mobile/.env.example` documents it. New tests: `test_deployment_config.py` (11),
  `test_notification_persistence.py` (6), `test_beta_hardening.py`'s restart-safety-matrix test updated to
  assert the new persisted-token behavior (was asserting the opposite, now-superseded behavior), mobile
  `lib/__tests__/config.test.ts` (25). `backend` test count 267 → 284 (+17); `logan_core` unchanged (306, no
  logan_core files touched); mobile Jest 100 → 125 (+25). mypy (run from the repo root, matching the
  existing baseline invocation)/ruff/black clean; `tsc --noEmit`/`eslint` clean.
- Deferred / flagged for the owner — real, not resolved here by design:
  1. **STRATUS Watch fatigue/cooldown state remains process-memory only** — see Decision 4's full reasoning;
     a bounded, documented gap, not silently unaddressed.
  2. **Ask STRATUS session history, `OpportunityContext` cache, and World Model/orchestrator event identity
     remain process-memory only** — unchanged from before this block, per the owner's explicit instruction
     that naturally reconstructable/ephemeral state need not be persisted.
  3. **No PostgreSQL migration** — explicitly out of scope for this block; the existing SQLite abstractions
     were preserved specifically to keep that migration possible later without a rewrite.
  4. **No Fly.io account, app, volume, or secret was created** — the repository is deployment-ready; actual
     deployment requires the owner's own Fly account and the exact CLI steps in the Block 1 report.
  5. **Full authentication/authorization remains Block 2's scope** — `X-Stratus-User-Id` is still
     client-asserted identity, not verified authentication; this block does not change that boundary, only
     documents it again for a hosted context where the distinction matters more.
  6. **CORS's empty beta/production default has not been validated against a real browser-based client** —
     no such client exists yet; the policy is designed correctly by inspection (native mobile is unaffected
     regardless) but has only been exercised by unit tests against the pure config function, not an actual
     cross-origin browser request against a hosted deployment.

## ADR-062: Sprint 3.6.9 Remote STRATUS closeout — FMP provider-level TTL cache

- Date: 2026-08-23
- Status: Accepted
- Context: Physical acceptance testing plus this session's own verification traffic against the newly-hosted
  `stratus-api.fly.dev` produced real `HTTP 429` rate-limit errors from FMP within ~25 minutes of the
  background notification poller running, confirmed directly from Fly logs, not projected. Root cause,
  confirmed by inspection: `backend/app/logan_feed.py` constructs a fresh `FmpEarningsProvider`/
  `FmpMarketDataProvider` instance on every single call (the background poller every 60s, *and* every direct
  `/v1/opportunities` request — mobile foreground polling, testing, the dev-diagnostics screen) with zero
  caching anywhere in the path. Measured steady-state cost from the poller alone: ~10,080 FMP calls/day
  against a 250/day free-tier limit — roughly 40x over. Owner decision: optimize first, do not purchase or
  upgrade the FMP plan.
- Decision: a process-lifetime, shared `FmpResponseCache` (`logan_core/receptors/providers/fmp.py`)
  wrapping only the raw HTTP fetch inside `FmpEarningsProvider.fetch_latest_earnings`/
  `FmpMarketDataProvider.fetch_quote`/`fetch_latest_grade_change` — trigger evaluation, qualification,
  confidence, and convergence are completely unaware a cache exists; a cache hit and a fresh fetch produce
  byte-identical downstream `RawSignal`/`TriggerEvent` behavior. Endpoint-appropriate TTLs, not one blanket
  value, per the owner's explicit guidance: `EARNINGS_CACHE_TTL_SECONDS` = 6 hours (earnings data changes
  quarterly), `GRADE_CACHE_TTL_SECONDS` = 2 hours (analyst grades change infrequently),
  `QUOTE_CACHE_TTL_SECONDS` = 30 minutes (the one genuinely freshness-sensitive path). Cache key is
  `(endpoint, entity_id)`, so tickers and endpoint types never collide. Only a real, successful provider
  response is ever cached — including a real "no data" `None`, which is a legitimate response, not an error
  — `FmpProviderError` always propagates uncached, so a transient failure is retried on the very next call
  rather than being remembered as "no data" for a full TTL window; this also means the cache never serves a
  stale-disguised-as-fresh result during a live outage, preserving the "no valid live data → no live
  opportunity" invariant exactly. Each provider's `__init__` gained an optional `cache:
  Optional[FmpResponseCache] = None` parameter, defaulting to one shared module-level singleton
  (`_shared_fmp_cache`) — this is what makes the background poller and every direct `/v1/opportunities`
  request genuinely share one cache despite each constructing its own fresh provider instance, with zero
  changes needed to `backend/app/logan_feed.py`'s existing call pattern. Tests inject an isolated
  `FmpResponseCache` instance with a fake, controllable clock for deterministic expiry testing; a new
  autouse fixture in both `backend/tests/conftest.py` and `logan_core/tests/conftest.py` resets the shared
  singleton between every test (this cache is itself a process-lifetime singleton, and without the reset,
  one test's cached FMP response could silently leak into another test expecting a different mocked result
  for the same ticker).
- Expected usage after this change, calculated (not guessed) from the TTLs above and the current
  three-ticker (NVDA/TSLA/AAPL) configuration: earnings = 3 tickers × 4 refreshes/day = 12 calls/day.
  Grades/quotes are conditional on a ticker currently showing a live earnings substitution — at the current
  real state (NVDA and AAPL both qualify, TSLA does not, per ADR-060's own documented BEAT-only gap):
  grades = 2 × 12/day = 24, quotes = 2 × 48/day = 96, for a **current-state total of 132 calls/day**. Worst
  case, if all three tickers were simultaneously qualifying: grades = 3 × 12 = 36, quotes = 3 × 48 = 144, for
  a **worst-case total of 192 calls/day**. Both are comfortably under FMP's 250/day free-tier limit (53% and
  77% utilization respectively), with headroom for the one-time burst a process restart causes (the
  in-memory cache is not persisted — a restart starts cold, at most 7 calls to refill it, a one-time cost,
  not a recurring one). **Conclusion: the free FMP plan remains viable for the current NVDA/TSLA/AAPL
  configuration; no paid-plan upgrade is needed.**
- Consequences: `logan_core/receptors/providers/fmp.py` gains `FmpResponseCache`, `_shared_fmp_cache`,
  `reset_fmp_cache()`, `EARNINGS_CACHE_TTL_SECONDS`/`GRADE_CACHE_TTL_SECONDS`/`QUOTE_CACHE_TTL_SECONDS`; both
  `FmpEarningsProvider`/`FmpMarketDataProvider` gain an optional `cache` constructor parameter; each
  provider's three fetch methods become thin cache-checking wrappers around an unchanged, renamed
  `_..._uncached` implementation — zero change to parsing, error handling, or the public Protocol shape.
  Re-exported from `logan_core/receptors/providers/__init__.py`. New `logan_core/tests/test_fmp_cache.py`
  (15 tests: cache hits, expiry per endpoint, ticker/endpoint separation, errors never cached, the
  legitimate-empty-response-is-still-cached distinction, cross-instance shared-cache proof matching the real
  production topology, and a live/demo-integrity check that a cached response feeds trigger evaluation
  identically to a fresh one). `backend`/`logan_core` combined test count 590 → 605 (+15). mypy/ruff/black
  clean.
- Deferred / flagged for the owner: this cache is process-memory only, not persisted to the durable Fly
  Volume — a deliberate scope match to the owner's "provider/infrastructure-oriented, contained" instruction,
  not an oversight; a restart's one-time refill burst is negligible at current scale. If a future domain
  expansion (Sports/Odds) adds its own external provider, that provider should get its own
  reconnaissance-first usage measurement before assuming this same cache design/TTL choices transfer
  directly — the numbers here are specific to FMP's specific free-tier limit and this specific 3-ticker
  configuration, not a general rule.

## ADR-063: Sprint 3.6.9 Remote STRATUS closeout — hosted LLM-grounded Ask STRATUS enabled

- Date: 2026-08-24
- Status: Accepted
- Context: The hosted `stratus-api` deployment (ADR-061) launched with `STRATUS_LLM_ASK` unset (no
  `ANTHROPIC_API_KEY` existed anywhere locally at the time — confirmed by an exhaustive search across the
  repo, every git worktree, and likely PC backup locations, none found). The owner subsequently created a
  new key via the Anthropic Console and placed it in `backend/.env` locally (gitignored, never committed).
  No redesign of Ask STRATUS: this activates the existing Sprint 3.6.8 Block 1 design (ADR-056) unchanged —
  same provider (Anthropic), same official SDK, same model configuration, same provider abstraction, same
  deterministic-fallback-on-any-failure behavior.
- Decision: `ANTHROPIC_API_KEY` imported into Fly via `fly secrets import`, piped directly from
  `backend/.env` (never printed, never appeared in any command text or tool output). `fly.toml`'s
  `STRATUS_LLM_ASK` uncommented to `"true"`; redeployed. Confirmed via the hosted app's own
  `startup_config_summary()` log line: `llm_ask=True`. Confirmed zero occurrences of the word "anthropic" or
  an Anthropic key prefix anywhere in Fly logs.
- Verification status: health check and the deterministic (non-contextual) Ask STRATUS path were confirmed
  working post-deploy. **Full verification of the contextual, LLM-grounded path (a real multi-turn
  conversation against a live opportunity) is blocked, not skipped** — FMP's real daily quota, exhausted
  during this same session's pre-cache-fix testing (see ADR-062), had not yet reset at deploy time, so
  `/v1/opportunities` was returning an honest empty feed with no live `event_id` to ground a contextual
  question against. The contextual Ask path structurally requires a real, currently-cached
  `OpportunityContext`, which requires live opportunity data — there is no way to exercise it without live
  data without fabricating a context, which the standing rules forbid. This will be completed once FMP's
  quota resets and a live opportunity is available again.
- Consequences: `fly.toml`'s `STRATUS_LLM_ASK` line uncommitted→committed as `"true"`. No application code
  changed — this is a secrets/config-only activation of already-shipped, already-tested functionality.

## ADR-064: Sprint 3.6.9 — Persistent Mobile Identity + Beta Security Boundary

- Date: 2026-08-24
- Status: Accepted
- Context: The formal post-3.6.8 gap analysis and the Remote STRATUS work that followed it both flagged the
  same standing gap: `X-Stratus-User-Id` provides real per-request *isolation*, never *authentication* — no
  client-supplied value is verified against anything. This was a documented, accepted limitation while the
  backend was local-only. Two things changed that calculus this sprint: the backend is now a real, hosted,
  internet-reachable service (ADR-061), and the mobile app never sent this header at all (every real request
  silently fell back to the backend's own default). Reconnaissance for this block, done before writing any
  code, found that default was worse than merely "no identity" — `LOCAL_FOUNDER_USER_ID` resolves to the
  fixed, publicly-visible string `"demo_user"` (`logan_core/contracts/common.py`), so *any* caller of the
  hosted API, with no guessing required, could either omit the header or set
  `X-Stratus-User-Id: demo_user` explicitly and receive the founder's own real, personalized data — actual
  holdings, interests, and behavioral history. This was a real information-disclosure exposure, not a
  theoretical one, the moment the backend became reachable from outside the founder's own machine. Full
  authentication (a real login, verified sessions, a third-party identity vendor) remains explicitly out of
  scope for this block — the owner's own instructions drew the line at "vendor-neutral groundwork," reserving
  any paid/external auth vendor decision for a future, explicit owner call.
- Decision (by area):
  1. **Persistent per-install mobile identity.** New `mobile/lib/identity.ts`: a random UUID (`expo-crypto`'s
     `randomUUID()`), generated once and persisted via `expo-secure-store` (iOS Keychain / Android
     Keystore-backed encrypted storage) — first-party Expo packages, no new account, no new vendor, no new
     paid service. Explicitly real *identity*, not authentication: nothing verifies this value belongs to a
     specific person, it only gives the backend a stable, non-guessable per-install identifier to scope data
     to, which is materially better than the prior state (no identity sent at all).
  2. **Centralized propagation, not per-call-site wiring.** `mobile/lib/apiClient.ts`'s `fetchJson()` — already
     the single, established choke point every backend call already goes through (V3.1.4 BATCH-5) — now
     attaches `X-Stratus-User-Id` to every request automatically. One change point, not threading identity
     through each of the many individual screens/hooks that call `fetchJson()`. Fails open, not closed: if
     identity resolution throws (SecureStore unavailable, a rare real-device edge case), the request still
     proceeds without the header rather than blocking the app — the backend's own mode-aware fallback (below)
     handles that case safely either way.
  3. **The founder-fallback exposure, closed at the resolution boundary.** `backend/app/user_context.py`'s
     `resolve_user_id()` is now mode-aware: demo/development mode (the default, matching every existing local
     caller/test) is completely unchanged — missing header still resolves to `LOCAL_FOUNDER_USER_ID`, an
     explicit header is still honored as-is, including the founder constant itself (several existing tests
     deliberately pass it). Beta/production mode (`config.live_data_only_mode()`) never resolves to the
     founder constant from a client-supplied header under any circumstance — not via an absent header (the
     old default), and not via a header that explicitly claims to *be* `"demo_user"` (the sharper,
     previously-open half of the exposure). Both cases resolve to a new, distinct `BETA_ANONYMOUS_USER_ID`
     constant instead — seeded exactly like any other non-founder `user_id` (ADR-057's "new-user seeding is
     genuinely blank" rule, unchanged), so these callers get a shared, harmless, blank-slate bucket, never the
     founder's real data. A real, currently-live per-install identity (the mobile app's own UUID, once a
     rebuilt binary is installed) is honored as-is in beta mode, same as demo mode.
  4. **Header-length cap, defense-in-depth.** `resolve_user_id()` also caps accepted values at 128 characters
     (a real UUID is 36) — an oversized header is treated exactly like an absent one, in both modes. Bounds a
     minor resource-abuse vector (an oversized value propagating into SQLite rows, in-memory dict keys, and
     rate-limit counters) at negligible cost.
  5. **Minimal, in-memory, vendor-neutral rate limiting.** New `backend/app/rate_limit.py`: a fixed-window
     counter per `(route, user_id)`, process-lifetime, no new infrastructure (no Redis, no external
     rate-limiting service) — found during this block's hosted attack-surface review that the API had zero
     request throttling anywhere. Applied to the two most cost-sensitive routes:
     `/v1/opportunities` (30 requests/60s — a full pipeline run per call) and, the sharpest concrete risk,
     `/v1/ask` (20 requests/5 minutes — a grounded question can trigger a real, metered Anthropic API call,
     enabled on the hosted beta this same session, ADR-063). Both limits are generous enough that no
     legitimate single mobile client is ever affected (the app's own foreground poll is far below either
     ceiling) — they exist to bound automated/scripted abuse, particularly real external cost via `/v1/ask`,
     not to throttle real usage. Keyed by the already-resolved `user_id`, which pairs naturally with Decision
     3: anonymous/spoofed/no-identity traffic collectively shares one throttled bucket (`BETA_ANONYMOUS_USER_ID`),
     while distinct real installs each get their own independent budget.
  6. **Hosted attack-surface review, remaining findings (documented, not all requiring code changes).**
     CORS already locked to a safe empty allowlist in beta mode (ADR-061); FMP API key redaction (Block 4) and
     the Anthropic key (ADR-063) both independently confirmed to never appear in logs; `internal_rank_score`
     never serialized (ADR-029); no debug-mode stack-trace leakage (FastAPI's default, `debug=True` never set);
     every SQLite write throughout this codebase already uses parameterized queries (no SQL-injection surface
     via `user_id` or any other client-controlled value). Full authentication remains the standing, correctly
     out-of-scope gap — isolation, not verified identity — reserved for an explicit future owner decision on an
     auth approach/vendor, per this block's own instructions.
- Consequences: `mobile/lib/identity.ts` (new), `mobile/lib/apiClient.ts` (identity header attachment),
  `mobile/package.json`/`app.json` gain `expo-secure-store`/`expo-crypto`. `backend/app/user_context.py`
  (mode-aware `resolve_user_id()`, new `BETA_ANONYMOUS_USER_ID`), `backend/app/rate_limit.py` (new),
  `backend/app/main.py` (rate-limit wiring on two routes). New tests: `test_user_context.py` (14 — pure
  function coverage across both modes plus two full end-to-end route-level proofs that a spoofed/missing
  header in beta mode never receives founder-seeded personalization), `test_rate_limit.py` (8 — limiter unit
  coverage plus real 429s through both wired routes), mobile `identity.test.ts` (4), `apiClient.test.ts`
  gains 3 identity-propagation tests. `backend`/`logan_core` combined 605 → 627 (+22: `test_user_context.py`
  14, `test_rate_limit.py` 8); mobile Jest 127 → 134 (+7: `identity.test.ts` 4, `apiClient.test.ts` +3).
  mypy/ruff/black clean; `tsc --noEmit`/`eslint` clean.
- Deferred / flagged for the owner:
  1. **Full authentication remains not implemented** — a real login/session/verified-identity system, or a
     third-party auth vendor, is a deliberate future decision, not made here. This block closes the sharpest
     concrete *exposure* (the founder-data leak) without pretending the underlying isolation-not-authentication
     boundary itself has changed.
  2. **`/v1/notifications/register` has no rate limit** — lower-priority than `/v1/opportunities`/`/v1/ask`
     (a cheap SQLite insert, not a metered external call), but an unbounded number of fake tokens could still
     be registered under one spoofed/anonymous `user_id` over time. Flagged, not fixed, in this pass.
  3. **The rate limiter and the founder-fallback fix are both process-memory-only** — consistent with this
     codebase's existing precedent (AttentionState, notification dedup) and proportionate at current beta
     scale; a restart resets both, which is acceptable here (worst case, a brief re-opened window) but would
     need reconsideration at materially larger scale.
  4. **The currently-installed phone build does not yet send the new identity header** — it requires a new
     EAS build to pick up this block's mobile changes; until then, real phone traffic still resolves via the
     mode-aware fallback (harmlessly, post-fix) rather than a real per-install identity.

## ADR-065: Sprint 3.6.9 — hosted remote validation pass: redeploy gap found, notification rate limit added

- Date: 2026-08-24
- Status: Accepted
- Context: A hosted verification pass (requested to prove ADR-064's identity/security work against the real
  `stratus-api.fly.dev` deployment, not just local tests) found that `d702ba8` — the commit containing the
  entire founder-fallback fix and rate limiter — had been committed and pushed to git but **never actually
  deployed to Fly**. The running image (`deployment-01M0RJMQ2PNB348BYMNYP1X0TE`) was still the one from the
  Anthropic-enable step, predating the security fix entirely — confirmed directly (`fly status`'s image tag)
  before assuming otherwise. This meant the real, live-exploitable exposure ADR-064 documents was still live
  in production at the moment this verification pass began, despite the code fix already existing.
- Decision: redeployed immediately (`fly deploy`, new image `deployment-01M0V1M0HJDTNA9FHG45GHEBD3`).
  Re-verified directly against the now-current hosted app: an explicit `X-Stratus-User-Id: demo_user` header
  and a missing header both now return the generic, non-founder-seeded opportunity framing (confirmed via
  the real response text — "Nothing in your current holdings..." rather than the founder-only "You're
  tracking a holding connected to NVDA..."), where before the redeploy both had still returned the
  founder-seeded response. `/v1/opportunities` and `/v1/ask` rate limits verified with bounded, safe request
  bursts (31 and 21 requests respectively, single test identities) — both correctly return `429` exactly past
  their configured thresholds (30/60s, 20/300s), with clean, non-leaking response bodies; `/health` confirmed
  unaffected. Separately, reassessed `/v1/notifications/register` per the owner's explicit instruction: added
  the same existing `check_rate_limit()` utility (10 requests/60s) rather than a new subsystem — real usage
  registers once per app launch, so this only bounds mass fake-token registration under one spoofed identity.
- Consequences: `backend/app/main.py` gains `_NOTIFICATIONS_REGISTER_RATE_LIMIT` and a `check_rate_limit()`
  call on that route; `backend/tests/test_rate_limit.py` gains 2 tests (normal-use-unaffected,
  exceeds-then-429). Redeployed to Fly a second time this session to include this change. `backend`/
  `logan_core` 627 → 629.
- **Process lesson, worth stating plainly**: "committed and pushed" is not "deployed" — this session had been
  treating a git push as if it closed the loop on a hosted fix, and it does not. Any future hosted-security
  or hosted-behavior claim in this project should be verified against the actual running Fly image
  (`fly status`'s image tag, or a fresh `fly deploy` immediately before verifying), not inferred from local
  git state.

## ADR-066: Stock Opportunity Logic V2 — Opportunity Lifecycle, Meaningful Change Detection, LLM-Assisted Interpretation

- Date: 2026-08-24/25
- Status: Accepted
- Context — the audit, done before any design work: the owner's product observation was that the same
  NVDA/AAPL cards could remain visible with essentially unchanged framing across days, with no sense of
  whether the underlying opportunity was strengthening, stable, cooling, or no longer worth attention. A
  full trace of the real code path (not documentation) found the exact, precise root causes:
  1. **`WorldModel.process()`'s dedup window (`world_model/model.py`, `DEDUP_WINDOW = timedelta(hours=1)`) is
     measured against each signal's own `captured_at`, not wall-clock arrival time.** For an earnings signal,
     `captured_at` is set once to `report.report_timestamp` (the real report's date, e.g. `2026-05-20`) and
     never advances on later corroboration (confirmed by reading `world_model/model.py`'s corroboration
     branch — `occurred_at`/`captured_at` are deliberately excluded from that `model_copy(update={...})`).
     Because that value never changes between polls, `(signal.captured_at - recent[0])` is *exactly* `0`
     forever once first observed — the dedup window can never expire for a fixed historical report, so the
     event_id stays permanently "the same event," with `is_new=False` on every subsequent poll indefinitely.
     Analyst-grade signals (`captured_at=grade.action_date`) have the identical property; quote signals
     (`captured_at=quote.quote_timestamp`) do not, since FMP's own quote timestamp genuinely advances.
  2. **`PrioritizationEngine.prioritize()`'s `changed_since_view` parameter — the exact mechanism its own
     cooldown logic (`in_cooldown = cooldown is not None and not changed_since_view`) depends on — defaults
     to `True` and is never actually computed by any real caller.** `Orchestrator.run()` (`orchestrator/
     pipeline.py`) calls `prioritize(user_id, domain, policy_result, recommendation)` with no
     `changed_since_view` argument at all, meaning every real call uses the hardcoded default. Cooldown is
     fully implemented, tested-in-isolation, and structurally unreachable through the real pipeline — a
     second, independent root cause layered on top of the first.
  3. **Every layer from World Model through Presentation recomputes its output fresh from the current poll
     alone.** Confirmed by reading `OpportunityEngine.evaluate()`, `EvidenceTrustEngine.evaluate()`,
     `ConclusionConfidenceEngine.evaluate()`, and `PresentationEngine.deliver()` in full: none of them read or
     store a prior snapshot. `EvidenceTrust`'s own `recency_score` (an `exp(-hours_elapsed/6.0)` decay against
     `event.occurred_at`) is the *only* time-awareness anywhere in the existing pipeline, and by the time this
     audit ran it had already fully decayed toward ~0 for both NVDA's and AAPL's real May 2026 earnings
     reports (confirmed by hand-deriving `confidence_score=0.595` from the exact formula and matching the
     real, repeatedly-observed value) — meaning even that one decay mechanism was already "used up" and
     invisible, not something the user could see change, and not strong enough alone to move `lifecycle`
     state, surface, or notification eligibility, none of which read it directly.
  - **Conclusion: the missing architectural piece is a component that persists a *prior* snapshot per
    opportunity and computes a structured diff against it — nothing in the existing 18-layer pipeline needs
    to be redesigned to add this; it slots in as one new, opt-in, additive layer, mirroring
    `StockConvergenceTracker`'s own already-proven pattern exactly.**
- Decision (by area):
  1. **`OpportunityLifecycleTracker`, a new `logan_core/opportunity_lifecycle/` package** — an opt-in
     `PipelineDependency` (`Optional[OpportunityLifecycleTracker] = None`, identical opt-in discipline to
     `trigger_detector`/`convergence_tracker`), wired into `Orchestrator.run()` between the `opportunity` and
     `policy` steps. Every pre-existing caller/test that doesn't wire one in is byte-for-byte unaffected — no
     `"opportunity_lifecycle"` trace layer, `lifecycle_delta` stays `None`, `changed_since_view` stays at its
     pre-existing hardcoded `True`. Entity-keyed (shared across users, matching World Model's own event
     identity) for objective world facts (confidence, active trigger_codes); a lightweight secondary
     `(user_id, entity_id)` index for personal-relevance-change detection, kept intentionally separate — two
     users must always see the identical objective lifecycle state for the same real-world opportunity, and
     personalization must never change that, only how much it matters to a given user.
  2. **Seven-state bounded lifecycle** (`logan_core/contracts/lifecycle.py`'s `LifecycleState`): `new` →
     `developing`/`high_attention` (strengthening) → `monitoring` (stable, unchanged) → `cooling` → `stale` →
     `expired`, plus `reactivated` as a transition (not a resting state) back into `developing`/
     `high_attention`. `high_attention`'s confidence floor (0.6) and the personal-relevance threshold (0.6)
     both reuse existing anchors (`PrioritizationEngine`'s own `visibility="primary"` bar,
     `opportunity/engine.py`'s own explicit-connection bump) rather than inventing new numbers.
  3. **Signal-specific decay windows, not one blanket timeout** (`_MONITORING_WINDOW_HOURS`/
     `_STALE_WINDOW_HOURS`/`_EXPIRE_WINDOW_HOURS` dicts, keyed by trigger_code): earnings 72h/240h/720h
     (quarterly-cadence data, a real reaction plays out over days), analyst actions 48h/168h/360h, price moves
     6h/24h/72h (the genuinely fast-moving signal), convergence 24h/72h/168h (the strongest single signal,
     longer than any one alone). When multiple trigger_codes are active on one opportunity, the *most
     generous* active window governs — an earnings signal still active alongside a price-move signal is
     governed by earnings' own longer window, not forced onto the price move's much shorter schedule (proven
     directly by `test_earnings_plus_price_move_uses_the_longer_earnings_window`). These are declared,
     reasoned constants, not learned — the same threshold-setting discipline this codebase already applies
     everywhere else (`FATIGUE_LIMIT`, `COOLDOWN_WINDOW`, `CONVERGENCE_WINDOW`).
  4. **`LifecycleDelta` — a structured answer to "what changed, when, why it matters, is it enough to update
     the card, is it enough to notify."** `is_meaningful` (confidence delta ≥0.05, or any new trigger_code
     appearing, or a first-time state-boundary crossing, or a personal-relevance delta ≥0.1/threshold
     crossing) feeds `PrioritizationEngine.prioritize()`'s previously-inert `changed_since_view` parameter
     directly — this is the literal fix for the root cause found above, proven end-to-end through the real,
     completely unmodified downstream pipeline (World Model → Evidence Trust → Reasoning → Opportunity →
     Policy → Prioritization) in `test_pipeline_lifecycle.py`. `is_notification_worthy` is a strictly
     narrower subset — aging alone (the natural `cooling`/`stale`/`expired` transitions) is never
     notification-worthy even though it *is* meaningful (updates the card, correctly, per the owner's own
     "an opportunity remains in the Attention Field only while there is a defensible reason" invariant); a
     modest confidence decrease is meaningful-but-not-notifying, while a *major* decrease (≥0.15, "real
     invalidation," a stricter bar than the base 0.05 threshold) does notify — a deliberate asymmetry: routine
     confidence noise updates the card silently, a genuine weakening interrupts, aging never does.
  5. **Notification eligibility redesigned**: `backend/app/logan_feed.py`'s `alert_event_ids` (the gate
     `dispatch_eligible_notifications()`/badge logic reads) now requires *both*
     `prioritized_item.interruption == "alert"` *and* (`lifecycle_delta is None or
     lifecycle_delta.is_notification_worthy`) — "opportunity qualifies as alert" is no longer, by itself,
     "send a notification." Proven directly against the real dispatch path: a repeated poll of unchanged live
     NVDA earnings data is alert-eligible on the first poll and correctly not on the second
     (`test_repeated_poll_of_unchanged_live_data_is_not_alert_eligible`), while the opportunity itself remains
     visible in `/v1/opportunities` throughout (`test_repeated_poll_still_returns_the_opportunity_just_not_
     alert_eligible`) — existence and notification-worthiness are now genuinely decoupled. The existing
     durable dispatch dedup (`_dispatched_event_ids`, ADR-061) remains as a second, independent protection
     layer, not the only one, per the owner's explicit instruction.
  6. **Durable persistence, `backend/app/lifecycle_store.py`'s `LifecycleStore`** — mirrors
     `notification_store.py`'s exact pattern: a separate SQLite file (`lifecycle_state.db`, sibling of
     `stratus_state.db`/`notifications.db` under the same durable volume), gated behind the same
     `STRATUS_PERSIST_MEMORY` flag (one operator decision, not a new toggle), load-on-first-use,
     write-through on every mutation. Deliberately compact per the owner's explicit instruction — stores only
     `LifecycleSnapshot`'s own small field set (confidence_score, trigger_code set, lifecycle_state, three
     timestamps), never raw provider payloads or full signal history. Scoped to `entity_id` only — the
     shared, objective world-fact state; per-user personal-relevance tracking remains process-memory-only, a
     deliberate, documented, bounded gap matching this codebase's existing `AttentionState` precedent
     (fatigue/cooldown are not durable either). Proven end-to-end through a real simulated restart at both the
     tracker level (`test_export_and_load_snapshot_round_trips_state`,
     `test_restart_simulated_tracker_reload_does_not_treat_known_entity_as_new`) and the full backend wiring
     level (`test_lifecycle_state_survives_a_simulated_restart`, `test_no_duplicate_notification_after_
     restart`, plus the deliberate converse `test_without_persistence_restart_does_reset_lifecycle_to_new`
     proving the persistence test isn't a false positive).
  7. **Gated behind `live_stock_tickers()`, the same flag as `trigger_detector`/`convergence_tracker`, not
     wired unconditionally.** `Orchestrator.run()` adds an `"opportunity_lifecycle"` trace layer whenever a
     tracker is wired at all — unconditional wiring would change trace shape (and start engaging
     `changed_since_view`-driven cooldown) for every simulated fixture across every domain, not just the live
     stocks path this block is actually about. Demo mode (no live tickers configured) stays byte-for-byte the
     pre-Sprint-3.6.9 behavior — confirmed, zero regressions, across the full pre-existing 654-test suite
     before any lifecycle-specific tests were even added.
  8. **API contract, additive, six new `FeedItem` fields, all `None`/`False` when lifecycle tracking isn't
     active**: `lifecycle_state`, `is_updated` (a different concept from the pre-existing `is_new_for_user` —
     that's about whether *this user* reviewed this event_id; this is about whether the opportunity itself
     genuinely changed), `meaningful_change_type`, `lifecycle_reason` (one field serving both "why still
     shown" and "why does this deserve attention now," whichever currently applies, rather than two
     separately-maintained fields with overlapping content), `last_meaningful_change_at`, `thesis_age_hours`
     — deliberately measured from `first_seen_at` (when STRATUS itself first surfaced the opportunity), never
     from the signal's own real-world `occurred_at`, which for something like an already-months-old earnings
     report would misrepresent how long the *card itself* has actually been sitting unchanged in the user's
     Attention Field. Two pre-existing tests (`test_live_nvda_response_has_no_internal_or_secret_fields`,
     `test_live_market_data_response_has_no_internal_or_secret_fields`) needed their exact-field-set
     allowlists updated to include these six real, intentional, non-secret fields — the only two real test
     changes this block required anywhere in the pre-existing suite, both updates rather than weakenings.
  9. **LLM-assisted delta-aware interpretation, reusing 100% of the existing Sprint 3.6.8 Block 1 provider
     infrastructure — no new LLM subsystem.** `OpportunityContext` (`ask_context.py`, already the single
     grounding object every Ask STRATUS call uses) gains five additive lifecycle fields, populated in
     `build_opportunity_context()` directly from the same `PipelineResult.lifecycle_delta` that already
     produced the card. `build_system_prompt()` (`ask_llm_provider.py`) renders a "Lifecycle" section only
     when present, explicitly instructing the model to prefer a delta-oriented answer over restating the
     original headline when nothing meaningful changed, and to never invent a change beyond the authoritative
     fields given — proven directly (`test_system_prompt_instructs_delta_oriented_answer_not_restating_card`,
     `test_system_prompt_never_fabricates_a_change_type_beyond_context`) and end-to-end through a real
     pipeline run whose resulting `OpportunityContext` was handed to a real (fixture) provider call
     (`test_real_pipeline_lifecycle_delta_reaches_the_llm_provider_call`). The deterministic
     `OpportunityLifecycleTracker` remains the sole author of every lifecycle fact — the LLM only ever
     narrates a delta it was already handed; there is no code path by which a model response could alter
     `lifecycle_state`, `confidence_score`, or any other authoritative field. Deterministic fallback
     (`answer_question()`) is completely untouched by this change and remains fully functional on any LLM
     failure, exactly as Sprint 3.6.8 Block 1 established.
- FMP capability audit (owner-required before building logic that depends on unavailable data) — classified
  against the three endpoints this codebase actually calls today (`/earnings`, `/quote`, `/grades` on FMP's
  `stable` API surface, confirmed by reading `logan_core/receptors/providers/fmp.py` directly) plus the
  broader signal types Stock Opportunity Logic V2 could plausibly use:

  | Signal / data type | Status | Notes |
  |---|---|---|
  | Earnings actual vs. consensus | **1 — available, in use** | `/earnings`, live-verified repeatedly this session |
  | Earnings timing/recency | **1 — available, in use** | `report_timestamp`, drives `first_seen_at`/decay windows |
  | Live/delayed quotes, price change | **1 — available, in use** | `/quote`, `change_pct` drives `STOCK_PRICE_MOVE_SIGNIFICANT` |
  | Analyst upgrades/downgrades | **1 — available, in use** | `/grades`, action-classified, no direction inference needed |
  | Historical prices | **5 — unnecessary right now** | V2's design only needs the current quote + the tracker's own prior snapshot, not a historical series; no current trigger/lifecycle logic reads it |
  | Volume / average volume | **3 — unavailable from this integration today** | Not read anywhere in the current `Quote` contract (`receptors/providers/base.py`) even though FMP's quote payload likely carries it; would need a real contract/receptor extension, not just a new field read — a genuine, if small, implementation gap, not a data-availability gap |
  | Volatility inputs | **3 — unavailable from this integration today** | Same as volume — not currently modeled anywhere in this codebase's signal types |
  | Analyst consensus (aggregate rating) | **4 — available but not the right shape for this use** | FMP's `/grades` returns individual rating *actions* (a specific firm's upgrade/downgrade), which is exactly what `STOCK_ANALYST_UPGRADE`/`DOWNGRADE` already uses; an aggregate consensus figure is a different, unused endpoint |
  | Estimate revisions | **3 — unavailable from this integration today** | No endpoint call exists for this; would be new provider surface |
  | Price targets | **3 — unavailable from this integration today** | Same |
  | Sector/industry classification | **5 — unnecessary right now** | No current trigger/lifecycle logic is sector-relative |
  | Sector/index relative performance | **5 — unnecessary right now** | Same |
  | Company news/catalysts | **3 — unavailable from this integration today** | No news endpoint integrated; the closest existing concept, `TRIGGER_REGISTRY_GLOBAL.md`'s macro/news triggers, remains entirely unimplemented (pre-existing gap, not new) |
  | Market/macro context | **5 — unnecessary right now** | Out of Stock Opportunity Logic V2's actual scope |
  | Insider/institutional activity | **3 — unavailable from this integration today** | No endpoint integrated |
  | Options activity | **3 — unavailable from this integration today** | No endpoint integrated; ADR-045 already rejected `STOCK_OPTIONS_FLOW_SURGE` for lack of provider data, unchanged finding |
  | Short interest | **3 — unavailable from this integration today** | No endpoint integrated |

  **Conclusion: FMP's free plan, exactly as currently integrated, is sufficient for everything Stock
  Opportunity Logic V2 actually needed to build this block.** Every signal this design depends on
  (confidence_score, trigger_codes, personal_relevance) is already fully served by the three existing
  endpoints — lifecycle tracking is a pure consumer of already-computed pipeline outputs and makes **zero**
  additional FMP calls of any kind, preserving ADR-062's FMP-cache work completely intact (confirmed: no
  change to `logan_core/receptors/providers/fmp.py` or the cache TTLs in this block). Volume/volatility are
  the one *near-term-plausible* gap (data likely exists in FMP's existing quote response, just not yet read
  into this codebase's contracts) — worth a small, contained follow-up if a future block wants
  volatility-aware lifecycle windows, but not required for anything built here. **No new provider or paid
  plan is needed for Stock Opportunity Logic V2 as scoped.**
- Reference implementation pattern for future domains (Sports/Odds, Prediction Markets — not implemented
  this block, per explicit instruction): `real event → qualification (trigger_detection) → opportunity
  (OpportunityEngine) → lifecycle (OpportunityLifecycleTracker, entity-keyed, signal-specific decay windows)
  → meaningful delta (LifecycleDelta) → user relevance (personal-relevance-crossing detection, same tracker)
  → attention transition (PrioritizationEngine, now genuinely fed by changed_since_view) → notification
  decision (is_notification_worthy, a strict subset of is_meaningful) → LLM interpretation (delta-aware
  OpportunityContext, additive, deterministic-authoritative) → expiration (signal-specific windows, never one
  blanket timeout)`. Every piece of this proven-on-stocks pattern is domain-agnostic by construction — the
  tracker itself has no stocks-specific logic beyond the `_MONITORING_WINDOW_HOURS`/etc. dictionaries, which
  gracefully default for any trigger_code they don't recognize. A future domain needs only its own
  trigger_detection module and its own reasoned decay-window table; the lifecycle/delta/notification/LLM
  machinery is already generic and ready.
- Consequences: new `logan_core/contracts/lifecycle.py`, `logan_core/opportunity_lifecycle/` package,
  `backend/app/lifecycle_store.py`; `logan_core/orchestrator/pipeline.py` (opt-in `lifecycle_tracker`
  dependency + wiring), `backend/app/config.py` (`lifecycle_store_db_path()`), `backend/app/logan_feed.py`
  (construction/persistence/notification-eligibility wiring, six new `FeedItem` fields),
  `backend/app/ask_context.py`/`ask_llm_provider.py` (delta-aware grounding, additive). New tests:
  `test_opportunity_lifecycle.py` (20 — tracker unit coverage across every lifecycle transition/threshold),
  `test_pipeline_lifecycle.py` (5 — real Orchestrator wiring, the `changed_since_view` fix proven end-to-end),
  `test_lifecycle_integration.py` (7 — backend wiring: notification suppression, API contract exposure,
  restart persistence, the converse no-persistence case), `test_ask_lifecycle_grounding.py` (5 — LLM
  grounding contract, real pipeline delta reaching a real provider call). 2 pre-existing tests updated
  (exact-field-set allowlists), 0 pre-existing tests weakened. `backend`/`logan_core` combined 629 → 666
  (+37: 20 + 5 + 7 + 5 across the four new test files above). mypy/ruff/black clean throughout,
  including two real fixes caught by mypy during this block (a lambda-closure `Optional` narrowing issue in
  `orchestrator/pipeline.py`, matching this file's own established `lambda x=y: ...` capture-by-value
  convention once identified) and a bracket-mismatch syntax error introduced and immediately caught while
  editing `ask_llm_provider.py` (fixed before any commit).
- Deferred / flagged for the owner:
  1. **Volume/volatility-aware lifecycle windows** — the one near-term-plausible FMP capability gap found by
     the audit; not required for anything built this block, worth a small contained follow-up if a future
     block wants it.
  2. **Per-user personal-relevance history remains process-memory-only** — a deliberate, bounded, documented
     scope choice (matching `AttentionState`'s own existing precedent), not an oversight; self-heals within
     one poll after any restart.
  3. **Sports/Odds/Prediction Markets remain entirely unimplemented** — the reference pattern above is
     documented and proven on stocks specifically per the explicit instruction not to build another domain
     this block.
  4. **A live, real-market demonstration of every lifecycle transition (cooling/stale/expired specifically)
     was not attempted** — these require real elapsed time on the order of days to weeks against real market
     data to observe naturally; deterministic tests (with an injected clock) are the correct, and only
     practical, way to verify this logic, matching the owner's own explicit instruction ("Use deterministic
     tests for scenarios that cannot be guaranteed in live markets").
- **Addendum, 2026-08-24 (recovery pass)**: the session that produced this ADR was cut off before it could
  record one more fact — it had already deployed this block to the hosted `stratus-api` Fly app (release
  `v7`, ~2026-08-24T20:09 ET, immediately after commit `146dcbe`). A recovery pass the same evening confirmed
  via a live, read-only `curl https://stratus-api.fly.dev/v1/opportunities` that the hosted deployment was
  already returning all six new fields (`lifecycle_state`, `is_updated`, `meaningful_change_type`,
  `lifecycle_reason`, `last_meaningful_change_at`, `thesis_age_hours`) on real NVDA/AAPL cards, correctly
  showing `"monitoring"` rather than resetting to `"new"` on repeated polls. This addendum exists solely to
  make the written record match production reality — no behavior changed, nothing was redeployed as part of
  recording this.

---

## ADR-067: Stock Opportunity Logic V2.1 — User Sync Gap (per-user knowledge state)

- Date: 2026-08-24
- Status: Accepted
- Context: ADR-066 (V2) answered "has the opportunity meaningfully changed since STRATUS last evaluated it?"
  — an objective, entity-keyed question, identical for every user. It deliberately left a second, genuinely
  different question unanswered: "has the opportunity meaningfully changed since *this specific user* last
  knew about it?" Without an answer, STRATUS could not distinguish nothing-changed from
  changed-but-already-seen from changed-and-still-unseen for a given user — the next-highest-leverage gap
  once V2 closed the "same card forever" problem.
- Decision (by area):
  1. **Global meaningful revisions, not every poll.** `LifecycleSnapshot` (and `LifecycleDelta`) gained a
     `revision` counter, bumped by `OpportunityLifecycleTracker.observe()` exactly when this poll produced an
     *objective* meaningful change (`is_global_meaningful`) — a new, deliberately narrower gate than V2's own
     `is_meaningful`, which also (correctly, for V2's own card-update scope) folds in personal-relevance
     crossing. A personal-relevance-only change updates the card (`is_meaningful=True`) but must never
     manufacture a new *global* revision — two users must see the identical revision number for the same
     real-world opportunity; personalization changes how much a revision matters to a user, never whether one
     occurred. `change_type in ("personal_relevance_increased", "personal_relevance_decreased")` is the exact,
     already-existing signal used to exclude that case — no new classification logic was needed. A durable,
     append-only `OpportunityRevision` row (`logan_core/contracts/lifecycle.py`, stored via new
     `backend/app/revision_store.py`, mirroring `lifecycle_store.py`'s SQLite pattern) is written only when
     `new_revision != previous_revision` — the common "none" or personal-only poll writes nothing. Typed/
     queryable core columns (`lifecycle_state`, `confidence_score`, `change_type`, `reason`), not an opaque
     blob; `trigger_codes` is the one JSON-serialized list field, matching `LifecycleSnapshot`'s own existing
     precedent. `entity_id` remains the stable opportunity identity across every revision — revision is a
     version number on that identity, not a new identity scheme.
  2. **Per-user knowledge state, compact and UPSERT-only.** New `UserOpportunityKnowledge`
     (`logan_core/opportunity_lifecycle/sync.py`), keyed `(user_id, entity_id)`, three optional high-water
     marks — `last_seen_revision`, `last_notified_revision`, `last_opened_revision` — updated in place via a
     single `_advance_user_knowledge()` upsert path in `backend/app/logan_feed.py` (never one row per
     interaction). Pointers only ever move forward (a `_max_opt` None-safe max). Durable via new
     `backend/app/user_knowledge_store.py`, same SQLite/`STRATUS_PERSIST_MEMORY`-gated pattern as every other
     Sprint 3.6.9+ store.
  3. **Exact seen/notified/opened semantics, chosen from what the app can already honestly tell apart.**
     `last_notified_revision` advances in exactly one place: `notifications.py`'s
     `dispatch_eligible_notifications()`, immediately *after* a real successful Expo send — never at "alert
     eligible" computation time (`get_alert_eligible_items()` alone is not a send). `last_seen_revision`
     advances in exactly one place: `record_interaction()`, for *any* real `interaction_type` reaching it,
     including `"impression"` — reusing Sprint 3.6.7 Block 3's own existing distinction
     (`useImpressionTracking.ts`'s docstring is explicit that serialization into an API response alone is NOT
     an impression; only the card becoming the field's focused vessel is) rather than inventing a new
     exposure signal. `last_opened_revision` advances only on `"view"` (the existing real card-disclosure/
     dwell-tracking interaction) — a strictly stronger signal, tracked separately per the explicit product
     requirement. Critically, **`_run_feed_pipeline()`/the GET `/v1/opportunities` path never advances any
     pointer** — computing `UserSyncDelta` there is a pure read, enforcing "fetching a feed does not imply
     seen" structurally, not by convention.
  4. **`compute_user_sync_delta()` — one pure, deterministic function**, not a class with state
     (`logan_core/opportunity_lifecycle/sync.py`). Four statuses: `NEW_TO_USER` (never seen, never notified),
     `UPDATED_SINCE_SEEN` (seen an earlier revision; current one is newer; no unseen notification pointing at
     it), `NOTIFIED_BUT_UNSEEN` (a notified revision this user's seen-pointer hasn't caught up to — takes
     priority over the other three: "you have an unopened notification" is the more actionable, specific
     fact), `UP_TO_DATE` (seen-pointer matches the current revision and no unseen notification). Never alters
     objective lifecycle, confidence, or market truth — purely a comparison of two already-durable pointers,
     computed fresh on every read.
  5. **Feed/API contract, additive.** Two new `FeedItem` fields, both `None` unless lifecycle/revision
     tracking is active: `opportunity_revision` (the objective, shared current revision number) and
     `user_sync_status` (this user's own `SyncStatus`). Deliberately not a broader copy-generation rewrite of
     `DeliveredItem`'s narrative text — per the owner's explicit "avoid broad visual redesign, focus on the
     intelligence/API contract and minimal presentation support" instruction, exposing the field is the proof
     of behavior; personalized card copy is left to a future presentation pass.
  6. **Ask STRATUS extended, not replaced.** `OpportunityContext` gained `current_revision`,
     `last_seen_revision`, `user_sync_status`, and a deterministic `sync_summary` sentence (computed in
     `ask_context.py`, never by the model). `build_system_prompt()` renders a "Sync" section only when
     tracked, instructing the model to ground a "what changed since I last looked" question in this summary
     specifically — including explicitly saying nothing changed when `UP_TO_DATE`, never manufacturing
     novelty. The deterministic sync computation remains the sole author of every fact; the LLM only narrates
     it, exactly matching V2's own LLM-role discipline.
  7. **Gating**: identical two-condition gate as V2's own lifecycle store — revision/user-knowledge stores
     are constructed only when `live_stock_tickers()` is configured *and* `memory_persistence_enabled()` is
     true; the in-memory tracker-level `revision` counter and process-lifetime knowledge cache work regardless
     of persistence (matching every other in-memory-only capability in this backend). Demo mode (no live
     tickers) is byte-for-byte unaffected — both new `FeedItem` fields stay `None`.
  8. **Migration**: `lifecycle_store.py`'s `lifecycle_snapshots` table gained an additive `revision INTEGER
     NOT NULL DEFAULT 1` column via a guarded `ALTER TABLE` (checked against `PRAGMA table_info` first, since
     `ADD COLUMN` errors if already present) — safe against the already-live hosted Fly volume's pre-V2.1
     database file (see ADR-066's addendum above): the column simply appears with every existing row starting
     at revision 1 the first time the updated binary runs against it, no manual migration step required.
- Consequences: new `logan_core/opportunity_lifecycle/sync.py`, `backend/app/revision_store.py`,
  `backend/app/user_knowledge_store.py`; `logan_core/contracts/lifecycle.py` (`revision` fields,
  `OpportunityRevision`), `logan_core/opportunity_lifecycle/tracker.py` (`is_global_meaningful` revision
  gate), `backend/app/lifecycle_store.py` (migration), `backend/app/config.py` (two new path helpers),
  `backend/app/logan_feed.py` (stores/cache wiring, `_advance_user_knowledge`/`mark_user_notified`, two new
  `FeedItem` fields, seen/opened advancement in `record_interaction()`), `backend/app/notifications.py`
  (notified-pointer advancement on real dispatch), `backend/app/ask_context.py`/`ask_llm_provider.py`
  (sync-aware grounding). New tests: `logan_core/tests/test_user_sync.py` (12 — pure tracker-revision and
  `compute_user_sync_delta` coverage, including the global-vs-personal separation and the
  same-revision-different-users acceptance scenario), `backend/tests/test_user_sync_integration.py` (8 —
  real interaction/dispatch/restart wiring), plus 4 new sync-grounding tests appended to
  `test_ask_lifecycle_grounding.py`. 2 pre-existing tests updated (exact-field-set allowlists, extended for
  the two new fields) and one pre-existing notification-dedup test's fake item fixture extended
  (`entity_id`/`opportunity_revision`) — both real, intentional updates, not weakenings.
  `backend`/`logan_core` combined 666 → 690 (+24). mypy/ruff/black clean throughout.
- Acceptance: STRATUS can now reliably answer "is this meaningful change new to this specific user" — proven
  end-to-end (real interaction recording, real Expo dispatch, real simulated restart) via
  `test_user_sync_integration.py`, not just at the pure-function level.
- Deferred / flagged for the owner:
  1. **Personalized card/notification copy using sync status** (e.g. rendering "No material change since you
     last looked" client-side) was not built — the field is exposed and proven; the presentation layer that
     would consume it for user-facing copy is a follow-up, per the explicit "minimal presentation support"
     scope for this block.
  2. **Ask STRATUS's "what changed since you last looked" answer is bounded to the two boundary facts**
     (last-seen revision number, current state/reason) rather than a full per-revision diff across every
     revision the user missed — a deliberate scope choice to avoid an unrequested history-diff framework;
     `OpportunityRevisionStore.history_for_entity()` exists and could back a richer multi-revision answer
     later if wanted.
  3. **`last_opened_revision` has no dedicated read API yet** — durable and tracked correctly, but nothing
     currently distinguishes "opened" from "seen" in the feed/Ask STRATUS surface; both currently drive the
     same `UP_TO_DATE`/`UPDATED_SINCE_SEEN` decision via `last_seen_revision`. Flagged as available headroom,
     not a gap in what was asked for this block.

---

## ADR-068: Stock Opportunity Logic V2.2 — Evidence + Trajectory Enrichment

- Date: 2026-08-25
- Status: Accepted
- Context: V2 (ADR-066) fixed "does the card ever change." V2.1 (ADR-067) fixed "is this change new to this
  user." Neither answers a third, genuinely different question: *why* an opportunity's card looks the way it
  does right now, and whether the underlying market evidence is getting stronger, holding, weakening, or
  actively turning against the original thesis. `confidence_score` alone doesn't answer this — it moves on
  discrete trigger-driven events (an earnings beat, an analyst action), not on the continuous, day-to-day
  question "is the market actually confirming this."
- FMP capability audit (owner-required before adding calls, done via a real bounded live call against the
  already-configured `FMP_API_KEY` before writing any code, 2026-08-24/25): FMP's `/stable/profile` endpoint
  — same base URL, same API key, same free plan already in use for `/earnings`, `/quote`, `/grades` — returns
  `sector`, `industry`, `averageVolume`, and `beta` for a real symbol (live-verified against NVDA:
  `{"sector": "Technology", "industry": "Semiconductors", "averageVolume": 145424700, "beta": 2.215}`). This
  closes the one gap ADR-066 flagged as "near-term-plausible but unread": volume/volatility data was already
  reachable, just not yet parsed into this codebase's contracts. **No new vendor, no new paid tier, no new
  secret required for anything built in this block.** Market- and sector-relative performance need one
  additional benchmark quote each — fetched through the exact same `/quote` endpoint, just a different
  symbol (SPY for the broad market; a small, reasoned sector→SPDR-Select-Sector-ETF lookup table for sector,
  e.g. Technology→XLK) — not a new endpoint or vendor either.
- Decision (by area):
  1. **New `MarketEvidenceInput`/`EvidenceSnapshot` contracts** (`logan_core/contracts/lifecycle.py`) carry
     typed, queryable core evidence — trigger price, price change since trigger, price change since the last
     *global* meaningful revision, market-relative and sector-relative performance, volume vs. average,
     beta-normalized move — never an opaque JSON blob. `CompanyProfile`/`CompanyProfileProvider`
     (`receptors/providers/base.py`) and `FmpMarketDataProvider.fetch_company_profile()` (new, third method
     on that class, same shared TTL cache pattern, `PROFILE_CACHE_TTL_SECONDS=24h` since sector/beta/avg-
     volume change on the order of days-to-quarters) are the new provider surface. `Quote` gained an
     additive, Optional `volume` field (confirmed present in FMP's real `/quote` response but never read
     before this block).
  2. **A clean, deterministic trajectory dimension, orthogonal to lifecycle state.** New
     `TrajectoryState = STRENGTHENING | STEADY | WEAKENING | REVERSING`
     (`logan_core/contracts/lifecycle.py`). Lifecycle answers "is this still an active thesis"; trajectory
     answers "which way is the evidence moving" — a REVERSING opportunity can still be
     `lifecycle_state="monitoring"`; the state-machine `elif` chain that decides `new_state` in
     `OpportunityLifecycleTracker.observe()` is completely untouched by this block. Computed in
     `_compute_trajectory()` (new, `opportunity_lifecycle/tracker.py`) from one signed number,
     `relative_to_market_pct` re-aligned to the opportunity's own thesis direction (`_signed_relative_
     strength`) — thesis direction itself is not invented: it's read directly from `TriggerEvent.direction`
     (already a real, implemented field, contracts/trigger.py — positive for an earnings beat/analyst
     upgrade, negative for a miss/downgrade), aggregated across this poll's active triggers
     (`_thesis_direction`; a genuine mix of positive and negative, or no directional trigger at all, takes no
     stance and holds the prior trajectory rather than guessing).
  3. **Explicit deterministic predicates, not a hardcoded universal rule or an opaque intelligence score** —
     per the owner's explicit instruction against "price moved > 2% = strengthening." Four declared constants
     (`TRAJECTORY_STRENGTHEN_DELTA=1.0pp`, `TRAJECTORY_REACCELERATION_DELTA=2.5pp`,
     `TRAJECTORY_REVERSAL_CONFIRM_THRESHOLD=0.5pp`, `HIGH_VOLUME_RATIO=1.5x`), each governing one independent,
     readable branch: STRENGTHENING/WEAKENING on a poll-over-poll delta in thesis-aligned relative strength;
     REVERSING specifically requires the *sign* to flip from genuinely confirming to genuinely contradicting
     (both sides past the deadband, not a value merely crossing zero); a volume-confirmation branch can
     promote STEADY to STRENGTHENING on unusually high participation (≥1.5x average) even without a big price
     move, but never against contradicting price action; reacceleration (a further, materially larger jump
     while already STRENGTHENING) is its own distinct, higher bar, satisfying the explicit "a strong thesis
     reaccelerates while remaining in the same trajectory category" requirement without spamming a new
     revision on ordinary continued-strengthening noise. Volatility-aware normalization is real but
     deliberately narrow in scope for this first version: `beta_normalized_move_pct` (raw `change_pct`
     divided by `beta`) is computed, persisted, and exposed to Ask STRATUS as a transparent, explicit figure,
     but is not itself a trajectory-transition driver this block — market-relative performance (already a
     volatility-normalizing comparison in its own right, since it nets out systematic market-wide moves) is
     the primary trajectory axis, kept deliberately to one clean signal rather than a two-axis framework.
  4. **Meaningful-change integration, additive and lowest-priority.** `is_meaningful` (and therefore the
     revision-bump gate `is_global_meaningful`, unchanged from ADR-067) now also includes `trajectory_
     meaningful`. `change_type` gains four new values (`trajectory_strengthening/_weakening/_reversing/
     _reaccelerated`) but they are chosen *only* in the pre-existing final `else` branch — i.e., only when
     nothing higher-priority (a real confidence/trigger-code change, an aging-window crossing, a personal-
     relevance crossing) already claimed this poll's `change_type`. A poll with both a real confidence change
     and a trajectory shift in the same tick still reports the confidence-driven `change_type`; the trajectory
     fields (`trajectory`/`previous_trajectory`/`trajectory_reason`) are independent fields on the same
     `LifecycleDelta` regardless, so the information is never lost, just not the *headline* reason that poll.
     Tiny quote noise (a delta under the declared thresholds) computes `trajectory="STEADY"`/`meaningful=False`
     every time — proven directly (`test_unchanged_quote_noise_does_not_create_meaningful_revision`).
  5. **Global vs. personal state kept separate, continuing ADR-067's own rule.** `_compute_trajectory` and
     every evidence computation take no `user_id`/`personal_relevance` input at all — proven directly
     (`test_trajectory_is_identical_regardless_of_which_user_polls`,
     `test_personal_relevance_alone_never_moves_trajectory`). V2.1's `UserSyncDelta`/`compute_user_sync_delta`
     are completely untouched by this block; a richer global revision (now potentially trajectory-driven)
     flows into the exact same, unmodified per-user sync comparison — a user who already saw the prior
     revision correctly gets `UPDATED_SINCE_SEEN` the moment a trajectory-only revision lands, with no new
     sync-layer logic needed.
  6. **Notification behavior stays deterministic and asymmetric**, mirroring the `confidence_increased`/
     `confidence_decreased` precedent exactly: `trajectory_strengthening`, `trajectory_reaccelerated`, and
     `trajectory_reversing` are notification-worthy (added to `_NOTIFICATION_WORTHY_CHANGE_TYPES`);
     `trajectory_weakening` deliberately is not — it updates the card without interrupting the user. No
     "notify again every X hours" timer of any kind was added; silence remains the correct, common outcome
     whenever nothing meaningful happened. Full end-to-end delivery of a real push additionally still passes
     through Prioritization's own pre-existing fatigue/cooldown vetoes (ADR-050) exactly as before — this
     block does not touch, weaken, or bypass that layer; the backend integration tests prove the V2.2-owned
     signal (the lifecycle snapshot's `last_notification_worthy_at` timestamp, the exact fact
     `get_alert_eligible_items`/dispatch reads) fires correctly, rather than re-proving fatigue/cooldown's own
     already-covered behavior.
  7. **Ask STRATUS extended, LLM remains narrator only.** `OpportunityContext` gained `trajectory`/
     `previous_trajectory`/`trajectory_reason`/`evidence` (additive, all `None`/`"STEADY"` when inactive).
     `build_system_prompt()` renders an "Evidence trajectory" section only when real evidence exists, stating
     the trajectory label plus every concrete figure available that poll (trigger price and price-change-
     since-trigger, price change since the last meaningful revision, market- and sector-relative performance,
     volume ratio, beta-normalized move) and explicitly instructing the model to explain *why* using only
     those figures, to say plainly when a figure is absent rather than guess, and to never invent relative
     performance, volume, or volatility numbers beyond what is listed. The deterministic tracker remains the
     sole author of every trajectory/evidence fact — matching V2/V2.1's own LLM-role discipline exactly; no
     code path lets a model response alter `trajectory`, `evidence`, or any other authoritative field.
     Deterministic fallback (`answer_question()`) is completely untouched and still fully functional with
     `evidence=None`/`trajectory="STEADY"`.
  8. **API contract, additive.** Four new `FeedItem` fields: `trajectory`, `previous_trajectory` (both
     default `"STEADY"`), `trajectory_reason` (`None` default), and `evidence` (a nested, fully-typed
     `EvidenceSnapshot` object — not a flattened dozen-plus top-level fields, matching how `delivered_item`
     is already a typed sub-object on this same contract). All four are `None`/`"STEADY"` whenever lifecycle
     tracking isn't active or no live market evidence was fetched this poll.
  9. **Persistence, extending the same store V2/V2.1 already proved.** `LifecycleSnapshot` gained
     `trigger_price`, `price_at_last_revision`, `last_relative_strength`, `last_volume_ratio`, `trajectory` —
     persisted via the same `LifecycleStore`, using the identical additive-column-guard pattern ADR-067
     introduced for `revision` (`PRAGMA table_info` checked before each `ALTER TABLE ADD COLUMN`, safe against
     the already-live hosted Fly volume's existing database file). No new store was introduced for evidence
     history — `OpportunityRevisionStore` (ADR-067) is deliberately not extended with evidence fields this
     block, a documented scope boundary (see Deferred below), since the *current* evidence already survives
     restart via the extended `LifecycleSnapshot` row, which is what the acceptance tests actually require.
  10. **Gating**: market evidence is fetched only for tickers already gated behind `live_stock_tickers()` *and*
      currently live-substituted this poll (`live_substituted`, the same set that gates the existing price-
      move/analyst-grade fetches) — a simulated demo entity never gets a live evidence fetch spliced onto it,
      preserving the "fully live or fully simulated, never blended" rule this file already enforces. Each of
      the up-to-three additional fetches (profile, market benchmark, sector benchmark) is independently
      best-effort: a failure on any one degrades that specific evidence field to `None` rather than failing
      the whole attempt, matching this file's existing per-signal failure-isolation discipline.
- Consequences: new fields on `logan_core/contracts/lifecycle.py` (`TrajectoryState`, `MarketEvidenceInput`,
  `EvidenceSnapshot`, plus additive fields on `LifecycleSnapshot`/`LifecycleDelta`); `opportunity_lifecycle/
  tracker.py` (`_thesis_direction`, `_signed_relative_strength`, `_build_evidence`, `_compute_trajectory`, new
  `observe()` parameters); `receptors/providers/base.py`/`fmp.py`/`fixture.py` (`CompanyProfile`,
  `fetch_company_profile()`, `Quote.volume`); `orchestrator/pipeline.py` (`run()` gained `market_evidence`,
  forwarded to `observe()` alongside `trigger_directions` derived from real `TriggerEvent.direction` values);
  `backend/app/logan_feed.py` (`_fetch_market_evidence()`, the sector-ETF lookup table, wiring into
  `_run_feed_pipeline()`, four new `FeedItem` fields); `backend/app/lifecycle_store.py` (five new additive
  columns); `backend/app/ask_context.py`/`ask_llm_provider.py` (evidence-aware grounding). New tests:
  `logan_core/tests/test_evidence_trajectory.py` (12 — pure tracker/trajectory logic, including the global-
  vs-personal separation and mixed-direction handling), `logan_core/tests/test_fmp_market_data_provider.py`
  (+7 — `fetch_company_profile` contract, including the real live-verified response shape and cache reuse),
  `logan_core/tests/test_pipeline_lifecycle.py` (+1 — real-Orchestrator vertical proof), `backend/tests/
  test_evidence_trajectory_integration.py` (7 — real backend wiring: FeedItem exposure, trigger-price
  persistence, trajectory-driven notification-worthy signal, the weakening/non-notify asymmetry, restart
  persistence, Ask STRATUS grounding, deterministic-fallback non-interference). 4 pre-existing tests updated
  (three FMP mock handlers extended to tolerate the new `/profile`/benchmark-quote calls; two exact-field-set
  allowlists extended for the four new fields) — all real, intentional updates, not weakenings.
  `backend`/`logan_core` combined 690 → 716 (+26). mypy/ruff/black clean throughout.
- Acceptance: STRATUS can now deterministically explain whether the objective evidence behind an opportunity
  is strengthening, steady, weakening, or reversing, and *why* (trigger price, relative-to-market/sector
  performance, volume vs. average, beta-normalized move) — proven end-to-end through the real backend, not
  just the pure tracker, and proven never to leak into or out of the per-user sync layer.
- Deferred / flagged for the owner:
  1. **`OpportunityRevisionStore` is not extended with evidence fields this block** — the durable revision
     history (ADR-067) still stores only lifecycle facts (state, confidence, trigger_codes, change_type,
     reason), not the evidence/trajectory snapshot that produced a given revision. Current evidence survives
     restart correctly (via the extended `LifecycleSnapshot` row), but a future "show me the evidence at
     revision N specifically, not just now" query isn't supported without this extension. Not required for
     anything built or asked for in this block.
  2. **Sector-relative performance uses one static sector→ETF table**, not a data-driven or FMP-supplied
     benchmark mapping — a real, if small, gap for any sector this table doesn't recognize (the entity simply
     gets no sector-relative figure that poll, never a fabricated one). Sufficient for the three currently
     live tickers (NVDA/AAPL: Technology; TSLA: Consumer Cyclical, per FMP's own real classification), not
     validated against every possible GICS sector FMP might return for a future ticker.
  3. **Volatility-aware normalization (`beta_normalized_move_pct`) is computed and exposed but not a
     trajectory-transition driver** — a deliberate, narrower first-version scope than a full two-axis
     (market-relative + volatility-normalized) trajectory state machine, per the explicit "don't build a
     giant scoring framework" instruction. Worth revisiting if market-relative performance alone proves too
     coarse in practice.
  4. **No live, real-market demonstration of a genuine STRENGTHENING→REVERSING transition was attempted** —
     same reasoning as ADR-066's equivalent deferral: this requires real, unpredictable market movement
     against a live position over time; deterministic tests with controlled evidence inputs are the correct
     and only practical verification method today.
  5. **Thesis-direction aggregation (`_thesis_direction`) takes no stance on genuinely mixed signals** (e.g.
     a real earnings beat alongside a real analyst downgrade in the same poll) — trajectory simply holds at
     its prior value rather than attempting to weight or reconcile conflicting directional evidence. A
     reasonable, honest first-version choice, not yet validated against a real mixed-signal scenario (none of
     the three live tickers has produced one to date).
- **Addendum, 2026-08-25 (hosted validation)**: deploying this block to the hosted `stratus-api` Fly app
  (release `v9`) and reading a real, live `/v1/opportunities` response surfaced one real FMP capability gap
  the pre-deploy audit's single bounded test call didn't catch: `/stable/quote` accepts the broad-market
  benchmark (`SPY` — confirmed live, `relative_to_market_pct` populated correctly with a real figure) but
  rejects the SPDR Select Sector ETF symbols this block's sector-benchmark table uses (`XLK` for NVDA/AAPL),
  returning a real `HTTP 402 Premium Query Parameter` error — sector ETFs are a paid-tier-only symbol class on
  FMP's current plan, not a free-tier "Special Endpoint" like ordinary equities/major index ETFs.
  `_fetch_market_evidence`'s existing best-effort-per-field design already handles this exactly as intended —
  the real hosted response shows `sector_change_pct`/`relative_to_sector_pct` correctly `null` (never
  fabricated), with every other evidence field (trigger price, market-relative performance, volume, beta)
  populated with real live data. No code change was needed; this is a genuine, confirmed data-availability
  gap, not an implementation defect: **sector-relative performance is not achievable for any ticker on FMP's
  current free plan without a paid-tier upgrade** — a real owner decision (purchase a plan upgrade, or accept
  this field staying empty), not something to route around silently. Everything else this block built
  (trajectory, market-relative performance, volume-vs-average, beta-normalization, trigger price) is fully
  live-verified and working exactly as designed on the current plan.
- **Addendum, 2026-08-25/26 (V2.3A hosted-validation fallout)**: deploying V2.3A and re-checking the hosted
  `/v1/opportunities` response found it returning an empty feed — real logs showed `HTTP 429 Limit Reach`
  from FMP across *every* endpoint (`/earnings` included, not just `/quote`), meaning this deployment's daily
  FMP quota was genuinely exhausted, not a code defect. Root cause: this block's own SPY/sector-benchmark
  quote fetches (item above) reused `fetch_quote()`'s tight 30-minute cache TTL — appropriate for an entity's
  own price (needs to catch a real move quickly) but unnecessarily expensive for a benchmark's relative
  standing, which doesn't need that freshness. Combined with the pre-existing 60-second background
  notification poller (ADR-046) re-running the full pipeline continuously, this materially increased daily
  call volume past ADR-062's own carefully-tuned budget. Fixed with a new `fetch_benchmark_quote()`
  (`logan_core/receptors/providers/fmp.py`) — the identical fetch/parse as `fetch_quote()`, cached
  separately under a new `BENCHMARK_QUOTE_CACHE_TTL_SECONDS` (4 hours) — used for the SPY/sector fetches in
  `backend/app/logan_feed.py::_fetch_market_evidence` only; an entity's own quote fetch is completely
  unaffected. 2 new tests (`test_benchmark_quote_maps_the_same_as_fetch_quote`,
  `test_benchmark_quote_uses_a_separate_longer_lived_cache_than_fetch_quote`); combined test count
  743 (+2). Not a new architectural decision — a direct, minimal fix for a real regression this same block's
  hosted validation surfaced, applied before the final report rather than left broken in production.

---

## ADR-069: STRATUS V2.3A — Identity & Account Foundation

- Date: 2026-08-25
- Status: Accepted
- Context: V2/V2.1/V2.2 built the objective Market Intelligence layer. Before building the personal-learning
  system V2.3B needs (declared/learned interests, behavioral signals, cross-device personalization),
  STRATUS needs a real identity/account foundation — without one, "personalization" has nowhere durable to
  attach, and the existing `X-Stratus-User-Id` header (Sprint 3.6.8/3.6.9) is pure client-asserted identity
  with zero verification: any caller can claim to be any `user_id` by changing one header. The explicit
  product requirement: no mandatory registration wall (`first launch → anonymous identity → immediate
  product access → later authenticate → same internal user continues`), and the internal `stratus_user_id`
  string must remain the one canonical identity every domain service already keys on — never replaced,
  never duplicated by a second identity model.
- Auth-provider evaluation (owner-confirmed before implementation, per the explicit "auth-provider
  commitment" stop condition): compared Clerk against Supabase Auth for this stack (Expo/React Native,
  FastAPI, Fly.io, existing `X-Stratus-User-Id` model). **Decision: Clerk.** Rationale: a dedicated,
  actively-maintained Expo SDK (`@clerk/expo`) with built-in Apple/Google/passwordless-email support and
  significantly less custom native-OAuth wiring than Supabase's more DIY Expo integration; backend
  verification is standard JWT/JWKS (no Clerk-specific server SDK), which is exactly what keeps domain logic
  fully decoupled from the vendor and makes a future provider swap a backend-only, one-module change. Clerk's
  free tier is 50,000 Monthly Retained Users (corrected from an earlier, outdated 10,000 figure) — ample for
  this project's current and near-term scale. No real Clerk account/project was created this block — the
  owner will supply real credentials afterward, same pattern as ADR-056's `ANTHROPIC_API_KEY` rollout; every
  piece of this block is built and tested against a real, self-signed-JWT-based test harness, and stays
  completely inert (no JWKS fetch, no auth UI rendered) until `CLERK_ISSUER_URL`/
  `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY` are configured.
- Decision (by area):
  1. **One identity model, not two.** The existing anonymous per-install identifier
     (`mobile/lib/identity.ts`'s `device_id`, a SecureStore-persisted UUID, Sprint 3.6.9) *is* the
     `stratus_user_id` for an anonymous user — no separate "local learning" identity was introduced. New
     `backend/app/account_store.py` (`AccountStore`, SQLite, same `STRATUS_PERSIST_MEMORY`-gated pattern as
     every other Sprint 3.6.9+ store) adds exactly two tables: `accounts` (one row per `stratus_user_id`,
     anonymous or authenticated — the anchor row V2.3B's own tables will key off of) and
     `external_identities` (the `(provider, external_subject) → stratus_user_id` mapping — many external
     identities may eventually map to one canonical id, never the reverse).
  2. **Backend verification, standard JWT/JWKS, no Clerk SDK.** New `backend/app/clerk_auth.py` verifies a
     real Clerk session token via PyJWT's built-in `PyJWKClient` (new dependency: `PyJWT[crypto]`) against
     Clerk's own published JWKS — RS256 only, explicit issuer/expiry/subject checks, fails closed and
     silently (`None`) on every failure mode (missing config, network error, bad signature, wrong issuer,
     expired). `ClerkClaims.subject` is the *only* thing this module ever exposes to a caller — no other
     token claim reaches `account_store.py` or any domain service.
  3. **`resolve_user_id()` (backend/app/user_context.py) gains a second, authenticated tier, without
     changing its own name or its existing anonymous behavior at all.** A present `Authorization: Bearer`
     header always takes priority over — and is never blended with — the anonymous `X-Stratus-User-Id`
     header; it either resolves to a real, verified `stratus_user_id` or the request is rejected outright
     (401), never silently downgraded to anonymous (a client that explicitly claims to be authenticated and
     fails verification must be told so plainly — masking an expired session as "anonymous" would hide a
     real bug behind an apparently-successful, differently-scoped response). A verified-but-never-before-seen
     external identity is auto-provisioned a *fresh* `stratus_user_id` immediately (`_provision_or_lookup_
     account` — the common case: a brand-new device with no anonymous history worth preserving). Every one of
     the eight pre-existing routes using `Depends(resolve_user_id)` is protected automatically by this one
     change — audited directly (`grep` across `main.py`): no route accepts a client-supplied `user_id` via
     body/query param anywhere, `resolve_user_id` is the sole choke point.
  4. **The anonymous → authenticated upgrade is a distinct, explicit action — never inferred inside
     `resolve_user_id()`.** New `POST /v1/account/link` (`require_clerk_claims`, a stricter sibling
     dependency requiring a valid token with no anonymous fallback) and `user_context.link_account()`: first
     link for a given `(provider, subject)` makes the anonymous device's *own existing* `stratus_user_id`
     become the canonical, now-authenticated identity — zero data migration, since every store (MemoryStore,
     UserKnowledgeStore, PrioritizationEngine's AttentionState, notification tokens) is already keyed by that
     same string. This must run *before* any other authenticated request from the same session, or
     auto-provisioning (item 3) will already have claimed a fresh, empty identity for that external account
     first — a real ordering requirement, documented here and enforced by the mobile client calling `/link`
     immediately after a successful sign-in, before any other authenticated call.
  5. **Anonymous-merge semantics: first-linked-wins, explicit and deterministic, not a sophisticated merge
     engine.** When a *second* device (already anonymous, with its own history) authenticates into an
     account already linked to a first device, `link_account()` returns the *first* device's canonical id,
     `upgraded_existing_identity=False` — the second device's own prior anonymous history is **not** merged
     into the canonical account; it remains intact under its own original id, simply no longer the active
     identity going forward. A deliberate, bounded, documented scope choice (see Deferred below), not an
     accident — proven directly
     (`test_second_device_linking_same_account_gets_first_linked_canonical_id`).
  6. **Founder/dev identity stays completely isolated, unchanged.** `LOCAL_FOUNDER_USER_ID` is a fixed,
     compile-time constant, never reachable via Clerk auto-provisioning or linking (a fresh authenticated
     `stratus_user_id` is always a random UUID) — `_get_user_model()`'s founder-only seed block
     (`backend/app/logan_feed.py`) is untouched and still only special-cases the literal founder constant.
     Proven directly (`test_authenticated_identity_is_never_the_founder_constant`).
  7. **Account deletion, built now as the central primitive V2.3B's own future stores will plug into.** New
     `backend/app/account_lifecycle.py::purge_user_data(stratus_user_id)` orchestrates deletion across every
     current user-scoped store: `MemoryStore.delete_user()` (new), `UserKnowledgeStore.delete_user()` (new),
     `NotificationStore.delete_user()` (new), `PrioritizationEngine.delete_user()` (new, in-memory
     AttentionState), and `user_context.purge_account_identity()` (the account row + every external-identity
     mapping pointing at it). Exposed via `DELETE /v1/account`, resolved via the caller's own
     `resolve_user_id()` — never a client-supplied target, so a caller can only ever delete their own data.
     Idempotent by construction. Deliberately does **not** touch objective/global state (LifecycleStore,
     RevisionStore, World Model) — an account's deletion must never alter what any other user sees for the
     same real-world opportunity.
  8. **Session/token handling uses Clerk's own supported lifecycle end to end, no homegrown session
     infrastructure.** Mobile: `mobile/lib/clerkTokenCache.ts` backs Clerk's persisted session in
     `expo-secure-store` (the same keychain mechanism `identity.ts` already uses) — this is what makes app
     restart/session restoration work automatically, before any request is made. `mobile/lib/clerkClient.ts`
     exposes the current session JWT to `apiClient.ts` (a plain function module, not a React component) via
     Clerk's own documented `getClerkInstance()` outside-of-React pattern. Sign-out is Clerk's own
     `signOut()` — the backend needs no additional state change, since JWTs are stateless and simply expire;
     the app reverts to sending only the anonymous header on the next request.
  9. **Mobile UX, deliberately minimal (V2.3B owns real onboarding design).** New `app/account.tsx`: a guest
     notice when Clerk isn't configured (today's default — the app is otherwise byte-for-byte unchanged),
     else Apple/Google (`useSSO`) and passwordless email-code (`useSignIn`'s current "Future resource" API —
     `signIn.emailCode.sendCode()`/`verifyCode()`/`finalize()`, verified directly against the installed
     `@clerk/expo` v4's own type definitions rather than older documentation) sign-in options, a signed-in
     view with sign-out and "delete my data," reachable from the existing hamburger menu's "Your STRATUS"
     section. `apiClient.ts` attaches `Authorization: Bearer <token>` *alongside*, never instead of, the
     existing `X-Stratus-User-Id` header on every request.
  10. **Privacy/data-ownership boundary, explicit.** External auth identity (Clerk `sub`) lives only in
      `clerk_auth.py`'s verification step and `account_store.py`'s mapping table — never reaches domain logic.
      STRATUS account identity (`stratus_user_id`) is the one thing every domain service sees. Anonymous-
      device identity is a `stratus_user_id` like any other, just never yet linked to an external identity.
      User-owned behavioral state (Memory, UserOpportunityKnowledge, AttentionState, notification tokens) is
      strictly per-`stratus_user_id`, purgeable via item 7. Objective/global opportunity intelligence
      (LifecycleSnapshot, OpportunityRevision) remains global/shared, never duplicated per account and never
      touched by any account-lifecycle operation — continuing V2/V2.1/V2.2's own boundary unchanged.
- Consequences: new `backend/app/account_store.py`, `clerk_auth.py`, `account_lifecycle.py`; `user_context.py`
  rewritten (authenticated tier, `link_account`, `purge_account_identity`, process-lifetime account/identity
  cache mirroring `logan_feed.py`'s own `_lifecycle_tracker`/`_lifecycle_store` pattern); `config.py`
  (`clerk_issuer_url`, `clerk_configured`, `account_store_db_path`); `main.py` (`POST /v1/account/link`,
  `DELETE /v1/account`, both rate-limited); `models.py` (`LinkAccountRequest/Response`,
  `DeleteAccountResponse`); `logan_core/memory/store.py` (`delete_user`);
  `logan_core/prioritization/engine.py` (`delete_user`); `backend/app/notification_store.py`/
  `user_knowledge_store.py` (`delete_user`); `backend/requirements.txt` (`PyJWT[crypto]`); `pyproject.toml`
  (a `flake8-bugbear.extend-immutable-calls` entry for `fastapi.Depends`, the standard fix for a
  non-`str`-typed `Depends(...)` default this block's first non-string dependency result surfaced). Mobile:
  new `@clerk/expo`, `expo-web-browser`, `expo-auth-session` dependencies; `lib/clerkConfig.ts`,
  `clerkTokenCache.ts`, `clerkClient.ts`, `account.ts`; `app/account.tsx`; `app/_layout.tsx`
  (conditional `<ClerkProvider>`); `apiClient.ts` (Bearer attachment); `app/index.tsx` (menu entry); a Jest
  manual mock (`__mocks__/@clerk/expo.js`) working around `@clerk/react`'s CJS build reaching into a
  web-only `react-dom` dependency under Jest's Node resolution (never hit by Metro's real, platform-aware
  bundler on-device). New tests: `backend/tests/test_clerk_auth.py` (9 — real RSA-keypair-signed JWT
  verification, not a mocked boolean), `backend/tests/test_account_identity.py` (16 — auto-provisioning,
  the security boundary, linking, first-linked-wins merge, founder isolation, deletion, restart
  persistence), plus store-level `delete_user` coverage folded into existing suites. Mobile:
  `lib/__tests__/account.test.ts`, `clerkClient.test.ts`, plus 2 new `apiClient.test.ts` cases (Bearer
  attachment/omission). `backend`/`logan_core` combined 716 → 741 (+25). Mobile Jest 134 → 143 (+9).
  mypy/ruff/black and `tsc --noEmit`/`eslint` clean throughout.
- Acceptance: every domain service still receives only a plain `stratus_user_id` string, identical in shape
  and meaning to every pre-V2.3A caller. A client cannot impersonate another user by spoofing
  `X-Stratus-User-Id` once a verified Bearer token is present (proven directly). An anonymous user's state
  survives authentication intact under the same identity string. Deletion actually removes every current
  user-scoped store's data for that identity, proven directly, without touching objective opportunity state.
- Deferred / flagged for the owner:
  1. **Real Clerk credentials were not created or supplied this block** — `CLERK_ISSUER_URL`/
     `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY` remain unset everywhere; the owner needs to create a real Clerk
     project (enabling Apple/Google/email-code strategies) and supply both values before any of this is
     reachable outside tests. Until then, the app and API are byte-for-byte the pre-V2.3A anonymous-only
     experience.
  2. **Mobile sign-in UI is implemented against `@clerk/expo`'s real, current type-checked API surface but
     not visually/behaviorally verified on a real device with a real Clerk project** — no simulator or real
     Clerk instance is available in this environment. `tsc --noEmit`/`eslint`/Jest are the validation this
     block could perform; a real on-device pass (Apple/Google native OAuth redirect handling in particular)
     remains the owner's next concrete step once real credentials exist.
  3. **Anonymous-history merge for a second device is intentionally not implemented** — first-linked-wins is
     the documented, deterministic behavior; a second device's own prior anonymous data is preserved but not
     folded into the canonical account. A real merge engine (reconciling potentially-conflicting behavioral
     evidence from two devices) is a materially larger, separate design question, correctly out of this
     block's bounded scope.
  4. **No dedicated backend sign-out endpoint** — deliberate: Clerk JWTs are stateless and simply expire;
     sign-out is entirely a client-side action (discarding the cached session). Revoking a specific session
     server-side (e.g. "sign out this device remotely") is a real Clerk capability not wired into this block.
  5. **Rate limiting on `/v1/account/link`/`DELETE /v1/account`** uses the same lightweight in-memory,
     per-process limiter as every other route (`rate_limit.py`) — not re-evaluated for this specific new
     attack surface beyond generous, defensive-in-depth defaults; a real Clerk-backed deployment may want
     tighter, provider-side abuse protection (Clerk itself rate-limits auth attempts) layered on top later.
