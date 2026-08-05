# Logan Intelligence — Learning and Feedback Specification
**Version:** 3.1.3
*New in v3.1.3. Fills the mechanism gap identified in the V3.1.2 reconciliation and ML architecture reviews: prior documents named what Learning updates but never specified how.*

---

## Why this document exists

Through v3.1.2, `06_LAYER_INTERFACE_SPECIFICATION.md`'s Learning System section listed *outputs* (trust score updates, hypothesis-confidence updates, decay recalibration, TriggerEvent outcome performance) without ever stating a formula, counter, or averaging rule. The running code (`logan_core/learning/engine.py`) implements only the explicit-feedback write-gate; `OutcomeRecord` has never been produced or consumed by anything. This document defines the mechanism, in stages, without pretending any stage beyond the first is implemented.

---

## Distinctions this document depends on

See `docs/DECISIONS.md`'s ML-review distinctions in full. Two matter most here:

- **Weak labels vs. verified labels.** A `FeedbackSignal` (explicit or implicit) is a weak label — it reflects user reaction, not verified truth. An `OutcomeRecord` with a resolved, verifiable result is a verified label. Learning must never treat the two as equivalent-strength evidence.
- **Explicit vs. implicit feedback.** Already schema-level in `07_DATA_CONTRACTS.md` (`FeedbackSignal.interaction_type` vs. `inferred_intent`, `Interest.source: "explicit"|"inferred"`). This document does not change that split — it defines what consumes it.

---

## Stage 0 (this release): the write-gate, unchanged in mechanism

`LearningEngine.process_feedback()` continues to operate exactly as today: pick a record type from the interaction, gate on `intent_confidence >= REVIEW_CONFIDENCE_THRESHOLD (0.40)`, write via the single-writer rule or hold for review. This release adds `watch` and `remind` as valid `interaction_type` values (see `MODEL_CONTRACTS.md` / `07_DATA_CONTRACTS.md`) with no new inference logic attached to either.

## Stage 1 (interface only, this release): `process_outcome()`

A typed interface is defined this release; **no implementation of the body beyond a non-functional stub exists**:

```
LearningEngine.process_outcome(record: OutcomeRecord) -> None
```

Contract for this stub, binding on any future implementation:

- MUST NOT perform training of any kind
- MUST NOT update any score, weight, or model parameter
- MUST NOT change `logan_core`'s current scoring behavior in any way
- MUST NOT write a fabricated or synthetic result
- MUST NOT claim outcome verification exists — if called before a real Outcome Verification scheduler exists upstream, it must either no-op safely or raise `NotImplementedError`, never silently succeed with fake data

Rationale for defining the interface now rather than later: `OutcomeRecord`'s shape (see `MODEL_CONTRACTS.md`'s amendment notes and the amended `OUTCOME_EVALUATION.md`) needs a stable consumption point so the redesigned contract doesn't need a second breaking revision once real calibration work begins.

## Stage 2 (not this release, requires ADR-032's Learning Engine work): source-reliability write-back

Once approved and implemented, the mechanism will be: `Calibration/Training Service` (see `MACHINE_LEARNING_ARCHITECTURE.md`) computes a proposed source-reliability adjustment from verified `OutcomeRecord`s on a schedule, and *proposes* it to `LearningEngine` exactly as a `FeedbackSignal` is proposed today — subject to the same single-writer gate, now also gated by `MODEL_GOVERNANCE_AND_EVALUATION.md`'s validation-before-promotion requirement. The specific formula is intentionally not specified in this document — see `docs/DECISIONS.md` for the `RESEARCH REQUIRED` marker on `hit_quality_score`'s underlying weights; the source-reliability update rule is a separate, simpler calibration (a running accuracy statistic against the existing `SOURCE_REPUTATION_REGISTRY`) and will be specified in its own follow-up ADR before implementation, not silently assumed here.

## Stage 3 (deferred): Personal Learning Loop

`07_DATA_CONTRACTS.md`'s `reaction_speed`, `explanation_preference`, `evidence_threshold`, `macro_micro_preference` fields remain reserved, unpopulated slots. No algorithm is specified for deriving them from `FeedbackSignal` history in this release — deferred per ADR-032 pending real user volume. See `PERSONALIZATION_ARCHITECTURE.md`'s deferred-trigger-condition note.

---

## What this document explicitly does not do

- It does not implement a feature store, training pipeline, or model registry — see `MODEL_CONTRACTS.md` for what *is* reserved this release.
- It does not specify `hit_quality_score`'s per-domain dimension weights (Sports, Crypto, Prediction Markets, Culture, Personal Finance) — these remain `RESEARCH REQUIRED` per the reconciliation review; inventing them here would violate the "do not invent missing formulas" constraint.
- It does not change `EvidenceTrust`'s current deterministic behavior in any way this release.

---

*Logan Intelligence Learning and Feedback Specification — v3.1.3 | 2026-08-04*
*New in v3.1.3.*
