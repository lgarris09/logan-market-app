# Logan Intelligence — UI Philosophy
**Version:** 3.1.3
*Source: Architecture v1.3 FINAL (2026-07-31). Original: “source_material/11_UI_PHILOSOPHY.md” (historical label).*

---

## The Core Idea

Most apps compete for your attention.
Logan gives you back your attention.

The interface is not a dashboard. It is not a feed. It is not a list of notifications.

It is a **living attention field** — a visual representation of what Logan currently believes deserves your focus, expressed as a spatial environment rather than a collection of UI components.

The atmosphere is calm by default. When nothing urgent deserves attention, the field is quiet. As Logan's confidence in something builds, intelligence condenses toward the center of the field — visually, organically, without forcing the user to scan through noise.

---

## The Condensation Model

The central metaphor of Logan's UI is **condensation**.

Think of Logan's intelligence like water vapor in the air. Most of the time it's invisible — present, but not demanding attention. As conditions change, moisture condenses into visible form: first a light fog at the edges, then droplets that gather toward the center of gravity.

**In Logan's UI:**
- Background signals and low-conviction items exist at the outer edges — present, but not demanding
- As conviction builds, nodes move inward and brighten
- High-conviction, time-sensitive items condense at the center — clear, focused, unavoidable
- When something resolves, it fades outward and dissolves

The user never has to sort, filter, or scan. Logan's intelligence organizes itself visually.

---

## The Opportunity Field

The Opportunity Field is Logan's primary surface. It is a spatial, radial canvas — not a list.

**Visual structure:**

```
                    outer ring
              (Detected, dim, small)

        middle ring
    (Emerging, moderate brightness)

   inner ring
(Building Conviction, bright)

  ● center cluster
(High Conviction + Action Window)
   maximum brightness, pulse
```

**Central "L" core:**
The Logan intelligence indicator sits at the center. It pulses subtly when the pipeline is actively reasoning. It is calmer when the field is in a steady state.

**Nodes:**
Each opportunity is a node. Nodes have:
- **Position** — proximity to center = importance × user value
- **Brightness** — lifecycle stage (dim = early stage, bright = high conviction)
- **Size** — scales with user value score
- **Pulse animation** — only for Action Window items (time-sensitive)
- **Edge glow** — community momentum indicator (community signal only, NOT personal relevance)
- **Color** (optional) — domain indicator (stocks, sports, predictions, cross-domain)

**Community momentum vs. personal relevance — LOCKED rule:**
Community momentum (from Community Intelligence) maps to **node edge glow only**. It must never map to brightness, proximity, or any visual property that implies personal relevance or conviction. Node brightness and proximity encode Logan's assessed quality and user value — these are distinct from crowd activity. See `02_LOGAN_INTELLIGENCE_BRAIN.md` for the full rule.

**Node tap:**
Tapping any node opens the full detail card. No navigation required. The field remains visible in the background.

**Empty field:**
When nothing deserves attention, the field is empty except for the central L core. This is correct behavior. An empty field means Logan is monitoring and nothing has risen to the surface. It is not an error. It is calm.

---

## The Attention Field as Living Intelligence

The field is not a static display. It is constantly changing as Logan's confidence evolves.

**Transitions:**
- A new node appears at the outer edge when something is first Detected
- As evidence builds, the node drifts inward over hours or days
- Contradiction or decay causes the node to dim and drift outward
- Action Window causes the node to pulse
- Resolution causes the node to slowly fade and dissolve outward

These transitions are fluid and organic — not sudden jumps. The field looks alive because it is alive. Logan's reasoning is continuous, and the field reflects it in real time.

---

## Glass, Depth, and Materiality

Logan's visual language draws from:

**Glass morphism** — translucent surfaces with subtle refraction. Intelligence feels like something you're looking *into*, not just at. The Opportunity Field has depth. Nodes feel like they exist in three-dimensional space, floating above the underlying surface.

**Depth and layering** — the field has a sense of Z-depth. Background items recede. Center items come forward. The eye naturally focuses where Logan wants it.

**Organic forms** — no hard rectangles. Nodes are soft, slightly irregular circles. The field itself breathes. Motion is fluid, not mechanical.

**Darkness as canvas** — Logan's primary palette is deep, dark backgrounds. Intelligence emerges from darkness. This is intentional — it mirrors how the brain's attention works. You notice light in darkness more than light on light.

