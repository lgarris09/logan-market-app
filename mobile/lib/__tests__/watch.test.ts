import { fetchJson } from "../apiClient";
import { logTelemetryEvent } from "../telemetry";
import { unwatchOpportunity, watchOpportunity } from "../watch";

jest.mock("../apiClient", () => ({ fetchJson: jest.fn() }));
jest.mock("../telemetry", () => ({ logTelemetryEvent: jest.fn() }));

const mockedFetchJson = fetchJson as jest.Mock;
const mockedLogTelemetryEvent = logTelemetryEvent as jest.Mock;

describe("watchOpportunity", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("posts to /v1/watches with the entity_id and returns the watched state", async () => {
    mockedFetchJson.mockResolvedValue({
      status: "success",
      data: { entity_id: "NVDA", watched: true, created: true },
    });

    const result = await watchOpportunity("NVDA", "evt-1");

    expect(mockedFetchJson).toHaveBeenCalledTimes(1);
    const [path, options] = mockedFetchJson.mock.calls[0];
    expect(path).toBe("/v1/watches");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({ entity_id: "NVDA" });
    expect(result).toEqual({ entityId: "NVDA", watched: true, created: true });
  });

  it("emits watch_created telemetry only when the backend says this call genuinely created the watch", async () => {
    mockedFetchJson.mockResolvedValue({
      status: "success",
      data: { entity_id: "NVDA", watched: true, created: true },
    });

    await watchOpportunity("NVDA", "evt-1");

    expect(mockedLogTelemetryEvent).toHaveBeenCalledTimes(1);
    expect(mockedLogTelemetryEvent).toHaveBeenCalledWith({
      eventName: "watch_created",
      opportunityId: "evt-1",
      sourceSurface: "feed_card",
    });
  });

  it("does not emit watch_created telemetry for an idempotent repeat (created: false)", async () => {
    mockedFetchJson.mockResolvedValue({
      status: "success",
      data: { entity_id: "NVDA", watched: true, created: false },
    });

    const result = await watchOpportunity("NVDA", "evt-1");

    expect(mockedLogTelemetryEvent).not.toHaveBeenCalled();
    expect(result?.created).toBe(false);
  });

  it("never emits telemetry when the request itself fails", async () => {
    mockedFetchJson.mockResolvedValue({ status: "error", message: "network down" });

    const result = await watchOpportunity("NVDA", "evt-1");

    expect(mockedLogTelemetryEvent).not.toHaveBeenCalled();
    expect(result).toBeNull();
  });

  it("returns null on timeout without emitting telemetry", async () => {
    mockedFetchJson.mockResolvedValue({ status: "timeout" });

    const result = await watchOpportunity("NVDA", "evt-1");

    expect(result).toBeNull();
    expect(mockedLogTelemetryEvent).not.toHaveBeenCalled();
  });
});

describe("unwatchOpportunity", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("sends a DELETE to /v1/watches/{entity_id}", async () => {
    mockedFetchJson.mockResolvedValue({
      status: "success",
      data: { entity_id: "NVDA", watched: false, removed: true },
    });

    const result = await unwatchOpportunity("NVDA", "evt-1");

    expect(mockedFetchJson).toHaveBeenCalledTimes(1);
    const [path, options] = mockedFetchJson.mock.calls[0];
    expect(path).toBe("/v1/watches/NVDA");
    expect(options.method).toBe("DELETE");
    expect(result).toEqual({ entityId: "NVDA", watched: false, removed: true });
  });

  it("URL-encodes the entity_id", async () => {
    mockedFetchJson.mockResolvedValue({
      status: "success",
      data: { entity_id: "some id", watched: false, removed: true },
    });

    await unwatchOpportunity("some id", "evt-1");

    expect(mockedFetchJson.mock.calls[0][0]).toBe("/v1/watches/some%20id");
  });

  it("emits watch_removed telemetry only when the backend says this call genuinely removed the watch", async () => {
    mockedFetchJson.mockResolvedValue({
      status: "success",
      data: { entity_id: "NVDA", watched: false, removed: true },
    });

    await unwatchOpportunity("NVDA", "evt-1");

    expect(mockedLogTelemetryEvent).toHaveBeenCalledTimes(1);
    expect(mockedLogTelemetryEvent).toHaveBeenCalledWith({
      eventName: "watch_removed",
      opportunityId: "evt-1",
      sourceSurface: "feed_card",
    });
  });

  it("does not emit watch_removed telemetry for an idempotent repeat (removed: false)", async () => {
    mockedFetchJson.mockResolvedValue({
      status: "success",
      data: { entity_id: "NVDA", watched: false, removed: false },
    });

    await unwatchOpportunity("NVDA", "evt-1");

    expect(mockedLogTelemetryEvent).not.toHaveBeenCalled();
  });

  it("never emits telemetry when the request itself fails", async () => {
    mockedFetchJson.mockResolvedValue({ status: "error", message: "network down" });

    const result = await unwatchOpportunity("NVDA", "evt-1");

    expect(mockedLogTelemetryEvent).not.toHaveBeenCalled();
    expect(result).toBeNull();
  });
});
