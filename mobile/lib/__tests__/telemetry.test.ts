import { fetchJson } from "../apiClient";
import { logTelemetryEvent, TELEMETRY_SCHEMA_VERSION } from "../telemetry";

jest.mock("../apiClient", () => ({ fetchJson: jest.fn() }));
jest.mock("expo-crypto", () => ({ randomUUID: jest.fn(() => "generated-uuid") }));

const mockedFetchJson = fetchJson as jest.Mock;
const mockedRandomUUID = jest.requireMock("expo-crypto").randomUUID as jest.Mock;

describe("logTelemetryEvent", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("posts a correctly-serialized request body to /v1/telemetry/events", () => {
    mockedFetchJson.mockResolvedValue({ status: "success", data: {} });

    logTelemetryEvent({
      eventName: "watch_created",
      opportunityId: "evt-1",
      sourceSurface: "feed_card",
    });

    expect(mockedFetchJson).toHaveBeenCalledTimes(1);
    const [path, options] = mockedFetchJson.mock.calls[0];
    expect(path).toBe("/v1/telemetry/events");
    expect(options.method).toBe("POST");
    expect(options.retries).toBe(0);

    const body = JSON.parse(options.body);
    expect(body.event_id).toBe("generated-uuid");
    expect(body.schema_version).toBe(TELEMETRY_SCHEMA_VERSION);
    expect(body.event_name).toBe("watch_created");
    expect(body.opportunity_id).toBe("evt-1");
    expect(body.source_surface).toBe("feed_card");
    expect(typeof body.occurred_at).toBe("string");
  });

  it("serializes context fields in snake_case for the backend contract", () => {
    mockedFetchJson.mockResolvedValue({ status: "success", data: {} });

    logTelemetryEvent({
      eventName: "ask_follow_up",
      context: { askSessionId: "session-123" },
    });

    const body = JSON.parse(mockedFetchJson.mock.calls[0][1].body);
    expect(body.context).toEqual({ ask_session_id: "session-123", useful: undefined });
  });

  it("generates a distinct event_id per call", () => {
    mockedRandomUUID.mockReturnValueOnce("uuid-1").mockReturnValueOnce("uuid-2");
    mockedFetchJson.mockResolvedValue({ status: "success", data: {} });

    logTelemetryEvent({ eventName: "watch_removed", opportunityId: "evt-1" });
    logTelemetryEvent({ eventName: "watch_removed", opportunityId: "evt-1" });

    const firstBody = JSON.parse(mockedFetchJson.mock.calls[0][1].body);
    const secondBody = JSON.parse(mockedFetchJson.mock.calls[1][1].body);
    expect(firstBody.event_id).not.toBe(secondBody.event_id);
  });

  it("never throws even when the underlying request fails", () => {
    mockedFetchJson.mockRejectedValue(new Error("network down"));

    expect(() =>
      logTelemetryEvent({ eventName: "watch_removed", opportunityId: "evt-1" })
    ).not.toThrow();
  });

  it("is fire-and-forget -- callers never need to await it", () => {
    mockedFetchJson.mockReturnValue(new Promise(() => {})); // never resolves

    const start = Date.now();
    logTelemetryEvent({ eventName: "watch_removed", opportunityId: "evt-1" });
    expect(Date.now() - start).toBeLessThan(50);
  });
});
