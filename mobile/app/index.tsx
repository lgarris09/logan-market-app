import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Modal,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { BlurView } from "expo-blur";
import { router } from "expo-router";

import { API_BASE_URL } from "../constants/config";
import { theme } from "../constants/theme";
import { OpportunityField } from "../components/OpportunityField";
import { DemoFeedResponse, FeedItem } from "../types/loganFeed";

const LEGACY_SCREENS: { label: string; href: "/classic" | "/ask" | "/memory" | "/demo" }[] = [
  { label: "Classic briefing (pre-Field home)", href: "/classic" },
  { label: "Ask Logan", href: "/ask" },
  { label: "Memory inbox", href: "/memory" },
  { label: "Tesla-only pipeline demo", href: "/demo" },
];

export default function OpportunityFieldScreen() {
  const [feed, setFeed] = useState<DemoFeedResponse | null>(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<FeedItem | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

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
    <SafeAreaView style={styles.safe}>
      <View style={styles.topbar}>
        <Pressable onPress={() => setMenuOpen(true)} hitSlop={10}>
          <Ionicons name="menu" size={24} color={theme.text} />
        </Pressable>
        <View style={styles.titleWrap}>
          <Text style={styles.wordmark}>LOGAN</Text>
          <Text style={styles.subtitle}>OPPORTUNITY FIELD</Text>
        </View>
        <View style={styles.liveBadge}>
          <View style={styles.liveDot} />
          <Text style={styles.liveText}>LIVE</Text>
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
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

      <Modal visible={menuOpen} animationType="fade" transparent onRequestClose={() => setMenuOpen(false)}>
        <Pressable style={styles.menuBackdrop} onPress={() => setMenuOpen(false)}>
          <View style={styles.menuCard}>
            <Text style={styles.menuTitle}>Preserved screens</Text>
            {LEGACY_SCREENS.map((screen) => (
              <Pressable
                key={screen.href}
                style={styles.menuItem}
                onPress={() => {
                  setMenuOpen(false);
                  router.push(screen.href);
                }}
              >
                <Text style={styles.menuItemText}>{screen.label}</Text>
                <Ionicons name="chevron-forward" size={16} color={theme.textSecondary} />
              </Pressable>
            ))}
          </View>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: theme.background },
  topbar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 18,
    paddingTop: 8,
    paddingBottom: 4,
  },
  titleWrap: { alignItems: "center" },
  wordmark: { color: theme.text, fontSize: 18, fontWeight: "900", letterSpacing: 4 },
  subtitle: { color: theme.warning, fontSize: 9, fontWeight: "800", letterSpacing: 2, marginTop: 2 },
  liveBadge: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: theme.surface,
    borderColor: theme.border,
    borderWidth: 1,
    borderRadius: 999,
    paddingVertical: 6,
    paddingHorizontal: 10,
  },
  liveDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: theme.success, marginRight: 6 },
  liveText: { color: theme.textSecondary, fontSize: 9, fontWeight: "800" },
  content: { paddingHorizontal: 12, paddingBottom: 42, alignItems: "center" },
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
  menuBackdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.6)", justifyContent: "flex-end" },
  menuCard: {
    backgroundColor: theme.surface,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 22,
    paddingBottom: 40,
  },
  menuTitle: { color: theme.textSecondary, fontSize: 11, fontWeight: "800", letterSpacing: 1, marginBottom: 14 },
  menuItem: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: theme.border,
  },
  menuItemText: { color: theme.text, fontSize: 15, fontWeight: "700" },
});
