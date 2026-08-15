import { useEffect, useMemo, useRef, useState } from "react";
import { LayoutChangeEvent, PanResponder, StyleSheet, View } from "react-native";
import {
  makeMutable,
  SharedValue,
  withDelay,
  withSequence,
  withTiming,
} from "react-native-reanimated";

import { useReducedMotion } from "../hooks/useReducedMotion";
import {
  computeAtmosphereLayout,
  defaultFocus,
  shiftFocus,
  VesselLayout,
} from "../lib/attentionLayout";
import { biasStateFor, FieldBias } from "../lib/fieldBias";
import { FeedItem } from "../types/loganFeed";
import { AttentionAtmosphere } from "./atmosphere/AttentionAtmosphere";
import { CARD_HEIGHT, CARD_SAFE_MARGIN, Vessel } from "./Vessel";

const SWIPE_THRESHOLD = 56;
// Opportunity Card redesign (owner device feedback): 0.82 -> 0.87 still read
// as "could be wider" -- one more step to 0.91. Still leaves CARD_SAFE_MARGIN
// on each side (verified against a real phone's minimum width, not just the
// common case) rather than going edge-to-edge.
const READING_WIDTH_RATIO = 0.91;
// Must comfortably exceed Vessel.tsx's own exit-fade duration (420ms, or
// 160ms under reduced motion) -- this is how long a departed vessel keeps
// rendering (frozen at its last known position) after leaving `items`, so
// it can fade out instead of vanishing the instant a poll drops it.
const EXIT_HOLD_MS = 480;
const EXIT_HOLD_REDUCED_MOTION_MS = 220;

/** A vessel that has left the live feed but is still on-screen, fading
 * out -- frozen at its last known item content/layout, since it's no
 * longer present in `items`/`layouts` to look either up fresh. */
type DepartedVessel = { item: FeedItem; layout: VesselLayout };

type Disclosure = 0 | 1;

// An external request to open a specific vessel's Opportunity Card (e.g.
// from the header's notification dropdown, not a tap inside the field
// itself). `token` changes on every request (even for the same eventId) so
// the effect below fires even if the same card is requested twice in a row.
export type OpenRequest = { eventId: string; token: number };

