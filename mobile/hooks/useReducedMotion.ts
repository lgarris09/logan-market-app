import { useEffect, useState } from "react";
import { AccessibilityInfo } from "react-native";

// Reads the OS-level "Reduce Motion" accessibility setting (iOS: Settings >
// Accessibility > Motion; Android: Settings > Accessibility > Remove animations)
// and stays in sync if the user changes it while the app is open. Framework-
// agnostic (AccessibilityInfo, not react-native-reanimated's own useReducedMotion)
// because AttentionField/Vessel/LoganCore drive their ambient animation through the
// classic Animated API, not Reanimated -- see mobile/eslint.config.js for why this
// codebase stays on classic Animated for that tree. The Atmosphere/Skia layer, which
// is Reanimated-driven, uses Reanimated's own useReducedMotion() directly instead of
// this hook -- both read the same OS setting, just through each tree's own animation
// library.
export function useReducedMotion(): boolean {
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    let mounted = true;

    AccessibilityInfo.isReduceMotionEnabled().then((enabled) => {
      if (mounted) setReducedMotion(enabled);
    });

    const subscription = AccessibilityInfo.addEventListener(
      "reduceMotionChanged",
      setReducedMotion
    );

    return () => {
      mounted = false;
      subscription.remove();
    };
  }, []);

  return reducedMotion;
}
