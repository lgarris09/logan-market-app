# Logan Intelligence — Package Manifest
**Version:** 3.1.3
*Source: Architecture v1.3 FINAL (2026-07-31). Original: “source_material/28_PACKAGE_MANIFEST.md” (historical label).*
*Complete index of all documents in the v3.1.3 package. Per-row Version reflects the actual last-touched version of that specific file — most files were bulk-copied from v3.1.2 unchanged and are honestly labeled 3.1.2; only files with real v3.1.3 content changes (this session, see `18_SESSION_LOG.md`) are labeled 3.1.3.*

---

## Core Documents (00–28)

| # | File | Version | Source | Verification Status | Notes |
|---|------|---------|--------|--------------------|----|
| 00 | 00_MASTER_BRIEF.md | 3.1.3 | v3.1.2 base (updated) | VERIFIED | 7→8 domains; 17_CLAUDE_ENGINEERING_GUIDE.md reference row corrected (ADR-038) |
| 01 | 01_PRODUCT_SPECIFICATION.md | 3.1.2 | v3.1 base (updated) | VERIFIED | Culture and Personal Finance domains added; not reconciled to v3.1.3 this pass |
| 02 | 02_LOGAN_INTELLIGENCE_BRAIN.md | 3.1.2 | v3.1 base (updated) | VERIFIED | TriggerEvent as first-class pipeline object; not reconciled to v3.1.3 this pass |
| 03 | 03_MEMORY_ARCHITECTURE.md | 3.1.2 | v3.1 base (updated) | VERIFIED | TriggerEvent outcome performance branch added; not reconciled to v3.1.3 this pass |
| 04 | 04_WORLD_MODEL.md | 3.1.2 | v3.1 base (updated) | VERIFIED | trigger_events array added to WorldModel entity; not reconciled to v3.1.3 this pass |
| 05 | 05_SYSTEM_ARCHITECTURE.md | 3.1.2 | v3.1 base (updated) | VERIFIED | TriggerEvent registry in pipeline; not reconciled to v3.1.3 this pass |
| 06 | 06_LAYER_INTERFACE_SPECIFICATION.md | 3.1.3 | source_material/02_LAYER_INTERFACES.md | VERIFIED | ReasoningResult/AttentionRecommendation/MemoryRecord/Dimensions fields reconciled to 07_DATA_CONTRACTS.md (ADR-021, 029, 033, 034) |
| 07 | 07_DATA_CONTRACTS.md | 3.1.3 | v3.1.2 base (updated) | VERIFIED | Full v3.1.3 reconciliation (ADR-021, 029, 030, 033, 034, 036, 037) |
| 08 | 08_BUILD_ORDER.md | 3.1.3 | v3.1.2 base (updated) | VERIFIED | 7→8 domains (ADR-037); priority_score→internal_rank_score (ADR-029) |
| 09 | 09_READ_AND_SUGGEST.md | 3.1.2 | v3.1 base (updated) | VERIFIED | LOCKED label; sports betting deferred to V2; not reconciled to v3.1.3 this pass |
| 10 | 10_OPPORTUNITY_ENGINE.md | 3.1.2 | v3.1 base (updated) | VERIFIED | action_window_opens/closes; not reconciled to v3.1.3 this pass |
| 11 | 11_UI_PHILOSOPHY.md | 3.1.2 | v3.1 base (updated) | VERIFIED | Community momentum/edge glow LOCKED rule; not reconciled to v3.1.3 this pass |
| 12 | 12_VISUAL_LANGUAGE.md | 3.1.3 | v3.1.2 base (updated) | VERIFIED | News domain color gap flagged, not invented (ADR-037) |
| 13 | 13_BRANDING.md | 3.1.2 | v3.1 base (updated) | VERIFIED | Advisory voice rule; correction state tone; not reconciled to v3.1.3 this pass |
| 14 | 14_ENGINEERING_STANDARDS.md | 3.1.2 | v3.1 base (updated) | VERIFIED | TriggerEvent registry section; not reconciled to v3.1.3 this pass |
| 15 | 15_DECISIONS.md | 3.1.3 | v3.1.2 base (updated) | VERIFIED | DECISION-016 cross-referenced to ADR-034 clarification |
| 16 | 16_ROADMAP.md | 3.1.3 | v3.1.2 base (updated) | VERIFIED | 7→8 domains throughout (ADR-037) |
| 17 | 17_CLAUDE_ENGINEERING_GUIDE.md | 3.1.2 | v3.1 base (updated) | VERIFIED | Not governing authority (ADR-038) — clarified via 00_MASTER_BRIEF.md reference, not edited in place |
| 18 | 18_SESSION_LOG.md | 3.1.3 | v3.1.2 base (updated) | VERIFIED | 2026-08-04/05 v3.1.3 reconciliation session entry added at top |
| 19 | 19_FUTURE_IDEAS.md | 3.1.2 | v3.1 base (updated) | VERIFIED | ML trigger discovery; not reconciled to v3.1.3 this pass |
| 20 | 20_LOGAN_PRINCIPLES.md | 3.1.2 | v3.1 base (updated) | VERIFIED | Principle 13 added; not reconciled to v3.1.3 this pass |
| 21 | 21_TRENDING_ENGAGEMENT.md | 3.1.3 | v3.1.2 base (updated) | VERIFIED | Amplifier mechanism removed per ADR-034 (written by the prior session) |
| 22 | 22_OPPORTUNITY_CARD_SPEC.md | 3.1.2 | v3.1 base (updated) | VERIFIED | 80-char headline; not reconciled to v3.1.3 this pass |
| 23 | 23_CURRENT_IMPLEMENTATION_STATE.md | 3.1.3 | Direct repository inspection | VERIFIED | Rewritten from `git`/`logan_core/`/`mobile/app/` inspection, not reconstructed |
| 24 | 24_API_SPECIFICATION.md | 3.1.3 | v3.1.2 base (updated) | VERIFIED | priority_score removed from public API response examples (ADR-029) |
| 25 | 25_INTEGRATION_FEASIBILITY.md | 3.1.3 | v3.1.2 base (updated) | VERIFIED | 7→8 domains; News integration assessment flagged RESEARCH REQUIRED, not invented |
| 26 | 26_GOLDEN_TEST_SCENARIOS.md | 3.1.3 | v3.1.2 base (updated) | VERIFIED | Scenario 13: 7→8 domains (ADR-037) |
| 27 | 27_SECURITY_PRIVACY_COMPLIANCE.md | 3.1.2 | v3.1 base (updated) | VERIFIED | User controls section; not reconciled to v3.1.3 this pass |
| 28 | 28_PACKAGE_MANIFEST.md | 3.1.3 | v3.1.2 base (updated) | VERIFIED | This file; rebuilt for the actual v3.1.3 file set |

