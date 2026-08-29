// Minimal STRATUS Watch (V2.3E) -- the mobile-side entry point into
// POST /v1/watches and DELETE /v1/watches/{entity_id} (see backend/app/main.py).
//
// One consumer intent only: "STRATUS, keep watching this for me." Not a
// portfolio, not a watchlist-management product, not a notification-rule
// builder -- see backend/app/watch.py's own module docstring for the full
// scope boundary.
//
// telemetry (watch_created/watch_removed) is fired here, not by the caller,
// and only when the backend's own response says this specific call is the
// one that genuinely created/removed the watch (`created`/`removed`) --
// never on a failed request (fetchJson's ApiResult "success" check below),
// and never on an idempotent repeat. This is what satisfies "a failed API
// action must never falsely emit successful telemetry" and "a duplicate
// request must never produce duplicate telemetry."
import { fetchJson } from "./apiClient";
import { logTelemetryEvent } from "./telemetry";

export type WatchResult = { entityId: string; watched: boolean; created: boolean };
export type UnwatchResult = { entityId: string; watched: boolean; removed: boolean };

/**
 * `eventId` is this opportunity's current FeedItem.event_id -- passed
 * through to telemetry only (the same "opportunity_id" every other
 * opportunity-scoped event already uses, per lib/telemetry.ts), never used
 * to identify the watch itself (that's `entityId`, the stable underlying
 * opportunity identity, unaffected by event_id changing across polls).
 */
export async function watchOpportunity(
  entityId: string,
  eventId: string
): Promise<WatchResult | null> {
  const result = await fetchJson<{
    entity_id: string;
    watched: boolean;
    created: boolean;
  }>("/v1/watches", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ entity_id: entityId }),
    retries: 0,
  });
  if (result.status !== "success") {
    return null;
  }
  if (result.data.created) {
    logTelemetryEvent({
      eventName: "watch_created",
      opportunityId: eventId,
      sourceSurface: "feed_card",
    });
  }
  return {
    entityId: result.data.entity_id,
    watched: result.data.watched,
    created: result.data.created,
  };
}

export async function unwatchOpportunity(
  entityId: string,
  eventId: string
): Promise<UnwatchResult | null> {
  const result = await fetchJson<{
    entity_id: string;
    watched: boolean;
    removed: boolean;
  }>(`/v1/watches/${encodeURIComponent(entityId)}`, {
    method: "DELETE",
    retries: 0,
  });
  if (result.status !== "success") {
    return null;
  }
  if (result.data.removed) {
    logTelemetryEvent({
      eventName: "watch_removed",
      opportunityId: eventId,
      sourceSurface: "feed_card",
    });
  }
  return {
    entityId: result.data.entity_id,
    watched: result.data.watched,
    removed: result.data.removed,
  };
}
