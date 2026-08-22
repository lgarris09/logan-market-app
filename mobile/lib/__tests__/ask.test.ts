import { fetchJson } from "../apiClient";
import { askStratus, createAskSessionId } from "../ask";

jest.mock("../apiClient", () => ({ fetchJson: jest.fn() }));

const mockedFetchJson = fetchJson as jest.Mock;

describe("askStratus", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("posts message + event_id + session_id, fire-with-no-retry, for a contextual question", async () => {
    mockedFetchJson.mockResolvedValue({
      status: "success",
      data: { answer: "Grounded answer.", event_id: "evt-1", session_id: "sess-1", grounded: true },
    });

    await askStratus({ message: "What changed?", eventId: "evt-1", sessionId: "sess-1" });

    expect(mockedFetchJson).toHaveBeenCalledWith(
      "/v1/ask",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: "What changed?",
          event_id: "evt-1",
          session_id: "sess-1",
        }),
        retries: 0,
      })
    );
  });

  it("posts without event_id/session_id for a generic question", async () => {
    mockedFetchJson.mockResolvedValue({
      status: "success",
      data: { answer: "Generic answer.", event_id: null, session_id: null, grounded: false },
    });

    await askStratus({ message: "hello" });

    const body = JSON.parse(mockedFetchJson.mock.calls[0][1].body);
    expect(body.event_id).toBeUndefined();
    expect(body.session_id).toBeUndefined();
  });

  it("maps a successful response to camelCase output", async () => {
    mockedFetchJson.mockResolvedValue({
      status: "success",
      data: { answer: "Grounded answer.", event_id: "evt-1", session_id: "sess-1", grounded: true },
    });

    const result = await askStratus({ message: "What changed?", eventId: "evt-1" });

    expect(result).toEqual({
      status: "success",
      data: {
        answer: "Grounded answer.",
        eventId: "evt-1",
        sessionId: "sess-1",
        grounded: true,
      },
    });
  });

  it("passes through non-success results unchanged", async () => {
    mockedFetchJson.mockResolvedValue({ status: "timeout" });

    const result = await askStratus({ message: "hello" });

    expect(result).toEqual({ status: "timeout" });
  });
});

describe("createAskSessionId", () => {
  it("returns a non-empty string", () => {
    expect(typeof createAskSessionId()).toBe("string");
    expect(createAskSessionId().length).toBeGreaterThan(0);
  });

  it("returns a distinct value on each call", () => {
    const ids = new Set([createAskSessionId(), createAskSessionId(), createAskSessionId()]);
    expect(ids.size).toBe(3);
  });
});
