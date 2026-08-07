import { useEffect, useMemo, useRef, useState } from "react";
import { Animated, LayoutChangeEvent, PanResponder, StyleSheet, View } from "react-native";

import { useReducedMotion } from "../hooks/useReducedMotion";
import { computeAtmosphereLayout, defaultFocus, shiftFocus } from "../lib/attentionLayout";
import { FeedItem } from "../types/loganFeed";
import { Vessel } from "./Vessel";

const SWIPE_THRESHOLD = 56;
const READING_WIDTH_RATIO = 0.76;

type Disclosure = 0 | 1 | 2;

// Logan's home screen. There is no card, no panel, no object placed on top
// of a background -- every entity is a vessel in one continuous medium,
// always alive (drifting, breathing with its own confidence, pulsing with
// its own priority). Focus decides which vessel is allowed to speak; tapping
// it again lets it condense further into words; tapping elsewhere, or
// swiping to another vessel, lets it dissolve back into pure atmosphere.
// Moving focus sends a real disturbance through the medium: whatever is
// connected to the newly focused vessel visibly echoes a moment later.
export function AttentionField({ items }: { items: FeedItem[] }) {
  const [width, setWidth] = useState(0);
  const [focusedId, setFocusedId] = useState<string | null>(
    () => defaultFocus(items)?.event_id ?? null
  );
  const [disclosure, setDisclosure] = useState<Disclosure>(0);

  useEffect(() => {
    if (!focusedId && items.length > 0) setFocusedId(defaultFocus(items)?.event_id ?? null);
  }, [items, focusedId]);

  const layouts = useMemo(() => computeAtmosphereLayout(items), [items]);
  const reducedMotion = useReducedMotion();

  const echoSignals = useRef(new Map<string, Animated.Value>()).current;
  const echoSignalFor = (eventId: string): Animated.Value => {
    let value = echoSignals.get(eventId);
    if (!value) {
      value = new Animated.Value(0);
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
    origin.setValue(0);
    Animated.timing(origin, { toValue: 1, duration: 260, useNativeDriver: true }).start(() => {
      Animated.timing(origin, { toValue: 0, duration: 550, useNativeDriver: true }).start();
    });

    focused.connected_event_ids.forEach((connectedId, index) => {
      if (!items.some((item) => item.event_id === connectedId)) return;
      const echo = echoSignalFor(connectedId);
      echo.setValue(0);
      Animated.sequence([
        Animated.delay(160 + index * 130),
        Animated.timing(echo, { toValue: 1, duration: 320, useNativeDriver: true }),
        Animated.timing(echo, { toValue: 0, duration: 650, useNativeDriver: true }),
      ]).start();
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusedId, reducedMotion]);

  const handlePress = (item: FeedItem) => {
    if (item.event_id !== focusedId) {
      setFocusedId(item.event_id);
      setDisclosure(0);
    } else {
      setDisclosure((current) => ((current + 1) % 3) as Disclosure);
    }
  };

  const panResponder = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponder: (_, gesture) =>
        Math.abs(gesture.dx) > 12 && Math.abs(gesture.dx) > Math.abs(gesture.dy),
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

  return (
    <View
      style={styles.fill}
      onLayout={(e: LayoutChangeEvent) => setWidth(e.nativeEvent.layout.width)}
      {...panResponder.panHandlers}
    >
      {width > 0 &&
        items.map((item) => {
          const layout = layouts.get(item.event_id);
          if (!layout) return null;
          const isFocused = item.event_id === focusedId;
          return (
            <Vessel
              key={item.event_id}
              item={item}
              layout={layout}
              isFocused={isFocused}
              disclosure={isFocused ? disclosure : 0}
              readingWidth={readingWidth}
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
