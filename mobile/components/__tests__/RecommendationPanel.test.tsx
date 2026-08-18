import { render, screen } from "@testing-library/react-native";

import { RecommendationPanel } from "../RecommendationPanel";

// Same module-resolution workaround as app/__tests__/index.test.tsx --
// @expo/vector-icons pulls in expo-font -> expo-asset, which isn't hoisted
// to where Jest's module resolution can find it under this repo's npm
// install layout, unrelated to what this test verifies.
jest.mock("@expo/vector-icons", () => {
  const { Text } = jest.requireActual("react-native");
  return { Ionicons: (props: { name: string }) => <Text>{`icon:${props.name}`}</Text> };
});

// Sprint 3.6 (sections 9-14): the free/locked path is the only one reachable
// from any real backend response today (no DeliveredItem in the wild has a
// `recommendation`) -- this is the behavior the live app actually exercises.
// The unlocked path is tested too since it's the contract boundary the
// component is built against for when a real recommendation exists.
describe("RecommendationPanel", () => {
  it("renders a locked teaser, not fabricated content, when no recommendation exists", () => {
    render(<RecommendationPanel />);

    expect(screen.getByText("STRATUS RECOMMENDATION")).toBeTruthy();
    expect(screen.getByText("icon:lock-closed")).toBeTruthy();
    expect(screen.getByText(/STRATUS\+/)).toBeTruthy();
    // No risk/action language should appear without real data behind it.
    expect(screen.queryByText(/RECOMMENDATION RISK/)).toBeNull();
  });

  it("renders the action and a distinctly-labeled risk when a recommendation is present", () => {
    render(
      <RecommendationPanel
        recommendation={{
          action: "Wait for confirmation before entering.",
          risk: "moderate",
          whatWouldChangeThis: "Sustained breadth above the breakout level.",
        }}
      />
    );

    expect(screen.getByText("Wait for confirmation before entering.")).toBeTruthy();
    // Section 11: risk must never read as a bare "MODERATE" that could be
    // mistaken for the card's own confidence label -- always qualified.
    expect(screen.getByText("RECOMMENDATION RISK · MODERATE RISK")).toBeTruthy();
    expect(screen.getByText("WHAT WOULD CHANGE THIS")).toBeTruthy();
    expect(screen.getByText("Sustained breadth above the breakout level.")).toBeTruthy();
    expect(screen.queryByText("icon:lock-closed")).toBeNull();
  });

  it("omits the WHAT WOULD CHANGE THIS section when that detail isn't available", () => {
    render(
      <RecommendationPanel
        recommendation={{ action: "Consider a limited/small exposure.", risk: "speculative" }}
      />
    );

    expect(screen.queryByText("WHAT WOULD CHANGE THIS")).toBeNull();
    expect(screen.getByText("RECOMMENDATION RISK · SPECULATIVE")).toBeTruthy();
  });
});
