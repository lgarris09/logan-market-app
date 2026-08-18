// Behavioral-personalization foundation (Part A): the mobile-side entry
// point into the new POST /v1/interactions route, which feeds the existing
// backend FeedbackSignal -> FeedbackEngine -> LearningEngine -> MemoryStore
// path (see backend/app/logan_feed.record_interaction and ADR-047). Kept
// deliberately narrow -- only fields the caller already truthfully has
// (event_id, entity_id, domain, interaction_type, an optional measured
// duration_ms) are sent; nothing here invents semantic fields.
import { fetchJson } from "./apiClient";

// Mirrors logan_core/contracts/feedback.py's InteractionType exactly -- see
// backend/app/models.py's RecordInteractionRequest. Not the full literal
// union (the backend still validates), just the values mobile code
// currently has a real reason to send.
export type InteractionType = "view" | "click" | "dismiss" | "save" | "share";

// Mirrors logan_core/contracts/common.py's Domain literal.
export type InteractionDomain =
  | "stocks"
  | "sports"
  | "poly"
  | "social"
  | "news"
  | "crypto";

export type RecordInteractionInput = {
  eventId: string;
  entityId: string;
  domain: InteractionDomain;
  interactionType: InteractionType;
  durationMs?: number;
};

/**
 * Fire-and-forget, same pattern as index.tsx's existing
 * `/v1/notifications/review` calls: the caller's own UI state (e.g. card
 * open/close, notification badge) already updated optimistically, and a
 * failed interaction record here has no user-visible effect worth blocking
 * or retrying for -- retries: 0 because a retried POST could otherwise
 * double-count one real interaction as two. fetchJson never throws, so no
 * caller needs a catch.
 */
export function recordInteraction(input: RecordInteractionInput): void {
  fetchJson("/v1/interactions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      event_id: input.eventId,
      entity_id: input.entityId,
      domain: input.domain,
      interaction_type: input.interactionType,
      duration_ms: input.durationMs,
    }),
    retries: 0,
  });
}
