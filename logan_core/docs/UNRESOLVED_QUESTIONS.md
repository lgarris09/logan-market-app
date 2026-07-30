# Unresolved engineering questions — logan_core Phase 1 vertical slice

Discovered while building. None of these block the vertical slice (simulated Tesla scenario, end-to-end,
passing tests) — they need a decision before the next roadmap phase that touches them.

## 1. Mental Model hypothesis identity

`MentalModelEngine` keys hypotheses as `f"{domain}:{significance_prefix}"` — a string derived from the
first clause of `ReasoningResult.significance`. That's fragile: two genuinely different hypotheses about
the same entity could collide, or near-duplicate phrasing could fail to merge into the same hypothesis.
This works for a single simulated scenario; it needs a real identity scheme (entity + topic + claim
shape, or an embedding-based match) before V2 activation makes Mental Model Engine output actually
influence the Opportunity Engine — a wrong merge/split there would corrupt confidence tracking.

## 2. Operational History storage shape at scale

Currently an in-memory list queried linearly by reference/kind/domain. [ADR-006](../../docs/DECISIONS.md#adr-006-database-and-hosting--open-decision)
covers the general database/hosting decision, but Operational History specifically (append-only, retained
indefinitely, queried by reference rather than joined against) may warrant a different storage engine than
Logan Memory / User Model (which are small and actively queried) even once ADR-006 is resolved — e.g. an
object/log store versus a relational database. Worth a dedicated follow-up ADR rather than assuming one
database serves both.

## 3. How engagement samples get scoped to an event in a real system

`CommunityIntelligenceEngine.measure()` takes `samples: list[EngagementSample]` as a direct parameter —
this vertical slice's caller decides what counts as "the engagement stream for this event." With live
data, that's a real design question: per-entity? per-event? a rolling time window? This needs to be
resolved before Phase 7 (Live Integrations) replaces simulated receptors.

## 4. `OutcomeRecord` / delayed learning path is unimplemented

The `OutcomeRecord` contract exists (`outcome_type`, `delay_window`, `learning_applied`), but no scheduler
processes delayed outcomes in this slice — only the immediate `FeedbackSignal` path (including the
Memory Inbox confirm/reject route, ADR-019) was built. A real "hours to months" delayed-resolution
scheduler is later-phase work, but the `LearningEngine` interface should be validated against it earlier
rather than discovering contract gaps at Phase 7.

## 5. External API surface between `logan_core` and `mobile/`

Already flagged in [`../../docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md#known-gaps-tracked-not-yet-urgent) —
repeating here because it's the most consequential open item this slice doesn't touch. Proving the
internal pipeline works end-to-end (this vertical slice) is a different problem from proving a client can
consume it. Next roadmap step, not yet started.

## 6. Should the Presentation/PolicyResult gap become a formal spec-correction ADR?

See `IMPLEMENTATION_DECISIONS.md` #1 — Presentation needs `PolicyResult` despite the original Input list
omitting it. Fixed pragmatically in code with an inline explanation. Recommend folding this into a future
documentation-correction ADR (same treatment as ADR-021) the next time `docs/specs/` gets revisited, so
the locked spec document itself stops disagreeing with what the code actually needs.

## 7. Real retry/backoff timing is unvalidated

See `IMPLEMENTATION_DECISIONS.md` #5 — retry *counting* and trace recording work; actual exponential
backoff delay is a no-op by default. Needs real timing and a test against genuinely flaky I/O before
Phase 7 (Live Integrations) introduces real network calls that can actually time out or rate-limit.
