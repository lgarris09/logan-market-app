import { renderHook } from "@testing-library/react-native";

import * as Device from "expo-device";
import * as Notifications from "expo-notifications";

import { fetchJson } from "../apiClient";
import { registerForPushNotificationsAsync, useNotificationTapHandler } from "../notifications";

// A getter backed by shared closure state rather than a plain data property:
// Babel's ESM interop can hand different import call-sites their own
// wrapped namespace object, so directly reassigning/redefining the
// property post-hoc doesn't reliably propagate to lib/notifications.ts's
// own `import * as Device`. The getter *function* itself (and the state it
// closes over) is preserved across that wrapping, so __setIsDevice always
// affects what every consumer's `Device.isDevice` actually reads.
jest.mock("expo-device", () => {
  const state = { isDevice: true };
  return {
    __setIsDevice: (value: boolean) => {
      state.isDevice = value;
    },
    get isDevice() {
      return state.isDevice;
    },
  };
});

jest.mock("expo-notifications", () => ({
  setNotificationHandler: jest.fn(),
  getPermissionsAsync: jest.fn(),
  requestPermissionsAsync: jest.fn(),
  getExpoPushTokenAsync: jest.fn(),
  addNotificationResponseReceivedListener: jest.fn(),
}));

jest.mock("expo-constants", () => ({
  expoConfig: { extra: { eas: { projectId: "test-project-id" } } },
}));

jest.mock("../apiClient", () => ({ fetchJson: jest.fn() }));

const mockedDevice = Device as unknown as { __setIsDevice: (value: boolean) => void };
const mockedNotifications = Notifications as jest.Mocked<typeof Notifications>;
const mockedFetchJson = fetchJson as jest.Mock;

describe("registerForPushNotificationsAsync", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedDevice.__setIsDevice(true);
  });

  it("returns not-a-device on a simulator", async () => {
    mockedDevice.__setIsDevice(false);

    const result = await registerForPushNotificationsAsync();

    expect(result).toEqual({ status: "not-a-device" });
    expect(mockedNotifications.getPermissionsAsync).not.toHaveBeenCalled();
  });

  it("returns permission-denied when the user declines", async () => {
    mockedNotifications.getPermissionsAsync.mockResolvedValue({ status: "undetermined" } as never);
    mockedNotifications.requestPermissionsAsync.mockResolvedValue({ status: "denied" } as never);

    const result = await registerForPushNotificationsAsync();

    expect(result).toEqual({ status: "permission-denied" });
    expect(mockedNotifications.getExpoPushTokenAsync).not.toHaveBeenCalled();
  });

  it("does not re-request already-granted permission", async () => {
    mockedNotifications.getPermissionsAsync.mockResolvedValue({ status: "granted" } as never);
    mockedNotifications.getExpoPushTokenAsync.mockResolvedValue({
      type: "expo",
      data: "ExponentPushToken[xyz]",
    } as never);
    mockedFetchJson.mockResolvedValue({
      status: "success",
      data: { registered: true, token_count: 1 },
    });

    await registerForPushNotificationsAsync();

    expect(mockedNotifications.requestPermissionsAsync).not.toHaveBeenCalled();
  });

  it("returns token-fetch-failed when getExpoPushTokenAsync throws", async () => {
    mockedNotifications.getPermissionsAsync.mockResolvedValue({ status: "granted" } as never);
    mockedNotifications.getExpoPushTokenAsync.mockRejectedValue(new Error("network down"));

    const result = await registerForPushNotificationsAsync();

    expect(result).toEqual({ status: "token-fetch-failed", message: "network down" });
    expect(mockedFetchJson).not.toHaveBeenCalled();
  });

  it("returns backend-registration-failed when the backend call fails", async () => {
    mockedNotifications.getPermissionsAsync.mockResolvedValue({ status: "granted" } as never);
    mockedNotifications.getExpoPushTokenAsync.mockResolvedValue({
      type: "expo",
      data: "ExponentPushToken[xyz]",
    } as never);
    mockedFetchJson.mockResolvedValue({ status: "error", message: "Server returned 500" });

    const result = await registerForPushNotificationsAsync();

    expect(result).toEqual({
      status: "backend-registration-failed",
      message: "Server returned 500",
    });
  });

  it("registers the real token with the backend on the happy path", async () => {
    mockedNotifications.getPermissionsAsync.mockResolvedValue({ status: "granted" } as never);
    mockedNotifications.getExpoPushTokenAsync.mockResolvedValue({
      type: "expo",
      data: "ExponentPushToken[xyz]",
    } as never);
    mockedFetchJson.mockResolvedValue({
      status: "success",
      data: { registered: true, token_count: 1 },
    });

    const result = await registerForPushNotificationsAsync();

    expect(result).toEqual({ status: "registered" });
    expect(mockedNotifications.getExpoPushTokenAsync).toHaveBeenCalledWith({
      projectId: "test-project-id",
    });
    expect(mockedFetchJson).toHaveBeenCalledWith(
      "/v1/notifications/register",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ expo_push_token: "ExponentPushToken[xyz]" }),
      })
    );
  });
});

describe("useNotificationTapHandler", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("calls onOpenEventId with the tapped notification's event_id", () => {
    mockedNotifications.addNotificationResponseReceivedListener.mockReturnValue({
      remove: jest.fn(),
    } as never);

    const onOpenEventId = jest.fn();
    renderHook(() => useNotificationTapHandler(onOpenEventId));

    const listener =
      mockedNotifications.addNotificationResponseReceivedListener.mock.calls[0][0];
    listener({
      notification: { request: { content: { data: { event_id: "abc-123" } } } },
    } as never);

    expect(onOpenEventId).toHaveBeenCalledWith("abc-123");
  });

  it("does nothing when the notification has no event_id", () => {
    mockedNotifications.addNotificationResponseReceivedListener.mockReturnValue({
      remove: jest.fn(),
    } as never);

    const onOpenEventId = jest.fn();
    renderHook(() => useNotificationTapHandler(onOpenEventId));

    const listener =
      mockedNotifications.addNotificationResponseReceivedListener.mock.calls[0][0];
    listener({ notification: { request: { content: { data: {} } } } } as never);

    expect(onOpenEventId).not.toHaveBeenCalled();
  });

  it("removes the subscription on unmount", () => {
    const remove = jest.fn();
    mockedNotifications.addNotificationResponseReceivedListener.mockReturnValue({
      remove,
    } as never);

    const { unmount } = renderHook(() => useNotificationTapHandler(jest.fn()));
    unmount();

    expect(remove).toHaveBeenCalled();
  });
});
