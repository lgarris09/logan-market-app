# Logan Intelligence System — Data Contracts v1.0 (corrected)

Status: **Locked for Phase 1**, per [ADR-014](../DECISIONS.md#adr-014-adopt-the-logan-intelligence-system-v10-architecture-as-canonical-retire-the-fastapisqlite-sketch-as-historical).
Companion to [LOGAN_ARCHITECTURE_v1.0.md](LOGAN_ARCHITECTURE_v1.0.md), which defines the layer-specific
objects (`RawSignal` through `DeliveredItem`) inline with each layer's interface. This document covers
the System Orchestrator, the cross-cutting conventions every layer must follow, and the small supporting
objects referenced by multiple layers.

## System Orchestrator

**Purpose**: Owns the execution pipeline. Contains no business logic. Coordinates layers, handles
retries, manages concurrency, schedules delayed work, records execution traces, and — per
[ADR-016](../DECISIONS.md#adr-016-orchestrator-owns-writing-operational-history) — persists Operational
History.

**Responsibilities**:
- Receive new events from Receptors.
- Execute the pipeline in the correct order (below).
- Manage parallel execution (Evidence Trust + Community Intelligence).
- **Persist every `NormalizedSignal` (and subsequent `EnrichedEvent`, `EvidenceTrust`, `CommunitySignal`,
  etc.) to Operational History**, immediately after Normalization, before World Model runs.
- Handle layer failures with a retry policy.
- Schedule delayed outcome resolution for the Learning System.
- Record an `ExecutionTrace` for every pipeline run.
- Emit `ExecutionMetrics` per layer per run.

**Execution sequence**:
```
1.  Receptors            (parallel, continuous)
2.  Normalization
2a. Orchestrator persists NormalizedSignal to Operational History
3.  World Model
4.  Evidence Trust        ┐ parallel
5.  Community Intel       ┘
6.  Memory read
7.  User Model + Active Context build
8.  Reasoning Engine
9.  Mental Model Engine   (V1 pass-through)
10. Conclusion Confidence
11. Opportunity Engine
12. Policy + Safety
13. Prioritization + Attention State
14. Presentation + Delivery
15. Feedback Layer         (async, event-driven)
16. Learning System        (async, scheduled; immediate path for high-confidence explicit feedback)
```

**Retry policy**: Transient failures retry up to 3 times with exponential backoff. Layer timeout: skip
the layer, flag in `ExecutionTrace`, continue the pipeline. Critical failure: halt the pipeline, emit an
alert, log the trace.

**Does not own**: Business logic. Scoring rules. Memory (Logan Memory, as opposed to Operational
History, which it does own). User state.

## Versioning convention

Every object includes `schema_version`, format `"<major>.<minor>"`. V1.0 is the current specification.
Minor bump = additive changes only (new optional fields). Major bump = breaking changes (field removal,
type changes). Old records remain valid until explicitly migrated. All layers must tolerate unknown
optional fields gracefully.

## Explainability convention

Every layer may append to `decision_trace` — optional in V1, required in V2. It lets Logan reconstruct
reasoning chains on demand rather than generating post-hoc explanations.

```
DecisionTraceEntry {
  layer        string      required
  rule         string      required   plain language rule that fired
  confidence   float       optional   0.0-1.0
  evidence     string[]    optional   references to supporting records
  timestamp    ISO8601     required
}
```

## Observability convention

Every layer emits `ExecutionMetrics` on completion:

```
ExecutionMetrics {
  schema_version    "1.0"    required
  layer             string   required
  pipeline_run_id   uuid     required
  event_id          uuid     optional (null for batch operations)
  latency_ms        integer  required
  success           boolean  required
  warnings          string[] optional
  retries           integer  required (default 0)
  confidence        float    optional (layer-level confidence if applicable)
  recorded_at       ISO8601  required
}
```

```
ExecutionTrace {
  schema_version    "1.0"                required
  pipeline_run_id    uuid                required
  event_id           uuid                optional
  started_at         ISO8601             required
  completed_at        ISO8601            optional
  status              "running"|"complete"|"failed"|"partial"   required
  layers              ExecutionMetrics[] required (one per layer executed)
  final_output        uuid                optional (DeliveredItem event_id)
  error                string              optional (set on failure)
}
```

## Supporting objects

```
Entity {
  entity_id     string   required   stable cross-domain identifier
  entity_type   "ticker"|"team"|"contract"|"topic"|"person"   required
  display_name  string   required
  domain        string   required
  attributes    object   optional   domain-specific properties
}

Delta {
  field         string    required
  prior_value   any       optional (null if no prior state known)
  new_value     any       required
  unit          string    optional
  changed_at    ISO8601   required
}

Reference {
  ref_type      "signal"|"event"|"memory"|"entity"   required
  ref_id        uuid      required
  description   string    optional
}
```

`Interest`, `Holding`, `Expertise`, and `DomainPref` (the `UserModel` sub-objects) are defined inline in
[LOGAN_ARCHITECTURE_v1.0.md](LOGAN_ARCHITECTURE_v1.0.md#layer-6a--user-model).

## Applied corrections

Per [DECISIONS.md](../DECISIONS.md):
- `RawSignal.domain` / `NormalizedSignal.domain` gain a fifth value, `"news"` ([ADR-020](../DECISIONS.md#adr-020-news-added-as-a-fifth-domain-receptor)),
  and a sixth, `"crypto"` ([ADR-024](../DECISIONS.md#adr-024-crypto-added-as-a-sixth-domain)).
- `ReasoningResult.personal_relevance` → `personal_relevance_narrative` ([ADR-021](../DECISIONS.md#adr-021-package-internal-documentation-fixes)) —
  do not confuse with `Dimensions.personal_relevance`, which keeps its name and stays a float score.
- Operational History's writer is now explicit: the System Orchestrator, not Memory System or World
  Model ([ADR-016](../DECISIONS.md#adr-016-orchestrator-owns-writing-operational-history)).
