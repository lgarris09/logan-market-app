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
  `Vessel.tsx`, `attentionLayout.ts`. **Open question, not resolved by this ADR**: whether the
  product-facing name should also change from "Opportunity Field" to "Attention Field" — the user's own
  reference mockups from this session label it "THE ATTENTION FIELD," and the code now uses
  `AttentionField` throughout, but nobody has explicitly decided this the way ADR-023 explicitly decided
  the Wheel→Field rename. Revisit and either ratify or reject explicitly; don't let it stay ambiguous.

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
