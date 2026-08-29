import { ReactNode } from "react";
import { render } from "@testing-library/react-native";

import { AttentionAtmosphere } from "../AttentionAtmosphere";
import { FeedItem } from "../../../types/loganFeed";

// @shopify/react-native-skia ships an ESM build that Jest's default
// transformIgnorePatterns doesn't cover, and its real implementation needs a
// native GPU context anyway -- neither is relevant to what this test verifies
// (the cloud count stays capped, dimensions-gating, no crashes), so the whole
// module is stubbed with no-op passthrough components.
jest.mock("@shopify/react-native-skia", () => {
  const { View } = jest.requireActual("react-native");
  const passthrough = (name: string) => {
    const Component = ({ children }: { children?: ReactNode }) => (
      <View testID={name}>{children}</View>
    );
    Component.displayName = name;
    return Component;
  };
  return {
    Canvas: passthrough("Canvas"),
    Circle: passthrough("Circle"),
    Group: passthrough("Group"),
    Rect: passthrough("Rect"),
    RadialGradient: passthrough("RadialGradient"),
    FractalNoise: passthrough("FractalNoise"),
    BlurMask: passthrough("BlurMask"),
    vec: (x: number, y: number) => ({ x, y }),
  };
});

function makeItem(id: string, rank: number): FeedItem {
  return {
    event_id: id,
    entity_id: id,
    display_name: id,
    category: "stocks",
    ticker: null,
    domain: "stocks",
    delivered_item: {
      event_id: id,
      surface: "wheel",
      headline: "",
      what_happened: "",
      why_it_matters: "",
      why_it_matters_to_me: "",
      why_now: "",
      confidence_label: "Moderate",
      confidence_score: 0.5,
      connected_items: [],
      required_disclaimers: [],
      delivered_at: "2026-08-06T00:00:00Z",
    },
    rank,
    confidence_score: 0.5,
    confidence_label: "Moderate",
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
    is_watched: false,
  };
}

describe("AttentionAtmosphere", () => {
  it("renders nothing until the field has real dimensions", () => {
    const items = [makeItem("a", 1)];

    const { toJSON } = render(<AttentionAtmosphere items={items} width={0} height={0} />);

    expect(toJSON()).toBeNull();
  });

  it("renders a fixed-cost ambient layer regardless of feed size", () => {
    // Sprint 3.6 (bubble-match pass): this used to also assert a capped
    // per-item "cloud" count -- those clouds sat directly behind the top
    // vessels and washed out Vessel.tsx's own hollow-centered bubble
    // gradient, so they were removed. What's left is one global haze
    // region, whose cost doesn't grow with feed size at all.
    const items = Array.from({ length: 11 }, (_, i) => makeItem(`event-${i}`, i + 1));

    const { getAllByTestId } = render(
      <AttentionAtmosphere items={items} width={390} height={844} />
    );

    expect(getAllByTestId("Circle")).toHaveLength(1);
  });

  it("renders without crashing for an empty feed", () => {
    expect(() => render(<AttentionAtmosphere items={[]} width={390} height={844} />)).not.toThrow();
  });
});
