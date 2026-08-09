# Session note — 2026-08-07 to 2026-08-08 — STRATUS iPhone device validation, Sprint 3.5 bug fixes, V3.1.4.2 brand polish

Covers getting a real EAS development-client build running on the owner's iPhone for the first time, then
three escalating rounds of real-device bug fixing and visual polish driven directly by the owner's own
screenshots — from "the field is unusable" through "make it feel like the STRATUS brand." One continuous
working thread across two calendar days.

## What was completed

### 1. iPhone build setup and device connectivity
- Confirmed and installed the `eas build --profile development --platform ios` result (already triggered
  before this session) on the owner's iPhone; walked through enabling iOS **Developer Mode** and trusting
  the profile.
- Diagnosed and fixed the phone-to-Metro connection: the Wi-Fi network was categorized **Public** in
  Windows (blocking inbound connections by default), and a Group Policy prevented recategorizing it
  (later confirmed unrelated to the corporate VPN the owner uses only on their phone). Fixed by adding
  scoped Windows Firewall inbound-allow rules for ports 8000 (backend) and 8081 (Metro) instead, run by
  the owner in an elevated PowerShell session.
- Backend (`uvicorn`) and Metro (`expo start --dev-client`) both left running in the background for the
  remainder of the session.

### 2. Sprint 3.5 device-validation bug fixes (V3.1.4.1, round 1)
Investigated first, reported findings, got explicit approval, then implemented:
- **Vessel taps did nothing on real device.** Root cause: the width/height/borderRadius "grow into a
  card" animation ran on the classic `Animated` API with `useNativeDriver:false` (JS thread), contending
  with several other concurrent per-vessel animations plus the live Skia atmosphere canvas — state
  updated but the visible growth never happened. Migrated `Vessel.tsx`'s entire animation system to
  Reanimated.
- Hardened the field's `PanResponder` (`onShouldBlockNativeResponder:false`, explicit
  `onStartShouldSetPanResponder:false`) — a known iOS failure mode where a `PanResponder` wrapping
  `Pressable` children can suppress their native touch handling.
- Set `pointerEvents="none"` directly on the Skia `<Canvas>`, not just its wrapping `View` (iOS/New
  Architecture gap).
- Fixed vessel clustering: replaced unconstrained random angle placement with sector-based placement
  (guaranteed minimum angular separation) plus a relaxation pass, sized relative to the real measured
  field, not a fixed reference canvas.
- Added persistent resting-state identity labels (ticker/name/confidence tier) — the field previously
  showed anonymous glowing dots.
- Simplified disclosure from a two-tap (dormant→glance→detail) to a one-tap (dormant→full card) model.
- Diagnosed and fixed the **Ask STRATUS** "does nothing" bug: it used a raw `fetch()` with no timeout,
  bypassing `lib/apiClient.ts`'s `fetchJson()` (built specifically to prevent this) — on real network
  conditions it could hang indefinitely with zero feedback. Migrated to `fetchJson`.
- Replaced the flat, legacy-heavy hamburger menu with a consumer-first structure (Home, Saved/Reminders/
  Settings as honest "SOON" placeholders — never fake functionality, Ask STRATUS, About STRATUS) and a
  single `__DEV__`-gated Developer/Diagnostics section.

### 3. Round 2 (real-device screenshots)
- **Opportunity Card could render off-screen.** Fixed by computing a per-vessel safe on-screen center in
  `AttentionField.tsx` (clamped to the real field bounds with margin) and animating the card to it as it
  grows — the glow/label stay at the vessel's natural position; only the card "detaches" when needed. Card
  height also now clamps to available space, falling back to an internal `ScrollView` if content would
  overflow.
- Card readability: raised blur intensity, added a solid dark scrim under the blur, added a colored focus
  border, strongly dimmed the rest of the field and dampened the Atmosphere canvas while a card is open.
- Field crowding: introduced label **tiers** (only the top few vessels get a descriptor line; the rest get
  identity+tier only) and rewrote the collision/relaxation math to account for each vessel's full
  occupied rectangle (glow **and** label footprint), not just the glow circle.
- Ask STRATUS keyboard bug: the screen relied on a native Stack header whose height
  `KeyboardAvoidingView` couldn't measure. Converted to `headerShown:false` + its own header/SafeAreaView,
  and rebuilt as a real scrolling conversation (message list) instead of a single replaced-in-place answer.
