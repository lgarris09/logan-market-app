import { tracking } from "../constants/theme";
import { humanizeSignalType } from "./signalType";
import { FeedItem } from "../types/loganFeed";

// Layout math for the Attention Field.
//
// Attention Gravity model (replaces the earlier sector+jitter scatter): the
// field organizes around a center of attention rather than being scattered
// and then collision-corrected into shape. Priority (rank/prominence) is
// the dominant force -- it alone decides how close to the center an item
// wants to sit. Relationships (connected_event_ids) and shared domain are
// weak, subordinate forces that nudge related items into loose
// neighborhoods without ever overriding priority. Collision avoidance is
// the final cleanup pass, not the layout generator. Nothing here decides
// text rendering or engaged-state sizing -- Vessel.tsx owns that; this file
// answers "where does this entity's nucleation point sit, what are its
// stable rhythm phases, and how much resting-state label (if any) has this
// vessel earned by rank."
//
// Determinism: every value below is derived either from an item's own
// identity (event_id) or from values already on the item (rank, domain,
// connected_event_ids) -- never from that item's index or position within
// the input array, and every internal pass processes items in a canonical
// event_id-sorted order rather than API response order. The same
// opportunity set, submitted in a different array order, produces the same
// target layout (see attentionLayout.test.ts's "order independence" case).
// This matters most for future live/backend-generated opportunities: a
// stable event_id should feel like it keeps its place in the field across
// polls, not reshuffle because of when a new item happened to appear in the
// response body.
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

function compareEventId(a: { event_id: string }, b: { event_id: string }): number {
  return a.event_id < b.event_id ? -1 : a.event_id > b.event_id ? 1 : 0;
}

/** Items ranked by priority -- the order focus moves through on a swipe.
 * Ties (equal rank) break on event_id, not input array position, so the
 * result never depends on the order the API happened to return items in. */
export function rankedByPriority(items: FeedItem[]): FeedItem[] {
  return [...items].sort((a, b) => a.rank - b.rank || compareEventId(a, b));
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

// The golden angle -- phyllotaxis's anti-clustering constant. See the
// angle-assignment comment further down for why this replaces a plain
// uniform-random angle.
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));

// All fractions below are relative to the field's shorter dimension (its
// width on a portrait phone), so the field composes the same way on an
// iPhone SE, a Pro Max, or an iPad.
// Composition pass: widened from 0.22 -- investigating the anchor pull's
// real behavior (see ANCHOR_ATTRACTION_STRENGTH below) surfaced that
// resolveAngularCrowding's pairwise-separation requirement is a genuine
// geometric floor on how tightly several large, similarly-prominent
// bubbles can cluster, and that floor is set by how much circumference
// the inner radius band actually has (2π * this fraction). A modest
// widening, paired with SIZE_MAX_FRACTION's own reduction below, gives
// real high-priority items more room to sit near the anchor without
// violating that separation -- easing the constraint rather than fighting
// it with stronger and stronger attraction, which plateaus against it
// regardless of magnitude.
const RADIUS_MIN_FRACTION = 0.25; // where rank 2+ organize -- not the anchor itself, see CORE_RADIUS_FRACTION
const RADIUS_MAX_FRACTION = 0.42;
// Composition pass (owner on-device review, round 2): even with the
// hierarchy improvements above, RADIUS_MIN_FRACTION still put rank 1
// noticeably off the true center -- "the center itself is largely empty,"
// so the field didn't read as having an obvious #1. Rank 1 (and only rank
// 1) now targets this much smaller radius instead of the standard
// rank-to-radius curve, so it unmistakably owns the middle of the field;
// rank 2+ still use RADIUS_MIN_FRACTION..RADIUS_MAX_FRACTION as before,
// now organizing around that tighter core rather than sharing it. Nonzero
// (not the literal center point) -- "doesn't need to be mathematically
// locked to exact center," and a true zero radius would make the anchor's
// own stable per-item angle meaningless and collapse its organic drift
// wobble into moving around a single fixed point instead of a small
// circle.
const CORE_RADIUS_FRACTION = 0.08;
// The actual guarantee (see the final anchor-recentering step in
// computeAtmosphereLayout): after every other pass runs -- including
// collision relaxation, which could in principle nudge the anchor if it's
// pushed hard enough resolving a neighbor's overlap -- rank 1 is
// re-clamped inward if it ended up past this radius. Deliberately larger
// than CORE_RADIUS_FRACTION itself (room for organic, collision-driven
// settling) but still unambiguously "the middle," not just "somewhere in
// the inner band." Exported so attentionLayout.test.ts's focal-radius
// guarantee test asserts against this value directly instead of a
// duplicated magic number that could silently drift out of sync.
export const ANCHOR_MAX_RADIUS_FRACTION = 0.14;
const SIZE_MIN_FRACTION = 0.1;
// Composition pass (owner review of a real-device screenshot): narrowed
// from 0.34 -- the single largest vessel (rank 1) was visually dominant
// enough to read as a second center of gravity competing with the
// intended primary attention anchor, especially combined with several
// other high-priority vessels also sitting near max size in the same
// crowded inner band. Still a clear size hierarchy (SIZE_MIN_FRACTION is
// unchanged, "don't flatten all vessels" per that review), just a less
// extreme ceiling -- and, as a side benefit, a bit more breathing room in
// the inner radius band for ANCHOR_ATTRACTION_STRENGTH below to work with.
const SIZE_MAX_FRACTION = 0.3;
// Minimum breathing room between two vessels' glow circles, so neighbors
// never visually fuse into one blob even after relaxation.
const MIN_GAP_FRACTION = 0.025;
// Attention Gravity's attraction pass (below) can leave items starting
// collision relaxation from a tighter-packed configuration than the old
// sector-scatter did -- pulling related/same-domain items together is
// its whole job -- so relaxation has more work to fully resolve,
// especially at larger field sizes. Bumped 16 -> 32 for that; still cheap
// (runs once per layout computation, not per frame).
const RELAXATION_PASSES = 32;

