// V2.3C Telemetry -- typed mobile client for POST /v1/telemetry/events.
//
// Telemetry records what happened; it never decides what it means (see
// backend/app/telemetry_models.py's own module docstring -- this file is
// the mobile half of the same contract, kept in sync by hand since this
// project has no shared-schema codegen).
//
// Fire-and-forget by design, matching this codebase's existing precedent
// for a background POST with no UI feedback to give (see app/index.tsx's
// openNotifications(), which posts /v1/notifications/review the same way):
// fetchJson() never throws (lib/apiClient.ts), so a telemetry call can
// never surface an unhandled rejection, and callers never await it --
// a slow or failed telemetry request must never delay or break the actual
// user-facing action it's attached to. Failures are silent by design (no
// console.error/warn) -- a dropped analytics event is not a problem worth
// surfacing to a developer console on every run, let alone a user.
import * as Crypto from "expo-crypto";

import { fetchJson } from "./apiClient";

export const TELEMETRY_SCHEMA_VERSION = "1.0";

// Mirrors backend/app/telemetry_models.py's TelemetryEventName exactly --
// a closed vocabulary, not a free string.
export type TelemetryEventName =
  | "opportunity_opened"
  | "opportunity_returned_to"
  | "watch_created"
  | "watch_removed"
  | "ask_started"
  | "ask_follow_up"
  | "usefulness_feedback_submitted";

export type TelemetrySourceSurface =
  | "wheel"
  | "feed_card"
  | "alert"
  | "digest"
  | "background"
  | "ask";

export type TelemetryContext = {
  askSessionId?: string;
  useful?: boolean;
};

export type TelemetryEventInput = {
  eventName: TelemetryEventName;
  /** The opportunity this event is about, when applicable -- FeedItem's own
   * event_id. Required server-side for opportunity-scoped event names (see
   * telemetry_models.py); omit for ask_started/ask_follow_up/usefulness_
   * feedback_submitted when there is no anchoring opportunity. */
  opportunityId?: string;
  sourceSurface?: TelemetrySourceSurface;
  context?: TelemetryContext;
};

function toRequestBody(input: TelemetryEventInput) {
  return {
    event_id: Crypto.randomUUID(),
    schema_version: TELEMETRY_SCHEMA_VERSION,
    event_name: input.eventName,
    occurred_at: new Date().toISOString(),
    opportunity_id: input.opportunityId,
    source_surface: input.sourceSurface,
    context: input.context
      ? {
          ask_session_id: input.context.askSessionId,
          useful: input.context.useful,
        }
      : undefined,
  };
}

/**
 * Fire-and-forget: intentionally not `async` from the caller's perspective
 * (no `await` at any call site -- see this file's own header). Builds a
 * fresh, stable, client-generated event_id per call (Crypto.randomUUID(),
 * the same primitive lib/identity.ts already uses) -- the backend's own
 * INSERT OR IGNORE makes a retried/duplicated send harmless.
 */
export function logTelemetryEvent(input: TelemetryEventInput): void {
  // fetchJson() never rejects by contract (see lib/apiClient.ts) -- this
  // .catch() is a defensive no-op, not a real error path, so a future
  // change to that contract can never turn a dropped telemetry event into
  // an unhandled promise rejection or a surfaced error.
  fetchJson("/v1/telemetry/events", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(toRequestBody(input)),
    retries: 0,
  }).catch(() => {});
}
