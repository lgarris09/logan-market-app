import { useEffect, useRef } from "react";
import { AppState, AppStateStatus } from "react-native";

import { InteractionDomain, recordInteraction } from "./interactions";

export type DwellTarget = {
  eventId: string;
  entityId: string;
  domain: InteractionDomain;
};

/**
 * Measures real open->close dwell time for one Opportunity Card and submits
 * it once, at close, as a single "view" interaction with the measured
 * duration_ms -- reusing the existing, unmodified FeedbackEngine dwell
 * thresholds (view+duration_ms>=8000 -> interested, etc; see
 * logan_core/feedback/engine.py) rather than inventing new ones here.
 * Rendering a card never counts by itself -- only a real open leading to a
 * close/replace/unmount/background span does.
 *
 * `target` must be null whenever no card is open, and the {eventId,
 * entityId, domain} of the currently open card otherwise. The effect
 * deliberately depends only on `target?.eventId` (a stable primitive), not
 * the `target` object itself -- a new object is constructed every render
 * (including on every poll refresh) even when the logically open card
 * hasn't changed, so depending on the object reference would fabricate a
 * fresh "open" on every poll.
 */
export function useCardDwellTracking(target: DwellTarget | null): void {
  const openedAtRef = useRef<number | null>(null);
  const appStateRef = useRef<AppStateStatus>(AppState.currentState);

  useEffect(() => {
    if (!target) return;

    openedAtRef.current = Date.now();

    const flush = () => {
      if (openedAtRef.current === null) return;
      const durationMs = Date.now() - openedAtRef.current;
      openedAtRef.current = null;
      recordInteraction({
        eventId: target.eventId,
        entityId: target.entityId,
        domain: target.domain,
        interactionType: "view",
        durationMs,
      });
    };

    const subscription = AppState.addEventListener("change", (nextState) => {
      const prevState = appStateRef.current;
      appStateRef.current = nextState;

      if (prevState === "active" && nextState !== "active") {
        // Backgrounding: submit what's been measured so far, then stop
        // measuring until (if ever) foreground returns -- background time
        // must never count toward dwell.
        flush();
      } else if (prevState !== "active" && nextState === "active") {
        // Foreground return: resume measuring the same still-open target.
        // Deliberately emits nothing here -- only flush() (backgrounding,
        // close, replace, or unmount) submits a signal, so resuming is
        // never mistaken for a fresh card open.
        openedAtRef.current = Date.now();
      }
    });

    // React fires this cleanup both when `target.eventId` changes (card
    // closed or replaced by a different card) and on unmount -- exactly the
    // two remaining cases (besides backgrounding, handled above) that must
    // flush the real measured duration exactly once, with no double-submit.
    return () => {
      subscription.remove();
      flush();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target?.eventId]);
}