// How many of the highest-priority vessels get a label at rest. The tier
// distinction is kept for the "none" cutoff at feed sizes well beyond
// what's been designed for -- it doesn't affect the collision math (the
// label sits inside the glow circle, not beside/below it), only how much
// text Vessel.tsx renders.
const FULL_LABEL_COUNT = 3;
const COMPACT_LABEL_COUNT = 24;

function labelTierFor(index: number, n: number): LabelTier {
  if (index < Math.min(FULL_LABEL_COUNT, n)) return "full";
  if (index < Math.min(COMPACT_LABEL_COUNT, n)) return "compact";
  return "none";
}

// Sprint 3.6 (bubble-match pass): the label renders centered *inside* the
// bubble, so a vessel with a long real name ("Federal Reserve") or
// descriptor ("VOLATILITY SPIKE") needs a bubble wide enough to actually
// hold it -- otherwise the rank-derived size alone could produce a bubble
// too small for its own text. This vessel grows to fit its label rather
// than silently relying on Vessel.tsx's numberOfLines/ellipsis truncation
// to hide the mismatch.
//
// There's no real measured text width available here -- layout has to
// happen before Vessel.tsx ever renders -- so these are conservative
// per-character-width multiples of font size, tuned to the app's real type
// scale (constants/theme.ts) rather than exact glyph metrics. Erring wide
// only costs a slightly bigger bubble; erring narrow would let text spill
// past the bubble's edge, which is the bug this exists to prevent. Font
// sizes/letter-spacing here must stay in sync with Vessel.tsx's
// restLabelName/restLabelPct/restLabelDescriptor(*Compact) styles.
const NAME_CHAR_WIDTH = 0.58; // InterTight_600SemiBold, mixed case
const PCT_CHAR_WIDTH = 0.62; // tabular-nums digits + "%"
const DESCRIPTOR_CHAR_WIDTH = 0.64; // Inter_500Medium, all-caps reads wider
const FULL_NAME_SIZE = 12;
const COMPACT_NAME_SIZE = 10;
const FULL_PCT_SIZE = 17;
const COMPACT_PCT_SIZE = 13;
const FULL_DESCRIPTOR_SIZE = 7.5;
const COMPACT_DESCRIPTOR_SIZE = 6.5;
// Vessel.tsx caps the label container's width at this fraction of the
// bubble's own diameter (breathing room so text never touches the rim) --
// exported so both files size against the same fraction instead of two
// independently-guessed numbers drifting apart.
export const LABEL_WIDTH_FRACTION = 0.82;

function estimatedLineWidth(
  text: string,
  fontSize: number,
  charWidth: number,
  letterSpacing = 0
): number {
  return text.length * (fontSize * charWidth + letterSpacing);
}

/** The smallest bubble diameter this vessel's own label content can fit
 * inside, at the given tier's font sizes, honoring LABEL_WIDTH_FRACTION.
 * Returns 0 for "none" (no label reserves no space). */
function minDiameterForLabel(item: FeedItem, tier: LabelTier): number {
  if (tier === "none") return 0;
  const compact = tier === "compact";
  const name = item.ticker ?? item.display_name;
  const pct = `${Math.round(item.confidence_score * 100)}%`;
  const descriptor = humanizeSignalType(item.signal_type);

  const widest = Math.max(
    estimatedLineWidth(name, compact ? COMPACT_NAME_SIZE : FULL_NAME_SIZE, NAME_CHAR_WIDTH),
    estimatedLineWidth(pct, compact ? COMPACT_PCT_SIZE : FULL_PCT_SIZE, PCT_CHAR_WIDTH),
    estimatedLineWidth(
      descriptor,
      compact ? COMPACT_DESCRIPTOR_SIZE : FULL_DESCRIPTOR_SIZE,
      DESCRIPTOR_CHAR_WIDTH,
      tracking.metadata
    )
  );

  return widest / LABEL_WIDTH_FRACTION;
}

