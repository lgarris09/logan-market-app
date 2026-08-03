import { Circle, vec } from "@shopify/react-native-skia";
import { useDerivedValue, SharedValue } from "react-native-reanimated";

// One unresolved signal: a barely-visible mote that twinkles on its own
// slow cycle. There is no per-particle animation loop -- every particle
// reads the same shared clock and computes its own phase from it, so 100+
// of these cost one shared value, not 100 separate tickers.
export function Particle({
  x,
  y,
  r,
  peak,
  freq,
  phase,
  time,
}: {
  x: number;
  y: number;
  r: number;
  peak: number;
  freq: number;
  phase: number;
  time: SharedValue<number>;
}) {
  const opacity = useDerivedValue(() => {
    const wave = (Math.sin(time.value * freq + phase) + 1) / 2; // 0..1
    return peak * (0.2 + wave * 0.8);
  }, [time]);

  return <Circle c={vec(x, y)} r={r} color="white" opacity={opacity} />;
}
