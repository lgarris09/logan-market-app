// Canonical Opportunity Card (V3.1.4 BATCH-4 consolidation) -- renders
// logan_core's DeliveredItem, the shape every current-generation, pipeline-backed
// screen uses. Previously duplicated as `LoganOpportunityCard.tsx`; that file's
// implementation now lives here under the canonical name. `classic.tsx` (ADR-026's
// preserved legacy screen, which reads the static /v1/briefing fixture instead of
// DeliveredItem) uses `LegacyOpportunityCard.tsx` and is intentionally not
// consolidated into this component -- the two render fundamentally different data
// shapes, and forcing them together would mean inventing a mapping between a
// deprecated demo fixture and the real pipeline contract.
import { StyleSheet, Text, View } from "react-native";

import { theme } from "../constants/theme";
import { DeliveredItem } from "../types/loganDemo";

const surfaceLabels: Record<DeliveredItem["surface"], string> = {
  wheel: "WHEEL",
  feed_card: "FEED",
  alert: "ALERT",
  digest: "DIGEST",
  background: "BACKGROUND",
};

export function OpportunityCard({ item }: { item: DeliveredItem }) {
  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Text style={styles.surface}>
          {surfaceLabels[item.surface] ?? item.surface.toUpperCase()}
        </Text>
        <Text style={styles.confidence}>
          {item.confidence_label} · {Math.round(item.confidence_score * 100)}%
        </Text>
      </View>

      <Text style={styles.headline}>{item.headline}</Text>
      <Text style={styles.whyNow}>{item.why_now}</Text>
      <Text style={styles.summary}>{item.what_happened}</Text>

      <View style={styles.divider} />

      <Text style={styles.reasonLabel}>WHY IT MATTERS</Text>
      <Text style={styles.reason}>{item.why_it_matters}</Text>

      <Text style={[styles.reasonLabel, styles.spacedLabel]}>WHY IT MATTERS TO YOU</Text>
      <Text style={styles.reason}>{item.why_it_matters_to_me}</Text>

      {item.required_disclaimers.length > 0 && (
        <View style={styles.disclaimers}>
          {item.required_disclaimers.map((disclaimer) => (
            <Text key={disclaimer} style={styles.disclaimerText}>
              {disclaimer}
            </Text>
          ))}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: theme.surface,
    borderColor: theme.border,
    borderWidth: 1,
    borderRadius: 18,
    padding: 18,
    marginBottom: 12,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 14,
  },
  surface: {
    color: theme.accent,
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1.3,
  },
  confidence: {
    color: theme.textSecondary,
    fontSize: 12,
    fontWeight: "700",
  },
  headline: {
    color: theme.text,
    fontSize: 20,
    lineHeight: 26,
    fontWeight: "800",
  },
  whyNow: {
    color: theme.warning,
    fontSize: 13,
    fontWeight: "700",
    marginTop: 8,
  },
  summary: {
    color: theme.textSecondary,
    fontSize: 15,
    lineHeight: 22,
    marginTop: 10,
  },
  divider: {
    height: 1,
    backgroundColor: theme.border,
    marginVertical: 16,
  },
  reasonLabel: {
    color: theme.textSecondary,
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 1.1,
    marginBottom: 7,
  },
  spacedLabel: {
    marginTop: 16,
  },
  reason: {
    color: theme.text,
    fontSize: 14,
    lineHeight: 21,
  },
  disclaimers: {
    marginTop: 16,
    paddingTop: 14,
    borderTopWidth: 1,
    borderTopColor: theme.border,
  },
  disclaimerText: {
    color: theme.textSecondary,
    fontSize: 11,
    lineHeight: 16,
    marginBottom: 4,
  },
});
