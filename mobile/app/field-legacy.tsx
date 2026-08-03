import { useCallback, useEffect, useMemo, useState } from "react";
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from "react-native";
import { BlurView } from "expo-blur";

import { API_BASE_URL } from "../constants/config";
import { theme } from "../constants/theme";
import { OpportunityField } from "../components/OpportunityField";
import { DemoFeedResponse, FeedItem } from "../types/loganFeed";

// The radial force-directed field, preserved as-is at /field-legacy for
// comparison (superseded on the home screen by the depth-of-focus Attention
// Field -- this used to be app/index.tsx).
export default function LegacyOpportunityFieldScreen() {
  const [feed, setFeed] = useState<DemoFeedResponse | null>(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<FeedItem | null>(null);

  const loadFeed = useCallback(async () => {
    try {
      setError("");
      const response = await fetch(`${API_BASE_URL}/v1/demo/feed`);
      if (!response.ok) throw new Error(`Server returned ${response.status}`);
      const data = (await response.json()) as DemoFeedResponse;
      setFeed(data);
      setSelected((current) => current ?? data.items[0] ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reach Logan.");
    }
  }, []);

  useEffect(() => {
    loadFeed();
  }, [loadFeed]);

  const items = useMemo(() => feed?.items ?? [], [feed]);

  return (
    <ScrollView style={styles.safe} contentContainerStyle={styles.content}>
      {!feed && !error && (
        <View style={styles.centerFill}>
          <ActivityIndicator color={theme.accent} size="large" />
        </View>
      )}

      {!!error && (
        <View style={styles.error}>
          <Text style={styles.errorTitle}>Backend not connected</Text>
          <Text style={styles.errorText}>{error}</Text>
          <Text style={styles.errorText}>
            Start FastAPI and set your computer IP in constants/config.ts.
          </Text>
        </View>
      )}

      {items.length > 0 && (
        <View style={styles.fieldWrap}>
          <OpportunityField
            items={items}
            selectedId={selected?.event_id ?? null}
            onSelect={setSelected}
            pulseKey={feed?.generated_at}
          />
        </View>
      )}

      {selected && (
        <View style={styles.detailCard}>
          <BlurView intensity={30} tint="dark" style={StyleSheet.absoluteFill} />
          <View style={styles.detailHeader}>
            <Text style={styles.detailName}>{selected.display_name}</Text>
            <Text style={styles.detailConfidence}>
              {selected.confidence_label} · {Math.round(selected.confidence_score * 100)}%
            </Text>
          </View>
          <Text style={styles.detailHeadline}>{selected.delivered_item.headline}</Text>

          <Text style={styles.detailLabel}>WHY THIS MATTERS</Text>
          <Text style={styles.detailText}>{selected.delivered_item.why_it_matters}</Text>

          <Text style={[styles.detailLabel, styles.spaced]}>WHY IT MATTERS TO YOU</Text>
          <Text style={styles.detailText}>{selected.delivered_item.why_it_matters_to_me}</Text>

          {selected.delivered_item.required_disclaimers.length > 0 && (
            <View style={styles.disclaimers}>
              {selected.delivered_item.required_disclaimers.map((d) => (
                <Text key={d} style={styles.disclaimerText}>
                  {d}
                </Text>
              ))}
            </View>
          )}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.background },
  content: { paddingHorizontal: 12, paddingTop: 16, paddingBottom: 42, alignItems: "center" },
  centerFill: { paddingTop: 120 },
  fieldWrap: { marginTop: 12, alignItems: "center" },
  error: {
    backgroundColor: theme.accentSoft,
    borderColor: theme.accent,
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
    marginTop: 20,
    width: "100%",
  },
  errorTitle: { color: theme.text, fontWeight: "900", marginBottom: 7 },
  errorText: { color: theme.textSecondary, lineHeight: 20, marginBottom: 4 },
  detailCard: {
    width: "100%",
    marginTop: 20,
    borderRadius: 20,
    borderColor: theme.border,
    borderWidth: 1,
    padding: 18,
    overflow: "hidden",
  },
  detailHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  detailName: { color: theme.text, fontSize: 18, fontWeight: "900" },
  detailConfidence: { color: theme.textSecondary, fontSize: 12, fontWeight: "700" },
  detailHeadline: { color: theme.textSecondary, fontSize: 14, lineHeight: 20, marginTop: 8 },
  detailLabel: {
    color: theme.textSecondary,
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 1.1,
    marginBottom: 6,
  },
  spaced: { marginTop: 16 },
  detailText: { color: theme.text, fontSize: 14, lineHeight: 21 },
  disclaimers: { marginTop: 16, paddingTop: 14, borderTopWidth: 1, borderTopColor: theme.border },
  disclaimerText: { color: theme.textSecondary, fontSize: 11, lineHeight: 16, marginBottom: 4 },
});
