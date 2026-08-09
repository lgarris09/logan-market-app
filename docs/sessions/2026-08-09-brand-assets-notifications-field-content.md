# Session note — 2026-08-09 — STRATUS brand assets, real notification system, Attention Field content redesign

Continuation of Sprint 3.6 (device-driven correction pass). Three largely independent threads in one
session: (1) replacing the hand-coded SVG brand marks with the owner's actual approved artwork, one
placement at a time with real-device feedback loops; (2) a live "new opportunity" notification badge on
the header dot, first built client-side then rebuilt against a genuine backend fix once a real architectural
bug was found; (3) restyling the Attention Field's resting vessels with real data (name, confidence
percentage, reason tag) per a new owner-supplied "Field Bias" reference sheet, which surfaced and fixed a
real vessel-collision bug in the layout algorithm.

## What was completed

### 1. STRATUS brand asset rollout (real artwork, not hand-coded SVG)
The owner supplied actual approved artwork (not just a reference image to approximate) and asked for it to
be used directly:
- **Wordmark** (`assets/images/stratus-wordmark-header.png`): cropped from the owner's source PNG. The
  source file's alpha channel was degenerate (zero everywhere despite real RGB data) — first crop attempt
  lost the artwork entirely. Fixed by synthesizing real alpha from luminance (glow-on-black "screen matte"
  technique). Went through several real-device rounds: washed out (glow radius too wide for a small render
  size) → tighter alpha cutoff → still hazy → isolated the true solid-fill plateau (~253-255 brightness) and
  cut everything below it, eliminating the halo entirely while keeping the letterforms and orange A crisp.
  Sized by width (132px header, 220px About screen, reused menu/About), not height — a fixed-height render
  let the glow padding dictate perceived size.
- **Horizon/sun mark** (`assets/images/stratus-horizon-mark.png`): this source file had a real, correctly
  varying alpha channel (unlike the wordmark) — direct crop worked on the first attempt. Used in Ask
  STRATUS's first-run state and the menu drawer footer (sized 30 → 42 → 52 → 58 → 62px wide across several
  owner-directed bumps).
- Both `StratusWordmark.tsx` and `HorizonMark.tsx` (the earlier hand-coded SVG components) are now unused
  everywhere in the app — left in place, not deleted unasked.
- Attention Field header layout fixed to a true 3-column centered arrangement (equal-width bookend columns
  for hamburger/dot) so the wordmark centers precisely regardless of icon/dot width — `justifyContent:
  space-between` on 3 unequal children doesn't actually center the middle one.

### 2. Header dot: pulse animation + real notification system
- Dot given a slow scale pulse (Reanimated `withRepeat(withTiming(...), -1, reverse: true)` — the initial
  manual `withSequence` + `withRepeat(..., false)` combination snapped at the loop boundary instead of
  reversing smoothly).
- Built a notification badge: tap opens a dropdown of new opportunities (name + confidence %), tapping an
  entry opens that vessel's real Opportunity Card via a new `AttentionField` `openRequest` prop (reuses the
  exact focus/disclosure state a direct vessel tap sets — not a second card implementation).
- **Real architecture bug found and fixed, not just a mobile feature.** `backend/app/logan_feed.py` built a
  brand-new `Orchestrator()` on every single `/v1/opportunities` request, so World Model's event-dedup index
  and Prioritization's `AttentionState` reset every time — every item got a random new `event_id` on every
  poll, and nothing could ever be told apart from "genuinely new" vs. "the same thing again." Owner
  explicitly approved fixing this properly (`backend/app/logan_feed.py` is normally hands-off) rather than
  routing around it with more client-side ID-diffing.
  - **Fix:** persistent, process-lifetime `Orchestrator` singleton (thread-safe, `threading.Lock`) —
    explicitly documented as resetting on backend restart; no durable/cross-restart persistence added
    (that's the separate, still-open ADR-006 question).
  - **Kept two concepts deliberately separate**, per explicit owner instruction: World Model event
    identity/dedup (already correct, untouched) vs. new `PrioritizedItem.is_new_for_user` / new
    `AttentionState.notifications_reviewed` (`NotificationReviewRecord`) for "has *this user* reviewed this
    opportunity." Did not reuse `changed_since_view` (its real job is overriding cooldowns on content
    change, a third concept) or `dismissed` (reserved for a different future "stop resurfacing" action).
  - New `POST /v1/notifications/review` endpoint (`PrioritizationEngine.mark_reviewed`).
  - First load per user is notification-silent (baseline established, not flagged as all-new).
  - Mobile side rewritten: `unread` is now derived directly from `FeedItem.is_new_for_user` each poll
    (no more client-side accumulation/diffing), with a small optimistic local-review overlay so the badge
    clears instantly while the backend catches up async.
  - Dev-only test button redesigned to force a *real* currently-displayed item's ID unread (not a fake ID),
    so it exercises the actual open-card flow too.
  - **A deliberate, understood side effect:** fixing the identity bug means `EvidenceTrustEngine`'s
    corroboration count now legitimately grows across repeated observations of the same event (more
    corroborating signals → higher trust → possibly different confidence/rank over a session). Two existing
    tests (`test_opportunities_matches_demo_feed_pipeline_output`,
    `test_feed_is_deterministic_across_runs`) only passed *because* of the old bug; fixed by resetting
    pipeline state between their comparison calls rather than weakening the assertions.
  - Verified end-to-end on the real running server (not just unit tests): first load silent, IDs stable
    across repeated polls, review endpoint works, confirmed on-device with no 60s reset.

