# Logan — Architecture

This document describes how Logan is built, the principles that should guide changes, and the
infrastructure decisions that are deliberately still open. For *why* a given choice was made, see
[DECISIONS.md](DECISIONS.md).

## Canonical architecture: the Logan Intelligence System

As of [ADR-014](DECISIONS.md#adr-014-adopt-the-logan-intelligence-system-v10-architecture-as-canonical-retire-the-fastapisqlite-sketch-as-historical),
Logan's canonical Phase 1 architecture is an 18-layer intelligence pipeline, not the original FastAPI
sketch. The full specification lives in [docs/specs/](specs/):

- [LOGAN_ARCHITECTURE_v1.0.md](specs/LOGAN_ARCHITECTURE_v1.0.md) — the pipeline diagram and every layer's
  purpose, inputs, outputs, ownership, and allowed/forbidden operations.
- [LOGAN_DATA_CONTRACTS_v1.0.md](specs/LOGAN_DATA_CONTRACTS_v1.0.md) — the System Orchestrator, and the
  versioning/explainability/observability conventions every layer follows.
- [LOGAN_IMPLEMENTATION_PLAN.md](specs/LOGAN_IMPLEMENTATION_PLAN.md) — repository structure, build
  sequence, testing strategy, and deliverables for the Phase 1 vertical slice.

**In one paragraph**: raw signals from five domains (stocks, sports betting, prediction markets, social
trends, news) get normalized, deduplicated and connected into a World Model, evaluated in parallel for
source trust and community momentum, checked against Memory and the User Model, reasoned about in
context, confidence-scored, and turned into an attention recommendation. Policy controls how that
recommendation may be communicated (this is where the advice-boundary and betting-language rules are
enforced as code, not just documentation). Prioritization manages competition for the user's attention,
and Presentation decides the surface and writes the explanation. Feedback and Learning close the loop —
and Learning is the *only* component permitted to write durable Memory or User Model updates.

This lives in a new top-level `logan_core/` directory (per
[ADR-017](DECISIONS.md#adr-017-new-top-level-logan_core-directory-with-one-folder-per-layer)), separate
from the existing `backend/` FastAPI service described below, which keeps running unmodified until
`logan_core/` reaches parity.

## Historical: the original FastAPI/SQLite sketch (superseded, still running)

This was Logan's first working prototype and remains the only code that actually runs today. It predates
the Logan Intelligence System architecture above and is preserved here as a historical record, not as a
design to extend further — see [ADR-014](DECISIONS.md#adr-014-adopt-the-logan-intelligence-system-v10-architecture-as-canonical-retire-the-fastapisqlite-sketch-as-historical).

```text
logan_market_app_starter/
├── backend/            FastAPI service — the memory engine and API (historical prototype)
│   └── app/
│       ├── main.py            API routes (/v1/*)
│       ├── memory_engine.py   Memory classification, scoring, storage
│       ├── memory_models.py   Memory-related Pydantic models
│       ├── models.py          Opportunity/briefing/ask Pydantic models
│       └── data.py            Demo/seed data
└── mobile/             Expo (React Native) app
    ├── app/            expo-router screens (index, ask, memory)
    ├── components/
    └── constants/config.ts    API_BASE_URL — points the app at the backend
```

- **Backend**: FastAPI + Pydantic, SQLite (`backend/data/logan_memory.db`), no ORM — the memory engine
  talks to SQLite directly. API is versioned under `/v1/`.
- **Mobile**: Expo/React Native with `expo-router` for navigation, TypeScript throughout. This remains
  the mobile client going forward; only the backend is being replaced.
- **Communication**: mobile talks to the backend over plain HTTP using a hardcoded LAN IP in
  `mobile/constants/config.ts` — a local-dev-only arrangement, not a deployment story.

## Architecture principles

These apply regardless of which specific technology is in play:

1. **Memory and the User Model are the core asset.** Everything else is a consumer of what Learning has
   written. Changes to Memory System, User Model, or Learning logic deserve the most scrutiny and the
   best test coverage in the codebase — see
   [ADR-018](DECISIONS.md#adr-018-stricter-per-layer-testing-bar-adopted-for-the-logan_core-pipeline).
2. **The external API is a contract — version it deliberately, and design it before assuming it.** The
   Logan Intelligence System defines internal layer contracts but not yet the surface a mobile client
   calls. When it's designed, treat it like the old `/v1/` prefix was intended to be treated: breaking
   changes get a new version or an explicit migration plan, never a silent change.
3. **Don't couple to infrastructure that isn't decided yet.** Database and hosting are still an open
   decision (see below) — now informed by the Operational History (append-only, queried by reference)
   vs. Logan Memory/User Model (small, actively queried) split, but not resolved by it.
4. **Keep clients simple; keep the intelligence in `logan_core`.** `logan_core` must remain client-agnostic
   — no dependency on React Native, Expo, or any specific frontend (see
   [ADR-012](DECISIONS.md#adr-012-logan-core-keeps-clean-api-boundaries-now-no-multi-client-platform-tooling-yet)).
   Business/reasoning logic never gets duplicated into a client.
5. **Config and secrets are environment-specific, never hardcoded.** See
   [STANDARDS.md](STANDARDS.md#security-practices).
6. **Prefer boring, well-understood technology.** Logan's differentiation is the reasoning/personalization
   product, not novel infrastructure. Reach for established tools (see
   [ADR-007](DECISIONS.md#adr-007-industry-standard-formatting-linting-and-type-checking-defaults)) over
   clever ones.
7. **Layer ownership boundaries are enforced, not just documented.** "Only Learning writes Memory/User
   Model," "only Policy suppresses," "only Presentation formats" — these aren't guidelines, they're the
   whole point of the architecture. A convenience shortcut that has one layer reach into another's
   responsibility defeats the design; treat any such shortcut as a bug, not a simplification.

## Data flow

The full pipeline diagram lives in
[specs/LOGAN_ARCHITECTURE_v1.0.md](specs/LOGAN_ARCHITECTURE_v1.0.md#pipeline-diagram). In short: signals
enter through five domain receptors, get normalized and connected into the World Model, evaluated for
trust and momentum, reasoned about against Memory and the User Model, confidence-scored, turned into an
attention recommendation, checked against Policy, prioritized, and delivered — with Feedback and Learning
closing the loop.

The old Memory Inbox concept (user directly confirms/rejects an uncertain memory) is preserved as a
product feature but its write path changed: it now emits a `FeedbackSignal` that Learning processes
immediately, rather than writing to memory directly — see
[ADR-019](DECISIONS.md#adr-019-memory-inbox-confirmation-routes-through-learning-as-a-feedbacksignal).
The user-facing behavior is unchanged.

## Known gaps (tracked, not yet urgent)

Called out explicitly so they're a conscious backlog, not a silent liability:

- **No authentication or per-user identity** anywhere yet, in either the historical backend or
  `logan_core`. Required before any multi-user or public deployment.
- **The historical backend's CORS is wide open** (`allow_origins=["*"]`), credentials disabled — fine for
  local dev, not acceptable once reachable from the public internet.
- **No secrets/config management pattern** established yet for either codebase.
- **The external API surface for `logan_core` is undesigned.** The internal layer contracts are locked;
  what a mobile client actually calls is explicit upcoming work, not yet decided.
- **No live data integration.** All five receptors run on simulated data in Phase 1 by design — see
  [specs/LOGAN_IMPLEMENTATION_PLAN.md](specs/LOGAN_IMPLEMENTATION_PLAN.md).

None of these block the Phase 1 vertical slice. They must be resolved before
[ADR-006](DECISIONS.md#adr-006-database-and-hosting--open-decision) is closed and before any deployment
beyond a developer's machine.

## Open questions

- **Database and hosting** — open per [ADR-006](DECISIONS.md#adr-006-database-and-hosting--open-decision).
  Phase 1 storage choices for Operational History and Logan Memory are made per-implementation, not
  locked to a production database or hosting provider yet.
- **Authentication model** — not yet designed. Needs a decision before multi-user support.
- **LLM/reasoning provider for the Reasoning Engine** — not yet chosen. Phase 1 can use rule-based or
  lightweight reasoning to prove the pipeline; when a model is chosen, prefer current latest-generation
  models and document the choice as a new ADR, since it directly affects cost, latency, and the
  analysis-vs-advice boundary in [PRODUCT.md](PRODUCT.md).
- **External API design** — see "Known gaps" above.

When any of these are resolved, add an ADR in [DECISIONS.md](DECISIONS.md) and update this document —
do not let this file drift from what's actually decided.