---

## TriggerEvent Framework Files

| File | Version | Status | Notes |
|------|---------|--------|-------|
| TRIGGER_EVENT_FRAMEWORK.md | 3.1.2 | WRITTEN | TriggerEvent architecture, contract, lifecycle, and enforcement rules |
| TRIGGER_REGISTRY_GLOBAL.md | 3.1.2 | WRITTEN | Master index of all registered trigger codes across all domains — no News entries yet |
| TRIGGER_REGISTRY_STOCKS.md | 3.1.2 | WRITTEN | Stocks domain trigger codes |
| TRIGGER_REGISTRY_SPORTS.md | 3.1.2 | WRITTEN | Sports domain trigger codes |
| TRIGGER_REGISTRY_PREDICTION_MARKETS.md | 3.1.2 | WRITTEN | Prediction Markets domain trigger codes |
| TRIGGER_REGISTRY_CRYPTO.md | 3.1.2 | WRITTEN | Crypto domain trigger codes |
| TRIGGER_REGISTRY_CULTURE.md | 3.1.2 | WRITTEN | Culture domain trigger codes |
| TRIGGER_REGISTRY_PERSONAL_FINANCE.md | 3.1.2 | WRITTEN | Personal Finance domain trigger codes |
| TRIGGER_REGISTRY_NEWS.md | — | **MISSING** | Referenced by `07_DATA_CONTRACTS.md` (ADR-037) but does not exist. Trigger codes are `RESEARCH REQUIRED` — not invented this session. |
| TRIGGER_SCORING_AND_CONFLICT_RULES.md | 3.1.2 | WRITTEN | How TriggerEvents affect scoring; conflict resolution |
| ENTITY_RESOLUTION.md | 3.1.2 | WRITTEN | Cross-domain entity identity resolution rules |
| NOTIFICATION_POLICY.md | 3.1.3 | WRITTEN | priority_score→internal_rank_score (ADR-029) |
| OUTCOME_EVALUATION.md | 3.1.3 | WRITTEN | Redesigned per ADR-036 (written by the prior session) |

---

