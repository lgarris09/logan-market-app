# Logan — Roadmap

This roadmap tracks *phases and workstreams*, not fixed dates. Update it as phases complete or priorities
shift; if a shift reflects a real decision change, add an ADR in [DECISIONS.md](DECISIONS.md) too.

Product phases (Prove the loop → Monetize → Expand) are defined in
[PRODUCT.md](PRODUCT.md#product-phases). This document tracks the **engineering** roadmap underneath
them — currently centered on building the Logan Intelligence System vertical slice in `logan_core/`, per
[ADR-014](DECISIONS.md#adr-014-adopt-the-logan-intelligence-system-v10-architecture-as-canonical-retire-the-fastapisqlite-sketch-as-historical).

## Now: Logan Intelligence System vertical slice

The current engineering focus, per [docs/specs/LOGAN_IMPLEMENTATION_PLAN.md](specs/LOGAN_IMPLEMENTATION_PLAN.md).
Eight-phase build sequence, authoritative per [ADR-021](DECISIONS.md#adr-021-package-internal-documentation-fixes):

1. **Contracts + Orchestrator** — typed data contracts, System Orchestrator, logging/metrics/execution
   traces, Operational History persistence.
2. **World Model** — entity graph, dedup, change detection.
3. **Memory + User Model** — Logan Memory, User Model, Active Context.
4. **Reasoning + Confidence** — Reasoning Engine, Mental Model Engine (V1 pass-through), Conclusion
   Confidence.
5. **Opportunity + Policy + Presentation** — Opportunity Engine, Policy & Safety, Prioritization,
   Presentation & Delivery.
6. **Feedback + Learning** — Feedback Layer, Learning System.
7. **Live Integrations** — replace simulated receptors with real feeds. *Not started until phases 1-6 run
   reliably with automated tests.*
8. **Optimization** — performance, cost, calibration tracking.

Phases 1-6 use **simulated data only** and constitute the Phase 1 vertical slice: the Tesla AI-partnership
scenario flowing end-to-end through the pipeline, per the resolved test scope in
[LOGAN_IMPLEMENTATION_PLAN.md](specs/LOGAN_IMPLEMENTATION_PLAN.md#first-operational-test--scope-resolved).

The historical `backend/` FastAPI service keeps running unmodified throughout this work — see
[ARCHITECTURE.md](ARCHITECTURE.md#historical-the-original-fastapisqlite-sketch-superseded-still-running).

## Phase 1 (product): Prove the loop

Goal: validate that Logan's reasoning-driven personalization is meaningfully more useful than a generic
feed. See [PRODUCT.md](PRODUCT.md#phase-1--prove-the-loop-current).

- [ ] Complete the Logan Intelligence System vertical slice (engineering roadmap above).
- [ ] Design the external API surface between `logan_core` and the mobile client (currently undesigned —
      see [ARCHITECTURE.md](ARCHITECTURE.md#known-gaps-tracked-not-yet-urgent)).
- [ ] Connect `mobile/` to `logan_core` once that API exists, replacing its connection to the historical
      `backend/` service.
- [ ] Instrument basic usage signals (return visits, Memory Inbox confirm/reject rates) to measure
      whether personalization is actually working.

## Phase 2 (product): Ready for real users

Goal: safe to put in front of more than one trusted local user. Gate for closing
[ADR-006](DECISIONS.md#adr-006-database-and-hosting--open-decision).

- [ ] Choose and migrate to a production-grade database and hosting provider — new ADR, informed by the
      Operational History vs. Logan Memory/User Model storage-shape split.
- [ ] Add authentication and per-user data isolation.
- [ ] Lock down CORS to real origins; remove wildcard config.
- [ ] Establish a secrets/config management pattern.
- [ ] **Required**: legal/compliance review of FOMO/urgency messaging against gambling-marketing and
      financial-promotion regulations — see
      [ADR-013](DECISIONS.md#adr-013-fomourgency-risk-tightened--betting-and-prediction-markets-must-stay-objective).
      This is a hard dependency, not optional polish.
- [ ] Design and introduce a premium tier per [PRODUCT.md](PRODUCT.md#phase-2--monetize-whats-proven).
- [ ] Activate the Mental Model Engine (V2) — confidence deltas become Opportunity Engine inputs.
- [ ] Invest in the full living-tree/ripple wheel animation, beyond Phase 1's simplified version.

## Phase 3 (product): Expand

Additional revenue streams, additional opportunity domains (business, technology, careers), and any
plugin ecosystem work. Intentionally not detailed yet — scope once Phase 1 and 2 usage data exists. See
[PRODUCT.md](PRODUCT.md#phase-3--expand).

## Explicitly not scheduled

Non-goals from [PRODUCT.md](PRODUCT.md#non-goals-for-now) are not on this roadmap at all: institutional/
advisor tooling, directive trade/bet recommendations, multi-user team accounts. If one of these becomes
real work, it needs a PRODUCT.md update and an ADR first, not just a roadmap line item.
