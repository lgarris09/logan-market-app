import Svg, { G, Path } from "react-native-svg";

import { theme } from "../constants/theme";

// V3.1.4.2 (brand correction pass): this used to be tracked system-font
// text with a colored "A" -- explicitly rejected by the owner ("I do not
// want a normal system font with added letter spacing and an orange A").
// STRATUS is now a dedicated vector component: a monoline geometric/
// technical-stencil alphabet (straight-line-dominant construction, matching
// the reference's aerospace/precision character -- smooth Latin-serif
// curves were deliberately avoided as harder to reproduce faithfully
// without the source vector file), built entirely from react-native-svg
// (already a dependency -- no new font or icon package). The "A" is a true
// custom glyph (an open triangle + crossbar), not a colored copy of the
// other letters' construction.
//
// Sprint 3.6 (real-device correction pass): the device screenshot showed
// this reading "too narrow / too faint / too compressed" against the
// reference's wide, confident header lockup. Two changes, both here so
// every call site inherits them: (1) `trackingRatio` default nearly doubled
// (0.22 -> 0.42) -- the reference's own typography panel calls out heavy
// tracking ("+200") on the wordmark specifically; (2) stroke weight bumped
// slightly (4.5 -> 5.5 local units) for more presence at small on-screen
// sizes without losing the thin/geometric character. The actual "too faint"
// symptom was mostly a call-site problem (the Attention Field header was
// rendering this at 13px in a muted secondary color) -- fixed at the call
// sites in app/index.tsx, not here.
//
// Honest limitation: this is a careful reproduction from visual study of
// the reference image, not a traced/pixel-exact copy of a source vector
// file (none was provided) -- expect to fine-tune proportions after seeing
// it rendered on-device.

const UNIT = 100; // glyph box height, in local (viewBox) units
const GLYPH_WIDTH = 40; // glyph box width, in local units

// Each glyph is one or more open (unfilled) stroke paths in a 0-40 x 0-100
// local box. Straight-line/right-angle construction throughout (a
// technical/stencil letterform, not a traced sans-serif) except the "A"'s
// triangular apex, which is the one place a true diagonal is the correct
// shape rather than an approximation of one.
const GLYPHS: Record<string, string[]> = {
  S: ["M32,6 L6,6 L6,50 L34,50 L34,94 L8,94"],
  T: ["M4,6 L36,6", "M20,6 L20,94"],
  R: ["M6,6 L6,94", "M6,6 L28,6 L34,14 L34,32 L28,40 L6,40", "M16,40 L36,94"],
  U: ["M6,6 L6,94 L34,94 L34,6"],
  // The custom glyph: an open triangle (no closing base stroke, matching a
  // real "A" -- the legs simply end at the baseline) plus a crossbar
  // positioned where the legs actually are at that height, not guessed.
  A: ["M20,4 L2,96", "M20,4 L38,96", "M9.4,58 L30.6,58"],
};

export function StratusWordmark({
  size = 28,
  color = theme.text,
  accentColor = theme.accent,
  trackingRatio = 0.42, // gap between glyphs, as a fraction of glyph height
}: {
  size?: number;
  color?: string;
  accentColor?: string;
  trackingRatio?: number;
}) {
  const word = "STRATUS";
  const gapUnits = UNIT * trackingRatio;
  const strokeWidthUnits = 5.5; // thin, constant relative to glyph height regardless of `size`
  const totalWidthUnits = word.length * GLYPH_WIDTH + (word.length - 1) * gapUnits;
  const scale = size / UNIT;
  const totalWidthPx = totalWidthUnits * scale;

  return (
    <Svg width={totalWidthPx} height={size} viewBox={`0 0 ${totalWidthUnits} ${UNIT}`}>
      {word.split("").map((letter, i) => {
        const isAccent = letter === "A";
        const offset = i * (GLYPH_WIDTH + gapUnits);
        return (
          <G key={`${letter}-${i}`} transform={`translate(${offset}, 0)`}>
            {(GLYPHS[letter] ?? []).map((d, pi) => (
              <Path
                key={pi}
                d={d}
                stroke={isAccent ? accentColor : color}
                strokeWidth={strokeWidthUnits}
                strokeLinecap="round"
                strokeLinejoin="round"
                fill="none"
              />
            ))}
          </G>
        );
      })}
    </Svg>
  );
}
