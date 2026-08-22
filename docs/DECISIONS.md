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
