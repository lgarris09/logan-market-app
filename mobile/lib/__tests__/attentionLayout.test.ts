import { computeAtmosphereLayout } from "../attentionLayout";
import { FeedItem } from "../../types/loganFeed";

// Sprint 3.5 device-validation finding: on real iPhone dimensions, vessels
// rendered close enough together to read as one clustered blob rather than
// distinct opportunities. These tests pin down the fix (sector-based angle
// assignment + relaxation pass, sized relative to the real field) so it
// can't silently regress back to unconstrained-random placement.

function makeItem(rank: number): FeedItem {
  const id = `evt-${rank}`;
  return {
    event_id: id,
    entity_id: `ENT${rank}`,
    display_name: `Entity ${rank}`,
    category: "stocks",
    ticker: `T${rank}`,
    domain: "markets",
    rank,
    confidence_score: 0.7,
    confidence_label: "High",
    connected_event_ids: [],
    is_new_for_user: false,
    signal_type: "test_signal",
    delivered_item: {
      event_id: id,
      surface: "wheel",
      headline: `Headline ${rank}`,
      what_happened: "Something happened.",
      why_it_matters: "It matters.",
      why_it_matters_to_me: "It matters to you.",
      why_now: "Now is relevant.",
      confidence_label: "High",
      confidence_score: 0.7,
      connected_items: [],
      required_disclaimers: ["Not financial advice."],
      delivered_at: new Date().toISOString(),
    },
  };
}

// Realistic iPhone portrait dimensions (iPhone 14/15-class), field height net
// of the top bar/tab bar.
const IPHONE_WIDTH = 390;
const IPHONE_HEIGHT = 740;

