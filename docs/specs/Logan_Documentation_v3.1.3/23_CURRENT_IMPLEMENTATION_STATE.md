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
| Data contracts (Pydantic) | BUILT | `logan_core/contracts/` — `Domain` literal currently has 6 values (`stocks, sports, poly, social, news, crypto`); `culture`/`personal_finance` are documentation-only, not yet in code (see ADR-037 consequences; adding them is out of scope for V3.1.4 — broad domain expansion excluded) |
| `MemoryRecord.user_id` isolation (ADR-033) | BUILT | Required, non-empty, validated; threaded through `LearningEngine.process_feedback()` and the Orchestrator's feedback/Memory Inbox methods. `LOCAL_FOUNDER_USER_ID = "demo_user"` in `contracts/common.py` |
| `ActiveContext.user_id` (V3.1.4 BATCH-2) | BUILT | Required, non-empty, validated; `ActiveContextBuilder.build()` takes `user_id` as first positional param; threaded through `orchestrator/pipeline.py`'s `run()` |
| Feedback interaction types `watch`/`remind` | BUILT | `FeedbackEngine.interpret()` maps both deterministically; no ML behavior |
| ML model-version metadata (ADR-032) | RESERVED, NOT FUNCTIONAL | `EvidenceTrust.source_reliability_model_version`, `ConclusionConfidence.confidence_model_version`/`calibrated_at` — default `"deterministic-baseline"`; no trained model exists; scoring unchanged |
| `OutcomeRecord` v2 (ADR-036) | BUILT, UNWIRED | `schema_version "2.0"`; nothing in `logan_core/` constructs it yet — no scheduler processes outcomes (see `UNRESOLVED_QUESTIONS.md` #4) |
| `SourceObservation` contract | BUILT, UNWIRED | Future-facing sibling of `OutcomeRecord` for ADR-032 source-reliability calibration; not read by `EvidenceTrustEngine`, cannot affect current trust scores |
| `LearningEngine.process_outcome()` | STUB ONLY | Raises `NotImplementedError` — typed interface, no scheduler, no model training, no fake results (ADR-036) |
| `MentalModel.confidence` isolation (ADR-015, V3.1.4 BATCH-1) | FIXED | `ConclusionConfidence.confidence_score` derives from `EvidenceTrust.trust_score` only (plus contradiction penalty); Mental Model no longer blended in |
| `community_momentum` excluded from ranking (ADR-034, V3.1.4 BATCH-1) | FIXED | `internal_rank_score` (renamed from `priority_score`, ADR-029) no longer contains a `community_momentum` term; `global_importance = confidence.confidence_score` only |
| `internal_rank_score` public exposure (ADR-029, V3.1.4 BATCH-1) | FIXED | Renamed from `priority_score` and documented internal-only; `backend/app/logan_feed.py` now exposes ordinal `FeedItem.rank` (1-indexed) instead of any score; mobile consumers migrated to `rank` |
| Prioritization fatigue/cooldown (V3.1.4 BATCH-2) | BUILT | `FATIGUE_WINDOW`/`FATIGUE_LIMIT`/`COOLDOWN_WINDOW` wired into real expiration logic in `prioritization/engine.py`, previously unwired constants |
| `decision_trace` population | BUILT | Populated across all layers that produce a decision (normalization, world_model, evidence_trust, reasoning, conclusion_confidence, policy, prioritization, presentation, feedback, mental_model, community_intelligence); the `contradicting` field on world-model events and the `contradicts` branch in reasoning remain documented-unreachable — no deterministic contradiction rule exists without inventing per-domain semantics (out of scope) |
| Domain Receptors | SIMULATED ONLY | `logan_core/receptors/simulated.py` — no live external data source wired up for any domain |
| Orchestrator | BUILT | Owns Operational History writes (ADR-016) |
| World Model, Evidence Trust, Community Intelligence, Reasoning, Mental Model, Conclusion Confidence, Opportunity Engine, Policy, Prioritization, Presentation, Memory, User Model, Active Context, Feedback, Learning | BUILT | Each has a real implementation file (`engine.py` or equivalent); every layer now has direct unit test coverage plus a full pipeline integration test (`test_pipeline_tesla.py`) — 95 `logan_core` tests + 8 `backend` tests as of V3.1.4 BATCH-2, up from 40 |
| Python tooling (Black/Ruff/mypy) | BUILT | Root `pyproject.toml`; dev-only deps in `logan_core/requirements.txt` and `backend/requirements.txt`; zero suppressions except 3 documented mypy limitations on default-arg-capture lambdas |
| Mobile tooling (ESLint/Prettier) | BUILT | `mobile/eslint.config.js` (flat config, `eslint-config-expo`), `.prettierrc.json`; React-Compiler-readiness rules disabled with documented rationale (near-100% false positives against this codebase's classic Animated/fetch-on-mount patterns) |
| CI (GitHub Actions) | BUILT | `.github/workflows/ci.yml` — 3 jobs: `logan_core`, `backend`, `mobile` |
| TriggerEvent registry | NOT BUILT IN CODE | Documented in `TRIGGER_EVENT_FRAMEWORK.md`/`TRIGGER_REGISTRY_*.md`, explicitly relabeled SPECIFIED — NOT IMPLEMENTED across the doc set in V3.1.4 BATCH-3 (OD-009); no corresponding `logan_core/` module exists and none is planned for V3.1.4 |
| `OpportunityLifecycle` / Decay Engine | NOT BUILT IN CODE | `10_OPPORTUNITY_ENGINE.md` relabeled SPECIFIED — NOT IMPLEMENTED (V3.1.4 BATCH-3, OD-009); current `opportunity/engine.py` produces a single-pass `AttentionRecommendation`, no stage machine, no decay accumulation |
| Real (non-demo) API endpoint | NOT BUILT AS OF BATCH-3 | `/v1/demo/tesla` bridge still the only route; V3.1.4 BATCH-4 adds a versioned `/v1/opportunities` thin adapter over `logan_core` |
| WebSocket server | NOT BUILT | |

**ADR-034 conflict — resolved in V3.1.4 BATCH-1:** the prior session's known conflict (`community.momentum_score`
influencing `priority_score` both directly and via `global_importance`, and `backend/app/logan_feed.py` exposing
`priority_score` as a public field) is fixed. `internal_rank_score` no longer contains any `community_momentum`
term, `global_importance` derives from `confidence.confidence_score` only, and the public feed response exposes
an ordinal `rank` instead of any score. See `docs/DECISIONS.md` ADR-029/034 and the V3.1.4 BATCH-1 commits
(`049b7cc`, `3c0e27d`, `a922a55`, `879ce0a`, `d47779d`).

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

1. **`logan_core/`** — all 18 pipeline layers implemented with real code and full per-layer unit tests (95 tests), plus a passing Tesla-scenario integration test. Receptors are simulated, not live. Type-checked (mypy), formatted (Black/Ruff).
2. **Mobile app** — Attention Field (depth-of-focus) as the home screen, legacy radial Opportunity Field preserved, Skia atmosphere-layer preview, several legacy/demo screens. ESLint/Prettier configured.
3. **`backend/app/`** — historical FastAPI/SQLite prototype, still running, bridged to `logan_core` via one demo endpoint (8 tests).
4. **Architecture documentation** — this v3.1.3 package (28 core files + TriggerEvent framework files + 6 new ML-foundation files), plus `source_material/` (original v1.3 spec). TriggerEvent and OpportunityLifecycle/Decay content relabeled SPECIFIED — NOT IMPLEMENTED in V3.1.4 BATCH-3 (OD-009).
5. **CI** — GitHub Actions workflow running `logan_core`, `backend`, and `mobile` jobs on push/PR.

---

## What Is Mocked vs. Real

- **Real, tested, code-backed:** all 18 `logan_core/` layers, the Tesla pipeline integration test, the demo bridge endpoint, the Attention Field and legacy Opportunity Field UI.
- **Simulated, not live:** every domain receptor (`logan_core/receptors/simulated.py`) — no external market/sports/news/etc. data source is actually polled.
- **Not built at all:** TriggerEvent registry in code, `OpportunityLifecycle`/Decay Engine in code, any real (non-demo) API (until V3.1.4 BATCH-4), WebSocket layer, Opportunity Card as fully specified in `22_OPPORTUNITY_CARD_SPEC.md`, all infrastructure/deployment.

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
*v3.1.3 code-foundation pass (2026-08-05): Backend table updated for the actual code changes — MemoryRecord.user_id, watch/remind interaction types, EvidenceTrust/ConclusionConfidence model-version reservations, OutcomeRecord v2, SourceObservation, and the process_outcome() stub, all BUILT this session (40 tests passing, up from 28). Added a "Known ADR-034 conflict, not fixed" note documenting two pre-existing priority_score/community_momentum issues found during required inspection but left unmodified as outside this pass's authorized scope. See V3.1.3_IMPLEMENTATION_SUMMARY.md for the full session record.*
*V3.1.4 changes (BATCH-1/2/3): ADR-034 conflict fixed (community_momentum removed from ranking); priority_score renamed to internal_rank_score and made genuinely internal-only (ADR-029); ActiveContext.user_id added; decision_trace populated across all layers; contradiction path documented as reserved/unreachable rather than silently dead; fatigue/cooldown windows wired into real expiration logic; domain fields typed as the `Domain` Literal throughout; full per-layer unit test coverage added (95 logan_core + 8 backend tests, up from 40); Black/Ruff/mypy and ESLint/Prettier tooling added with CI; TriggerEvent and OpportunityLifecycle/Decay Engine content relabeled SPECIFIED — NOT IMPLEMENTED across the doc set (OD-009).*
