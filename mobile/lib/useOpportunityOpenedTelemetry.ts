import { useEffect } from "react";

import { logTelemetryEvent, TelemetrySourceSurface } from "./telemetry";

export type OpenedTelemetryTarget = {
  eventId: string;
};

/**
 * V2.3C Telemetry: records a real card open, exactly once per open (not
 * once per render while it stays open) -- depends only on the stable
 * eventId primitive, mirroring useCardDwellTracking's own dependency-array
 * reasoning (a new object is constructed every render, including on every
 * poll refresh, even when the logically open card hasn't changed).
 *
 * Deliberately no ref-based "have I ever recorded this eventId" cache
 * (contrast useImpressionTracking, which suppresses re-focusing an
 * already-recorded card): a genuine re-open of the same card after closing
 * it is a real, distinct open event each time, not a one-time exposure --
 * this hook's job is to report that raw fact, never to decide whether it
 * counts as a "return" (the backend does that from this user's own durable
 * view history -- see backend/app/telemetry.py's promotion logic).
 */
export function useOpportunityOpenedTelemetry(
  target: OpenedTelemetryTarget | null,
  sourceSurface: TelemetrySourceSurface = "feed_card"
): void {
  useEffect(() => {
    if (!target) return;
    logTelemetryEvent({
      eventName: "opportunity_opened",
      opportunityId: target.eventId,
      sourceSurface,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target?.eventId]);
}
