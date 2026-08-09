import { useEffect, useState } from "react";
import { AccessibilityInfo } from "react-native";

// Reads the OS-level "Reduce Motion" accessibility setting (iOS: Settings >
// Accessibility > Motion; Android: Settings > Accessibility > Remove animations)
// and stays in sync if the user changes it while the app is open. Framework-
// agnostic (AccessibilityInfo, not react-native-reanimated's own useReducedMotion)
// for consumers that still drive animation through the classic Animated API --
// LoganCore.tsx (not on the live screen) and FadeIn.tsx -- see
// mobile/eslint.config.js for why this codebase carries lint exceptions for that
// pattern. AttentionField/Vessel moved to Reanimated in V3.1.4.1 (Sprint 3.5
// device-validation fix: the classic API's non-native-driven layout animation was
// the likely cause of taps not visibly producing a focus/card transition on a real
// iPhone) and now use Reanimated's own useReducedMotion() directly instead of this
// hook, matching the Atmosphere/Skia layer -- all three read the same OS setting,
// just through each tree's own animation library.
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
