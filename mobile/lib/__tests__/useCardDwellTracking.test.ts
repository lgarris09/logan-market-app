import { act, renderHook } from "@testing-library/react-native";

import { recordInteraction } from "../interactions";
import { DwellTarget, useCardDwellTracking } from "../useCardDwellTracking";

jest.mock("../interactions", () => ({ recordInteraction: jest.fn() }));

type Listener = (state: string) => void;

let mockCurrentState = "active";
let mockListener: Listener | null = null;
const mockRemove = jest.fn();
const mockAddEventListener = jest.fn((_event: string, cb: Listener) => {
  mockListener = cb;
  return { remove: mockRemove };
});

jest.mock("react-native", () => ({
  AppState: {
    get currentState() {
      return mockCurrentState;
    },
    addEventListener: (event: string, cb: Listener) => mockAddEventListener(event, cb),
  },
}));

const mockedRecordInteraction = recordInteraction as jest.Mock;

function setAppState(next: string) {
  mockCurrentState = next;
  mockListener?.(next);
}

const target: DwellTarget = { eventId: "evt-1", entityId: "NVDA", domain: "stocks" };

describe("useCardDwellTracking", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockCurrentState = "active";
    mockListener = null;
    jest.useFakeTimers().setSystemTime(0);
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("records nothing while a card is simply open -- rendering alone is not an interaction", () => {
    renderHook(({ t }: { t: DwellTarget | null }) => useCardDwellTracking(t), {
      initialProps: { t: target },
    });

    expect(mockedRecordInteraction).not.toHaveBeenCalled();
  });

  it("records nothing when no card is open", () => {
    renderHook(({ t }: { t: DwellTarget | null }) => useCardDwellTracking(t), {
      initialProps: { t: null },
    });

    expect(mockedRecordInteraction).not.toHaveBeenCalled();
  });

  it("records a single view interaction with the measured duration on close", () => {
    const { rerender } = renderHook(
      ({ t }: { t: DwellTarget | null }) => useCardDwellTracking(t),
      { initialProps: { t: target as DwellTarget | null } }
    );

    jest.setSystemTime(5000);
    rerender({ t: null });

    expect(mockedRecordInteraction).toHaveBeenCalledTimes(1);
    expect(mockedRecordInteraction).toHaveBeenCalledWith({
      eventId: "evt-1",
      entityId: "NVDA",
      domain: "stocks",
      interactionType: "view",
      durationMs: 5000,
    });
  });

  it("flushes exactly once when the open card is replaced by a different one", () => {
    const { rerender } = renderHook(
      ({ t }: { t: DwellTarget | null }) => useCardDwellTracking(t),
      { initialProps: { t: target } }
    );

    jest.setSystemTime(3000);
    const other: DwellTarget = { eventId: "evt-2", entityId: "TSLA", domain: "stocks" };
    rerender({ t: other });

    expect(mockedRecordInteraction).toHaveBeenCalledTimes(1);
    expect(mockedRecordInteraction).toHaveBeenCalledWith(
      expect.objectContaining({ eventId: "evt-1", durationMs: 3000 })
    );
  });

  it("flushes once on unmount", () => {
    const { unmount } = renderHook(() => useCardDwellTracking(target));

    jest.setSystemTime(2000);
    unmount();

    expect(mockedRecordInteraction).toHaveBeenCalledTimes(1);
    expect(mockedRecordInteraction).toHaveBeenCalledWith(
      expect.objectContaining({ durationMs: 2000 })
    );
  });

  it("does not fabricate a new open on repeated polling with the same event_id", () => {
    const { rerender } = renderHook(
      ({ t }: { t: DwellTarget | null }) => useCardDwellTracking(t),
      { initialProps: { t: target } }
    );

    // A new object reference for the same logical target (e.g. a poll
    // refresh reconstructing `items`) must not retrigger the effect.
    rerender({ t: { ...target } });
    rerender({ t: { ...target } });

    expect(mockedRecordInteraction).not.toHaveBeenCalled();
  });

  it("flushes on backgrounding without counting background time, and emits nothing on foreground return", () => {
    const { unmount } = renderHook(() => useCardDwellTracking(target));

    jest.setSystemTime(4000);
    act(() => setAppState("background"));

    expect(mockedRecordInteraction).toHaveBeenCalledTimes(1);
    expect(mockedRecordInteraction).toHaveBeenCalledWith(
      expect.objectContaining({ durationMs: 4000 })
    );

    jest.setSystemTime(10000); // 6s "in background" -- must never be counted
    act(() => setAppState("active"));
    expect(mockedRecordInteraction).toHaveBeenCalledTimes(1); // no emission on resume

    jest.setSystemTime(11000); // 1s of real foreground viewing after resume
    unmount();

    expect(mockedRecordInteraction).toHaveBeenCalledTimes(2);
    expect(mockedRecordInteraction).toHaveBeenLastCalledWith(
      expect.objectContaining({ durationMs: 1000 })
    );
  });

  it("removes the AppState subscription on unmount", () => {
    const { unmount } = renderHook(() => useCardDwellTracking(target));
    unmount();

    expect(mockRemove).toHaveBeenCalled();
  });
});
