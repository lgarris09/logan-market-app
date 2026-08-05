# Logan Intelligence — Outcome Evaluation
**Version:** 3.1.3
*New in v3.1.2. Amended in v3.1.3: outcome records redesigned from a simplistic win/loss framing to a structured evaluation object per `docs/DECISIONS.md` ADR-036; `correction_state` wired as an actual Learning System input (previously display-only); false-negative, ranking-quality, and notification-usefulness scope added as explicitly-deferred (not silently absent).*

---

## Purpose

Outcome evaluation is how Logan learns whether its intelligence was correct. It is the feedback loop that connects a surfaced opportunity, through the user's experience, to Logan's future accuracy.

Without outcome evaluation, Logan has no way to improve. It would repeat the same reasoning patterns regardless of whether they produced accurate intelligence.

---

## When Outcome Evaluation Occurs

An opportunity enters the **Outcome** stage when:
1. The underlying event resolves (e.g., earnings are reported, a game is played, a contract expires)
2. The Action Window closes (if applicable)
3. The opportunity decays to inaction (no user interaction, signal fades)

After the Outcome stage, the opportunity enters the **Learning** stage, where outcome evaluation runs.

---

## What Is Being Evaluated

Outcome evaluation measures three things:

### 1. Hit Quality Accuracy

Was Logan's `hit_quality_score` correct given what actually happened?

```
hit_accuracy = 1.0 - abs(predicted_hit_quality - actual_outcome_quality)
```

**actual_outcome_quality** is determined by the domain-specific outcome evaluator:
- **Stocks:** Did the price move in the predicted direction? By approximately the implied magnitude?
- **Sports:** Did the game result match the signal direction (e.g., the underdog Logan identified won)?
- **Prediction Markets:** Did the contract resolve in the direction implied by Logan's analysis?
- **Culture:** Did the artist/content continue to gain momentum as predicted?
- **Personal Finance:** Did the macro event lead to the market/rate changes Logan's reasoning implied?

### 2. Thesis Accuracy

Was Logan's hypothesis — the stated reason the opportunity was worth attention — correct?

This is a qualitative evaluation driven by:
- Whether the stated `what_happened` triggers actually played out
- Whether the `why_now` timing was correct
- Whether `contradicting_evidence` Logan surfaced proved prescient (suggests good calibration)

For V1, thesis accuracy is logged but not automatically scored — it requires the Hypothesis Engine to compare outcome data against the original hypothesis. This is a V2 automation target.

### 3. TriggerEvent Predictive Accuracy

**Amended in v3.1.3.** Per-trigger accuracy is not a bare win/loss tally — per ADR-036, every evaluated trigger contribution carries the full structured shape defined in "Outcome Object" below, not a single boolean. A trigger's contribution is characterized along multiple independent dimensions (did it fire correctly, was the underlying event resolvable at all, how reliable was the evaluation), because collapsing these into "win" or "loss" destroys information the Learning System needs — a trigger that fired correctly on an unresolvable/ambiguous outcome is not the same case as one that fired incorrectly on a cleanly-resolved outcome, and treating them identically would corrupt future calibration.

```
For each trigger_code in opportunity.trigger_events:
    record a TriggerContribution (see Outcome Object) — not a win/loss increment
    running_accuracy[trigger_code] is derived FROM the structured record set,
    only after filtering to entries where resolvability == "resolved" and
    verification_quality is at or above a documented minimum (not yet specified —
    RESEARCH REQUIRED, see docs/DECISIONS.md)
```

This produces per-code accuracy rates that feed the Learning System — see `LEARNING_AND_FEEDBACK_SPECIFICATION.md`'s `process_outcome()` interface. Over time, trigger codes with low predictive accuracy are flagged for registry review. **As of v3.1.3, this remains a specified design, not implemented code** — `process_outcome()` is a non-functional stub; no accuracy rate is currently computed anywhere in `logan_core/`.

---

## Outcome Sources

Logan uses these sources to determine outcomes:

| Domain | Primary Outcome Source | Fallback |
|--------|----------------------|----------|
| Stocks | Price data (Alpaca/Polygon) — compare to thesis direction | None |
| Sports | Game result from sports data provider | None |
| Prediction Markets | Contract resolution from Kalshi/Polymarket API | None |
| Culture | Chart position and stream data 7 days post-trigger | Social signal |
| Personal Finance | Market reaction data (rate changes, asset prices) 3 days post-announcement | BLS/Fed subsequent releases |

