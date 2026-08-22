// Sprint 3.6.7 Block 4: typed client for the contextual/generic Ask STRATUS
// route (backend/app/main.py's ask_logan, backed by backend/app/models.py's
// AskRequest/AskResponse). One shared shape for both: `eventId` present ->
// contextual (grounded in a real opportunity), omitted -> the pre-existing
// generic path, unchanged.
import { ApiResult, fetchJson } from "./apiClient";

export type AskInput = {
  message: string;
  /** A stable FeedItem.event_id -- the only opportunity reference the client
   * ever sends; the backend rehydrates real context from it server-side. */
  eventId?: string;
  /** Client-generated once per Ask STRATUS screen visit (see
   * createAskSessionId below) -- lets a follow-up question omit `eventId`
   * and still resolve against the same opportunity the session started
   * with. */
  sessionId?: string;
  signal?: AbortSignal;
};

export type AskOutput = {
  answer: string;
  eventId: string | null;
  sessionId: string | null;
  /** Whether this answer was actually grounded in real opportunity context
   * vs. the generic fallback. */
  grounded: boolean;
};

type AskResponseBody = {
  answer: string;
  event_id: string | null;
  session_id: string | null;
  grounded: boolean;
};

export function askStratus(input: AskInput): Promise<ApiResult<AskOutput>> {
  return fetchJson<AskResponseBody>("/v1/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message: input.message,
      event_id: input.eventId,
      session_id: input.sessionId,
    }),
    signal: input.signal,
    // Non-idempotent -- matches the pre-existing ask.tsx call's own
    // convention (retries: 0) rather than risking a double-submitted
    // question (and, for a contextual one, a double-counted ASK_FOLLOWUP --
    // though the backend's session-scoped cap already protects against
    // that specifically, this avoids sending the duplicate at all).
    retries: 0,
  }).then((result) => {
    if (result.status !== "success") return result;
    return {
      status: "success",
      data: {
        answer: result.data.answer,
        eventId: result.data.event_id,
        sessionId: result.data.session_id,
        grounded: result.data.grounded,
      },
    };
  });
}

let sessionCounter = 0;

/** A client-generated session identifier, stable for the lifetime of one
 * Ask STRATUS screen visit -- not a real UUID (no such dependency exists in
 * this app), just unique enough to key a short-lived server-side session
 * map (see backend/app/logan_feed.py's _ask_sessions). */
export function createAskSessionId(): string {
  sessionCounter += 1;
  return `ask-${Date.now()}-${sessionCounter}-${Math.random().toString(36).slice(2, 8)}`;
}
