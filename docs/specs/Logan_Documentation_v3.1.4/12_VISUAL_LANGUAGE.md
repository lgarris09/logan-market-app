# Logan Intelligence — Visual Language
**Version:** 3.1.3
*Source: Architecture v1.3 FINAL (2026-07-31). Original: “source_material/12_VISUAL_LANGUAGE.md” (historical label).*

---

## Design System Overview

Logan's visual language is built for one purpose: making complex intelligence feel calm, clear, and beautiful. Every design decision traces back to the UI Philosophy. This document defines the specific tokens, patterns, and rules that implement that philosophy.

---

## Color

### Primary Palette

| Token | Value | Usage |
|---|---|---|
| `background.primary` | `#080B12` | Main app background — deep space black |
| `background.card` | `rgba(255,255,255,0.06)` | Glass card surfaces |
| `background.elevated` | `rgba(255,255,255,0.10)` | Elevated surfaces, modals |
| `text.primary` | `#F0F4FF` | Primary text — slightly cool white |
| `text.secondary` | `rgba(240,244,255,0.60)` | Secondary text, labels |
| `text.tertiary` | `rgba(240,244,255,0.35)` | Placeholder, disabled |
| `border.subtle` | `rgba(255,255,255,0.08)` | Card borders, dividers |
| `border.active` | `rgba(255,255,255,0.20)` | Active/focused borders |

### Accent Colors

| Token | Value | Usage |
|---|---|---|
| `accent.blue` | `#4A9EFF` | Primary actions, Logan core |
| `accent.blue.glow` | `rgba(74,158,255,0.25)` | Node glow, active states |
| `accent.gold` | `#FFB830` | High conviction, action window |
| `accent.gold.glow` | `rgba(255,184,48,0.20)` | Gold node glow |
| `accent.green` | `#34D399` | Positive outcomes, confirmation |
| `accent.red` | `#F87171` | Contradictions, warnings, risk |
| `accent.purple` | `#A78BFA` | Cross-domain intelligence |

### Domain Colors

| Domain | Color | Glow |
|---|---|---|
| Stocks | `#4A9EFF` (blue) | `rgba(74,158,255,0.20)` |
| Sports | `#F59E0B` (amber) | `rgba(245,158,11,0.20)` |
| Prediction Markets | `#A78BFA` (purple) | `rgba(167,139,250,0.20)` |
| Crypto | `#2DD4BF` (teal) | `rgba(45,212,191,0.20)` |
| Culture / Music | `#FB7185` (coral) | `rgba(251,113,133,0.20)` |
| Personal Finance | `#34D399` (green) | `rgba(52,211,153,0.20)` |
| Cross-Domain | `#FFB830` (gold) | `rgba(255,184,48,0.20)` |
| Economics | `#60A5FA` (light blue) | `rgba(96,165,250,0.20)` |

**Gap, not resolved here (ADR-037):** News is restored as an 8th domain in the `Domain` data contract, but no color token is assigned above — a color assignment is a visual-design decision and is `RESEARCH REQUIRED`, not invented as part of this documentation reconciliation pass.

### Confidence Colors

| Confidence Level | Color |
|---|---|
| Very High (≥0.80) | `#FFB830` (gold) |
| High (≥0.65) | `#4A9EFF` (blue) |
| Moderate (≥0.45) | `#60A5FA` (light blue) |
| Low (≥0.25) | `rgba(240,244,255,0.45)` (muted) |
| Speculative / Unknown | `rgba(240,244,255,0.25)` (dim) |

---

## Typography

### Font Stack
- **Primary:** SF Pro Display (iOS) / Google Sans Display (Android) / system-ui fallback
- **Monospace:** SF Mono / Roboto Mono (for scores, percentages, IDs)

### Type Scale

| Token | Size | Weight | Usage |
|---|---|---|---|
| `text.display` | 28px | 700 | Screen titles, opportunity headline |
| `text.headline` | 20px | 600 | Card headlines, section titles |
| `text.body.lg` | 16px | 400 | Primary body text |
| `text.body` | 14px | 400 | Secondary body, detail content |
| `text.label` | 12px | 500 | Labels, badges, metadata |
| `text.micro` | 10px | 500 | Disclaimers, fine print |
| `text.score` | 22px | 700 mono | Confidence scores, percentages |

### Type Rules
- Never use more than 2 weights on a single screen
- Line height: 1.5× for body text, 1.2× for headlines
- Letter spacing: -0.3px for display, 0 for body, +0.5px for labels
- Max line length: 68 characters for reading comfort
- **Headline max: 80 characters** — enforced at Presentation layer

---

## Spacing

Based on a 4px base unit.

