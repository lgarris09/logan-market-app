import { useEffect } from "react";
import { StyleSheet } from "react-native";
import {
  Canvas,
  Circle,
  FractalNoise,
  Group,
  Rect,
  vec,
  RadialGradient,
} from "@shopify/react-native-skia";
import Animated, {
  interpolate,
  useAnimatedStyle,
  useDerivedValue,
  useReducedMotion,
  useSharedValue,
  withRepeat,
  withTiming,
  Easing,
} from "react-native-reanimated";

import { paletteForHexColor } from "../../lib/atmosphereGradients";
import { resolveSymbol } from "../../lib/symbolResolver";
import { FeedItem } from "../../types/loganFeed";

// The Attention Field's subordinate atmosphere layer (V3.1.4 BATCH-5, ADR-028's
// "not yet merged into the live screen" resolved). This is NOT the Sprint 1
// preview's full atmosphere (see AtmosphereField.tsx / atmosphere-preview.tsx,
// preserved unchanged) -- it deliberately drops that preview's 130 unresolved-
// signal particles and its fixed demo-entity clouds. Both existed to visualize
// "everything Logan hasn't resolved yet," which is the opposite job of this
// screen: every Vessel here IS a resolved, informative item, so duplicating that
// as decorative clouds behind it would be a second, competing visual mode, not a
// subordinate one. What's kept is only what's genuinely ambient and adds depth
// without carrying its own claim to attention: two low-opacity haze regions,
// tinted from the current highest-priority item so the room's overall tone
// still tracks the real feed.
//
// Sprint 3.6 (bubble-match pass): this used to also render a handful of soft,
// blurred color "cloud" regions at each of the top few items' own real layout
// positions -- material depth sitting directly behind those Vessels. Once
// Vessel.tsx's own bubble became a hollow-centered gradient (transparent
// where the label sits, thickening toward the rim, so the black field shows
// through the middle), those clouds sat in exactly the same spot and washed
// the hollow center back toward solid -- two overlapping colored layers where
// the design now calls for one. Removed; the far fainter, purely global haze
// below is what remains.
export function AttentionAtmosphere({
  items,
  width,
  height,
  dampened = false,
}: {
  items: FeedItem[];
  width: number;
  height: number;
  /** True while an Opportunity Card is open. Round 2 (real-device
   * screenshots): the ambient field needs to strongly recede, not just
   * subtly, for the focused card to read clearly against it -- the field
   * stays alive underneath (still Atmosphere, not switched off), just
   * dimmed well down. */
  dampened?: boolean;
}) {
  const time = useSharedValue(0);
  // Reanimated's own hook (this layer is Reanimated/Skia-driven), same as
  // AtmosphereField.tsx. Captured once at mount per Reanimated's own docs.
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    if (reducedMotion) return;
    time.value = withRepeat(
      withTiming(100000, { duration: 100000000, easing: Easing.linear }),
      -1,
      false
    );
  }, [time, reducedMotion]);

  const dampenAnim = useSharedValue(0);
  useEffect(() => {
    dampenAnim.value = withTiming(dampened ? 1 : 0, { duration: 300 });
  }, [dampened, dampenAnim]);
  const dampenStyle = useAnimatedStyle(() => ({
    opacity: interpolate(dampenAnim.value, [0, 1], [1, 0.2]),
  }));

  const topItem = [...items].sort((a, b) => a.rank - b.rank)[0];
  const hazePalette = topItem
    ? paletteForHexColor(
        resolveSymbol({
          entity_id: topItem.entity_id,
          display_name: topItem.display_name,
          category: topItem.category,
          ticker: topItem.ticker,
        }).color
      )
    : { base: "70,150,140" };

  const hazeTransformA = useDerivedValue(
    () => [
      { translateX: Math.sin(time.value * 0.025) * 18 },
      { translateY: Math.cos(time.value * 0.02) * 12 },
    ],
    [time]
  );
  const hazeR = Math.max(width, height) * 0.5;

  if (width === 0 || height === 0) return null;

  return (
    <Animated.View pointerEvents="none" style={[StyleSheet.absoluteFill, dampenStyle]}>
      {/* pointerEvents is set on both this wrapper and the Canvas itself --
          Skia's Canvas is backed by its own native view on iOS and has been
          observed not to fully inherit a parent's pointerEvents="none" under
          New Architecture, which would otherwise intercept vessel taps
          (Sprint 3.5 device-validation fix). */}
      <Canvas style={StyleSheet.absoluteFill} pointerEvents="none">
        <Group transform={hazeTransformA}>
          <Circle c={vec(width * 0.2, height * 0.25)} r={hazeR}>
            <RadialGradient
              c={vec(width * 0.2, height * 0.25)}
              r={hazeR}
              colors={[`rgba(${hazePalette.base},0.08)`, `rgba(${hazePalette.base},0)`]}
            />
          </Circle>
        </Group>

        {/* Fine grain so the field reads as a material, not a flat vector fill --
            static cost, no per-frame work. */}
        <Rect x={0} y={0} width={width} height={height} opacity={0.02}>
          <FractalNoise freqX={0.8} freqY={0.8} octaves={2} />
        </Rect>
      </Canvas>
    </Animated.View>
  );
}
