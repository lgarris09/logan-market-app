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
   BIAS learning, Ask STRATUS linkage) remains correctly deferred, unchanged from the prior session's report.
   need real data, not invented numbers), and whether the full 5-tab navigation is worth building next.