describe("computeAtmosphereLayout", () => {
  it("returns an entry per item, all within the [0,1] field fraction", () => {
    const items = Array.from({ length: 8 }, (_, i) => makeItem(i + 1));
    const layout = computeAtmosphereLayout(items, IPHONE_WIDTH, IPHONE_HEIGHT);

    expect(layout.size).toBe(items.length);
    for (const item of items) {
      const v = layout.get(item.event_id)!;
      expect(v).toBeDefined();
      expect(v.x).toBeGreaterThanOrEqual(0);
      expect(v.x).toBeLessThanOrEqual(1);
      expect(v.y).toBeGreaterThanOrEqual(0);
      expect(v.y).toBeLessThanOrEqual(1);
    }
  });

  it("keeps every pair of vessels from visually overlapping on iPhone dimensions", () => {
    const items = Array.from({ length: 9 }, (_, i) => makeItem(i + 1));
    const layout = computeAtmosphereLayout(items, IPHONE_WIDTH, IPHONE_HEIGHT);
    const points = items.map((item) => layout.get(item.event_id)!);

    for (let i = 0; i < points.length; i++) {
      for (let j = i + 1; j < points.length; j++) {
        const a = points[i];
        const b = points[j];
        const dx = (a.x - b.x) * IPHONE_WIDTH;
        const dy = (a.y - b.y) * IPHONE_HEIGHT;
        const dist = Math.hypot(dx, dy);
        const minDist = (a.size + b.size) / 2;
        expect(dist).toBeGreaterThanOrEqual(minDist - 1); // -1px float slack
      }
    }
  });

  it("gives the highest-priority item the smallest resting radius from center", () => {
    const items = Array.from({ length: 6 }, (_, i) => makeItem(i + 1));
    const layout = computeAtmosphereLayout(items, IPHONE_WIDTH, IPHONE_HEIGHT);

    const distFromCenter = (eventId: string) => {
      const v = layout.get(eventId)!;
      return Math.hypot((v.x - 0.5) * IPHONE_WIDTH, (v.y - 0.5) * IPHONE_HEIGHT);
    };

    const rank1Dist = distFromCenter("evt-1");
    const lastRankDist = distFromCenter(`evt-${items.length}`);
    expect(rank1Dist).toBeLessThan(lastRankDist);
  });

  it("is deterministic for the same item set and dimensions", () => {
    const items = Array.from({ length: 5 }, (_, i) => makeItem(i + 1));
    const first = computeAtmosphereLayout(items, IPHONE_WIDTH, IPHONE_HEIGHT);
    const second = computeAtmosphereLayout(items, IPHONE_WIDTH, IPHONE_HEIGHT);
    for (const item of items) {
      expect(second.get(item.event_id)).toEqual(first.get(item.event_id));
    }
  });

  it("returns an empty map for zero items or unmeasured (zero) dimensions", () => {
    expect(computeAtmosphereLayout([], IPHONE_WIDTH, IPHONE_HEIGHT).size).toBe(0);
    expect(computeAtmosphereLayout([makeItem(1)], 0, 0).size).toBe(0);
  });

  it("keeps every vessel's full footprint (glow + label) inside the field bounds", () => {
    // V3.1.4.2 (real-device screenshot review): vessels/labels could extend
    // past the screen edge because the old clamp used a flat fraction
    // regardless of a vessel's actual size or label height. This mirrors
    // Vessel.tsx's own footprint math (label hangs below the glow only).
    const items = Array.from({ length: 9 }, (_, i) => makeItem(i + 1));
    const layout = computeAtmosphereLayout(items, IPHONE_WIDTH, IPHONE_HEIGHT);

    // Mirrors lib/attentionLayout.ts's FULL_LABEL_HEIGHT/COMPACT_LABEL_HEIGHT/
    // LABEL_WIDTH -- taller now (name + real confidence percentage + real
    // signal_type descriptor, three lines instead of two) per the owner's
    // Field Bias reference.
    const footprintHeight = (tier: string) => (tier === "none" ? 0 : tier === "full" ? 47 : 40);
    const footprintWidth = (tier: string, size: number) =>
      Math.max(size, tier === "none" ? 0 : 118);

    for (const item of items) {
      const v = layout.get(item.event_id)!;
      const cx = v.x * IPHONE_WIDTH;
      const cy = v.y * IPHONE_HEIGHT;
      const halfW = footprintWidth(v.labelTier, v.size) / 2;
      const topH = v.size / 2;
      const bottomH = v.size / 2 + footprintHeight(v.labelTier);

      expect(cx - halfW).toBeGreaterThanOrEqual(-1); // 1px float slack
      expect(cx + halfW).toBeLessThanOrEqual(IPHONE_WIDTH + 1);
      expect(cy - topH).toBeGreaterThanOrEqual(-1);
      expect(cy + bottomH).toBeLessThanOrEqual(IPHONE_HEIGHT + 1);
    }
  });

  it("gives every vessel at least a short identity+tier label at rest", () => {
    // V3.1.4.2 brand correction pass: the reference shows no descriptor text
    // on any vessel -- full/compact tiers now render identical content
    // (identity + confidence tier only); "none" is reserved for feed sizes
    // well beyond what's been designed for.
    const items = Array.from({ length: 9 }, (_, i) => makeItem(i + 1));
    const layout = computeAtmosphereLayout(items, IPHONE_WIDTH, IPHONE_HEIGHT);

    expect(layout.get("evt-1")!.labelTier).toBe("full");
    expect(layout.get("evt-2")!.labelTier).toBe("full");
    expect(layout.get("evt-3")!.labelTier).toBe("full");
    expect(layout.get("evt-4")!.labelTier).toBe("compact");
    expect(layout.get("evt-6")!.labelTier).toBe("compact");
    expect(layout.get("evt-7")!.labelTier).toBe("compact");
    expect(layout.get("evt-9")!.labelTier).toBe("compact");
  });

  it("keeps labeled vessels' occupied rectangles (glow + label) from overlapping", () => {
    // The old check only accounted for glow diameter -- labels could still
    // collide even when glows didn't. This reconstructs each labeled
    // vessel's real footprint (label hangs below the glow, never above) and
    // asserts no two rectangles intersect.
    const items = Array.from({ length: 9 }, (_, i) => makeItem(i + 1));
    const layout = computeAtmosphereLayout(items, IPHONE_WIDTH, IPHONE_HEIGHT);
    const points = items.map((item) => layout.get(item.event_id)!);

    // Mirrors lib/attentionLayout.ts's FULL_LABEL_HEIGHT/COMPACT_LABEL_HEIGHT/
    // LABEL_WIDTH -- taller now (name + real confidence percentage + real
    // signal_type descriptor, three lines instead of two) per the owner's
    // Field Bias reference.
    const footprintHeight = (tier: string) => (tier === "none" ? 0 : tier === "full" ? 47 : 40);
    const footprintWidth = (tier: string, size: number) =>
      Math.max(size, tier === "none" ? 0 : 118);

    for (let i = 0; i < points.length; i++) {
      for (let j = i + 1; j < points.length; j++) {
        const a = points[i];
        const b = points[j];
        const ax = a.x * IPHONE_WIDTH;
        const ay = a.y * IPHONE_HEIGHT;
        const bx = b.x * IPHONE_WIDTH;
        const by = b.y * IPHONE_HEIGHT;

        const aBox = {
          left: ax - footprintWidth(a.labelTier, a.size) / 2,
          right: ax + footprintWidth(a.labelTier, a.size) / 2,
          top: ay - a.size / 2,
          bottom: ay + a.size / 2 + footprintHeight(a.labelTier),
        };
        const bBox = {
          left: bx - footprintWidth(b.labelTier, b.size) / 2,
          right: bx + footprintWidth(b.labelTier, b.size) / 2,
          top: by - b.size / 2,
          bottom: by + b.size / 2 + footprintHeight(b.labelTier),
        };

        const overlapX = Math.min(aBox.right, bBox.right) - Math.max(aBox.left, bBox.left);
        const overlapY = Math.min(aBox.bottom, bBox.bottom) - Math.max(aBox.top, bBox.top);
        const bothOverlap = overlapX > 1 && overlapY > 1; // 1px float slack
        expect(bothOverlap).toBe(false);
      }
    }
  });
});