| Token | Value | Usage |
|---|---|---|
| `space.1` | 4px | Micro gaps, icon padding |
| `space.2` | 8px | Tight spacing, inline elements |
| `space.3` | 12px | Default padding, list gaps |
| `space.4` | 16px | Card padding, section spacing |
| `space.6` | 24px | Between sections |
| `space.8` | 32px | Large section breaks |
| `space.12` | 48px | Screen-level padding |

---

## Border Radius

| Token | Value | Usage |
|---|---|---|
| `radius.sm` | 8px | Small components, badges |
| `radius_medium` | 12px | Cards, inputs |
| `radius.lg` | 20px | Modals, sheets |
| `radius.full` | 9999px | Pills, nodes, circles |

---

## Glass Effect

Glass surfaces are defined by three properties:
1. **Background fill:** semi-transparent (see color tokens above)
2. **Blur:** backdrop blur 20–40px (platform-dependent)
3. **Border:** 1px subtle border (see `border.subtle`)

```
card: {
  background: rgba(255, 255, 255, 0.06),
  backdropBlur: 24,
  border: 1px solid rgba(255, 255, 255, 0.08),
  borderRadius: 20px
}
```

Glass is used for: cards, modals, detail sheets, overlays.
Glass is NOT used for: the Opportunity Field canvas itself (that is Skia-rendered `[PROVISIONAL]`).

---

## Animation Tokens

| Token | Duration | Easing | Usage |
|---|---|---|---|
| `motion.instant` | 100ms | ease-out | Feedback, immediate responses |
| `motion.fast` | 200ms | ease-in-out | State changes, toggles |
| `motion.standard` | 350ms | ease-in-out | Most transitions |
| `motion.slow` | 600ms | ease-in-out | Card expand/collapse, screen transitions |
| `motion.ambient` | 2000–4000ms | linear | Node drift, field breathing |
| `motion.pulse` | 1200ms | ease-in-out, loop | Action Window pulse |

**Reduced-motion mode:** `motion.ambient` becomes 0ms (static), `motion.pulse` becomes static glow. All `motion.*` tokens still apply for non-ambient transitions.

---

## Opportunity Field Node Specs

| Property | Rule |
|---|---|
| Node shape | Soft circle, `radius.full` |
| Node size range | 20px (Detected) — 56px (High Conviction) |
| Node brightness | 0.3 opacity (Detected) → 1.0 opacity (High Conviction) |
| Node glow radius | 0px (Detected) → 24px (High Conviction) |
| Node glow opacity | 0 → 0.40 at High Conviction |
| **Edge glow** | Community momentum only — distinct from node glow. Present = active crowd signal. NOT a conviction indicator. |
| Pulse animation | Only Action Window — scale 1.0→1.12→1.0, 1200ms loop |
| Ambient drift | 0.5–2px per second, organic path |
| Tap target | Minimum 44×44px regardless of visual size |

**LOCKED:** Edge glow (community momentum) is always visually distinct from node brightness and node glow (conviction). No design revision may conflate the two.

---

## Icons

- **Style:** Outlined, 1.5px stroke, rounded ends
- **Size:** 16px (small), 20px (standard), 24px (large)
- **Color:** Inherits from context — never hardcoded
- **Source:** [TBD — custom icon set or licensed library]

---

## Illustrations / Empty States

- Empty Opportunity Field: Central L core only, breathing subtly. No text overlay. The emptiness communicates calm, not failure.
- Loading states: Skeleton nodes at outer ring, fading in/out. Never a spinner.
- Error states: Minimal — single line of text, no aggressive red banners.

---

## Lighting

Logan's environment has a single implied light source — slightly above and to the right.

This creates:
- Subtle top-right highlight on glass cards
- Soft bottom-left shadow
- Node glow that wraps slightly toward the light source

This is not literal — it is an impression. The goal is depth and warmth, not realism.

---

## Interaction States

| State | Visual treatment |
|---|---|
| Default | Per token definitions above |
| Hover (non-mobile) | Subtle brightness increase +10% |
| Pressed | Scale 0.96, brightness -5% |
| Focused | Accent border glow (`border.active`) |
| Disabled | 40% opacity, no interaction affordance |
| Loading | Pulse opacity 0.4→0.8, `motion.ambient` timing |

---

*Logan Intelligence Visual Language — v3.1.2 | 2026-08-03*
*v3.1.2 changes: Domain colors expanded to include Culture/Music (coral) and Personal Finance (green). Crypto (teal) and Sports (amber) color tokens corrected from v3.0. Edge glow rule added to Node Specs with LOCKED label. Headline max 80 characters added to type rules. Reduced-motion note added to Animation Tokens.*