**V1 limitation:** Outcome sources require the Domain Receptor to still be running. If the receptor has been paused or the data provider is unavailable, outcome evaluation is deferred (not skipped — deferred until data is available).

---

## Outcome Evaluation Timeline

| Domain | Evaluation Wait Period | Rationale |
|--------|----------------------|-----------|
| Stocks (earnings) | 5 trading days | Enough time for initial market reaction to settle |
| Sports | 24 hours after game | Game is complete |
| Prediction Markets | At contract resolution | Contract resolves definitively |
| Culture | 7 days | Enough time for momentum signals to confirm or reverse |
| Personal Finance | 5 trading days | Market reaction to macro data |

---

## Outcome Object

**Redesigned in v3.1.3 per ADR-036.** The prior version of this object (see `DOCUMENTATION_CHANGELOG_v3.1.3.md` for the full diff) recorded a simplistic direction/magnitude win-loss comparison. That framing is replaced: outcome evaluation must never be reducible to "the opportunity was right" or "the opportunity was wrong," because that framing cannot represent an opportunity that never resolved, a prediction that was correct for the wrong reason, or evidence too weak to verify either way. The structured object below is required to preserve, at minimum: evaluation horizon, observed result, resolvability, invalidation status, verification quality, source contribution, and prediction/claim type — per the approved Phase 3 outcome-trace requirements.

```json
{
  "schema_version": "2.0",
  "opportunity_id": "opp_abc123",
  "prediction_id": "pred_def456",
  "user_id": "user_local_founder",
  "entity_id": "entity_nvda",
  "trigger_event_ids": ["trig_001", "trig_002"],
  "evidence_ids": ["ev_001", "ev_002", "ev_003"],
  "raw_predicted_value": {
    "claim_type": "directional_price_move",
    "thesis_direction": "up",
    "thesis_magnitude_implied_pct": 8.0
  },
  "created_at": "2026-08-03T14:22:00Z",
  "evaluation_horizon": {
    "value": 5,
    "unit": "trading_days",
    "domain_source": "OUTCOME_EVALUATION.md#outcome-evaluation-timeline"
  },
  "evaluated_at": "2026-08-10T09:00:00Z",

  "resolvability": "resolved",
  "observed_result": {
    "actual_direction": "up",
    "actual_magnitude_pct": 6.4,
    "outcome_source": "alpaca_price_data"
  },

  "invalidation_status": "none",
  "invalidation_conditions": [
    "thesis invalidated if price reverses below entry basis before evaluation_horizon"
  ],

  "verification_quality": {
    "level": "verified",
    "method": "direct_price_data_comparison",
    "confidence_in_verification": 0.95
  },

  "source_contribution": [
    {"trigger_code": "STOCK_EARNINGS_BEAT", "evidence_id": "ev_001", "contribution_assessment": "correctly_anticipatory"},
    {"trigger_code": "STOCK_OPTIONS_FLOW_SURGE", "evidence_id": "ev_002", "contribution_assessment": "correctly_anticipatory"}
  ],

  "prediction_or_claim_type": "directional_price_move",

  "decision_trace_ref": "trace_opp_abc123_v1",
  "contradicting_evidence_proved_significant": false,
  "correction_state_at_evaluation": "original",
  "user_acted": true,
  "user_feedback_type": "acted",
  "learning_system_received": false
}
```

**Field notes:**
- `resolvability` is one of `"resolved" | "unresolved_pending" | "unresolvable_data_unavailable" | "unresolvable_ambiguous"` — an opportunity that faded without a clean event is `"unresolvable_ambiguous"`, not a silent omission or a forced win/loss guess.
- `verification_quality.level` is one of `"verified" | "partially_verified" | "self_reported" | "unverifiable"` — this is what row 3's filtering (above) uses before an outcome is allowed to influence any future accuracy rate.
- `invalidation_status` is one of `"none" | "invalidated_before_resolution" | "invalidated_at_resolution"` — distinct from `correction_state` (Presentation-facing) though related; see the Correction State section below.
- `learning_system_received: false` in the example above is intentional — as of v3.1.3, `process_outcome()` is a stub (see `LEARNING_AND_FEEDBACK_SPECIFICATION.md`), so no outcome object has actually been received and processed by a running Learning System yet. This field must not be hardcoded `true` in any example or fixture that doesn't have a real consumer.