**Subtle particles** (optional, configurable off) — very low-opacity particles drift in the field, suggesting continuous activity. They are not prominent. They are ambient texture.

---

## Motion Principles

Motion in Logan is always purposeful. It is never decorative.

**Every animation communicates something:**
- Node drifting inward = conviction building
- Node brightening = confidence increasing
- Node pulsing = time-sensitive (Action Window only)
- Node edge glow = community momentum (not conviction)
- Node fading = resolving or decaying
- Field breathing = Logan is active and reasoning
- Card expanding = you're getting more detail

**Motion rules:**
- No bounce, spring, or playful physics — Logan is an intelligence tool, not a game
- All transitions are smooth and continuous, not instant
- Duration: most transitions 300–600ms, some as slow as 2–4s for ambient drift
- Easing: ease-in-out for most transitions, linear for ambient motion
- Never interrupt the user with sudden movement — changes happen gracefully

---

## The Detail Card

When a user taps a node, a detail card expands — rising from the field rather than navigating away from it.

**Card design:**
- Glass surface with subtle border glow matching the node's color
- The field is still visible in the background (dimmed, not hidden)
- Card is dismissible with a downward swipe or tap outside
- Content is structured, not prose — scannable at a glance

**Card hierarchy (top to bottom):**
1. Headline — what this is in one line (max 80 characters)
2. Why it matters to me — personalized first, always (first rendered field, LOCKED)
3. What happened — the underlying event
4. Why now — timing context
5. How long Logan has been watching this
6. Supporting evidence — what is confirmed
7. Contradicting evidence — what argues against (shown when present, never hidden)
8. Confidence — label + score + what raises/limits it
9. Hit Quality vs. User Value — both scores visible
10. Action window — opens/closes timestamps when applicable
11. Expandable: full reasoning chain (decision trace)
12. Connected items (if any)
13. Required disclaimer (compact, at bottom)

**Correction state:**
If Logan's thesis has changed since the opportunity was first surfaced, a `correction_state` indicator appears with a `correction_note` explaining what changed and why. Logan surfaces the update — it does not silently overwrite.

---

## Negative Space as Intelligence

What Logan does NOT show is as important as what it shows.

An empty field is not a broken app. It is Logan saying: "Nothing deserves your attention right now. I'm still watching."

Notifications are not the default. Logan surfaces things when they deserve it — not on a schedule, not because an algorithm decided it was time to re-engage you.

This is what separates Logan from every app that competes for attention. Logan respects that your attention is finite and valuable. It does not waste it.

---

## Atmospheric vs. Dashboard

| Dashboard | Logan Atmosphere |
|---|---|
| Information is always present | Information condenses when it's worth it |
| User must scan and filter | Logan filters; user focuses |
| Organized by category/date | Organized by importance and conviction |
| Passive display | Living, continuous reflection of intelligence |
| Same for every user | Shaped by this user's specific model |
| Requires interaction to get value | Provides ambient awareness without demanding interaction |

---

## Node Visual Specification — Wheel and Ripple Behavior

Each node in the Opportunity Field has a precise set of visual properties that encode its intelligence state. This section defines them formally.

### Node Geometry

| Property | Encoding | Range |
|---|---|---|
| **Center distance** | Importance × User Value | 0 = center (max), 1 = outer edge |
| **Size** | User Value score | 12dp (min) → 48dp (max) |
| **Brightness** | Lifecycle stage | 0.15 (Watching) → 1.0 (Action Window) |
| **Opacity** | Confidence | 0.4 (low) → 1.0 (high) |
| **Edge glow** | Community momentum | present = community activity; absent = no crowd signal |
| **Color tint** | Domain | Stocks: blue · Sports: amber · Prediction: violet · Crypto: teal · Culture: coral · Personal Finance: green · Cross-domain: white |

**LOCKED:** Edge glow maps only to community momentum. It does NOT indicate personal relevance, conviction level, or opportunity quality. Any change to this encoding requires an explicit architectural decision.

### Pulse Animation (Action Window Only)

The pulse animation is reserved exclusively for Action Window stage items. It is the only "active" animation — all other node motion is ambient drift.

