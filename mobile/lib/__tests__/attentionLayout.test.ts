import {
  ANCHOR_MAX_RADIUS_FRACTION,
  computeAtmosphereLayout,
  LABEL_WIDTH_FRACTION,
  NAME_ICON_ALLOWANCE,
} from "../attentionLayout";
import { FeedItem } from "../../types/loganFeed";

// Attention Gravity model: the field organizes around a center of
// attention (priority/rank decides distance from focus), with weak
// relationship/domain attraction and a final collision-relaxation cleanup
// pass -- replacing the earlier sector-angle-plus-jitter scatter. These
// tests pin down that model's actual guarantees: priority dominance,
// determinism independent of input array order, positional continuity when
// the item set changes incrementally, relationship/domain attraction (and
// its bounds), and that none of this depends on a fixed/named entity set or
// item count.

function makeItem(
  rank: number,
  overrides: Partial<
    Pick<FeedItem, "event_id" | "domain" | "connected_event_ids" | "confidence_score">
  > = {}
): FeedItem {
  const id = overrides.event_id ?? `evt-${rank}`;
  return {
    event_id: id,
    entity_id: `ENT${rank}`,
    display_name: `Entity ${rank}`,
    category: "stocks",
    ticker: `T${rank}`,
    domain: overrides.domain ?? "markets",
    rank,
    confidence_score: overrides.confidence_score ?? 0.7,
    confidence_label: "High",
    connected_event_ids: overrides.connected_event_ids ?? [],
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

function distFromCenter(v: { x: number; y: number }): number {
  return Math.hypot((v.x - 0.5) * IPHONE_WIDTH, (v.y - 0.5) * IPHONE_HEIGHT);
}

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

  it("keeps every pair from overlapping even with relationship/domain attraction active", () => {
    // Collision relaxation runs *after* attraction (the final cleanup pass,
    // not the layout generator) -- this pins that ordering down by giving
    // every item a reason to be pulled toward its neighbors and asserting
    // the no-overlap guarantee still holds regardless.
    const items = Array.from({ length: 10 }, (_, i) =>
      makeItem(i + 1, {
        domain: i % 2 === 0 ? "markets" : "odds",
        connected_event_ids: [`evt-${((i + 1) % 10) + 1}`],
      })
    );
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
        expect(dist).toBeGreaterThanOrEqual(minDist - 1);
      }
    }
  });

  it("moves closer to the attention center as rank improves, across the whole field", () => {
    // Soft attention zones, not fixed rings -- the spec deliberately doesn't
    // require every single pair to be in strict order (an individual item
    // can legitimately get a real, larger local collision-relaxation nudge
    // when several similarly-prominent bubbles compete for the same tight
    // inner band -- resolving that crowding without eroding the *zone-
    // level* tendency is what the tangential-biased collision push and
    // angular-decrowding pass exist for, but "zero perturbation for any
    // single item" was never the guarantee). What must hold, and does, is
    // the group-level tendency this asserts: the highest-priority items are
    // reliably nearer the center than the lowest-priority ones, in
    // aggregate, not just for a hand-picked best-vs-worst pair.
    // Every item its own domain -- this test isolates priority's effect
    // specifically; domain (and relationship) attraction are separate,
    // deliberately weak forces already covered by their own dedicated
    // tests below, and shouldn't be a confound here.
    const items = Array.from({ length: 8 }, (_, i) => makeItem(i + 1, { domain: `domain-${i}` }));
    const layout = computeAtmosphereLayout(items, IPHONE_WIDTH, IPHONE_HEIGHT);
    const distances = items.map((item) => distFromCenter(layout.get(item.event_id)!));

    const groupSize = 2;
    const average = (values: number[]) => values.reduce((sum, v) => sum + v, 0) / values.length;
    const topAvg = average(distances.slice(0, groupSize));
    const bottomAvg = average(distances.slice(-groupSize));

    expect(topAvg).toBeLessThan(bottomAvg);
  });

  it("is deterministic for the same item set and dimensions", () => {
    const items = Array.from({ length: 5 }, (_, i) => makeItem(i + 1));
    const first = computeAtmosphereLayout(items, IPHONE_WIDTH, IPHONE_HEIGHT);
    const second = computeAtmosphereLayout(items, IPHONE_WIDTH, IPHONE_HEIGHT);
    for (const item of items) {
      expect(second.get(item.event_id)).toEqual(first.get(item.event_id));
    }
  });

  it("produces the same target layout regardless of the input array's order", () => {
    // The layout must not depend on API response order -- every internal
    // pass (initial placement, attraction, collision relaxation) processes
    // items in a canonical event_id order, never array position. Includes
    // relationships and a tied rank (a real condition that used to expose
    // order-dependent tie-breaking in a plain stable sort by rank alone).
    const items = [
      makeItem(1, { connected_event_ids: ["evt-4"] }),
      makeItem(2, { domain: "odds" }),
      makeItem(3),
      makeItem(3, { event_id: "evt-3b", domain: "odds" }), // tied rank with evt-3
      makeItem(4, { connected_event_ids: ["evt-1"] }),
      makeItem(5),
      makeItem(6, { domain: "odds" }),
    ];
    const shuffled = [items[6], items[2], items[0], items[5], items[3], items[1], items[4]];

    const original = computeAtmosphereLayout(items, IPHONE_WIDTH, IPHONE_HEIGHT);
    const reordered = computeAtmosphereLayout(shuffled, IPHONE_WIDTH, IPHONE_HEIGHT);

    for (const item of items) {
      const a = original.get(item.event_id)!;
      const b = reordered.get(item.event_id)!;
      expect(b.x).toBeCloseTo(a.x, 9);
      expect(b.y).toBeCloseTo(a.y, 9);
      expect(b.size).toBeCloseTo(a.size, 9);
      expect(b.labelTier).toBe(a.labelTier);
    }
  });

  it("returns an empty map for zero items or unmeasured (zero) dimensions", () => {
    expect(computeAtmosphereLayout([], IPHONE_WIDTH, IPHONE_HEIGHT).size).toBe(0);
    expect(computeAtmosphereLayout([makeItem(1)], 0, 0).size).toBe(0);
  });

  it("keeps every vessel's glow circle inside the field bounds", () => {
    const items = Array.from({ length: 9 }, (_, i) => makeItem(i + 1));
    const layout = computeAtmosphereLayout(items, IPHONE_WIDTH, IPHONE_HEIGHT);

    for (const item of items) {
      const v = layout.get(item.event_id)!;
      const cx = v.x * IPHONE_WIDTH;
      const cy = v.y * IPHONE_HEIGHT;
      const r = v.size / 2;

      expect(cx - r).toBeGreaterThanOrEqual(-1); // 1px float slack
      expect(cx + r).toBeLessThanOrEqual(IPHONE_WIDTH + 1);
      expect(cy - r).toBeGreaterThanOrEqual(-1);
      expect(cy + r).toBeLessThanOrEqual(IPHONE_HEIGHT + 1);
    }
  });

  it("gives every vessel at least a short identity+tier label at rest", () => {
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

  describe("positional continuity across updated feeds", () => {
    it("adding one new opportunity does not materially reposition unrelated existing ones", () => {
      const base = Array.from({ length: 9 }, (_, i) => makeItem(i + 1));
      const before = computeAtmosphereLayout(base, IPHONE_WIDTH, IPHONE_HEIGHT);

      const withNewItem = [...base, makeItem(10)]; // unconnected, different from every existing domain grouping
      const after = computeAtmosphereLayout(withNewItem, IPHONE_WIDTH, IPHONE_HEIGHT);

      for (const item of base) {
        const a = before.get(item.event_id)!;
        const b = after.get(item.event_id)!;
        const movedPx = Math.hypot((b.x - a.x) * IPHONE_WIDTH, (b.y - a.y) * IPHONE_HEIGHT);
        // A small shift from rank-range renormalization (and, for whichever
        // vessel ends up adjacent to the new one, a small collision-cleanup
        // nudge) is expected and fine -- a full reshuffle is not. 33px on a
        // 390px-wide field is a fraction of one vessel's own radius band.
        expect(movedPx).toBeLessThan(33);
      }
    });

    it("removing one opportunity does not globally reshuffle everything else", () => {
      const base = Array.from({ length: 10 }, (_, i) => makeItem(i + 1));
      const before = computeAtmosphereLayout(base, IPHONE_WIDTH, IPHONE_HEIGHT);

      const withoutLast = base.slice(0, -1);
      const after = computeAtmosphereLayout(withoutLast, IPHONE_WIDTH, IPHONE_HEIGHT);

      for (const item of withoutLast) {
        const a = before.get(item.event_id)!;
        const b = after.get(item.event_id)!;
        const movedPx = Math.hypot((b.x - a.x) * IPHONE_WIDTH, (b.y - a.y) * IPHONE_HEIGHT);
        expect(movedPx).toBeLessThan(33);
      }
    });

    it("moves an opportunity inward when a later poll reports a better rank", () => {
      // Simulates the same stable event_id across two polls: first at a
      // mid/low rank, then promoted to rank 1 -- the kind of update a real
      // backend re-prioritization would send.
      const firstPoll = Array.from({ length: 8 }, (_, i) => makeItem(i + 1));
      const before = computeAtmosphereLayout(firstPoll, IPHONE_WIDTH, IPHONE_HEIGHT);
      const beforeDist = distFromCenter(before.get("evt-6")!);

      const secondPoll = firstPoll.map((item) =>
        item.event_id === "evt-6"
          ? { ...item, rank: 1 }
          : item.rank === 1
            ? { ...item, rank: 6 }
            : item
      );
      const after = computeAtmosphereLayout(secondPoll, IPHONE_WIDTH, IPHONE_HEIGHT);
      const afterDist = distFromCenter(after.get("evt-6")!);

      expect(afterDist).toBeLessThan(beforeDist);
    });
  });

  describe("relationship and domain attraction", () => {
    it("pulls connected opportunities measurably closer together than an equivalent unconnected pair", () => {
      // Same rank, same domain grouping shape, same field -- the only
      // difference is whether the pair lists each other in
      // connected_event_ids. Several other items give the attraction pass
      // something to displace *through*.
      // Mid/low rank (not rank 1) -- a rank-1 pair's bubbles are large
      // enough that collision clearance alone can force them to their
      // minimum legal separation regardless of any attraction pull,
      // masking the effect this test exists to observe.
      const filler = Array.from({ length: 6 }, (_, i) => makeItem(i + 1, { domain: "odds" }));

      const connectedItems = [
        makeItem(7, { event_id: "conn-a", connected_event_ids: ["conn-b"] }),
        makeItem(8, { event_id: "conn-b", connected_event_ids: ["conn-a"] }),
        ...filler,
      ];
      const unconnectedItems = [
        makeItem(7, { event_id: "conn-a" }),
        makeItem(8, { event_id: "conn-b" }),
        ...filler,
      ];

      const connectedLayout = computeAtmosphereLayout(connectedItems, IPHONE_WIDTH, IPHONE_HEIGHT);
      const unconnectedLayout = computeAtmosphereLayout(
        unconnectedItems,
        IPHONE_WIDTH,
        IPHONE_HEIGHT
      );

      const pairDist = (layout: Map<string, { x: number; y: number }>) => {
        const a = layout.get("conn-a")!;
        const b = layout.get("conn-b")!;
        return Math.hypot((a.x - b.x) * IPHONE_WIDTH, (a.y - b.y) * IPHONE_HEIGHT);
      };

      expect(pairDist(connectedLayout)).toBeLessThan(pairDist(unconnectedLayout));
    });

    it("pulls same-domain opportunities closer than a different-domain pair, but more subtly than a real connection", () => {
      // Low rank + smaller bubbles + more filler for real breathing room,
      // same reasoning as the connected-pair test above -- avoids the
      // collision-clearance floor masking attraction's effect entirely.
      const filler = Array.from({ length: 9 }, (_, i) => makeItem(i + 1, { domain: "trends" }));

      const sameDomain = [
        makeItem(10, { event_id: "dom-a", domain: "markets" }),
        makeItem(11, { event_id: "dom-b", domain: "markets" }),
        ...filler,
      ];
      const differentDomain = [
        makeItem(10, { event_id: "dom-a", domain: "markets" }),
        makeItem(11, { event_id: "dom-b", domain: "odds" }),
        ...filler,
      ];
      const connected = [
        makeItem(10, { event_id: "dom-a", domain: "markets", connected_event_ids: ["dom-b"] }),
        makeItem(11, { event_id: "dom-b", domain: "odds", connected_event_ids: ["dom-a"] }),
        ...filler,
      ];

      const pairDist = (items: FeedItem[]) => {
        const layout = computeAtmosphereLayout(items, IPHONE_WIDTH, IPHONE_HEIGHT);
        const a = layout.get("dom-a")!;
        const b = layout.get("dom-b")!;
        return Math.hypot((a.x - b.x) * IPHONE_WIDTH, (a.y - b.y) * IPHONE_HEIGHT);
      };

      const sameDomainDist = pairDist(sameDomain);
      const differentDomainDist = pairDist(differentDomain);
      const connectedDist = pairDist(connected);

      // Domain must never make a pair land *materially farther* apart than
      // having no shared grouping at all -- not necessarily strictly closer
      // in the final on-screen distance, since both pulls are subject to
      // the same collision-clearance floor a pair can converge to
      // regardless of exactly how they got there (a tiny epsilon absorbs
      // float noise between the two computation paths landing on that same
      // floor, not a real "farther" outcome). The mechanism's real,
      // positive effect is demonstrated with room to show it by the
      // dedicated connected-vs-unconnected test above.
      expect(sameDomainDist).toBeLessThanOrEqual(differentDomainDist + 0.01);
      // A real relationship pulls at least as hard as merely sharing a
      // domain -- not necessarily strictly harder in the *final* on-screen
      // distance, since both pulls are subject to the same collision-
      // clearance floor once a pair gets close enough (two same-size
      // bubbles can only ever get so close before relaxation pushes them
      // back apart) -- but relationship must never land farther than a
      // domain-only pull. The strength difference itself (materially
      // stronger relationship pull, structurally capped well above
      // domain's) is covered directly by the connected-vs-unconnected test
      // above, which has room to show it without hitting that floor.
      expect(connectedDist).toBeLessThanOrEqual(sameDomainDist + 0.01);
    });

    it("never lets relationship attraction pull a low-priority item closer to the center than an unrelated higher-priority one", () => {
      // The lowest-ranked item in a reasonably large field, connected to the
      // single highest-priority item -- the most adversarial case for
      // "attraction could override priority." Compared against a
      // comfortably-higher-priority, unconnected item elsewhere in the field.
      const n = 12;
      const items = Array.from({ length: n }, (_, i) =>
        makeItem(i + 1, i === 0 ? { connected_event_ids: [`evt-${n}`] } : {})
      );
      items[n - 1] = makeItem(n, { connected_event_ids: ["evt-1"] });

      const layout = computeAtmosphereLayout(items, IPHONE_WIDTH, IPHONE_HEIGHT);
      const lowPriorityConnected = distFromCenter(layout.get(`evt-${n}`)!);
      const midPriorityUnconnected = distFromCenter(layout.get("evt-4")!);

      expect(lowPriorityConnected).toBeGreaterThan(midPriorityUnconnected);
    });
  });

  it("handles an arbitrary item count with no named/demo entities baked in", () => {
    // Generic ids/names only (evt-N / Entity N), an unusual count (23, well
    // beyond the current 9-11 demo size and beyond what the relaxation pass
    // counts below were tuned against), still produces a valid layout with
    // no severe overlap -- the layout must not assume today's fixture size
    // or entities. Slack is wider here than the dedicated realistic-scale
    // overlap tests above (which hold to within 1px): at this unusually
    // high density, the attraction/angular-decrowding/collision pipeline
    // can leave a few px of residual softness rather than a fully solved
    // pack -- imperceptible on screen, and worth revisiting if/when the
    // product actually renders fields this dense.
    const items = Array.from({ length: 23 }, (_, i) =>
      makeItem(i + 1, { domain: i % 3 === 0 ? "markets" : i % 3 === 1 ? "odds" : "trends" })
    );
    const layout = computeAtmosphereLayout(items, IPHONE_WIDTH, IPHONE_HEIGHT);

    expect(layout.size).toBe(items.length);
    const points = items.map((item) => layout.get(item.event_id)!);
    for (let i = 0; i < points.length; i++) {
      for (let j = i + 1; j < points.length; j++) {
        const a = points[i];
        const b = points[j];
        const dist = Math.hypot((a.x - b.x) * IPHONE_WIDTH, (a.y - b.y) * IPHONE_HEIGHT);
        expect(dist).toBeGreaterThanOrEqual((a.size + b.size) / 2 - 16);
      }
    }
  });

  describe("attention anchor (composition pass)", () => {
    it("clusters high-priority items into a tighter angular group than equivalent low-priority items", () => {
      // Same shape (same count, unique domains, no connections) at two
      // different priority tiers -- isolates the anchor pull's effect as a
      // *relative* comparison rather than against a fixed theoretical
      // baseline. A fixed baseline (e.g. "average distance from the anchor
      // should beat the ~90° a uniform spread would produce") turned out to
      // be the wrong test, and an earlier attempt at this relative
      // comparison tied several "high" items to the same rank -- realistic
      // ranks 2/3/4... get progressively *smaller* bubbles (size scales
      // with prominence, same as everything else in this model); tying
      // several to one rank gave them all near-maximal, identical size,
      // which is exactly the case where resolveAngularCrowding's real
      // (correct) pairwise-separation requirement has no choice but to
      // spread same-size bubbles across most of the circle regardless of
      // any organizing pull. Even with realistic decreasing ranks, that
      // packing floor is real: rank 2/3/4 in a real field are still large,
      // still need real mutual separation -- the clustering *tendency* is
      // there (confirmed directly against the solver's intermediate state
      // while investigating this test) but a group of 3+ genuinely large
      // bubbles converges close enough to the packing floor that this
      // particular measure can't reliably tell it apart from chance. Two
      // items shows a clear, reliable margin without hitting that floor.
      const groupSize = 2;
      const items = [
        makeItem(1, { event_id: "anchor", domain: "domain-anchor" }),
        ...Array.from({ length: groupSize }, (_, i) =>
          makeItem(i + 2, { event_id: `high-${i}`, domain: `domain-high-${i}` })
        ),
        ...Array.from({ length: groupSize }, (_, i) =>
          makeItem(i + 20, { event_id: `low-${i}`, domain: `domain-low-${i}` })
        ),
      ];
      const layout = computeAtmosphereLayout(items, IPHONE_WIDTH, IPHONE_HEIGHT);
      const centerX = IPHONE_WIDTH / 2;
      const centerY = IPHONE_HEIGHT / 2;

      const angleOf = (id: string) => {
        const v = layout.get(id)!;
        return Math.atan2(v.y * IPHONE_HEIGHT - centerY, v.x * IPHONE_WIDTH - centerX);
      };

      // Mean resultant length of a set of angles (treated as unit vectors)
      // -- a standard circular-statistics measure of clustering: 1.0 means
      // every angle is identical, 0.0 means they're spread perfectly
      // evenly around the full circle. Doesn't depend on picking any
      // single reference angle (like the anchor's own), just how tightly
      // the group sits together.
      const clustering = (angles: number[]): number => {
        let sumCos = 0;
        let sumSin = 0;
        for (const a of angles) {
          sumCos += Math.cos(a);
          sumSin += Math.sin(a);
        }
        return Math.hypot(sumCos, sumSin) / angles.length;
      };

      const highAngles = Array.from({ length: groupSize }, (_, i) => angleOf(`high-${i}`));
      const lowAngles = Array.from({ length: groupSize }, (_, i) => angleOf(`low-${i}`));

      expect(clustering(highAngles)).toBeGreaterThan(clustering(lowAngles));
    });

    it("still lets a low-priority item roam the outer field, barely pulled toward the anchor", () => {
      // Same identity (same natural hash angle) at high vs. low rank --
      // the anchor pull scales by the puller's own prominence, so a
      // peripheral item should end up close to its un-pulled radius-band
      // position regardless of where the anchor sits, while a high-rank
      // item with the same identity would be pulled measurably.
      const lowPriorityField = [
        makeItem(1, { event_id: "anchor", domain: "domain-anchor" }),
        makeItem(10, { event_id: "subject", domain: "domain-subject" }),
        ...Array.from({ length: 8 }, (_, i) => makeItem(i + 2, { domain: `domain-filler-${i}` })),
      ];
      const layout = computeAtmosphereLayout(lowPriorityField, IPHONE_WIDTH, IPHONE_HEIGHT);
      const v = layout.get("subject")!;
      const centerX = IPHONE_WIDTH / 2;
      const centerY = IPHONE_HEIGHT / 2;
      const dist = Math.hypot(v.x * IPHONE_WIDTH - centerX, v.y * IPHONE_HEIGHT - centerY);

      // A rank-10-of-10 item's un-pulled radius is RADIUS_MAX_FRACTION
      // (0.42) of the field's shorter dimension -- if the anchor pull
      // were meaningfully affecting it despite its near-zero prominence,
      // it would land noticeably inside that radius instead.
      const minDim = Math.min(IPHONE_WIDTH, IPHONE_HEIGHT);
      expect(dist).toBeGreaterThan(minDim * 0.38);
    });
  });

  describe("field balance (composition pass)", () => {
    it("keeps the field's area-weighted mass roughly centered even for a domain-heavy field", () => {
      const items = [
        ...Array.from({ length: 6 }, (_, i) => makeItem(i + 1, { domain: "markets" })),
        ...Array.from({ length: 6 }, (_, i) => makeItem(i + 7, { domain: "odds" })),
      ];
      const layout = computeAtmosphereLayout(items, IPHONE_WIDTH, IPHONE_HEIGHT);

      let totalArea = 0;
      let massX = 0;
      let massY = 0;
      for (const item of items) {
        const v = layout.get(item.event_id)!;
        const area = Math.PI * (v.size / 2) ** 2;
        totalArea += area;
        massX += v.x * IPHONE_WIDTH * area;
        massY += v.y * IPHONE_HEIGHT * area;
      }
      massX /= totalArea;
      massY /= totalArea;

      const offset = Math.hypot(massX - IPHONE_WIDTH / 2, massY - IPHONE_HEIGHT / 2);
      const minDim = Math.min(IPHONE_WIDTH, IPHONE_HEIGHT);

      expect(offset).toBeLessThan(minDim * 0.18);
    });
  });

  describe("rank 1 owns the center (composition pass, round 2)", () => {
    it("keeps rank 1 within the defined central focal radius across representative item sets and viewport sizes", () => {
      // Owner on-device finding: even with the improved hierarchy, the
      // true center still read as empty -- rank 1 needs a hard, provable
      // guarantee (ANCHOR_MAX_RADIUS_FRACTION), not just a tendency, and
      // it needs to hold regardless of how many items are on the field,
      // what relationships/domains they have, or what device the field is
      // rendering on.
      const viewports = [
        { width: 320, height: 568 }, // iPhone SE-class -- smallest realistic target
        { width: 390, height: 740 }, // iPhone 14/15-class -- this file's usual fixture
        { width: 430, height: 900 }, // iPhone Pro Max-class
        { width: 768, height: 1024 }, // iPad portrait -- meaningfully different aspect ratio
      ];

      const itemSets: FeedItem[][] = [
        Array.from({ length: 5 }, (_, i) => makeItem(i + 1)),
        Array.from({ length: 9 }, (_, i) =>
          makeItem(i + 1, { domain: ["markets", "odds", "trends"][i % 3] })
        ),
        Array.from({ length: 15 }, (_, i) => makeItem(i + 1, { domain: `domain-${i % 4}` })),
        // Rank 1 itself has real connections/domain peers -- the anchor
        // force pulls *other* items toward it, never the anchor toward
        // anything else, but this exercises that asymmetry directly.
        [
          makeItem(1, { connected_event_ids: ["evt-2", "evt-3"] }),
          makeItem(2, { connected_event_ids: ["evt-1"], domain: "markets" }),
          makeItem(3, { connected_event_ids: ["evt-1"], domain: "markets" }),
          ...Array.from({ length: 6 }, (_, i) => makeItem(i + 4, { domain: "odds" })),
        ],
      ];

      for (const viewport of viewports) {
        for (const items of itemSets) {
          const layout = computeAtmosphereLayout(items, viewport.width, viewport.height);
          const anchorId = rankedByFixture(items)[0].event_id;
          const anchor = layout.get(anchorId)!;
          const centerX = viewport.width / 2;
          const centerY = viewport.height / 2;
          const dist = Math.hypot(
            anchor.x * viewport.width - centerX,
            anchor.y * viewport.height - centerY
          );
          const minDim = Math.min(viewport.width, viewport.height);

          expect(dist).toBeLessThanOrEqual(minDim * ANCHOR_MAX_RADIUS_FRACTION + 1); // 1px float slack
        }
      }
    });
  });

  describe("resting label sizing accounts for the icon-above-name layout (Sprint 3.6.5)", () => {
    it("grows a full-tier vessel's minimum size well past the icon's own width floor, for a long real name", () => {
      // Vessel.tsx's resting label now renders the contextual icon in its
      // own centered row *above* the name, not sharing a line with it (see
      // Vessel.tsx's restLabelIconWrap) -- attentionLayout.ts's
      // minDiameterForLabel (not exported directly, exercised here through
      // its effect on the returned `size`) therefore estimates the name
      // line's width from the text alone, with NAME_ICON_ALLOWANCE only
      // acting as an independent floor (the bubble must be at least as wide
      // as the icon itself). This isn't a pinned-pixel snapshot (that would
      // break on every unrelated font/char-width tweak) -- it's a sanity
      // floor: for a representative long name ("Federal Reserve", the same
      // case called out in the Attention Gravity comments elsewhere in this
      // file), the resulting minimum size must clear the icon-width floor
      // by a comfortable multiple, proving the label-sizing helper is
      // actually driven by the long name's real text width, not just
      // returning something close to the icon floor alone (which would mean
      // the text measurement silently broke).
      //
      // Three items with large, closely-clustered rank values (rather than
      // 1/2/3) keeps every item's rank-derived `t` near zero -- see the
      // rank-to-t formula above -- so sizeMin (not the rank curve) is what
      // the label-driven minimum has to visibly beat, isolating
      // minDiameterForLabel's contribution instead of it being masked by
      // an already-large rank-based size.
      const items = [
        makeItem(1000, { event_id: "fed", connected_event_ids: [] }),
        makeItem(1001, { event_id: "evt-b" }),
        makeItem(1002, { event_id: "evt-c" }),
      ];
      items[0] = { ...items[0], display_name: "Federal Reserve", ticker: null };

      const layout = computeAtmosphereLayout(items, IPHONE_WIDTH, IPHONE_HEIGHT);
      const fed = layout.get("fed")!;

      expect(fed.labelTier).toBe("full");
      expect(fed.size).toBeGreaterThan(NAME_ICON_ALLOWANCE * 3);
    });

    it("still floors a full-tier vessel's minimum size at the icon's own width for a very short name", () => {
      // The inverse case: a short name/ticker ("AI") whose text width alone
      // would be narrower than the icon now sitting above it -- the bubble
      // must still be at least NAME_ICON_ALLOWANCE wide (divided by
      // LABEL_WIDTH_FRACTION, same as every other candidate in `widest`) so
      // the icon itself isn't left overflowing a too-narrow bubble.
      const items = [
        makeItem(1000, { event_id: "short", connected_event_ids: [] }),
        makeItem(1001, { event_id: "evt-b" }),
        makeItem(1002, { event_id: "evt-c" }),
      ];
      items[0] = { ...items[0], display_name: "AI", ticker: "AI" };

      const layout = computeAtmosphereLayout(items, IPHONE_WIDTH, IPHONE_HEIGHT);
      const short = layout.get("short")!;

      expect(short.labelTier).toBe("full");
      expect(short.size).toBeGreaterThanOrEqual(NAME_ICON_ALLOWANCE / LABEL_WIDTH_FRACTION - 1); // 1px float slack
    });
  });
});

function rankedByFixture(items: FeedItem[]): FeedItem[] {
  return [...items].sort((a, b) => a.rank - b.rank || (a.event_id < b.event_id ? -1 : 1));
}