---

## Correction State as a Learning Input (new in v3.1.3)

**Gap this section closes:** through v3.1.2, `correction_state`/`correction_note` were scoped purely as `DeliveredItem` (Presentation) display fields in both this package and the running code — a reversed thesis was shown to the user but never fed back to adjust the trigger or source that produced the original, incorrect thesis. The Learning System's documented inputs were explicitly only `FeedbackSignal[]`/`OutcomeRecord[]`.

**Resolution:** `correction_state_at_evaluation` (see Outcome Object above) captures the correction state *as of the outcome evaluation*, so a reversed thesis is visible to `process_outcome()`'s future implementation as ordinary outcome data, not a separate, unreachable Presentation-only fact. This is a contract/interface change only in v3.1.3 — no scoring adjustment based on corrections is implemented yet, consistent with `process_outcome()` remaining a non-functional stub.

---

## What Outcome Evaluation Feeds

Outcome results are passed to the Learning System, which updates:

1. **TriggerEvent performance metrics** — per-code accuracy rates in the Memory System
2. **Detector calibration** — were the detectors that fired for this opportunity well-calibrated?
3. **Domain analysis accuracy** — was the domain_analysis layer's hit_quality prediction correct?
4. **User prediction calibration** — if the user acted, was their action rewarded? This feeds user_value_score calibration.

The Learning System writes these updates asynchronously. The Opportunity Engine does not wait for learning before surfacing future opportunities — learning is a background process.

---

## V1 Automation Scope

In V1, the following aspects of outcome evaluation are automated:
- Outcome data collection from Domain Receptors (automated)
- Direction accuracy check (automated)
- TriggerEvent outcome logging (automated)
- Learning System signal write (automated)

The following are deferred to V2:
- Thesis accuracy scoring (requires NLP comparison of hypothesis vs. outcome text)
- Automated outcome detection for all edge cases (V2 extension point noted in `19_FUTURE_IDEAS.md`)
- Counterfactual scoring ("what would have happened if the user had acted?" — V2, extension point reserved)

---

## Non-Outcome Situations

Not every opportunity has a clean outcome:

| Situation | Treatment |
|-----------|-----------|
| Signal fades without event | Record as "inconclusive" — no hit/miss logged |
| User dismissed before event | Record dismissal; still evaluate outcome for Logan's accuracy tracking (not for user learning) |
| Data unavailable for outcome | Defer evaluation; do not fabricate outcome |
| Opportunity reversed (thesis changed) | Correction state is noted; evaluate the revised thesis, not the original |

---

## Scope Explicitly Deferred, Not Silently Absent (new in v3.1.3)

Three capabilities were entirely unaddressed through v3.1.2, in both this package and the running code. They remain unimplemented, but are now explicitly scoped here rather than absent without record:

| Capability | Why it's not implemented yet | Deferred to |
|---|---|---|
| False-negative tracking | Requires an independent ground-truth feed of "this event happened" regardless of whether Logan surfaced it — no such feed exists | Post-Sprint-2 design work |
| Ranking-quality evaluation | Requires multiple concurrently-ranked opportunities with resolved outcomes compared against their relative order, not just per-item accuracy | Post-Sprint-2, after first ML use case (ADR-032) |
| Notification usefulness | Requires notification-level outcome tracking distinct from general `FeedbackSignal` | Post-Sprint-2 |

---

*Logan Intelligence Outcome Evaluation — v3.1.3 | 2026-08-04*
*v3.1.3 changes: Outcome Object redesigned from win/loss to a structured evaluation object (ADR-036) preserving evaluation horizon, observed result, resolvability, invalidation status, verification quality, source contribution, and prediction/claim type. `correction_state_at_evaluation` added as a genuine Learning System input. False-negative, ranking-quality, and notification-usefulness scope explicitly recorded as deferred. `process_outcome()` referenced as the (non-functional stub) consumption interface — see `LEARNING_AND_FEEDBACK_SPECIFICATION.md`.*
