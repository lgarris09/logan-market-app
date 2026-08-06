# Logan — Architecture

This document describes how Logan is built, the principles that should guide changes, and the
infrastructure decisions that are deliberately still open. It's written to be enough on its own for
someone joining the project cold — for *why* a given choice was made rather than *what* it is, see
[DECISIONS.md](DECISIONS.md); for the locked layer-by-layer contract details, see
[docs/specs/](specs/).

## The system in one picture

```text
logan_core/  (reasoning pipeline, 18 layers, simulated data, client-agnostic)
     │
     │  Orchestrator.run() — Python, in-process
     ▼
backend/app/  (FastAPI — historical prototype + the current demo bridge)
     │
     │  HTTP / JSON, GET /v1/demo/feed
     ▼
mobile/  (Expo/React Native — the Opportunity Field is now the home screen)
```

Three things worth internalizing before touching any of it:

1. **`logan_core` is the product's real asset.** It doesn't know FastAPI, React Native, or HTTP exist. It
   takes signals in and produces reasoned, confidence-scored, policy-checked opportunities out, entirely
   in Python objects.
2. **`backend/app/` is a bridge, not the final API.** It's one FastAPI process wearing two hats: the
   original prototype endpoints (`/v1/briefing`, `/v1/memories`, `/v1/ask`) and the newer `logan_core`
   demo bridge (`/v1/demo/tesla`, `/v1/demo/feed`). Neither is the real, designed external API contract —
   see [Known gaps](#known-gaps-tracked-not-yet-urgent).
3. **The mobile app now has two visual generations living side by side on purpose.** The Opportunity
   Field (home screen) is the current product direction; the classic card-list briefing is preserved at
   `/classic` for comparison, per [ADR-026](DECISIONS.md#adr-026-opportunity-field-ships-field-only-for-phase-1-full-tab-bar-deferred).
   Don't delete either without being asked.

## `logan_core`: the Logan Intelligence System

Per [ADR-014](DECISIONS.md#adr-014-adopt-the-logan-intelligence-system-v10-architecture-as-canonical-retire-the-fastapisqlite-sketch-as-historical),
this is Logan's canonical reasoning architecture — an 18-layer pipeline, one folder per layer under
`logan_core/`. The full specification lives in [docs/specs/](specs/):

- [LOGAN_ARCHITECTURE_v1.0.md](specs/LOGAN_ARCHITECTURE_v1.0.md) — the pipeline diagram and every layer's
  purpose, inputs, outputs, ownership, and allowed/forbidden operations.
- [LOGAN_DATA_CONTRACTS_v1.0.md](specs/LOGAN_DATA_CONTRACTS_v1.0.md) — the System Orchestrator, and the
  versioning/explainability/observability conventions every layer follows.
- [LOGAN_IMPLEMENTATION_PLAN.md](specs/LOGAN_IMPLEMENTATION_PLAN.md) — repository structure, build
  sequence, testing strategy, and deliverables for the Phase 1 vertical slice.

**In one paragraph**: raw signals from six domains (stocks, sports betting, prediction markets, social
trends, news, crypto — see [ADR-024](DECISIONS.md#adr-024-crypto-added-as-a-sixth-domain)) get normalized,
deduplicated and connected into a World Model, evaluated in parallel for source trust and community
momentum, checked against Memory and the User Model, reasoned about in context, confidence-scored, and
turned into an attention recommendation. Policy controls how that recommendation may be communicated
(this is where the advice-boundary and betting-language rules are enforced as code, not just
documentation). Prioritization manages competition for the user's attention, and Presentation decides the
surface and writes the explanation. Feedback and Learning close the loop — and Learning is the *only*
component permitted to write durable Memory or User Model updates.

Phase 1 runs entirely on **simulated data** — see `logan_core/receptors/simulated.py`. There are no live
API integrations yet, by design (see [LOGAN_IMPLEMENTATION_PLAN.md](specs/LOGAN_IMPLEMENTATION_PLAN.md)).

### The 11-entity demo fixture set

`logan_core/receptors/simulated.py`'s `simulated_fixtures()` currently returns one `RawSignal` per entity
across the six domains: Tesla, NVIDIA, Apple, Markets, Oil (stocks), Bitcoin (crypto), Federal Reserve
(news), NFL (sports), Music, AI (social), Polymarket (poly). `logan_core/world_model/model.py`'s
`DOWNSTREAM_EFFECTS` map creates real ripple relationships between some of them (Tesla ↔ NVIDIA ↔ AI ↔
Markets ↔ Federal Reserve ↔ Bitcoin form one connected cluster; Apple, NFL, Music, Oil, and Polymarket are
deliberately left standalone — not everything ripples into everything else). This is what currently
powers the Opportunity Field feed — see [Where future domains and entities plug in](#where-future-domains-and-entities-plug-in)
below for how to extend it.

## The bridge: `backend/app/`

This is one FastAPI process (`uvicorn app.main:app`) that currently does two unrelated jobs:

```text
backend/app/
├── main.py              All routes. Both the historical prototype's and the demo bridge's.
├── memory_engine.py      Historical prototype: SQLite-backed memory classify/score/store.
├── memory_models.py      Historical prototype: memory Pydantic models.
├── models.py             Historical prototype: Opportunity/briefing/ask Pydantic models.
├── data.py               Historical prototype: demo/seed opportunity data.
├── logan_demo.py         Bridge: runs the single Tesla scenario through logan_core.
├── logan_feed.py         Bridge: runs all 11 simulated entities through one shared
│                          Orchestrator, returns a ranked, connected feed.
└── entity_registry.py    Bridge: the "Canonical Entity" step — maps entity_id to
                           display name / category / ticker for the frontend. See below.
```

**Historical prototype** (`memory_engine.py`, `memory_models.py`, `models.py`, `data.py`) — SQLite-backed,
pre-dates `logan_core`, serves `/v1/briefing`, `/v1/memories`, `/v1/context/{category}`, `/v1/ask`. Kept
running and untouched per [ADR-014](DECISIONS.md#adr-014-adopt-the-logan-intelligence-system-v10-architecture-as-canonical-retire-the-fastapisqlite-sketch-as-historical) —
this is what the `/classic` mobile screen calls.

**The `logan_core` demo bridge** (`logan_demo.py`, `logan_feed.py`, `entity_registry.py`) — per
[ADR-022](DECISIONS.md#adr-022-logan_core-bridged-into-the-historical-backend-via-a-demo-endpoint-not-a-real-api-design),
this exists to prove `logan_core` works end-to-end through a real client, not as the final API design.
Both bridge modules use a `sys.path` shim (`logan_core` has no installable packaging yet — no
`pyproject.toml`) and construct a **fresh `Orchestrator` per request**, so repeated calls don't
accumulate state (`AttentionState`, Memory) across unrelated demo sessions.

- `GET /v1/demo/tesla` (via `logan_demo.py`) — the single-event Tesla scenario. Returns `DeliveredItem`,
  `ConclusionConfidence`, `PolicyResult`, and an execution-trace summary. Backs the `/demo` mobile screen.
- `GET /v1/demo/feed` (via `logan_feed.py`) — all 11 simulated entities run through one shared
  `Orchestrator`, ranked by `priority_score`, annotated with which other entities each one "ripples" to
  (`connected_event_ids`, computed from `World Model` entity/downstream overlap). Backs the Opportunity
  Field.

### The canonical entity registry — `entity_registry.py`

`logan_core`'s own `Entity` object (in `logan_core/contracts/common.py`) only carries what reasoning
needs: `entity_id`, `entity_type`, `display_name`, `domain`. It deliberately doesn't know about tickers,
UI categories, or how it should look on screen — display/symbol concerns belong to Presentation, not the
reasoning core, per the architecture's own separation rules (see
[layer ownership](#architecture-principles), principle 7).

`entity_registry.py` is where that presentation metadata actually lives: a small `entity_id -> {
display_name, category, ticker }` lookup (`CanonicalEntity`), consulted by `logan_feed.py` when building
each `FeedItem`. If an entity isn't in the registry, `resolve()` falls back to whatever `logan_core`
already knows (its own display name and domain) rather than erroring — a new simulated entity works
end-to-end with zero registry changes, just with a plainer label and no ticker, until someone adds a
proper entry.

## The frontend: the Opportunity Field

Per [ADR-023](DECISIONS.md#adr-023-opportunity-wheel-renamed-to-opportunity-field), this is the current
name — call it the Field, not the Wheel, in new code and docs.

### Screens (`mobile/app/`)

```text
mobile/app/
├── index.tsx      Opportunity Field — the home screen. Fetches /v1/demo/feed.
├── classic.tsx     The pre-Field home screen (card-list briefing), preserved as-is.
├── ask.tsx         Ask Logan — unchanged, preserved.
├── memory.tsx       Memory Inbox — unchanged, preserved.
├── demo.tsx          Single-event Tesla demo — unchanged, preserved.
└── _layout.tsx        Registers all five screens on a Stack navigator.
```

`index.tsx` owns a hamburger menu (top-left) that opens a modal linking to `classic`, `ask`, `memory`, and
`demo` — that's the whole "preserve and allow fallback" mechanism from
[ADR-026](DECISIONS.md#adr-026-opportunity-field-ships-field-only-for-phase-1-full-tab-bar-deferred).
There's no tab bar yet; the reference render's Watchlist/Insights/Alerts/Profile tabs are intentionally
not built until they have real content.

### The symbol resolution pipeline

This is the reusable architecture the Field depends on — the explicit requirement was that the frontend
should never need new code when Logan encounters a new entity. The pipeline, end to end:

```text
Signal (logan_core)
   │
   ▼
Canonical Entity (backend/app/entity_registry.py) — display_name, category, ticker
   │  travels over HTTP as part of FeedItem
   ▼
Symbol Resolver (mobile/lib/symbolResolver.ts) — decides how to render it
   │
   ▼
EntitySymbol (mobile/components/EntitySymbol.tsx) — the one component that renders it
   │
   ▼
OpportunityNode (mobile/components/OpportunityNode.tsx) — adds label, status, press handling
```

`symbolResolver.ts` is a pure lookup, not a component — it returns one of four `ResolvedSymbol` shapes,
tried in this order:

1. **`logo`** — a known brand icon (currently just Apple and Bitcoin, via `@expo/vector-icons`'
   FontAwesome5 brand set — no logo image assets are bundled).
2. **`ticker`** — the entity's ticker text (Tesla → "TSLA"), if the registry has one.
3. **`category`** — a generic icon for the entity's category (stocks → chart-line, sports → football,
   macro → university, etc.) if neither of the above applies.
4. **`initials`** — derived from the display name, the last resort.

Colors follow the same pattern: a per-entity color table for the entities we already know about, falling
back to a deterministic hash of `entity_id` into a small fixed palette for anything new — so an unlisted
entity still gets a stable, distinct color instead of a default gray.

**No new dependency and no new component is required to add an entity.** Worst case, an unregistered
entity renders with initials, a category icon or plain fallback color, and a plainer display name — never
a crash, never a blank node. See [Where future domains and entities plug in](#where-future-domains-and-entities-plug-in).

### The Field layout itself

`mobile/components/OpportunityField.tsx` does the actual radial math:

- **Radius** (distance from center) is inversely proportional to `priority_score` — the highest-priority
  item sits closest to `LoganCore`.
- **Angle** is evenly distributed around the circle, ordered by priority, starting at the top.
- **Connection lines** are drawn (via `react-native-svg`) between any two items whose `connected_event_ids`
  overlap — this is `logan_core`'s real World Model ripple data, not decorative.
- **`LoganCore`** (`mobile/components/LoganCore.tsx`) is the center glyph — a slow breathing
  scale/opacity loop via `Animated`, glass panel via `expo-blur`, glow via `expo-linear-gradient`. It's
  explicitly not a logo; treat changes to it as a product decision, not a styling tweak.
- Entrance animation staggers each node's fade/scale-in by priority order.

Three dependencies were added specifically for this — `react-native-svg`, `expo-linear-gradient`,
`expo-blur` — see [ADR-025](DECISIONS.md#adr-025-frontend-dependencies-approved-for-the-opportunity-field-ui).
No icon library was added; `@expo/vector-icons` (already present) covers the symbol resolver's icon needs.

## Where future domains and entities plug in

This is the concrete extension path — deliberately spelled out so a future domain or entity doesn't
require re-deriving the architecture from scratch.

**Adding a new entity to an existing domain** (e.g. another stock ticker):
1. `logan_core/receptors/simulated.py` — add a `RawSignal` fixture to `simulated_fixtures()`.
2. `logan_core/world_model/model.py` — optionally add it to `DOWNSTREAM_EFFECTS` if it should ripple into
   other entities, and to `ENTITY_DISPLAY_NAMES` for a fallback display name.
3. `backend/app/entity_registry.py` — add a `CanonicalEntity` entry for a proper display name, category,
   and ticker. Skippable — `resolve()` falls back gracefully — but skipping it means a plainer label.
4. `mobile/lib/symbolResolver.ts` — optionally add a `KNOWN_LOGOS` or `ENTITY_COLORS` entry for a specific
   look. Skippable — the fallback chain (ticker → category icon → initials, deterministic color) handles
   it with zero frontend code changes.

**Adding a new domain** (e.g. a domain today's six don't cover):
1. `logan_core/contracts/common.py` — add the new value to the `Domain` `Literal` type.
2. `logan_core/normalization/normalize.py` — add a `SIGNAL_TYPE_REGISTRY` entry listing that domain's
   valid `signal_type`s.
3. Follow the "Adding a new entity" steps above for at least one entity in the new domain.
4. Update [docs/specs/Logan_Documentation_v3.1.3/07_DATA_CONTRACTS.md](specs/Logan_Documentation_v3.1.3/07_DATA_CONTRACTS.md)
   and [06_LAYER_INTERFACE_SPECIFICATION.md](specs/Logan_Documentation_v3.1.3/06_LAYER_INTERFACE_SPECIFICATION.md)
   (domain lists, signal type registry) — this package supersedes the older `LOGAN_ARCHITECTURE_v1.0.md`/
   `LOGAN_DATA_CONTRACTS_v1.0.md` lineage per [ADR-040](DECISIONS.md#adr-040-docsspecslogan_documentation_v313-ratified-as-the-authoritative-spec-lineage-older-docsspecsmd-numbered-files-marked-historical) —
   and log an ADR — see [ADR-020](DECISIONS.md#adr-020-news-added-as-a-fifth-domain-receptor) and
   [ADR-024](DECISIONS.md#adr-024-crypto-added-as-a-sixth-domain) for the precedent. Note `culture` and
   `personal_finance` are documented in `07_DATA_CONTRACTS.md` but not yet added to the running `Domain`
   `Literal` (SPECIFIED — NOT IMPLEMENTED, OD-009) — adding a domain to code and documenting one are
   tracked separately.

**Adding a real (non-simulated) receptor**, once Phase 1's simulated-data constraint is lifted: implement
a new Layer 1 Domain Receptor per its interface spec in
[LOGAN_ARCHITECTURE_v1.0.md](specs/LOGAN_ARCHITECTURE_v1.0.md#layer-1--domain-receptors) — receptors are
explicitly documented as pluggable "without touching existing layers." Nothing downstream of Normalization
needs to change.

## Historical: the original FastAPI/SQLite sketch

Preserved as a historical record, not a design to extend further — see the
[Bridge](#the-bridge-backendapp) section above for what's actually current in `backend/app/`.

- **Backend**: FastAPI + Pydantic, SQLite (`backend/data/logan_memory.db`), no ORM — the memory engine
  talks to SQLite directly.
- **Communication**: mobile talks to the backend over plain HTTP using a LAN IP set in
  `mobile/constants/config.ts` — a local-dev-only arrangement (Expo tunnel for wider sharing), not a
  deployment story.

## Architecture principles

These apply regardless of which specific technology is in play:

1. **Memory and the User Model are the core asset.** Everything else is a consumer of what Learning has
   written. Changes to Memory System, User Model, or Learning logic deserve the most scrutiny and the
   best test coverage in the codebase — see
   [ADR-018](DECISIONS.md#adr-018-stricter-per-layer-testing-bar-adopted-for-the-logan_core-pipeline).
2. **The external API is a contract — version it deliberately, and design it before assuming it.** The
   `/v1/demo/*` bridge routes are explicitly not that design — see [Known gaps](#known-gaps-tracked-not-yet-urgent).
3. **Don't couple to infrastructure that isn't decided yet.** Database and hosting are still an open
   decision (see below) — now informed by the Operational History (append-only, queried by reference)
   vs. Logan Memory/User Model (small, actively queried) split, but not resolved by it.
4. **Keep clients simple; keep the intelligence in `logan_core`.** `logan_core` must remain client-agnostic
   — no dependency on React Native, Expo, or any specific frontend (see
   [ADR-012](DECISIONS.md#adr-012-logan-core-keeps-clean-api-boundaries-now-no-multi-client-platform-tooling-yet)).
   Business/reasoning logic never gets duplicated into a client. This is also why `entity_registry.py`
   lives in `backend/app/`, not `logan_core/` — it's presentation metadata, not reasoning.
5. **Config and secrets are environment-specific, never hardcoded.** See
   [STANDARDS.md](STANDARDS.md#security-practices). (`mobile/constants/config.ts`'s LAN IP is a known,
   accepted local-dev exception — never committed with a real value, see the git history/session notes.)
6. **Prefer boring, well-understood technology.** Logan's differentiation is the reasoning/personalization
   product, not novel infrastructure. Reach for established tools (see
   [ADR-007](DECISIONS.md#adr-007-industry-standard-formatting-linting-and-type-checking-defaults)) over
   clever ones.
7. **Layer ownership boundaries are enforced, not just documented.** "Only Learning writes Memory/User
   Model," "only Policy suppresses," "only Presentation formats" — these aren't guidelines, they're the
   whole point of the architecture. A convenience shortcut that has one layer reach into another's
   responsibility defeats the design; treat any such shortcut as a bug, not a simplification.
8. **One reusable component per concept on the frontend, not one per entity.** The symbol resolution
   pipeline exists specifically so a new company, team, or trend never requires new UI code — extend the
   lookup tables, not the component tree.

## Known gaps (tracked, not yet urgent)

Called out explicitly so they're a conscious backlog, not a silent liability:

- **No authentication or per-user identity** anywhere yet, in either the historical backend or
  `logan_core`. Required before any multi-user or public deployment.
- **The historical backend's CORS is wide open** (`allow_origins=["*"]`), credentials disabled — fine for
  local dev, not acceptable once reachable from the public internet.
- **No secrets/config management pattern** established yet for either codebase.
- **The `/v1/demo/*` bridge is not the real external API.** It proves connectivity and is what the mobile
  app currently calls, but the actual client-facing API contract (versioning, auth, pagination, real
  entity coverage beyond the 11 demo fixtures) is still undesigned.
- **No live data integration.** All receptors run on simulated data in Phase 1 by design — see
  [specs/LOGAN_IMPLEMENTATION_PLAN.md](specs/LOGAN_IMPLEMENTATION_PLAN.md).
- **`logan_core` has no installable packaging** — the backend bridge reaches it via a `sys.path` shim
  (see [ADR-022](DECISIONS.md#adr-022-logan_core-bridged-into-the-historical-backend-via-a-demo-endpoint-not-a-real-api-design)),
  not a proper dependency. Fine for one repo, would need fixing to ship `logan_core` independently.

None of these block the Phase 1 vertical slice. They must be resolved before
[ADR-006](DECISIONS.md#adr-006-database-and-hosting--open-decision) is closed and before any deployment
beyond a developer's machine.

## Open questions

- **Database and hosting** — open per [ADR-006](DECISIONS.md#adr-006-database-and-hosting--open-decision).
  Phase 1 storage choices for Operational History and Logan Memory are made per-implementation, not
  locked to a production database or hosting provider yet.
- **Authentication model** — not yet designed. Needs a decision before multi-user support.
- **LLM/reasoning provider for the Reasoning Engine** — not yet chosen. Phase 1 uses rule-based reasoning
  to prove the pipeline; when a model is chosen, prefer current latest-generation models and document the
  choice as a new ADR, since it directly affects cost, latency, and the analysis-vs-advice boundary in
  [PRODUCT.md](PRODUCT.md).
- **External API design** — see "Known gaps" above.
- **Full 5-tab navigation chrome** (Watchlist/Insights/Alerts/Profile) — deferred per
  [ADR-026](DECISIONS.md#adr-026-opportunity-field-ships-field-only-for-phase-1-full-tab-bar-deferred)
  until there's real content for them.

When any of these are resolved, add an ADR in [DECISIONS.md](DECISIONS.md) and update this document —
do not let this file drift from what's actually decided.
