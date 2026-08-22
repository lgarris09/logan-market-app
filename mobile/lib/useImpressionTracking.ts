import { useEffect, useRef } from "react";

import { InteractionDomain, recordInteraction } from "./interactions";

export type ImpressionTarget = {
  eventId: string;
  entityId: string;
  domain: InteractionDomain;
};

/**
 * Sprint 3.6.7 Block 3: records a real exposure/impression the moment a
 * vessel becomes the Attention Field's focused card -- reusing the field's
 * own existing `focusedId` state (AttentionField.tsx) rather than adding new
 * viewport-tracking UI. Deliberately distinct from card *open* (disclosure
 * === 1, see useCardDwellTracking.ts): a vessel can be focused and never
 * opened, and that's still a real exposure -- generation/serialization into
 * an API response alone is NOT an impression (every item in `items` that
 * never becomes focused records nothing here), but becoming the
 * field's attended-to card is a meaningfully stronger, honest signal than
 * "was present in the response."
 *
 * Fires at most once per distinct `eventId` becoming focused -- swiping back
 * to an already-recorded card does not re-fire (tracked via a ref cache, not
 * per-render), and rendering/re-rendering the same still-focused card on
 * every ~60s poll refresh never fabricates a second impression either.
 */
export function useImpressionTracking(target: ImpressionTarget | null): void {
  const lastRecordedEventIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (!target) return;
    if (lastRecordedEventIdRef.current === target.eventId) return;
    lastRecordedEventIdRef.current = target.eventId;
    recordInteraction({
      eventId: target.eventId,
      entityId: target.entityId,
      domain: target.domain,
      interactionType: "impression",
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target?.eventId]);
}
