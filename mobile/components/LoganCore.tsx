import { useEffect, useRef } from "react";
import { Animated, StyleSheet, Text, View } from "react-native";
import { BlurView } from "expo-blur";
import { LinearGradient } from "expo-linear-gradient";

const CORE_SIZE = 148;
const GOLD = "#E8B95C";

// The center of the Opportunity Field. Not a logo -- represents Logan itself.
// Calm, slow breathing animation only; no flashy or game-like motion.
export function LoganCore() {
  const breath = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(breath, { toValue: 1, duration: 2600, useNativeDriver: true }),
        Animated.timing(breath, { toValue: 0, duration: 2600, useNativeDriver: true }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [breath]);

  const scale = breath.interpolate({ inputRange: [0, 1], outputRange: [1, 1.035] });
  const glowOpacity = breath.interpolate({ inputRange: [0, 1], outputRange: [0.55, 0.9] });

  return (
    <View style={styles.wrapper} pointerEvents="none">
      <Animated.View
        style={[styles.glow, { opacity: glowOpacity, transform: [{ scale }] }]}
      />
      <Animated.View style={[styles.core, { transform: [{ scale }] }]}>
        <BlurView intensity={40} tint="dark" style={StyleSheet.absoluteFill} />
        <LinearGradient
          colors={["rgba(232,185,92,0.55)", "rgba(232,185,92,0.05)"]}
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
  glow: {
    position: "absolute",
    width: CORE_SIZE * 1.6,
    height: CORE_SIZE * 1.6,
    borderRadius: (CORE_SIZE * 1.6) / 2,
    backgroundColor: GOLD,
    opacity: 0.5,
    shadowColor: GOLD,
    shadowOpacity: 0.8,
    shadowRadius: 40,
    shadowOffset: { width: 0, height: 0 },
  },
  core: {
    width: CORE_SIZE,
    height: CORE_SIZE,
    borderRadius: CORE_SIZE / 2,
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
    backgroundColor: "rgba(10,13,18,0.75)",
  },
  ring: {
    position: "absolute",
    width: CORE_SIZE - 14,
    height: CORE_SIZE - 14,
    borderRadius: (CORE_SIZE - 14) / 2,
    borderWidth: 1.5,
    borderColor: GOLD,
    opacity: 0.8,
  },
  glyph: {
    color: GOLD,
    fontSize: 56,
    fontWeight: "800",
    fontFamily: undefined,
    textShadowColor: GOLD,
    textShadowRadius: 18,
    textShadowOffset: { width: 0, height: 0 },
  },
});
