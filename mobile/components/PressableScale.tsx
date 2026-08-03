import { ReactNode, useRef } from "react";
import { Animated, Pressable, PressableProps, ViewStyle } from "react-native";

import { motion } from "../constants/theme";

// Shared press-feedback wrapper so every button and node responds to touch the
// same way, instead of each screen deciding on its own (or not at all).
export function PressableScale({
  style,
  scaleTo = 0.96,
  children,
  ...props
}: Omit<PressableProps, "children" | "style"> & {
  style?: ViewStyle | ViewStyle[];
  scaleTo?: number;
  children?: ReactNode;
}) {
  const scale = useRef(new Animated.Value(1)).current;

  const pressIn = () => {
    Animated.timing(scale, { toValue: scaleTo, duration: motion.fast, useNativeDriver: true }).start();
  };
  const pressOut = () => {
    Animated.spring(scale, { toValue: 1, useNativeDriver: true, friction: 5, tension: 120 }).start();
  };

  return (
    <Pressable onPressIn={pressIn} onPressOut={pressOut} {...props}>
      <Animated.View style={[style, { transform: [{ scale }] }]}>{children}</Animated.View>
    </Pressable>
  );
}
