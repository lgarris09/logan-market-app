// Preserved for `classic.tsx` only (ADR-026's pre-Field home screen, kept for
// comparison/fallback) -- reads the static /v1/briefing fixture's Opportunity shape,
// not logan_core's DeliveredItem. The canonical, pipeline-backed card is
// `OpportunityCard.tsx`; this component is not used by any current-generation
// screen. Renamed from `OpportunityCard.tsx` during the V3.1.4 BATCH-4 Opportunity
// Card consolidation -- see that commit for the rationale.
import { StyleSheet, Text, View } from "react-native";

import { theme } from "../constants/theme";

export type Opportunity = {
  id: string;
  category: "stocks" | "sports" | "polymarket";
  title: string;
  summary: string;
  why_it_matters: string;
  score: number;
  urgency: "watch" | "important" | "now";
  change_label: string;
  source_label: string;
};

const labels = {
  stocks: "MARKETS",
  sports: "SPORTS",
  polymarket: "POLYMARKET",
};

export function LegacyOpportunityCard({ item }: { item: Opportunity }) {
  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Text style={styles.category}>{labels[item.category]}</Text>
        <Text style={styles.score}>{item.score}% match</Text>
      </View>

      <Text style={styles.title}>{item.title}</Text>
      <Text style={styles.change}>{item.change_label}</Text>
      <Text style={styles.summary}>{item.summary}</Text>

      <View style={styles.divider} />

      <Text style={styles.reasonLabel}>WHY IT MATTERS TO YOU</Text>
      <Text style={styles.reason}>{item.why_it_matters}</Text>
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
  category: {
    color: theme.accent,
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1.3,
  },
  score: {
    color: theme.textSecondary,
    fontSize: 12,
    fontWeight: "700",
  },
  title: {
    color: theme.text,
    fontSize: 20,
    lineHeight: 26,
    fontWeight: "800",
  },
  change: {
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
  reason: {
    color: theme.text,
    fontSize: 14,
    lineHeight: 21,
  },
});
