import { humanizeSignalType } from "../signalType";

describe("humanizeSignalType", () => {
  it("replaces underscores with spaces and uppercases", () => {
    expect(humanizeSignalType("earnings_signal")).toBe("EARNINGS SIGNAL");
    expect(humanizeSignalType("volatility_spike")).toBe("VOLATILITY SPIKE");
    expect(humanizeSignalType("news_event")).toBe("NEWS EVENT");
  });

  it("leaves an already-single-word signal_type readable", () => {
    expect(humanizeSignalType("breaking_news")).toBe("BREAKING NEWS");
  });
});