## ML Foundation Files (NEW in v3.1.3)

| File | Version | Status | Notes |
|------|---------|--------|-------|
| MACHINE_LEARNING_ARCHITECTURE.md | 3.1.3 | WRITTEN | Canonical ML architecture — async supporting infrastructure, not a new layer (ADR-031) |
| LEARNING_AND_FEEDBACK_SPECIFICATION.md | 3.1.3 | WRITTEN | `process_outcome()` interface (non-functional stub this release) |
| MODEL_CONTRACTS.md | 3.1.3 | WRITTEN | Reserved model-version metadata fields; RESEARCH REQUIRED formula gaps marked, not filled |
| MODEL_GOVERNANCE_AND_EVALUATION.md | 3.1.3 | WRITTEN | Deterministic fallback, traceability, validation, rollback, approval gate (ADR-035) |
| ML_PRIVACY_AND_DATA_SEPARATION.md | 3.1.3 | WRITTEN | MemoryRecord.user_id (ADR-033); population-learning boundary (ADR-034) |
| ML_OBSERVABILITY_AND_AUDITABILITY.md | 3.1.3 | WRITTEN | decision_trace-based observability for any future learned value |

---

## Supporting Files

| File | Version | Status | Notes |
|------|---------|--------|-------|
| DOCUMENTATION_CHANGELOG_v3.1.2.md | 3.1.2 | WRITTEN | Full v3.1 → v3.1.2 delta — historical record, not updated for v3.1.3 |
| DOCUMENTATION_REFERENCE_AUDIT.md | 3.1.2 | WRITTEN | Cross-reference check across all docs — not re-run this session |
| V3.1.3_IMPLEMENTATION_SUMMARY.md | 3.1.3 | WRITTEN | New (2026-08-05) — records the first code-level pass on `logan_core/` following this doc package; see file for full detail |
| source_material/ | 1.3 FINAL | PRESERVED | Original spec (2026-07-31); 10 files; ground truth for tech specs — untouched |

---

## Total

- **Core files:** 29 numbered documents (00–28)
- **TriggerEvent framework:** 13 files listed (12 written + 1 missing/flagged: TRIGGER_REGISTRY_NEWS.md)
- **ML Foundation:** 6 new files
- **Supporting:** DOCUMENTATION_CHANGELOG + DOCUMENTATION_REFERENCE_AUDIT + V3.1.3_IMPLEMENTATION_SUMMARY + source_material/ (10 files)
- **Total:** 60 files present (29 + 12 + 6 + 3 + 10 source_material) + 1 flagged missing (TRIGGER_REGISTRY_NEWS.md)

---

## Files That Must Be Updated Regularly

| File | Update Trigger |
|------|--------------|
| `18_SESSION_LOG.md` | Every working session |
| `23_CURRENT_IMPLEMENTATION_STATE.md` | Every session that changes code |
| `15_DECISIONS.md` | When any decision is made or changes |
| `28_PACKAGE_MANIFEST.md` | When new files are added |
| `TRIGGER_REGISTRY_GLOBAL.md` | When any new trigger code is added to any domain registry |
| Domain trigger registries | When new trigger codes are added or existing codes are modified |

---

*Logan Intelligence Package Manifest — v3.1.2 | 2026-08-03*
*v3.1.2 changes: All 29 core document entries updated from v3.1 to v3.1.2 with change summaries. TriggerEvent Framework section added (12 new files). DOCUMENTATION_REFERENCE_AUDIT.md added to Supporting Files. Total count updated from 40 to 55. TRIGGER_REGISTRY_GLOBAL.md added to regularly-updated files list.*
*v3.1.3 changes: Rebuilt to reflect the actual v3.1.3 package. Per-file Version column now reflects each file's real last-touched version rather than a blanket bump — most files remain honestly labeled 3.1.2 (bulk-copied, not reconciled this pass). 6 new ML Foundation files added. TRIGGER_REGISTRY_NEWS.md listed as missing/flagged rather than silently omitted. Total corrected to 59 present + 1 flagged missing.*
*v3.1.3 code-foundation pass (2026-08-05): V3.1.3_IMPLEMENTATION_SUMMARY.md added to Supporting Files (new). ADR-036/037/038 accepted (see docs/DECISIONS.md). Total corrected to 60 present + 1 flagged missing.*


## v3.1.2 Patch
All top-level documents are version-aligned to v3.1.2. Trigger framework and operational requirements supersede their v3.1.1 sections where conflicts exist.
