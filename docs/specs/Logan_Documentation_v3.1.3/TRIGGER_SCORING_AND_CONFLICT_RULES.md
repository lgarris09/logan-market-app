# Logan Intelligence — Trigger Scoring and Conflict Rules
**Version:** 3.1.3
**Status:** PROVISIONAL calculation model; required behavior is LOCKED.

## Required outputs
Every evaluated trigger may affect confidence, urgency, risk, personal relevance, recommendation strength, presentation priority, lifecycle, notification, or suppression. Each effect must be traceable.

## Conceptual impact model

`impact = evidence_strength × source_reliability × verification × source_independence × normalized_magnitude × temporal_relevance × user_relevance × domain_weight × decay − contradiction_penalty − data_quality_penalty − exposure_risk_penalty`

The exact calibration is provisional. Implement ranges, caps, floors, and feature flags; never hide a score change. Trending engagement is excluded from evidence quality.

## Non-negotiable override hierarchy
1. Legal/geographic/eligibility/safety gates override attractiveness.
2. Explicit invalidation overrides ordinary confirmation.
3. Verified primary-source facts outrank rumor.
4. Independent confirmation outranks syndication count.
5. Direct evidence generally outranks inference.
6. Material recent evidence may supersede older evidence.
7. User exposure/risk limits may override attractiveness.
8. Data-quality suppression may delay or block presentation.
9. Trending never overrides weak evidence.
10. Seasonal patterns never override a direct current catalyst.

## Action types
A trigger effect must declare one or more: `adjust_score`, `cap_score`, `warning`, `recalculate`, `suppress`, `invalidate`, `block_notification`, `block_external_link`.

## Double-counting controls
- Aggregate by `underlying_event_key` before score calculation.
- Correlated child signals are attribution, not independent evidence.
- Source independence is distinct from source count.
- Cross-domain amplification is allowed only for genuinely different impact pathways and is capped.

## Provider disagreement
Timestamp-align values, identify canonical/primary providers, compute consensus where appropriate, flag outliers, reduce confidence, and suppress when disagreement exceeds domain thresholds.

## Revision and reversal
A material revision recalculates affected opportunities. The system decides: silent update, visible changed state, correction, thesis-changed alert, retirement, or post-action risk guidance.

## Historical baselines and cold start
Terms such as unusual/large/accelerating require a documented baseline. With insufficient history, lower personalization confidence, avoid behavioral claims, use explicit interests, and disclose limited personalization.

## Calibration and outcome evaluation
Evaluate prediction usefulness, timing, benchmark, risk communication, and causal uncertainty by domain. Engagement is not outcome quality.

---
*Logan Intelligence Trigger Scoring and Conflict Rules — v3.1.2*
