import { useEffect, useState } from "react";
import { LayoutChangeEvent, Pressable, StyleSheet, Text, View } from "react-native";
import Svg, { Line, Path } from "react-native-svg";
import Animated, {
  useAnimatedProps,
  useReducedMotion,
  useSharedValue,
  withTiming,
} from "react-native-reanimated";

import { font, spacing, theme, tracking } from "../constants/theme";
import { FieldBias } from "../lib/fieldBias";

const AnimatedLine = Animated.createAnimatedComponent(Line);

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
// Round 1 (Sprint 3.6.5 device-feedback pass) added a short, brighter
// orange trace over just the selected quarter, on top of a full low-opacity
// platinum/gray base -- explicitly not the whole arc turning orange, to
// avoid a tachometer/gauge-fill read. On a physical device that quarter-
// width trace *still* read as a bar/slider segment, not a mark -- length,
// not brightness, was the problem. Round 2 dropped the arc-trace element
// entirely and fell back to a small rectangular tick below the label row --
// which then read as *effectively invisible* on a physical device (2px
// tall was too thin to register at a glance). Round 3 (owner rendering
// reference): the base arc stays pure platinum texture at every state
// (never orange, at any span -- see ellipseArcPath below), and the active
// state is now a small burnt-orange tick/notch drawn directly on the arc at
// the selected quarter's position (see the animated tick further down),
// plus the selected label's own color/weight step-up. A point marker
// crossing the arc reads as "a position on an instrument," never as "a
// filled segment" the way any along-the-arc trace does, regardless of how
// short that trace is made. `theme.muted` (not `theme.border`, which is
// nearly the same value as the background) is what makes the base arc
// actually read as "subtle platinum/gray," not "invisible."
const ARC_BASE_OPACITY = 0.4;
const ARC_BASE_SAMPLES = 40;
// The tick: a short vertical mark crossing the arc at the selected
// position, not a span along it -- see the round-3 comment above for why
// that shape distinction is what keeps this from reading as a bar. Drawn as
// two coincident lines (see the JSX below): a soft, wider, low-opacity halo
// for on-device visibility against the dark field, plus a crisp, narrower
// full-opacity core for definition -- "small but clearly visible... without
// becoming heavy" without needing an actual blur filter.
const TICK_HALF_LENGTH = 5;
const TICK_CORE_STROKE_WIDTH = 2.25;
const TICK_HALO_STROKE_WIDTH = 6.5;
const TICK_HALO_OPACITY = 0.3;

const LABEL_ROW_HEIGHT = 32;
const TOP_PADDING = spacing.sm;
const BOTTOM_PADDING = spacing.md;

// Real, exported height -- other code (app/index.tsx's flex layout) needs
// this actual number, not a guessed magic constant, so it reserves exactly
// the space this control occupies. Round 3: the active-state tick moved
// onto the arc itself (see above), so this no longer reserves extra height
// below the label row for a separate indicator element.
export const FIELD_BIAS_CONTROL_HEIGHT =
  TOP_PADDING + ARC_ZONE_HEIGHT + LABEL_ROW_HEIGHT + BOTTOM_PADDING;

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
// segmented-pill/tab-bar/button/gauge treatment -- four equal-width text
// labels over a barely-there horizon arc that stays neutral platinum at
// every state, with a small burnt-orange tick/notch marking the selected
// position directly on the arc, plus the selected label's own color/weight
// step-up (never a filled pill, segment background, or orange arc trace --
// two earlier rounds tried an along-the-arc orange trace and a below-label
// rectangle, and both either read as a bar/slider or were too faint to
// register on a physical device; a short mark crossing the arc at a single
// point is what finally reads as "a position on an instrument" rather than
// either extreme). The user is adjusting the lens STRATUS presents the
// opportunity field through, not filtering a list -- the visual language
// here stays as restrained as that framing requires. All actual
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

  const handleLayout = (e: LayoutChangeEvent) => setWidth(e.nativeEvent.layout.width);

  const arcHeight = Math.max(ARC_MIN_HEIGHT, width * ARC_HEIGHT_RATIO);
  const archRy = arcHeight * 0.82;
  const cy = arcHeight * 0.86;
  const halfW = Math.max(0, width / 2 - ARC_SIDE_INSET);
  const cx = width / 2;

  // The tick's position on the arc: the same parametric ellipse
  // ellipseArcPath traces (t=0..1 left-to-right through the top), evaluated
  // at the midpoint of the selected quarter and animated by tracking
  // indicatorPosition (0..3, same withTiming transition the label/tick
  // switch has always used) rather than jumping instantly.
  const tickAnimatedProps = useAnimatedProps(() => {
    const t = (indicatorPosition.value + 0.5) / LABELS.length;
    const x = cx - halfW * Math.cos(t * Math.PI);
    const y = cy - archRy * Math.sin(t * Math.PI);
    return {
      x1: x,
      x2: x,
      y1: y - TICK_HALF_LENGTH,
      y2: y + TICK_HALF_LENGTH,
    };
  });

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
            {/* Halo first (wider, dimmer), core on top (narrower, full
                opacity) -- both share the same animated x/y so they move as
                one mark. */}
            <AnimatedLine
              animatedProps={tickAnimatedProps}
              stroke={theme.accent}
              strokeOpacity={TICK_HALO_OPACITY}
              strokeWidth={TICK_HALO_STROKE_WIDTH}
              strokeLinecap="round"
            />
            <AnimatedLine
              animatedProps={tickAnimatedProps}
              stroke={theme.accent}
              strokeWidth={TICK_CORE_STROKE_WIDTH}
              strokeLinecap="round"
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
});
