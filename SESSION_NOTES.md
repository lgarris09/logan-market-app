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
approach before building it.
