import {
  feedStatusFor,
  STALE_AFTER_MS,
  staleNotice,
  summarizeSinceLastVisit,
} from "../returningUser";
import type { FeedItem } from "../../types/loganFeed";

type Row = Pick<FeedItem, "is_new_for_user" | "since_last_looked">;

function row(
  isNew: boolean,
  status: "first_view" | "material_change" | "no_material_change" | null
): Row {
  return {
    is_new_for_user: isNew,
    since_last_looked:
      status === null ? null : ({ status } as unknown as FeedItem["since_last_looked"]),
  };
}

describe("summarizeSinceLastVisit", () => {
  it("counts new and changed opportunities separately", () => {
    const summary = summarizeSinceLastVisit([
      row(true, "first_view"),
      row(true, "first_view"),
      row(false, "material_change"),
      row(false, "no_material_change"),
    ]);
    expect(summary).toEqual({
      newCount: 2,
      changedCount: 1,
      text: "2 new · 1 changed since you last looked",
    });
  });

  it("reports revisions when nothing is new", () => {
    expect(
      summarizeSinceLastVisit([row(false, "material_change"), row(false, "material_change")])?.text
    ).toBe("2 changed since you last looked");
  });

  it("reports new items when nothing was revised", () => {
    expect(summarizeSinceLastVisit([row(true, null)])?.text).toBe("1 new since you last looked");
  });

  it("does not count a new item as changed as well", () => {
    expect(summarizeSinceLastVisit([row(true, "material_change")])).toMatchObject({
      newCount: 1,
      changedCount: 0,
    });
  });

  it("says so plainly when very little has changed", () => {
    expect(
      summarizeSinceLastVisit([row(false, "no_material_change"), row(false, "first_view")])?.text
    ).toBe("Nothing material has changed since you last looked.");
  });

  it("says nothing on a first-ever view or without lifecycle tracking", () => {
    expect(summarizeSinceLastVisit([row(false, "first_view")])).toBeNull();
    expect(summarizeSinceLastVisit([row(false, null)])).toBeNull();
    expect(summarizeSinceLastVisit([])).toBeNull();
  });
});

describe("staleNotice", () => {
  const now = 1_000_000_000;

  it("is silent while refreshes succeed, however old the data", () => {
    expect(staleNotice(now - 10 * 60_000, now, false)).toBeNull();
  });

  it("is silent for one dropped poll on fresh data", () => {
    expect(staleNotice(now - STALE_AFTER_MS + 1, now, true)).toBeNull();
  });

  it("is silent before any successful fetch", () => {
    expect(staleNotice(null, now, true)).toBeNull();
  });

  it("names how old the data is once a refresh has failed and it matters", () => {
    expect(staleNotice(now - 5 * 60_000, now, true)).toBe(
      "Couldn't refresh. Showing STRATUS as of 5 min ago."
    );
    expect(staleNotice(now - 3 * 3_600_000, now, true)).toBe(
      "Couldn't refresh. Showing STRATUS as of 3 hours ago."
    );
    expect(staleNotice(now - 1 * 3_600_000, now, true)).toBe(
      "Couldn't refresh. Showing STRATUS as of 1 hour ago."
    );
    expect(staleNotice(now - 9 * 86_400_000, now, true)).toBe(
      "Couldn't refresh. Showing STRATUS as of 9 days ago."
    );
  });
});

describe("feedStatusFor", () => {
  const now = 1_000_000_000;
  const base = {
    items: [row(true, "first_view")],
    providerDegraded: false,
    lastSuccessAtMs: now,
    nowMs: now,
    refreshFailed: false,
  };

  it("shows the return summary in the normal case", () => {
    expect(feedStatusFor(base)).toEqual({
      tone: "quiet",
      text: "1 new since you last looked",
    });
  });

  it("puts unrefreshed data ahead of everything else", () => {
    const status = feedStatusFor({
      ...base,
      providerDegraded: true,
      lastSuccessAtMs: now - 20 * 60_000,
      refreshFailed: true,
    });
    expect(status?.tone).toBe("notice");
    expect(status?.text).toMatch(/^Couldn't refresh\./);
  });

  it("flags a partly degraded provider even when the feed has items", () => {
    expect(feedStatusFor({ ...base, providerDegraded: true })).toEqual({
      tone: "notice",
      text: "Some live data is temporarily unavailable. This may be incomplete.",
    });
  });

  it("is empty when there is nothing true to say", () => {
    expect(feedStatusFor({ ...base, items: [row(false, null)] })).toBeNull();
  });

  it("never states a number, a probability or advice", () => {
    for (const status of [
      feedStatusFor({ ...base, providerDegraded: true }),
      feedStatusFor({ ...base, items: [row(false, "no_material_change")] }),
    ]) {
      expect(status?.text).not.toMatch(/%|buy|sell|likely|should/i);
    }
  });
});
