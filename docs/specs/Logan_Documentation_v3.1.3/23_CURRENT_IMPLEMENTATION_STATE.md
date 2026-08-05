# Logan Intelligence — Current Implementation State
**Version:** 3.1.3
*Last updated: 2026-08-04/05 (v3.1.3 reconciliation session) — verified against the actual repository, not reconstructed.*

> This document was rewritten from a direct repository inspection (`git remote`, `git log`, `logan_core/` and `mobile/app/` directory listings) during the v3.1.3 reconciliation session. It supersedes the prior "UNVERIFIED IMPLEMENTATION SNAPSHOT" placeholder below, which predates this repository's actual `logan_core/` build (see `docs/DECISIONS.md` ADR-014 through ADR-028) and was never updated to match it.

---

## Repository

| Item | Value |
|------|-------|
| Remote | `https://github.com/lgarris09/logan-market-app.git` |
| Repo structure | Monorepo: `logan_core/` (canonical pipeline, ADR-014/017), `backend/app/` (historical FastAPI/SQLite prototype, still running, not extended — ADR-014), `mobile/` (Expo/React Native) |
| Primary language | Python (`logan_core/`, `backend/`), TypeScript/React Native (`mobile/`) |

---

## Mobile App (`mobile/app/`)

| Item | State | Notes |
|------|-------|-------|
| Expo Router screens | EXISTS | `index.tsx` (home/Attention Field), `field-legacy.tsx` (preserved radial Opportunity Field, ADR-027), `atmosphere-preview.tsx` (Skia atmosphere layer, ADR-028), `ask.tsx`, `classic.tsx`, `demo.tsx`, `memory.tsx` |
| Attention Field (depth-of-focus, `Vessel` component) | BUILT | Not yet wired to real entity data (ADR-027); Skia atmosphere layer is a standalone preview, not yet merged into the live screen (ADR-028) |
| Opportunity Field (legacy radial layout) | BUILT | Preserved unchanged, reachable via menu (ADR-023, ADR-027) |
| API connection | DEMO ONLY | Calls `backend/app/logan_demo.py`'s single `run_tesla_demo()` route, not a real client-facing API (ADR-022) |
| WebSocket client | NOT BUILT | |
| Opportunity Card (full spec, `22_OPPORTUNITY_CARD_SPEC.md`) | NOT BUILT AS SPECIFIED | Demo screens render pipeline output directly, not the full card contract |

---

## Backend

### `logan_core/` — canonical pipeline (ADR-014)

All 18 layer folders plus `contracts/`, `orchestrator/`, and `tests/` exist with real implementation files (not stubs) as of this session:
`contracts, orchestrator, receptors, normalization, world_model, evidence_trust, community_intelligence, memory, user_model, active_context, reasoning, mental_model, conclusion_confidence, opportunity, policy, prioritization, presentation, feedback, learning`.

| Item | State | Notes |
|------|-------|-------|
| Data contracts (Pydantic) | BUILT | `logan_core/contracts/` — `Domain` literal currently has 6 values (`stocks, sports, poly, social, news, crypto`); `culture`/`personal_finance` are documentation-only, not yet in code (see ADR-037 consequences) |
| Domain Receptors | SIMULATED ONLY | `logan_core/receptors/simulated.py` — no live external data source wired up for any domain |
| Orchestrator | BUILT | Owns Operational History writes (ADR-016) |
| World Model, Evidence Trust, Community Intelligence, Reasoning, Mental Model, Conclusion Confidence, Opportunity Engine, Policy, Prioritization, Presentation, Memory, User Model, Active Context, Feedback, Learning | BUILT | Each has a real implementation file (`engine.py` or equivalent); test coverage exists for contracts, evidence_trust, feedback+learning, opportunity, policy, world_model, and a full pipeline integration test (`test_pipeline_tesla.py`) |
| TriggerEvent registry | NOT BUILT IN CODE | Documented in `TRIGGER_EVENT_FRAMEWORK.md`/`TRIGGER_REGISTRY_*.md`; no corresponding `logan_core/` module yet |
| Real (non-demo) API endpoint | NOT BUILT | Only the `/v1/demo/tesla` bridge exists (ADR-022) |
| WebSocket server | NOT BUILT | |

