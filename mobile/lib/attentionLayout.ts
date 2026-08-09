// Layout math for the Attention Field.
//
// There is no longer a special "focused subject" position and a separate
// "background" scatter -- every entity is a vessel in the same medium, at a
// stable position determined by priority alone. Focus is an interaction
// state layered on top (which vessel is allowed to grow and speak), not a
// different place in space. Nothing here decides text rendering or engaged-
// state sizing -- Vessel.tsx owns that; this file answers "where does this
// entity's nucleation point sit, what are its stable rhythm phases, and how
// much resting-state label (if any) should the field reserve room for."

import { FeedItem } from "../types/loganFeed";

// V3.1.4.1 round 2 (real-device screenshot review): dormant labels showing a
// full identity + headline preview on every vessel were the dominant source
// of visual crowding, and the layout's collision math only accounted for
// glow-circle size, never label footprint -- so labels overlapped even where
// glows didn't. Two changes here: (1) only the highest-priority vessels get
// a persistent label at all, in two shrinking tiers, so information density
// scales with actual priority instead of every vessel competing equally; (2)
// the relaxation pass now separates vessels by their real occupied
// rectangle (glow + label, label hanging below per Vessel.tsx's layout), not
// just glow diameter.
export type LabelTier = "full" | "compact" | "none";

export type VesselLayout = {
  eventId: string;
  x: number; // 0..1 fraction of field width -- stable regardless of focus
  y: number; // 0..1 fraction of field height
  size: number; // px diameter of the resting (dormant) glow
  // 0..1, derived from this item's rank position among the current items
  // (1.0 = rank 1 / most important). Public API responses never expose a raw
  // ranking score (ADR-029) -- this is the correct, already-normalized value
  // for any visual "how prominent should this feel" calculation. Vessel.tsx
  // should read this instead of deriving anything from a score field.
  prominence: number;
  // How much persistent resting-state identity this vessel has earned by
  // rank, not a per-vessel visual choice -- see FULL_LABEL_COUNT/
  // COMPACT_LABEL_COUNT below. Vessel.tsx renders strictly less content as
  // this narrows; it never invents its own threshold.
  labelTier: LabelTier;
  driftPhase: number; // 0..2π, stable per entity
  driftFreq: number; // ~0.6..1.1
  breathPhase: number; // 0..2π -- confidence-driven flicker cycle
  breathFreq: number; // ~0.5..0.9
  pulsePhase: number; // 0..2π -- priority-driven prominence cycle
  pulseFreq: number; // ~0.18..0.3, slower than breathing
};

function hashString(value: string): number {
  let hash = 0;
  for (let i = 0; i < value.length; i++) {
    hash = (hash * 31 + value.charCodeAt(i)) >>> 0;
  }
  return hash;
}

function stableRandom(seed: string): number {
  return (hashString(seed) % 10000) / 10000;
}

/** Items ranked by priority -- the order focus moves through on a swipe. */
export function rankedByPriority(items: FeedItem[]): FeedItem[] {
  return [...items].sort((a, b) => a.rank - b.rank);
}

/** The item that should be in focus by default: whatever matters most right now. */
export function defaultFocus(items: FeedItem[]): FeedItem | null {
  return rankedByPriority(items)[0] ?? null;
}

/** The next (or previous) item to bring into focus, wrapping around the ranked order. */
export function shiftFocus(
  items: FeedItem[],
  currentId: string,
  direction: 1 | -1
): FeedItem | null {
  const ranked = rankedByPriority(items);
  if (ranked.length === 0) return null;
  const idx = ranked.findIndex((i) => i.event_id === currentId);
  if (idx === -1) return ranked[0];
  const nextIdx = (idx + direction + ranked.length) % ranked.length;
  return ranked[nextIdx];
}

