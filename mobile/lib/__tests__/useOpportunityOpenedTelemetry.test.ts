import { renderHook } from "@testing-library/react-native";

import { logTelemetryEvent } from "../telemetry";
import {
  OpenedTelemetryTarget,
  useOpportunityOpenedTelemetry,
} from "../useOpportunityOpenedTelemetry";

jest.mock("../telemetry", () => ({
  ...jest.requireActual("../telemetry"),
  logTelemetryEvent: jest.fn(),
}));

const mockedLog = logTelemetryEvent as jest.Mock;

const target: OpenedTelemetryTarget = { eventId: "evt-1" };

describe("useOpportunityOpenedTelemetry", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("logs nothing when nothing is open", () => {
    renderHook(
      ({ t }: { t: OpenedTelemetryTarget | null }) => useOpportunityOpenedTelemetry(t),
      { initialProps: { t: null } }
    );

    expect(mockedLog).not.toHaveBeenCalled();
  });

  it("logs opportunity_opened the moment a card opens", () => {
    renderHook(
      ({ t }: { t: OpenedTelemetryTarget | null }) => useOpportunityOpenedTelemetry(t),
      { initialProps: { t: target as OpenedTelemetryTarget | null } }
    );

    expect(mockedLog).toHaveBeenCalledTimes(1);
    expect(mockedLog).toHaveBeenCalledWith({
      eventName: "opportunity_opened",
      opportunityId: "evt-1",
      sourceSurface: "feed_card",
    });
  });

  it("does not re-fire on repeated polling with the same event_id (new object, same logical target)", () => {
    const { rerender } = renderHook(
      ({ t }: { t: OpenedTelemetryTarget | null }) => useOpportunityOpenedTelemetry(t),
      { initialProps: { t: target } }
    );

    rerender({ t: { ...target } });
    rerender({ t: { ...target } });

    expect(mockedLog).toHaveBeenCalledTimes(1);
  });

  it("fires again for a genuine re-open of the same card after it closed", () => {
    const { rerender } = renderHook(
      ({ t }: { t: OpenedTelemetryTarget | null }) => useOpportunityOpenedTelemetry(t),
      { initialProps: { t: target as OpenedTelemetryTarget | null } }
    );

    rerender({ t: null }); // closed
    rerender({ t: target }); // genuinely reopened

    // Unlike useImpressionTracking's one-time-ever exposure semantics, a
    // real reopen after a real close is a distinct open event each time --
    // this hook never decides whether that counts as a "return" (the
    // backend does, from durable view history).
    expect(mockedLog).toHaveBeenCalledTimes(2);
  });

  it("fires for a different card when focus moves elsewhere", () => {
    const { rerender } = renderHook(
      ({ t }: { t: OpenedTelemetryTarget | null }) => useOpportunityOpenedTelemetry(t),
      { initialProps: { t: target } }
    );

    rerender({ t: { eventId: "evt-2" } });

    expect(mockedLog).toHaveBeenCalledTimes(2);
    expect(mockedLog).toHaveBeenLastCalledWith(
      expect.objectContaining({ opportunityId: "evt-2" })
    );
  });

  it("accepts a custom source surface", () => {
    renderHook(() => useOpportunityOpenedTelemetry(target, "wheel"));

    expect(mockedLog).toHaveBeenCalledWith(
      expect.objectContaining({ sourceSurface: "wheel" })
    );
  });
});
