import { useEffect, useMemo } from "react";
import { StyleSheet, View } from "react-native";
import {
  Canvas,
  Circle,
  FractalNoise,
  Group,
  Rect,
  vec,
  RadialGradient,
} from "@shopify/react-native-skia";
import {
  useDerivedValue,
  useReducedMotion,
  useSharedValue,
  withRepeat,
  withTiming,
  Easing,
} from "react-native-reanimated";

import { AtmosphereCloud, CloudSpec } from "./AtmosphereCloud";
import { paletteForHexColor, ringGradient } from "../../lib/atmosphereGradients";
import { VesselLayout } from "../../lib/attentionLayout";
import { resolveSymbol } from "../../lib/symbolResolver";
import { FeedItem } from "../../types/loganFeed";

// A small, fixed cap regardless of feed size -- this is ambient depth, not a
// rendering of every entity. Keeps the layer's cost constant (a handful of
// blurred circles sharing one clock) rather than growing with the feed.
const MAX_CLOUDS = 4;

// The Attention Field's subordinate atmosphere layer (V3.1.4 BATCH-5, ADR-028's
// "not yet merged into the live screen" resolved). This is NOT the Sprint 1
// preview's full atmosphere (see AtmosphereField.tsx / atmosphere-preview.tsx,
// preserved unchanged) -- it deliberately drops that preview's 130 unresolved-
// signal particles and its fixed demo-entity clouds. Both existed to visualize
// "everything Logan hasn't resolved yet," which is the opposite job of this
// screen: every Vessel here IS a resolved, informative item, so duplicating that
// as decorative clouds behind it would be a second, competing visual mode, not a
// subordinate one. What's kept is only what's genuinely ambient and adds depth
// without carrying its own claim to attention: two low-opacity haze regions
// (tinted from the current highest-priority item, so the room's overall tone
// still tracks the real feed) plus a handful of soft, blurred color regions at
// each of the top few items' real layout positions -- material depth behind the
// Vessels, never text, never interactive, never louder than what it sits behind.
export function AttentionAtmosphere({
  items,
  layouts,
  width,
  height,
}: {
  items: FeedItem[];
  layouts: Map<string, VesselLayout>;
  width: number;
  height: number;
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

  const clouds = useMemo<CloudSpec[]>(() => {
    if (width === 0 || height === 0) return [];
    const ranked = [...items].sort((a, b) => a.rank - b.rank).slice(0, MAX_CLOUDS);
    return ranked.flatMap((item) => {
      const layout = layouts.get(item.event_id);
      if (!layout) return [];
      const symbol = resolveSymbol({
        entity_id: item.entity_id,
        display_name: item.display_name,
        category: item.category,
        ticker: item.ticker,
      });
      const palette = paletteForHexColor(symbol.color);
      const { colors, positions } = ringGradient(palette.base, palette.highlight);
      return [
        {
          id: item.event_id,
          cx: layout.x * width,
          cy: layout.y * height,
          // Larger than the vessel's own dormant glow so it reads as the room
          // around the item, not a duplicate of the item itself.
          r: layout.size * 1.4,
          colors,
          positions,
          driftPhase: layout.driftPhase,
          driftFreq: layout.driftFreq * 0.4, // slower than the vessel's own drift
        },
      ];
    });
  }, [items, layouts, width, height]);

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
    <View pointerEvents="none" style={StyleSheet.absoluteFill}>
      <Canvas style={StyleSheet.absoluteFill}>
        <Group transform={hazeTransformA}>
          <Circle c={vec(width * 0.2, height * 0.25)} r={hazeR}>
            <RadialGradient
              c={vec(width * 0.2, height * 0.25)}
              r={hazeR}
              colors={[`rgba(${hazePalette.base},0.10)`, `rgba(${hazePalette.base},0)`]}
            />
          </Circle>
        </Group>

        <Group>
          {clouds.map((c) => (
            <AtmosphereCloud key={c.id} {...c} time={time} />
          ))}
        </Group>

        {/* Fine grain so the field reads as a material, not a flat vector fill --
            static cost, no per-frame work. */}
        <Rect x={0} y={0} width={width} height={height} opacity={0.02}>
          <FractalNoise freqX={0.8} freqY={0.8} octaves={2} />
        </Rect>
      </Canvas>
    </View>
  );
}
