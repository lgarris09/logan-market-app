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
