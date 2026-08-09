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
import { computeAtmosphereLayout, defaultFocus, shiftFocus } from "../lib/attentionLayout";
import { FeedItem } from "../types/loganFeed";
import { AttentionAtmosphere } from "./atmosphere/AttentionAtmosphere";
import { CARD_HEIGHT, CARD_SAFE_MARGIN, Vessel } from "./Vessel";

const SWIPE_THRESHOLD = 56;
const READING_WIDTH_RATIO = 0.82;

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
}: {
  items: FeedItem[];
  /** Opens a specific vessel's card on request, reusing the exact same
   * focus/disclosure state a direct tap would set -- see the effect below.
   * Silently ignored if the requested eventId isn't in the current items
   * (e.g. a dev-only test notification with no real backing item). */
  openRequest?: OpenRequest | null;
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
        <AttentionAtmosphere
          items={items}
          layouts={layouts}
          width={width}
          height={height}
          dampened={anyExpanded}
        />
      )}

      {width > 0 &&
        items.map((item) => {
          const layout = layouts.get(item.event_id);
          if (!layout) return null;
          const isFocused = item.event_id === focusedId;
          const isDimmed = focusedId !== null && disclosure > 0 && !isFocused;

          // Clamp the card's eventual on-screen center (not the vessel's own
          // resting position) into a safe reading region, with margins. If
          // the field is too narrow/short for any valid clamp range (a
          // degenerate size), fall back to the field's own center rather
          // than an inverted range.
          const anchorX = layout.x * width;
          const anchorY = layout.y * height;
          const cardHalfW = readingWidth / 2;
          const cardHalfH = Math.min(CARD_HEIGHT, maxCardHeight) / 2;
          const minCenterX = CARD_SAFE_MARGIN + cardHalfW;
          const maxCenterX = width - CARD_SAFE_MARGIN - cardHalfW;
          const minCenterY = CARD_SAFE_MARGIN + cardHalfH;
          const maxCenterY = height - CARD_SAFE_MARGIN - cardHalfH;
          const safeX =
            minCenterX <= maxCenterX
              ? Math.min(Math.max(anchorX, minCenterX), maxCenterX)
              : width / 2;
          const safeY =
            minCenterY <= maxCenterY
              ? Math.min(Math.max(anchorY, minCenterY), maxCenterY)
              : height / 2;

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
              onPress={() => handlePress(item)}
            />
          );
        })}
    </View>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
});
