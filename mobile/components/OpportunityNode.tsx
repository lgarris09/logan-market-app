import { useEffect, useRef } from "react";
import { Animated, Easing, StyleSheet, Text } from "react-native";

import { EntitySymbol } from "./EntitySymbol";
import { PressableScale } from "./PressableScale";
import { theme, motion } from "../constants/theme";
import { useReducedMotion } from "../hooks/useReducedMotion";
import { resolveSymbol } from "../lib/symbolResolver";
import { FeedItem } from "../types/loganFeed";

const NODE_SIZE = 66;

export type NodeEmphasis = "focused" | "related" | "dimmed";

export function OpportunityNode({
  item,
  onPress,
  emphasis,
  floatPhase = 0,
  floatFreq = 1,
}: {
  item: FeedItem;
  onPress: () => void;
  emphasis: NodeEmphasis;
  floatPhase?: number;
  floatFreq?: number;
}) {
  const symbol = resolveSymbol(item);
  const reducedMotion = useReducedMotion();

  const focusAnim = useRef(new Animated.Value(emphasis === "focused" ? 1 : 0)).current;
  const opacityAnim = useRef(new Animated.Value(emphasis === "dimmed" ? 0.38 : 1)).current;
  // A one-shot local ripple, distinct from the core's global one -- fires
  // when this specific node becomes the focus (a real event: the user
  // pointed at it), not on a timer.
  const selectRipple = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(focusAnim, {
      toValue: emphasis === "focused" ? 1 : 0,
      duration: motion.base,
      useNativeDriver: true,
    }).start();
    Animated.timing(opacityAnim, {
      toValue: emphasis === "dimmed" ? 0.38 : 1,
      duration: motion.base,
      useNativeDriver: true,
    }).start();

    if (emphasis === "focused" && !reducedMotion) {
      selectRipple.setValue(0);
      Animated.timing(selectRipple, { toValue: 1, duration: 750, useNativeDriver: true }).start();
    }
  }, [emphasis, focusAnim, opacityAnim, selectRipple, reducedMotion]);

  const rippleScale = selectRipple.interpolate({ inputRange: [0, 1], outputRange: [1, 1.9] });
  const rippleOpacity = selectRipple.interpolate({
    inputRange: [0, 0.15, 1],
    outputRange: [0, 0.4, 0],
  });

  // Only a few pixels, slow, and phase-shifted per node so the field never
  // moves in unison -- nearly subconscious, not a visible "loading" wobble.
  const driftX = useRef(new Animated.Value(0)).current;
  const driftY = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (reducedMotion) {
      driftX.setValue(0);
      driftY.setValue(0);
      return;
    }
    const base = 4400 / floatFreq;
    const delay = (floatPhase / (Math.PI * 2)) * base;
    const ease = Easing.inOut(Easing.sin);

    const loopY = Animated.loop(
      Animated.sequence([
        Animated.timing(driftY, {
          toValue: 1,
          duration: base,
          delay,
          easing: ease,
          useNativeDriver: true,
        }),
        Animated.timing(driftY, {
          toValue: -1,
          duration: base * 2,
          easing: ease,
          useNativeDriver: true,
        }),
        Animated.timing(driftY, {
          toValue: 0,
          duration: base,
          easing: ease,
          useNativeDriver: true,
        }),
      ])
    );
    const loopX = Animated.loop(
      Animated.sequence([
        Animated.timing(driftX, {
          toValue: 1,
          duration: base * 1.3,
          delay: delay * 0.5,
          easing: ease,
          useNativeDriver: true,
        }),
        Animated.timing(driftX, {
          toValue: -1,
          duration: base * 2.6,
          easing: ease,
          useNativeDriver: true,
        }),
        Animated.timing(driftX, {
          toValue: 0,
          duration: base * 1.3,
          easing: ease,
          useNativeDriver: true,
        }),
      ])
    );
    loopY.start();
    loopX.start();
    return () => {
      loopY.stop();
      loopX.stop();
    };
  }, [driftX, driftY, floatFreq, floatPhase, reducedMotion]);

  const ringScale = focusAnim.interpolate({ inputRange: [0, 1], outputRange: [1, 1.08] });
  const translateY = driftY.interpolate({ inputRange: [-1, 1], outputRange: [-3, 3] });
  const translateX = driftX.interpolate({ inputRange: [-1, 1], outputRange: [-2, 2] });

  return (
    <Animated.View style={{ opacity: opacityAnim, transform: [{ translateX }, { translateY }] }}>
      <PressableScale
        onPress={onPress}
        style={styles.wrapper}
        scaleTo={0.92}
        accessibilityLabel={item.display_name}
        accessibilityHint="Focuses this opportunity"
        accessibilityState={{ selected: emphasis === "focused" }}
      >
        <Animated.View
          pointerEvents="none"
          style={[
            styles.selectRipple,
            {
              width: NODE_SIZE,
              height: NODE_SIZE,
              borderRadius: NODE_SIZE / 2,
              borderColor: symbol.color,
              opacity: rippleOpacity,
              transform: [{ scale: rippleScale }],
            },
          ]}
        />
        <Animated.View
          style={[
            styles.ring,
            {
              width: NODE_SIZE,
              height: NODE_SIZE,
              borderRadius: NODE_SIZE / 2,
              borderColor: symbol.color,
              shadowColor: symbol.color,
              backgroundColor: theme.surface,
              transform: [{ scale: ringScale }],
            },
            emphasis === "focused" && styles.ringFocused,
          ]}
        >
          <EntitySymbol symbol={symbol} size={NODE_SIZE - 16} />
        </Animated.View>
        <Text
          style={[styles.label, emphasis === "focused" && styles.labelFocused]}
          numberOfLines={1}
        >
          {item.display_name.toUpperCase()}
        </Text>
        <Text style={[styles.status, { color: symbol.color }]} numberOfLines={1}>
          {item.confidence_label}
        </Text>
      </PressableScale>
    </Animated.View>
  );
}

export { NODE_SIZE };

const styles = StyleSheet.create({
  wrapper: {
    alignItems: "center",
    width: 92,
  },
  selectRipple: {
    position: "absolute",
    top: 0,
    borderWidth: 1,
  },
  ring: {
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 2,
    shadowOpacity: 0.6,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 0 },
    elevation: 6,
  },
  ringFocused: {
    borderWidth: 3,
    shadowOpacity: 0.9,
    shadowRadius: 16,
    elevation: 10,
  },
  label: {
    color: theme.text,
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 0.6,
    marginTop: 6,
    textAlign: "center",
  },
  labelFocused: {
    color: theme.text,
    fontWeight: "900",
  },
  status: {
    fontSize: 9,
    fontWeight: "700",
    marginTop: 2,
    textAlign: "center",
  },
});
