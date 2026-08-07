# Logan Intelligence — Model Contracts
**Version:** 3.1.3
*New in v3.1.3. Minimal, reserved-field contracts for model version metadata — no trained model exists this release.*

---

## Purpose

Reserve the fields future calibration/training work needs on existing contracts, now, so populating them later does not require a breaking schema change. This document defines shape only; see `MODEL_GOVERNANCE_AND_EVALUATION.md` for the process that will eventually populate these fields.

---

## Reserved fields

### On `Dimensions` / `AttentionRecommendation` (`07_DATA_CONTRACTS.md`)

```
hit_quality_model_version   string   optional, default "deterministic-baseline"
calibrated_at                ISO8601 | null   optional, default null
```

### On `ConclusionConfidence`

```
confidence_model_version    string   optional, default "deterministic-baseline"
calibrated_at                ISO8601 | null   optional, default null
```

### On `EvidenceTrust`

```
source_reliability_model_version   string   optional, default "deterministic-baseline"
```

### New: `TrainingSnapshot` reference (reserved, not populated this release)

```
training_snapshot_id   uuid | null   optional, default null
```
Reserved on any future model-governed object. Not populated until a real training-data snapshot mechanism exists (blocked on the ADR-006 database/hosting decision — see `docs/specs/09_CURRENT_STATE.md`).

---

## The `"deterministic-baseline"` marker

Every reserved `*_model_version` field defaults to the literal string `"deterministic-baseline"`, never an empty string or `null`. This is a deliberate, explicit marker meaning: *this value was produced by the existing hand-coded formula, not a trained model*. It must not be silently omitted or treated as equivalent to a real model version once one exists — code that branches on model version must treat `"deterministic-baseline"` as a distinct, always-valid fallback state, not an error condition.

---

## Non-goals this release

- No feature store, no training pipeline, no model registry service — these fields are metadata only, not backed by running infrastructure.
- No `FEATURE_AND_LABEL_REGISTRY.md` — deferred until a second real model exists (see `docs/DECISIONS.md`).
- No change to how `Dimensions`, `ConclusionConfidence`, or `EvidenceTrust` actually compute their values — the deterministic formulas in `logan_core/opportunity/engine.py`, `logan_core/conclusion_confidence/engine.py`, and `logan_core/evidence_trust/trust.py` are unchanged by this document.

---

*Logan Intelligence Model Contracts — v3.1.3 | 2026-08-04*
*New in v3.1.3.*