// All fractions below are relative to the field's shorter dimension (its
// width on a portrait phone), so the field composes the same way on an
// iPhone SE, a Pro Max, or an iPad -- V3.1.4.1 fixed these as raw pixel
// constants tuned against a wide reference canvas, which is what produced
// visible clustering/overlap on real iPhone dimensions (Sprint 3.5 device
// validation finding).
// Widened 0.17 -> 0.22 (Sprint 3.6 Field Bias content pass): the two
// largest, highest-priority vessels (both near SIZE_MAX_FRACTION) sit in
// this innermost band together -- with the taller three-line labels, they
// no longer had enough circumferential room there to avoid overlapping.
// Doesn't touch SIZE_MAX_FRACTION's deliberate prominence-contrast tuning,
// just gives the same-size vessels more room at the radius they already
// occupy.
const RADIUS_MIN_FRACTION = 0.22; // highest-priority items rest nearest the center, but not on top of it
const RADIUS_MAX_FRACTION = 0.42;
// V3.1.4.2 (brand-alignment pass): widened from 0.12/0.32 -- "don't make
// every vessel equally prominent" -- so the strongest opportunities are
// unmistakably larger than quiet ones. Vessel.tsx no longer forces the
// visual glow size up to the accessibility touch-target minimum (it pads
// the tappable *hit area* via hitSlop instead), so this range now actually
// reaches the screen rather than being silently clamped for low-priority
// items.
const SIZE_MIN_FRACTION = 0.1;
const SIZE_MAX_FRACTION = 0.34;
// Minimum breathing room between two vessels' occupied rectangles, so
// neighbors never visually fuse into one blob even after relaxation.
// Was widened 0.03 -> 0.045 in the earlier real-device correction pass;
// narrowed back down for the Field Bias content pass -- the much larger
// three-line label footprints now provide real separation on their own, and
// keeping 0.045 on top of that over-constrained the layout at typical demo
// vessel counts (9-11 labeled vessels genuinely could not all satisfy
// non-overlap within the existing radius band -- more relaxation passes
// didn't help because the system was geometrically over-constrained, not
// under-iterated).
const MIN_GAP_FRACTION = 0.025;
// Bumped 6 -> 14 (Sprint 3.6 Field Bias content pass): label footprints
// roughly doubled in both dimensions (three lines of real content instead
// of two), so a typical demo-sized field (9-11 labeled vessels) needs more
// iterations to fully resolve every pairwise overlap, not just the largest
// ones. Cheap either way -- this runs once per layout computation, not
// per frame.
const RELAXATION_PASSES = 16;

// How many of the highest-priority vessels get a label at rest. Reversed
// again from the V3.1.4.2 brand-correction pass's "zero descriptor text"
// rule: the owner's newer Field Bias reference explicitly shows every
// vessel with a name, a real confidence percentage, and a short real-data
// reason tag (signal_type) -- see Vessel.tsx's rest-label JSX. Full and
// compact tiers render the same three-line content, just smaller/quieter
// at compact (the same "prominence via size, not content" pattern as
// before, just with richer content at both tiers now). The tier distinction
// is kept for the "none" cutoff at feed sizes well beyond what's been
// designed for. These are label *footprint* allowances for the collision
// math -- Vessel.tsx's own styling must stay within them or the two will
// drift apart. Both tiers share one container width (Vessel.tsx's
// restLabel style is untiered) -- only height differs, since compact's
// smaller text still needs the same horizontal room for long real names
// ("Federal Reserve") and descriptors ("VOLATILITY SPIKE").
const FULL_LABEL_COUNT = 3;
const COMPACT_LABEL_COUNT = 24;
// Trimmed from an initial 132/56/46 estimate: those genuinely didn't fit
// the highest-priority vessels' inner radius band at typical demo vessel
// counts (9-11) -- two max-size glows there are already tightly packed by
// RADIUS_MIN_FRACTION/SIZE_MAX_FRACTION alone, before labels enter into it.
const LABEL_WIDTH = 118; // name + percentage + descriptor, both tiers
const FULL_LABEL_HEIGHT = 47; // name + large percentage + descriptor lines
const COMPACT_LABEL_HEIGHT = 40; // same three lines, smaller text

