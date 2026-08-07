import { ReactNode } from "react";
import { render } from "@testing-library/react-native";

import { AttentionAtmosphere } from "../AttentionAtmosphere";
import { computeAtmosphereLayout } from "../../../lib/attentionLayout";
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
  };
}

describe("AttentionAtmosphere", () => {
  it("renders nothing until the field has real dimensions", () => {
    const items = [makeItem("a", 1)];
    const layouts = computeAtmosphereLayout(items);

    const { toJSON } = render(
      <AttentionAtmosphere items={items} layouts={layouts} width={0} height={0} />
    );

    expect(toJSON()).toBeNull();
  });

  it("caps rendered clouds regardless of feed size", () => {
    // Performance guard: the atmosphere is a fixed-cost ambient layer, not one
    // cloud per item -- a feed of 11 items (the real simulated fixture size)
    // must still only render MAX_CLOUDS (4) clouds, not 11.
    const items = Array.from({ length: 11 }, (_, i) => makeItem(`event-${i}`, i + 1));
    const layouts = computeAtmosphereLayout(items);

    const { getAllByTestId } = render(
      <AttentionAtmosphere items={items} layouts={layouts} width={390} height={844} />
    );

    // 1 haze circle + 2 circles per cloud (AtmosphereCloud's main lobe + secondary
    // lobe) -- 4 capped clouds -> 1 + 4*2 = 9, never 1 + 11*2 = 23.
    expect(getAllByTestId("Circle")).toHaveLength(9);
  });

  it("renders without crashing for an empty feed", () => {
    expect(() =>
      render(<AttentionAtmosphere items={[]} layouts={new Map()} width={390} height={844} />)
    ).not.toThrow();
  });
});