- Collapsed the inline Developer/Diagnostics content (API status + 5 legacy screens) into one dedicated
  `app/dev-diagnostics.tsx` screen, reachable via a single drawer row.

### 4. V3.1.4.2 — brand alignment (first pass)
- Shifted the color palette from blue-tinted dark to a neutral graphite-black family per the STRATUS
  apparel/logo reference; added a `StratusWordmark` component (wide-tracked, orange "A") used across
  every screen header.
- Restructured the Opportunity Card's content into **STRATUS TAKE / WHY IT MATTERS NOW / WHAT CHANGED**,
  mapped to real contract fields (`why_it_matters_to_me`, `why_now`, `what_happened`), plus a related-
  signals/last-updated metadata row.
- Investigated the actual `logan_core` pipeline (not just the mobile type) to confirm what the requested
  **WATCH FOR** section and a punchier headline would need — see "Known issues" below.
- Widened the size contrast between high- and low-priority vessels; fixed a bug where low-priority
  vessels' *visual* glow was silently forced up to the accessibility touch-target minimum.

### 5. V3.1.4.2 — final brand + interface polish (second pass)
- **Fixed a real label-centering bug**: the resting-state label relied on the parent's
  `alignItems:"center"` to center an absolutely-positioned child with no explicit `left` — unreliable in
  RN/Yoga for `position:"absolute"`. Added explicit `left:"50%"`.
- **Fixed a real edge-containment bug**: the field's clamp used one fixed fraction range regardless of a
  vessel's actual size or label height. Rewrote to clamp per-vessel, in real pixels, against each
  vessel's true occupied rectangle, re-clamping after every relaxation push.
- **Standardized the field's color system**: rewrote `symbolResolver.ts` from a wide per-entity rainbow
  (+hash fallback) to a small category-driven palette (muted teal-green for market categories, muted gold
  for crypto, muted violet for culture/trends, neutral graphite for everything else) — brand orange is
  never used for entity glow color, reserved for STRATUS chrome.
- Added a shared typography `weight`/`tracking` scale and applied it across every screen, replacing most
  remaining 700–900 font weights.
- Redesigned Ask STRATUS's first-run state (a `HorizonMark` SVG mark, headline, 3 tappable starter
  prompts) and restyled assistant responses as bordered "intelligence panels" instead of chat bubbles,
  without changing the underlying (already-fixed) request/keyboard logic.
- Refined the menu toward a "premium command drawer" feel (more spacing, quieter labels, smaller badges).

### 6. Brand & Interface Correction Pass (owner supplied an exact reference rendering)
The owner provided a detailed reference image (wordmark, small horizon mark, exact hex palette, field/
card/menu screens) and asked for a correction pass against it specifically, not further approximation:
- **Rebuilt the STRATUS wordmark as a dedicated SVG component** (`components/StratusWordmark.tsx`) — a
  monoline geometric/technical-stencil letterform alphabet (straight-line construction), with the **"A" as
  a true custom glyph** (open triangle + crossbar, not a colored copy of the other letters). Explicitly
  *not* pixel-traced from a vector source (none was provided) — flagged to the owner as a best-effort
  visual reproduction needing on-device verification.
- **Rebuilt the horizon mark** (`components/HorizonMark.tsx`) — removed a dot/sun that had crept in and
  replaced a circular semicircle with a genuinely shallow, wide elliptical arc, matching the small mark
  shown above "Powered by LGI" in the reference (not the larger illustrative sunrise version). Used
  consistently in the menu footer and Ask STRATUS's first-run state.
- **Corrected the color taxonomy** to match the reference exactly (previous round's palette was an
  invented approximation): Markets = muted green `#22C55E` (stocks/markets/commodities/technology/
  **crypto** — the reference groups BTC under "Markets," not a separate hue), Odds = muted red `#EF4444`
  (sports/prediction-markets), Trends = muted violet `#A78BFA` (culture), neutral graphite otherwise.
  Updated `theme.border` to the reference's exact Jet Gray (`#1A1A1F`, was `#2A2A2F`). Goal: the
  AttentionField reads as "one STRATUS system," per this pass's explicit ask.