### 3. Attention Field vessel content redesign (real data, not more chrome)
Owner supplied a new "Field Bias" reference sheet (FIELD BIAS control itself explicitly out of scope again,
same as earlier rounds) showing vessels with name + confidence percentage + a short reason tag, reversing
the earlier "zero descriptor text" decision from the previous brand pass.
- Confirmed two things needed honest handling rather than fabrication, per the project's "don't fake
  capabilities" rule:
  - The reference's trend arrow (up-triangle) has no real backing data (`trending_indicator` is spec'd but
    not implemented anywhere in `logan_core`, confirmed earlier this session) — **omitted**, not faked.
  - The reference's short descriptor phrases aren't backed by any existing field — but the real
    Normalization-layer `signal_type` (e.g. `earnings_signal`, `volatility_spike`) already exists and reads
    close in spirit when humanized. Added `signal_type: str` to `FeedItem` (backend + mobile contract) and a
    small `humanizeSignalType()` helper — real data, not hand-authored copy.
- `Vessel.tsx`'s resting label redesigned: name (bigger, bold) → confidence percentage (large, category
  color, tabular figures) → descriptor (small, quiet, real `signal_type`). Dropped the redundant
  `EntitySymbol` icon badge next to the name (the reference's cleanest vessels show none, and it duplicated
  the name text). The opened Opportunity Card itself is untouched.
- **Found and fixed a real layout bug this content change exposed.** Roughly doubling each vessel's label
  footprint (three real data lines instead of two) broke the field's collision-avoidance math in two ways:
  1. An AABB (rectangle) non-overlap doesn't imply the underlying glow *circles* don't overlap when the
     rectangle is much taller than the circle it contains — resolving a label-rectangle overlap via a
     vertical push could leave two glow circles still visibly overlapping. Fixed with an independent
     circle-only separation check (pushed along the true vessel-to-vessel vector) alongside the existing
     rectangle check.
  2. The relaxation algorithm's per-pair push had no way to compensate when one vessel got clamped at a
     field edge mid-push — its partner never learned the shortfall existed, and the pair silently settled
     for a real, visible overlap. Fixed with shortfall compensation (`moveAndClamp` reports how much of the
     intended movement actually happened; the other vessel absorbs the difference).
  3. Widened the innermost radius band (`RADIUS_MIN_FRACTION` 0.17 → 0.22) so the two largest,
     highest-priority vessels have enough circumferential room to coexist — without touching
     `SIZE_MAX_FRACTION`'s separately-tuned prominence-contrast decision.
  - Trimmed label footprint dimensions once during implementation (132/56/46 → 118/47/40) after confirming
    via a throwaway diagnostic test that the larger estimate was genuinely infeasible for the highest-
    priority vessels' inner radius band, not just under-iterated.

