import { isFirstUserMessage } from "../ask";

describe("isFirstUserMessage", () => {
  it("is true for an empty transcript (a brand-new session)", () => {
    expect(isFirstUserMessage([])).toBe(true);
  });

  it("is true when only assistant messages exist yet (e.g. a greeting)", () => {
    expect(isFirstUserMessage([{ role: "assistant" }])).toBe(true);
  });

  it("is false once at least one real user question has been asked", () => {
    expect(
      isFirstUserMessage([
        { role: "user" },
        { role: "assistant" },
      ])
    ).toBe(false);
  });

  it("is false for a later follow-up in a longer transcript", () => {
    expect(
      isFirstUserMessage([
        { role: "user" },
        { role: "assistant" },
        { role: "user" },
        { role: "assistant" },
      ])
    ).toBe(false);
  });
});
