import { act, renderHook, waitFor } from "@testing-library/react-native";
import { AccessibilityInfo, EmitterSubscription } from "react-native";

import { useReducedMotion } from "../useReducedMotion";

// AccessibilityInfo.addEventListener is overloaded per event name; TS can't infer
// which overload a generic jest mock satisfies, so the mock is typed against the
// "reduceMotionChanged" overload specifically rather than widened with `any`.
type ReduceMotionListener = (enabled: boolean) => void;
function mockReduceMotionListener(
  impl: (eventName: "reduceMotionChanged", handler: ReduceMotionListener) => EmitterSubscription
) {
  return jest
    .spyOn(AccessibilityInfo, "addEventListener")
    .mockImplementation(impl as unknown as typeof AccessibilityInfo.addEventListener);
}

describe("useReducedMotion", () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("reflects the OS setting once isReduceMotionEnabled resolves", async () => {
    jest.spyOn(AccessibilityInfo, "isReduceMotionEnabled").mockResolvedValue(true);
    const addEventListenerSpy = jest.spyOn(AccessibilityInfo, "addEventListener");

    const { result } = renderHook(() => useReducedMotion());

    expect(result.current).toBe(false); // initial value before the promise resolves

    await waitFor(() => expect(result.current).toBe(true));
    expect(addEventListenerSpy).toHaveBeenCalledWith("reduceMotionChanged", expect.any(Function));
  });

  it("updates live when the OS setting changes while mounted", async () => {
    jest.spyOn(AccessibilityInfo, "isReduceMotionEnabled").mockResolvedValue(false);
    let changeHandler: ReduceMotionListener | undefined;
    mockReduceMotionListener((_event, handler) => {
      changeHandler = handler;
      return { remove: jest.fn() } as unknown as EmitterSubscription;
    });

    const { result } = renderHook(() => useReducedMotion());
    await waitFor(() => expect(result.current).toBe(false));

    act(() => changeHandler?.(true));

    expect(result.current).toBe(true);
  });

  it("removes its listener on unmount", async () => {
    jest.spyOn(AccessibilityInfo, "isReduceMotionEnabled").mockResolvedValue(false);
    const remove = jest.fn();
    mockReduceMotionListener(() => ({ remove }) as unknown as EmitterSubscription);

    const { unmount } = renderHook(() => useReducedMotion());
    unmount();

    expect(remove).toHaveBeenCalled();
  });
});
