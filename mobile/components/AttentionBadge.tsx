import { StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { font, theme, tracking } from "../constants/theme";
import type { AttentionJudgment, AttentionTone } from "../lib/attentionJudgment";

// Replaces the old ConfidenceRing in the primary consumer card treatment
// (2026-08-29 audit + product decision): a plain three-state judgment
// answering "how much attention does this deserve right now," not a
// numeric confidence percentage -- see lib/attentionJudgment.ts for why.
// confidence_score/confidence_label remain on the data contract and keep
// flowing to Ask STRATUS/evidence reasoning unchanged; this component just
// no longer surfaces the raw number on the card itself.
const ICON_BY_TONE: Record<AttentionTone, keyof typeof Ionicons.glyphMap> = {
  high: "flash",
  "worth-a-look": "eye-outline",
  developing: "time-outline",
};

const COLOR_BY_TONE: Record<AttentionTone, string> = {
  high: theme.accent,
  "worth-a-look": theme.info,
  developing: theme.textSecondary,
};

export function AttentionBadge({
  judgment,
  tone,
  width = 76,
}: {
  judgment: AttentionJudgment;
  tone: AttentionTone;
  width?: number;
}) {
  const color = COLOR_BY_TONE[tone];

  return (
    <View style={[styles.wrap, { width }]}>
      <View style={[styles.iconCircle, { borderColor: color }]}>
        <Ionicons name={ICON_BY_TONE[tone]} size={18} color={color} />
      </View>
      <Text style={[styles.label, { color }]} numberOfLines={2}>
        {judgment}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: "center" },
  iconCircle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    borderWidth: 1.5,
    alignItems: "center",
    justifyContent: "center",
  },
  label: {
    marginTop: 6,
    fontSize: 10,
    textAlign: "center",
    fontFamily: font.metadata,
    letterSpacing: tracking.metadata,
  },
});
