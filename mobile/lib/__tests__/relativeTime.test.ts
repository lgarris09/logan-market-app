import { relativeTimeFrom } from "../relativeTime";

const NOW = new Date("2026-08-08T12:00:00Z").getTime();

describe("relativeTimeFrom", () => {
  it("renders 'just now' for under a minute", () => {
    expect(relativeTimeFrom("2026-08-08T11:59:45Z", NOW)).toBe("just now");
  });

  it("renders minutes ago", () => {
    expect(relativeTimeFrom("2026-08-08T11:46:00Z", NOW)).toBe("14m ago");
  });

  it("renders hours ago", () => {
    expect(relativeTimeFrom("2026-08-08T08:00:00Z", NOW)).toBe("4h ago");
  });

  it("renders days ago", () => {
    expect(relativeTimeFrom("2026-08-05T12:00:00Z", NOW)).toBe("3d ago");
  });

  it("returns a placeholder for an invalid timestamp", () => {
    expect(relativeTimeFrom("not-a-date", NOW)).toBe("—");
  });
});
