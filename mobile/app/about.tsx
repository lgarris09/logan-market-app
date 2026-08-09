import Constants from "expo-constants";
import { Image, ScrollView, StyleSheet, Text, View } from "react-native";

import { font, spacing, theme, tracking, type } from "../constants/theme";

// Sprint 3.6 device retest: About STRATUS now renders the same
// owner-approved wordmark artwork used in the Attention Field header and
// menu drawer (see assets/images/stratus-wordmark-header.png) instead of
// the hand-coded StratusWordmark.tsx SVG. Sized larger here (220 vs 132)
// since this is a hero placement, not chrome alongside other controls --
// same asset, same aspect ratio, just a different width.
const ABOUT_LOGO_SOURCE = require("../assets/images/stratus-wordmark-header.png");
const ABOUT_LOGO_ASPECT_RATIO = 1536 / 310;
const ABOUT_LOGO_WIDTH = 220;

// V3.1.4.1: consumer-facing product identity, split out of the hamburger
// menu (which used to mix this with legacy/test screens -- see
// app/index.tsx's menu rewrite in the same change).
export default function AboutScreen() {
  const version = Constants.expoConfig?.version ?? "—";
  const build = Constants.nativeBuildVersion ?? Constants.expoConfig?.ios?.buildNumber ?? "—";

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Image
        source={ABOUT_LOGO_SOURCE}
        resizeMode="contain"
        accessibilityRole="image"
        accessibilityLabel="STRATUS"
        style={styles.logo}
      />
      <Text style={styles.tagline}>POWERED BY LGI</Text>

      <View style={styles.card}>
        <Row label="Version" value={String(version)} />
        <Row label="Build" value={String(build)} />
      </View>

      <Text style={styles.legalNote}>
        Privacy and legal information will appear here in a future release.
      </Text>
    </ScrollView>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: theme.background },
  content: { padding: spacing.xl, paddingTop: spacing.xxl },
  logo: { width: ABOUT_LOGO_WIDTH, height: ABOUT_LOGO_WIDTH / ABOUT_LOGO_ASPECT_RATIO },
  tagline: {
    color: theme.muted,
    fontSize: 10,
    fontFamily: font.metadata,
    letterSpacing: tracking.metadata,
    marginTop: 10,
    marginBottom: spacing.xl,
  },
  card: {
    backgroundColor: theme.surface,
    borderColor: theme.border,
    borderWidth: 1,
    borderRadius: 16,
    paddingHorizontal: spacing.lg,
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: theme.border,
  },
  rowLabel: { color: theme.textSecondary, fontSize: type.body, fontFamily: font.body },
  rowValue: { color: theme.text, fontSize: type.body, fontFamily: font.bodyMedium },
  legalNote: {
    color: theme.muted,
    fontSize: type.label,
    fontFamily: font.body,
    lineHeight: 18,
    marginTop: spacing.xl,
  },
});
