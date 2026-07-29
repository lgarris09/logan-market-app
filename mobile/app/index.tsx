import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { router } from "expo-router";

import { API_BASE_URL } from "../constants/config";
import { theme } from "../constants/theme";
import { Opportunity, OpportunityCard } from "../components/OpportunityCard";

type Briefing = {
  greeting: string;
  headline: string;
  opportunities: Opportunity[];
};

export default function HomeScreen() {
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const loadBriefing = useCallback(async () => {
    try {
      setError("");
      const response = await fetch(`${API_BASE_URL}/v1/briefing`);
      if (!response.ok) throw new Error(`Server returned ${response.status}`);
      setBriefing((await response.json()) as Briefing);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reach Logan.");
    }
  }, []);

  useEffect(() => {
    loadBriefing();
  }, [loadBriefing]);

  const onRefresh = async () => {
    setRefreshing(true);
    await loadBriefing();
    setRefreshing(false);
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={theme.accent}
          />
        }
      >
        <View style={styles.topbar}>
          <View>
            <Text style={styles.kicker}>PERSONAL INTELLIGENCE</Text>
            <Text style={styles.product}>APP NAME TBD</Text>
          </View>
          <View style={styles.status}>
            <View style={styles.dot} />
            <Text style={styles.statusText}>ACTIVE</Text>
          </View>
        </View>

        <View style={styles.hero}>
          <Text style={styles.greeting}>{briefing?.greeting ?? "Welcome back"}</Text>
          <Text style={styles.headline}>
            {briefing?.headline ?? "Checking what changed while you were away."}
          </Text>
          <Text style={styles.subline}>
            Ranked against your interests, past decisions, and active categories.
          </Text>
        </View>

        <View style={styles.summaryRow}>
          <View style={styles.summaryItem}>
            <Text style={styles.summaryNumber}>{briefing?.opportunities.length ?? "—"}</Text>
            <Text style={styles.summaryLabel}>RELEVANT</Text>
          </View>
          <View style={styles.summaryItem}>
            <Text style={styles.summaryNumber}>1</Text>
            <Text style={styles.summaryLabel}>URGENT</Text>
          </View>
          <View style={styles.summaryItem}>
            <Text style={styles.summaryNumber}>24/7</Text>
            <Text style={styles.summaryLabel}>WATCHING</Text>
          </View>
        </View>

        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Worth your attention</Text>
        </View>

        {!briefing && !error && <ActivityIndicator color={theme.accent} size="large" />}

        {!!error && (
          <View style={styles.error}>
            <Text style={styles.errorTitle}>Backend not connected</Text>
            <Text style={styles.errorText}>{error}</Text>
            <Text style={styles.errorText}>
              Start FastAPI and set your computer IP in constants/config.ts.
            </Text>
          </View>
        )}

        {briefing?.opportunities.map((item) => (
          <OpportunityCard key={item.id} item={item} />
        ))}

        <Pressable style={styles.primaryButton} onPress={() => router.push("/ask")}>
          <Text style={styles.primaryButtonText}>Ask Logan</Text>
        </Pressable>

        <Pressable style={styles.secondaryButton} onPress={() => router.push("/memory")}>
          <Text style={styles.secondaryButtonText}>Memory inbox</Text>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.background },
  content: { paddingHorizontal: 18, paddingTop: 18, paddingBottom: 42 },
  topbar: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  kicker: { color: theme.accent, fontSize: 10, fontWeight: "900", letterSpacing: 1.4 },
  product: { color: theme.text, fontSize: 18, fontWeight: "900", marginTop: 4 },
  status: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: theme.surface,
    borderColor: theme.border,
    borderWidth: 1,
    borderRadius: 999,
    paddingVertical: 8,
    paddingHorizontal: 11,
  },
  dot: { width: 7, height: 7, borderRadius: 4, backgroundColor: theme.success, marginRight: 7 },
  statusText: { color: theme.textSecondary, fontSize: 9, fontWeight: "800" },
  hero: { paddingTop: 42, paddingBottom: 26 },
  greeting: { color: theme.textSecondary, fontSize: 15 },
  headline: { color: theme.text, fontSize: 33, lineHeight: 39, fontWeight: "900", marginTop: 8 },
  subline: { color: theme.textSecondary, fontSize: 15, lineHeight: 22, marginTop: 12 },
  summaryRow: { flexDirection: "row", gap: 8, marginBottom: 30 },
  summaryItem: {
    flex: 1,
    backgroundColor: theme.surface,
    borderColor: theme.border,
    borderWidth: 1,
    borderRadius: 14,
    padding: 14,
  },
  summaryNumber: { color: theme.text, fontSize: 21, fontWeight: "900" },
  summaryLabel: { color: theme.textSecondary, fontSize: 9, fontWeight: "800", marginTop: 5 },
  sectionHeader: { marginBottom: 13 },
  sectionTitle: { color: theme.text, fontSize: 20, fontWeight: "800" },
  error: {
    backgroundColor: theme.accentSoft,
    borderColor: theme.accent,
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
    marginBottom: 14,
  },
  errorTitle: { color: theme.text, fontWeight: "900", marginBottom: 7 },
  errorText: { color: theme.textSecondary, lineHeight: 20, marginBottom: 4 },
  primaryButton: {
    backgroundColor: theme.accent,
    borderRadius: 16,
    alignItems: "center",
    paddingVertical: 16,
    marginTop: 4,
  },
  primaryButtonText: { color: "#FFFFFF", fontSize: 16, fontWeight: "900" },
  secondaryButton: {
    borderColor: theme.border,
    borderWidth: 1,
    borderRadius: 16,
    alignItems: "center",
    paddingVertical: 16,
    marginTop: 10,
  },
  secondaryButtonText: { color: theme.text, fontSize: 15, fontWeight: "800" },
});
