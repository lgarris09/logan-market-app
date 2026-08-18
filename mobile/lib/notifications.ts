// Sprint 3.6.6F -- STRATUS Watch, first real push-notification slice. This
// file owns permission request, Expo push token acquisition, backend
// registration, and the tap-response listener. It deliberately does NOT own
// opening a card -- the caller (app/index.tsx) already has
// openNotificationCard(eventId) wired to the same open-card flow the
// in-app notification dropdown uses; this file just extracts event_id from
// a tapped notification and hands it back via a callback, so a push
// notification opens the identical card, not a second implementation.
//
// Foreground display behavior is configured here (setNotificationHandler)
// since it has no natural home in a screen component and must be set once,
// early, before any notification could arrive.
import Constants from "expo-constants";
import * as Device from "expo-device";
import * as Notifications from "expo-notifications";
import { useEffect } from "react";

import { fetchJson } from "./apiClient";

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

export type RegisterPushTokenResult =
  | { status: "registered" }
  | { status: "not-a-device" }
  | { status: "permission-denied" }
  | { status: "token-fetch-failed"; message: string }
  | { status: "backend-registration-failed"; message: string };

/**
 * Requests iOS notification permission (if not already granted or denied),
 * acquires an Expo push token, and registers it with the backend. Safe to
 * call on every app start -- expo-notifications and the backend's
 * /v1/notifications/register are both idempotent (re-requesting an already-
 * granted permission is a no-op; re-registering an already-known token just
 * confirms it, see backend/app/notifications.py's token_count behavior).
 *
 * Push notifications require a real device and the native module linked
 * into the installed dev-client build -- neither is true in a simulator or
 * an un-rebuilt dev-client, so both are reported as explicit result states
 * rather than silently failing.
 */
export async function registerForPushNotificationsAsync(): Promise<RegisterPushTokenResult> {
  if (!Device.isDevice) {
    return { status: "not-a-device" };
  }

  const existing = await Notifications.getPermissionsAsync();
  let finalStatus = existing.status;
  if (finalStatus !== "granted") {
    const requested = await Notifications.requestPermissionsAsync();
    finalStatus = requested.status;
  }
  if (finalStatus !== "granted") {
    return { status: "permission-denied" };
  }

  let expoPushToken: string;
  try {
    const projectId = Constants.expoConfig?.extra?.eas?.projectId;
    const tokenResponse = await Notifications.getExpoPushTokenAsync(
      projectId ? { projectId } : undefined
    );
    expoPushToken = tokenResponse.data;
  } catch (error) {
    return {
      status: "token-fetch-failed",
      message: error instanceof Error ? error.message : "Unable to acquire push token.",
    };
  }

  const result = await fetchJson<{ registered: boolean; token_count: number }>(
    "/v1/notifications/register",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expo_push_token: expoPushToken }),
      retries: 1,
    }
  );
  if (result.status !== "success") {
    return {
      status: "backend-registration-failed",
      message: result.status === "error" ? result.message : result.status,
    };
  }
  return { status: "registered" };
}

/**
 * Wires a tap on a STRATUS Watch push notification to the same
 * openNotificationCard(eventId) flow the in-app notification dropdown
 * already uses. Extracts event_id from the payload backend/app/
 * notifications.py's _build_push_message sends -- never invents an
 * event_id, and does nothing if a malformed/foreign notification lacks one.
 */
export function useNotificationTapHandler(onOpenEventId: (eventId: string) => void) {
  useEffect(() => {
    const subscription = Notifications.addNotificationResponseReceivedListener((response) => {
      const eventId = response.notification.request.content.data?.event_id;
      if (typeof eventId === "string" && eventId.length > 0) {
        onOpenEventId(eventId);
      }
    });
    return () => subscription.remove();
  }, [onOpenEventId]);
}