type ScatterPoint = {
  eventId: string;
  // Working position in real px (not the [0,1] fraction), clamped per
  // vessel against its own real glow radius so nothing extends past the
  // true screen edge regardless of vessel size.
  xPx: number;
  yPx: number;
  size: number;
  prominence: number;
  labelTier: LabelTier;
  radius: number; // size / 2 -- the vessel's true occupied footprint
};

// Minimum breathing room from the true screen edge, on top of each vessel's
// own glow radius.
const EDGE_PADDING = 12;

/** Clamps a vessel's center so its full glow circle stays within the real
 * field bounds, with a small edge margin. Falls back to centering on that
 * axis if the vessel is too large to fit with margin at all (a degenerate
 * field size), rather than producing an inverted range. */
function clampToField(
  xPx: number,
  yPx: number,
  radius: number,
  width: number,
  height: number
): { x: number; y: number } {
  const minX = radius + EDGE_PADDING;
  const maxX = width - radius - EDGE_PADDING;
  const minY = radius + EDGE_PADDING;
  const maxY = height - radius - EDGE_PADDING;
  return {
    x: minX <= maxX ? Math.min(Math.max(xPx, minX), maxX) : width / 2,
    y: minY <= maxY ? Math.min(Math.max(yPx, minY), maxY) : height / 2,
  };
}

// Attention Gravity: relationship/domain/anchor attraction. Applied after
// initial priority-based placement, before collision relaxation -- a weak
// organizing force, not a second layout generator. Weights are
// deliberately asymmetric: a real opportunity relationship
// (connected_event_ids) pulls materially harder than merely sharing a
// domain, which stays subtle on purpose so the field develops loose
// semantic neighborhoods rather than collapsing into domain-colored
// clumps. Single-shot, not iterative: each force's pull is computed once,
// toward its target's priority-derived origin position (not an already-
// attracted position), and independently capped in isolation before all
// three are summed. That -- not a shared "total across N passes" budget
// that's hard to reason about precisely -- is what makes "domain stays
// materially weaker than relationship" and "no force can drag a
// low-priority item into the high-attention center" exact, provable
// bounds rather than emergent/approximate ones.
const RELATIONSHIP_ATTRACTION_STRENGTH = 0.35;
const DOMAIN_ATTRACTION_STRENGTH = 0.12;
// Composition pass: pulls every *other* item toward the single
// highest-priority item's own origin position, scaled by the puller's own
// prominence (see applyAttraction's per-point use below) -- so rank 2/3
// organize around that one primary anchor instead of each independently
// seeking their own center, while low-priority items (prominence near 0)
// are barely pulled at all and keep roaming the outer field freely. This
// is what turns "several local centers" into "one dominant focal zone
// with secondary orbits," per the owner's real-device review -- not a
// second radius rule, just another bounded, tangentially-biased pull like
// relationship/domain above.
const ANCHOR_ATTRACTION_STRENGTH = 0.42;
// Each force's own hard ceiling, applied before all three are combined.
// Domain's is materially smaller than relationship's -- "subtle" is a
// property of the cap, not just the strength constant above, so it holds
// regardless of how many domain peers (or how tightly connected
// relationships) an item happens to have. Anchor's is scaled per-item by
// that item's own prominence before use (see applyAttraction), so this is
// only its *base* value -- a low-priority item's effective anchor cap is
// close to zero regardless of this number.
const RELATIONSHIP_PULL_CAP_FRACTION = 0.045;
const DOMAIN_PULL_CAP_FRACTION = 0.014;
const ANCHOR_PULL_CAP_FRACTION = 0.075;
// Final safety ceiling on an item's *combined* displacement from its
// priority-derived origin (all three forces together). This -- not any
// individual force's own cap -- is the actual "priority stays dominant"
// guarantee: whatever the forces add up to, no item can end up more than
// this far from where its own rank alone placed it. Widened from 0.05 to
// make room for the anchor force to meaningfully co-express alongside
// relationship/domain rather than being diluted by a budget sized for two
// forces -- still well under RADIUS_MAX_FRACTION - RADIUS_MIN_FRACTION
// (0.20)'s own band width, so it organizes neighborhoods without eroding
// the radius bands priority itself establishes.
const MAX_ATTRACTION_DISPLACEMENT_FRACTION = 0.11;
// How much of the combined pull's *radial* component (toward/away from the
// attention center) survives, vs. its tangential component (around it) --
// see biasTangential's own comment. Deliberately much stronger than
// collision relaxation's tangential bias: attraction's whole job is to
// organize neighborhoods (an angular concept), never to move an item
// toward or away from the center, which is priority's job alone. Without
// this, a connected/domain neighbor that happens to sit almost directly
// toward the center from a given point could spend that point's entire
// capped pull budget closing radius instead of organizing angle.
const ATTRACTION_RADIAL_DAMPING = 0.12;

function capMagnitude(dx: number, dy: number, maxPx: number): { dx: number; dy: number } {
  const dist = Math.hypot(dx, dy);
  if (dist <= maxPx || dist < 1e-6) return { dx, dy };
  const scale = maxPx / dist;
  return { dx: dx * scale, dy: dy * scale };
}

