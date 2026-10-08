import { act, fireEvent, render, screen, waitFor } from "@testing-library/react-native";

import AttentionFieldScreen from "../index";
import { ApiResult, fetchJson } from "../../lib/apiClient";
import { OpportunitiesResponse } from "../../types/loganFeed";

jest.mock("../../lib/apiClient", () => ({
  fetchJson: jest.fn(),
}));

// V2.3A consumer closeout -- the header avatar navigates via expo-router's
// `router.push`; mocked so tests can assert on it directly rather than
// depending on jest-expo's real navigation context being fully set up for
// a screen rendered standalone (outside any actual Stack).
const mockRouterPush = jest.fn();
jest.mock("expo-router", () => ({
  router: { push: (...args: unknown[]) => mockRouterPush(...args) },
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

function opportunitiesResult(
  itemCount: number,
  providerDegraded = false
): ApiResult<OpportunitiesResponse> {
  return {
    status: "success",
    data: {
      schema_version: "1.0",
      generated_at: "2026-08-06T00:00:00Z",
      items: Array.from({ length: itemCount }, (_, i) => ({
        event_id: `event-${i}`,
      })) as unknown as OpportunitiesResponse["items"],
      provider_degraded: providerDegraded,
    },
  };
}

describe("AttentionFieldScreen", () => {
  beforeEach(() => {
    mockedFetchJson.mockReset();
    mockRouterPush.mockReset();
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

    await waitFor(() =>
      expect(screen.getByText("Nothing needs your attention right now")).toBeTruthy()
    );
    // V2.3C Block 13: restrained, honest healthy-but-sparse language --
    // distinct from the provider-degraded copy asserted below.
    expect(
      screen.getByText("STRATUS is still watching. This will update when something changes.")
    ).toBeTruthy();
  });

  // V2.3A.1 field reliability work: a zero-item response caused by a genuine
  // live-data provider outage (backend's provider_degraded) must render an
  // honestly different message than "nothing to see" -- an empty field must
  // never quietly pass off a real outage as "there's genuinely nothing here."
  it("shows a truthful degraded-data state when zero items is a provider outage, not a genuine empty field", async () => {
    mockedFetchJson.mockResolvedValue(opportunitiesResult(0, true));

    render(<AttentionFieldScreen />);

    await waitFor(() => expect(screen.getByText("Live data temporarily unavailable")).toBeTruthy());
    expect(screen.queryByText("Nothing needs your attention right now")).toBeNull();
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

  describe("header profile avatar (V2.3A -- standard account affordance)", () => {
    it("renders a distinct, guest-fallback avatar next to the notification bell, not the old ambiguous dot", () => {
      mockedFetchJson.mockReturnValue(new Promise(() => {}));

      render(<AttentionFieldScreen />);

      // Clerk isn't configured in this test environment, so the header
      // renders its guest fallback (a plain person glyph) rather than
      // calling any Clerk hook -- see components/ProfileAvatar.tsx.
      expect(screen.getByLabelText("Account and settings")).toBeTruthy();
      expect(screen.getByText("icon:person-outline")).toBeTruthy();
      // The bell is a separate element with its own label/icon, not merged
      // into the same tap target as the avatar.
      expect(screen.getByLabelText("No new opportunities")).toBeTruthy();
      expect(screen.getByText("icon:notifications-outline")).toBeTruthy();
    });

    it("navigates to the Account & Settings screen when the avatar is pressed", () => {
      mockedFetchJson.mockReturnValue(new Promise(() => {}));

      render(<AttentionFieldScreen />);
      fireEvent.press(screen.getByLabelText("Account and settings"));

      expect(mockRouterPush).toHaveBeenCalledWith("/account");
    });

    it("pressing the avatar never also triggers the notifications panel", () => {
      mockedFetchJson.mockReturnValue(new Promise(() => {}));

      render(<AttentionFieldScreen />);
      fireEvent.press(screen.getByLabelText("Account and settings"));

      // NEW OPPORTUNITIES panel title only ever renders once panelItems is
      // set by openNotifications() -- confirming it's absent proves the
      // avatar's own press handler is fully independent of the bell's.
      expect(screen.queryByText("NEW OPPORTUNITIES")).toBeNull();
    });
  });
});

// Beta 1 (returning user): reopening the app must not blank a feed that is
// already on screen, and a failed refresh must not replace it with an error.
describe("AttentionFieldScreen -- returning user", () => {
  const { AppState } = jest.requireActual("react-native");

  function captureAppStateHandler() {
    const handlers: ((state: string) => void)[] = [];
    jest.spyOn(AppState, "addEventListener").mockImplementation(((
      _type: string,
      handler: (state: string) => void
    ) => {
      handlers.push(handler);
      return { remove: jest.fn() };
    }) as never);
    return handlers;
  }

  function itemsResult(
    items: Record<string, unknown>[],
    providerDegraded = false
  ): ApiResult<OpportunitiesResponse> {
    return {
      status: "success",
      data: {
        schema_version: "1.0",
        generated_at: "2026-10-08T00:00:00Z",
        items: items as unknown as OpportunitiesResponse["items"],
        provider_degraded: providerDegraded,
      },
    };
  }

  beforeEach(() => {
    mockedFetchJson.mockReset();
    jest.restoreAllMocks();
  });

  it("keeps the feed on screen while it refreshes on resume", async () => {
    const handlers = captureAppStateHandler();
    mockedFetchJson.mockResolvedValue(opportunitiesResult(3));
    render(<AttentionFieldScreen />);
    await waitFor(() => expect(screen.getByText("AttentionField:3")).toBeTruthy());

    // The refresh is slow: it never resolves during this test.
    mockedFetchJson.mockReturnValue(new Promise(() => {}));
    act(() => handlers.forEach((handler) => handler("active")));

    expect(screen.getByText("AttentionField:3")).toBeTruthy();
    expect(screen.queryByLabelText("Loading opportunities")).toBeNull();
  });

  it("keeps the feed when the network is unavailable on resume", async () => {
    const handlers = captureAppStateHandler();
    mockedFetchJson.mockResolvedValue(opportunitiesResult(3));
    render(<AttentionFieldScreen />);
    await waitFor(() => expect(screen.getByText("AttentionField:3")).toBeTruthy());

    mockedFetchJson.mockResolvedValue({ status: "error", message: "Network request failed" });
    await act(async () => {
      handlers.forEach((handler) => handler("active"));
    });

    expect(screen.getByText("AttentionField:3")).toBeTruthy();
    expect(screen.queryByText("Unable to reach STRATUS")).toBeNull();
    expect(screen.queryByText("Backend not connected")).toBeNull();
    expect(screen.queryByText("Taking longer than expected")).toBeNull();
  });

  it("still shows the full error state when there is nothing to keep", async () => {
    mockedFetchJson.mockResolvedValue({ status: "error", message: "Network request failed" });
    render(<AttentionFieldScreen />);
    await waitFor(() => expect(screen.getByLabelText("Retry")).toBeTruthy());
  });

  it("tells a returning user what is new and what changed", async () => {
    mockedFetchJson.mockResolvedValue(
      itemsResult([
        {
          event_id: "a",
          display_name: "Example Co",
          ticker: "EXM",
          is_new_for_user: true,
          since_last_looked: null,
          delivered_item: { evidence_label: "Supported evidence" },
        },
        {
          event_id: "b",
          is_new_for_user: false,
          since_last_looked: { status: "material_change" },
        },
        {
          event_id: "c",
          is_new_for_user: false,
          since_last_looked: { status: "no_material_change" },
        },
      ])
    );
    render(<AttentionFieldScreen />);
    await waitFor(() =>
      expect(screen.getByText("1 new · 1 changed since you last looked")).toBeTruthy()
    );
  });

  it("says so when very little has changed", async () => {
    mockedFetchJson.mockResolvedValue(
      itemsResult([
        {
          event_id: "a",
          is_new_for_user: false,
          since_last_looked: { status: "no_material_change" },
        },
      ])
    );
    render(<AttentionFieldScreen />);
    await waitFor(() =>
      expect(screen.getByText("Nothing material has changed since you last looked.")).toBeTruthy()
    );
  });

  it("flags partly unavailable live data without hiding the feed", async () => {
    mockedFetchJson.mockResolvedValue(
      itemsResult([{ event_id: "a", is_new_for_user: false, since_last_looked: null }], true)
    );
    render(<AttentionFieldScreen />);
    await waitFor(() =>
      expect(
        screen.getByText("Some live data is temporarily unavailable. This may be incomplete.")
      ).toBeTruthy()
    );
    expect(screen.getByText("AttentionField:1")).toBeTruthy();
  });

  it("presents a quiet market as a normal state, not an error", async () => {
    mockedFetchJson.mockResolvedValue(opportunitiesResult(0));
    render(<AttentionFieldScreen />);
    await waitFor(() =>
      expect(screen.getByText("Nothing needs your attention right now")).toBeTruthy()
    );
    expect(screen.queryByText("Live data temporarily unavailable")).toBeNull();
  });
});
