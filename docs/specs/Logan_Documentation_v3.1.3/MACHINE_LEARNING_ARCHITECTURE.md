# Logan Intelligence — Machine Learning Architecture
**Version:** 3.1.3
*New in v3.1.3. Canonical ML architecture document — resolves the "how does ML fit the pipeline" question left open through v3.1.2.*

---

## Status

`[LOCKED]` — the framing decision below (async infrastructure, not a synchronous layer) is locked per ADR-031. Everything else in this document is `[PROVISIONAL]` until the referenced ADRs are individually accepted.

---

## Core framing decision

Machine learning in Logan is **asynchronous supporting infrastructure and typed inputs to existing layers** — it is not a new synchronous pipeline layer, and it does not change the locked layer count (see `docs/DECISIONS.md` ADR-017, ADR-031).

Two reasons this is the correct shape for Logan specifically:

1. Feedback and Learning already exist as asynchronous supporting systems alongside the numbered synchronous layers, both in this package and in the running `logan_core/` implementation. ML capability belongs in the same category — it runs on its own schedule, not once per pipeline request.
2. Every score ML would ever influence is already owned by an existing layer: Evidence Trust owns `source_score`/`trust_score`, Conclusion Confidence owns `confidence_score`, Opportunity Engine owns `hit_quality_score`/`user_value_score`, User Model owns personalization state. Those layers gain one more typed, versioned input — they are not replaced or duplicated by a parallel "ML layer."

**Consequence for `logan_core/`:** new folders (`calibration/`, `outcome_verification/`, and eventually `personal_learning/`) may be added under the same one-folder-per-responsibility convention ADR-017 already established for `feedback/` and `learning/`. This is an amendment to ADR-017's folder list, not a supersession of it, and does not renumber or add to the 18 synchronous layers.

---

## Non-negotiable constraints

These hold regardless of which ML capability is eventually built:

- **Policy remains deterministic and authoritative.** No ML logic lives inside the Policy & Safety layer itself. A model regression can never simultaneously break the safety gate, because the gate never depends on a model.
- **Models cannot bypass Policy.** A learned score is Policy's *input*, never Policy's replacement.
- **Models cannot authorize trades, wagers, orders, or execution.** `external_execution_link` remains reserved, nullable, and unrendered — see `ML_PRIVACY_AND_DATA_SEPARATION.md` and `docs/DECISIONS.md` ADR-030.
- **Popularity, engagement, community momentum, and crowd behavior cannot become evidence.** See DECISION-016 as clarified by `docs/DECISIONS.md` ADR-034.
- **Every learned value has a deterministic fallback.** No learned output may ship without a working deterministic-only path it degrades to when the model is unavailable, low-confidence, or rolled back. See `MODEL_GOVERNANCE_AND_EVALUATION.md` and ADR-035.
- **No missing formula is ever invented to unblock a document.** Where this package or its predecessors do not provide an approved formula (e.g. `hit_quality_score`'s per-domain dimension weights beyond Stocks), the gap is marked `RESEARCH REQUIRED`, not filled in silently.

---

## What ML is *not*, in this architecture

See `docs/DECISIONS.md`'s ML-review distinctions for the full set. The three most load-bearing for implementers:

- **Not a blended master score.** `priority_score` is deprecated as a public/decision score (ADR-029). `hit_quality_score` (objective) and `user_value_score` (personalized) remain separate. An internal-only ranking value may exist for pure operational ordering (e.g. notification queue priority) but must be explicitly named, documented, internal-only, never returned via a public API, and must never become Opportunity confidence or independently determine truth or policy approval.
- **Not a substitute for symbolic reasoning.** Reasoning and Evidence Trust continue to operate on typed objects via explicit rules. A learned value is one more input those layers may consume, weighted and bounded, never a replacement for the deterministic formula underneath it.
- **Not personalization by default.** Personalized ranking, notification-selection ML, outcome prediction, and population-level learning are explicitly deferred (see `docs/DECISIONS.md` ADR-032). Source-reliability calibration is the sole approved first capability.

---

## Component ownership

| Component | Type | Owner | Status this release |
|---|---|---|---|
| Outcome Verification | New, async, scheduled | System Orchestrator (extends ADR-016 role) | Interface defined (`LEARNING_AND_FEEDBACK_SPECIFICATION.md`); scheduler not implemented |
| Calibration/Training Service | New, async, batch | New `logan_core/calibration/` (folder reserved, not implemented) | Not implemented — first target is source-reliability calibration per ADR-032 |
| Personal Learning Service | New, async, deferred | Extends User Model's existing ownership | Deferred — see `docs/DECISIONS.md` ADR-032; blocked on real user volume |
| Model Registry / metadata | Cross-cutting contract fields, not a service | Contracts layer | Reserved fields only this release — see `MODEL_CONTRACTS.md` |
| Evidence Trust | Existing, extended | Unchanged | Deterministic today; reserved to accept a calibrated source-reliability input later |
| Conclusion Confidence | Existing, extended | Unchanged | Deterministic today; reserved to accept a calibration adjustment later |
| Opportunity Engine | Existing, extended | Unchanged — still the only layer that scores/ranks | Deterministic today; personalization signal is deferred |
| Learning System | Existing, extended | Unchanged — sole writer to Memory/User Model | Gains `process_outcome()` interface this release (stub, non-functional — see `LEARNING_AND_FEEDBACK_SPECIFICATION.md`) |
| Policy & Safety | Existing, unchanged in kind | Unchanged | Gains optional model-version/confidence as an additional gating input, no behavior change this release |
| Presentation | Existing, unchanged in kind | Unchanged | Gains optional model/calibration version metadata for trace display, no behavior change this release |

---

## Sprint 2 scope (this release)

Sprint 2 ships **zero trained production models**. Everything above marked "not implemented" or "reserved" stays that way this release. Sprint 2's actual code changes are documentation/contract preparation only — see `LEARNING_AND_FEEDBACK_SPECIFICATION.md` and `MODEL_CONTRACTS.md` for the exact scope, and `docs/specs/09_CURRENT_STATE.md` for what has landed in `logan_core/` as of this release.

---

## Open questions this document does not resolve

Per `docs/DECISIONS.md`'s open-decision log:

- Exact timing of `logan_core/calibration/` folder creation (schema/interface now vs. at implementation time)
- Whether the Outcome Verification scheduler's design proceeds ahead of the ADR-006 database/hosting decision
- Personal-learning timeline (wait for real users vs. build synthetic cohorts)

---

*Logan Intelligence Machine Learning Architecture — v3.1.3 | 2026-08-04*
*New in v3.1.3. Supersedes no prior document — this capability was undocumented through v3.1.2.*