/** Splits (dx,dy) into components radial/tangential to the field center as
 * seen from (px,py), damps the radial share, and rescales back to the
 * original magnitude -- only the *direction* a movement takes shifts
 * toward "around the center" rather than "toward/away from it," never how
 * far it moves. Shared by collision relaxation (resolving an overlap by
 * spreading two neighbors apart in angle, not shoving one radially, keeps
 * priority ordering intact) and attraction (a real relationship/domain tie
 * should organize a neighborhood, never meaningfully migrate an item's
 * priority tier). */
function biasTangential(
  px: number,
  py: number,
  centerX: number,
  centerY: number,
  dx: number,
  dy: number,
  radialDamping: number
): { dx: number; dy: number } {
  const radiusX = px - centerX;
  const radiusY = py - centerY;
  const radiusDist = Math.hypot(radiusX, radiusY);
  if (radiusDist < 1e-6) return { dx, dy };

  const radialX = radiusX / radiusDist;
  const radialY = radiusY / radiusDist;
  const tangentX = -radialY;
  const tangentY = radialX;
  const radialComponent = dx * radialX + dy * radialY;
  const tangentComponent = dx * tangentX + dy * tangentY;

  const biasedX = tangentComponent * tangentX + radialComponent * radialDamping * radialX;
  const biasedY = tangentComponent * tangentY + radialComponent * radialDamping * radialY;
  const biasedMag = Math.hypot(biasedX, biasedY);
  if (biasedMag < 1e-6) return { dx, dy };

  const originalMag = Math.hypot(dx, dy);
  const scale = originalMag / biasedMag;
  return { dx: biasedX * scale, dy: biasedY * scale };
}

function applyAttraction(
  points: ScatterPoint[],
  items: FeedItem[],
  width: number,
  height: number,
  minDim: number,
  anchorId: string | null
): void {
  if (points.length < 2) return;

  const itemById = new Map(items.map((item) => [item.event_id, item]));

  // Symmetric: an item "connects" to another if either side lists it, so
  // the pull applies to both regardless of which side the backend recorded
  // it on. Filtered to ids actually present on the field -- a connection to
  // an item that didn't make this poll's cut has nothing to pull toward.
  const connectionsOf = new Map<string, Set<string>>();
  const link = (a: string, b: string) => {
    if (!connectionsOf.has(a)) connectionsOf.set(a, new Set());
    connectionsOf.get(a)!.add(b);
  };
  for (const item of items) {
    for (const otherId of item.connected_event_ids) {
      if (otherId === item.event_id || !itemById.has(otherId)) continue;
      link(item.event_id, otherId);
      link(otherId, item.event_id);
    }
  }

  const domainGroups = new Map<string, string[]>();
  for (const item of items) {
    if (!domainGroups.has(item.domain)) domainGroups.set(item.domain, []);
    domainGroups.get(item.domain)!.push(item.event_id);
  }

  // Origin = each point's priority-derived placement, before any attraction
  // -- every pull below is computed toward *these* fixed positions (never
  // toward another point's already-attracted position), so the whole
  // function reduces to one deterministic pass per point instead of an
  // iterative process whose outcome depends on how many rounds ran.
  const originX = new Map(points.map((p) => [p.eventId, p.xPx]));
  const originY = new Map(points.map((p) => [p.eventId, p.yPx]));
  const relationshipCapPx = RELATIONSHIP_PULL_CAP_FRACTION * minDim;
  const domainCapPx = DOMAIN_PULL_CAP_FRACTION * minDim;
  const anchorCapPx = ANCHOR_PULL_CAP_FRACTION * minDim;
  const maxDisplacementPx = MAX_ATTRACTION_DISPLACEMENT_FRACTION * minDim;
  const centerX = width / 2;
  const centerY = height / 2;
  const anchorOx = anchorId ? (originX.get(anchorId) ?? null) : null;
  const anchorOy = anchorId ? (originY.get(anchorId) ?? null) : null;

  for (const point of points) {
    const item = itemById.get(point.eventId)!;
    const ox = originX.get(point.eventId)!;
    const oy = originY.get(point.eventId)!;
    let dx = 0;
    let dy = 0;

    const connections = connectionsOf.get(point.eventId);
    if (connections && connections.size > 0) {
      let cx = 0;
      let cy = 0;
      connections.forEach((id) => {
        cx += originX.get(id) ?? ox;
        cy += originY.get(id) ?? oy;
      });
      cx /= connections.size;
      cy /= connections.size;
      const pull = capMagnitude(
        (cx - ox) * RELATIONSHIP_ATTRACTION_STRENGTH,
        (cy - oy) * RELATIONSHIP_ATTRACTION_STRENGTH,
        relationshipCapPx
      );
      dx += pull.dx;
      dy += pull.dy;
    }

    const domainPeers = (domainGroups.get(item.domain) ?? []).filter((id) => id !== point.eventId);
    if (domainPeers.length > 0) {
      let cx = 0;
      let cy = 0;
      domainPeers.forEach((id) => {
        cx += originX.get(id) ?? ox;
        cy += originY.get(id) ?? oy;
      });
      cx /= domainPeers.length;
      cy /= domainPeers.length;
      const pull = capMagnitude(
        (cx - ox) * DOMAIN_ATTRACTION_STRENGTH,
        (cy - oy) * DOMAIN_ATTRACTION_STRENGTH,
        domainCapPx
      );
      dx += pull.dx;
      dy += pull.dy;
    }

    // Composition pass: every item (other than the anchor itself) is
    // pulled a little toward the single highest-priority item's own
    // origin position, scaled by *this* item's own prominence -- a rank
    // 2/3 item (prominence near 1) gets nearly the full anchor pull and
    // visibly organizes around it; a low-priority item (prominence near 0)
    // gets almost none and stays free to roam the outer field. This is
    // the "secondary orbit around one dominant focal zone" the owner asked
    // for, not a second radius rule -- still just a bounded, tangentially-
    // biased nudge like relationship/domain above.
    if (anchorId && point.eventId !== anchorId && anchorOx !== null && anchorOy !== null) {
      const pull = capMagnitude(
        (anchorOx - ox) * ANCHOR_ATTRACTION_STRENGTH * point.prominence,
        (anchorOy - oy) * ANCHOR_ATTRACTION_STRENGTH * point.prominence,
        anchorCapPx * point.prominence
      );
      dx += pull.dx;
      dy += pull.dy;
    }

    // Attraction organizes neighborhoods -- it should never meaningfully
    // migrate an item's priority tier. Damping the radial share heavily
    // (far more than collision relaxation's own, milder damping) is what
    // makes that true even in the worst case: a connected/domain neighbor
    // that happens to sit almost directly toward the center from this
    // point, where an undamped pull would spend its entire capped budget
    // closing radius instead of organizing angle.
    const biased = biasTangential(ox, oy, centerX, centerY, dx, dy, ATTRACTION_RADIAL_DAMPING);

    // Final safety ceiling on the *combined* pull, then re-clamp to field
    // bounds -- the actual "priority stays dominant" guarantee: whatever
    // the three independently-capped forces add up to, no item can end up
    // more than this far from where its own rank alone placed it.
    const capped = capMagnitude(biased.dx, biased.dy, maxDisplacementPx);
    const clamped = clampToField(ox + capped.dx, oy + capped.dy, point.radius, width, height);
    point.xPx = clamped.x;
    point.yPx = clamped.y;
  }
}

