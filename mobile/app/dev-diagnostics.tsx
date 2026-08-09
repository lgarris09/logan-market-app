import { useEffect, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import Constants from "expo-constants";
import { router } from "expo-router";

import { API_BASE_URL } from "../constants/config";
import { radius, spacing, theme, tracking, type, weight } from "../constants/theme";
import { fetchJson } from "../lib/apiClient";

// V3.1.4.1 round 2 (real-device screenshot review): the drawer used to inline
// API status plus five legacy screen links directly, which made the
// consumer menu feel dominated by developer content. Collapsed into this one
// dedicated, __DEV__-gated destination -- see app/index.tsx's single
// "Developer / Diagnostics" row.
const LEGACY_SCREENS: {
  label: string;
  href: "/atmosphere-preview" | "/field-legacy" | "/classic" | "/memory" | "/demo";
}[] = [
  { label: "Atmosphere (Sprint 1 preview)", href: "/atmosphere-preview" },
  { label: "Opportunity Field (previous)", href: "/field-legacy" },
  { label: "Classic briefing (pre-Field home)", href: "/classic" },
  { label: "Memory inbox (internal)", href: "/memory" },
  { label: "Tesla-only pipeline demo", href: "/demo" },
];

export default function DevDiagnosticsScreen() {
  const [apiStatus, setApiStatus] = useState<"checking" | "online" | "unreachable">("checking");

  useEffect(() => {
    let cancelled = false;
    setApiStatus("checking");
    fetchJson("/health", { timeoutMs: 4000, retries: 0 }).then((result) => {
      if (!cancelled) setApiStatus(result.status === "success" ? "online" : "unreachable");
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <View style={styles.statusCard}>
        <View style={styles.statusLine}>
          <View
            style={[
              styles.statusDot,
              {
                backgroundColor:
                  apiStatus === "online"
                    ? theme.success
                    : apiStatus === "unreachable"
                      ? theme.accent
                      : theme.muted,
              },
            ]}
          />
          <Text style={styles.statusText}>
            API {apiStatus === "checking" ? "checking…" : apiStatus}
          </Text>
        </View>
        <Text style={styles.statusUrl} numberOfLines={1}>
          {API_BASE_URL}
        </Text>
        <Text style={styles.statusUrl}>
          v{Constants.expoConfig?.version ?? "—"} · build{" "}
          {Constants.nativeBuildVersion ?? Constants.expoConfig?.ios?.buildNumber ?? "—"}
        </Text>
      </View>

      <Text style={styles.sectionTitle}>Legacy / test screens</Text>
      <View style={styles.list}>
        {LEGACY_SCREENS.map((screen) => (
          <Pressable
            key={screen.href}
            style={styles.listItem}
            onPress={() => router.push(screen.href)}
            accessibilityRole="button"
            accessibilityLabel={screen.label}
          >
            <Text style={styles.listItemText}>{screen.label}</Text>
            <Ionicons name="chevron-forward" size={16} color={theme.textSecondary} />
          </Pressable>
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: theme.background },
  content: { padding: spacing.lg, paddingBottom: 40 },
  statusCard: {
    backgroundColor: theme.surface,
    borderColor: theme.border,
    borderWidth: 1,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.xl,
    gap: 4,
  },
  statusLine: { flexDirection: "row", alignItems: "center", gap: 8 },
  statusDot: { width: 7, height: 7, borderRadius: 3.5 },
  statusText: { color: theme.text, fontSize: 13, fontWeight: "600", textTransform: "capitalize" },
  statusUrl: { color: theme.muted, fontSize: 12 },
  sectionTitle: {
    color: theme.textSecondary,
    fontSize: 11,
    fontWeight: weight.label,
    letterSpacing: tracking.label,
    marginBottom: spacing.sm,
  },
  list: {
    backgroundColor: theme.surface,
    borderColor: theme.border,
    borderWidth: 1,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
  },
  listItem: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: theme.border,
  },
  listItemText: { color: theme.text, fontSize: type.body, fontWeight: "500" },
});
