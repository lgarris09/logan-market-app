// STRATUS brand accent: burnt orange, hex #F47A2A (Pantone 1655C closest),
// per the approved brand reference (2026-08-07). Used sparingly, as a single
// intentional accent against black/white/graphite -- not a general-purpose
// warm color; `warning` below remains a distinct semantic color.
export const theme = {
  background: "#0A0D12",
  surface: "#11161D",
  surfaceSoft: "#171D26",
  panel: "#171D26",
  border: "#232B36",
  text: "#F5F7FA",
  textSecondary: "#9AA5B4",
  muted: "#5B6472",
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

// Shared motion timings so every entrance/press feels like the same product.
export const motion = {
  fast: 140,
  base: 220,
  slow: 380,
};