// Composition pass: a soft counterweight against the field accumulating
// most of its visible mass on one side. The anchor/relationship/domain
// forces above are all real, meaningful organization -- a genuinely
// connected cluster of high-priority same-domain items *should* be able to
// sit together even if that leans the field one way -- so this can't be a
// hard symmetry rule (a rigid grid or forced balance would fight that
// organization and read as mechanical). Instead it measures how lopsided
// the field's *actual bubble area* (not just point count) has ended up,
// and only when that's genuinely skewed, gives the vessels contributing
// most to the skew a gentle tangential nudge toward the lighter side.
// Runs after attraction (so it's reacting to where the real organizing
// forces, including the new anchor pull, actually left things) and before
// angular de-crowding/collision (so both still get a chance to resolve
// whatever local crowding this shifts around).
const BALANCE_STRENGTH = 0.06;
const BALANCE_PULL_CAP_FRACTION = 0.03;
// Below this, the field's area-weighted "center of mass" is close enough
// to the true center that nudging anything would be correcting noise, not
// a real imbalance.
const BALANCE_IMBALANCE_THRESHOLD_FRACTION = 0.05;
// A cluster of high-priority items legitimately organizing around the
// anchor *is* real justification for the field leaning that way -- exactly
// the "unless the opportunity relationships truly justify it" carve-out.
// Without this, balance would measure the anchor pull's own clustering as
// an "imbalance" and fan those same items back apart, directly undoing
// the primary-focal-zone effect the anchor force exists to create. Items
// at or above this prominence are exempt from being nudged (they can
// still contribute to *measuring* the imbalance, just never get pushed
// for it); only the more free-floating lower-priority items -- which
// weren't meaningfully anchor-pulled in the first place -- get redistributed
// to fill in genuinely empty space elsewhere.
const BALANCE_EXEMPT_PROMINENCE = 0.5;

