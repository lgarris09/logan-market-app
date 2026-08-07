import { useEffect, useRef } from "react";
import { Animated, Easing, Platform, Pressable, StyleSheet, Text, View } from "react-native";
import { BlurView } from "expo-blur";
import { LinearGradient } from "expo-linear-gradient";

import { theme } from "../constants/theme";
import { useReducedMotion } from "../hooks/useReducedMotion";
import { resolveSymbol } from "../lib/symbolResolver";
import { VesselLayout } from "../lib/attentionLayout";
import { FeedItem } from "../types/loganFeed";

const SERIF = Platform.select({ ios: "Georgia", android: "serif", default: "serif" });

// Every entity on the Attention Field renders through this one component --
// there is no separate "card" anywhere. A vessel is always alive (drifting,
// breathing with its own confidence, pulsing with its own priority, rippling
// when something it's connected to stirs) whether or not anyone is looking
// at it. Disclosure only decides how much of it has condensed into words: 0
// is pure atmosphere, 1 is a single held line, 2 is the full thought. The
// shape itself grows to hold that -- text never appears on a separate
// object placed on top of the glow.
export function Vessel({
  item,
  layout,
  isFocused,
  disclosure,
  readingWidth,
  echoSignal,
  onPress,
}: {
  item: FeedItem;
  layout: VesselLayout;
  isFocused: boolean;
  disclosure: 0 | 1 | 2;
  readingWidth: number;
  echoSignal: Animated.Value;
  onPress: () => void;
}) {
  const symbol = resolveSymbol(item);
  const instability = 1 - item.confidence_score; // low confidence -> more visible flicker
  // Already 0..1 and rank-derived (see attentionLayout.ts) -- no raw score is
  // ever available here, per ADR-029.
  const prominence = layout.prominence;
  const reducedMotion = useReducedMotion();

  const entrance = useRef(new Animated.Value(0)).current;
  const drift = useRef(new Animated.Value(0)).current;
  const breath = useRef(new Animated.Value(0)).current;
  const pulse = useRef(new Animated.Value(0)).current;
  const disclosureAnim = useRef(new Animated.Value(0)).current;
  const focusAnim = useRef(new Animated.Value(isFocused ? 1 : 0)).current;

  // Condensation: this vessel did not simply appear -- it accreted, starting
  // diffuse and settling. Staggered per entity so the whole field doesn't
  // form in unison.
  // Reduced motion (OS accessibility setting): the vessel still appears, still
  // discloses on tap, still shows focus -- what stops is the ambient, non-essential
  // motion that never carries information on its own (continuous drift/breath/pulse
  // loops, the condensation spring-in, cross-vessel echo ripples). Disclosure and
  // focus still transition, just quickly and without spring bounce, since those are
  // direct responses to a user's own tap/swipe, not ambient animation.
  useEffect(() => {
    if (reducedMotion) {
      entrance.setValue(1);
      return;
    }
    const delay = stableDelay(item.event_id);
    Animated.sequence([
      Animated.delay(delay),
      Animated.spring(entrance, { toValue: 1, useNativeDriver: true, friction: 6, tension: 30 }),
    ]).start();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reducedMotion]);

  useEffect(() => {
    if (reducedMotion) {
      drift.setValue(0);
      return;
    }
    const base = 6000 / layout.driftFreq;
    const delay = (layout.driftPhase / (Math.PI * 2)) * base;
    const ease = Easing.inOut(Easing.sin);
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(drift, {
          toValue: 1,
          duration: base,
          delay,
          easing: ease,
          useNativeDriver: true,
        }),
        Animated.timing(drift, {
          toValue: -1,
          duration: base * 2,
          easing: ease,
          useNativeDriver: true,
        }),
        Animated.timing(drift, { toValue: 0, duration: base, easing: ease, useNativeDriver: true }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [drift, layout.driftFreq, layout.driftPhase, reducedMotion]);

  // Confidence made continuous: a settled belief barely moves; an uncertain
  // one visibly wavers the whole time you look at it, not just once.
  useEffect(() => {
    if (reducedMotion) {
      breath.setValue(0);
      return;
    }
    const base = 3400 / layout.breathFreq;
    const delay = (layout.breathPhase / (Math.PI * 2)) * base;
    const ease = Easing.inOut(Easing.sin);
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(breath, {
          toValue: 1,
          duration: base,
          delay,
          easing: ease,
          useNativeDriver: true,
        }),
        Animated.timing(breath, {
          toValue: 0,
          duration: base,
          easing: ease,
          useNativeDriver: true,
        }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [breath, layout.breathFreq, layout.breathPhase, reducedMotion]);

  // Priority made continuous: what matters more visibly asserts itself more
  // often -- a slow heartbeat, not a fixed brightness.
  useEffect(() => {
    if (reducedMotion) {
      pulse.setValue(0);
      return;
    }
    const base = 2200 / layout.pulseFreq;
    const delay = (layout.pulsePhase / (Math.PI * 2)) * base;
    const ease = Easing.inOut(Easing.sin);
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: 1,
          duration: base,
          delay,
          easing: ease,
          useNativeDriver: true,
        }),
        Animated.timing(pulse, { toValue: 0, duration: base, easing: ease, useNativeDriver: true }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [pulse, layout.pulseFreq, layout.pulsePhase, reducedMotion]);

  useEffect(() => {
    if (reducedMotion) {
      Animated.timing(disclosureAnim, {
        toValue: disclosure,
        duration: 120,
        useNativeDriver: false,
      }).start();
      return;
    }
    Animated.spring(disclosureAnim, {
      toValue: disclosure,
      useNativeDriver: false, // drives width/height/borderRadius, not transform-only
      friction: 9,
      tension: 40,
    }).start();
  }, [disclosure, disclosureAnim, reducedMotion]);

  useEffect(() => {
    Animated.timing(focusAnim, {
      toValue: isFocused ? 1 : 0,
      duration: reducedMotion ? 120 : 420,
      useNativeDriver: true,
    }).start();
  }, [isFocused, focusAnim, reducedMotion]);

  const dormantSize = layout.size;
  const glanceHeight = 118;
  const detailHeight = 268;

  const width = disclosureAnim.interpolate({
    inputRange: [0, 1, 2],
    outputRange: [dormantSize * 0.7, readingWidth, readingWidth],
  });
  const height = disclosureAnim.interpolate({
    inputRange: [0, 1, 2],
    outputRange: [dormantSize * 0.7, glanceHeight, detailHeight],
  });
  const radius = disclosureAnim.interpolate({
    inputRange: [0, 1, 2],
    outputRange: [(dormantSize * 0.7) / 2, glanceHeight / 2, 34],
  });
  const frostOpacity = disclosureAnim.interpolate({
    inputRange: [0, 0.35, 1],
    outputRange: [0, 0, 1],
    extrapolate: "clamp",
  });
  const headlineOpacity = disclosureAnim.interpolate({
    inputRange: [0, 0.7, 1, 2],
    outputRange: [0, 0, 1, 1],
    extrapolate: "clamp",
  });
  const detailOpacity = disclosureAnim.interpolate({
    inputRange: [0, 1, 1.55, 2],
    outputRange: [0, 0, 1, 1],
    extrapolate: "clamp",
  });

  const translateX = drift.interpolate({ inputRange: [-1, 1], outputRange: [-5, 5] });
  const translateY = drift.interpolate({ inputRange: [-1, 1], outputRange: [-7, 7] });

  const coreOpacityBase = 0.36;
  const coreOpacity = breath.interpolate({
    inputRange: [0, 1],
    outputRange: [
      coreOpacityBase * (1 - instability * 0.45),
      coreOpacityBase * (1 + instability * 0.45),
    ],
  });
  const pulseScale = pulse.interpolate({
    inputRange: [0, 1],
    outputRange: [1, 1 + 0.05 + prominence * 0.14],
  });
  const focusScale = focusAnim.interpolate({ inputRange: [0, 1], outputRange: [1, 1.14] });
  const entranceScale = entrance.interpolate({
    inputRange: [0, 0.6, 1],
    outputRange: [0.3, 1.12, 1],
  });

  // A disturbance arriving from a connected vessel: a ring expands outward
  // from the core and fades, distinct from (not summed with) this vessel's
  // own confidence/priority rhythm -- a visitor, not a property of itself.
  const echoRingScale = echoSignal.interpolate({ inputRange: [0, 1], outputRange: [0.7, 2.1] });
  const echoRingOpacity = echoSignal.interpolate({
    inputRange: [0, 0.15, 1],
    outputRange: [0, 0.55, 0],
  });

  const outer = dormantSize * 1.15;
  const mid = dormantSize * 0.62;
  const core = dormantSize * 0.3;
  const glowBoxSize = Math.max(outer, readingWidth) + 40;

  const supporting =
    item.delivered_item.why_it_matters_to_me?.trim() || item.delivered_item.why_now?.trim();

  return (
    <Animated.View
      style={{
        position: "absolute",
        left: `${layout.x * 100}%`,
        top: `${layout.y * 100}%`,
        width: glowBoxSize,
        height: glowBoxSize,
        marginLeft: -glowBoxSize / 2,
        marginTop: -glowBoxSize / 2,
        alignItems: "center",
        justifyContent: "center",
        opacity: entrance,
        transform: [{ translateX }, { translateY }],
      }}
      pointerEvents="box-none"
    >
      {/* The glow -- always present, never text-bearing. This is Logan
          reasoning about this entity whether or not it is being read. */}
      <View pointerEvents="none" style={styles.glowLayerHost}>
        <View
          style={[
            styles.glowRing,
            { width: outer, height: outer, borderRadius: outer / 2, backgroundColor: symbol.color },
          ]}
        />
        <View
          style={[
            styles.glowRing,
            {
              width: mid,
              height: mid,
              borderRadius: mid / 2,
              backgroundColor: symbol.color,
              opacity: 0.5,
            },
          ]}
        />
        <Animated.View
          pointerEvents="none"
          style={[
            styles.echoRing,
            {
              width: core * 2.2,
              height: core * 2.2,
              borderRadius: core * 1.1,
              borderColor: symbol.color,
              opacity: echoRingOpacity,
              transform: [{ scale: echoRingScale }],
            },
          ]}
        />
        <Animated.View
          style={[
            styles.glowCore,
            {
              width: core,
              height: core,
              borderRadius: core / 2,
              backgroundColor: symbol.color,
              shadowColor: symbol.color,
              shadowRadius: core,
              opacity: coreOpacity,
              transform: [{ scale: entranceScale }, { scale: pulseScale }, { scale: focusScale }],
            },
          ]}
        />
      </View>

      <Pressable
        onPress={onPress}
        hitSlop={12}
        style={styles.pressable}
        accessibilityRole="button"
        accessibilityLabel={`${item.display_name}: ${item.delivered_item.headline}`}
        accessibilityHint={
          disclosure < 2 ? "Reveals more detail about this opportunity" : "Shows less detail"
        }
        accessibilityState={{ expanded: disclosure > 0, selected: isFocused }}
      >
        <Animated.View style={{ width, height, borderRadius: radius, overflow: "hidden" }}>
          <Animated.View style={[StyleSheet.absoluteFill, { opacity: frostOpacity }]}>
            <BlurView intensity={38} tint="dark" style={StyleSheet.absoluteFill} />
            <LinearGradient
              colors={[symbol.color + "24", "transparent"]}
              start={{ x: 0.1, y: 0.05 }}
              end={{ x: 0.7, y: 0.6 }}
              style={StyleSheet.absoluteFill}
            />
            <View style={styles.content}>
              <Animated.Text
                style={[styles.headline, { opacity: headlineOpacity }]}
                numberOfLines={3}
              >
                {item.delivered_item.headline}
              </Animated.Text>

              <Animated.View style={{ opacity: detailOpacity }}>
                {!!supporting && (
                  <Text style={styles.supporting} numberOfLines={4}>
                    {supporting}
                  </Text>
                )}
                <View style={styles.footerRow}>
                  <View style={[styles.confidenceDot, { backgroundColor: symbol.color }]} />
                  <Text style={styles.confidenceText}>{item.confidence_label.toUpperCase()}</Text>
                </View>
                {item.delivered_item.required_disclaimers.map((d) => (
                  <Text key={d} style={styles.disclaimerText}>
                    {d}
                  </Text>
                ))}
              </Animated.View>
            </View>
          </Animated.View>
        </Animated.View>
      </Pressable>
    </Animated.View>
  );
}

function stableDelay(seed: string): number {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  return (hash % 900) + 60;
}

const styles = StyleSheet.create({
  glowLayerHost: { position: "absolute", alignItems: "center", justifyContent: "center" },
  glowRing: { position: "absolute", opacity: 0.15 },
  echoRing: { position: "absolute", borderWidth: 1.5 },
  glowCore: {
    position: "absolute",
    shadowOpacity: 0.9,
    shadowOffset: { width: 0, height: 0 },
    elevation: 1,
  },
  pressable: { alignItems: "center", justifyContent: "center" },
  content: { flex: 1, padding: 20, justifyContent: "center" },
  headline: {
    color: theme.text,
    fontFamily: SERIF,
    fontSize: 19,
    lineHeight: 25,
  },
  supporting: { color: theme.textSecondary, fontSize: 13, lineHeight: 19, marginTop: 12 },
  footerRow: { flexDirection: "row", alignItems: "center", marginTop: 16 },
  confidenceDot: { width: 6, height: 6, borderRadius: 3, marginRight: 8 },
  confidenceText: {
    color: theme.textSecondary,
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 1.4,
  },
  disclaimerText: { color: theme.muted, fontSize: 10, lineHeight: 15, marginTop: 10 },
});
