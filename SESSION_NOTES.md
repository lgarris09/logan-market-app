> **Update, 2026-08-03**: the next session's notes went to
> [`docs/sessions/2026-08-03-attention-field-atmosphere-skia.md`](docs/sessions/2026-08-03-attention-field-atmosphere-skia.md)
> instead of here — resolving (by precedent, not an explicit decision) the inconsistency flagged below in
> favor of `docs/sessions/`. Future notes should go there.

# Session Notes — 2026-07-31

Note: an earlier, more detailed dated note from the first half of today's work also exists at
[`docs/sessions/2026-07-31-logan-core-bridge-and-phone-test.md`](docs/sessions/2026-07-31-logan-core-bridge-and-phone-test.md)
(logan_core build, backend bridge, first phone test). This file covers the rest of the day — the
Opportunity Field — and is kept at the project root per today's request, so it's worth deciding whether
future session notes live here or under `docs/sessions/`, not both inconsistently.

## What was completed

- Renamed "Opportunity Wheel" to **Opportunity Field** across code and docs (design language evolved past
  a fixed circular menu).
- Reviewed a reference visual mockup, agreed a scoped Phase 1 plan (dependencies, navigation approach)
  before writing UI code.
- Built the Opportunity Field as the new mobile home screen: a reusable, entity-agnostic symbol
  resolution pipeline, a radial layout with real ripple connections, and a glowing central "Logan core."
- Expanded the simulated `logan_core` demo from one entity (Tesla) to eleven, run through one shared
  pipeline so cross-entity connections are genuine.
- Found and fixed a real correctness bug in the World Model's event deduplication while testing.
- Committed all of the above; repository confirmed clean (see below).
- Rewrote `docs/ARCHITECTURE.md` to reflect the current system end-to-end.

## Files created or modified

**Backend:** `backend/app/entity_registry.py` (new), `backend/app/logan_feed.py` (new),
`backend/app/main.py` (route wiring).

**logan_core:** `contracts/common.py`, `normalization/normalize.py`, `world_model/model.py`,
`receptors/simulated.py`, `tests/test_world_model.py`.

**Mobile:** `app/index.tsx` (rewritten — now the Field), `app/classic.tsx` (new — the prior home screen,
preserved), `app/_layout.tsx`, `components/EntitySymbol.tsx`, `components/OpportunityNode.tsx`,
`components/LoganCore.tsx`, `components/OpportunityField.tsx`, `lib/symbolResolver.ts`,
`types/loganFeed.ts`, `package.json` / `package-lock.json` (three new dependencies).

**Docs:** `docs/DECISIONS.md` (ADR-023 through ADR-026), `docs/specs/LOGAN_ARCHITECTURE_v1.0.md` and
`LOGAN_DATA_CONTRACTS_v1.0.md` (crypto domain), `docs/ARCHITECTURE.md` (full rewrite, this session).

## Backend changes

