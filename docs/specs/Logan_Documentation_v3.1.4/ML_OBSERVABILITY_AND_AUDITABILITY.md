# Logan Intelligence — ML Observability and Auditability
**Version:** 3.1.3
*New in v3.1.3. Extends the existing `decision_trace` pattern to cover model-version metadata — no new mechanism invented.*

---

## The existing precedent this extends

`logan_core/`'s `decision_trace` field (present on 12+ contracts, e.g. `logan_core/contracts/opportunity.py`) is a real, working, tested audit mechanism. `OpportunityEngine.evaluate()` already appends a step-by-step trace explaining exactly how `priority_score` (soon: `hit_quality_score`/`user_value_score` per ADR-029) was derived, validated in `logan_core/tests/test_opportunity.py`. This is decision-step-level explainability, not per-feature attribution — that distinction is preserved, not blurred, by this document.

---

## What changes this release

Nothing functional. `decision_trace` entries may now optionally reference a `*_model_version` field (see `MODEL_CONTRACTS.md`) when one is populated — since every such field defaults to `"deterministic-baseline"` this release, every trace entry continues to read exactly as it does today: a deterministic-rule explanation.

---

## Requirement for any future model

When a real model version other than `"deterministic-baseline"` exists, its contribution to a `decision_trace` entry must be:

- Attributable to that specific version (not "a model," but *which* model, trained/calibrated when)
- Distinguishable from a deterministic-rule step in the same trace — a user or reviewer inspecting the trace must be able to tell which parts of a conclusion came from a fixed formula and which from a learned adjustment
- Never rendered with more rhetorical certainty than the deterministic baseline would carry for the same conclusion (see `docs/DECISIONS.md`'s model-confidence-vs-opportunity-confidence distinction)

---

## Non-goals this release

No feature-attribution tooling (e.g. SHAP-style per-feature contribution breakdowns) — out of scope until a model complex enough to need it exists. Source-reliability calibration (ADR-032's approved first use case) has few enough inputs that decision-step tracing, as already implemented, is sufficient.

---

*Logan Intelligence ML Observability and Auditability — v3.1.3 | 2026-08-04*
*New in v3.1.3.*
