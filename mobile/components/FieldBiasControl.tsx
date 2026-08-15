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
// a thin horizon texture.
const ARC_HEIGHT_RATIO = 0.05;
const ARC_MIN_HEIGHT = 10;
const ARC_ZONE_HEIGHT = 22;
const ARC_STROKE_WIDTH = 1.2;
const ARC_SIDE_INSET = 10;
// Sprint 3.6.5 device-feedback pass: the arc used to be a single uniform
// path stroked entirely in theme.border (nearly indistinguishable from the
// background), with the only active-state signal being the small tick below
// the labels -- on a physical device this read as too subtle to tell which
// state was active without reading the label color. Two coats now: a full,
// low-opacity platinum/gray base (still just texture, never a competing
// graphic) plus a short, brighter orange trace over just the selected
// quarter -- explicitly NOT the whole arc turning orange (that would read
// as a tachometer/gauge-fill, which the owner's feedback calls out to
// avoid). `theme.muted` (not `theme.border`, which is nearly the same value
// as the background) is what makes the base arc actually read as "subtle
// platinum/gray," not "invisible."
const ARC_BASE_OPACITY = 0.4;
const ARC_ACTIVE_OPACITY = 0.95;
const ARC_ACTIVE_STROKE_WIDTH = ARC_STROKE_WIDTH + 0.7;
const ARC_ACTIVE_SAMPLES = 16;
const ARC_BASE_SAMPLES = 40;

const LABEL_ROW_HEIGHT = 32;
// Widened 14 -> 18 (Sprint 3.6.5): "preserve the small active indicator"
// while making the selected state read more clearly active -- a touch more
// footprint, still a short tick, never a filled segment/pill.
const INDICATOR_WIDTH = 18;
const INDICATOR_HEIGHT = 2;
const INDICATOR_GAP = 6;
const TOP_PADDING = spacing.sm;
const BOTTOM_PADDING = spacing.md;

// Real, exported height -- other code (app/index.tsx's flex layout) needs
// this actual number, not a guessed magic constant, so it reserves exactly
// the space this control occupies.
export const FIELD_BIAS_CONTROL_HEIGHT =
  TOP_PADDING +
  ARC_ZONE_HEIGHT +
  LABEL_ROW_HEIGHT +
  INDICATOR_GAP +
  INDICATOR_HEIGHT +
  BOTTOM_PADDING;

// Traces a point-sampled polyline approximating the same semi-ellipse the
// control's arc always used (rx=halfW, ry=ry, centered at (cx,cy), spanning
// t=0 at the left endpoint to t=1 at the right endpoint through the top at
// t=0.5) -- parametric rather than a single SVG elliptical-arc command so a
// sub-range of it (the active segment) can be traced independently, over
// the same curve, without a second, differently-shaped approximation.
function ellipseArcPath(
  cx: number,
  cy: number,
  halfW: number,
  ry: number,
  tFrom: number,
  tTo: number,
  samples: number
): string {
  const cmds: string[] = [];
  for (let i = 0; i <= samples; i++) {
    const t = tFrom + ((tTo - tFrom) * i) / samples;
    const x = cx - halfW * Math.cos(t * Math.PI);
    const y = cy - ry * Math.sin(t * Math.PI);
    cmds.push(`${i === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`);
  }
  return cmds.join(" ");
}

// FIELD BIAS: the bottom-of-Attention-Field lens control. Deliberately not a
// segmented-pill/tab-bar/button treatment -- four equal-width text labels
// over a barely-there horizon arc, with a short accent tick and a matching
// short orange arc trace (never a filled pill or segment background)
// marking the active state. The user is adjusting the lens STRATUS presents
// the opportunity field through, not filtering a list -- the visual
// language here stays as restrained as that framing requires. All actual
// field-rebalancing behavior lives in AttentionField.tsx/Vessel.tsx (this
// component is pure chrome + a value/onChange contract); the category ->
// bias grouping lives in lib/fieldBias.ts.
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
  const cx = width / 2;
  const activeFrom = selectedIndex / LABELS.length;
  const activeTo = (selectedIndex + 1) / LABELS.length;

  return (
    <View style={styles.outer}>
      <View style={styles.inner} onLayout={handleLayout}>
        {width > 0 && (
          <Svg width={width} height={ARC_ZONE_HEIGHT} style={styles.arc}>
            <Path
              d={ellipseArcPath(cx, cy, halfW, archRy, 0, 1, ARC_BASE_SAMPLES)}
              stroke={theme.muted}
              strokeOpacity={ARC_BASE_OPACITY}
              strokeWidth={ARC_STROKE_WIDTH}
              strokeLinecap="round"
              fill="none"
            />
            <Path
              d={ellipseArcPath(cx, cy, halfW, archRy, activeFrom, activeTo, ARC_ACTIVE_SAMPLES)}
              stroke={theme.accent}
              strokeOpacity={ARC_ACTIVE_OPACITY}
              strokeWidth={ARC_ACTIVE_STROKE_WIDTH}
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
  // Sprint 3.6.5: bumped to the heavier heading face (SemiBold, matching
  // restLabelName's own weight elsewhere in the app) and a point larger, on
  // top of the existing color change -- "selected label should read more
  // clearly active," not just a different color at the same weight/size.
  labelSelected: {
    color: theme.accent,
    fontFamily: font.heading,
    fontSize: 12,
  },
  indicator: {
    position: "absolute",
    left: 0,
    width: INDICATOR_WIDTH,
    height: INDICATOR_HEIGHT,
    borderRadius: INDICATOR_HEIGHT / 2,
    backgroundColor: theme.accent,
  },
});
