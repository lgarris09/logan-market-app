import { fireEvent, render, screen, waitFor } from "@testing-library/react-native";

import LearningControlsScreen from "../learning";
import { getLearningSummary, suppressLearningReason } from "../../lib/learningControls";

jest.mock("@expo/vector-icons", () => {
  const { Text } = jest.requireActual("react-native");
  return { Ionicons: (props: { name: string }) => <Text>{`icon:${props.name}`}</Text> };
});

jest.mock("../../lib/learningControls", () => ({
  getLearningSummary: jest.fn(),
  suppressLearningReason: jest.fn(),
}));

const mockGetSummary = getLearningSummary as jest.Mock;
const mockSuppress = suppressLearningReason as jest.Mock;

const EXPLANATION =
  "This reflects only what you've explicitly told STRATUS or how you've used the app.";

describe("LearningControlsScreen", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it("shows neither content nor a failure message while the summary is still loading", () => {
    mockGetSummary.mockReturnValue(new Promise(() => {})); // never resolves
    render(<LearningControlsScreen />);

    expect(screen.queryByText("What STRATUS has learned")).toBeNull();
    expect(screen.queryByText(/Couldn.t load this right now/)).toBeNull();
    expect(screen.queryByText("Nothing learned yet")).toBeNull();
  });

  it("renders traits with the explicit/inferred distinction once loaded", async () => {
    mockGetSummary.mockResolvedValueOnce({
      generatedAt: "2026-09-04T12:00:00Z",
      traits: [
        {
          entityId: "AAPL",
          description: "You tend to care more about AAPL than most stocks STRATUS tracks.",
          basis: "explicit",
          canSuppress: true,
        },
        {
          entityId: "TSLA",
          description: "STRATUS has noticed a pattern of returning to TSLA.",
          basis: "inferred",
          canSuppress: true,
        },
      ],
      explanation: EXPLANATION,
    });

    render(<LearningControlsScreen />);

    await waitFor(() =>
      expect(
        screen.getByText("You tend to care more about AAPL than most stocks STRATUS tracks.")
      ).toBeTruthy()
    );
    expect(screen.getByText("STRATUS has noticed a pattern of returning to TSLA.")).toBeTruthy();
    expect(screen.getByText("You told STRATUS this")).toBeTruthy();
    expect(screen.getByText("Noticed from your activity")).toBeTruthy();
    expect(screen.getByText(EXPLANATION)).toBeTruthy();
  });

  it("shows an honest empty state for a fresh user with nothing learned yet", async () => {
    mockGetSummary.mockResolvedValueOnce({
      generatedAt: "2026-09-04T12:00:00Z",
      traits: [],
      explanation: EXPLANATION,
    });

    render(<LearningControlsScreen />);

    await waitFor(() => expect(screen.getByText("Nothing learned yet")).toBeTruthy());
  });

  it("shows a friendly failure state when the summary fails to load, with a retry", async () => {
    mockGetSummary.mockResolvedValueOnce(null);

    render(<LearningControlsScreen />);

    await waitFor(() => expect(screen.getByText(/Couldn.t load this right now/)).toBeTruthy());
    expect(screen.getByText("Try again")).toBeTruthy();

    mockGetSummary.mockResolvedValueOnce({
      generatedAt: "2026-09-04T12:00:00Z",
      traits: [],
      explanation: EXPLANATION,
    });
    fireEvent.press(screen.getByText("Try again"));

    await waitFor(() => expect(screen.getByText("Nothing learned yet")).toBeTruthy());
    expect(mockGetSummary).toHaveBeenCalledTimes(2);
  });

  it("calls suppressLearningReason with the trait's entity id and refreshes the list on success", async () => {
    mockGetSummary.mockResolvedValueOnce({
      generatedAt: "2026-09-04T12:00:00Z",
      traits: [
        {
          entityId: "AAPL",
          description: "You tend to care more about AAPL than most stocks STRATUS tracks.",
          basis: "explicit",
          canSuppress: true,
        },
      ],
      explanation: EXPLANATION,
    });
    mockSuppress.mockResolvedValueOnce(true);
    // Post-suppression refresh: the entity is genuinely gone now, matching
    // the backend's real behavior (test_suppressed_trait_disappears_from_the_summary).
    mockGetSummary.mockResolvedValueOnce({
      generatedAt: "2026-09-04T12:01:00Z",
      traits: [],
      explanation: EXPLANATION,
    });

    render(<LearningControlsScreen />);
    await waitFor(() =>
      expect(
        screen.getByText("You tend to care more about AAPL than most stocks STRATUS tracks.")
      ).toBeTruthy()
    );

    fireEvent.press(screen.getByLabelText(/Stop using this reason/));

    expect(mockSuppress).toHaveBeenCalledWith("AAPL");
    await waitFor(() => expect(screen.getByText("Nothing learned yet")).toBeTruthy());
    expect(mockGetSummary).toHaveBeenCalledTimes(2);
  });

  it("leaves the trait visible and the button usable again when suppression fails", async () => {
    mockGetSummary.mockResolvedValueOnce({
      generatedAt: "2026-09-04T12:00:00Z",
      traits: [
        {
          entityId: "AAPL",
          description: "You tend to care more about AAPL than most stocks STRATUS tracks.",
          basis: "explicit",
          canSuppress: true,
        },
      ],
      explanation: EXPLANATION,
    });
    mockSuppress.mockResolvedValueOnce(false);

    render(<LearningControlsScreen />);
    await waitFor(() =>
      expect(
        screen.getByText("You tend to care more about AAPL than most stocks STRATUS tracks.")
      ).toBeTruthy()
    );

    fireEvent.press(screen.getByLabelText(/Stop using this reason/));

    await waitFor(() => expect(mockSuppress).toHaveBeenCalledTimes(1));
    // No reload on failure -- the trait, and a usable button, remain.
    expect(mockGetSummary).toHaveBeenCalledTimes(1);
    expect(
      screen.getByText("You tend to care more about AAPL than most stocks STRATUS tracks.")
    ).toBeTruthy();
    expect(screen.getByLabelText(/Stop using this reason/)).not.toBeDisabled();
  });

  it("never renders a suppress action for a trait the backend marks non-suppressible", async () => {
    mockGetSummary.mockResolvedValueOnce({
      generatedAt: "2026-09-04T12:00:00Z",
      traits: [
        {
          entityId: "AAPL",
          description: "You're tracking a holding connected to this.",
          basis: "explicit",
          canSuppress: false,
        },
      ],
      explanation: EXPLANATION,
    });

    render(<LearningControlsScreen />);

    await waitFor(() =>
      expect(screen.getByText("You're tracking a holding connected to this.")).toBeTruthy()
    );
    expect(screen.queryByText("Stop using this reason")).toBeNull();
  });
});
