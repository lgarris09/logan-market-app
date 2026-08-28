import { act, fireEvent, render, screen, waitFor } from "@testing-library/react-native";

import AttentionFieldScreen from "../index";
import { ApiResult, fetchJson } from "../../lib/apiClient";
import { OpportunitiesResponse } from "../../types/loganFeed";

jest.mock("../../lib/apiClient", () => ({
  fetchJson: jest.fn(),
}));

// @expo/vector-icons pulls in expo-font -> expo-asset, which isn't hoisted to a
// location Jest's (Node-standard) module resolution can find under npm's nested
// install layout -- unrelated to this screen's own logic, so it's mocked out
// rather than pulling expo-asset into package.json just to satisfy a test.
jest.mock("@expo/vector-icons", () => {
  const { Text } = jest.requireActual("react-native");
  return { Ionicons: (props: { name: string }) => <Text>{`icon:${props.name}`}</Text> };
});

// The Attention Field itself (Vessel's classic-Animated glow/blur tree) is covered
// by its own concerns -- this screen test is about which state (loading, loaded,
// empty, timeout, error+retry) the screen renders for a given fetchJson outcome,
// not about re-testing Vessel's rendering.
jest.mock("../../components/AttentionField", () => ({
  AttentionField: ({ items }: { items: { event_id: string }[] }) => {
    const { Text } = jest.requireActual("react-native");
    return <Text>{`AttentionField:${items.length}`}</Text>;
  },
}));

const mockedFetchJson = fetchJson as jest.MockedFunction<typeof fetchJson>;

function opportunitiesResult(itemCount: number): ApiResult<OpportunitiesResponse> {
  return {
    status: "success",
    data: {
      schema_version: "1.0",
      generated_at: "2026-08-06T00:00:00Z",
      items: Array.from({ length: itemCount }, (_, i) => ({
        event_id: `event-${i}`,
      })) as unknown as OpportunitiesResponse["items"],
    },
  };
}

describe("AttentionFieldScreen", () => {
  beforeEach(() => {
    mockedFetchJson.mockReset();
  });

  it("shows a loading state before the request resolves", () => {
    mockedFetchJson.mockReturnValue(new Promise(() => {})); // never resolves

    render(<AttentionFieldScreen />);

    expect(screen.getByLabelText("Loading opportunities")).toBeTruthy();
    // V2.3A field report fix: a bare spinner on this screen's near-black
    // background was indistinguishable from a dead/black screen on a slow
    // or blocked network (reproduced on a real work Wi-Fi) -- this text is
    // the fix for that specific confusion.
    expect(screen.getByText("Connecting to STRATUS…")).toBeTruthy();
  });

  it("renders the Attention Field once opportunities load", async () => {
    mockedFetchJson.mockResolvedValue(opportunitiesResult(3));

    render(<AttentionFieldScreen />);

    await waitFor(() => expect(screen.getByText("AttentionField:3")).toBeTruthy());
  });

  it("shows an empty state when the feed loads with zero items", async () => {
    mockedFetchJson.mockResolvedValue(opportunitiesResult(0));

    render(<AttentionFieldScreen />);

    await waitFor(() => expect(screen.getByText("Nothing to show yet")).toBeTruthy());
  });

  it("shows a timeout state and can retry", async () => {
    mockedFetchJson.mockResolvedValueOnce({ status: "timeout" });

    render(<AttentionFieldScreen />);

    await waitFor(() => expect(screen.getByText("Taking longer than expected")).toBeTruthy());

    mockedFetchJson.mockResolvedValueOnce(opportunitiesResult(1));
    await act(async () => {
      fireEvent.press(screen.getByLabelText("Retry"));
    });

    await waitFor(() => expect(screen.getByText("AttentionField:1")).toBeTruthy());
    expect(mockedFetchJson).toHaveBeenCalledTimes(2);
  });

  it("shows an error state with the server message and can retry", async () => {
    mockedFetchJson.mockResolvedValueOnce({ status: "error", message: "Server returned 500" });

    render(<AttentionFieldScreen />);

    await waitFor(() => expect(screen.getByText("Server returned 500")).toBeTruthy());

    mockedFetchJson.mockResolvedValueOnce(opportunitiesResult(2));
    await act(async () => {
      fireEvent.press(screen.getByLabelText("Retry"));
    });

    await waitFor(() => expect(screen.getByText("AttentionField:2")).toBeTruthy());
  });

  it("shows the hosted-network error copy (not dev-only 'start FastAPI' guidance) outside __DEV__", async () => {
    // V2.3A field report fix: the dev-oriented "Start FastAPI..." message
    // was being shown verbatim on hosted/production builds too, actively
    // wrong and confusing on a real device that simply can't reach a
    // blocked or unreachable hosted backend.
    const originalDev = (global as { __DEV__?: boolean }).__DEV__;
    (global as { __DEV__?: boolean }).__DEV__ = false;
    try {
      mockedFetchJson.mockResolvedValueOnce({ status: "error", message: "Server returned 500" });

      render(<AttentionFieldScreen />);

      await waitFor(() => expect(screen.getByText("Unable to reach STRATUS")).toBeTruthy());
      expect(screen.queryByText(/Start FastAPI/)).toBeNull();
    } finally {
      (global as { __DEV__?: boolean }).__DEV__ = originalDev;
    }
  });
});
