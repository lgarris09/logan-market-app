// Layout math for the Opportunity Field, kept separate from rendering.
//
// This is deliberately a small physics-style relaxation, not a formula that
// computes an exact angle/radius and cosmetically jitters it. Each node is
// seeded at a natural starting point, then three simple forces are applied
// over many iterations until the system settles:
//   - a radial spring pulling each node toward the orbit distance its
//     rank implies (importance = distance from the core)
//   - a cohesion pull toward its cluster's centroid (related entities drift
//     toward each other)
//   - mutual repulsion between every pair of nodes (nothing overlaps, nothing
//     collides with a neighbor's label)
// The final position is whatever those forces settle into -- not prescribed.
// It's deterministic (same items always settle the same way), just not
// evenly-spaced-by-construction.

import { FeedItem } from "../types/loganFeed";

const MIN_SPACING = 82; // px, center-to-center -- node ring + label clearance
const ITERATIONS = 70;
const RADIAL_STRENGTH = 0.08;
const COHESION_STRENGTH = 0.02;
const REPULSION_STRENGTH = 0.55; // fraction of overlap resolved per iteration
const GOLDEN_ANGLE = 2.399963229728653; // radians -- natural, non-repeating spread

export type FieldNodePosition = {
  x: number;
  y: number;
  floatPhase: number; // 0..2π, stable per entity
  floatFreq: number; // ~0.85..1.15, stable per entity
};

function hashString(value: string): number {
  let hash = 0;
  for (let i = 0; i < value.length; i++) {
    hash = (hash * 31 + value.charCodeAt(i)) >>> 0;
  }
  return hash;
}

// Deterministic pseudo-random in [0, 1) for a given seed string -- the same
// entity always gets the same seed position/phase, so the field doesn't
// reshuffle itself on every refresh.
function stableRandom(seed: string): number {
  return (hashString(seed) % 10000) / 10000;
}

class UnionFind {
  private parent = new Map<string, string>();

  find(x: string): string {
    if (!this.parent.has(x)) this.parent.set(x, x);
    const p = this.parent.get(x)!;
    if (p !== x) {
      const root = this.find(p);
      this.parent.set(x, root);
      return root;
    }
    return x;
  }

  union(a: string, b: string) {
    const ra = this.find(a);
    const rb = this.find(b);
    if (ra !== rb) this.parent.set(ra, rb);
  }
}

/** Groups items into connected components using connected_event_ids. */
export function buildClusters(items: FeedItem[]): Map<string, string[]> {
  const uf = new UnionFind();
  const knownIds = new Set(items.map((i) => i.event_id));
  items.forEach((item) => uf.find(item.event_id));
  items.forEach((item) => {
    item.connected_event_ids.forEach((otherId) => {
      if (knownIds.has(otherId)) uf.union(item.event_id, otherId);
    });
  });

  const clusters = new Map<string, string[]>();
  items.forEach((item) => {
    const root = uf.find(item.event_id);
    if (!clusters.has(root)) clusters.set(root, []);
    clusters.get(root)!.push(item.event_id);
  });
  return clusters;
}

/** All event_ids in the same connected component as eventId (including itself). */
export function clusterMembersOf(items: FeedItem[], eventId: string): Set<string> {
  const clusters = buildClusters(items);
  for (const ids of clusters.values()) {
    if (ids.includes(eventId)) return new Set(ids);
  }
  return new Set([eventId]);
}

type Point = { x: number; y: number };

