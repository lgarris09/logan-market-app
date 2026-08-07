# Logan Intelligence — Memory Architecture
**Version:** 3.1.3
**TriggerEvent status:** the `trigger_event_outcome` memory branch and TriggerEvent performance retention rules described below are SPECIFIED — NOT IMPLEMENTED (V3.1.4 BATCH-3, OD-009). `logan_core/memory/store.py` writes no TriggerEvent-derived records as of V3.1.4.

---

## Overview

Memory is what separates Logan from a stateless recommendation engine. Without memory, Logan resets every session. With memory, Logan gets smarter over time — about the world, about the user, and about how its own reasoning performs.

**Critical rule (LOCKED):** Only the Learning System may write to memory. All other layers read.

---

## Two-Store Architecture

Logan maintains two separate memory stores with different purposes and retention policies.

```
┌─────────────────────────────────────────────────────────┐
│ OPERATIONAL HISTORY                                     │
│ Everything. Every signal. Every event. Every decision.  │
│ Not retained between reasoning cycles.                  │
│ Used for: audit, debugging, outcome tracking            │
│ Retention: configurable window (default 90 days raw)    │
└───────────────────────────────────────────────────────┬─┘
                                                        │
                                                        │ Learning System
                                                        │ decides what to retain
                                                        ▼
┌─────────────────────────────────────────────────────────┐
│ LOGAN MEMORY                                            │
│ Retained knowledge. Importance-ranked. Branch-based.    │
│ Used for: reasoning, personalization, hypothesis testing│
│ Retention: importance-weighted, decay-subject           │
└─────────────────────────────────────────────────────────┘
```

---

## Memory Branches

Logan Memory is branch-based, not a flat log. Each branch has its own retention rules, importance weighting, and decay behavior.

### Branch 1 — User Memory
**What it stores:** Everything Logan has learned about this specific person.

Contents:
- Explicit statements ("I own NVIDIA", "I don't bet on basketball")
- Inferred preferences (from behavior, not stated)
- Decision history (what the user acted on, dismissed, engaged with)
- Feedback history (explicit ratings or corrections)
- Risk tolerance (inferred from portfolio behavior)
- Domain interests and weights
- Reaction speed (how fast they typically act on an opportunity)
- Explanation preference (brief vs. detailed)
- Evidence threshold (how certain they need Logan to be)

Retention: Long-term for explicit statements. Behavioral inferences decay slowly if contradicted by newer behavior. Users may delete any stored record — see `27_SECURITY_PRIVACY_COMPLIANCE.md`.

---

### Branch 2 — Domain Memory
**What it stores:** Logan's understanding of how each domain behaves.

Contents:
- Source reliability scores per domain per source
- Pattern confidence scores (how often each pattern type has been accurate)
- Detector hit rates (historical accuracy per detector per domain)
- Entity relationship maps (which entities tend to move together)
- TriggerEvent historical performance (trigger codes → outcome accuracy)
- Domain-specific baseline statistics (rolling averages for anomaly detection)

Retention: Updated continuously. Historical accuracy kept indefinitely (needed for calibration). Rolling baselines kept on configurable window (default 30 days).

---

### Branch 3 — Hypothesis Memory
**What it stores:** Active and historical hypotheses about the world.

Contents:
- Current active hypotheses (formed by Hypothesis Engine, not yet confirmed or disproved)
- Confirmed hypotheses (promoted to Mental Model)
- Disproved hypotheses (kept to prevent re-forming the same wrong belief)
- Hypothesis history per entity (how beliefs about specific entities have evolved)

Retention: Active hypotheses kept until resolved. Disproved hypotheses kept for 180 days (to prevent re-formation). Confirmed hypotheses transferred to Mental Model.

---

### Branch 4 — Outcome Memory
**What it stores:** What actually happened vs. what Logan predicted.

Contents:
- Prediction records (what Logan surfaced, at what confidence, with what timing)
- Outcome records (what actually happened after the opportunity resolved)
- Accuracy deltas (predicted vs. actual, per detector type, per domain)
- TriggerEvent outcome records (trigger code → actual post-event move, per domain)
- User outcome records (did the user act? What was the result?)

Retention: Permanent for system records. User-outcome records deleted on user request. Outcome records are the foundation of learning and should never expire without explicit deletion.

---

### Branch 5 — Temporary Context Memory
**What it stores:** Session-scoped information that does not persist.

Contents:
- Active Context (current session state — expires at session end)
- In-progress reasoning (intermediate results within a pipeline run)
- Pending feedback signals (before Learning System processes them)

Retention: Session-scoped. Never written to Logan Memory directly. May be promoted to other branches by the Learning System after a session ends.

---

## Importance Scoring

Not all memories are equal. Logan assigns an importance score to every memory record to determine retention priority.

```
importance_score = (
  recency_weight       * 0.30 +    ← how recently was this relevant?
  outcome_validation   * 0.25 +    ← did this memory prove accurate?
  user_engagement      * 0.20 +    ← did the user act on this?
  signal_strength      * 0.15 +    ← how strong was the original signal?
  source_reliability   * 0.10      ← how reliable was the source?
)
```