function labelTierFor(index: number, n: number): LabelTier {
  if (index < Math.min(FULL_LABEL_COUNT, n)) return "full";
  if (index < Math.min(COMPACT_LABEL_COUNT, n)) return "compact";
  return "none";
}

function labelFootprint(tier: LabelTier): { width: number; height: number } {
  if (tier === "full") return { width: LABEL_WIDTH, height: FULL_LABEL_HEIGHT };
  if (tier === "compact") return { width: LABEL_WIDTH, height: COMPACT_LABEL_HEIGHT };
  return { width: 0, height: 0 };
}

type ScatterPoint = {
  eventId: string;
  // Working position in real px (not the [0,1] fraction) -- V3.1.4.2 (real-
  // device screenshot review): the old clamp used a single fixed fraction
  // range (8-92% / 14-88%) regardless of a vessel's actual size or label
  // footprint, so a large glow or a full-tier label could still extend past
  // the true screen edge. Clamping now happens in px, per vessel, against
  // its own real occupied rectangle.
  xPx: number;
  yPx: number;
  size: number;
  prominence: number;
  labelTier: LabelTier;
  // Half-width and the (asymmetric -- label hangs below, not above) top/
  // bottom extents of this vessel's real occupied rectangle, in px.
  halfW: number;
  topH: number;
  bottomH: number;
};

// Minimum breathing room from the true screen edge, on top of each vessel's
// own glow/label footprint.
const EDGE_PADDING = 12;

/** Clamps a vessel's center so its full occupied rectangle (glow radius on
 * top, glow radius + label height on the bottom, half-width on each side --
 * whichever of the glow or the label is wider) stays within the real field
 * bounds, with a small edge margin. Falls back to centering on that axis if
 * the vessel is too large to fit with margin at all (a degenerate field
 * size), rather than producing an inverted range. */
function clampToField(
  xPx: number,
  yPx: number,
  halfW: number,
  topH: number,
  bottomH: number,
  width: number,
  height: number
): { x: number; y: number } {
  const minX = halfW + EDGE_PADDING;
  const maxX = width - halfW - EDGE_PADDING;
  const minY = topH + EDGE_PADDING;
  const maxY = height - bottomH - EDGE_PADDING;
  return {
    x: minX <= maxX ? Math.min(Math.max(xPx, minX), maxX) : width / 2,
    y: minY <= maxY ? Math.min(Math.max(yPx, minY), maxY) : height / 2,
  };
}

/**
 * One stable position + one set of rhythm phases per item, for the whole
 * session -- nothing here changes when focus moves. Priority alone decides
 * distance from center and resting size; there is no separate "orbit" for a
 * focused item because nothing here treats focus as spatial.
 *
 * `width`/`height` are the real, measured field dimensions in px. Passing
 * the actual on-screen size (rather than assuming a fixed canvas) is what
 * lets this scale correctly across device sizes, and lets the relaxation
 * pass below reason about real pixel overlap, not just fractional radius.
 */
