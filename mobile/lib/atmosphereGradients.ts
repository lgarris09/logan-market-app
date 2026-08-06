// Ring-contour density curve shared by every cloud in the atmosphere: a
// few faint rebounds in opacity rather than one smooth falloff, the way
// real condensation leaves ring artifacts where it has repeatedly
// gathered on the same spot (see LOGAN_VISUALIZATION_PHILOSOPHY_v1.0's
// Memory law). The first two stops use the highlight tint (a lightened,
// near-pastel version of the base color) so the very center reads as
// denser/clearer material, not a separate light source.
const RING_STOPS: [number, number][] = [
  [0, 0.52],
  [13, 0.4],
  [20, 0.46],
  [35, 0.24],
  [43, 0.3],
  [62, 0.13],
  [72, 0.18],
  [90, 0.04],
  [100, 0],
];

export function ringGradient(
  baseRgb: string,
  highlightRgb: string
): { colors: string[]; positions: number[] } {
  const colors = RING_STOPS.map(
    ([pos, alpha], i) => `rgba(${i <= 2 ? highlightRgb : baseRgb},${alpha})`
  );
  const positions = RING_STOPS.map(([pos]) => pos / 100);
  return { colors, positions };
}

// Mirrors the real per-entity palette in symbolResolver.ts (kept separate
// on purpose -- this file only concerns how a color becomes a cloud, not
// which entity owns which color).
export const ATMOSPHERE_PALETTE: Record<string, { base: string; highlight: string }> = {
  TSLA: { base: "240,68,68", highlight: "255,215,204" },
  NVDA: { base: "79,209,165", highlight: "210,255,240" },
  BTC: { base: "247,147,26", highlight: "255,225,190" },
  FED: { base: "74,144,217", highlight: "220,235,255" },
  MARKETS: { base: "45,212,191", highlight: "205,250,245" },
  OIL: { base: "240,182,74", highlight: "255,240,205" },
};
