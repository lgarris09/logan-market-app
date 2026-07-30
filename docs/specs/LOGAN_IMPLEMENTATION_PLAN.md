# Logan Intelligence System — Implementation Plan (corrected, consolidated)

Status: **Locked for Phase 1**, per [ADR-014](../DECISIONS.md#adr-014-adopt-the-logan-intelligence-system-v10-architecture-as-canonical-retire-the-fastapisqlite-sketch-as-historical).

This consolidates the original package's `README_FIRST.md`, `PROJECT_STATUS.md`,
`Logan_Engineering_Specification_v1.0`, `Logan_Engineering_Manual_v1.0`, `Logan_Claude_Handoff_Package_v1`,
and `Logan_Claude_Implementation_Prompt` into one document. Those six files overlapped heavily and
disagreed with each other in places (see [DECISIONS.md](../DECISIONS.md) ADR-015, ADR-021 for the specific
inconsistencies and how they were resolved) — this is the single source going forward instead of six
partially-conflicting ones.

## Vision

Logan is an AI intelligence platform that continuously observes multiple domains, understands events,
personalizes significance, prioritizes opportunities, explains its recommendations, learns from outcomes,
and improves over time. See [docs/PRODUCT.md](../PRODUCT.md) for the full product vision this serves.

## Core principles

- Separation of responsibilities — no layer merges another's job.
- Explainability first — every layer may contribute a decision trace.
- User-centric reasoning — personalization flows from the User Model, not generic rules.
- Learning through controlled updates — only the Learning System writes durable state.
- Modular domain expansion — new domains register without touching existing layers.
- Versioned interfaces and contracts — nothing breaks silently.

## Architecture status

Locked for Phase 1. Interfaces, ownership rules, and data contracts in
[LOGAN_ARCHITECTURE_v1.0.md](LOGAN_ARCHITECTURE_v1.0.md) and
[LOGAN_DATA_CONTRACTS_v1.0.md](LOGAN_DATA_CONTRACTS_v1.0.md) should not change without a documented
rationale — a new ADR — before the interface or contract itself is touched. Do not merge responsibilities
or simplify layers without a concrete engineering reason discovered during implementation.

## Repository structure

Per [ADR-017](../DECISIONS.md#adr-017-new-top-level-logan_core-directory-with-one-folder-per-layer), a
new top-level `logan_core/` directory, sibling to `backend/` and `mobile/`:

```
logan_core/
├── contracts/               typed objects — RawSignal through DeliveredItem, plus supporting types
├── orchestrator/            pipeline execution, retries, Operational History persistence, traces
├── receptors/                five domain receptors (stocks, sports, poly, social, news) — simulated in Phase 1
├── normalization/            RawSignal -> NormalizedSignal schema mapping (Layer 2)
├── world_model/
├── evidence_trust/
├── community_intelligence/
├── memory/                   Operational History access + Logan Memory
├── user_model/
├── active_context/
├── reasoning/
├── mental_model/              V1 pass-through slot
├── conclusion_confidence/
├── opportunity/
├── policy/
├── prioritization/
├── presentation/
├── feedback/
├── learning/
├── tests/
└── docs/                     implementation decisions log, unresolved questions, local setup
```

`backend/app/` (the existing FastAPI/SQLite prototype) is untouched and keeps running — see
[ADR-014](../DECISIONS.md#adr-014-adopt-the-logan-intelligence-system-v10-architecture-as-canonical-retire-the-fastapisqlite-sketch-as-historical).
`logan_core/` does not depend on it, and does not depend on React Native or Expo — the backend must
remain client-agnostic (see [ADR-012](../DECISIONS.md#adr-012-logan-core-keeps-clean-api-boundaries-now-no-multi-client-platform-tooling-yet)).
The external API surface a mobile client will call is **not yet designed** — that's explicit Phase 1 work
against the `DeliveredItem`/`FeedbackSignal` boundary, not assumed here.

## Development roadmap (8 phases, per ADR-021 — authoritative over the source package's 6-phase version)

1. **Contracts + Orchestrator** — typed data contracts, System Orchestrator, logging/metrics/execution
   traces, Operational History persistence.
2. **World Model** — entity graph, dedup, change detection.
3. **Memory + User Model** — Logan Memory, User Model, Active Context.
4. **Reasoning + Confidence** — Reasoning Engine, Mental Model Engine (pass-through), Conclusion
   Confidence.
5. **Opportunity + Policy + Presentation** — Opportunity Engine, Policy & Safety, Prioritization,
   Presentation & Delivery.
6. **Feedback + Learning** — Feedback Layer, Learning System.
7. **Live Integrations** — replace simulated receptors with real feeds.
8. **Optimization** — performance, cost, calibration tracking.

Phase 1 of *this* implementation effort (the vertical slice) spans roadmap phases 1–6 using **simulated
data only**; phase 7 (live integrations) does not start until the full pipeline runs reliably with
automated tests, per the original handoff instructions.

## First operational test — scope resolved

The source package's own documents disagreed on where the "first operational test" stops: `README_FIRST.md`
included Feedback + Learning; the Implementation Prompt stopped at Presentation. Resolved as follows,
since a single simulated event has no real user interaction to feed Feedback/Learning yet:

- **Test 1 (primary vertical slice)**: `Raw Signal → Normalization → World Model → Evidence Trust →
  Community Intelligence → Memory → User Model → Active Context → Reasoning → Mental Model (pass-through)
  → Conclusion Confidence → Opportunity → Policy → Prioritization → Presentation`, using the simulated
  event **"Tesla announces a major AI chip partnership."** Expected output: opportunity card
  (`DeliveredItem`), confidence score, explanation, supporting evidence, decision trace, execution
  metrics — matching the original handoff's success criteria exactly.
- **Test 2 (feedback loop)**: a simulated user interaction (e.g. "act"/confirm on the delivered item)
  proves `Feedback → Learning → MemoryWrite → Memory/User Model update`, closing the loop the first test
  intentionally leaves open.

## Engineering rules

- Only the Learning System writes Memory or User Model.
- The Opportunity Engine recommends attention; it does not execute financial actions or issue directives.
- Policy determines permitted communication; Presentation determines user experience.
- Every object is schema-versioned.
- Every layer emits observability metrics and may contribute an explainability trace.
- The System Orchestrator owns Operational History persistence — no other layer does.

## Testing strategy (per ADR-018 — supersedes ADR-005's pragmatic bar inside `logan_core/` only)

- Unit tests for every layer's core logic (e.g. `trust_score`/`priority_score` formulas, classification
  thresholds, dedup/entity-extraction rules).
- Contract validation tests for every typed object (schema, required fields, value constraints).
- Pipeline integration tests — the Tesla scenario end-to-end, and the feedback-loop scenario.
- A regression suite that runs before any contract/schema change ships.
- `mobile/` and anything outside `logan_core/` keep the pragmatic bar from
  [ADR-005](../DECISIONS.md#adr-005-pragmatic-testing-bar-during-mvppre-launch).

## Security

- Least privilege between layers — enforced by the ownership boundaries in
  [LOGAN_ARCHITECTURE_v1.0.md](LOGAN_ARCHITECTURE_v1.0.md).
- Secrets stay outside the repository (already the case, see `.gitignore`).
- Durable writes (Learning System → Memory/User Model) are auditable — every `MemoryWrite` carries
  `source_signal`, `confidence`, and `authorized_at`.
- Operational History is immutable once written.
- User-controlled deletion is a stated extension point on the Memory System, not yet built in Phase 1.

## Deferred until later phases

Live API integrations · production authentication · mobile UI polish and advanced wheel/ripple animation
(Phase 1 ships a technically simplified wheel, see [ADR-011](../DECISIONS.md#adr-011-opportunity-wheel--living-ripple-ui-is-a-required-mvp-differentiator)) ·
Mental Model Engine V2 activation (the V1 slot itself *is* built now, see ADR-015) · plugin ecosystem ·
enterprise deployment features.

## Deliverables for this vertical slice

- Working `logan_core/` repository.
- Passing automated tests (unit + contract + integration, per the testing strategy above).
- Local setup instructions (`logan_core/docs/`).
- List of implementation decisions made while building (`logan_core/docs/`).
- List of unresolved engineering questions discovered while building (`logan_core/docs/`).