### 4. Operational lesson (saved to memory, not just this note)
Restarting the backend repeatedly appeared not to pick up code changes. Root cause: on this Windows
machine, `uvicorn --reload`'s actual request-handling worker is a separate `multiprocessing.spawn_main`
child process — killing the parent reloader's PID does **not** kill it, and the orphan keeps silently
serving the old port with stale code (one orphan traced back to that morning's very first backend launch).
Saved as a feedback memory (`backend_uvicorn_orphan_workers.md`): always verify via
`Get-CimInstance Win32_Process -Filter "Name = 'python.exe'"` and kill every related process, not just
whatever `Get-NetTCPConnection` currently reports as the port owner, before trusting a restart.

## Files created or modified

**Backend/logan_core — modified:** `backend/app/logan_feed.py` (persistent Orchestrator, baseline handling,
`is_new_for_user`, `signal_type`), `backend/app/main.py` (`POST /v1/notifications/review`),
`backend/app/models.py` (request/response models), `backend/tests/conftest.py` (autouse pipeline-state
reset fixture), `backend/tests/test_logan_feed.py`, `backend/tests/test_opportunities_api.py`,
`logan_core/contracts/__init__.py`, `logan_core/contracts/prioritization.py` (`NotificationReviewRecord`,
`is_new_for_user`), `logan_core/prioritization/engine.py` (`mark_reviewed`), `logan_core/tests/
test_presentation.py`, `logan_core/tests/test_prioritization.py`.

**Backend/logan_core — new:** `backend/tests/test_notifications.py`.

**Mobile — new:** `assets/images/stratus-wordmark-header.png`, `assets/images/stratus-horizon-mark.png`,
`lib/signalType.ts`, `lib/__tests__/signalType.test.ts`.

**Mobile — modified:** `app/index.tsx` (brand assets, live dot pulse, full notification system rewrite),
`app/ask.tsx` (horizon mark), `app/about.tsx` (wordmark — see prior session note, carried into this one's
git status), `components/Vessel.tsx` (rest-label content redesign), `components/AttentionField.tsx`
(`openRequest` prop), `lib/attentionLayout.ts` (label footprint, relaxation algorithm fixes, radius band),
`types/loganFeed.ts` (`is_new_for_user`, `signal_type`), plus test-fixture updates in
`lib/__tests__/attentionLayout.test.ts` and `components/atmosphere/__tests__/AttentionAtmosphere.test.tsx`.

(Several other modified/untracked files in `git status` — `StratusWordmark.tsx`, `HorizonMark.tsx`,
`ConfidenceRing.tsx`, `RecommendationPanel.tsx`, `lib/cardOverflow.ts`, `lib/relativeTime.ts`, etc. — are
carried over from the prior Sprint 3.6 session, not new this session; see the 2026-08-08 session note.)

## What was verified

- Mobile: `tsc --noEmit`, `eslint .`, `prettier --check .` all clean; **46/46** Jest tests passing.
- Backend/logan_core: `black --check`, `ruff check`, `mypy` all clean; **118/118** pytest passing.
- Live-verified against the actual running backend (not just tests): brand assets rendered correctly at
  real size on-device across multiple owner-reviewed rounds; notification first-load-silent + stable-ID +
  repeated-request-stays-quiet + review-endpoint all confirmed via `curl`/PowerShell against a verified
  single clean server process, then confirmed again on the physical iPhone (owner: "no 60 second reset").
  Attention Field content redesign validated via automated layout tests (collision/overlap/footprint) —
  **not yet seen on the physical device as of this note.**

## Known issues / open items carried forward

- **Nothing from this session (or the prior Sprint 3.6 session) has been committed.** `git status` shows
  ~30 modified files plus ~15 new/untracked files across `backend/`, `logan_core/`, and `mobile/`.
- The Attention Field vessel content redesign (name + % + descriptor, new relaxation algorithm) has **not
  yet been retested on the physical iPhone** — this is the very next thing to do next session.
- Several decisions from today look ADR-worthy but aren't yet formalized in `docs/DECISIONS.md`: the
  Orchestrator persistence fix and its process-lifetime-only scope; the `is_new_for_user` vs. event-identity
  separation; the relaxation algorithm's circle-check + shortfall-compensation additions.
- `changed_since_view` remains hardcoded to its default (`True`) by the Orchestrator caller — a real,
  pre-existing, separate bug noticed while investigating the notification fix (this makes the
  cooldown-override mechanism currently inert in production). Not fixed — explicitly out of scope for this
  pass, flagged for a future one.
- Durable/cross-restart notification persistence remains blocked on ADR-006 (database/hosting still
  officially undecided) — the current fix is honestly scoped to "correct while the backend process is
  running," not durable.
- All infrastructure risks from prior session notes (no `logan_core` installable packaging, no auth/
  production hosting, CORS wide open) stand unchanged.

## How to resume next session

The owner is restarting both Claude Code and VS Code — backend and Metro (both background shells) will not
survive that. Nothing needs recovering from disk (all file changes already saved), but both processes need
restarting before any on-device testing can resume. **Important, per this session's own findings:** verify
no orphaned python processes are already holding port 8000 before trusting a fresh `uvicorn` start — see
the saved memory note.

```powershell
# Verify no leftover backend processes first
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Select-Object ProcessId, CommandLine

# Terminal 1 -- backend
cd backend
.venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 -- Metro
cd mobile
npx expo start --dev-client
```

Re-check `mobile/.env`'s `EXPO_PUBLIC_API_BASE_URL` still matches this computer's current LAN IP
(`ipconfig`) if the network has changed. No rebuild needed — same EAS development-client build already on
the phone.

## Next recommended steps

1. **Retest the Attention Field content redesign on the physical iPhone** — the least-verified piece of
   today's work (validated by automated layout tests only so far, not seen rendered).
2. Decide whether/when to commit — the uncommitted arc now spans two full sessions and touches
   `backend/app/`, `logan_core/`, and `mobile/`.
3. Consider writing up today's real architectural fixes (Orchestrator persistence, is_new_for_user
   separation, relaxation algorithm changes) as ADRs given their scope.
4. Fix `changed_since_view`'s hardcoded-True wiring in a future pass (separate from today's notification
   work) if the cooldown-override mechanism is meant to be functional.
5. `Saved`, `Reminders`, `Settings` remain honest "SOON" placeholders — still no backing functionality,
   unchanged this session.
