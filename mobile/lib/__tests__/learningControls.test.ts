import { getLearningSummary, suppressLearningReason } from "../learningControls";
import { fetchJson } from "../apiClient";

jest.mock("../apiClient", () => ({
  fetchJson: jest.fn(),
}));

describe("getLearningSummary", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it("maps the backend's snake_case summary into the mobile shape", async () => {
    (fetchJson as jest.Mock).mockResolvedValueOnce({
      status: "success",
      data: {
        schema_version: "1.0",
        user_id: "user-1",
        generated_at: "2026-09-04T12:00:00Z",
        traits: [
          {
            entity_id: "AAPL",
            description: "You tend to care more about AAPL than most stocks STRATUS tracks.",
            basis: "explicit",
            can_suppress: true,
          },
          {
            entity_id: "TSLA",
            description: "STRATUS has noticed a pattern of returning to TSLA.",
            basis: "inferred",
            can_suppress: true,
          },
        ],
        explanation:
          "This reflects only what you've explicitly told STRATUS or how you've used the app.",
      },
    });

    const result = await getLearningSummary();

    expect(fetchJson).toHaveBeenCalledWith("/v1/learning/summary");
    expect(result).toEqual({
      generatedAt: "2026-09-04T12:00:00Z",
      traits: [
        {
          entityId: "AAPL",
          description: "You tend to care more about AAPL than most stocks STRATUS tracks.",
          basis: "explicit",
          canSuppress: true,
        },
        {
          entityId: "TSLA",
          description: "STRATUS has noticed a pattern of returning to TSLA.",
          basis: "inferred",
          canSuppress: true,
        },
      ],
      explanation:
        "This reflects only what you've explicitly told STRATUS or how you've used the app.",
    });
  });

  it("returns an empty-but-valid summary for a fresh user with nothing learned yet", async () => {
    (fetchJson as jest.Mock).mockResolvedValueOnce({
      status: "success",
      data: {
        schema_version: "1.0",
        user_id: "user-1",
        generated_at: "2026-09-04T12:00:00Z",
        traits: [],
        explanation:
          "This reflects only what you've explicitly told STRATUS or how you've used the app.",
      },
    });

    const result = await getLearningSummary();

    expect(result?.traits).toEqual([]);
  });

  it("returns null when the backend call fails", async () => {
    (fetchJson as jest.Mock).mockResolvedValueOnce({ status: "error", message: "boom" });

    const result = await getLearningSummary();

    expect(result).toBeNull();
  });

  it("returns null on a timeout", async () => {
    (fetchJson as jest.Mock).mockResolvedValueOnce({ status: "timeout" });

    const result = await getLearningSummary();

    expect(result).toBeNull();
  });
});

describe("suppressLearningReason", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it("posts the entity_id and returns true on a confirmed suppression", async () => {
    (fetchJson as jest.Mock).mockResolvedValueOnce({
      status: "success",
      data: { entity_id: "AAPL", suppressed: true },
    });

    const result = await suppressLearningReason("AAPL");

    expect(fetchJson).toHaveBeenCalledWith(
      "/v1/learning/suppress",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ entity_id: "AAPL" }),
      })
    );
    expect(result).toBe(true);
  });

  it("returns false when the backend call fails", async () => {
    (fetchJson as jest.Mock).mockResolvedValueOnce({ status: "error", message: "boom" });

    const result = await suppressLearningReason("AAPL");

    expect(result).toBe(false);
  });

  it("returns false if the backend responds without confirming suppression", async () => {
    (fetchJson as jest.Mock).mockResolvedValueOnce({
      status: "success",
      data: { entity_id: "AAPL", suppressed: false },
    });

    const result = await suppressLearningReason("AAPL");

    expect(result).toBe(false);
  });
});