export function computeAtmosphereLayout(
  items: FeedItem[],
  width: number,
  height: number
): Map<string, VesselLayout> {
  const result = new Map<string, VesselLayout>();
  if (items.length === 0 || width <= 0 || height <= 0) return result;

  const minDim = Math.min(width, height);
  const sizeMin = SIZE_MIN_FRACTION * minDim;
  const sizeMax = SIZE_MAX_FRACTION * minDim;

  // Normalize by rank position, not a raw score (ADR-029 -- the backend
  // never sends one). Rank 1 (best) -> t=1; the lowest-ranked item -> t=0.
  const ranked = rankedByPriority(items);
  const maxRank = Math.max(...items.map((item) => item.rank));
  const rankRange = maxRank - 1 || 1;
  const n = ranked.length;
  const sector = (Math.PI * 2) / n;
  // One stable rotation for the whole ring, seeded off the current item set,
  // so the arrangement doesn't always start with rank 1 due north.
  const rotation = stableRandom(ranked.map((item) => item.event_id).join("|")) * Math.PI * 2;

  const points: ScatterPoint[] = ranked.map((item, index) => {
    const t = 1 - (item.rank - 1) / rankRange;
    const radiusFraction = RADIUS_MAX_FRACTION - t * (RADIUS_MAX_FRACTION - RADIUS_MIN_FRACTION);
    const size = sizeMin + t * (sizeMax - sizeMin);
    const tier = labelTierFor(index, n);
    const label = labelFootprint(tier);

    // Each item gets its own even sector of the circle (guaranteeing a
    // minimum angular gap up front) plus a stable jitter within that sector
    // so the field still reads as organic scatter, not a mechanical wheel.
    const jitter = (stableRandom(`${item.event_id}:angle`) - 0.5) * sector * 0.6;
    const angle = index * sector + jitter + rotation;

    // Flattened vertically so the scatter reads as a loose horizon rather
    // than a perfect ring.
    const xFrac = 0.5 + radiusFraction * Math.cos(angle);
    const yFrac = 0.5 + radiusFraction * Math.sin(angle) * 0.82;

    const halfW = Math.max(size, label.width) / 2;
    const topH = size / 2;
    const bottomH = size / 2 + label.height;
    const clamped = clampToField(
      xFrac * width,
      yFrac * height,
      halfW,
      topH,
      bottomH,
      width,
      height
    );

    return {
      eventId: item.event_id,
      xPx: clamped.x,
      yPx: clamped.y,
      size,
      prominence: t,
      labelTier: tier,
      halfW,
      topH,
      bottomH,
    };
  });

  // Relaxation pass: separate every pair of vessels by their real occupied
  // rectangle (glow + label footprint, asymmetric since the label hangs
  // below the glow, never above it) rather than just glow diameter -- this
  // is what V3.1.4.1 round 1 got wrong (labels overlapped even when glows
  // didn't, because only glow size fed the old circular distance check). A
  // standard 2D AABB minimum-translation push, resolving along whichever
  // axis has the smaller overlap so a pair doesn't over-correct.
  const minGapPx = MIN_GAP_FRACTION * minDim;

  // Moves `p` by (dx,dy) then clamps to field bounds, returning how much of
  // the intended movement actually happened (1 = full movement, less than 1
  // if a field edge cut it short). Sprint 3.6 content pass finding: with
  // the much taller three-line labels, a vessel near a field edge could get
  // clamped mid-push, silently absorbing less than its half of the required
  // separation -- its partner never learns the shortfall exists, and the
  // pair settles for a real, visible overlap. Reported back so the caller
  // can give the difference to the *other* vessel instead.
  function moveAndClamp(p: ScatterPoint, dx: number, dy: number): number {
    const intended = Math.hypot(dx, dy);
    if (intended < 1e-6) return 1;
    const clamped = clampToField(p.xPx + dx, p.yPx + dy, p.halfW, p.topH, p.bottomH, width, height);
    const achieved = Math.hypot(clamped.x - p.xPx, clamped.y - p.yPx);
    p.xPx = clamped.x;
    p.yPx = clamped.y;
    return achieved / intended;
  }

  for (let pass = 0; pass < RELAXATION_PASSES; pass++) {
    for (let i = 0; i < points.length; i++) {
      for (let j = i + 1; j < points.length; j++) {
        const a = points[i];
        const b = points[j];
        const ax = a.xPx;
        const ay = a.yPx;
        const bx = b.xPx;
        const by = b.yPx;

        const overlapX = a.halfW + b.halfW + minGapPx - Math.abs(bx - ax);

        // The Y case is asymmetric (a vessel's label only hangs below it,
        // never above), so "overlap" depends on which vessel is above the
        // other -- the gap between them is (lower vessel's top) minus
        // (upper vessel's bottom), regardless of which is a/b.
        const aAboveB = ay <= by;
        const verticalGap = aAboveB
          ? by - ay - (a.bottomH + b.topH)
          : ay - by - (b.bottomH + a.topH);
        const yOverlap = minGapPx - verticalGap;

        if (overlapX > 0 && yOverlap > 0) {
          if (overlapX < yOverlap) {
            const dir = Math.sign(bx - ax) || 1;
            const push = overlapX / 2;
            const aFrac = moveAndClamp(a, -dir * push, 0);
            const bFrac = moveAndClamp(b, dir * push, 0);
            if (aFrac < 1) moveAndClamp(b, dir * push * (1 - aFrac), 0);
            if (bFrac < 1) moveAndClamp(a, -dir * push * (1 - bFrac), 0);
          } else {
            const dir = aAboveB ? 1 : -1;
            const push = yOverlap / 2;
            const aFrac = moveAndClamp(a, 0, -dir * push);
            const bFrac = moveAndClamp(b, 0, dir * push);
            if (aFrac < 1) moveAndClamp(b, 0, dir * push * (1 - aFrac));
            if (bFrac < 1) moveAndClamp(a, 0, -dir * push * (1 - bFrac));
          }
        }

        // Independent of the label-rectangle push above: the glow circles
        // themselves must never overlap either, even when their (much
        // taller, asymmetric) label rectangles already don't. Sprint 3.6
        // content pass finding: once label height roughly doubled (three
        // real data lines instead of two), the AABB push above could
        // resolve a pair's *rectangle* overlap via a vertical shift while
        // leaving their underlying glow circles' true Euclidean distance
        // under the combined radius -- a rectangle non-overlap doesn't
        // imply a circle non-overlap when the rectangle is much taller
        // than the circle it contains. Pushed directly along the real
        // vessel-to-vessel vector (not axis-aligned) so it doesn't fight
        // the AABB push's own direction choice.
        const dx = b.xPx - a.xPx;
        const dy = b.yPx - a.yPx;
        const dist = Math.hypot(dx, dy) || 0.0001; // guards a divide-by-zero for coincident points
        const minCircleDist = a.size / 2 + b.size / 2 + minGapPx;
        if (dist < minCircleDist) {
          const push = (minCircleDist - dist) / 2;
          const ux = dx / dist;
          const uy = dy / dist;
          const aFrac = moveAndClamp(a, -ux * push, -uy * push);
          const bFrac = moveAndClamp(b, ux * push, uy * push);
          if (aFrac < 1) moveAndClamp(b, ux * push * (1 - aFrac), uy * push * (1 - aFrac));
          if (bFrac < 1) moveAndClamp(a, -ux * push * (1 - bFrac), -uy * push * (1 - bFrac));
        }
      }
    }
  }

  points.forEach((point) => {
    result.set(point.eventId, {
      eventId: point.eventId,
      x: point.xPx / width,
      y: point.yPx / height,
      size: point.size,
      prominence: point.prominence,
      labelTier: point.labelTier,
      driftPhase: stableRandom(`${point.eventId}:drift`) * Math.PI * 2,
      driftFreq: 0.6 + stableRandom(`${point.eventId}:driftFreq`) * 0.5,
      breathPhase: stableRandom(`${point.eventId}:breath`) * Math.PI * 2,
      breathFreq: 0.5 + stableRandom(`${point.eventId}:breathFreq`) * 0.4,
      pulsePhase: stableRandom(`${point.eventId}:pulse`) * Math.PI * 2,
      pulseFreq: 0.18 + stableRandom(`${point.eventId}:pulseFreq`) * 0.12,
    });
  });

  return result;
}
