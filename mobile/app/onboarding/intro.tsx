// V2.3A consumer closeout -- first-run splash/intro. Reached automatically
// (see app/_layout.tsx's onboarding gate) only for a device that hasn't
// finished onboarding yet; never shown again after that. Deliberately a
// restrained static screen, not the future V3 splash animation -- auto-
// advances after a short beat, or immediately on tap, straight into the
// account step. Uses the same owner-approved wordmark/horizon artwork
// already shipped for the Attention Field header and menu footer (see
// app/index.tsx's own comments on those assets) -- no recreated logo.
import { useEffect, useRef } from "react";
import { Image, Pressable, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";

import { font, spacing, theme, tracking, type } from "../../constants/theme";

const WORDMARK_SOURCE = require("../../assets/images/stratus-wordmark-header.png");
const WORDMARK_ASPECT_RATIO = 1536 / 310;
const WORDMARK_WIDTH = 260;

const HORIZON_SOURCE = require("../../assets/images/stratus-horizon-mark.png");
const HORIZON_ASPECT_RATIO = 1512 / 430;

const AUTO_ADVANCE_MS = 2400;

export default function IntroScreen() {
  const advanced = useRef(false);

  const advance = () => {
    if (advanced.current) return;
    advanced.current = true;
    // push, not replace: account.tsx's back chevron needs a real history
    // entry to return to (the root onboarding gate already used replace()
    // to get here, so intro is the base of the stack, not a phantom entry).
    router.push("/onboarding/account");
  };

  useEffect(() => {
    const timer = setTimeout(advance, AUTO_ADVANCE_MS);
    return () => clearTimeout(timer);
  }, []);

  return (
    <Pressable style={styles.screen} onPress={advance} accessibilityRole="button" accessibilityLabel="Continue">
      <View style={styles.center}>
        <Image
          source={WORDMARK_SOURCE}
          resizeMode="contain"
          accessibilityRole="image"
          accessibilityLabel="STRATUS"
          style={styles.wordmark}
        />
        <Text style={styles.tagline}>SEE WHAT MATTERS NEXT.</Text>
      </View>

      <Image
        source={HORIZON_SOURCE}
        resizeMode="contain"
        accessibilityElementsHidden
        importantForAccessibility="no"
        style={styles.horizon}
      />

      <Text style={styles.poweredBy}>
        POWERED BY <Text style={styles.poweredByAccent}>LGI</Text>
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: theme.background, justifyContent: "space-between" },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: spacing.md },
  wordmark: { width: WORDMARK_WIDTH, height: WORDMARK_WIDTH / WORDMARK_ASPECT_RATIO },
  tagline: {
    fontFamily: font.metadata,
    fontSize: type.label,
    color: theme.accent,
    letterSpacing: tracking.label,
  },
  horizon: {
    width: "100%",
    height: undefined,
    aspectRatio: HORIZON_ASPECT_RATIO,
  },
  poweredBy: {
    fontFamily: font.metadata,
    fontSize: type.micro,
    color: theme.muted,
    letterSpacing: tracking.metadata,
    textAlign: "center",
    marginBottom: spacing.xl,
  },
  poweredByAccent: { color: theme.accent },
});
