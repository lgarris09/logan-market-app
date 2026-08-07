import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Modal,
  Pressable,
  SafeAreaView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";

import { API_BASE_URL } from "../constants/config";
import { theme } from "../constants/theme";
import { AttentionField } from "../components/AttentionField";
import { OpportunitiesResponse } from "../types/loganFeed";

const LEGACY_SCREENS: {
  label: string;
  href: "/atmosphere-preview" | "/field-legacy" | "/classic" | "/ask" | "/memory" | "/demo";
}[] = [
  { label: "Atmosphere (Sprint 1 preview)", href: "/atmosphere-preview" },
  { label: "Opportunity Field (previous)", href: "/field-legacy" },
  { label: "Classic briefing (pre-Field home)", href: "/classic" },
  { label: "Ask Logan", href: "/ask" },
  { label: "Memory inbox", href: "/memory" },
  { label: "Tesla-only pipeline demo", href: "/demo" },
];

// Logan's home screen. One opportunity held in clear focus, everything else
// Logan is tracking present only as soft, ambient light around it. Swipe, or
// touch a glow directly, to bring something else into focus.
export default function AttentionFieldScreen() {
  const [feed, setFeed] = useState<OpportunitiesResponse | null>(null);
  const [error, setError] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);

  const loadFeed = useCallback(async () => {
    try {
      setError("");
      const response = await fetch(`${API_BASE_URL}/v1/opportunities`);
      if (!response.ok) throw new Error(`Server returned ${response.status}`);
      setFeed((await response.json()) as OpportunitiesResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reach Logan.");
    }
  }, []);

  useEffect(() => {
    loadFeed();
  }, [loadFeed]);

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.topbar}>
        <Pressable onPress={() => setMenuOpen(true)} hitSlop={10}>
          <Ionicons name="menu" size={22} color={theme.textSecondary} />
        </Pressable>
        <Text style={styles.wordmark}>LOGAN</Text>
        <View style={styles.liveDot} />
      </View>

      {!feed && !error && (
        <View style={styles.centerFill}>
          <ActivityIndicator color={theme.accent} size="large" />
        </View>
      )}

      {!!error && (
        <View style={styles.centerFill}>
          <View style={styles.error}>
            <Text style={styles.errorTitle}>Backend not connected</Text>
            <Text style={styles.errorText}>{error}</Text>
            <Text style={styles.errorText}>
              Start FastAPI and set your computer IP in constants/config.ts.
            </Text>
          </View>
        </View>
      )}

      {feed && feed.items.length > 0 && <AttentionField items={feed.items} />}

      <Modal
        visible={menuOpen}
        animationType="fade"
        transparent
        onRequestClose={() => setMenuOpen(false)}
      >
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
    paddingHorizontal: 20,
    paddingTop: 6,
    paddingBottom: 10,
  },
  wordmark: { color: theme.textSecondary, fontSize: 13, fontWeight: "800", letterSpacing: 5 },
  liveDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: theme.success },
  centerFill: { flex: 1, alignItems: "center", justifyContent: "center", paddingHorizontal: 24 },
  error: {
    backgroundColor: theme.accentSoft,
    borderColor: theme.accent,
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
    width: "100%",
  },
  errorTitle: { color: theme.text, fontWeight: "900", marginBottom: 7 },
  errorText: { color: theme.textSecondary, lineHeight: 20, marginBottom: 4 },
  menuBackdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.6)", justifyContent: "flex-end" },
  menuCard: {
    backgroundColor: theme.surface,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 22,
    paddingBottom: 40,
  },
  menuTitle: {
    color: theme.textSecondary,
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1,
    marginBottom: 14,
  },
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