// Logan's home screen. There is no card, no panel, no object placed on top
// of a background -- every entity is a vessel in one continuous medium,
// always alive (drifting, breathing with its own confidence, pulsing with
// its own priority). Focus decides which vessel is allowed to speak; tapping
// it opens its Opportunity Card, tapping it again (or moving focus to
// another vessel) lets it dissolve back into pure atmosphere. Moving focus
// sends a real disturbance through the medium: whatever is connected to the
// newly focused vessel visibly echoes a moment later.
export function AttentionField({
  items,
  openRequest,
  fieldBias = "all",
}: {
  items: FeedItem[];
  /** Opens a specific vessel's card on request, reusing the exact same
   * focus/disclosure state a direct tap would set -- see the effect below.
   * Silently ignored if the requested eventId isn't in the current items
   * (e.g. a dev-only test notification with no real backing item). */
  openRequest?: OpenRequest | null;
  /** FIELD BIAS: a presentation-only lens (see lib/fieldBias.ts and
   * FieldBiasControl.tsx), never a filter -- every item in `items` is
   * still rendered as a Vessel regardless of this value. "all" (the
   * default) is fully neutral, matching every item, so omitting this prop
   * entirely reproduces the pre-FIELD-BIAS field exactly. */
  fieldBias?: FieldBias;
}) {
  const [{ width, height }, setDimensions] = useState({ width: 0, height: 0 });
  const [focusedId, setFocusedId] = useState<string | null>(
    () => defaultFocus(items)?.event_id ?? null
  );
  const [disclosure, setDisclosure] = useState<Disclosure>(0);

  useEffect(() => {
    if (!focusedId && items.length > 0) setFocusedId(defaultFocus(items)?.event_id ?? null);
  }, [items, focusedId]);

  useEffect(() => {
    if (!openRequest) return;
    if (!items.some((item) => item.event_id === openRequest.eventId)) return;
    setFocusedId(openRequest.eventId);
    setDisclosure(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [openRequest]);

  const layouts = useMemo(
    () => computeAtmosphereLayout(items, width, height),
    [items, width, height]
  );
  const reducedMotion = useReducedMotion();

  // Attention Gravity: continuity means a departed event_id shouldn't just
  // vanish the instant a poll drops it -- it keeps rendering, frozen at its
  // last known item/layout (both are gone from `items`/`layouts` the
  // moment it's no longer live, so there's nothing fresh to look up), long
  // enough for Vessel.tsx's own exit-fade to actually play. `departed` is
  // real state (not a ref) so removal after the hold re-renders; the timer
  // handles live in a ref so they can be cancelled on unmount or if the
  // same event_id reappears before its hold finishes.
  const [departed, setDeparted] = useState<Map<string, DepartedVessel>>(new Map());
  const departureTimers = useRef(new Map<string, ReturnType<typeof setTimeout>>()).current;
  const prevItemsRef = useRef<FeedItem[]>(items);
  const prevLayoutsRef = useRef<Map<string, VesselLayout>>(layouts);

  useEffect(() => {
    const prevItems = prevItemsRef.current;
    const prevLayouts = prevLayoutsRef.current;
    const currentIds = new Set(items.map((item) => item.event_id));

    const justDeparted: DepartedVessel[] = [];
    for (const prevItem of prevItems) {
      if (currentIds.has(prevItem.event_id)) continue;
      const prevLayout = prevLayouts.get(prevItem.event_id);
      if (!prevLayout) continue;
      justDeparted.push({ item: prevItem, layout: prevLayout });
    }

    if (justDeparted.length > 0) {
      setDeparted((current) => {
        const next = new Map(current);
        for (const entry of justDeparted) next.set(entry.item.event_id, entry);
        return next;
      });
      const holdMs = reducedMotion ? EXIT_HOLD_REDUCED_MOTION_MS : EXIT_HOLD_MS;
      for (const entry of justDeparted) {
        const id = entry.item.event_id;
        const existing = departureTimers.get(id);
        if (existing) clearTimeout(existing);
        departureTimers.set(
          id,
          setTimeout(() => {
            departureTimers.delete(id);
            setDeparted((current) => {
              if (!current.has(id)) return current;
              const next = new Map(current);
              next.delete(id);
              return next;
            });
          }, holdMs)
        );
      }
    }

    // An event_id that reappears before its hold finishes just resumes as
    // a normal live vessel -- cancel the pending removal rather than
    // fading it out and immediately back in.
    let anyReappeared = false;
    departed.forEach((_, id) => {
      if (currentIds.has(id)) anyReappeared = true;
    });
    if (anyReappeared) {
      setDeparted((current) => {
        const next = new Map(current);
        currentIds.forEach((id) => next.delete(id));
        return next;
      });
      currentIds.forEach((id) => {
        const timer = departureTimers.get(id);
        if (timer) {
          clearTimeout(timer);
          departureTimers.delete(id);
        }
      });
    }

    prevItemsRef.current = items;
    prevLayoutsRef.current = layouts;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items, layouts, reducedMotion]);

  useEffect(() => {
    return () => {
      departureTimers.forEach((timer) => clearTimeout(timer));
      departureTimers.clear();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // V3.1.4.1: ported from classic Animated.Value to Reanimated's makeMutable
  // (the same underlying primitive useSharedValue uses, minus the hook --
  // needed here because these are created lazily per event_id in a plain
  // Map, not up front in a fixed set of hook calls). This keeps the ripple
  // on the same UI-thread-driven animation system as Vessel.tsx now uses,
  // rather than mixing two animation libraries across a single prop.
  const echoSignals = useRef(new Map<string, SharedValue<number>>()).current;
  const echoSignalFor = (eventId: string): SharedValue<number> => {
    let value = echoSignals.get(eventId);
    if (!value) {
      value = makeMutable(0);
      echoSignals.set(eventId, value);
    }
    return value;
  };

  // A disturbance in the medium: the newly-focused vessel flashes at the
  // origin, and everything it's connected to echoes a beat later, decaying
  // outward -- this is how relatedness is felt, never drawn as a line.
  useEffect(() => {
    if (!focusedId) return;
    // Purely decorative: relatedness is still conveyed by which vessel gains
    // focus and its own disclosure state, so under reduced motion the ripple is
    // skipped entirely rather than sped up.
    if (reducedMotion) return;
    const focused = items.find((item) => item.event_id === focusedId);
    if (!focused) return;

    const origin = echoSignalFor(focusedId);
    origin.value = 0;
    origin.value = withSequence(withTiming(1, { duration: 260 }), withTiming(0, { duration: 550 }));

    focused.connected_event_ids.forEach((connectedId, index) => {
      if (!items.some((item) => item.event_id === connectedId)) return;
      const echo = echoSignalFor(connectedId);
      echo.value = 0;
      echo.value = withDelay(
        160 + index * 130,
        withSequence(withTiming(1, { duration: 320 }), withTiming(0, { duration: 650 }))
      );
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusedId, reducedMotion]);

  const handlePress = (item: FeedItem) => {
    if (item.event_id !== focusedId) {
      setFocusedId(item.event_id);
      setDisclosure(1);
    } else {
      setDisclosure((current) => (current === 0 ? 1 : 0));
    }
  };

  const panResponder = useRef(
    PanResponder.create({
      // Explicit false (matches the default) so there is no ambiguity: this
      // never claims a plain tap, only a clear horizontal drag past the
      // threshold below.
      onStartShouldSetPanResponder: () => false,
      onMoveShouldSetPanResponder: (_, gesture) =>
        Math.abs(gesture.dx) > 12 && Math.abs(gesture.dx) > Math.abs(gesture.dy),
      // iOS-specific: without this, PanResponder can suppress native gesture
      // recognition (which Pressable relies on) for the whole subtree it
      // wraps, even on touches it never claims -- a known cause of "taps do
      // nothing" when a PanResponder wraps Pressable children. This is the
      // Sprint 3.5 device-validation fix for that failure mode.
      onShouldBlockNativeResponder: () => false,
      onPanResponderTerminationRequest: () => true,
      onPanResponderRelease: (_, gesture) => {
        if (!focusedId) return;
        if (gesture.dx <= -SWIPE_THRESHOLD) {
          const next = shiftFocus(items, focusedId, 1);
          if (next) {
            setFocusedId(next.event_id);
            setDisclosure(0);
          }
        } else if (gesture.dx >= SWIPE_THRESHOLD) {
          const prev = shiftFocus(items, focusedId, -1);
          if (prev) {
            setFocusedId(prev.event_id);
            setDisclosure(0);
          }
        }
      },
    })
  ).current;

  const readingWidth = width * READING_WIDTH_RATIO;
  // Round 2 (real-device screenshots): the card could previously grow to a
  // fixed height regardless of how much room the field actually had,
  // rendering partially off-screen near the top/bottom edge. Capping it to
  // the real measured field height (minus safe margins) is what lets
  // Vessel.tsx fall back to its internal ScrollView instead.
  const maxCardHeight = Math.max(220, height - CARD_SAFE_MARGIN * 2);
  const anyExpanded = disclosure > 0;

  // FIELD BIAS paint order: when a lens is active, emphasized items render
  // after (on top of) neutral/receded ones for this pass, so an emphasized
  // vessel's slight scale-up is never clipped under a neighbor. Safe to
  // reorder purely for iteration -- each <Vessel> below keys off the stable
  // event_id (not array position), so this never causes a remount, and
  // `items` itself (used for departure-tracking, focus, echo signals
  // elsewhere in this component) is untouched. "all" keeps the original
  // order exactly, matching the pre-FIELD-BIAS render.
  const renderItems =
    fieldBias === "all"
      ? items
      : [...items].sort(
          (a, b) =>
            Number(biasStateFor(a, fieldBias) === "emphasized") -
            Number(biasStateFor(b, fieldBias) === "emphasized")
        );

  return (
    <View
      style={styles.fill}
      onLayout={(e: LayoutChangeEvent) =>
        setDimensions({
          width: e.nativeEvent.layout.width,
          height: e.nativeEvent.layout.height,
        })
      }
      {...panResponder.panHandlers}
    >
      {width > 0 && (
        <AttentionAtmosphere items={items} width={width} height={height} dampened={anyExpanded} />
      )}

      {width > 0 &&
        renderItems.map((item) => {
          const layout = layouts.get(item.event_id);
          if (!layout) return null;
          const isFocused = item.event_id === focusedId;
          const isDimmed = focusedId !== null && disclosure > 0 && !isFocused;
          // FIELD BIAS: presentation-only emphasis, never a filter -- every
          // item still renders. See lib/fieldBias.ts and Vessel.tsx's own
          // biasState handling for the "recede but stay visible" guarantee.
          const biasState = biasStateFor(item, fieldBias);

          // Every opened card lands at the same fixed point -- the field's
          // own center -- regardless of which vessel was tapped or where it
          // happens to sit (owner request: opening a card from the edge of
          // the field used to detach only as far as the nearest safe
          // reading region, so different opportunities could land in
          // visibly different spots; that inconsistency is what this
          // replaces). The vessel's own natural position (`anchorX/anchorY`)
          // no longer factors into where the card lands at all -- only
          // cardOffsetX/Y (safeX/Y minus anchorX/Y) does, and Vessel.tsx
          // only applies that offset once disclosureAnim actually starts
          // moving toward 1, so the glow/label still stay exactly where
          // Attention Gravity placed them at rest.
          const anchorX = layout.x * width;
          const anchorY = layout.y * height;
          const safeX = width / 2;
          // Owner device feedback: the card's bottom-edge position was
          // already right (vertically centering left CARD_SAFE_MARGIN of
          // clearance below it, same as above) -- growing CARD_HEIGHT
          // should extend the card *upward*, toward the header, not
          // symmetrically in both directions. Anchoring the target center
          // to a fixed bottom edge (rather than the field's vertical
          // center) does that: as cardHalfH grows toward maxCardHeight/2,
          // the center moves up to compensate, keeping the bottom edge
          // fixed at height - CARD_SAFE_MARGIN regardless of how tall the
          // card ends up. Mirrors Vessel.tsx's own
          // Math.min(CARD_HEIGHT, maxCardHeight) exactly so this position
          // math never assumes a height the card doesn't actually render at.
          const cardHalfH = Math.min(CARD_HEIGHT, maxCardHeight) / 2;
          const safeY = height - CARD_SAFE_MARGIN - cardHalfH;

          return (
            <Vessel
              key={item.event_id}
              item={item}
              layout={layout}
              isFocused={isFocused}
              disclosure={isFocused ? disclosure : 0}
              isDimmed={isDimmed}
              readingWidth={readingWidth}
              cardOffsetX={safeX - anchorX}
              cardOffsetY={safeY - anchorY}
              maxCardHeight={maxCardHeight}
              echoSignal={echoSignalFor(item.event_id)}
              fieldWidth={width}
              fieldHeight={height}
              biasState={biasState}
              onPress={() => handlePress(item)}
            />
          );
        })}

      {/* Departed vessels: still fading out (see the departure-tracking
          effect above), frozen at their last known item/layout since
          they're no longer present in `items`/`layouts`. Never focusable,
          never interactive, no card -- only Vessel.tsx's own exit-fade
          matters here. */}
      {width > 0 &&
        Array.from(departed.values()).map(({ item, layout }) => (
          <Vessel
            key={item.event_id}
            item={item}
            layout={layout}
            isFocused={false}
            disclosure={0}
            isDimmed={anyExpanded}
            readingWidth={readingWidth}
            cardOffsetX={0}
            cardOffsetY={0}
            maxCardHeight={maxCardHeight}
            echoSignal={echoSignalFor(item.event_id)}
            fieldWidth={width}
            fieldHeight={height}
            biasState="neutral"
            isExiting
            onPress={() => {}}
          />
        ))}
    </View>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
});