function applyBalance(points: ScatterPoint[], width: number, height: number, minDim: number): void {
  if (points.length < 2) return;
  const centerX = width / 2;
  const centerY = height / 2;

  let totalArea = 0;
  let massX = 0;
  let massY = 0;
  for (const point of points) {
    const area = Math.PI * point.radius * point.radius;
    totalArea += area;
    massX += point.xPx * area;
    massY += point.yPx * area;
  }
  if (totalArea < 1e-6) return;
  massX /= totalArea;
  massY /= totalArea;

  const imbalanceX = massX - centerX;
  const imbalanceY = massY - centerY;
  const imbalanceDist = Math.hypot(imbalanceX, imbalanceY);
  const thresholdPx = BALANCE_IMBALANCE_THRESHOLD_FRACTION * minDim;
  if (imbalanceDist < thresholdPx) return; // already reasonably balanced

  const imbalanceDirX = imbalanceX / imbalanceDist;
  const imbalanceDirY = imbalanceY / imbalanceDist;
  const tangentX = -imbalanceDirY;
  const tangentY = imbalanceDirX;
  const capPx = BALANCE_PULL_CAP_FRACTION * minDim;

  for (const point of points) {
    const px = point.xPx - centerX;
    const py = point.yPx - centerY;
    const pointDist = Math.hypot(px, py);
    if (pointDist < 1) continue; // sitting right at the center -- no meaningful side to nudge from

    // How much this point sits toward the "heavy" side (positive) vs. the
    // light one (negative) -- only vessels actually contributing to the
    // imbalance get nudged, and how far past the threshold the field is
    // scales the push, so a mildly uneven field barely moves while a
    // genuinely lopsided one gets a real (still capped, still tangential)
    // correction.
    const alignment = (px / pointDist) * imbalanceDirX + (py / pointDist) * imbalanceDirY;
    if (alignment <= 0) continue;
    if (point.prominence >= BALANCE_EXEMPT_PROMINENCE) continue;

    const areaShare = (Math.PI * point.radius * point.radius) / totalArea;
    const pushMag = Math.min(
      capPx,
      BALANCE_STRENGTH * (imbalanceDist - thresholdPx) * alignment * areaShare * points.length
    );
    if (pushMag < 1e-6) continue;

    // Push tangentially, choosing whichever rotation direction actually
    // moves this specific point away from the heavy axis (points on
    // opposite sides of that axis need to fan out in opposite directions).
    const sign = px * tangentX + py * tangentY >= 0 ? 1 : -1;
    const clamped = clampToField(
      point.xPx + tangentX * sign * pushMag,
      point.yPx + tangentY * sign * pushMag,
      point.radius,
      width,
      height
    );
    point.xPx = clamped.x;
    point.yPx = clamped.y;
  }
}

