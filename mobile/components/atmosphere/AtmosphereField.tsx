import { useEffect, useMemo } from "react";
import { StyleSheet, useWindowDimensions } from "react-native";
import {
  Canvas,
  Circle,
  Fill,
  FractalNoise,
  Group,
  RadialGradient,
  Rect,
  vec,
} from "@shopify/react-native-skia";
import {
  useDerivedValue,
  useSharedValue,
  withRepeat,
  withTiming,
  Easing,
} from "react-native-reanimated";

import { AtmosphereCloud, CloudSpec } from "./AtmosphereCloud";
import { Particle } from "./Particle";
import { ATMOSPHERE_PALETTE, ringGradient } from "../../lib/atmosphereGradients";

const PARTICLE_COUNT = 130;

// Sprint 1 -- Atmosphere. This is the medium itself: depth, structured
// clouds, and a field of unresolved particles, all driven off one shared
// clock so 130+ moving parts cost one animation, not 130. No entities, no
// text, no interaction yet -- those are later sprints, layered on top of
// this once it holds up on its own at 60fps.
export function AtmosphereField() {
  const { width, height } = useWindowDimensions();
  const time = useSharedValue(0);

  useEffect(() => {
    time.value = withRepeat(
      withTiming(100000, { duration: 100000000, easing: Easing.linear }),
      -1,
      false
    );
  }, [time]);

  const clouds = useMemo<CloudSpec[]>(() => {
    const entries: {
      key: keyof typeof ATMOSPHERE_PALETTE;
      x: number;
      y: number;
      r: number;
      phase: number;
      freq: number;
    }[] = [
      { key: "TSLA", x: 0.22, y: 0.22, r: 44, phase: 0.3, freq: 0.09 },
      { key: "FED", x: 0.76, y: 0.16, r: 38, phase: 1.4, freq: 0.07 },
      { key: "BTC", x: 0.18, y: 0.56, r: 40, phase: 2.6, freq: 0.11 },
      { key: "OIL", x: 0.78, y: 0.6, r: 34, phase: 3.8, freq: 0.08 },
      { key: "MARKETS", x: 0.45, y: 0.82, r: 34, phase: 4.9, freq: 0.1 },
      { key: "NVDA", x: 0.5, y: 0.44, r: 66, phase: 0, freq: 0.05 },
    ];
    return entries.map((e) => {
      const palette = ATMOSPHERE_PALETTE[e.key];
      const { colors, positions } = ringGradient(palette.base, palette.highlight);
      return {
        id: e.key,
        cx: e.x * width,
        cy: e.y * height,
        r: e.r,
        colors,
        positions,
        driftPhase: e.phase,
        driftFreq: e.freq,
      };
    });
  }, [width, height]);

  const particles = useMemo(() => {
    return Array.from({ length: PARTICLE_COUNT }, (_, i) => ({
      id: i,
      x: Math.random() * width,
      y: Math.random() * height,
      r: Math.random() * 1.3 + 0.4,
      peak: Math.random() * 0.3 + 0.06,
      freq: 0.15 + Math.random() * 0.25,
      phase: Math.random() * Math.PI * 2,
    }));
  }, [width, height]);

  const hazeTransformA = useDerivedValue(
    () => [
      { translateX: Math.sin(time.value * 0.025) * 18 },
      { translateY: Math.cos(time.value * 0.02) * 12 },
    ],
    [time]
  );
  const hazeTransformB = useDerivedValue(
    () => [
      { translateX: Math.sin(time.value * 0.018 + 2) * -20 },
      { translateY: Math.cos(time.value * 0.022 + 2) * 14 },
    ],
    [time]
  );

  const hazeR = Math.max(width, height) * 0.55;

  return (
    <Canvas style={StyleSheet.absoluteFill}>
      <Fill color="#050505" />

      {/* depth: large, dim, independently-drifting haze behind everything
          else -- deliberately undifferentiated, unlike the clouds below.
          This is the medium in its unresolved state, not a place where
          anything has condensed yet. */}
      <Group transform={hazeTransformA}>
        <Circle c={vec(width * 0.12, height * 0.22)} r={hazeR}>
          <RadialGradient
            c={vec(width * 0.12, height * 0.22)}
            r={hazeR}
            colors={["rgba(70,150,140,0.16)", "rgba(70,150,140,0)"]}
          />
        </Circle>
      </Group>
      <Group transform={hazeTransformB}>
        <Circle c={vec(width * 0.85, height * 0.62)} r={hazeR * 0.9}>
          <RadialGradient
            c={vec(width * 0.85, height * 0.62)}
            r={hazeR * 0.9}
            colors={["rgba(120,90,180,0.13)", "rgba(120,90,180,0)"]}
          />
        </Circle>
      </Group>

      {/* structured clouds -- the coherent regions the atmosphere is capable of holding */}
      <Group>
        {clouds.map((c) => (
          <AtmosphereCloud key={c.id} {...c} time={time} />
        ))}
      </Group>

      {/* particles: hundreds of unresolved signals, one shared clock */}
      <Group>
        {particles.map((p) => (
          <Particle key={p.id} {...p} time={time} />
        ))}
      </Group>

      {/* fine grain so the field reads as a material, not a flat vector fill */}
      <Rect x={0} y={0} width={width} height={height} opacity={0.03}>
        <FractalNoise freqX={0.8} freqY={0.8} octaves={2} />
      </Rect>
    </Canvas>
  );
}
