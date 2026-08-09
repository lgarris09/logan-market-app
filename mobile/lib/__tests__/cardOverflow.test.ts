import { shouldShowOverflowFade } from "../cardOverflow";

describe("shouldShowOverflowFade", () => {
  it("is false when content fits entirely within the container", () => {
    expect(shouldShowOverflowFade(200, 300)).toBe(false);
    expect(shouldShowOverflowFade(300, 300)).toBe(false);
  });

  it("is true once content meaningfully exceeds the container", () => {
    expect(shouldShowOverflowFade(400, 300)).toBe(true);
  });

  it("ignores float-level differences under the epsilon", () => {
    expect(shouldShowOverflowFade(301, 300)).toBe(false);
  });

  it("is false before real measurements arrive (container height 0)", () => {
    // Sprint 3.6 (section 7): onLayout/onContentSizeChange haven't fired yet
    // on first render -- must not flash a fade before real numbers exist.
    expect(shouldShowOverflowFade(500, 0)).toBe(false);
  });
});