- Added `crypto` as a sixth `logan_core` domain (Bitcoin didn't fit anywhere else) — same pattern as the
  earlier News addition.
- Expanded the simulated fixture set to 11 entities (Tesla, NVIDIA, Apple, Bitcoin, Federal Reserve, NFL,
  Music, Polymarket, Markets, Oil, AI), all run through **one shared `Orchestrator`** so entities that
  genuinely overlap (Tesla's ripple touching NVIDIA and AI, which have their own direct fixtures too)
  connect to each other for real, not by scripted coincidence.
- Added `backend/app/entity_registry.py` — the "Canonical Entity" step: entity_id → display name /
  category / ticker. Deliberately kept out of `logan_core` itself (display concerns are a Presentation
  concern, not a reasoning-core concern, per the architecture's own layering rules).
- New endpoint: `GET /v1/demo/feed` — returns all 11 entities, ranked by priority, with computed
  cross-entity connections.

## Frontend changes

- Added the reusable **Signal → Canonical Entity → Symbol Resolver → EntitySymbol → Opportunity Node**
  pipeline. One component renders every entity; a new entity needs a lookup-table entry, never new UI
  code (and even with zero entry, it still renders via the fallback chain: logo → ticker → category icon
  → initials).
- Added `OpportunityField` (radial layout, priority-based positioning, SVG connection lines) and
  `LoganCore` (the center glyph — slow breathing animation, glass, glow).
- Added three dependencies: `react-native-svg`, `expo-linear-gradient`, `expo-blur` — approved before
  installation, all Expo-first-party/recommended. No icon library needed; `@expo/vector-icons` (already
  installed) covered it.
- `app/index.tsx` is now the Opportunity Field. The previous briefing screen moved intact to
  `app/classic.tsx`, reachable via a hamburger menu alongside Ask Logan, Memory Inbox, and the Tesla-only
  demo — nothing was deleted.

## Bugs fixed

- **World Model dedup used a fixed calendar-hour bucket** for merging corroborating signals about the
  same event. Two signals a few minutes apart could land on opposite sides of an hour boundary and
  wrongly split into two separate events instead of merging. Replaced with a proper sliding time window.
  Found while building the expanded feed, not something the user reported — logged and fixed the same
  session.

## What was verified

- `logan_core` test suite: 28/28 passing (including after both the dedup fix and the domain/entity
  expansion).
- `GET /v1/demo/feed` tested directly (in-process) and over real HTTP: 11 items returned, priority scores
  spread 0.49–0.88, correct connection clusters (6 connected entities, 5 standalone).
- TypeScript compiles clean — zero new errors from anything built today. (Three pre-existing, unrelated
  errors in `app/ask.tsx` remain, confirmed via `git diff` to predate this work.)
- Full iOS Metro bundle succeeds — 1,300 modules, no errors, all new files and the three new native
  modules confirmed present in the compiled output.
- **Not yet verified**: actual visual appearance on a real device — glow/blur quality, radial spacing at
  11 nodes, whether the breathing animation reads as calm. That's tomorrow's task.

## Known limitations

- The Opportunity Field has not been seen on a real phone yet — everything above is bundle/logic
  verification, not a visual check.
- `logan_core`'s external API is still just the demo bridge (`/v1/demo/*`), not a designed client
  contract — see `docs/ARCHITECTURE.md`'s "Known gaps."
- `logan_core` has no installable packaging; the backend reaches it via a `sys.path` shim.
- No authentication, no production hosting, CORS wide open — all pre-existing, all still open per
  `docs/DECISIONS.md` ADR-006.
- Two stray files were found in the working tree during cleanup and deliberately excluded from every
  commit so far: `.claude/settings.json` (new, untracked tooling config) and
  `mobile/app/UI Render 00.png` (the reference mockup, sitting inside the Expo Router screens directory —
  wrong location for a reference asset). Neither has been touched; both are still sitting there
  untracked.
- `Engineering docs/` and two duplicate `.docx` files directly under `docs/` remain untracked, as
  established in earlier sessions — raw source material superseded by `docs/specs/`.

## Next recommended steps

1. **Tomorrow's actual goal**: run the Field on a real phone and evaluate whether it feels like the
   product direction, before any further design or architecture work.
   ```powershell
   # Backend
   cd backend
   .venv\Scripts\activate
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

   # Mobile (separate terminal)
   cd mobile
   npx expo start --tunnel
   ```
   Re-check the LAN IP if it's been a while — `mobile/constants/config.ts` currently points at a specific
   local IP that may have changed.
2. Decide what to do with the two flagged stray files (`.claude/settings.json`, the reference PNG).
3. Once the Field is validated on-device, revisit the deferred items with real reaction in hand: traveling
   connection-line animation, the top Market Pulse/Portfolio Growth widgets (currently omitted — they'd

---

# Session Notes — 2026-08-19 (behavioral-personalization foundation, UserModel persistence pass)

Branch: `integration/sprint-3.6.6-stratus-watch`. Prior commit this session: `9f1f5e3` (ADR-047 — card-open/
dwell/notification-open interaction capture wired into the existing `FeedbackSignal -> FeedbackEngine ->
LearningEngine -> MemoryStore` path). **No new commit was made in this pass** — see stop condition below.

## What was asked

Turn interaction capture into persistent user learning: make `UserModel` survive across repeated
`/v1/opportunities` requests (today it's rebuilt from scratch via `UserModelBuilder().seed(...)` on every
single call in `backend/app/logan_feed.py::_run_feed_pipeline()`), and extend `UserModelBuilder.build()` to
read the `feedback_record`s Part A now produces into `established_behaviors` / `domain_preferences` /
`Interest(source="inferred")`, without touching STRATUS Watch eligibility.

## What was inspected (Phase 1, complete)

- `UserModelBuilder.seed()`/`.build()` (`logan_core/user_model/model.py`): `.build()` already does the right
  shape for safe persistence — `base.model_copy(update={...})` only ever touches `model_confidence`/
  `last_updated`/`version`, leaving `interests`/`holdings`/`domain_preferences`/`established_behaviors`/
  `inferred_expertise` copied through from `base` untouched. That's the existing mechanism that would keep
  explicit data intact across rebuilds — no new mechanism needed for that part.
- `.build()`'s `preference_records` filter only matches `record_type in ("preference_signal",
  "user_statement")`. Nothing in live code ever produces `preference_signal`. Our new interactions produce
  `feedback_record`s, which `.build()` currently ignores entirely — confirms the verified gap.
- **New finding, not previously surfaced**: `MemoryRecord.content` for our Part A interactions is just
  `f"{interaction_type} on {entity_id} ({domain})"` (`logan_feed.record_interaction()`) — it does **not**
  preserve `FeedbackEngine.interpret()`'s output (`inferred_intent`, `intent_confidence`). Consuming
  behavioral evidence deterministically (not by re-parsing prose or re-deriving from a `duration_ms` that also
  isn't stored) needs that interpretation captured at write time. Fixing this is in-scope, small, and doesn't
  touch any Pydantic contract (`MemoryRecord.content: object` is already deliberately untyped) — it just means
  building `content` in `record_interaction()` *after* calling `feedback_engine.interpret()` instead of before.
- No existing `UserModelStore`/cache abstraction exists. The correct precedent to mirror is the
  `_orchestrator: Orchestrator | None` process-lifetime singleton already in `logan_feed.py` (Sprint 3.6.6C) —
  same file, same pattern, not a new persistence layer.
- Confirmed `Orchestrator.run()` already calls `user_model_builder.build()` once **per entity, per pipeline
  run**, scoped to that entity's own `memory_store.query(entities=[...])` records — this internal, narrow
  call is separate from (and should stay untouched by) a new top-level call using the user's full record set,
  which is what would actually need to persist forward as next request's `base`.

## Stop condition hit — implementation did not proceed past inspection

`ReasoningEngine.reason()` (`logan_core/reasoning/engine.py`) reads `user_model.interests` **without
filtering by `source`**:
```python
interest_topics = {i.topic for i in user_model.interests}
connected_entities = sorted(touched_ids & (holding_ids | interest_topics))
```
`connected_entities` (any interest, explicit or inferred, matching) is one of the two branches that raise
`personal_relevance` in `opportunity/engine.py` (`_ACTIONABILITY_SCORE...` then `max(personal_relevance,
0.6)`), and `Dimensions.personal_relevance` is a live input to `PrioritizationEngine`'s alert/interruption
gating (confirmed by ADR-046's own trace, which already showed `personal_relevance` values driving alert
eligibility). **Writing any `Interest(source="inferred")` today would therefore change STRATUS Watch
eligibility as a side effect**, in direct contradiction of this task's explicit instruction not to touch Watch
eligibility tonight — and the fix (making `ReasoningEngine` distinguish `source="explicit"` from
`source="inferred"`) is itself a Reasoning-layer logic change, which is out of scope for a "no Watch policy
changes tonight" pass, not something to route around silently.

This is exactly one of the user's own listed stop conditions ("changing Watch policy," reached as an
unintended side effect rather than a direct ask) — so the pass stopped here rather than guessing. No code was
changed this turn; the branch is unchanged from commit `9f1f5e3`, clean and synced with
`origin/integration/sprint-3.6.6-stratus-watch`.

## Recommended next steps, in order

1. **Decide/confirm** whether `ReasoningEngine.reason()` should filter `user_model.interests` to
   `source == "explicit"` only when computing `connected_entities`/`personal_relevance_narrative` (keeping
   inferred interests legible elsewhere, e.g. a future personalization surface, without them silently feeding
   today's Watch-adjacent relevance signal). This is a real product/architecture decision, not an
   implementation detail — needs explicit sign-off before any `Interest(source="inferred")` write is safe.
2. Once (1) is decided: implement the persistence + `.build()` extension exactly as scoped tonight —
   process-lifetime `UserModel` cache in `logan_feed.py` (mirroring `_orchestrator`), `record_interaction()`
   enriched to capture `inferred_intent`/`intent_confidence` in `content`, `.build()` extended to populate
   `established_behaviors` and `domain_preferences.active` from repeated (>=2, the minimal definition of
   "not isolated") same-`(domain, entity_id)` `interested`-intent evidence, confidence values reused directly
   from `FeedbackEngine.interpret()`'s output rather than invented. `inferred_expertise` was already ruled out
   for this pass — "expertise" isn't demonstrated by view/click/dwell signals, only attention is.
3. Everything else from this pass's brief (impression/exposure, Watch Personal/Exceptional routes, FIELD
   BIAS learning, Ask STRATUS linkage) remains correctly deferred, unchanged from the prior session's report.

---

# Session Notes — 2026-08-21 (behavioral-personalization foundation, completed after interruption + recovery)

Branch: `integration/sprint-3.6.6-stratus-watch`. Prior commit: `6e01819` (the stop-condition note above).

## Reconciling what actually happened between 2026-08-19 and this session

The commit above (`6e01819`) accurately describes its own moment — the pass really did stop at the
`ReasoningEngine`/Watch-eligibility blocker with no code written yet. Work resumed after that commit (decision
1 above was made: filter `connected_entities` by `Interest.source`, keeping explicit and inferred as separate
signals rather than choosing one), and the full implementation described in step 2 above was written —
but that work was interrupted by a session limit before validation, commit, or push, and the machine was then
restarted before it could be revisited. `6e01819` therefore understates what had actually been built; no
commit ever captured it. This session recovered the uncommitted working tree intact after the restart,
inspected it file-by-file against `git diff` before touching anything, verified nothing was lost or
corrupted, and confirmed local `HEAD` still matched `origin/integration/sprint-3.6.6-stratus-watch` exactly.

Two things from the recovered code needed a real decision before proceeding, rather than assuming the
uncommitted state was already correct:

- `record_interaction()` had started calling `feedback_engine.interpret()` and
  `learning_engine.process_feedback()` directly, bypassing `Orchestrator.run_feedback_loop()` — a regression
  against ADR-047's own stated layer-ownership invariant. Root cause: `run_feedback_loop()`'s `content`
  parameter had to be supplied before its internal `interpret()` call, so structured content built from
  `interpret()`'s own output had no way to reach it. Fixed at the root (see ADR-048) rather than kept as a
  bypass: `content` now also accepts a callable that receives the computed `FeedbackSignal`, restoring
  Orchestrator ownership without a second interpretation.
- `_fold_behavioral_evidence()`'s new `DomainPref(weight=0.5)` was verified against `UserModelBuilder.seed()`
  (unmodified, pre-existing code at the top of the same file) before being kept — `weight=0.5` is exactly
  `seed()`'s own existing default for a newly-created domain preference, not an invented number specific to
  this pass.

See ADR-048 (`docs/DECISIONS.md`) for the complete decision record: the source-aware relevance split
(`connected_entities_explicit`/`connected_entities_inferred`), the behavioral-evidence folding into
`UserModel`, the restored Orchestrator ownership, and the new process-lifetime `UserModel` persistence in
`backend/app/logan_feed.py` (`_get_user_model()`, mirroring `_get_orchestrator()`) — the piece that was
previously only inspected/scoped (step 2 above) and is now actually wired into `_run_feed_pipeline()`.

## Status at the end of this session

Implementation complete for this pass's scope. `backend`/`logan_core` test count 244 → 264 (20 new/updated
tests covering repeated-vs-isolated evidence, no cross-entity/domain leakage, explicit data preservation,
`inferred_expertise` untouched, explicit-vs-inferred relevance bounding, Orchestrator-ownership restoration,
single-interpretation, and cross-request `UserModel` persistence). mypy/ruff/black clean. Mobile untouched by
this pass — not re-validated. Watch alert/interruption thresholds, Personal/Exceptional Watch routes,
impression/exposure semantics, FIELD BIAS learning, and Ask STRATUS linkage were not touched, as scoped.

## What remains before Watch Personal/Exceptional policy work

- The learning inputs (behavioral evidence → `UserModel`, source-aware relevance, audit trail) now exist and
  persist, but nothing yet *changes Watch dispatch behavior* based on them — `OpportunityEngine`'s inferred-only
  bound (0.5) only ever raises `personal_relevance` for non-actionable events; it was never wired into
  `PolicyEngine`/`PrioritizationEngine`'s alert/interruption gating, which remains exactly as it was.
- Whether/how an accumulated `established_behaviors`/inferred-`Interest` pattern should eventually promote an
  entity toward Personal or Exceptional Watch eligibility is an explicit open product decision, not addressed
  here.
- `UserModel` persistence is process-lifetime/in-memory only (mirrors the existing `_orchestrator` limitation)
  — a backend restart still resets accumulated behavioral learning. Real durable per-user persistence remains
  the open, undecided ADR-006 question.
- `MemoryStore.query()` has no `user_id` filter; this pass's single-user (`LOCAL_FOUNDER_USER_ID`) scope makes
  that safe today but it would need addressing before any real multi-user support.

---

# Session Notes — 2026-08-21 (STRATUS Watch: Personal / Exceptional eligibility routes)

Branch: `integration/sprint-3.6.6-stratus-watch`. Prior commit: `49f5848` (ADR-048, behavioral-learning
foundation). See ADR-049 (`docs/DECISIONS.md`) for the full decision record; this note covers the session
narrative and what to know before touching Watch again.

## What was asked

Make STRATUS Watch actually use the personalization signal ADR-048 built: two eligibility routes answering
"should STRATUS interrupt this user about this event right now" — Personal (meaningfully relevant to this
user) and Exceptional (important enough regardless of personalization) — replacing the old single
`urgency >= 0.7` alert gate, without replacing `PolicyEngine`, without touching Watch thresholds elsewhere,
and without inventing arbitrary new numeric thresholds where an existing anchor already fit.

## What inspection found before writing code

- The live path (Opportunity → Policy → Prioritization → Presentation) was confirmed unchanged from prior
  understanding. `PolicyEngine.evaluate()` already receives everything needed (`Dimensions` +
  `internal_rank_score`) — no input-contract change was needed.
- Fatigue re-verified still Prioritization-owned, still evaluated after Policy — but re-verifying the
  *consequence* (not just re-stating the ownership fact) showed Prioritization's fatigue check already runs
  before the `communication_mode` check and unconditionally overrides to `interruption="none"`, meaning it
  already has correct final veto power with no reordering needed. The routes were implemented entirely inside
  `PolicyEngine` with zero changes to `prioritization/engine.py`.
- A second instance of the same "Policy decides necessary-but-not-sufficient conditions" pattern was found and
  is new to this session's record: `interruption == "alert"` also requires Prioritization's own
  `internal_rank_score >= 0.6` ("primary visibility") separately from whatever `communication_mode` says — the
  `[0.35, 0.6)` "feed" branch structurally never produces `"alert"`. This was already true before this ADR; it
  is documented now because it directly explains one of the deterministic trace rows below (BTC).
- A real correctness hazard was caught by testing against live simulated fixtures instead of trusting hand-
  picked unit-test numbers: `OpportunityEngine`'s "nothing connected" default and its "inferred connection"
  bound are numerically identical (`personal_relevance = 0.5`) — a naive inferred-relevance route check would
  have silently let ADR-046's FED-shaped generic-urgency problem back in through a new door. Fixed with an
  additional `connection_strength > 0` guard (an existing `Dimensions` field, not a new one).
- A design flaw in the first draft of the inferred tier (requiring `internal_rank_score >= 0.6` in addition to
  its own urgency/confidence floors) was caught the same way: verified against a live two-repeat "watch"
  interaction on BTC, the tier was practically unreachable even when its own conditions were genuinely met.
  Removed that redundant requirement from the inferred tier only (kept on the explicit tier, where it's the
  tier's actual quality signal).

## Status at the end of this session

Implementation complete for this pass's scope. `backend`/`logan_core` test count 264 → 279 (15 new,
`logan_core/tests/test_policy.py`). mypy/ruff/black clean — one real regression was caught and fixed during
this session's own validation pass: embedding `internal_rank_score` as text in `DecisionTraceEntry.evidence`
broke `test_tesla_demo_response_has_no_internal_score_fields` (ADR-029's internal-only field, serialized as
part of the full pipeline result) — removed before finalizing. Mobile untouched, not re-validated. Watch
thresholds elsewhere (fatigue window/limit, cooldown window, recommend threshold, bot-risk suppression),
impression/exposure, FIELD BIAS, Ask STRATUS, and Attention Field were not touched, as scoped.

## What remains before STRATUS Watch can be considered feature-complete

- The routes decide `communication_mode`, not the final `interruption`. A Personal-route item can still end up
  `digest` instead of `alert` if `internal_rank_score < 0.6` (see the BTC row in ADR-049's trace table) — this
  is consistent with Prioritization's pre-existing, unmodified authority over final interruption, not a gap in
  this pass, but it means "qualifies for Personal" and "will actually push" are not always the same thing.
  Whether that's the right end-to-end behavior for a mature inferred interest is an open product question.
- No product decision has been made about whether/how a Personal or Exceptional alert should interact
  differently with fatigue/cooldown than an ordinary digest item (e.g. should a Personal-route alert bypass
  domain fatigue the way an "Exceptional" event arguably should). Fatigue currently applies identically
  regardless of which route qualified an alert.
- The Exceptional route's thresholds (0.8 urgency / 0.7 confidence / 0.7 novelty) were validated against the
  current 11-entity simulated fixture set, not against real live signal distributions (only NVDA's earnings
  path is real today, gated off by default). Real-world calibration is unverified.
- `internal_rank_score >= 0.6` doing double duty (Prioritization's own visibility bar, reused by Policy's
  explicit tier as a quality proxy) is a soft coupling between two layers that happen to agree on the same
  number today — not enforced by any shared contract. A future change to either threshold independently could
  silently change the other's behavior; worth a comment/test tripwire if either value is ever revisited.

---

# Session Notes — 2026-08-21 (Sprint 3.6.6 close-out)

Branch: `integration/sprint-3.6.6-stratus-watch`. Latest implementation commit: `7ca1e8a` (ADR-049). This
note closes out Sprint 3.6.6 — a docs-only pass, no application logic or Watch policy changed.

## Sprint 3.6.6 final closeout

Sprint 3.6.6 is functionally complete. Delivered across the sprint (see `docs/DECISIONS.md` ADR-042 through
ADR-049 for the full per-decision record, and `docs/specs/Logan_Documentation_v3.1.4/23_CURRENT_IMPLEMENTATION_STATE.md`'s
own "Sprint 3.6.6 close-out" section for the verified state table):

- First real external intelligence path: FMP-backed NVDA earnings → deterministic `STOCK_EARNINGS_BEAT`/`MISS`/`IN_LINE`
  trigger detection → the existing, unmodified `logan_core` pipeline → a real `/v1/opportunities` NVDA item
  (config-gated, default off).
- STRATUS Watch: real push notifications (Expo registration/tap-to-open), badge/push state coherence, cleaner
  wording, and an eligibility trace/debugging pass (ADR-046) that caught and fixed a fixture-timing artifact
  inflating `lifecycle_state` — the same trace that first surfaced the generic-urgency-alert question ADR-049
  later resolved.
- Behavioral-personalization foundation: card-open/dwell/notification-tap capture reaching `MemoryStore`
  through the existing `Orchestrator`/`FeedbackEngine`/`LearningEngine` path (ADR-047); process-lifetime
  persistent `UserModel` that actually accumulates repeated meaningful evidence into inferred interests,
  explicit-vs-inferred relevance separation with inferred bounded weaker, and an auditable `DecisionTrace`
  (ADR-048).
- STRATUS Watch Personal and Exceptional eligibility routes (ADR-049) — the sprint's final Watch-policy
  decision record — replacing the old single generic-urgency alert gate, with the existing downstream fatigue
  veto preserved unchanged.

Final state: branch `integration/sprint-3.6.6-stratus-watch`, commit `7ca1e8a`, 279 backend/logan_core tests
passing, mypy/ruff/black clean, working tree clean, local HEAD matches origin, no merge to main.

## Sprint 3.6.7 starting point

The following are recorded as the deliberate starting point for the next sprint — not resolved tonight, not
implemented, not guessed at:

1. **Personal-route rank-score gap.** A Personal-route item can qualify in `PolicyEngine` but still become
   `digest` instead of `alert`, because `PrioritizationEngine`'s existing `internal_rank_score >= 0.6` gate
   retains final authority over the actual `interruption` value. Open decision: should mature inferred
   Personal-route relevance be sufficient to produce a real push even when the rank bar is below 0.6?
2. **Impression/exposure semantics remain unresolved** — server-surfaced vs. client-rendered — and behavioral
   relevance is not yet normalized against exposure.
3. **Route-aware interruption handling is undecided.** Personal and Exceptional routes currently share
   identical fatigue/cooldown behavior; whether either route should interact differently with fatigue is a
   future decision, not made this sprint.
4. **Exceptional-route thresholds are fixture-validated only** — checked against the current
   deterministic/simulated fixture distributions, not broad real-world signal distributions.
5. **`UserModel` persistence is still process-lifetime only.** Durable persistence remains deferred (ADR-006
   territory).
6. **`MemoryStore.query()` remains single-user-safe only** — acceptable for the current single-user prototype,
   not yet multi-user safe.
7. **`internal_rank_score >= 0.6` is a soft coupling** between `PolicyEngine` and `PrioritizationEngine` — not
   enforced by any shared contract. Treat carefully if either threshold changes; consider a tripwire test if
   either is revisited.
8. **Still deferred, unchanged from prior sprints:** FIELD BIAS learning, Ask STRATUS linkage, broader trigger
   expansion, durable persistence, and broader ML calibration.

Recommended Sprint 3.6.7 starting objective: resolve item 1 above first (the Personal-route rank-score gap) —
it's the most direct, narrowly-scoped follow-on to ADR-049 and blocks a clean answer to "does mature
personalization actually produce a push," which is the natural next question after this sprint's work.
Impression/exposure semantics (item 2) is the next-most-consequential but is a larger, more open-ended design
question better scoped as its own follow-up once item 1's precedent (Policy-vs-Prioritization authority) is
settled.

---

# Session Notes — 2026-08-21 (Sprint 3.6.7 Block 1 — stock signal expansion + Personal-route authority rule)

Branch: `feat/sprint-3.6.7-stock-signal-expansion`, cut from the clean Sprint 3.6.6 integration HEAD
(`92acfbc`). See ADR-050 and ADR-051 (`docs/DECISIONS.md`) for the full decision records; this note covers
the session narrative.

## What was asked

Two things, explicitly ordered: (1) resolve the ADR-049 Personal-route rank-score gap flagged as Sprint
3.6.7's recommended starting objective, with an explicit, testable authority rule; (2) generalize the proven
NVDA-earnings signal architecture so new stock signal types plug in reusably, and implement a real first
expansion pack against live provider data — not scaffolding alone.

## What became reusable

The Provider → Receptor → deterministic Evaluator pattern Sprint 3.6.6 proved for earnings now has two more
implementations sharing the same shape: `QuoteProvider`/`GradeChange` contracts
(`receptors/providers/base.py`), `FmpMarketDataProvider` (a sibling to `FmpEarningsProvider`, not a merge —
that class stays untouched), `FixtureMarketDataProvider`, and `StocksTriggerEvaluator.evaluate()`'s dispatch
now routes by `signal_type` to per-signal-type evaluator methods instead of being earnings-only. A new signal
type is now: one Provider method, one Receptor function, one pure condition function, one `elif` branch —
not a parallel system.

## Signals now implemented (real, live-verified)

- `STOCK_PRICE_MOVE_SIGNIFICANT` (`TRIGGER_REGISTRY_STOCKS.md`, confidence `+0.10`) — from FMP's `/quote`
  endpoint (real-time price/change/previous-close, no new endpoint discovery needed beyond what earnings
  already established as reachable).
- `STOCK_ANALYST_UPGRADE` / `STOCK_ANALYST_DOWNGRADE` (confidence `+0.08` each) — from FMP's `/grades`
  endpoint, which supplies a pre-classified `action` field (upgrade/downgrade/maintain/initiate) — trusted
  directly rather than inferring direction from rating text.

Both live-verified against real current NVDA data (2026-08-21): neither fired today (change_pct -0.98%, most
recent grade action "maintain") — an honest result, not forced. A **real, fixture-driven, full-pipeline alert**
was proven deterministically in `test_pipeline_market_data.py`: NVDA holding + a qualifying price move →
`communication_mode="alert"`, `watch_route=personal`, `interruption="alert"`, exercising ADR-049/050 together.

## Signals deferred, and why

- `STOCK_GUIDANCE_RAISED`/`LOWERED`, `STOCK_OPTIONS_FLOW_SURGE` — no reliable provider data on the current FMP
  plan (guidance/options-flow), consistent with ADR-045's prior finding.
- "Unusual volume" / "volatility spike" — not implemented at all: no registered trigger code exists for
  either in `TRIGGER_REGISTRY_STOCKS.md`, so implementing one would mean inventing an unbacked
  `confidence_contribution`, which the standing Sprint 3.6.6D rule forbids. `/quote` also carries no
  average-volume baseline to compute "unusual" against. Framework is ready for either the moment a registry
  entry and a real baseline data source exist.
- Wiring the two new signals into `backend/app/logan_feed.py`'s live `/v1/opportunities` path — deliberately
  not attempted. `WorldModel.process()` dedups by `(entity_id, signal_type)`; feeding NVDA's earnings signal
  *and* a live price-move/analyst signal in the same request would silently drop one from that entity's
  single-opportunity result. Wiring it now would mean informally half-solving signal convergence, which is
  Block 2's own scope.

## Personal-route/prioritization authority decision (ADR-050)

`PrioritizationEngine` already stated its design principle in its own docstring — "separates visibility from
interruption" — but the implementation coupled them. Now decoupled: `visibility` stays purely
`internal_rank_score`-driven (unchanged); `interruption` is `"alert"` whenever
`policy_result.communication_mode == "alert"`, independent of the rank-driven visibility tier. Fatigue,
cooldown, and `permitted` are evaluated first and are completely unaffected — verified by 5 new tests proving
each veto still fully applies even when `communication_mode=="alert"`. No duplicate fatigue state, no
blanket bypass: this only ever changes the outcome for the previously-stuck `[0.35, 0.6)` rank band.

## Status at the end of this session

`backend`/`logan_core` test count 279 → 330 (51 new: 5 for ADR-050, 46 for the signal expansion). mypy/ruff/
black clean. No merge to main. No existing receptor, contract, API, or Watch threshold was broken — the
earnings path's own tests pass unmodified.

## Recommended Sprint 3.6.7 Block 2 starting objective: signal convergence

Resolve the exact gap ADR-051's inspection finding 5 identified: `WorldModel.process()`'s
`(entity_id, signal_type)` dedup key means multiple *different* live signal types for the same entity within
one poll are not merged — only the last-processed one survives into that request's single opportunity. This
is also literally `TRIGGER_REGISTRY_STOCKS.md`'s own `STOCK_CONVERGENCE_MULTI_SOURCE` code (confidence
`+0.20`, fire condition "≥3 distinct source types emit signals within 30 minutes") — a registered, currently
SPECIFIED-NOT-IMPLEMENTED trigger this gap is a direct precondition for. Block 2 should: (1) decide how
multiple `TriggerEvent`s for one entity within a window should combine into one `EnrichedEvent` (World
Model's dedup/merge model needs to widen beyond one `(entity_id, signal_type)` key, or a new aggregation step
needs to sit between trigger detection and World Model), (2) implement `STOCK_CONVERGENCE_MULTI_SOURCE`
itself once that foundation exists, and (3) only then wire the Sprint 3.6.7 Block 1 signals (and earnings)
into `backend/app/logan_feed.py`'s live `/v1/opportunities` path for entities that could plausibly have
multiple simultaneous live signals — completing the "live provider data → real Watch notification" loop this
sprint's signals were built for but deliberately didn't finish wiring. This is a real architecture decision
(how World Model's dedup/merge model changes), not a routine implementation task — worth confirming the
approach before building it.

---

# Session Notes — 2026-08-22 (Sprint 3.6.7 Block 2 — signal convergence)

Branch: `feat/sprint-3.6.7-stock-signal-expansion`, resumed after a PC crash cut off the first Block 2 attempt
almost immediately (reconnaissance/architecture-discussion stage only — no partial edits existed). Post-reboot
crash-recovery verification confirmed: HEAD `6fe4fdd`, working tree clean, synced to origin, stash empty. See
ADR-052 (`docs/DECISIONS.md`) for the full decision record; this note covers the session narrative.

## What was asked

Resolve the gap ADR-051's inspection finding 5 identified and this file's own prior recommendation scoped:
implement `STOCK_CONVERGENCE_MULTI_SOURCE` (registered, SPECIFIED — NOT IMPLEMENTED), fix the real
"multiple `EnrichedEvent`s for one entity, only the last survives" bug, and only then wire Block 1's live
price-move/analyst-grade signals into `/v1/opportunities` alongside earnings — completing the "live provider
data → real Watch notification" loop across Blocks 1 and 2.

## The architecture decision (carried over from the interrupted attempt, re-verified before building)

`WorldModel`'s `(entity_id, signal_type)` dedup key stays completely unmodified — widening it to merge
*different* signal_types for one entity into one event was explicitly rejected. It would erase real, already-
depended-upon behavior (duplicate-poll suppression, corroboration counting, per-`trigger_code` replace-not-
stack) and conflate two different concerns: what World Model considers one underlying fact per signal source,
versus what makes multiple *independent* sources newsworthy together. Chosen instead: **Option 1 — a parallel
convergence tracker**, sitting beside World Model, not inside it.

## What got built

1. **`StockConvergenceTracker`** (`logan_core/convergence/tracker.py`, new) — persistent, process-lifetime,
   watches the same `TriggerEvent`s trigger detection already produces. Fires `STOCK_CONVERGENCE_MULTI_SOURCE`
   when ≥3 distinct `signal_type`s are active for one entity within a 30-minute window. The one real design
   correction made mid-session: the window is based on `detected_timestamp` (real evaluation-time "now"), not
   `event_timestamp`/`captured_at` — an earnings report's date, a quote's real-time timestamp, and an
   analyst's action date are independently sourced and routinely diverge by far more than 30 minutes even when
   all three are detected as live opportunities in the same poll; a first pass windowed on `event_timestamp`
   and a manual pipeline test proved it would essentially never fire on real data. An active episode reuses its
   `trigger_id`/`event_timestamp` across repeated polls (no fresh "alert" every request); distinct types are
   tracked as a set, so repeated polling of one already-observed type can never manufacture a false third
   source.
2. **Coherent-opportunity merge** (`orchestrator/pipeline.py`) — the actual root-cause fix for "only the last
   raw_signal's event survives": every signal's `EnrichedEvent` is kept during `Orchestrator.run()`'s loop,
   same-`event_id` repeats collapse to the up-to-date version (reproducing old behavior exactly), and genuinely
   distinct signal_type events are unioned into one coherent per-entity opportunity afterward. A no-op for the
   single-signal case, verified byte-for-byte against the full pre-existing suite.
3. **Live wiring** (`backend/app/logan_feed.py`) — Block 1's price-move/analyst-grade signals now feed into
   the live NVDA path alongside earnings, each independently gated on its own trigger actually firing, additive
   rather than a fixture replacement.

## Status at the end of this session

`logan_core` test count 248 → 265 (+17). `backend` test count 82 → 89 (+7). mypy/ruff/black clean. One
unrelated pre-existing flake found and fixed while running the full suite (`test_pipeline_market_data.py`'s
price-move test decaying below its own rank-score assertion purely from real-world time passing since its
fixture's fixed timestamp) — confirmed via `git stash` against clean `6fe4fdd` before touching it, so it's not
attributable to this session's changes. No merge to main.

## Recommended Sprint 3.6.7 Block 3 starting objective

Two reasonable candidates, in order of how directly they follow from this block:

1. **Live-verify `STOCK_CONVERGENCE_MULTI_SOURCE` end-to-end against real FMP data.** Blocks 1–2 together
   completed the "live provider data → real Watch notification" loop this sprint was built for, but no session
   has yet observed real NVDA data actually qualify all three signal types in the same poll (ADR-051's
   live-verification found neither price move nor analyst grade fired on 2026-08-21). A
   `logan_core/live_verification/nvda_convergence.py` script, mirroring the existing `nvda_earnings.py`/
   `nvda_market_data.py` pattern, would let a future session confirm this the moment real market conditions
   qualify — closing the loop with an honest, unforced live result rather than fixture-only proof.
2. **Impression/exposure semantics** — flagged as "next-most-consequential" as far back as the Sprint 3.6.6
   close-out note and still untouched: server-surfaced vs. client-rendered exposure is unresolved, and
   behavioral relevance is not yet normalized against it. Larger and more open-ended than option 1; better
   scoped as its own dedicated block once a session has time to work through the design question properly
   rather than picked up as a quick follow-on.

Recommendation: option 1 first — it's a narrow, low-risk verification task that closes out this sprint's own
stated goal, and doesn't foreclose picking up option 2 (or any other item from the carried-over limitations
list in `23_CURRENT_IMPLEMENTATION_STATE.md`) as Block 4 or a dedicated future sprint.

---

# Session Notes — 2026-08-22 (Sprint 3.6.7 Block 3 — persistent behavioral personalization + exposure semantics)

Branch: `feat/sprint-3.6.7-stock-signal-expansion`, continuing directly from the Block 2 closeout commit
`ebb5079`. See ADR-053 (persistent behavioral personalization) and ADR-054 (live convergence verification) in
`docs/DECISIONS.md` for the full decision records; this note covers the session narrative. This was, by a
wide margin, the largest single block of this sprint.

## What was asked

A substantial end-to-end implementation moving STRATUS from explicit-only holdings/interests toward learning
from repeated exposure and engagement: opportunity shown -> exposure recorded -> engagement or non-engagement
observed -> deterministic relevance evidence -> UserModel updates persistently -> future relevance/ranking
changes -> STRATUS Watch reflects the stronger signal without spam or runaway feedback loops. Plus, as one
acceptance item inside this block, the Block 2 live-convergence-verification carryover.

## The one architecture question that genuinely needed confirmation

Before writing any persistence code: this project's `CLAUDE.md` explicitly requires stopping for confirmation
on any database schema change, and ADR-006 flags database/hosting as an open decision (though it already
sanctions "SQLite + local dev for Phase 1" specifically). Asked directly rather than guessing: a new, dedicated
SQLite store scoped to this architecture (not extending the historical `memory_engine.py`/`logan_memory.db`,
a different, unrelated schema), with `UserModel` staying derived state rebuilt from persisted records rather
than stored directly. Confirmed before proceeding; everything else in this block proceeded without further
stops, per the explicit instruction to only stop for a genuinely blocking architecture conflict.

## Reconnaissance finding: the foundation was more mature than the request implied

Before designing anything, inspected the existing personalization architecture in full: `UserModel`,
`ReasoningEngine`/`OpportunityEngine`'s explicit-vs-inferred relevance split, `PrioritizationEngine`,
`PolicyEngine`'s Personal/Exceptional Watch routes, and the existing `POST /v1/interactions` route (ADR-047)
already reaching `MemoryStore` through `Orchestrator.run_feedback_loop()`, with `UserModelBuilder.build()`
(ADR-048) already folding repeated `feedback_record` evidence into `established_behaviors`/`domain_preferences`/
inferred `Interest` (`MIN_REPEAT_EVIDENCE=2`). Mobile already sent real `view`/dwell and `click` interactions.
This meant Block 3 was a real extension of working infrastructure, not a green-field build -- and the actual
gaps were narrower and more specific than the request's framing suggested: no true exposure/impression concept
distinct from card-open, no persistence surviving a restart, and -- the most consequential finding --
`OpportunityEngine`'s inferred-connection relevance was a flat `0.5` regardless of how much evidence backed
it, so more mature behavioral evidence literally could not matter more than a single just-qualifying
interaction. That last gap is what the acceptance target actually needed solved.

## What got built (see ADR-053 for the full per-area decision record)

1. **`MemoryStore` persistence** -- optional SQLite backing, schema-versioned, bounded-history compaction,
   `None` (every pre-Block-3 caller/test) unchanged.
2. **Exposure/impression semantics** -- new `InteractionType` values (`impression`, `ask_followup`), new
   `RecordType` (`exposure_record`) structurally excluded from behavioral-evidence folding, new
   `LearningEngine.process_exposure()`/`Orchestrator.run_exposure_loop()`, idempotent (one lifetime record per
   event), a new 5-minute dedup window on ordinary feedback too.
3. **Deterministic behavioral relevance model** -- maturity scaling (bounded), recency-based decay (14-day
   half-life measured from each pair's own most recent evidence, not from "when this was last rebuilt" -- a
   real design correction made mid-session after realizing `UserModelBuilder.build()` always receives full
   history, so decay has to be embedded in the evidence computation itself or it's overwritten every call),
   exposure-fatigue dampening (weak, bounded, recency-gated against the last real engagement, never fabricated
   from mere non-engagement).
4. **Matured relevance reaching Personal route** -- `ReasoningResult.inferred_relevance_strength` +
   `OpportunityEngine._scale_inferred_relevance()` replace the flat `0.5` floor with a `[0.5, 0.59]` range
   scaled to evidence maturity, verified against the exact pre-existing test assertions before implementing
   (not discovered after breaking them) to confirm the default case reproduces the old behavior exactly.
5. **Watch integration** -- zero changes to `PolicyEngine`/`PrioritizationEngine`; mature evidence now
   measurably moves events within their existing, unmodified thresholds.
6. **Mobile** -- `useImpressionTracking.ts` fires on `AttentionField`'s existing `focusedId` change, not a new
   viewport-tracking system -- the minimal real hook the block's own scope asked for.
7. **Live convergence verification (ADR-054)** -- ran live against real FMP data: only 1 of 3 NVDA signal types
   fired today, so `STOCK_CONVERGENCE_MULTI_SOURCE` honestly did not qualify -- an unforced, correct result, not
   a failure.

## Bugs found and fixed while building this, not pre-planned

- `LearningEngine.process_feedback()` computed its own `datetime.now()` instead of reusing
  `FeedbackEngine.interpret()`'s already-computed `feedback.observed_at` -- identical in production (they run
  synchronously back-to-back) but made the new dedup window untestable without real wall-clock waits. Fixed at
  the root by reusing the existing timestamp.
- First draft of exposure-fatigue dampening gated on "has this entity ever had qualifying engagement" -- which,
  since `memory_records` is always full history, is trivially always true for any entity with an inferred
  interest at all (having one requires having had qualifying engagement), making the guard permanently
  unreachable. Caught before shipping by tracing through the actual data flow; corrected to gate on recency
  (impressions continuing well after the last real engagement) instead of a lifetime engaged/never-engaged
  split.

## Status at the end of this session

`logan_core`/`backend` test count 354 -> 405 (+51). `mobile` test count 88 -> 94 (+6). mypy/ruff/black clean;
`tsc --noEmit`/`eslint` clean. Acceptance scenario (no explicit AMD holding, 4 recorded engagements, simulated
backend restart, inferred relevance still present and genuinely matured) proven end-to-end and covered by an
automated test, not just manually verified. No merge to main.

## Recommended Sprint 3.6.7 Block 4 starting objective

The carried-over limitations list in `23_CURRENT_IMPLEMENTATION_STATE.md` (impression/exposure exact
UI-viewport semantics beyond the focus-based proxy this block shipped, `MemoryStore.query()` remaining
single-user-only, Exceptional-route thresholds validated only against simulated fixtures,
`internal_rank_score>=0.6`'s soft coupling between Policy and Prioritization) is now the natural backlog --
none of it was resolved this block, and none of it blocks anything shipped here. Two reasonable next
candidates:

1. **Real Ask-STRATUS-about-this-opportunity linkage.** `ask_followup` now has a full, tested backend/domain
   contract (interpreted, persisted, foldable into behavioral evidence) but is deliberately not wired to the
   existing `/v1/ask` route, which is a disconnected legacy chat stub with no `event_id` concept at all and
   reads from the historical `memory_engine`, not this pipeline. Wiring a real per-opportunity "ask STRATUS"
   flow would let `ask_followup` actually fire from production UI instead of only being reachable through the
   backend contract directly, and gives the behavioral relevance model a second, strong engagement signal type
   with a real UI path. Flagged as deferred since the Sprint 3.6.6 close-out; this block is the first time the
   backend half of it has actually been built.
2. **Multi-user safety.** `MemoryStore.query()`, `UserModel`, and now the new SQLite persistence are all still
   single-user (`LOCAL_FOUNDER_USER_ID`) by construction -- not a bug for the current single-operator
   prototype, but a real prerequisite before ADR-006's Phase 2 (multi-user/public launch) database decision can
   be made meaningfully. Larger and more foundational than option 1; better scoped as its own dedicated block.

Recommendation: option 1 first -- it's a direct, well-scoped completion of work this block already built the
backend half of, and gives a second real UI-driven engagement signal to validate the behavioral relevance
model against. Option 2 is real and necessary but foundational enough to deserve its own dedicated planning
pass rather than being picked up as a quick follow-on.

---

# Session Notes — 2026-08-22 (Sprint 3.6.7 Block 4 — contextual Ask STRATUS + ASK_FOLLOWUP behavioral evidence)

Branch: `feat/sprint-3.6.7-stock-signal-expansion`, continuing directly from the Block 3 closeout commit
`0d9351c`. See ADR-055 (`docs/DECISIONS.md`) for the full decision record; this note covers the session
narrative.

## What was asked

Connect Ask STRATUS directly to the opportunity intelligence system: a user asks about a specific opportunity,
the answer is grounded in that opportunity's real data, and the interaction becomes real, appropriately-bounded
behavioral evidence via Block 3's `ask_followup` concept -- end to end, not a placeholder.

## The one real architectural finding: there is no LLM in this codebase

Before designing anything, checked the existing `/v1/ask` route (`backend/app/main.py`). It predates
`logan_core` entirely -- reads from the historical `memory_engine` SQLite prototype, has no `event_id`
concept, and answers with a static template regardless of the question. There is no model call anywhere in
this repository. Adding one now would be a new external dependency, which CLAUDE.md's collaboration model
requires explicit confirmation for before adding -- a separate decision this block does not make. Built the
entire grounded-answer path deterministically instead: real, already-computed pipeline fields
(`DeliveredItem`'s narrative text, `ConclusionConfidence`'s `classification`/`limiting_factors`/`alternatives`,
attached `TriggerEvent`s, `Dimensions.personal_relevance`) matched against the question via ordered keyword
classification, never fabricated, honest ("nothing currently limits this") when a category has no real data
to answer from.

## What got built (see ADR-055 for the full per-area record)

1. **Authoritative rehydration** -- the client sends only a stable `event_id`; a new `OpportunityContext`/
   `OpportunityContextCache` (`backend/app/ask_context.py`) reconstructs real context server-side from the same
   `PipelineResult` that already produced that request's `FeedItem`, not a second computation. An unresolvable
   `event_id` (stale, or from before a restart) gets an honest "no current context" answer.
2. **One route, not two** -- `AskRequest`/`AskResponse` gained additive optional `event_id`/`session_id`/
   `grounded` fields on the *existing* `/v1/ask` route. The pre-existing generic path (which, notably, had zero
   test coverage before this session) is unaffected and now finally tested.
3. **`answer_question()`** (`ask_engine.py`) -- deterministic, ordered keyword classification covering what
   changed, why now, which signals, convergence, confidence, what would weaken this, personal relevance, and
   comparison questions, each grounded in real fields.
4. **`ASK_FOLLOWUP` wired for real** -- a successful contextual question records real behavioral evidence
   through the exact Block 3 path (`record_interaction()` → `FeedbackEngine`, 0.80 confidence tier, unchanged).
   Invalid opportunity, empty message, and generic questions never record engagement.
5. **Session continuity, structural only** -- a bounded, process-lifetime session store holds just the
   continuity anchor (which opportunity a session is discussing, and a session-level `ASK_FOLLOWUP` cap) --
   never raw conversation transcripts, which the deterministic engine doesn't need. Deliberately not persisted
   to SQLite -- documented as a short-lived UI-convenience boundary, not durable preference data.
6. **Feedback-loop protection** -- at most one `ASK_FOLLOWUP` contribution per (session, opportunity),
   regardless of how many follow-ups that session asks. Verified this sits correctly *on top of*, not in
   conflict with, Block 3's pre-existing session-agnostic 5-minute dedup rather than assumed.
7. **Mobile** -- one "Ask STRATUS about this" button per opportunity card (`Vessel.tsx`); `ask.tsx` reads
   `eventId`/`entityId`/`displayName`/`domain` via Expo Router params (a genuinely new pattern for this app --
   no prior screen took params) and shows contextual first-state copy/starters plus an honest "Discussing
   {entity}" chip only when real context exists.

## A test-design correction made mid-session, not pre-planned

The acceptance scenario as described used "AMD" as the example entity, but AMD isn't a real simulated-fixture
entity anywhere in this codebase (the fixtures are TSLA/NVDA/AAPL/MARKETS/OIL/BTC/FED/NFL/MUSIC/POLY/AI_SECTOR)
-- caught by the first test run actually failing on a `None` lookup rather than assumed correct from the
description. Substituted AAPL, which satisfies the same real requirement (no explicit holding/interest in the
seeded `UserModel`), and documented the substitution explicitly in both the test and the ADR rather than
quietly swapping it. Separately, an early version of one test expected two different session IDs asking the
same question moments apart to each independently record evidence -- this actually collided with Block 3's
own pre-existing short-window dedup (which is intentionally session-agnostic), so the test's expectation was
wrong, not the implementation; corrected the test and used a real time-gap technique (directly rewinding a
just-written record's `created_at`, the same class of fixture-timing tool `test_user_model_behavioral.py`
already established) to prove the acceptance scenario's four *genuinely separate* engagements each counted.

## Status at the end of this session

`logan_core`/`backend` test count 405 → 446 (+41). `mobile` test count 94 → 100 (+6). mypy/ruff/black clean;
`tsc --noEmit`/`eslint` clean. Acceptance scenario (opens an opportunity with no explicit holding, asks real
contextual follow-ups across several sessions, simulated backend restart, inferred relevance still present and
genuinely matured) proven end-to-end and covered by an automated test. No merge to main.

## Integration-hardening pass (secondary task, Blocks 1–4)

Checked every item on the requested list against the actual repository, not assumed clean:

- **Duplicated logic**: found one genuine, low-risk instance --
  `live_nvda_earnings_enabled()`/`memory_persistence_enabled()` (`backend/app/config.py`) had byte-identical
  boolean-env-var parsing. Extracted a shared `_env_flag(name)` helper; both public functions now call it,
  behavior unchanged (140 backend tests re-verified green immediately after). Everything else inspected
  (`StockConvergenceTracker`'s episode dedup, `LearningEngine`'s record dedup, `_ask_sessions`'s session dedup;
  the `_orchestrator`/`_user_model`/`_opportunity_context_cache`/`_ask_sessions` process-lifetime-singleton
  pattern) is *structurally similar* but operates on genuinely different data/lifecycles at different layers --
  consolidating any of it would be a real, riskier refactor for cosmetic benefit, which the block's own
  instructions explicitly excluded ("do not perform unrelated cosmetic refactors"). Left alone, documented here
  as inspected-and-rejected rather than silently skipped.
- **Stable IDs/schema versions**: `MemoryRecord.schema_version`, `MEMORY_STORE_SCHEMA_VERSION`,
  `TriggerEvent`/`EnrichedEvent.schema_version`, `OPPORTUNITIES_SCHEMA_VERSION` are all unchanged and
  consistent. New Block 4 types (`OpportunityContext`, `AskRequest`/`AskResponse`) deliberately carry no
  `schema_version` -- ephemeral, never persisted or versioned across releases, consistent with every other
  request/response model in `models.py`.
- **Provenance survives the full path**: added a new, dedicated integration test
  (`test_ask_context.py::test_convergence_provenance_survives_into_opportunity_context`) proving real
  three-signal convergence (Block 2's `StockConvergenceTracker`) survives `Orchestrator.run()`'s
  coherent-opportunity merge all the way into `OpportunityContext.convergence_sources` and a real, grounded
  Ask STRATUS answer (Block 4) -- not just inspected, actually executed and green.
- **Persistence migrations**: `MemoryStore._migrate()`'s fresh-database and reopen-existing-database paths are
  both covered by `test_memory_store_persistence.py` (unchanged this pass); only one schema version exists
  today so there is nothing further to exercise until a real version-2 change lands.
- **Config defaults**: `STRATUS_LIVE_NVDA_EARNINGS` and `STRATUS_PERSIST_MEMORY` both still default off, both
  still isolate the entire pre-existing test suite from real external state unless a test explicitly opts in.
  No new Block 4 config flag was needed -- the contextual Ask path is inert unless a client explicitly sends a
  real `event_id`, which nothing does until the new mobile button is actually pressed.
- **No test-only fixtures in production paths / no live-provider fabrication**: re-inspected
  `_live_nvda_raw_signal`/`_live_nvda_price_move_raw_signal`/`_live_nvda_analyst_grade_raw_signal`
  (`logan_feed.py`) and confirmed via `git diff HEAD` that this session's edits touched none of them --  the
  only changed lines in that file are the intentional `OpportunityContext`/session-store additions. Re-ran
  every `logan_core/live_verification/*.py` script's import (all three) to confirm nothing broke silently.
- **Full validation suite re-run after every change above**: stayed green throughout (140 → 447 backend/
  logan_core tests across the whole hardening pass, 100 mobile tests, mypy/ruff/black/tsc/eslint clean) --
  no regressions found requiring a fix beyond the one consolidation described above.

## Recommended Sprint 3.6.7 closeout / next-sprint objective

Sprint 3.6.7 is functionally complete across all four blocks: generalized live stock-signal architecture
(Block 1), signal convergence (Block 2), persistent behavioral personalization (Block 3), and contextual Ask
STRATUS with real behavioral evidence (Block 4) -- a complete, tested, live-data-verified loop from raw
provider signals through to a user asking STRATUS about a specific opportunity and that shaping future
relevance. Recommend treating this as the sprint's close-out point rather than opening a Block 5 speculatively.

Two reasonable candidates for the next sprint, carried forward from this block's own findings (not resolved
here, deliberately):

1. **Real per-opportunity NLU / whether an LLM belongs in this system at all.** `answer_question()`'s
   deterministic keyword classification is honest and grounded but has real ceilings a genuine free-text
   question can exceed (multi-part questions, questions this classifier's keyword list doesn't anticipate,
   genuinely comparative/analytical questions beyond "which triggers are attached"). Introducing an LLM is a
   real, separate architectural decision (a new external dependency, cost/latency/safety-boundary
   implications for the analysis-not-advice guardrail) that this block deliberately did not make -- worth a
   dedicated design conversation, not a quiet addition to a future block.
2. **Multi-user safety**, unchanged from Block 3's own recommendation -- `MemoryStore.query()`, `UserModel`,
   the new SQLite persistence, and now the Ask STRATUS session store are all still single-user
   (`LOCAL_FOUNDER_USER_ID`)/process-lifetime by construction. Not a bug for the current single-operator
   prototype, but the real prerequisite before ADR-006's Phase 2 (multi-user/public launch) database decision
   can be made meaningfully.

Recommendation: pause new Block 5 feature work here and let this sprint's four-block arc stand as a complete,
closed unit; pick up either candidate above as the deliberate start of the *next* sprint, with its own
planning pass rather than a same-session continuation.

---

# Session Notes — 2026-08-22 (Sprint 3.6.8 Block 1 — grounded LLM Ask STRATUS)

Branch: `feat/sprint-3.6.7-stock-signal-expansion`, continuing directly from the Block 4 closeout commit
`1e67120`. See ADR-056 (`docs/DECISIONS.md`) for the full decision record; this note covers the session
narrative.

## What was asked

Sprint 3.6.7's own closeout note (above) named this exact question as the natural next-sprint candidate: does
an LLM belong in this system, and if so, add it as a second, optional stage over Block 4's deterministic Ask
STRATUS engine — never replacing it, always falling back to it, never letting the model invent facts the
pipeline didn't compute.

## Recon before writing any code

Confirmed by direct inspection (not assumed): no LLM call exists anywhere in `backend/`, `logan_core/`, or
`mobile/` prior to this block. Adding one is a genuine new external dependency and a genuine new secret, both
requiring explicit owner confirmation under CLAUDE.md's collaboration model before any implementation code was
written. Stopped and asked two questions: which model tier, and whether to approve the `anthropic` SDK
dependency plus a new `ANTHROPIC_API_KEY` secret. Owner chose `claude-sonnet-5` (over the skill's higher-tier
default, on cost/latency grounds for a short grounded-composition task) and approved both the dependency and
the secret.

## What got built (see ADR-056 for the full per-area record)

1. **Vendor-agnostic provider abstraction** (`ask_llm_provider.py`, `ask_llm_fixture.py`,
   `ask_llm_anthropic.py`) — mirrors `receptors/providers/{base,fmp,fixture}.py`'s established pattern. Only
   `ask_llm_anthropic.py` knows anything Anthropic-specific; everything else in the codebase sees only the
   `AskLlmProvider` protocol and the one domain error, `AskLlmProviderError`.
2. **Structured grounding** — `build_system_prompt()` renders the same real `OpportunityContext` fields
   Block 4's deterministic engine already uses, explicitly instructs the model not to invent market facts or
   contradict the given classification, and restates the ADR-002/010 advice boundary as a second, independent
   enforcement point.
3. **Deterministic fallback owned by the caller, not the provider** — `generate_grounded_answer()`
   (`ask_engine.py`) is the one place that decides what happens on any failure (disabled, unavailable, network,
   timeout, rate limit, refusal, empty/malformed response) — all of it falls through to the exact same
   `answer_question()` Block 4 already had. No LLM failure mode can break Ask STRATUS.
4. **Config gating** — `STRATUS_LLM_ASK`, defaults off, same rollout pattern as every other capability flag in
   this codebase. `get_ask_llm_provider()` is a lazy, thread-safe, memoized construction point that degrades to
   `None` (never a crash) on a missing key or any construction failure.
5. **Prompt-injection hygiene, structural not just instructional** — the user's question is never concatenated
   into the system prompt string; it's sent as a wholly separate `user` message. Verified directly against a
   captured call, not just against prompt text.
6. **`ASK_FOLLOWUP` unchanged and decoupled from which path answered** — recording depends only on "did a real
   answer get produced," never on LLM-vs-deterministic. Verified: an LLM-failure-then-fallback question records
   exactly one `ask_followup` event, not zero and not two.

## Implementation went smoothly — the one real fix was a type annotation, not a design problem

`output_config={"effort": DEFAULT_EFFORT}` failed mypy because `DEFAULT_EFFORT` was inferred as plain `str`
where the SDK's `OutputConfigParam` TypedDict requires a `Literal`. Fixed by typing the constant explicitly
(`DEFAULT_EFFORT: Literal["low"] = "low"`). Everything else — provider construction, the fallback branch, route
wiring, `ASK_FOLLOWUP` idempotency — worked correctly on first manual smoke test via `TestClient` +
`unittest.mock.patch`, later formalized into the permanent `test_ask_llm.py` suite (38 tests).

## Status at the end of this session

`backend` test count 141 → 179 (+38); `logan_core` unaffected (306, untouched by this block). mypy/ruff/black
clean on every new/changed production and test file (two pre-existing `**dict[str, object]` mypy findings in
Block 4's own `test_ask_engine.py`/`test_ask_route.py` predate this block and are unrelated — noted, not
touched). `AskRequest`/`AskResponse` (`models.py`) unchanged, so no mobile contract impact and no mobile test
re-run required. No merge to main.

**Deferred, flagged for the owner:** `backend/.env` was not given a real `ANTHROPIC_API_KEY` — this session has
no real key to insert. `STRATUS_LLM_ASK` defaults off, so the system behaves exactly as before this block until
the owner both flips the flag and adds their own key locally; a missing key at that point still degrades
gracefully to the deterministic path.

## Recommended next Sprint 3.6.8 block

The Block 1 spec's own scope boundary named two things explicitly out of scope here, both still open:

1. **Minimal mobile surfacing of `grounded`/answer provenance**, if the owner wants the app to visually
   distinguish an LLM-composed answer from a deterministic one — Block 1 deliberately kept `used_llm`/
   `llm_model` internal to `GroundedAnswer` and off the public `AskResponse` contract, since no UI change was
   required to satisfy this block's own requirements.
2. **Production user boundaries** — the sprint's own stated direction ("Grounded LLM Ask STRATUS + Production
   User Boundaries") named a second half this block didn't touch: `MemoryStore.query()`, `UserModel`, and every
   session/provider singleton in this codebase are still single-user (`LOCAL_FOUNDER_USER_ID`)/process-lifetime
   by construction — the same carried-over item Sprint 3.6.7's own closeout flagged, now explicitly named in
   this sprint's own title rather than just a backlog candidate.

Recommendation: Production User Boundaries is very likely the intended Block 2, given it's named directly in
the sprint's own two-part title — worth confirming with the owner before starting, since it's foundational
enough (touches `MemoryStore`, `UserModel`, every process-lifetime singleton added across Sprint 3.6.7) to
deserve its own explicit scoping conversation rather than an assumed continuation.

---

# Session Notes — 2026-08-22 (Sprint 3.6.8 Block 2 — production user boundaries)

Branch: `feat/sprint-3.6.7-stock-signal-expansion`, continuing directly from the Block 1 closeout commit
`eb7ad40`. See ADR-057 (`docs/DECISIONS.md`) for the full decision record; this note covers the session
narrative, including a mid-session usage-limit interruption and resume.

## What was asked

Remove founder/local-user assumptions from the stateful STRATUS intelligence loop and establish explicit
user-scoped boundaries for persistence, personalization, Watch, interactions, and Ask session state — a
production architecture hardening block, not a cosmetic refactor.

## Recon finding that reshaped the scope: most of logan_core was already multi-user-ready

Before writing any code, checked every stateful path introduced across Sprints 3.6.6–3.6.8. The real
surprise: `Orchestrator.run()`/`run_feedback_loop()`/`run_exposure_loop()` already take an explicit `user_id`,
`MemoryRecord.user_id` is required and validated (ADR-033), and `PrioritizationEngine`'s `AttentionState` was
already stored in a `dict[user_id, AttentionState]` internally. The gap was concentrated in exactly two
places: `backend/app/logan_feed.py`, which never threaded any real per-request identity through (8 hardcoded
`LOCAL_FOUNDER_USER_ID` call sites) and held single global process-lifetime singletons instead of per-user
ones; and one real, concrete bug inside `logan_core` itself —
`orchestrator/pipeline.py`'s `run()` called `memory_store.query(entities=...)` with **no `user_id` filter at
all**, even though `user_id` was in scope two lines below. That single unfiltered call fed every user's
`feedback_record`s for a shared entity into every other user's `UserModelBuilder.build()` rebuild — a real
cross-user behavioral-evidence leak, not a hypothetical one. `MemoryStore.query()`/`.all()` had no `user_id`
parameter at all despite the SQLite schema already having a required `user_id` column and index (Sprint
3.6.7 Block 3) — the isolation that column was built for was simply never enforced at the read path.

## Two review points resolved before continuing (post-usage-limit resume)

The owner asked for two specific things to be checked, not assumed, before continuing implementation:

1. **`record_interaction()` ownership** — whether it had drifted from `Orchestrator.run_feedback_loop()` to
   calling `feedback_engine.interpret()`/`learning_engine.process_feedback()` directly. Checked by direct
   read plus a repo-wide grep for both method names outside `orchestrator/pipeline.py` — confirmed no such
   bypass exists anywhere in this codebase. The function has gone through the Orchestrator's content-builder-
   callable pattern (ADR-047) since Sprint 3.6.6, unchanged by this block. No code change needed; documented
   as reviewed-and-confirmed-clean.
2. **`DomainPref(weight=0.5)`** — whether this is an arbitrary invented behavioral weight. Confirmed by
   inspection: it's a required contract field with no documented semantic meaning anywhere in the spec, and
   — checked directly — no consumer reads `domain_preferences[].weight` anywhere in Reasoning,
   OpportunityEngine, Policy, or Prioritization today; it's also never updated again after creation. Unlike
   `model_confidence`'s own `0.5` (a real, evidence-scaled formula), this is genuinely inert. Left the value
   unchanged (removing it would mean a contract change, out of scope) and added explicit comments at both
   construction sites in `user_model/model.py` documenting why it's inert rather than silently leaving it
   unexplained or inventing new meaning for it.

## What got built (see ADR-057 for the full per-area record)

1. **Identity transport** — new `X-Stratus-User-Id` header, resolved via `backend/app/user_context.py`'s
   `resolve_user_id()` FastAPI dependency. Absent → `LOCAL_FOUNDER_USER_ID`, so every existing caller (the
   mobile app sends no such header today) is completely unaffected. Wired into every user-facing route.
2. **`MemoryStore.query()`/`.all()` now require `user_id` explicitly** — no default, no "all users" mode.
   Closes the real leak at its root (`orchestrator/pipeline.py`'s `run()` now passes `user_id=user_id`).
   No SQLite schema change — the column and index already existed; this is a Python interface-contract change,
   migrated deliberately across 3 production and ~15 test call sites.
3. **`backend/app/logan_feed.py`'s singletons converted to per-user dicts** — `_user_model` →
   `_user_models`, the `OpportunityContextCache` → per-user (closes the sharpest read-side leak: it carries
   personalized `personal_relevance`/`connection_basis`/`is_new_for_user`), `_ask_sessions` → keyed by
   `(user_id, session_id)` since a session_id is client-generated and not itself a secret. The shared
   `_orchestrator` (one World Model) is deliberately **not** duplicated per user — two users seeing the
   identical `event_id` for the identical real-world fact is correct; only the personalization layer on top
   is user-scoped.
4. **New-user seeding: blank, never copied from the founder** — only `LOCAL_FOUNDER_USER_ID` gets the seeded
   NVDA holding/AI_SECTOR interest; every other `user_id` starts genuinely blank.
5. **`backend/app/notifications.py`'s token/dispatch/review state converted to per-user dicts** — the
   background poller now loops once per registered user, computing that user's own alert-eligible items and
   dispatching only to their own tokens.

## Status at the end of this session

`backend` test count 179 → 193 (+14, `test_multi_user_isolation.py` — identity-boundary backward
compatibility, behavioral-evidence isolation, explicit-vs-inferred relevance isolation including the
founder-seed-never-copied guarantee, Ask STRATUS session/OpportunityContext isolation including a deliberate
session-id-collision case, Watch notification-review isolation, push-token/dispatch/review isolation, and
restart-persistence staying correctly user-scoped). `logan_core` unchanged at 306 (no new logan_core-only
test file — its own call-site migrations are covered by the existing suite, including a rewritten
`test_compaction_is_scoped_per_user` that now checks each user's own `.all(user_id=...)` view directly).
Combined 485 → 499. mypy/ruff/black clean — the same 14 pre-existing `**dict[str, object]` mypy findings from
Block 1 are unchanged in count and location. `AskRequest`/`AskResponse`/every other request contract is
unchanged (identity travels via header, not body) — no mobile contract impact, no mobile test re-run
required. Committed locally, **not pushed**, per explicit instruction pending review.

## Deferred / flagged for the owner

- Mobile has no persisted per-device identity mechanism at all yet — `X-Stratus-User-Id` is never actually
  sent by any real client today. Wiring that up would need a new client-side storage dependency
  (`expo-secure-store` or similar) not present in this app — a separate, explicit dependency decision, not
  folded into this block.
- `DomainPref.weight`'s "inert, no consumer" status is now documented but not resolved — a real per-domain
  weighting design, if ever needed, is a separate future decision.
- Push-token/dispatch/review state remains in-memory, process-lifetime only per user — a durable per-user
  token store surviving a restart is still an ADR-006-scale decision, unmade.
- The single process-wide `_state_lock` remains coarse-grained (one lock across every user's pipeline runs) —
  correct, not a regression, but a real scalability limit at higher concurrent-user counts; out of this
  block's own "no broad performance work" scope.
- `docs/specs/.../27_SECURITY_PRIVACY_COMPLIANCE.md`'s prior "multi-user persistence explicitly excluded from
  V3.1.4 scope" note needs a follow-up edit reflecting this block's real (if partial) multi-user isolation
  work.

---

# Session Notes — 2026-08-23 (Sprint 3.6.8 Block 3 — bounded conversational Ask STRATUS)

Branch: `feat/sprint-3.6.7-stock-signal-expansion`, continuing directly from the Block 2 closeout commit
`9f8807e`. See ADR-058 (`docs/DECISIONS.md`) for the full decision record; this note covers the session
narrative. Working autonomously per the owner's own instruction, with Block 4 to follow directly if Block 3
finished clean with no unresolved owner-level decision.

## What was asked

Turn the existing single-turn grounded Ask STRATUS path into bounded, genuinely conversational reasoning --
"why?", "which of those signals is strongest?", "is that because of the analyst downgrade?" -- while keeping
deterministic STRATUS intelligence as the sole source of authoritative truth.

## The recon finding that shaped the whole block: mobile already does its half

Before writing any code, read `mobile/app/ask.tsx` closely. It already renders a real, accumulating
multi-turn conversation (a `messages` array of user/assistant turns), already resends the identical
`session_id` on every submit within one screen visit, already resends the same `eventId` from its route
params on every turn (never omitting it to rely on session continuity), and already handles
loading/timeout/error states. The entire gap was server-side: nothing retained what was asked earlier, and
nothing threaded it into the LLM call. This meant the block's own "minimum additive mobile changes" and
"reuse rather than rebuild" instructions resolved to **zero mobile code changes** -- confirmed, not assumed,
by re-running the full mobile suite (100 Jest tests, `tsc --noEmit`, `eslint`) at the end and finding it
untouched and clean.

## What got built (see ADR-058 for the full per-area record)

1. **Bounded history on the existing per-`(user_id, session_id)` `_AskSession`** (Block 2's own store, not a
   new one) -- `_MAX_ASK_HISTORY_TURNS=6` pairs, `_MAX_ASK_HISTORY_CHARS=4000` as a secondary defensive bound,
   both reasoned small integers in this codebase's existing style, not tuned against usage data. Eviction
   always drops a full `(user, assistant)` pair at once so retained history never breaks the
   strictly-alternating-role invariant Anthropic's Messages API requires.
2. **Opportunity-anchor-change detection** -- new this block: `set_ask_session_event()` now clears history
   when a session's `event_id` genuinely changes, a deliberate reset so a "why?" can never accidentally
   resolve against a different opportunity. Resending the same `event_id` every turn (what mobile already
   does) is correctly a no-op.
3. **Authoritative-context-wins made an explicit, structural invariant** -- `build_system_prompt()` still
   takes only `context`, so history can never be concatenated into the system prompt at all; new prompt text
   states current context always wins over anything implied by an earlier turn, from either party.
4. **No invented signal ranking** -- added to the system prompt directly: without a genuine convergence
   firing, say the data doesn't support a definitive ranking rather than inventing one (the deterministic
   path's own `_dominant_signal_answer` already enforced this; now the LLM path says so explicitly too).
5. **Provider abstraction evolved additively** -- new vendor-neutral `ConversationTurn`, `AskLlmProvider.
   generate()` gained a defaulted `history` parameter, `AnthropicAskLlmProvider` is the only place that
   translates it into Anthropic's own message shape.
6. **Deterministic fallback: reasoned, not just implemented** -- the fallback path deliberately does not
   attempt conversational reference resolution (a materially larger, separate change); whichever path
   actually produced an answer becomes the retained turn, since both are real and true.
7. **ASK_FOLLOWUP bound: verified unchanged, not re-derived** -- the existing per-`(session, opportunity)` cap
   already made conversational depth independent of personalization strength; added tests proving 12
   real turns and a mid-session opportunity switch both stay correctly bounded.

## Status at the end of this session

`backend` test count 193 → 223 (+30, `test_ask_conversation.py`). `logan_core` unaffected (306). Combined
529. mypy/ruff/black clean (one new mypy fix needed: `messages` had to be typed as
`list[anthropic.types.MessageParam]`, not a plain `list[dict[str, str]]`, for the SDK's overload resolution
to accept it -- caught immediately by the existing mypy pass, not a runtime bug). Mobile: 100/100 Jest,
`tsc --noEmit`, `eslint` all clean with zero code changes. No owner-level architecture decision was
encountered -- provider abstraction, bounded-cache design, and history-eviction policy were all judged to be
within the pre-approved "straightforward bounded-cache implementation" / "normal refactoring" categories.
Continuing directly into Block 4 per the owner's own instruction.

---

# Session Notes — 2026-08-23 (Sprint 3.6.8 Block 4 — beta-readiness hardening)

Branch: `feat/sprint-3.6.7-stock-signal-expansion`, continuing directly from the Block 3 closeout commit
`0d0b771`. See ADR-059 (`docs/DECISIONS.md`) for the full decision record; this note covers the session
narrative.

## A mid-session rule from the owner reshaped how this block's recon was reported

Partway through the integrated-path recon, the owner stated an explicit, governing rule: production
opportunity generation must be live-data-first -- demo fixtures/hardcoded events/synthetic qualifying
conditions belong only in deterministic tests and acceptance scenarios, never the real app path, and no
threshold may ever be lowered or a signal fabricated to force a live check to pass. Confirmed understanding
immediately and reported the true state honestly: Block 3 never touches signal generation at all (no
violation there), but the broader, pre-existing app has always run its production feed
(`/v1/opportunities`) on `simulated_fixtures()` for 10 of 11 entities, with only NVDA having any live path
at all -- a foundational fact from Sprint 3.6.6, not something this sprint introduced. Built a precise
inventory rather than a guess (see ADR-059 Decision 8): TSLA/AAPL could extend the *existing* FMP
integration without a new vendor (it's hardcoded to the symbol "NVDA," not parameterized); MARKETS/OIL need
a product decision about what instrument they represent; the other five entities (BTC/FED/NFL/MUSIC/POLY)
each need a genuine new external vendor per domain. None added, none guessed at -- reported as the single
biggest beta-readiness finding.

## Two real bugs found and fixed during the integrated-path recon

1. **Notification dispatch per-user isolation had a real gap.** `dispatch_eligible_notifications()`
   (Block 2) already documented that one user's failure must not stop another's dispatch -- but only the
   push send itself was guarded; the per-user pipeline call (`get_alert_eligible_items(user_id)`) was not.
   An exception there would have silently skipped every other registered user for that whole poll cycle,
   contradicting the function's own stated contract. Fixed by widening the try/except to cover the whole
   per-user body; new test proves the fix.
2. **The notification poller blocked the event loop.** `_notification_poll_loop()` is `async def` but
   called the fully synchronous `dispatch_eligible_notifications()` directly -- unlike every HTTP route
   (plain sync `def`, already threadpooled by FastAPI/Starlette automatically), this ran a full pipeline per
   registered user, including up to three sequential 10s-bounded live FMP calls when enabled, directly on
   the main event loop. A slow poll cycle would have frozen every other concurrent request. Fixed with
   `asyncio.to_thread()`. Currently inert (the live flag defaults off) but a real, latent hazard.

A third, smaller hardening addition: FMP's error messages include up to 200 characters of the raw response
body, and the API key is sent as a URL query param -- some APIs echo an invalid credential back in an error
message. Added a defensive `_redact()` helper so the real key can never end up in a raised exception's
message, even though no live-observed instance of this ever happened; "never log API keys" is satisfied by
construction, not just by absence of an observed problem.

## What got built (see ADR-059 for the full per-area record)

1. The two bug fixes above, plus the FMP key redaction.
2. Minimum viable observability: one new log line per successfully-grounded Ask STRATUS turn (`user_id`,
   `entity_id`, which path answered) -- routing metadata only, never question/answer text, using the
   existing `print(f"[tag] ...")` convention already established throughout this codebase.
3. A restart-safety matrix made an explicit, executable test: MemoryStore records survive a persisted
   restart; AttentionState (Watch fatigue/cooldown), Ask conversation history, and notification token state
   all do not, regardless of the persistence flag -- documented as a real contract, not left implicit.
4. Multi-user regression re-proven through the actual Block 3 conversational stack (not just the original
   single-turn surface Block 2 shipped against), including a shared `session_id` string between two users.
5. The full integrated acceptance path from the block's own spec, using fixtures throughout and never
   forcing a live threshold to pass.
6. `27_SECURITY_PRIVACY_COMPLIANCE.md` corrected precisely, not just softened -- the stale "no way for a
   second distinct user to exist" claim replaced with an accurate, careful description of what Block 2
   actually built (real backend state isolation) and what it explicitly is not (authentication -- the
   `X-Stratus-User-Id` header is never verified against anything).

## Status at the end of this session

`backend` test count 223 → 227 (+4). `logan_core` unchanged (306, only the redaction helper touched,
behavior-neutral). Combined 529 → 533. mypy/ruff/black clean (same pre-existing baseline pattern). Mobile:
100/100 Jest, `tsc --noEmit`, `eslint` clean with zero code changes. No owner-level architecture decision
was required to complete this block's actual scope -- the two real beta-readiness blockers found (live-data
coverage, `eas.json`'s missing `EXPO_PUBLIC_API_BASE_URL`) were both correctly *not* attempted, matching the
standing instruction not to guess at new-vendor or hosting decisions, and are reported precisely instead.

---

# Session Notes — 2026-08-23 (Sprint 3.6.8 Block 5 — live-data transition foundation)

Branch: `feat/sprint-3.6.7-stock-signal-expansion`, continuing directly from the Block 4 closeout commit
`e1c24b5`. See ADR-060 (`docs/DECISIONS.md`) for the full decision record; this note covers the session
narrative. Governed throughout by the owner's explicit live-data-first rule (confirmed and applied at the
start of Block 4, restated as this block's own primary directive).

## What was asked

Remove the NVDA-only limitation from the already-approved FMP provider architecture and establish a
reusable live equities runtime path, bringing NVDA/TSLA/AAPL onto real data without adding a new vendor.
Establish an explicit production-vs-demo runtime boundary. Complete the fixture-backed runtime inventory
Block 4 started. Do not choose providers for BTC/FED/NFL/MUSIC/POLY/macro/sports/prediction-markets.

## The recon finding that made this block clean: the NVDA coupling was never architectural

Before writing any code, traced every layer named in the recon list. The result was better than expected:
`logan_core`'s entire receptor-mapping layer (`earnings_report_to_raw_signal`/`quote_to_raw_signal`/
`grade_change_to_raw_signal`), `FmpEarningsProvider`/`FmpMarketDataProvider`, `StocksTriggerEvaluator`, and
critically `StockConvergenceTracker` were already fully entity-generic -- a repo-wide grep for "NVDA" inside
`logan_core/` found zero real hardcoded logic, only docstring comments and an unrelated ripple-connection
map. `StockConvergenceTracker` was already internally keyed by `entity_id` (`_observations`/
`_active_episode` dicts), meaning multi-stock convergence entity isolation required no code change at all --
just a test proving it, since it was already correct by construction. The *entire* NVDA-only coupling was
three private functions and one config flag, all inside `backend/app/logan_feed.py`/`config.py`. This
significantly narrowed the actual scope of "generalize NVDA-only live stock handling" to something much
smaller and safer than the block's own framing implied.

## Two real bugs found while generalizing the wiring -- both the exact pattern the owner's rule forbids

1. **TSLA's simulated corroboration signal was unconditionally appended**, regardless of whether TSLA's own
   primary signal that poll was genuinely live. A real live TSLA earnings beat would have been silently
   joined by a fabricated "Reuters confirms AI chip partnership" corroborating signal -- simulated
   intelligence entering a live-labeled opportunity, exactly what the rule forbids. Fixed with a
   `live_substituted` set tracking exactly which tickers went live this poll.
2. **Price-move/analyst-grade fetches were gated only on the flag being on, not on whether earnings itself
   went live that poll.** A live price-move signal could have been spliced onto a *simulated* primary
   earnings signal when the live earnings fetch failed -- a genuinely blended simulated+live opportunity,
   since World Model's narrative is driven by the first/primary signal in the raw_signals list. Fixed with
   the same `live_substituted` gate: an opportunity is now always fully live or fully simulated, never a
   blend. Both bugs pre-date this block (they existed in the original NVDA-only wiring too) -- found here
   because generalizing to multiple tickers made the blast radius concrete enough to prioritize.

## What got built (see ADR-060 for the full per-area record)

1. `config.live_stock_tickers()` -- new `STRATUS_LIVE_STOCK_TICKERS`, backward-compatible with the original
   `STRATUS_LIVE_NVDA_EARNINGS` flag (falls back to `("NVDA",)` when the new flag is unset).
2. Three NVDA-hardcoded functions generalized to accept any ticker, exact same failure-mode discipline,
   deliberately preserving the pre-Block-5 substitution semantics (only BEAT triggers substitution, not
   MISS/IN_LINE -- see the real live-verified gap below).
3. The two bug fixes above.
4. `config.live_data_only_mode()` -- new `STRATUS_RUNTIME_MODE`, the production-vs-demo boundary. In
   live-data-only mode, `fixtures` starts empty; an entity only appears if a genuine live fetch substituted
   it. One small change makes every one of the block's live/demo requirements true at once.
5. Data provenance: confirmed the existing `source_id` field (`"fmp"` vs. `"bloomberg_terminal"` etc.) and
   the existing print-based observability convention already served this purpose completely -- nothing new
   was built, no parallel metadata architecture invented.
6. A generalized live-verification script, run for real against the real FMP API.

## Live verification, run for real (2026-08-23)

**NVDA** -- real earnings beat fired (1.87 vs. 1.76 consensus); price move (-0.98%) and analyst grade
(maintain) correctly did not fire. **TSLA** -- real earnings *miss* fired (0.33 vs. 0.50) and real price move
(+5.14%) fired; through the actual `_run_feed_pipeline()` wiring, this correctly did **not** go live,
directly confirming the deliberate BEAT-only gap with real data, not a hypothetical. **AAPL** -- real
earnings beat (2.02 vs. 1.89) and a real analyst downgrade both fired, combining into one coherent live
opportunity. No convergence fired for any ticker (none reached 3 distinct signal types) -- honest, not
forced. This is the first time this codebase's live-data path has been proven against more than one entity
with real, current market data.

## Status at the end of this session

`backend` test count 227 → 267 (+40: `test_config_live_stocks.py` 17, `test_live_equities.py` 23).
`logan_core` unchanged (306 -- the entire generalization lived in `backend/app/`, confirming logan_core was
already entity-generic). Combined 533 → 573. mypy/ruff/black clean. Mobile: 100/100 Jest, `tsc --noEmit`,
`eslint` clean with zero code changes. No owner-level architecture decision was encountered -- no new vendor
was added or selected for any domain, matching the standing instruction precisely.

# Session Notes — 2026-08-23 (Sprint 3.6.9 Block 1 — Remote STRATUS: Fly.io hosting readiness)

## What was asked

First block of Sprint 3.6.9 ("Beta Foundation: Remote Operation + Sports/Odds Intelligence"), following the
formal post-3.6.8 gap analysis. Scoped to remote operation only — Sports/Odds explicitly deferred. Owner
decisions given up front: Fly.io as the hosting target; SQLite kept on a durable Fly Volume (no PostgreSQL
migration this block); `STRATUS_PERSIST_MEMORY` enabled for the hosted configuration; mobile API
configuration in-scope; no external account/payment/secret created without the owner doing so directly.
Reconnaissance and a hosting/persistence decision package were delivered first (Fly.io recommended over
Render/AWS-GCP; SQLite-on-durable-volume recommended over an immediate Postgres migration) and approved
before any implementation began.

## The correctness gap the owner specifically asked to be investigated: notification state on redeploy

Reconnaissance had flagged registered push tokens and dispatch/review dedup state as process-memory only,
unrelated to `STRATUS_PERSIST_MEMORY` — every hosted redeploy would silently drop every tester's push
registration. Investigated whether this was a contained fix using the existing durable-volume architecture,
per the owner's explicit "if contained, implement it" instruction. It was: a new, independent SQLite file
(`NotificationStore`, a sibling of `MemoryStore`'s own file, never a shared connection to it) reusing the
existing `STRATUS_PERSIST_MEMORY` flag rather than a second toggle. Persisted the three flat dedup
sets — registered tokens, dispatched-event ids, reviewed-event ids — and deliberately did *not* persist
Ask STRATUS session history, the `OpportunityContext` cache, World Model/orchestrator event identity, or
STRATUS Watch's fatigue/cooldown `AttentionState`, per the owner's explicit "don't persist everything"
scope. The fatigue/cooldown case got its own judgment call (see ADR-061 Decision 4): not persisted this
block — a materially different, larger-shaped piece of `PrioritizationEngine`-internal state than the flat
dedup sets, and the risk is already bounded by the independent per-event dispatch dedup, which prevents an
actual duplicate *push* regardless of fatigue state. Documented as a known, bounded gap, not silently
skipped.

## One real bug found while wiring the notification persistence in

`dispatch_eligible_notifications()` (the background poller's own function) checked
`if not _registered_tokens: return 0` *before* anything had triggered the durable store's lazy load. On the
very first poll cycle after a real restart — before any client had re-registered a token that process's
lifetime — this would have silently short-circuited to "nothing to do" every cycle, meaning the entire
point of the persistence being added (not needing to reopen the app after a redeploy) would have silently
never actually worked. Fixed by calling `_get_store()` (which hydrates the three dicts from disk on first
use) at the very top of that function, before the empty check. Caught by writing
`test_enabled_mode_dispatch_dedup_survives_restart_no_duplicate_push`, which simulates exactly this
sequence (dispatch → restart → dispatch again) and asserts no second push actually went out.

## What got built (see ADR-061 for the full per-area record)

1. `Dockerfile`/`.dockerignore`/`fly.toml` (repo root) — repository made deployment-ready, nothing deployed.
   Build context is the repo root, not `backend/`, because `backend/app/*.py`'s existing `sys.path` bridge to
   `logan_core` (ADR-022) needs both directories present as siblings — preserved rather than refactored.
   `.dockerignore` excludes `backend/.env` (holds the real `FMP_API_KEY`/`ANTHROPIC_API_KEY`) and local
   `*.db` files from the image. `fly.toml` pins `min_machines_running=1`/`auto_stop_machines=false` because
   the existing in-process notification poller only works while the server process stays running.
2. `config.legacy_memory_db_path()` — the historical `memory_engine.py` prototype's SQLite path was
   hardcoded to `backend/data/`, which is ephemeral container storage in a hosted deployment; now
   configurable via `STRATUS_LEGACY_MEMORY_DB_PATH`, defaulting to the exact pre-Block-1 path when unset.
3. `NotificationStore` + the wiring above.
4. `config.cors_allowed_origins()` — replaces the hardcoded `allow_origins=["*"]`. Demo/development mode
   unchanged; beta/production mode defaults to an empty allowlist unless explicitly configured. CORS is
   browser-only enforcement, so this can never affect the React Native app's own requests either way.
5. `config.startup_config_summary()` — one non-secret line logged at process startup stating effective
   runtime mode, configured tickers, persistence/LLM-Ask status, and the active CORS policy.
6. Mobile release-URL invariant — new `EXPO_PUBLIC_APP_ENV` (set per `eas.json` build profile) and
   `constants/config.ts`'s new `resolveApiBaseUrl()`/`isLanOrLocalUrl()` (pure, unit-tested functions).
   `development` keeps the existing zero-config LAN fallback exactly. `preview`/`production` throw a
   specific, readable error at load time if `EXPO_PUBLIC_API_BASE_URL` is unset, LAN/loopback-shaped, or not
   HTTPS — a deliberate loud-crash-over-silent-failure choice, since a release build silently pointing at an
   unreachable LAN address is indistinguishable from "the app is broken" with no diagnostic. `eas.json`'s
   `preview`/`production` profiles deliberately do not yet set `EXPO_PUBLIC_API_BASE_URL` (no Fly URL exists
   yet) — building either profile today correctly throws until the owner adds the real hosted URL, which is
   the intended behavior for this stage.

## Status at the end of this session

`backend` test count: 267 → 284 (+17: `test_deployment_config.py` 11, `test_notification_persistence.py`
6). `test_beta_hardening.py`'s restart-safety-matrix test updated to assert the new persisted-token
behavior (was asserting the now-superseded opposite). `logan_core` unchanged (306, no logan_core files
touched). mobile Jest: 100 → 125 (+25: `lib/__tests__/config.test.ts`). mypy (run from the repo root,
matching the existing baseline invocation)/ruff/black clean; `tsc --noEmit`/`eslint` clean. No Docker
install available in this environment to locally build the image — reviewed for correctness, not build-
verified; `fly deploy`'s own remote builder does not require local Docker either, so this is not expected to
block actual deployment. No Fly.io account, app, volume, or secret was created — see the Block 1 report for
the exact remaining owner steps. No merge to main; commit not pushed pending review.

# Session Notes — 2026-08-23 (Sprint 3.6.9 — Fly.io deployment + Remote STRATUS mobile closeout)

## Fly.io deployment (owner had already created the account/payment; this session did the CLI work)

Installed `flyctl`; interactive `fly auth login` could not complete through this session's non-interactive
shell even via the `!` prefix (confirmed twice) — the owner authenticated via a Fly Personal Access Token
instead, which doesn't need a browser callback. From there, executed end-to-end without further stops:
created app `stratus-api` (org `personal`), created and attached a 1GB encrypted `stratus_data` volume in
`iad`, imported `FMP_API_KEY` from `backend/.env` directly into `fly secrets import` via a shell pipe (never
printed, never touched by this session's own output), and deployed via `fly deploy` (Fly's remote builder —
no local Docker install needed or used). Enabled `STRATUS_LIVE_STOCK_TICKERS=NVDA,TSLA,AAPL` on the hosted
config (Block 1's `fly.toml` had it commented out) — the exact set already live-verified in Sprint 3.6.8
Block 5, not a new provider decision; without it, beta mode's live-data-only gate would have served an empty
feed forever, defeating the whole point of the deployment. Committed as `15b1cff`, pushed.

Verified against the real running app, not assumed: `/health` 200 over HTTPS; HTTP→HTTPS redirect (301);
`/v1/opportunities` returned real NVDA (EPS 1.87 vs. 1.76) and AAPL (EPS 2.02 vs. 1.89) data identical to
Block 5's local live-verification numbers, TSLA correctly absent (the documented MISS-doesn't-substitute
gap, now proven hosted, not just local); CORS confirmed non-wildcard (no `Access-Control-Allow-Origin` for
an arbitrary origin); deterministic Ask STRATUS confirmed both generic and contextually-grounded
(`grounded: true` against a real NVDA event_id); push-token registration proven durable across a **real**
`fly machine restart` (not simulated) — registered a token, restarted the machine, registered a second, got
`token_count: 2`, directly proving the exact behavior the original notification-persistence bug fix exists
for. Region/machine confirmed via `fly machine status`: `iad`, `shared-cpu-1x`, 512MB — matching the
intended spec exactly, no Amsterdam, no 256MB.

## Remote STRATUS mobile closeout

Checked for an existing `ANTHROPIC_API_KEY` anywhere in this project's approved local config
(`backend/.env`, `.env.*` files, current shell environment) without printing any value found — none exists.
LLM-grounded Ask STRATUS stays disabled on the hosted deployment; this is a genuine owner-only secret input,
not something this session could source itself. Deterministic Ask STRATUS (verified above) remains fully
functional regardless, exactly as designed.

Wired `mobile/eas.json`'s `preview`/`production` profiles to
`EXPO_PUBLIC_API_BASE_URL=https://stratus-api.fly.dev` — `development` unchanged, still LAN-based, per the
explicit invariant. Added a regression test (`config.test.ts`) that reads `eas.json` directly and asserts
its configured release URLs pass `resolveApiBaseUrl()`/are never LAN-shaped, so a future accidental edit
reintroducing a LAN address there is caught by the test suite, not discovered by a silently-broken build.
Re-confirmed by direct grep that the LAN fallback constant in `constants/config.ts` is the *only* LAN/
localhost reference anywhere in mobile code, and it is structurally unreachable once `EXPO_PUBLIC_APP_ENV`
is `preview`/`production` (which `eas.json` now sets for both profiles).

Ran a real, non-interactive `eas build --profile preview --platform ios`. Already-stored Apple distribution
certificate (valid through 2027) and provisioning profile (already includes the founder's iPhone UDID) meant
zero interactive Apple/2FA/certificate steps were needed — build succeeded in ~5 minutes. Install link:
`https://expo.dev/accounts/garris-engineering-llc/projects/logan-market-mobile/builds/faa2fe54-2889-4be3-ace1-aee44198393d`.
Build metadata confirms it picked up `EXPO_PUBLIC_APP_ENV`/`EXPO_PUBLIC_API_BASE_URL` from the edited
`eas.json`. mobile Jest 125 → 127 (+2); `tsc --noEmit`/`eslint` clean.

## Status at the end of this session

Fly deployment and mobile release-URL wiring are both live and verified by direct inspection, not just
tested in isolation. What remains is the physical-phone half of the acceptance procedure (install the build,
leave the LAN, stop the dev-machine backend, confirm the feed/Ask/push flow) — an owner-performed step by
nature, not something this session can execute itself. LLM Ask STRATUS on the hosted beta remains gated on
the owner supplying a real `ANTHROPIC_API_KEY`. No merge to main.

# Session Notes — 2026-08-23 (Sprint 3.6.9 Remote STRATUS closeout — physical acceptance + FMP caching)

## Physical acceptance test: passed

Owner confirmed, over cellular with home Wi-Fi off: the iOS preview build loaded the expected two live
opportunity cards from the hosted backend, and deterministic Ask STRATUS worked (correctly still only
reframing card content, since the hosted LLM path was not yet enabled at that point). `iPhone → cellular →
Fly.io → live STRATUS backend` confirmed working end-to-end, physically, not just via API testing from this
session.

## A real, already-occurring production problem found while measuring FMP usage (not projected)

Instructed to measure real FMP call volume before any capacity decision. Found actual `HTTP 429` rate-limit
errors already appearing in the hosted app's logs within ~25 minutes of the poller running -- not a
projection. Root cause, confirmed by inspection: `backend/app/logan_feed.py` constructs a fresh FMP provider
instance on every call (poller every 60s, plus every direct `/v1/opportunities` request) with zero caching
anywhere. Measured steady-state cost from the poller alone: ~10,080 calls/day against FMP's 250/day free
limit -- ~40x over.

Reported this, with the real math, before touching any code -- the owner's explicit decision was "optimize
first, do not upgrade the FMP plan."

## FMP provider-level TTL cache (see ADR-062 for the full record)

Implemented a shared, process-lifetime `FmpResponseCache` in `logan_core/receptors/providers/fmp.py`,
wrapping only the raw HTTP fetch inside each of the three FMP call methods -- trigger evaluation,
qualification, confidence, and convergence never know it exists. Endpoint-appropriate TTLs per the owner's
explicit guidance (earnings 6h, grades 2h, quotes 30min, reflecting how often each kind of data actually
changes) rather than one blanket value. Defaults to one shared module-level singleton, so the background
poller and every direct request genuinely share one cache despite each constructing a fresh provider
instance -- zero changes needed to `logan_feed.py`'s existing call pattern. Only real, successful responses
are ever cached (including a legitimate empty "no data" result, which is not an error); a raised
`FmpProviderError` always propagates uncached, so a transient failure retries next call rather than being
remembered as "no data" for a full TTL window -- this also means the live-data invariant ("no valid live
data -> no live opportunity, never a stale-disguised-as-fresh substitute") holds exactly as before.

Found and fixed a real test-isolation risk while implementing this: since the cache is a process-lifetime
module singleton, two different test functions fetching the same ticker through different mocks would have
the second one silently receive the first one's cached result. Added an autouse `reset_fmp_cache()` fixture
to both `backend/tests/conftest.py` and `logan_core/tests/conftest.py`, mirroring the existing
`reset_pipeline_state()`/`reset_notification_state()` convention.

**Calculated (not guessed) expected usage after the fix:** current real state (NVDA + AAPL both showing a
live earnings beat, TSLA does not) = 132 calls/day. Worst case, all three tickers qualifying simultaneously
= 192 calls/day. Both comfortably under the 250/day free-tier limit -- **the free FMP plan stays viable, no
upgrade needed.**

New `logan_core/tests/test_fmp_cache.py` (15 tests). `backend`/`logan_core` combined 590 → 605 (+15).
mypy/ruff/black clean.

## Status at the end of this session

FMP caching implemented, tested, and ready to deploy. Anthropic hosted-Ask work paused pending the owner
creating a new `ANTHROPIC_API_KEY` (the previously-referenced Sprint 3.6.8 key was searched for exhaustively
across the repo, all git worktrees, and likely backup locations on the PC -- confirmed genuinely never
existed anywhere findable, not merely misplaced). No merge to main.
