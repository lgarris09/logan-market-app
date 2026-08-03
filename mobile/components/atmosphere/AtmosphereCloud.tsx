import { BlurMask, Circle, Group, RadialGradient, vec } from "@shopify/react-native-skia";
import { useDerivedValue, SharedValue } from "react-native-reanimated";

export type CloudSpec = {
  id: string;
  cx: number;
  cy: number;
  r: number;
  colors: string[]; // ring-contour stops, center -> transparent edge
  positions: number[];
  driftPhase: number;
  driftFreq: number;
};

// One coherent region of the atmosphere. Two overlapping lobes (not one
// perfect circle) filled with the same ring-contour gradient -- the faint
// density rebounds real condensation leaves where it keeps gathering on
// the same spot -- softened only by a mask blur, never emitting light of
// its own. Slow, near-imperceptible drift comes from one shared clock, not
// a dedicated animation per cloud.
export function AtmosphereCloud({ cx, cy, r, colors, positions, driftPhase, driftFreq, time }: CloudSpec & { time: SharedValue<number> }) {
  const transform = useDerivedValue(() => {
    const dx = Math.sin(time.value * driftFreq + driftPhase) * (r * 0.1);
    const dy = Math.cos(time.value * driftFreq * 0.8 + driftPhase) * (r * 0.14);
    return [{ translateX: dx }, { translateY: dy }];
  }, [time]);

  const lobeCx = cx - r * 0.32;
  const lobeCy = cy + r * 0.26;
  const lobeR = r * 0.58;

  return (
    <Group transform={transform}>
      <Circle c={vec(cx, cy)} r={r}>
        <RadialGradient c={vec(cx, cy)} r={r} colors={colors} positions={positions} />
        <BlurMask blur={9} />
      </Circle>
      <Circle c={vec(lobeCx, lobeCy)} r={lobeR}>
        <RadialGradient c={vec(lobeCx, lobeCy)} r={lobeR} colors={colors} positions={positions} />
        <BlurMask blur={7} />
      </Circle>
    </Group>
  );
}