// Each item's stable per-item angle (assigned in computeAtmosphereLayout,
// before this runs) is well-distributed on average, but with no guaranteed
// minimum separation -- two items that both land in a crowded radius band
// (most often the small, high-prominence inner band, where several large
// bubbles compete for the same tight ring) can still coincidentally land
// at a near-identical angle. Left for general 2D collision relaxation to
// discover, that gets "resolved" by pushing one item a large distance
// radially outward -- eroding exactly the priority ordering this model
// exists to preserve. Rotating both points apart around the field center
// instead -- preserving each one's own radius, and therefore its priority
// ordering -- keeps that resolution to a small, cheap angular adjustment.
// Runs before both attraction and full collision relaxation, so neither
// has to discover this case through that large radial escape.
function resolveAngularCrowding(
  points: ScatterPoint[],
  width: number,
  height: number,
  minDim: number
): void {
  if (points.length < 2) return;
  const centerX = width / 2;
  const centerY = height / 2;
  const minGapPx = MIN_GAP_FRACTION * minDim;
  const passes = 16;

  for (let pass = 0; pass < passes; pass++) {
    for (let i = 0; i < points.length; i++) {
      for (let j = i + 1; j < points.length; j++) {
        const a = points[i];
        const b = points[j];
        const aRadius = Math.hypot(a.xPx - centerX, a.yPx - centerY);
        const bRadius = Math.hypot(b.xPx - centerX, b.yPx - centerY);
        if (aRadius < 1 || bRadius < 1) continue; // degenerate: sitting right at the center

        const aAngle = Math.atan2(a.yPx - centerY, a.xPx - centerX);
        const bAngle = Math.atan2(b.yPx - centerY, b.xPx - centerX);
        let angleDiff = bAngle - aAngle;
        while (angleDiff > Math.PI) angleDiff -= Math.PI * 2;
        while (angleDiff <= -Math.PI) angleDiff += Math.PI * 2;

        // The same linear separation collision relaxation itself enforces
        // (combined radius + gap), converted to an angular threshold at
        // these two points' average radius from center.
        const avgRadius = (aRadius + bRadius) / 2;
        const requiredLinear = a.radius + b.radius + minGapPx;
        const requiredAngle = Math.min(Math.PI, requiredLinear / avgRadius);

        const currentAngleGap = Math.abs(angleDiff);
        if (currentAngleGap < requiredAngle) {
          const push = (requiredAngle - currentAngleGap) / 2;
          const dir = angleDiff >= 0 ? 1 : -1;
          const newAAngle = aAngle - dir * push;
          const newBAngle = bAngle + dir * push;
          a.xPx = centerX + Math.cos(newAAngle) * aRadius;
          a.yPx = centerY + Math.sin(newAAngle) * aRadius;
          b.xPx = centerX + Math.cos(newBAngle) * bRadius;
          b.yPx = centerY + Math.sin(newBAngle) * bRadius;
        }
      }
    }
  }

  // Re-clamp to field bounds -- rotating around the center shouldn't
  // normally push a point past the edge (radius is unchanged), but this
  // guards the degenerate case anyway, consistent with every other pass.
  for (const point of points) {
    const clamped = clampToField(point.xPx, point.yPx, point.radius, width, height);
    point.xPx = clamped.x;
    point.yPx = clamped.y;
  }
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
 *
 * This function is source-agnostic and count-agnostic by design -- it reads
 * only event_id, rank, domain, connected_event_ids, confidence_score,
 * signal_type, ticker/display_name (all part of the generic opportunity
 * contract), never a hardcoded entity list or an assumed item count.
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
  const maxRank = Math.max(...items.map((item) => item.rank));
  const rankRange = maxRank - 1 || 1;
  const n = items.length;

  // Tier (full/compact/none label) is rank-position-based -- computed from
  // the tie-broken rank order -- but every *pairwise* pass below (attraction,
  // collision) iterates over `canonical` (sorted purely by event_id), never
  // by rank or by API response order, so the result never depends on the
  // order items happened to arrive in.
  const ranked = rankedByPriority(items);
  const rankPosition = new Map(ranked.map((item, i) => [item.event_id, i]));
  const canonical = [...items].sort(compareEventId);
  // The single highest-priority item -- the primary attention anchor
  // everything else (secondary orbit, relationship/domain neighborhoods)
  // organizes around. Computed once here and reused for both the anchor's
  // own tight radius below and applyAttraction's anchor-pull force.
  const anchorId = ranked[0]?.event_id ?? null;

  const points: ScatterPoint[] = canonical.map((item) => {
    const t = 1 - (item.rank - 1) / rankRange;
    // Rank 1 owns the center: it targets a small, fixed core radius
    // instead of the standard rank-to-radius curve, so the field always
    // has an unmistakable focal point rather than rank 1 merely being
    // *somewhat* closer than rank 2. Everyone else still uses the normal
    // curve, now organizing around that core rather than sharing it.
    const radiusFraction =
      item.event_id === anchorId
        ? CORE_RADIUS_FRACTION
        : RADIUS_MAX_FRACTION - t * (RADIUS_MAX_FRACTION - RADIUS_MIN_FRACTION);
    const tier = labelTierFor(rankPosition.get(item.event_id)!, n);
    // Rank alone can produce a bubble too small for its own label (a long
    // real name/descriptor on a lower-priority item) -- the vessel grows to
    // fit its text rather than relying on truncation to hide the mismatch.
    const size = Math.max(sizeMin + t * (sizeMax - sizeMin), minDiameterForLabel(item, tier));

    // Attention Gravity: angle is derived from a stable hash of this item's
    // own event_id alone -- never its index or rank position among the
    // current set -- so adding, removing, or reordering other items never
    // shifts where THIS item wants to sit angularly. Distance from center
    // (radiusFraction above) is what carries priority; angle only spreads
    // items around that radius so same-priority items don't stack on one
    // point. Flattened vertically so the scatter reads as a loose horizon
    // rather than a perfect ring.
    //
    // Uses the golden angle (~137.5°), not a uniform-random angle: plain
    // `stableRandom(id) * 2π` occasionally puts two same-priority-band
    // items at nearly the same angle by chance (no guarantee against it,
    // unlike the old sector system), forcing collision relaxation to push
    // one of them a large, visually-arbitrary distance to resolve it.
    // Mapping each item's hash to a "slot" in a large, fixed conceptual
    // sequence and stepping by the golden angle keeps angles just as
    // per-item/order-independent (the slot still comes only from this
    // item's own event_id) while getting the same anti-clustering
    // distribution phyllotaxis uses -- even nearby slot numbers land at
    // well-separated angles, so collision relaxation only ever has to
    // resolve genuine radius-band crowding, not incidental angle clashes.
    const angleSlot = Math.floor(stableRandom(`${item.event_id}:angle`) * 100000);
    const angle = (angleSlot * GOLDEN_ANGLE) % (Math.PI * 2);
    const xFrac = 0.5 + radiusFraction * Math.cos(angle);
    const yFrac = 0.5 + radiusFraction * Math.sin(angle) * 0.82;

    const radius = size / 2;
    const clamped = clampToField(xFrac * width, yFrac * height, radius, width, height);

    return {
      eventId: item.event_id,
      xPx: clamped.x,
      yPx: clamped.y,
      size,
      prominence: t,
      labelTier: tier,
      radius,
    };
  });

  // Relationships/domain/anchor: weak organizing forces layered on top of
  // the priority-derived placement above, bounded well under the collision
  // gap's own tolerance -- see applyAttraction's own comment for the
  // guarantees this provides.
  applyAttraction(points, items, width, height, minDim, anchorId);

  // Composition: corrects for the field's real bubble-area mass ending up
  // lopsided, most often as a side effect of the organizing forces above
  // (a cluster of connected/same-domain/anchor-pulled high-priority items
  // can legitimately end up leaning one way) -- see applyBalance's own
  // comment for why this is a soft, threshold-gated nudge, not a rigid
  // symmetry rule.
  applyBalance(points, width, height, minDim);

  // Both the forces above and the placement step before them can leave two
  // items at a near-identical angle in a crowded radius band (most often
  // the small, high-prominence inner band, where several large bubbles
  // compete for the same tight ring, now further pulled together by the
  // new anchor force on purpose). Left alone, collision relaxation would
  // "resolve" that by pushing one of them a large distance radially --
  // eroding exactly the priority ordering this model exists to preserve.
  // Resolving angular crowding directly, after organization but before
  // general 2D relaxation runs, keeps that resolution to a small rotation
  // around the center instead -- the anchor-pulled cluster still reads as
  // one neighborhood, just with each vessel in its own space within it.
  resolveAngularCrowding(points, width, height, minDim);

  // Collision relaxation: the final cleanup pass, not the layout generator.
  // Separates every pair of vessels by their glow circles (the label sits
  // centered inside the glow, so circle-circle distance is the vessel's
  // true occupied footprint). Iterates over `points`, already in canonical
  // event_id order from the map above, so this pass's result doesn't depend
  // on API response order either.
  const minGapPx = MIN_GAP_FRACTION * minDim;
  const centerX = width / 2;
  const centerY = height / 2;
  // Resolving an overlap by shoving a point straight along the raw a<->b
  // vector can drive a genuinely high-priority item radially outward, past
  // where its own rank alone would put it -- most visibly in the crowded
  // inner band, where several large, similarly-prominent bubbles compete
  // for the same small radius. Damping the *radial* share of every push
  // (while keeping the *tangential* share -- spreading neighbors apart in
  // angle around the attention center -- at full strength) resolves the
  // same overlap distance without eroding the priority ordering the whole
  // rest of this model is built to preserve. Only a bias, not a hard
  // constraint (a small radial share still leaks through, and a point near
  // a field edge can still be clamped however it needs to be) -- pure
  // tangential-only resolution isn't always geometrically possible.
  const RADIAL_PUSH_DAMPING = 0.3;

  // Moves `p` by (dx,dy) then clamps to field bounds, returning how much of
  // the intended movement actually happened (1 = full movement, less than 1
  // if a field edge cut it short). A vessel near a field edge can get
  // clamped mid-push, silently absorbing less than its half of the required
  // separation -- its partner never learns the shortfall exists, and the
  // pair settles for a real, visible overlap. Reported back so the caller
  // can give the difference to the *other* vessel instead.
  function moveAndClamp(p: ScatterPoint, dx: number, dy: number): number {
    const intended = Math.hypot(dx, dy);
    if (intended < 1e-6) return 1;
    const clamped = clampToField(p.xPx + dx, p.yPx + dy, p.radius, width, height);
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

        const dx = b.xPx - a.xPx;
        const dy = b.yPx - a.yPx;
        const dist = Math.hypot(dx, dy) || 0.0001; // guards a divide-by-zero for coincident points
        const minCircleDist = a.radius + b.radius + minGapPx;
        if (dist < minCircleDist) {
          const push = (minCircleDist - dist) / 2;
          const midX = (a.xPx + b.xPx) / 2;
          const midY = (a.yPx + b.yPx) / 2;
          const biased = biasTangential(midX, midY, centerX, centerY, dx, dy, RADIAL_PUSH_DAMPING);
          const biasedDist = Math.hypot(biased.dx, biased.dy) || 0.0001;
          const ux = biased.dx / biasedDist;
          const uy = biased.dy / biasedDist;

          const aFrac = moveAndClamp(a, -ux * push, -uy * push);
          const bFrac = moveAndClamp(b, ux * push, uy * push);
          if (aFrac < 1) moveAndClamp(b, ux * push * (1 - aFrac), uy * push * (1 - aFrac));
          if (bFrac < 1) moveAndClamp(a, -ux * push * (1 - bFrac), -uy * push * (1 - bFrac));
        }
      }
    }
  }

  // The actual "rank 1 owns the center" guarantee: everything above --
  // angular de-crowding, collision relaxation -- is designed to leave the
  // anchor's radius alone (rotating neighbors around it rather than
  // pushing it outward), but nothing before this point *proves* it stayed
  // put. One direct, final check costs nothing and makes the promise
  // exact rather than merely likely: if the anchor ended up past
  // ANCHOR_MAX_RADIUS_FRACTION for any reason, pull it straight back in
  // along whatever angle it's currently at (preserving the organic
  // per-item angle/drift, not resetting it) rather than re-deriving its
  // position from scratch.
  if (anchorId) {
    const anchor = points.find((point) => point.eventId === anchorId);
    if (anchor) {
      const centerX = width / 2;
      const centerY = height / 2;
      const dx = anchor.xPx - centerX;
      const dy = anchor.yPx - centerY;
      const dist = Math.hypot(dx, dy);
      const maxRadiusPx = ANCHOR_MAX_RADIUS_FRACTION * minDim;
      if (dist > maxRadiusPx && dist > 1e-6) {
        const scale = maxRadiusPx / dist;
        const clamped = clampToField(
          centerX + dx * scale,
          centerY + dy * scale,
          anchor.radius,
          width,
          height
        );
        anchor.xPx = clamped.x;
        anchor.yPx = clamped.y;
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