```
Pulse cycle: 2.4 seconds
  0.0s → 0.8s   scale 1.0 → 1.18  (ease-out)
  0.8s → 1.4s   scale 1.18 → 1.0  (ease-in)
  1.4s → 2.4s   hold at 1.0        (pause before next pulse)

Simultaneously:
  0.0s → 0.8s   glow radius expands 0 → 12dp (ease-out)
  0.8s → 1.4s   glow radius contracts to 0 (ease-in)
  Glow opacity: 0.6 at peak
```

### Ripple (Conviction Change Event)

When Logan's confidence in an opportunity changes significantly (stage transition, new evidence), a ripple emanates from the node to signal the update.

```
Ripple trigger: stage transition or confidence delta > 0.15
Duration: 600ms
  0ms    → 200ms  ring expands from node radius → node radius × 2.5 (ease-out)
  200ms  → 600ms  ring fades opacity 0.8 → 0.0 (linear)
  Ring width: 2dp
  Ring color: matches node color tint at full opacity
```

The ripple is a communication — it tells the user "something changed here." It does not demand interaction.

### Ambient Drift

All nodes drift continuously, independent of intelligence updates. Drift is ambient texture — it communicates that the field is alive.

```
Drift pattern: Lissajous-like, slightly randomized per node
Amplitude: 6dp–14dp (proportional to distance from center)
Period: 8s–20s (randomized per node, avoids synchronization)
Easing: sinusoidal (continuous, no start/stop)
```

Inner nodes drift less (they are in focus). Outer nodes drift more (they are in the background).

### Node Tap Response

```
Tap down:   scale 1.0 → 0.92 in 80ms (ease-in)
Hold:       hold at 0.92
Release:    scale 0.92 → 1.0 in 120ms (ease-out) → card expands
```

### Accessibility

- **Reduced-motion mode:** pulse becomes a static glow; drift becomes stationary; ripple is skipped. All intelligence is still accessible — motion is ambient, not informational.
- **High Contrast:** node colors increase saturation by 30%
- **Large Text:** labels beneath nodes scale with system text size
- **Color-independent status:** node shape or ring pattern distinguishes domain when color is unavailable. Color is never the sole encoding of status.
- **VoiceOver / TalkBack:** every node has a text label and accessible description including entity name, lifecycle stage, and headline.

---

## The Orbital Interface (Advanced / V2 Direction)

From UI explorations: the field can be extended into a three-dimensional orbital view.

Imagine the Opportunity Field tilted slightly away from you — like looking down into a holographic table. The intelligence nodes orbit the central core at different distances and elevations. High-conviction items orbit at the closest, brightest radius. Distant items orbit at the outer rings.

This reinforces the depth metaphor: some intelligence is close and actionable; some is monitoring from a distance.

**V1:** 2D spatial field with depth illusion via Skia rendering `[PROVISIONAL]`
**V2:** Full 3D orbital view with tilt, rotation, and depth-based occlusion

---

## Platform Considerations

**iOS:** The UI feels native-premium. Uses system blur where appropriate. Respects Dynamic Island and safe areas. No gimmicks — every visual choice is intentional.

**Android:** Adapts to Material You color extraction where available. Same depth and glass language. Performance first — no visual effect is worth a dropped frame.

**Frame rate target:** 60fps for all animations. 120fps on ProMotion devices. If an effect can't hit 60fps, the effect is removed.

---

## What the UI Must Never Do

- Never show a list as the primary interface
- Never compete with Logan's own content for attention (no banners, badges, dots everywhere)
- Never show raw data (prices, odds) without context — Logan provides meaning, not just numbers
- Never surface a notification unless something genuinely deserves attention
- Never feel like a dashboard someone skinned to look different
- Never sacrifice performance for visual effect
- Never use community momentum (edge glow) to imply personal relevance or conviction — LOCKED

---

*Logan Intelligence UI Philosophy — v3.1.2 | 2026-08-03*
*v3.1.2 changes: Community momentum / personal relevance visual separation rule added and marked LOCKED. Edge glow encoding formalized. Culture and Personal Finance color tints added to node geometry table. Card hierarchy updated: 80-char headline, why_it_matters_to_me first, supporting_evidence, contradicting_evidence, action window timestamps, correction_state. Accessibility section expanded with color-independent status and VoiceOver/TalkBack requirements. Ambient drift defined as non-informational (reduced-motion safe).*
