// STRATUS brand palette. V3.1.4.2 brand-correction pass: values now match
// the owner's reference rendering's "COLOR PALETTE (STANDARDIZED)" panel
// exactly (Pure Black #0B0B0D, Graphite #151517, Jet Gray #1A1A1F, Platinum
// #F5F5F5, STRATUS Orange #F47A2A) rather than an approximation -- `border`
// moves from the prior pass's #2A2A2F to the reference's exact Jet Gray.
// `success`/`warning` remain distinct functional/semantic colors (status
// dots, not brand chrome) and are intentionally left alone here.
export const theme = {
  background: "#0B0B0D",
  surface: "#151517",
  surfaceSoft: "#1C1C1F",
  panel: "#151517",
  border: "#1A1A1F",
  text: "#F5F5F5",
  textSecondary: "#A1A1AA",
  muted: "#6B6B70",
  accent: "#F47A2A",
  accentSoft: "#2A1C10",
  success: "#4FD1A5",
  warning: "#F0B64A",
};

// A small shared scale so spacing, corner radius, and text size stay consistent
// as more screens are polished, instead of every screen picking its own numbers.
export const spacing = {
  xs: 6,
  sm: 10,
  md: 14,
  lg: 18,
  xl: 24,
  xxl: 32,
};

export const radius = {
  sm: 12,
  md: 16,
  lg: 18,
  xl: 22,
  pill: 999,
};

export const type = {
  display: 32,
  title: 24,
  heading: 18,
  body: 15,
  label: 12,
  micro: 10,
};

// Letter-spacing scale for the brand's wide-tracked aerospace/instrument
// language -- e.g. section labels like "WHAT CHANGED" and small metadata
// readouts. The wordmark itself doesn't use this scale -- it's a dedicated
// SVG component (see StratusWordmark.tsx) with its own glyph-relative
// tracking, since letter-spacing on real text can't reproduce a custom "A"
// glyph.
export const tracking = {
  label: 2.2, // section labels (WHAT CHANGED, STRATUS TAKE, ...)
  metadata: 1.4, // small instrument-style readouts -- widened (Sprint 3.6) to read as quieter/subordinate, not just smaller
  vessel: 0.3, // Attention Field vessel identity labels -- tight, not brand-level tracking
};

// Font weights for the brand's typographic hierarchy -- lighter than this
// app's earlier 700-900-heavy defaults, which read as "generic bold mobile
// app" rather than "engineered instrument." Body copy is deliberately the
// lightest/most readable.
export const weight = {
  label: "500" as const, // section labels, nav titles
  metadata: "500" as const, // small readouts -- 400 read too thin to scan at 9-10px in practice
  body: "400" as const,
};

// Sprint 3.6 (brand-fidelity pass): named font faces matching the
// reference's typography panel -- "Headings: Inter Tight / Medium, Body:
// Inter / Regular, Metadata: Inter / Medium (Wide Tracking)". Loaded via
// @expo-google-fonts in app/_layout.tsx. Two families by design (section 22
// of the Sprint 3.6 brief): Inter Tight for brand/nav/instrument text
// (headings, card headline, identity names), plain Inter for analytical
// body copy where tight spacing would hurt readability. `fontWeight` is
// deliberately omitted wherever one of these is used -- RN can't reliably
// synthesize bold on a named custom font, so the weight lives in which face
// is selected, not a numeric fontWeight alongside it.
export const font = {
  heading: "InterTight_600SemiBold", // card headline, header identity name, Ask STRATUS hero
  headingMedium: "InterTight_500Medium", // wordmark-adjacent nav titles
  body: "Inter_400Regular", // analytical paragraphs, disclaimers
  bodyMedium: "Inter_500Medium", // user message text, list items
  metadata: "Inter_500Medium", // wide-tracked instrument labels (section labels, tier pills, meta rows)
};

// Shared motion timings so every entrance/press feels like the same product.
export const motion = {
  fast: 140,
  base: 220,
  slow: 380,
};
