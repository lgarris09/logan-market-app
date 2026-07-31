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
   need real data, not invented numbers), and whether the full 5-tab navigation is worth building next.
