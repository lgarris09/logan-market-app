# Logan Intelligence — Model Governance and Evaluation
**Version:** 3.1.3
*New in v3.1.3. Formalizes the deterministic-fallback and approval-gate requirement approved in `docs/DECISIONS.md` ADR-035.*

---

## Status

`[LOCKED]` as a standing requirement per ADR-035. The specific mechanisms below (shadow testing procedure, rollback tooling) are `[PROVISIONAL]` until a first model exists to exercise them against.

---

## The standing rule

Every ML-influenced output shipped in Logan must have, from the moment it ships:

1. **A deterministic fallback.** A working, non-ML code path the system uses when the model is unavailable, low-confidence, out-of-distribution, or rolled back. This is not optional or added later — it must exist *before* the learned path ships, not as a follow-up.
2. **Version traceability.** Every learned value traces to a `*_model_version` (see `MODEL_CONTRACTS.md`), visible in the existing `decision_trace` mechanism (see `ML_OBSERVABILITY_AND_AUDITABILITY.md`).
3. **Validation before promotion.** No calibration/model update reaches production without being checked against held-out verified outcomes first.
4. **Rollback.** Any promoted update can be reverted to the immediately prior version without a code deploy.
5. **Human approval gate.** Promotion is not automatic. This extends the existing, working Memory Inbox pattern (`logan_core/feedback/engine.py`'s `confirm_memory_inbox`/`reject_memory_inbox`, ADR-019) and the existing `REVIEW_CONFIDENCE_THRESHOLD` low-confidence hold — the same shape of gate, applied to model promotion instead of individual memory writes.

---

## Existing precedents this rule formalizes

Two real, tested mechanisms already in `logan_core/` are the template, not hypothetical future work:

- **Deterministic fallback:** `PolicyEngine.evaluate()` — when `community.bot_risk >= BOT_RISK_SUPPRESSION_THRESHOLD (0.7)`, deterministically returns `communication_mode="suppressed", permitted=False`, contract-enforced by a validator, tested at `logan_core/tests/test_policy.py`. Any future ML fallback should read the same way: a hard, inspectable, always-available deterministic answer.
- **Human approval gate:** the Memory Inbox pattern (ADR-019) and `LearningEngine`'s `REVIEW_CONFIDENCE_THRESHOLD`-based hold queue. Model promotion should use the same shape: hold, don't auto-commit, require an explicit approval action.

---

## Promotion checklist (for the first model, once ADR-032's work begins)

Not implemented this release — recorded here so it exists before it's needed:

- [ ] Held-out verified-outcome validation set exists and is disjoint from the calibration input
- [ ] New version's accuracy on the validation set is compared against the current deterministic baseline
- [ ] A human explicitly approves promotion (per the approval-gate requirement above)
- [ ] The new version is logged with a `training_snapshot_id` and validation result before it can be referenced by any `*_model_version` field
- [ ] A rollback path to the prior version (or to `"deterministic-baseline"`) is confirmed working before promotion, not after

---

## What this document does not do

It does not implement shadow testing, champion/challenger infrastructure, or drift detection — these remain `long-term` per the ML architecture review's Sprint classification, out of scope until a real model exists to test.

---

*Logan Intelligence Model Governance and Evaluation — v3.1.3 | 2026-08-04*
*New in v3.1.3.*