Importance score determines:
- Whether a memory is retained past its default window
- How quickly a memory decays
- How much weight it receives during retrieval

---

## Memory Aging and Decay

Memories age based on their type, importance score, and access frequency.

### Decay Rules

| Memory Type | Default Decay | Accelerated by | Reset by |
|---|---|---|---|
| User explicit statement | Very slow (years) | User correction | Never |
| User inferred preference | Moderate | Contradicting behavior | Confirming behavior |
| Source reliability score | Slow | New accuracy data | — |
| Pattern confidence | Moderate | New outcome data | — |
| Active hypothesis | None (resolves) | Disproving evidence | — |
| Outcome record | Never | — | — |
| Domain baseline | Rolling window | — | New data |
| TriggerEvent performance | Never | — | — |

### Decay Formula

```
current_weight = initial_weight × e^(-decay_rate × days_since_last_access)

decay_rate by type:
  user_explicit_statement    0.001  (very slow)
  user_inferred_preference   0.010
  source_reliability         0.005
  pattern_confidence         0.008
  domain_baseline            rolling window only
  outcome_record             0.000  (never decays)
  trigger_event_performance  0.000  (never decays)
```

When `current_weight < 0.10`, memory is flagged for consolidation review. It is not deleted — it moves to long-term archive.

---

## Memory Consolidation

At defined intervals, the Learning System reviews low-weight memories and decides whether to:
1. Archive them (move to cold storage, available for retrieval but not active reasoning)
2. Merge them into a summary record (compress many small records into one)
3. Delete them (only for temporary/session records with no lasting value)

Outcome records are never deleted by the system. User explicit statements are never deleted without explicit user request.

---

## Retrieval

Memory retrieval is context-sensitive. Different layers request different memory shapes.

### Retrieval by layer

| Layer | What it requests | Memory branch |
|---|---|---|
| Reasoning Engine | Prior analysis on this entity, active hypotheses | Hypothesis, Domain |
| Hypothesis Engine | Prior hypotheses on this entity or domain | Hypothesis |
| Mental Model Engine | Confirmed beliefs in this domain | Hypothesis (confirmed) |
| Opportunity Engine | User interest weights, prior user value scores | User |
| Presentation | User explanation preference, reaction speed | User |
| Learning System | Outcome records, prior predictions | Outcome |

### Retrieval performance requirements

| Operation | Target latency |
|---|---|
| User Model read | < 10ms |
| Active hypothesis read | < 20ms |
| Prior analysis read (single entity) | < 50ms |
| Full user behavior history read | < 100ms |
| Outcome record query | < 200ms |

---

## Memory Write Protocol

**Only the Learning System may write. LOCKED — enforced at the infrastructure level, not just by convention.**

Write sequence:
1. Learning System receives FeedbackSignal or OutcomeRecord
2. Learning System computes what should change in memory
3. Learning System creates a MemoryWrite object with authorization timestamp
4. Memory System validates the write came from Learning System
5. Write is applied
6. Write is logged to audit trail

Any layer that attempts to write to memory directly fails with an authorization error. This includes the Reasoning Engine, Hypothesis Engine, and Opportunity Engine — they read only.

---

## MemoryRecord Schema

```json
{
  "schema_version": "1.0",
  "record_id": "uuid",
  "record_type": "see registry below",
  "content": "any",
  "domain": "string (optional)",
  "entities": ["entity_id array (optional)"],
  "source_layer": "learning_system",
  "created_at": "ISO8601",
  "last_accessed": "ISO8601 (optional)",
  "decay_weight": "float 0.0-1.0",
  "operational_ref": "uuid (optional)"
}
```

**Record Type Registry:**
- `user_statement` — explicit statement from user
- `behavior_record` — inferred from user behavior
- `feedback_record` — explicit user rating or correction
- `outcome_record` — actual result vs. predicted
- `source_reliability` — updated source credibility score
- `prior_analysis` — Logan's prior reasoning on this entity
- `preference_signal` — inferred user preference
- `correction_record` — user correction to Logan's prior claim
- `reaction_pattern` — learned user reaction speed
- `explanation_engagement` — how much user engaged with explanation detail
- `hypothesis_record` — active or resolved hypothesis
- `trigger_event_outcome` — TriggerEvent code → actual post-event behavior (accuracy)

---

## V1 Build Scope

**Build in V1:**
- Both stores (Operational History + Logan Memory)
- All 5 memory branches
- Importance scoring
- Basic decay (time-based)
- Learning System as sole writer (enforced)
- Retrieval by layer with correct shape
- User data deletion on account disconnect

**Defer to V2:**
- ML-based importance scoring
- Automated consolidation
- Cross-user pattern learning (aggregate, anonymized)
- Memory visualization for users ("Logan remembers...")
- Memory export / portability

---

*Logan Intelligence Memory Architecture — v3.1.2 | 2026-08-03*
*v3.1.2 changes: "Permanent" retention language replaced with LOCKED / long-term / explicit-request. TriggerEvent outcome records added to Branch 4. TriggerEvent performance added to Branch 2. User deletion rights referenced. Decay table updated.*