- Dropped the vessel descriptor line entirely (the reference shows zero descriptor text on any vessel,
  including the most prominent one) — removed `shortDescriptor()` and its tests as dead code.
- **Fixed the Ask STRATUS consumer-language leak** — `backend/app/main.py`'s `ask_logan()` was returning
  strings containing "confirmed memory," "V1," "category-linked memories." This is the **one backend touch
  this entire arc** (everything else stayed mobile-only); scoped deliberately narrow (wording only, same
  branching logic, same response shape) and flagged explicitly since `backend/app/` is otherwise treated as
  hands-off per this repo's CLAUDE.md.
- Shrank the Ask STRATUS send button (46px→36px) and slimmed starter-prompt rows; menu SOON/DEV badges
  reduced to ~65% opacity and DEV detuned from orange to graphite.
- The owner has **not yet seen this round rendered on-device** — this is the most speculative round
  visually (the custom wordmark/mark especially) and the most likely to need a follow-up iteration.

## Files created or modified

**Mobile — new files:** `app/about.tsx`, `app/dev-diagnostics.tsx`, `components/ConfidenceRing.tsx`,
`components/HorizonMark.tsx`, `components/StratusWordmark.tsx`, `lib/relativeTime.ts`,
`lib/__tests__/attentionLayout.test.ts`, `lib/__tests__/relativeTime.test.ts`,
`lib/__tests__/symbolResolver.test.ts`.

**Mobile — modified:** `app/_layout.tsx`, `app/ask.tsx` (rewritten), `app/index.tsx` (menu rewritten),
`components/AttentionField.tsx`, `components/EntitySymbol.tsx`, `components/Vessel.tsx` (animation system
migrated + content restructured), `components/atmosphere/AttentionAtmosphere.tsx`,
`components/atmosphere/__tests__/AttentionAtmosphere.test.tsx`, `constants/theme.ts`, `eslint.config.js`
(comment accuracy only), `hooks/useReducedMotion.ts` (comment accuracy only), `lib/attentionLayout.ts`
(rewritten), `lib/symbolResolver.ts` (rewritten).

**Backend:** `backend/app/main.py` — `ask_logan()` response copy only (see round 6 above). The only backend
file touched this entire session; everything else was mobile-only.

**Windows host machine:** two scoped inbound firewall rules added (ports 8000/8081, run by the owner).

## What was verified

- `npx tsc --noEmit`, `eslint .`, `prettier --check` (then `--write`, whitespace-only fixes), and `jest`
  all run clean after every round; final state as of the last round: **37/37 tests passing**, 0 typecheck
  errors, 0 lint issues. (Test count dropped from 38 to 37 net of this session: added `symbolResolver`
  taxonomy tests, removed `shortDescriptor` tests when that function was deleted as dead code.)
