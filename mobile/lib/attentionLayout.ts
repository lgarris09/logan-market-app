// Layout math for the Attention Field.
//
// There is no longer a special "focused subject" position and a separate
// "background" scatter -- every entity is a vessel in the same medium, at a
// stable position determined by priority alone. Focus is an interaction
// state layered on top (which vessel is allowed to grow and speak), not a
// different place in space. Nothing here decides text, size-on-screen for
// engaged states, or brightness -- Vessel.tsx owns all of that; this file
// only answers "where does this entity's nucleation point sit, and what are
// its stable rhythm phases."

import { FeedItem } from "../types/loganFeed";

export type VesselLayout = {
  eventId: string;
  x: number; // 0..1 fraction of field width -- stable regardless of focus
  y: number; // 0..1 fraction of field height
  size: number; // px diameter of the resting (dormant) glow
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
  return [...items].sort((a, b) => b.priority_score - a.priority_score);
}

/** The item that should be in focus by default: whatever matters most right now. */
export function defaultFocus(items: FeedItem[]): FeedItem | null {
  return rankedByPriority(items)[0] ?? null;
}

/** The next (or previous) item to bring into focus, wrapping around the ranked order. */
export function shiftFocus(items: FeedItem[], currentId: string, direction: 1 | -1): FeedItem | null {
  const ranked = rankedByPriority(items);
  if (ranked.length === 0) return null;
  const idx = ranked.findIndex((i) => i.event_id === currentId);
  if (idx === -1) return ranked[0];
  const nextIdx = (idx + direction + ranked.length) % ranked.length;
  return ranked[nextIdx];
}

const RADIUS_MIN = 0.07; // highest-priority items rest nearest the center
const RADIUS_MAX = 0.42;
const SIZE_MIN = 46;
const SIZE_MAX = 132;

/**
 * One stable position + one set of rhythm phases per item, for the whole
 * session -- nothing here changes when focus moves. Priority alone decides
 * distance from center and resting size; there is no separate "orbit" for a
 * focused item because nothing here treats focus as spatial.
 */
export function computeAtmosphereLayout(items: FeedItem[]): Map<string, VesselLayout> {
  const result = new Map<string, VesselLayout>();
  if (items.length === 0) return result;

  const scores = items.map((item) => item.priority_score);
  const minScore = Math.min(...scores);
  const maxScore = Math.max(...scores);
  const range = maxScore - minScore || 1;

  items.forEach((item) => {
    const t = (item.priority_score - minScore) / range;
    const radius = RADIUS_MAX - t * (RADIUS_MAX - RADIUS_MIN);
    const size = SIZE_MIN + t * (SIZE_MAX - SIZE_MIN);

    const angle = stableRandom(`${item.event_id}:angle`) * Math.PI * 2;
    const x = 0.5 + radius * Math.cos(angle);
    // Flattened vertically so the scatter reads as a loose horizon rather
    // than a perfect ring.
    const y = 0.5 + radius * Math.sin(angle) * 0.82;

    result.set(item.event_id, {
      eventId: item.event_id,
      x: Math.min(0.92, Math.max(0.08, x)),
      y: Math.min(0.88, Math.max(0.14, y)),
      size,
      driftPhase: stableRandom(`${item.event_id}:drift`) * Math.PI * 2,
      driftFreq: 0.6 + stableRandom(`${item.event_id}:driftFreq`) * 0.5,
      breathPhase: stableRandom(`${item.event_id}:breath`) * Math.PI * 2,
      breathFreq: 0.5 + stableRandom(`${item.event_id}:breathFreq`) * 0.4,
      pulsePhase: stableRandom(`${item.event_id}:pulse`) * Math.PI * 2,
      pulseFreq: 0.18 + stableRandom(`${item.event_id}:pulseFreq`) * 0.12,
    });
  });

  return result;
}
