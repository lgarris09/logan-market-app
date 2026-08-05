# Logan Intelligence — TriggerEvent Framework
**Version:** 3.1.3
**Status:** LOCKED for current implementation cycle; changes require ADR and user approval.

---

## Purpose

The TriggerEvent layer gives one persistent identity to a meaningful real-world event across sources, domains, revisions, and recommendations. Existing signal registries and detectors remain valid; they feed this framework.

A filing, article, price reaction, odds move, social spike, and account exposure may describe one underlying event. Logan must connect them rather than count them as independent catalysts.

## Canonical flow

Raw Signal → Normalization → Trigger Detection → TriggerEvent Identity/Deduplication → Domain Impacts → Evidence/Verification → World Model → User Relevance → Reasoning → Recommendation → Opportunity Lifecycle → Policy → Presentation/Notification → Feedback → Outcome Evaluation → Learning

## Terminology

- **Signal:** raw observed input.
- **Trigger:** meaningful event or condition detected.
- **Catalyst:** may cause a future change.
- **Confirmation:** strengthens a thesis.
- **Contradiction:** weakens a thesis.
- **Invalidation:** makes a thesis no longer valid.
- **Expiration:** no longer actionable.
- **Personal relevance trigger:** matters because of user context.
- **Suppression trigger:** reduces, delays, warns, or blocks presentation.

## Canonical TriggerEvent contract

```json
{
  "trigger_id": "trg_01J...",
  "underlying_event_key": "nvda:fq2_2026:earnings_release",
  "schema_version": "1.1",
  "trigger_code": "STOCK_EARNINGS_BEAT",
  "trigger_class": "catalyst",
  "trigger_type": "earnings_surprise",
  "trigger_status": "confirmed",
  "revision_number": 2,
  "supersedes_revision": 1,
  "event_timestamp": "2026-08-03T20:00:00Z",
  "detected_timestamp": "2026-08-03T20:00:03Z",
  "confirmed_timestamp": "2026-08-03T20:00:09Z",
  "last_updated_timestamp": "2026-08-03T20:05:00Z",
  "expiration_timestamp": null,
  "originating_signal_ids": ["sig_1","sig_2"],
  "supporting_evidence_ids": ["ev_1"],
  "contradicting_evidence_ids": [],
  "invalidating_evidence_ids": [],
  "affected_entity_ids": ["entity_nvda"],
  "affected_domains": ["stocks","prediction_markets"],
  "domain_impacts": [],
  "source_ids": ["src_sec","src_wire"],
  "original_source_id": "src_sec",
  "source_reliability": 0.96,
  "source_independence_count": 2,
  "verification_status": "primary_source_confirmed",
  "direction": "positive",
  "raw_magnitude": 17.4,
  "normalized_magnitude": 0.72,
  "severity_band": "high",
  "urgency": 0.68,
  "expected_duration": "P7D",
  "action_window_start": "2026-08-03T20:00:00Z",
  "action_window_end": "2026-08-04T20:00:00Z",
  "decay_profile": "event_fast_24h_then_slow",
  "confidence": 0.84,
  "personal_relevance": 0.74,
  "recommendation_effect": {"confidence_delta":0.12,"urgency_delta":0.08},
  "lifecycle_effect": "advance_to_emerging",
  "seasonal_context": {"earnings_season":true,"contribution":0.03},
  "historical_baseline_id": "base_nvda_eps_surprise_12q",
  "causal_relationship": "probable",
  "related_trigger_ids": [],
  "contradicting_trigger_ids": [],
  "invalidating_trigger_ids": [],
  "decision_trace_contribution": ["trace_88"],
  "provenance_chain": [],
  "provider_disagreement_state": "none",
  "legal_or_policy_gate": "pass",
  "notification_eligibility": "standard_push",
  "recalculation_required": true,
  "user_update_required": false
}
```

## DomainImpact

Each TriggerEvent may carry multiple impacts without duplication:

- domain; affected entities; direction; raw/normalized magnitude; confidence; duration; relevance; action window; recommendation contribution; lifecycle contribution; policy effect; user-exposure effect.

## Identity and deduplication

- `underlying_event_key` is stable across revisions.
- Multiple reports are clustered by entity, event type, time, semantic similarity, and primary-source lineage.
- Syndicated copies do not increase `source_independence_count`.
- One event may affect multiple scores only through explicit trace contributions.
- The same evidence cannot be counted as both catalyst and independent confirmation.
- Registry codes are exact, versioned, and cannot be silently renamed.

## Revision model

The event identity is stable; revisions are immutable snapshots. New facts create revision N+1, linked through `supersedes_revision`. Do not create an unrelated trigger merely because a source corrected the same event. Each revision records changed fields, prior/current values, reason, source, recalculation requirement, affected opportunities, and user-correction requirement.

## States

`detected`, `unverified`, `partially_verified`, `confirmed`, `strengthening`, `weakening`, `contradicted`, `invalidated`, `expired`, `archived`.

## Eligibility

Every registry code defines minimum evidence, magnitude, source quality, confirmation, cooldown, deduplication window, expiration, and no-fire conditions. No TriggerEvent is emitted merely because data exists.

## Severity normalization

Domains keep raw units and map to shared normalized magnitude. Provisional bands: negligible 0.00–0.19; low 0.20–0.39; moderate 0.40–0.59; high 0.60–0.79; extreme 0.80–1.00. Baseline, peer group, seasonal adjustment, sample size, and regime must be traceable.

## Temporal context

Temporal Context includes user-local time, market session/calendar, month/quarter/fiscal period, domain season, earnings/tax/hurricane/holiday/election cycles, countdowns, recurring user events, freshness, action-window expiration, and decay. Seasonality is evidence-based and never a generic monthly multiplier.

## Causal confidence

Allowed values: `direct`, `probable`, `possible`, `correlational`, `unknown`. Correlation may not be presented as causation.

## Policy and suppression

Legal, geographic, eligibility, privacy, safety, stale-data, manipulation, unresolved identity, and exposure-limit gates may cap, warn, suppress, block notification, or block external links. Policy gates override attractiveness.

## User-specific triggers and safeguards

Ownership, following, overexposure, correlated positions, available liquidity, goals, recent actions, and observable behavior may change relevance and risk. Behavioral triggers require observable evidence, minimum sample size, neutral wording, separate confidence, user correction, and no psychological or mental-health inference.

## Architecture ownership

Receptors observe; Normalization standardizes; Trigger Resolution identifies/deduplicates/revises; World Model maintains event/entity state; Evidence Trust verifies; User Model personalizes; Active Context selects; Reasoning resolves conflict; Policy gates; Opportunity Engine manages lifecycle; Presentation controls display/notification; Feedback and Learning evaluate outcomes.

## Required domain registries

Stocks, Sports, Prediction Markets, Crypto, Culture/Social, and Personal Finance must each define codes, schemas, thresholds, baselines, severity, deduplication, decay, action windows, recommendation/lifecycle effects, notification eligibility, suppression, and golden tests.

---
*Logan Intelligence TriggerEvent Framework — v3.1.2*
