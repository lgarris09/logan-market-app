# STRATUS iPhone Acceptance Test — V3.1.4

**What this is:** A walkthrough to try STRATUS on your own iPhone and tell us what actually works, what's
confusing, and what needs polish. No technical knowledge needed — just follow along and jot down what you
notice.

**Before you start:** Make sure STRATUS is installed and open, and that you can see opportunities loading
(if not, see `STRATUS_IPHONE_BUILD_INSTRUCTIONS_V3.1.4.md` first).

**How to use this document:** Go through each section in order. For each item, just note ✅ (worked fine),
❌ (didn't work / broken), or write a sentence about what happened. There's no wrong answer — the point is
to catch real problems before we polish anything.

---

## A. Installation

- [ ] The app installed on your phone without errors.
- [ ] Tapping the STRATUS icon opens the app.
- [ ] The app doesn't crash or close by itself in the first few seconds.
- [ ] You see the STRATUS name/wordmark somewhere near the top of the screen (not "Logan" or "Market
      Intelligence" or anything else).

**Notes:**

---

## B. Connection

- [ ] The app shows a loading indicator briefly after opening.
- [ ] After loading, you see a field of glowing opportunities (not a blank screen).
- [ ] It does **not** spin forever without ever showing anything.
- [ ] The opportunities that appear look like real content — headlines, not placeholder text like
      "undefined" or "null" or empty boxes.

**Notes:**

---

## C. Attention Field (the main screen)

This is the home screen — a field of soft glowing shapes, one of which is more prominent than the others.

- [ ] The glowing shapes ("vessels") are visible and distinct from each other.
- [ ] One of them is clearly more prominent/focused than the rest — it's obvious which one STRATUS thinks
      matters most right now.
- [ ] Tapping a different glow shifts focus to it smoothly (not a jarring jump).
- [ ] Tapping the same (already-focused) glow again reveals more detail about it.
- [ ] Tapping it a third time reveals even more detail (a fuller view).
- [ ] Swiping left or right moves focus to a neighboring opportunity.
- [ ] The background has a subtle atmospheric glow/texture behind everything — it should feel like ambient
      depth, not a distracting animation, and it should **never** block you from tapping or swiping.

**Notes:**

---

## D. Opportunity detail

When you tap into an opportunity to see more:

- [ ] It's clear which opportunity you're looking at.
- [ ] The information has a clear order — the headline/most important thing is easy to spot first.
- [ ] The text is legible against the background (not too dim, not overlapping).
- [ ] Any extra details (confidence level, disclaimers, etc.) are readable and don't feel like clutter.
- [ ] You can back out of the detail view (tap elsewhere, tap again, or swipe) without getting stuck.

**Notes:**

---

## E. Feedback

**Heads-up:** as of V3.1.4, tapping to focus/expand an opportunity is the only feedback action built into
this screen — there are no separate Watch, Remind, or Dismiss buttons on an opportunity yet, and none of
this is saved between app launches (close and reopen the app and it starts fresh). If you don't see those
specific buttons, that's expected — please don't spend time hunting for them.

- [ ] Tapping/expanding an opportunity feels responsive (view/engage).
- [ ] Nothing about tapping an opportunity looks broken or half-finished.

**Memory Inbox (a separate, real feature — reachable from the menu):**
- [ ] Open the menu and choose "Memory inbox."
- [ ] If anything is listed, try **Confirm** on one item — it should visibly update or disappear from the
      list.
- [ ] Try **Reject** on another item — same expectation.
- [ ] If the list is empty, that's a valid, expected state ("Nothing waiting") — not a bug.

**Notes:**

---

## F. Network failure

This section checks what happens when things go wrong — an important, easy-to-overlook part of using the
app in the real world.

1. With the app open and working, turn on **Airplane Mode** (or turn off Wi-Fi).
2. [ ] Pull to refresh, or reopen the app — you should see a clear message explaining STRATUS can't be
       reached, not a spinner that never stops.
3. [ ] There's a **Retry** (or similar) button visible.
4. Turn Wi-Fi back on.
5. [ ] Tap **Retry** — the app recovers and shows opportunities again.
6. Ask whoever set up the backend to stop it (close the terminal window running it, or press Ctrl+C).
7. [ ] Try again in the app — you should see a similar clear error, not a crash or a silent freeze.
8. Have them restart the backend.
9. [ ] Retry once more — the app should recover.

**Notes:**

---

## G. Accessibility

Even if you don't use these settings yourself, please check them — they matter for other users.

- [ ] **Reduce Motion:** In iPhone Settings → Accessibility → Motion, turn on **Reduce Motion**. Reopen
      STRATUS. The constant drifting/pulsing glow should stop or become much calmer, while everything
      should still work normally (tapping, swiping, viewing detail). Turn Reduce Motion back off afterward
      if you'd like.
- [ ] **Text size:** All the text you saw was legible at your phone's normal text size.
- [ ] **Touch targets:** Buttons and tappable areas felt big enough to hit reliably (not tiny or
      finicky).
- [ ] **VoiceOver (optional, if you're comfortable):** Turn on VoiceOver (Settings → Accessibility →
      VoiceOver) and swipe through the home screen. The menu button and opportunities should announce
      something sensible, not silence or "button" with no label.
- [ ] Nothing on screen relies **only** on color to tell you something important (e.g., no situation where
      the only way to know something matters is "it's the orange one").

**Notes:**

---

## H. Visual quality

For each of these, rate it: **BUG** (something is actually wrong), **CONFUSING** (works but unclear),
**POLISH** (works and is clear, but could look better), or **STRONG — KEEP** (this is good, don't change
it).

| Area | Rating | Notes |
|---|---|---|
| Atmosphere intensity (the background glow) | | |
| Orange accent usage (too much? too little? just right?) | | |
| Animation speed (too fast, too slow, just right) | | |
| Spacing between elements | | |
| Typography (text style/sizing) | | |
| Opportunity detail hierarchy (what draws your eye first) | | |
| Attention Field focus (is it obvious what matters most?) | | |
| Overall feel — does it feel premium/considered, or rough? | | |

**Anything else that stood out, good or bad:**

---

## I. Performance

Use the app for a few minutes — swipe around, tap into a few opportunities, leave it open for a bit.

- [ ] Any stutter or jerkiness when swiping or tapping?
- [ ] Any taps that felt delayed (you tapped, and it took a beat to respond)?
- [ ] Did the phone get noticeably warm?
- [ ] Any noticeable battery drain over a short session?
- [ ] Did the background glow (Atmosphere) specifically seem to cause any slowdown?
- [ ] Any full freezes (app stops responding)?
- [ ] Any crashes (app closes itself)? If so, what were you doing right before it happened?

**Note:** we have not been able to test real iPhone performance ourselves before this — this is the first
real signal we'll have, so please be specific if anything felt off, including which screen/action.

**Notes:**

---

## Wrap-up

Once you've gone through all of this, send back:
1. This document with your notes/checkmarks filled in.
2. Anything from Section H rated **BUG** or **CONFUSING**, roughly in order of how much it bothered you.
3. Anything rated **STRONG — KEEP** — just as useful, so we know what not to touch.

This feedback becomes the basis for the next round of polish (V3.1.4.1) — real fixes based on what you
actually saw, not guesses.
