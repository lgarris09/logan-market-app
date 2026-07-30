# Implementation decisions — logan_core Phase 1 vertical slice

Decisions made while implementing the pipeline that weren't already captured as project-level ADRs in
[`../../docs/DECISIONS.md`](../../docs/DECISIONS.md). Per the architecture's own ground rules, these are
documented because they touch (or clarify) a locked interface, not because they're routine implementation
detail.

## 1. Presentation reads `PolicyResult`, not just `PrioritizedQueue` + `ReasoningResult` + `ConclusionConfidence`

`LOGAN_ARCHITECTURE_v1.0.md`'s Layer 13 Input list (inherited from the original package) doesn't list
`PolicyResult` as an input, but the Data Contracts validation rule for `PolicyResult` states
`required_disclaimers must appear verbatim in DeliveredItem` — unsatisfiable without Presentation reading
it. `presentation/engine.py` takes `policy_result` as an explicit parameter. This is a real gap in the
source package, not a design choice; worth folding into a future documentation-correction ADR (alongside
ADR-021) rather than leaving as an inline code comment only.

## 2. World Model accumulates corroborating signals into one `EnrichedEvent`

`WorldModel.process()` doesn't just emit a fresh single-signal event on every call — when a signal falls
into the same entity+signal_type+time-window dedup bucket as a prior event, it merges the new
`signal_id` into that event's `signal_ids` and `supporting` lists and returns the updated event. Without
this, corroboration counting (Evidence Trust) and the "supporting evidence" deliverable would never
reflect multiple sources reporting the same event — which the first operational test explicitly requires
(Tesla press release + Reuters corroboration → one event, `corroboration >= 1`).

## 3. `change_delta` is only computed on the first signal in a dedup window

A corroborating signal's free-text `value` (e.g. "Tesla confirms..." vs "Tesla announces...") isn't a
meaningful state change — it's the same event reported differently. `change_delta` is only computed when
a dedup bucket is first created, comparing against the last known value from a *previous* window, not
against other signals within the same window.

## 4. Opportunity Engine derives `global_importance`/`urgency` without reading `EvidenceTrust` directly

The spec's Input list for Layer 10 doesn't include `EvidenceTrust` — trust flows in only via
`ConclusionConfidence.confidence_score`. `global_importance` is `community.momentum_score` and
`confidence.confidence_score` combined; `urgency` is derived from `CommunitySignal.lifecycle_state` (an
`"emerging"` event is more urgent than a `"dormant"` one) plus a bump when the event is directly
actionable. This follows the spec's Input list as written rather than assuming access to a layer that
isn't listed.

## 5. Retry backoff is structural, not timed

`Orchestrator._execute` implements the retry-count and `ExecutionTrace`/`ExecutionMetrics` recording
exactly as specified, but `retry_sleep` defaults to `0.0` — there's no real exponential backoff delay yet.
Correct for a simulated-data test suite that needs to run fast; not yet validated against real transient
failures (see `UNRESOLVED_QUESTIONS.md`).

## 6. Source reputation registry and downstream-effect mapping are small static dicts

`evidence_trust/trust.py`'s `SOURCE_REPUTATION_REGISTRY` and `world_model/model.py`'s
`DOWNSTREAM_EFFECTS` are hardcoded for the domains/entities this vertical slice needed (enough to prove
the Tesla → NVIDIA → semiconductor-ETF ripple). Both are explicitly named as V1-static, matching the
source spec's own "extension point: dynamic reputation learning" / "causal link inference" notes — not a
shortcut that contradicts the architecture, just its documented V1 scope.

## 7. All stores are in-memory, process-lifetime only

`OperationalHistoryStore`, `MemoryStore`, and `PrioritizationEngine`'s per-user `AttentionState` hold
state in plain Python dicts/lists with no persistence. Consistent with
[ADR-006](../../docs/DECISIONS.md#adr-006-database-and-hosting--open-decision) remaining open — nothing
here assumes a specific database, and nothing here is durable across a process restart.
