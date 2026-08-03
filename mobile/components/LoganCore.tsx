import { useEffect, useRef } from "react";
import { Animated, StyleSheet, Text, View } from "react-native";
import { BlurView } from "expo-blur";
import { LinearGradient } from "expo-linear-gradient";

const CORE_SIZE = 84;
const GOLD = "#E8B95C";

// Not a continuous timer. Each ring fires once, as a staggered cascade, when
// `pulseKey` changes -- i.e. when something real happened (Logan finished a
// reasoning pass over the field), not on a decorative loop. Slightly
// different duration/scale/eccentricity per ring so the cascade doesn't read
// as a perfectly repeating target pattern.
const RINGS = [
  { duration: 1900, delay: 0, peakScale: 1.9, eccentricity: 1.0 },
  { duration: 2200, delay: 220, peakScale: 2.35, eccentricity: 1.05 },
  { duration: 2000, delay: 460, peakScale: 2.75, eccentricity: 0.96 },
];

function useRippleBurst(trigger: unknown, duration: number, delay: number) {
  const progress = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (trigger === undefined) return;
    progress.setValue(0);
    const anim = Animated.timing(progress, { toValue: 1, duration, delay, useNativeDriver: true });
    anim.start();
    return () => anim.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trigger]);

  return progress;
}

function Ripple({
  trigger,
  duration,
  delay,
  peakScale,
  eccentricity,
}: (typeof RINGS)[number] & { trigger: unknown }) {
  const progress = useRippleBurst(trigger, duration, delay);

  const scaleX = progress.interpolate({ inputRange: [0, 1], outputRange: [1, peakScale] });
  const scaleY = progress.interpolate({
    inputRange: [0, 1],
    outputRange: [1, peakScale * eccentricity],
  });
  // Quick appearance, slow dissipation -- reads as a single wave arriving and
  // fading, the way an actual ripple decays.
  const opacity = progress.interpolate({
    inputRange: [0, 0.12, 1],
    outputRange: [0, 0.26, 0],
  });

  return (
    <Animated.View
      pointerEvents="none"
      style={[styles.ripple, { opacity, transform: [{ scaleX }, { scaleY }] }]}
    />
  );
}

// The center of the Opportunity Field. Not a logo -- represents Logan itself.
// Breathing is continuous and ambient (Logan is alive). Ripples are discrete
// and event-driven (Logan just noticed or concluded something) -- pass a
// value that changes whenever a reasoning pass completes, e.g. the feed's
// generated_at timestamp. Passing the same pulseKey twice does nothing.
export function LoganCore({ pulseKey }: { pulseKey?: string | number }) {
  const breath = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(breath, { toValue: 1, duration: 2800, useNativeDriver: true }),
        Animated.timing(breath, { toValue: 0, duration: 2800, useNativeDriver: true }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [breath]);

  const scale = breath.interpolate({ inputRange: [0, 1], outputRange: [1, 1.03] });

  return (
    <View style={styles.wrapper} pointerEvents="none">
      {RINGS.map((ring, index) => (
        <Ripple key={index} trigger={pulseKey} {...ring} />
      ))}

      <Animated.View style={[styles.core, { transform: [{ scale }] }]}>
        <BlurView intensity={35} tint="dark" style={StyleSheet.absoluteFill} />
        <LinearGradient
          colors={["rgba(232,185,92,0.20)", "rgba(232,185,92,0.02)"]}
          style={StyleSheet.absoluteFill}
        />
        <View style={styles.ring} />
        <Text style={styles.glyph}>L</Text>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    width: CORE_SIZE,
    height: CORE_SIZE,
    alignItems: "center",
    justifyContent: "center",
  },
  ripple: {
    position: "absolute",
    width: CORE_SIZE,
    height: CORE_SIZE,
    borderRadius: CORE_SIZE / 2,
    borderWidth: 1,
    borderColor: GOLD,
  },
  core: {
    width: CORE_SIZE,
    height: CORE_SIZE,
    borderRadius: CORE_SIZE / 2,
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
    backgroundColor: "rgba(10,13,18,0.78)",
  },
  ring: {
    position: "absolute",
    width: CORE_SIZE - 10,
    height: CORE_SIZE - 10,
    borderRadius: (CORE_SIZE - 10) / 2,
    borderWidth: 1,
    borderColor: GOLD,
    opacity: 0.7,
  },
  glyph: {
    color: GOLD,
    fontSize: 30,
    fontWeight: "800",
    textShadowColor: GOLD,
    textShadowRadius: 10,
    textShadowOffset: { width: 0, height: 0 },
  },
});