export function computeFieldLayout(
  items: FeedItem[],
  center: number,
  innerRadius: number,
  outerRadius: number
): Map<string, FieldNodePosition> {
  const result = new Map<string, FieldNodePosition>();
  if (items.length === 0) return result;

  const clusterByItem = new Map<string, string>();
  buildClusters(items).forEach((ids, root) => ids.forEach((id) => clusterByItem.set(id, root)));

  // Normalize by rank position, not a raw score (ADR-029 -- the backend
  // never sends one). Rank 1 (best) -> t=1; the lowest-ranked item -> t=0.
  const maxRank = Math.max(...items.map((i) => i.rank));
  const rankRange = maxRank - 1 || 1;

  const targetRadius = new Map<string, number>();
  const points = new Map<string, Point>();

  // Seed: golden-angle spread (the same distribution pattern that gives
  // sunflower seeds and pinecones their non-repeating natural look) at each
  // item's target orbit distance, plus a stable per-item nudge so identical
  // ranks don't seed on top of each other.
  items.forEach((item, index) => {
    const t = 1 - (item.rank - 1) / rankRange;
    const radius = outerRadius - t * (outerRadius - innerRadius);
    targetRadius.set(item.event_id, radius);

    const angle = index * GOLDEN_ANGLE + stableRandom(`${item.entity_id}:seed`) * 0.6;
    points.set(item.event_id, {
      x: center + radius * Math.cos(angle),
      y: center + radius * Math.sin(angle),
    });
  });

  const ids = items.map((i) => i.event_id);

  for (let iter = 0; iter < ITERATIONS; iter++) {
    // Cluster cohesion: pull each node toward its cluster's current centroid.
    const centroids = new Map<string, Point & { count: number }>();
    ids.forEach((id) => {
      const cluster = clusterByItem.get(id)!;
      const p = points.get(id)!;
      const c = centroids.get(cluster) ?? { x: 0, y: 0, count: 0 };
      c.x += p.x;
      c.y += p.y;
      c.count += 1;
      centroids.set(cluster, c);
    });

    ids.forEach((id) => {
      const cluster = clusterByItem.get(id)!;
      const c = centroids.get(cluster)!;
      if (c.count < 2) return; // no cohesion pull for a cluster of one
      const centroidX = c.x / c.count;
      const centroidY = c.y / c.count;
      const p = points.get(id)!;
      p.x += (centroidX - p.x) * COHESION_STRENGTH;
      p.y += (centroidY - p.y) * COHESION_STRENGTH;
    });

    // Radial spring: pull each node toward its priority-based orbit distance,
    // along whatever direction it currently sits from the core -- angle is
    // never fixed, only distance is nudged.
    ids.forEach((id) => {
      const p = points.get(id)!;
      const dx = p.x - center;
      const dy = p.y - center;
      const dist = Math.sqrt(dx * dx + dy * dy) || 0.001;
      const desired = targetRadius.get(id)!;
      const delta = (desired - dist) * RADIAL_STRENGTH;
      const ux = dx / dist;
      const uy = dy / dist;
      p.x += ux * delta;
      p.y += uy * delta;
    });

    // Mutual repulsion: nothing settles closer than MIN_SPACING.
    for (let i = 0; i < ids.length; i++) {
      for (let j = i + 1; j < ids.length; j++) {
        const a = points.get(ids[i])!;
        const b = points.get(ids[j])!;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 0.001;
        if (dist < MIN_SPACING) {
          const overlap = (MIN_SPACING - dist) * REPULSION_STRENGTH;
          const ux = dx / dist;
          const uy = dy / dist;
          a.x -= ux * overlap * 0.5;
          a.y -= uy * overlap * 0.5;
          b.x += ux * overlap * 0.5;
          b.y += uy * overlap * 0.5;
        }
      }
    }
  }

  // Safety clamp -- keeps a pathological force interaction from ever pushing a
  // node off the visible field, without affecting normal settled layouts.
  const minAllowed = innerRadius * 0.45;
  const maxAllowed = outerRadius * 1.25;
  ids.forEach((id) => {
    const p = points.get(id)!;
    const dx = p.x - center;
    const dy = p.y - center;
    const dist = Math.sqrt(dx * dx + dy * dy) || 0.001;
    if (dist < minAllowed || dist > maxAllowed) {
      const clamped = Math.min(Math.max(dist, minAllowed), maxAllowed);
      const ux = dx / dist;
      const uy = dy / dist;
      p.x = center + ux * clamped;
      p.y = center + uy * clamped;
    }
  });

  items.forEach((item) => {
    const p = points.get(item.event_id)!;
    result.set(item.event_id, {
      x: p.x,
      y: p.y,
      floatPhase: stableRandom(`${item.entity_id}:phase`) * Math.PI * 2,
      floatFreq: 0.85 + stableRandom(`${item.entity_id}:freq`) * 0.3,
    });
  });

  return result;
}
