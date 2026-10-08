// Beta 1: what a returning user is told the moment the feed appears.
//
// Pure presentation of fields the backend already decided (is_new_for_user,
// since_last_looked) and of the app's own knowledge of when it last fetched
// successfully. Nothing here scores, ranks or infers anything, and nothing
// is invented: when there is nothing true to say, the helpers return null
// and the status line stays empty.
import type { FeedItem } from "../types/loganFeed";

export type ReturnSummary = {
  newCount: number;
  changedCount: number;
  text: string;
};

function plural(count: number, word: string): string {
  return `${count} ${word}`;
}

/**
 * One line answering "what changed since I was last here":
 *   "2 new · 3 changed since you last looked"
 *   "Nothing material has changed since you last looked."
 * Null on a first-ever view (nothing to compare against) and when lifecycle
 * tracking is not active for anything on screen.
 *
 * "New" is the backend's own unread flag. "Changed" is an opportunity the
 * user has opened before whose evidence materially changed since -- the
 * backend's since_last_looked verdict, never re-derived here.
 */
export function summarizeSinceLastVisit(
  items: readonly Pick<FeedItem, "is_new_for_user" | "since_last_looked">[]
): ReturnSummary | null {
  const newCount = items.filter((item) => item.is_new_for_user).length;
  const changedCount = items.filter(
    (item) => !item.is_new_for_user && item.since_last_looked?.status === "material_change"
  ).length;
  if (newCount > 0 || changedCount > 0) {
    const parts: string[] = [];
    if (newCount > 0) parts.push(plural(newCount, "new"));
    if (changedCount > 0) parts.push(plural(changedCount, "changed"));
    return { newCount, changedCount, text: `${parts.join(" · ")} since you last looked` };
  }
  const seenBefore = items.some(
    (item) => item.since_last_looked != null && item.since_last_looked.status !== "first_view"
  );
  if (!seenBefore) return null;
  return {
    newCount: 0,
    changedCount: 0,
    text: "Nothing material has changed since you last looked.",
  };
}

// Data older than this, after a failed refresh, is called out. Below it a
// failed refresh is ordinary network noise and says nothing.
export const STALE_AFTER_MS = 3 * 60 * 1000;

function ago(ms: number): string {
  const minutes = Math.round(ms / 60000);
  if (minutes < 60) return `${Math.max(minutes, 1)} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  return `${Math.round(hours / 24)} days ago`;
}

/**
 * What to say when the feed on screen could not be refreshed. Null unless a
 * refresh actually failed AND what is shown is old enough to matter: the app
 * never presents old data as current, and never alarms over a single
 * dropped poll.
 */
export function staleNotice(
  lastSuccessAtMs: number | null,
  nowMs: number,
  refreshFailed: boolean
): string | null {
  if (!refreshFailed || lastSuccessAtMs == null) return null;
  const age = nowMs - lastSuccessAtMs;
  if (age < STALE_AFTER_MS) return null;
  return `Couldn't refresh. Showing STRATUS as of ${ago(age)}.`;
}

export type FeedStatus = { tone: "notice" | "quiet"; text: string } | null;

/**
 * The single status line under the header. Precedence: data that could not
 * be refreshed, then a partially degraded provider, then the return
 * summary. One line, fixed height, so the field below never moves when the
 * status changes.
 */
export function feedStatusFor(input: {
  items: readonly Pick<FeedItem, "is_new_for_user" | "since_last_looked">[];
  providerDegraded: boolean;
  lastSuccessAtMs: number | null;
  nowMs: number;
  refreshFailed: boolean;
}): FeedStatus {
  const stale = staleNotice(input.lastSuccessAtMs, input.nowMs, input.refreshFailed);
  if (stale) return { tone: "notice", text: stale };
  if (input.providerDegraded) {
    return {
      tone: "notice",
      text: "Some live data is temporarily unavailable. This may be incomplete.",
    };
  }
  const summary = summarizeSinceLastVisit(input.items);
  return summary ? { tone: "quiet", text: summary.text } : null;
}
