import { useEffect, useState } from "react";
import { LayoutChangeEvent, Pressable, StyleSheet, Text, View } from "react-native";
import Svg, { Path } from "react-native-svg";
import Animated, {
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withTiming,
} from "react-native-reanimated";

import { font, spacing, theme, tracking } from "../constants/theme";
import { FieldBias } from "../lib/fieldBias";

const LABELS: { value: FieldBias; label: string }[] = [
  { value: "all", label: "ALL" },
  { value: "markets", label: "MARKETS" },
  { value: "odds", label: "ODDS" },
  { value: "trends", label: "TRENDS" },
];

// Shallow, wide elliptical arc -- the same SVG elliptical-arc technique as
// HorizonMark.tsx (the actual STRATUS horizon mark: wide radius, shallow
// radius, so it reads as a flat horizon line rather than a bulging dial),
// re-parameterized to this control's own measured width instead of
// HorizonMark's small fixed icon size. Deliberately shallower than
// HorizonMark's own 0.18 height ratio -- at this control's real width (most
// of the screen), that ratio would produce a visibly bulging arc rather than
// a thin horizon texture. Stroked in theme.border, not theme.accent -- this
// is texture behind the control, never a competing graphic; the reference
// concept image's own "FIELD BIAS" bottom control shows exactly this: a
// barely-there arc with the actual signal (the accent tick) reserved for the
// active state below.
const ARC_HEIGHT_RATIO = 0.05;
const ARC_MIN_HEIGHT = 10;
const ARC_ZONE_HEIGHT = 22;
const ARC_STROKE_WIDTH = 1.2;
const ARC_SIDE_INSET = 10;

const LABEL_ROW_HEIGHT = 32;
const INDICATOR_WIDTH = 14;
const INDICATOR_HEIGHT = 2;
const INDICATOR_GAP = 6;
const TOP_PADDING = spacing.sm;
const BOTTOM_PADDING = spacing.md;

// Real, exported height -- other code (app/index.tsx's flex layout, and its
// __DEV__ notification test button's bottom offset) needs this actual
// number, not a guessed magic constant, so it reserves exactly the space
// this control occupies.
export const FIELD_BIAS_CONTROL_HEIGHT =
  TOP_PADDING +
  ARC_ZONE_HEIGHT +
  LABEL_ROW_HEIGHT +
  INDICATOR_GAP +
  INDICATOR_HEIGHT +
  BOTTOM_PADDING;

// FIELD BIAS: the bottom-of-Attention-Field lens control. Deliberately not a
// segmented-pill/tab-bar/button treatment -- four equal-width text labels
// over a barely-there horizon arc, with a short accent tick (never a filled
// pill or segment background) marking the active state. The user is
// adjusting the lens STRATUS presents the opportunity field through, not
// filtering a list -- the visual language here stays as restrained as that
// framing requires. All actual field-rebalancing behavior lives in
// AttentionField.tsx/Vessel.tsx (this component is pure chrome + a value/
// onChange contract); the category -> bias grouping lives in
// lib/fieldBias.ts.
export function FieldBiasControl({
  value,
  onChange,
}: {
  value: FieldBias;
  onChange: (next: FieldBias) => void;
}) {
  const [width, setWidth] = useState(0);
  const reducedMotion = useReducedMotion();

  const selectedIndex = Math.max(
    0,
    LABELS.findIndex((item) => item.value === value)
  );
  const indicatorPosition = useSharedValue(selectedIndex);

  useEffect(() => {
    indicatorPosition.value = withTiming(selectedIndex, { duration: reducedMotion ? 100 : 260 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedIndex, reducedMotion]);

  const indicatorStyle = useAnimatedStyle(() => {
    const segmentWidth = width / LABELS.length;
    const translateX =
      indicatorPosition.value * segmentWidth + (segmentWidth - INDICATOR_WIDTH) / 2;
    return { transform: [{ translateX }] };
  });

  const handleLayout = (e: LayoutChangeEvent) => setWidth(e.nativeEvent.layout.width);

  const arcHeight = Math.max(ARC_MIN_HEIGHT, width * ARC_HEIGHT_RATIO);
  const archRy = arcHeight * 0.82;
  const cy = arcHeight * 0.86;
  const halfW = Math.max(0, width / 2 - ARC_SIDE_INSET);

  return (
    <View style={styles.outer}>
      <View style={styles.inner} onLayout={handleLayout}>
        {width > 0 && (
          <Svg width={width} height={ARC_ZONE_HEIGHT} style={styles.arc}>
            <Path
              d={`M ${width / 2 - halfW} ${cy} A ${halfW} ${archRy} 0 0 1 ${width / 2 + halfW} ${cy}`}
              stroke={theme.border}
              strokeWidth={ARC_STROKE_WIDTH}
              strokeLinecap="round"
              fill="none"
            />
          </Svg>
        )}

        <View style={[styles.labelRow, { marginTop: ARC_ZONE_HEIGHT }]}>
          {LABELS.map((item) => {
            const selected = item.value === value;
            return (
              <Pressable
                key={item.value}
                style={styles.labelTap}
                onPress={() => onChange(item.value)}
                hitSlop={8}
                accessibilityRole="button"
                accessibilityLabel={item.label}
                accessibilityState={{ selected }}
                accessibilityHint={
                  item.value === "all"
                    ? "Shows the full Attention Field with no lens applied"
                    : `Brings ${item.label.toLowerCase()} forward in the Attention Field`
                }
              >
                <Text style={[styles.label, selected && styles.labelSelected]}>{item.label}</Text>
              </Pressable>
            );
          })}
        </View>

        {width > 0 && (
          <Animated.View
            pointerEvents="none"
            style={[
              styles.indicator,
              { top: ARC_ZONE_HEIGHT + LABEL_ROW_HEIGHT + INDICATOR_GAP },
              indicatorStyle,
            ]}
          />
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  outer: { width: "100%", backgroundColor: "transparent", paddingHorizontal: spacing.lg },
  inner: {
    width: "100%",
    paddingTop: TOP_PADDING,
    paddingBottom: BOTTOM_PADDING,
  },
  arc: { position: "absolute", top: 0, left: 0 },
  labelRow: { flexDirection: "row", width: "100%", height: LABEL_ROW_HEIGHT },
  labelTap: { flex: 1, alignItems: "center", justifyContent: "center" },
  label: {
    color: theme.muted,
    fontSize: 11,
    fontFamily: font.headingMedium,
    letterSpacing: tracking.label,
  },
  labelSelected: { color: theme.accent },
  indicator: {
    position: "absolute",
    left: 0,
    width: INDICATOR_WIDTH,
    height: INDICATOR_HEIGHT,
    borderRadius: INDICATOR_HEIGHT / 2,
    backgroundColor: theme.accent,
  },
});
