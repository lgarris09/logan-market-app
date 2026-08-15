# Logan Intelligence — Current Implementation State
**Version:** 3.1.4
*Last updated: 2026-08-06/07 (V3.1.4 BATCH-1 through BATCH-5) — verified against the actual repository, not reconstructed.*

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
| Expo Router screens | EXISTS | `index.tsx` (home/Attention Field), `field-legacy.tsx` (preserved radial Opportunity Field, ADR-027), `atmosphere-preview.tsx` (Skia atmosphere Sprint-1 preview, ADR-028, unchanged), `ask.tsx`, `classic.tsx`, `demo.tsx`, `memory.tsx` |
| Attention Field (depth-of-focus, `Vessel` component) | BUILT | Wired to real `/v1/opportunities` data (V3.1.4 BATCH-4); Atmosphere is now integrated as a subordinate background layer behind the Vessels (`AttentionAtmosphere.tsx`, V3.1.4 BATCH-5, resolves ADR-028's open item) — a narrower, capped version of the Sprint 1 preview, not the full particle/demo-entity version |
| Opportunity Field (legacy radial layout) | BUILT | Preserved unchanged, reachable via menu (ADR-023, ADR-027); still calls `/v1/demo/feed` (deprecated but functional) |
| API connection | REAL (primary screen), DEMO (legacy screens) | Home screen calls the real, versioned `GET /v1/opportunities` (V3.1.4 BATCH-4, `backend/app/opportunities.py`); `field-legacy.tsx`/`demo.tsx`/`classic.tsx` remain on their existing demo/legacy routes, all still functional (`deprecated=True`, not removed) |
| WebSocket client | NOT BUILT | |
| Opportunity Card (full spec, `22_OPPORTUNITY_CARD_SPEC.md`) | NOT BUILT AS SPECIFIED, but consolidated | Two near-duplicate card components merged into one canonical `OpportunityCard` (`DeliveredItem`-based, V3.1.4 BATCH-4); still not the full `22_OPPORTUNITY_CARD_SPEC.md` contract |
| Reduced motion | BUILT | `hooks/useReducedMotion.ts` (AccessibilityInfo-based) wired into AttentionField/Vessel/LoganCore/OpportunityNode; Atmosphere layers use Reanimated's own `useReducedMotion()` (V3.1.4 BATCH-5) |
| Accessibility (labels/roles/hints/states) | BUILT (partial) | Applied to every interactive element reached in V3.1.4 BATCH-5 (Vessel, home screen menu, OpportunityNode, ask/memory/demo/classic screens); not a full accessibility audit of every screen |
| Centralized fetch / loading-empty-timeout-retry-error states | BUILT | `lib/apiClient.ts` (timeout, bounded retry, `AbortSignal` cancellation); wired into the home screen only (V3.1.4 BATCH-5) |
| Mobile test suite (Jest/RNTL) | BUILT | First ever for this repo — 19 tests (`jest-expo` preset, `@testing-library/react-native@13`); wired into CI (V3.1.4 BATCH-5) |
| Design tokens (`spacing`/`radius`/`type`) | PARTIAL | Adopted on the flagship screen (`index.tsx`) and `Vessel.tsx` wherever an exact-value match existed; not a full sweep of every screen (V3.1.4 BATCH-5) |

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
| Domain Receptors | SIMULATED by default; one real, live-verified provider exists and is config-gated into the live backend path for NVDA only (Sprint 3.6.6C) | `logan_core/receptors/simulated.py` — every domain's live backend path (`backend/app/logan_feed.py`) is simulated by default, NVDA included. `receptors/providers/`: `EarningsProvider` Protocol, `FixtureEarningsProvider` (explicitly labeled non-live, used by tests), and `FmpEarningsProvider` (Sprint 3.6.6B, live-verified against the real FMP API in 3.6.6B/3.6.6C — real EPS data observed, `STOCK_EARNINGS_BEAT` fired). `receptors/stocks_earnings.py` maps provider data into `RawSignal`. As of Sprint 3.6.6C, `backend/app/logan_feed.py` calls `FmpEarningsProvider` for NVDA specifically, but only when `STRATUS_LIVE_NVDA_EARNINGS=true` is set (default: unset/off) — see the NVDA live-path row below. Every other entity, and NVDA itself when the flag is off, remains simulated-only. See docs/DECISIONS.md ADR-042/ADR-043/ADR-044 |
| Orchestrator | BUILT | Owns Operational History writes (ADR-016); Sprint 3.6.6 added an opt-in `trigger_detection` step (`PipelineDependencies.trigger_detector`, defaults `None`) between normalization and World Model. As of Sprint 3.6.6C, `backend/app/logan_feed.py`'s shared Orchestrator instance wires this detector only when `STRATUS_LIVE_NVDA_EARNINGS=true` at construction time — with the flag off (the default), the trace is byte-for-byte identical to every pre-Sprint-3.6.6 caller (no `trigger_detection` layer entry at all, for any entity) |
| World Model, Evidence Trust, Community Intelligence, Reasoning, Mental Model, Conclusion Confidence, Opportunity Engine, Policy, Prioritization, Presentation, Memory, User Model, Active Context, Feedback, Learning | BUILT | Each has a real implementation file (`engine.py` or equivalent); every layer now has direct unit test coverage plus a full pipeline integration test (`test_pipeline_tesla.py`) — 143 `logan_core` tests, up from 95 pre-Sprint-3.6.6 (Sprint 3.6.6 added 26 trigger/receptor/pipeline-integration tests; Sprint 3.6.6B added 17 `FmpEarningsProvider` contract tests, plus 2 more after the live-verification selection-logic fix). World Model (`trigger_events` on `EnrichedEvent`) and Evidence Trust/Conclusion Confidence (`trigger_confidence_bonus`, additive/default-zero) gained small, backward-compatible extensions in Sprint 3.6.6 — see ADR-042; every pre-Sprint-3.6.6 test still passes unmodified |
| Python tooling (Black/Ruff/mypy) | BUILT | Root `pyproject.toml`; dev-only deps in `logan_core/requirements.txt` and `backend/requirements.txt`; zero suppressions except 3 documented mypy limitations on default-arg-capture lambdas |
| `backend` test suite | BUILT | 31 tests (18 pre-Sprint-3.6.6C + 13 new Sprint 3.6.6C tests covering the config-gated live NVDA path: disabled-mode trace parity, fired/non-fired live behavior, provider-failure fallback, and API-contract/no-secret-leak checks) |
| NVDA live-path config gate (Sprint 3.6.6C) | BUILT, DEFAULT OFF | `backend/app/config.py`: `live_nvda_earnings_enabled()` reads `STRATUS_LIVE_NVDA_EARNINGS` (unset/false by default) and `load_dotenv()`s `backend/.env` for `FMP_API_KEY` at import time. `backend/app/logan_feed.py`: when enabled, fetches the latest NVDA report via `FmpEarningsProvider`, pre-checks it against the same `evaluate_earnings_beat_condition()` `StocksTriggerEvaluator` uses, and substitutes it for the simulated NVDA fixture (never both — dict-keyed replacement) only when the beat condition actually fires. Falls back to the simulated NVDA fixture — never a crash, never simulated data mislabeled live — on: provider construction failure (no API key), fetch failure (network/rate-limit/malformed), no report on file, or a real report that does not satisfy `STOCK_EARNINGS_BEAT`. `internal_rank_score`, the API key, and raw provider payloads are never exposed in the `FeedItem`/`/v1/opportunities` response contract, which is otherwise unchanged. Live-verified locally against the real FMP API 2026-08-14/15: real EPS 1.87 vs. consensus 1.76 (beat_pct 6.25%), `confidence_score` 0.595. See ADR-044 |
| Mobile tooling (ESLint/Prettier/Jest) | BUILT | `mobile/eslint.config.js` (flat config, `eslint-config-expo`), `.prettierrc.json`; React-Compiler-readiness rules disabled with documented rationale. `jest-expo` + `@testing-library/react-native@13` (V3.1.4 BATCH-5) — 19 tests, this repository's first mobile test suite |
| CI (GitHub Actions) | BUILT | `.github/workflows/ci.yml` — 3 jobs: `logan_core`, `backend`, `mobile` (mobile's `jest` step runs for real as of V3.1.4 BATCH-5, previously a no-op placeholder) |
| TriggerEvent registry | PARTIALLY BUILT (Sprint 3.6.6) — one trigger code, minimal contract | `logan_core/contracts/trigger.py` (a minimal `TriggerEvent`, not the full ~60-field `TRIGGER_EVENT_FRAMEWORK.md` contract — no revision/dedup model, `domain_impacts`, `lifecycle_effect`, `seasonal_context`, `causal_relationship`, `provider_disagreement_state`, `notification_eligibility`, etc.) and `logan_core/trigger_detection/stocks.py` implement only `STOCK_EARNINGS_BEAT` from `TRIGGER_REGISTRY_STOCKS.md`. Every other stocks code (`STOCK_EARNINGS_MISS`, `STOCK_GUIDANCE_RAISED`, etc.) and every other domain's registry remain SPECIFIED — NOT IMPLEMENTED, unchanged from OD-009 (V3.1.4 BATCH-3). See docs/DECISIONS.md ADR-042, which partially — not fully — supersedes OD-009 |
| `OpportunityLifecycle` / Decay Engine | NOT BUILT IN CODE | `10_OPPORTUNITY_ENGINE.md` relabeled SPECIFIED — NOT IMPLEMENTED (V3.1.4 BATCH-3, OD-009); current `opportunity/engine.py` produces a single-pass `AttentionRecommendation`, no stage machine, no decay accumulation |
| Real (non-demo) API endpoint | BUILT (V3.1.4 BATCH-4); NVDA can be config-gated to a real live opportunity (Sprint 3.6.6C) | `GET /v1/opportunities` (`backend/app/opportunities.py`) — thin adapter over the real `logan_core` pipeline, `schema_version` metadata, `internal_rank_score` never serialized. `/v1/demo/tesla` and `/v1/demo/feed` marked `deprecated=True`, kept functional for the legacy screens. With `STRATUS_LIVE_NVDA_EARNINGS=true` and a valid `FMP_API_KEY`, the NVDA item this endpoint returns can be a genuine FMP-driven opportunity instead of the simulated fixture — see the NVDA live-path config gate row above |
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
| EAS build (mobile) | CONFIGURED, not executed | `eas.json` (development/preview/production profiles), `expo-dev-client` for Skia dev-client builds (ADR-028); bundle ID `com.garrisengineeringllc.loganmarketmobile` and EAS project ID present in `app.json`. Actual Apple-signed build (`eas build --profile development --platform ios`) requires interactive Apple ID auth this environment cannot perform — not attempted; see `V3.1.4_IMPLEMENTATION_SUMMARY.md` |

---

## What Exists

1. **`logan_core/`** — all 18 pipeline layers implemented with real code and full per-layer unit tests (95 tests), plus a passing Tesla-scenario integration test. Receptors are simulated, not live. Type-checked (mypy), formatted (Black/Ruff).
2. **Mobile app** — Attention Field (depth-of-focus) as the home screen, wired to the real `/v1/opportunities` API with a subordinate Atmosphere background layer, reduced-motion support, and accessibility labels; legacy radial Opportunity Field and other demo screens preserved. ESLint/Prettier/Jest configured (19 tests).
3. **`backend/app/`** — historical FastAPI/SQLite prototype, still running; `GET /v1/opportunities` is now a real thin adapter over `logan_core` (15 tests total).
4. **Architecture documentation** — this v3.1.3 package (28 core files + TriggerEvent framework files + 6 new ML-foundation files), plus `source_material/` (original v1.3 spec). TriggerEvent and OpportunityLifecycle/Decay content relabeled SPECIFIED — NOT IMPLEMENTED in V3.1.4 BATCH-3 (OD-009).
5. **CI** — GitHub Actions workflow running `logan_core`, `backend`, and `mobile` (now including real Jest tests) jobs on push/PR.

---

## What Is Mocked vs. Real

- **Real, tested, code-backed, and live-verified:** `FmpEarningsProvider` (Sprint 3.6.6B) against the real FMP API, and (Sprint 3.6.6C) the full path from that provider through the unmodified `logan_core` pipeline to a real `GET /v1/opportunities` response for NVDA — but only when explicitly enabled via `STRATUS_LIVE_NVDA_EARNINGS=true`; off by default.
- **Real, tested, code-backed, not yet live-verified beyond NVDA:** the remaining 17 `logan_core/` layers, the Tesla pipeline integration test, the Attention Field (wired to real data) and legacy Opportunity Field UI, and the `STOCK_EARNINGS_BEAT` trigger-detection logic itself (deterministic, unit- and integration-tested; proven against both `FixtureEarningsProvider` and, as of 3.6.6C, real FMP data for NVDA specifically — not proven for any other entity or trigger code).
- **Simulated, not live (the default):** every domain receptor (`logan_core/receptors/simulated.py`) — no external market/sports/news/etc. data source is actually polled by default. `/v1/opportunities` is a real pipeline run over simulated input for every entity except NVDA when `STRATUS_LIVE_NVDA_EARNINGS=true` is explicitly set; NVDA itself remains simulated whenever the flag is off, and falls back to simulated even with the flag on if FMP is unreachable, unauthenticated, or the real report doesn't satisfy `STOCK_EARNINGS_BEAT` (Sprint 3.6.6C — see the NVDA live-path row in the table above and ADR-044).
- **Fixture-proven, explicitly not live (Sprint 3.6.6, new category):** `receptors/providers/FixtureEarningsProvider` and the `STOCK_EARNINGS_BEAT` trigger it feeds — deliberately, visibly labeled non-live (`source_id="fixture_earnings_provider"`) so this is never mistaken for real data. Still used by the deterministic unit/contract test suite; unrelated to the live FMP path.
- **Not built at all:** the rest of the TriggerEvent registry (every stocks code besides `STOCK_EARNINGS_BEAT`, and every other domain's registry), TriggerEvent's revision/dedup model, `OpportunityLifecycle`/Decay Engine in code, WebSocket layer, Opportunity Card as fully specified in `22_OPPORTUNITY_CARD_SPEC.md`, auth, all infrastructure/deployment, an Apple-signed device build (configuration present — bundle ID, EAS project ID, dev-client build profile — but not executed in this environment; see `V3.1.4_IMPLEMENTATION_SUMMARY.md`). Live data for any entity/trigger other than NVDA/`STOCK_EARNINGS_BEAT` remains unbuilt — this sprint deliberately did not expand breadth.

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

### Sprint 3.6.6 actual progress against this target (2026-08-14)

The table above describes the target state when Sprint 2A is *complete* — left
unchanged. Actual progress this sprint, against each row:

| Item | Sprint 3.6.6 status |
|------|---------------------|
| Stocks receptor (NVIDIA) | PARTIAL — provider abstraction + receptor mapping built and tested; no live provider/credentials yet, so not REAL by this table's own definition |
| TriggerEvent: STOCK_EARNINGS_BEAT | PARTIAL — deterministic, unit- and integration-tested, fires correctly against fixture data; not yet proven against a live report |
| Normalization | REAL (unchanged — reused exactly as-is, not modified this sprint) |
| World Model (single entity) | PARTIAL — `trigger_events` populates and dedups/replaces correctly (tested); only exercised via the fixture path |
| Convergence Detector | NOT BUILT — this named component doesn't exist in code; `StocksTriggerEvaluator` plays an analogous narrow role for this one trigger code only, not a general convergence mechanism |
| Domain Analysis (Stocks) | NOT BUILT — out of scope this sprint |
| Reasoning Engine | REAL (unchanged — reused exactly as-is) |
| Opportunity Engine | REAL (unchanged — reused exactly as-is; correctly receives the trigger-boosted confidence through the existing `Dimensions.confidence` input, no new code in this layer) |
| /v1/opportunities endpoint | NOT WIRED to the new capability — still simulated-only for every entity, NVDA included |
| Mobile: Opportunity Field (1 node) | NOT TOUCHED this sprint |
| Mobile: Opportunity Card | NOT TOUCHED this sprint |
| Feedback capture (Dismiss) | NOT TOUCHED this sprint — out of scope |
| Learning System (receives signal) | NOT TOUCHED this sprint — out of scope |

Checkpoints: Checkpoint 1 partially applies — the *minimal* `TriggerEvent` contract this sprint built
matches `07_DATA_CONTRACTS.md`'s field names where implemented, but deliberately omits most of the full
canonical shape (see docs/DECISIONS.md ADR-042). Checkpoints 2 and 3 were not attempted (out of scope).

See docs/DECISIONS.md ADR-042 for the full decision record.

### Sprint 3.6.6C actual progress (2026-08-15)

Sprint 3.6.6C's scope was narrower than the Sprint 2A target table above: wire the already-proven
(3.6.6B) live NVDA earnings path into the existing `GET /v1/opportunities` endpoint, config-gated and
off by default, with no new triggers and no redesign of the pipeline. Progress against that specific
scope:

| Item | Sprint 3.6.6C status |
|------|----------------------|
| `/v1/opportunities` NVDA live path | REAL, config-gated (`STRATUS_LIVE_NVDA_EARNINGS`, default off) — live-verified against the real FMP API; returns exactly one NVDA item either way (simulated or live), never both |
| Trigger-gated substitution | REAL — the live NVDA fixture is substituted only when `STOCK_EARNINGS_BEAT` actually fires (verified via `evaluate_earnings_beat_condition` pre-check, shared with `StocksTriggerEvaluator`); a valid-but-non-beating report falls back to the simulated fixture, not a fabricated live opportunity |
| Disabled-mode trace parity | REAL — `PipelineDependencies.trigger_detector` is only constructed when the flag is on, so the disabled-mode `ExecutionTrace` is byte-for-byte identical to every pre-3.6.6C caller for every entity |
| All other entities/domains | NOT TOUCHED — still simulated-only, unaffected by this sprint regardless of the flag |
| Other stocks trigger codes (`STOCK_EARNINGS_MISS`, etc.) | NOT BUILT — explicitly out of scope; stopped here per the sprint's boundary instruction to report before adding more triggers |

See docs/DECISIONS.md ADR-044 for the full decision record, including the disabled-mode-trace and
non-fire-substitution fixes made during implementation review, and a cross-suite test-isolation issue
(`backend/app/config.py`'s import-time `load_dotenv()` leaking a real local `FMP_API_KEY` into a
`logan_core` test that assumed a clean environment) found and fixed along the way.

---

*Update this document at every session end.*
*Logan Intelligence Current Implementation State — v3.1.2 | 2026-08-03*
*v3.1.2 changes: TriggerEvent registry row added to backend table. Culture and Personal Finance receptors noted. 7 domains count updated. Reduced-motion mode added to mobile table. Sprint 2A target state updated to include TriggerEvent, World Model trigger_events, and all three Checkpoints.*
*v3.1.3 changes: Entire document rewritten from a direct repository inspection (git remote, logan_core/ and mobile/app/ directory listings) rather than left as an unverified placeholder — see the note at the top of this file. Repository, Mobile App, Backend, Infrastructure, "What Exists", and "What Is Mocked vs. Real" sections replaced with verified current state. Sprint 2A Target State section below is unchanged (it describes a future target, not current state).*
*v3.1.3 code-foundation pass (2026-08-05): Backend table updated for the actual code changes — MemoryRecord.user_id, watch/remind interaction types, EvidenceTrust/ConclusionConfidence model-version reservations, OutcomeRecord v2, SourceObservation, and the process_outcome() stub, all BUILT this session (40 tests passing, up from 28). Added a "Known ADR-034 conflict, not fixed" note documenting two pre-existing priority_score/community_momentum issues found during required inspection but left unmodified as outside this pass's authorized scope. See V3.1.3_IMPLEMENTATION_SUMMARY.md for the full session record.*
*V3.1.4 changes (BATCH-1/2/3): ADR-034 conflict fixed (community_momentum removed from ranking); priority_score renamed to internal_rank_score and made genuinely internal-only (ADR-029); ActiveContext.user_id added; decision_trace populated across all layers; contradiction path documented as reserved/unreachable rather than silently dead; fatigue/cooldown windows wired into real expiration logic; domain fields typed as the `Domain` Literal throughout; full per-layer unit test coverage added (95 logan_core + 8 backend tests, up from 40); Black/Ruff/mypy and ESLint/Prettier tooling added with CI; TriggerEvent and OpportunityLifecycle/Decay Engine content relabeled SPECIFIED — NOT IMPLEMENTED across the doc set (OD-009).*
*V3.1.4 changes (BATCH-4/5, 2026-08-07): GET /v1/opportunities shipped as a real thin adapter over logan_core (backend/app/opportunities.py), replacing the old static-fixture route; /v1/demo/tesla and /v1/demo/feed marked deprecated, kept functional. Mobile home screen migrated to the real API; Opportunity Card components consolidated into one canonical DeliveredItem-based component; hardcoded LAN IP replaced with EXPO_PUBLIC_API_BASE_URL. Reduced motion (useReducedMotion) wired into every ambient animation across AttentionField/Vessel/LoganCore/OpportunityNode and the Atmosphere layer; accessibility labels/roles/hints/states added across interactive elements reached this pass; centralized fetch (lib/apiClient.ts) added with timeout/retry/cancellation and five distinct home-screen states (loading/loaded/empty/timeout/error); this repository's first Jest/RNTL test suite added (19 tests) and wired into CI; design tokens adopted on the flagship screen and Vessel; AttentionAtmosphere.tsx integrates a capped, feed-connected subordinate Atmosphere layer into the live screen, resolving ADR-028's open item. backend test count: 15 (up from 8). mobile test count: 19 (new). See V3.1.4_IMPLEMENTATION_SUMMARY.md for the full batch-by-batch record, including mobile deployment (Apple-signed iOS build) status.*
*Sprint 3.6.6 changes (2026-08-14): first real vertical slice, narrowly scoped -- NVIDIA earnings data -> deterministic STOCK_EARNINGS_BEAT detection -> existing unmodified intelligence pipeline -> delivered opportunity. New: minimal `TriggerEvent` contract (contracts/trigger.py, not the full TRIGGER_EVENT_FRAMEWORK.md shape), `trigger_detection/stocks.py` (one trigger code only), `receptors/providers/` (EarningsProvider Protocol + FixtureEarningsProvider, explicitly labeled non-live), `receptors/stocks_earnings.py`. Small additive extensions (all backward-compatible, default-off/zero): Orchestrator's opt-in `trigger_detector` dependency, EnrichedEvent.trigger_events, EvidenceTrust.trigger_confidence_bonus, ConclusionConfidenceEngine's formula (+bonus, still deterministic -- not the ADR-032 ML surface, not ADR-015's Mental Model exclusion). backend/app/logan_feed.py and /v1/opportunities were NOT wired to this -- the live demo is unaffected, NVDA included. logan_core test count: 126 (up from 95). See docs/DECISIONS.md ADR-042, which partially supersedes OD-009 (only STOCK_EARNINGS_BEAT moved from SPECIFIED to BUILT -- the rest of the TriggerEvent framework remains SPECIFIED — NOT IMPLEMENTED). Next step: a real stocks-earnings provider + credentials, an explicit decision not made this sprint.*
*Sprint 3.6.6B changes (2026-08-14): first live provider -- `FmpEarningsProvider` (receptors/providers/fmp.py), backed by Financial Modeling Prep, satisfying the existing EarningsProvider Protocol unmodified. `httpx>=0.27` added as a genuine new logan_core runtime dependency (explicitly flagged, not silent). 17 contract tests, all httpx.MockTransport-mocked, no real network calls in the normal suite. A separate, never-pytest-collected live-verification script (logan_core/live_verification/nvda_earnings.py) added. Live-verified same day: found and fixed a genuine selection-logic bug (fetch_latest_earnings was picking the latest-dated entry regardless of whether it was reported yet, occasionally selecting an upcoming scheduled report over the latest actually-reported one) -- fixed to prefer reported entries, falling back to scheduled only when nothing has been reported. 2 regression tests added (19 total in that file). logan_core test count: 143. Not wired into backend/app/logan_feed.py or /v1/opportunities yet. See docs/DECISIONS.md ADR-043.*
*Sprint 3.6.6C changes (2026-08-15): wired the proven live NVDA path into GET /v1/opportunities, config-gated and off by default (STRATUS_LIVE_NVDA_EARNINGS, backend/app/config.py). backend/app/logan_feed.py: FmpEarningsProvider fetches the latest NVDA report when enabled; substitution only happens when the report actually satisfies STOCK_EARNINGS_BEAT (pre-checked via the same evaluate_earnings_beat_condition StocksTriggerEvaluator uses internally) -- a valid-but-non-beating report, provider failure, missing API key, or no data all fall back to the simulated NVDA fixture, never both, never mislabeled. Orchestrator's trigger_detector is only constructed when the flag is on, keeping disabled-mode's ExecutionTrace byte-for-byte identical to every pre-3.6.6C caller. Both of these behaviors were corrected during implementation review (an earlier unconditional-wiring draft would have changed the trace for every entity even with the flag off, and would have surfaced a real-but-non-firing report as a live opportunity) -- see ADR-044. Also found and fixed a cross-suite test-isolation bug exposed by config.py's import-time load_dotenv(): a logan_core FMP test that assumed no FMP_API_KEY in the environment now explicitly isolates via monkeypatch, matching its sibling test's existing pattern. 13 new backend tests added (31 total, up from 18); logan_core test count unchanged at 143 (one existing test hardened, none weakened). Live-verified locally against the real FMP API through the actual GET /v1/opportunities route: real EPS 1.87 vs. consensus 1.76 (beat_pct 6.25%), STOCK_EARNINGS_BEAT fired, confidence_score 0.595, exactly one NVDA item returned, all 10 other simulated entities untouched, no internal_rank_score/secret leak. Stopped here per the sprint's explicit boundary instruction -- no new trigger codes added. See docs/DECISIONS.md ADR-044.*