### `backend/app/` — historical prototype (ADR-014, untouched)

Still the only thing actually deployed/running: `main.py`, `memory_engine.py`, `memory_models.py`, `models.py`, `data.py`, `entity_registry.py`, `logan_feed.py`, and `logan_demo.py` (the `logan_core` bridge, ADR-022). Not extended with new pipeline logic per CLAUDE.md.

---

## Infrastructure

| Item | State | Notes |
|------|-------|-------|
| Database/hosting | NOT DECIDED | Open per ADR-006; SQLite + local dev only |
| CI/CD | NOT BUILT | |
| Cloud deployment | NOT CONFIGURED | |
| EAS build (mobile) | CONFIGURED | `eas.json`, `expo-dev-client` added for Skia dev-client builds (ADR-028) |

---

## What Exists

1. **`logan_core/`** — all 18 pipeline layers implemented with real code and layer-level tests, plus a passing Tesla-scenario integration test. Receptors are simulated, not live.
2. **Mobile app** — Attention Field (depth-of-focus) as the home screen, legacy radial Opportunity Field preserved, Skia atmosphere-layer preview, several legacy/demo screens.
3. **`backend/app/`** — historical FastAPI/SQLite prototype, still running, bridged to `logan_core` via one demo endpoint.
4. **Architecture documentation** — this v3.1.3 package (28 core files + TriggerEvent framework files + 6 new ML-foundation files), plus `source_material/` (original v1.3 spec).

---

## What Is Mocked vs. Real

- **Real, tested, code-backed:** all 18 `logan_core/` layers, the Tesla pipeline integration test, the demo bridge endpoint, the Attention Field and legacy Opportunity Field UI.
- **Simulated, not live:** every domain receptor (`logan_core/receptors/simulated.py`) — no external market/sports/news/etc. data source is actually polled.
- **Not built at all:** TriggerEvent registry in code, any real (non-demo) API, WebSocket layer, Opportunity Card as fully specified in `22_OPPORTUNITY_CARD_SPEC.md`, all infrastructure/deployment.

---

## Sprint 2A Target State

When Sprint 2A is complete, this document should show:

| Item | Target State |
|------|-------------|
| Stocks receptor (NVIDIA) | REAL — polling live price/news API |
| TriggerEvent: STOCK_EARNINGS_BEAT | REAL — fires on known earnings beat pattern |
| Normalization | REAL |
| World Model (single entity) | REAL — NVDA entity with trigger_events populated |
| Convergence Detector | REAL — fires and emits TriggerEvent |
| Domain Analysis (Stocks) | REAL |
| Reasoning Engine | REAL |
| Opportunity Engine | REAL |
| /v1/opportunities endpoint | REAL |
| Mobile: Opportunity Field (1 node) | REAL — correct brightness, position |
| Mobile: Opportunity Card | REAL — all required fields populated |
| Feedback capture (Dismiss) | REAL — FeedbackSignal logged |
| Learning System (receives signal) | REAL — does not need to write yet |

After Sprint 2A passes:
- Checkpoint 1: All objects match `07_DATA_CONTRACTS.md`
- Checkpoint 2: `hit_quality_score` ≠ `user_value_score` confirmed
- Checkpoint 3: FeedbackSignal → Learning System → MemoryWrite logged

---

*Update this document at every session end.*
*Logan Intelligence Current Implementation State — v3.1.2 | 2026-08-03*
*v3.1.2 changes: TriggerEvent registry row added to backend table. Culture and Personal Finance receptors noted. 7 domains count updated. Reduced-motion mode added to mobile table. Sprint 2A target state updated to include TriggerEvent, World Model trigger_events, and all three Checkpoints.*
*v3.1.3 changes: Entire document rewritten from a direct repository inspection (git remote, logan_core/ and mobile/app/ directory listings) rather than left as an unverified placeholder — see the note at the top of this file. Repository, Mobile App, Backend, Infrastructure, "What Exists", and "What Is Mocked vs. Real" sections replaced with verified current state. Sprint 2A Target State section below is unchanged (it describes a future target, not current state).*
