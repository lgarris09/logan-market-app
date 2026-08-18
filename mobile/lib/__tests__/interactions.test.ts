import { fetchJson } from "../apiClient";
import { recordInteraction } from "../interactions";

jest.mock("../apiClient", () => ({ fetchJson: jest.fn() }));

const mockedFetchJson = fetchJson as jest.Mock;

describe("recordInteraction", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("posts to /v1/interactions with the given fields, fire-and-forget with no retry", () => {
    recordInteraction({
      eventId: "evt-1",
      entityId: "NVDA",
      domain: "stocks",
      interactionType: "view",
      durationMs: 9000,
    });

    expect(mockedFetchJson).toHaveBeenCalledWith(
      "/v1/interactions",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event_id: "evt-1",
          entity_id: "NVDA",
          domain: "stocks",
          interaction_type: "view",
          duration_ms: 9000,
        }),
        retries: 0,
      })
    );
  });

  it("omits duration_ms when not provided (e.g. a notification-open click)", () => {
    recordInteraction({
      eventId: "evt-2",
      entityId: "FED",
      domain: "stocks",
      interactionType: "click",
    });

    const body = JSON.parse(mockedFetchJson.mock.calls[0][1].body);
    expect(body.duration_ms).toBeUndefined();
    expect(body.interaction_type).toBe("click");
    expect(body.event_id).toBe("evt-2");
  });
});
