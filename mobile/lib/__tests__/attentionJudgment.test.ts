import { attentionJudgmentFor, attentionToneFor } from "../attentionJudgment";

describe("attentionJudgmentFor", () => {
  it("maps alert to High attention", () => {
    expect(attentionJudgmentFor("alert")).toBe("High attention");
  });

  it("maps wheel (the field's single focused item) to High attention", () => {
    expect(attentionJudgmentFor("wheel")).toBe("High attention");
  });

  it("maps digest to Worth a look", () => {
    expect(attentionJudgmentFor("digest")).toBe("Worth a look");
  });

  it("maps feed_card to Worth a look", () => {
    expect(attentionJudgmentFor("feed_card")).toBe("Worth a look");
  });

  it("maps background to Developing", () => {
    expect(attentionJudgmentFor("background")).toBe("Developing");
  });
});

describe("attentionToneFor", () => {
  it("maps each judgment to a distinct tone", () => {
    expect(attentionToneFor("High attention")).toBe("high");
    expect(attentionToneFor("Worth a look")).toBe("worth-a-look");
    expect(attentionToneFor("Developing")).toBe("developing");
  });
});
