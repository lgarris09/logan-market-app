import { render, screen } from "@testing-library/react-native";

import { AttentionBadge } from "../AttentionBadge";

// Same @expo/vector-icons mocking convention as ProfileAvatar.test.tsx.
jest.mock("@expo/vector-icons", () => {
  const { Text } = jest.requireActual("react-native");
  return { Ionicons: (props: { name: string }) => <Text>{`icon:${props.name}`}</Text> };
});

describe("AttentionBadge", () => {
  it("renders the judgment text, never a numeric percentage", () => {
    render(<AttentionBadge judgment="High attention" tone="high" />);

    expect(screen.getByText("High attention")).toBeTruthy();
    expect(screen.queryByText(/%/)).toBeNull();
  });

  it("renders each of the three consumer-facing states", () => {
    const { rerender } = render(<AttentionBadge judgment="Developing" tone="developing" />);
    expect(screen.getByText("Developing")).toBeTruthy();

    rerender(<AttentionBadge judgment="Worth a look" tone="worth-a-look" />);
    expect(screen.getByText("Worth a look")).toBeTruthy();

    rerender(<AttentionBadge judgment="High attention" tone="high" />);
    expect(screen.getByText("High attention")).toBeTruthy();
  });
});