- Regression tests added for: layout separation/collision (including the AABB label-footprint check and
  the edge-containment guarantee), `relativeTimeFrom`, and `symbolResolver`'s category-driven color logic
  (including an explicit assertion that brand orange is never returned for an entity glow, and that the
  taxonomy matches the reference's Markets/Odds/Trends grouping exactly).
- **Not verified by this session directly**: no live device retest was performed by the assistant for any
  of rounds 2 through 6 (the owner tests on their own iPhone and reports back with screenshots — this is
  the established working pattern for this thread, not an oversight). **The owner has not yet retested
  round 6 (the wordmark/horizon-mark/color-taxonomy correction pass) on-device as of this note** — that is
  the very next thing to do next session, before anything else.

## Backend / `logan_core` findings (read-only investigation, no code changed)

While scoping the "make card copy compelling" and "add a WATCH FOR section" requests, traced the actual
`/v1/opportunities` pipeline (confirmed to live in `logan_core/`, not `backend/app/`, which is a thin
adapter):
- `headline` is a simple string template (`f"{entity}: {signal_type} ({value})"` in
  `logan_core/world_model/model.py`), not natural-language generation — e.g. `"NVIDIA: earnings signal
  (NVIDIA data-center demand guidance raised)"`. This is why card headlines read like event-log entries;
  fixing it needs a `logan_core` Presentation-engine content change, not mobile styling.
- `strengthening_signals`, `invalidating_signals`, `raising_factors`, `limiting_factors`, `lifecycle_stage`,
  and `trending_indicator` are documented in `docs/specs/Logan_Documentation_v3.1.4/07_DATA_CONTRACTS.md`
  but **do not exist on the actual `DeliveredItem` class** in `logan_core/contracts/presentation.py` — a
  real spec/implementation gap, not just a mobile-type omission. This is why the requested "WATCH FOR"
  card section and a "time sensitivity" metadata field were omitted rather than faked.
- The closest existing hook for WATCH FOR: `ConclusionConfidence.limiting_factors` is populated internally
  with real reasoning text (e.g. *"Only one independent source has corroborated this so far."*) but is
  never copied into `DeliveredItem` by `PresentationEngine.deliver()`.

## Known issues / open items carried forward

- **Nothing from this entire two-day arc has been committed.** `git status` shows 22 changed/new files in
  `mobile/`, all uncommitted, following the same pattern flagged in earlier session notes.
- The owner has not yet retested the final V3.1.4.2 round (label centering, edge containment, color
  system, typography, Ask STRATUS redesign) on-device — everything above is static-check-verified, not
  device-confirmed for that round.
- Several decisions made this session look ADR-worthy but haven't been formalized in `docs/DECISIONS.md`
  (next number would be **ADR-042**): migrating `Vessel.tsx`/`AttentionField.tsx` off the classic
  `Animated` API onto Reanimated; the card-"detaches"-from-the-vessel's-field-position interaction pattern
  for viewport safety; the category-driven (not per-entity) color system replacing the earlier rainbow
  palette described in `symbolResolver.ts`'s original design comment.
- Headline content quality and the WATCH FOR section remain blocked on `logan_core` Presentation-engine
  work (see above) — explicitly out of scope for this presentation-only arc, not forgotten.
- `Saved`, `Reminders`, and `Settings` remain honest "SOON" placeholders in the menu — no backing
  functionality exists yet.
- Inter typeface (named in the brand reference) was deliberately not added — would be a new dependency;
  tracking/weight/spacing on the existing system font was used instead per explicit instruction.
- Voice/mic input on Ask STRATUS was deliberately not added despite appearing in the reference mockup —
  not implemented anywhere in the app, and a non-functional icon would be exactly the kind of fake
  affordance this project's rules forbid.
- All carried-forward infrastructure risks from prior session notes (no `logan_core` installable
  packaging, no auth/production hosting, CORS wide open, ADR-006 database/hosting still open) stand
  unchanged — untouched this session.

## How to resume next session

The session paused for the night with the computer about to restart (owner heading to dinner,
2026-08-08). Backend and Metro were both running in this session's background shells, which do not
survive a restart or closing VS Code. Nothing needs recovering — all file changes are already on disk,
untouched by a restart — but both processes need restarting before any on-device testing can resume:

```powershell
# Terminal 1 -- backend
cd backend
.venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 -- Metro
cd mobile
npx expo start --dev-client
```

Re-check `mobile/.env`'s `EXPO_PUBLIC_API_BASE_URL` still matches this computer's current LAN IP
(`ipconfig`) if the network has changed since — it drifts on Wi-Fi reconnect. No rebuild needed; this is
the same EAS development-client build already installed on the phone. **First thing to do once both are
up: retest round 6** (the brand/wordmark correction pass below) — it hasn't been seen on-device at all yet.

## Next recommended steps

1. **Owner retests round 6 first** (wordmark, horizon mark, color taxonomy, Ask STRATUS consumer-language
   fix, menu badge treatment) — this is the least-verified round of the whole session. Report back
   specifics on the wordmark especially (letter proportions, the "A," spacing, weight) so it can be
   iterated precisely rather than re-guessed.
2. Decide whether/when to commit — the working tree has been growing uncommitted across multiple sessions
   now; this is the largest uncommitted arc yet (22+ files, now including one backend file).
3. If the Reanimated migration, card-detach pattern, and category-color-system decisions are being kept,
   write them up as ADR-042 (or split into multiple ADRs) rather than leaving them undocumented.
4. Scope a `logan_core` follow-up for headline content generation quality and wiring
   `ConclusionConfidence.limiting_factors` into `DeliveredItem` to enable a real WATCH FOR section —
   both are concrete, well-scoped, and independent of this mobile-presentation arc.
5. Real Saved/Reminders/Settings functionality is presumably a future sprint (persistence, out of scope
   for the device-polish work completed so far).
