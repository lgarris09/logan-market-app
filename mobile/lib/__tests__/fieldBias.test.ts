import { biasStateFor, categoryGroup } from "../fieldBias";
import { FeedItem } from "../../types/loganFeed";

function makeItem(category: string): FeedItem {
  return {
    event_id: "evt-1",
    entity_id: "ENT1",
    display_name: "Entity 1",
    category,
    ticker: "T1",
    domain: "markets",
    rank: 1,
    confidence_score: 0.7,
    confidence_label: "High",
    connected_event_ids: [],
    is_new_for_user: false,
    signal_type: "test_signal",
    lifecycle_state: null,
    is_updated: false,
    meaningful_change_type: null,
    lifecycle_reason: null,
    last_meaningful_change_at: null,
    thesis_age_hours: null,
    opportunity_revision: null,
    user_sync_status: null,
    trajectory: "STEADY",
    previous_trajectory: "STEADY",
    trajectory_reason: null,
    evidence: null,
    since_last_looked: null,
    delivered_item: {
      event_id: "evt-1",
      surface: "wheel",
      headline: "Headline",
      what_happened: "Something happened.",
      why_it_matters: "It matters.",
      why_it_matters_to_me: "It matters to you.",
      why_now: "Now is relevant.",
      confidence_label: "High",
      confidence_score: 0.7,
      connected_items: [],
      required_disclaimers: [],
      delivered_at: "2026-01-01T00:00:00Z",
    },
  };
}

// FIELD BIAS: a presentation lens, never a filter or a ranking change --
// these tests pin down the domain mapping (category -> group) and the
// resulting per-item visual state so that stays true.
describe("categoryGroup", () => {
  it("maps the real FeedItem.category taxonomy to Markets/Odds/Trends, same grouping as symbolResolver.ts's CATEGORY_COLORS", () => {
    expect(categoryGroup("stocks")).toBe("markets");
    expect(categoryGroup("commodities")).toBe("markets");
    expect(categoryGroup("technology")).toBe("markets");
    expect(categoryGroup("crypto")).toBe("markets");
    expect(categoryGroup("sports")).toBe("odds");
    expect(categoryGroup("prediction-markets")).toBe("odds");
    expect(categoryGroup("culture")).toBe("trends");
  });

  it("returns null for macro and any other unmapped category, never a guess", () => {
    expect(categoryGroup("macro")).toBeNull();
    expect(categoryGroup("some-future-category")).toBeNull();
  });
});

describe("biasStateFor", () => {
  it("is neutral for every item when no lens is active", () => {
    expect(biasStateFor(makeItem("stocks"), "all")).toBe("neutral");
    expect(biasStateFor(makeItem("macro"), "all")).toBe("neutral");
  });

  it("emphasizes an item whose group matches the active lens", () => {
    expect(biasStateFor(makeItem("stocks"), "markets")).toBe("emphasized");
    expect(biasStateFor(makeItem("sports"), "odds")).toBe("emphasized");
    expect(biasStateFor(makeItem("culture"), "trends")).toBe("emphasized");
  });

  it("recedes an item whose group does not match the active lens", () => {
    expect(biasStateFor(makeItem("sports"), "markets")).toBe("receded");
    expect(biasStateFor(makeItem("culture"), "odds")).toBe("receded");
  });

  it("keeps an unmapped category neutral under any active lens, never receded -- an item Logan never confidently grouped must not be penalized for not matching a lens it was never placed in", () => {
    expect(biasStateFor(makeItem("macro"), "markets")).toBe("neutral");
    expect(biasStateFor(makeItem("macro"), "odds")).toBe("neutral");
    expect(biasStateFor(makeItem("macro"), "trends")).toBe("neutral");
  });
});
