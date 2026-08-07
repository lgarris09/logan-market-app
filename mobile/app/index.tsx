import { useCallback, useEffect, useRef, useState } from "react";
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

import { theme } from "../constants/theme";
import { AttentionField } from "../components/AttentionField";
import { PressableScale } from "../components/PressableScale";
import { fetchJson } from "../lib/apiClient";
import { OpportunitiesResponse } from "../types/loganFeed";

type FeedState =
  | { kind: "loading" }
  | { kind: "loaded"; response: OpportunitiesResponse }
  | { kind: "empty" }
  | { kind: "timeout" }
  | { kind: "error"; message: string };

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
  const [state, setState] = useState<FeedState>({ kind: "loading" });
  const [menuOpen, setMenuOpen] = useState(false);

  const loadFeed = useCallback(async (signal: AbortSignal) => {
    setState({ kind: "loading" });
    const result = await fetchJson<OpportunitiesResponse>("/v1/opportunities", { signal });
    switch (result.status) {
      case "success":
        setState(
          result.data.items.length > 0
            ? { kind: "loaded", response: result.data }
            : { kind: "empty" }
        );
        return;
      case "timeout":
        setState({ kind: "timeout" });
        return;
      case "aborted":
        // Screen unmounted or a new load superseded this one -- no state update.
        return;
      case "error":
        setState({ kind: "error", message: result.message });
        return;
    }
  }, []);

  // Cancels the in-flight request if the screen unmounts before it resolves,
  // instead of calling setState on an unmounted component.
  const controllerRef = useRef<AbortController | null>(null);

  const startLoad = useCallback(() => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    loadFeed(controller.signal);
  }, [loadFeed]);

  useEffect(() => {
    startLoad();
    return () => controllerRef.current?.abort();
  }, [startLoad]);

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.topbar}>
        <Pressable
          onPress={() => setMenuOpen(true)}
          hitSlop={10}
          accessibilityRole="button"
          accessibilityLabel="Menu"
          accessibilityHint="Opens the list of preserved screens"
        >
          <Ionicons name="menu" size={22} color={theme.textSecondary} />
        </Pressable>
        <Text style={styles.wordmark}>LOGAN</Text>
        <View style={styles.liveDot} accessibilityElementsHidden importantForAccessibility="no" />
      </View>

      {state.kind === "loading" && (
        <View style={styles.centerFill} accessibilityLabel="Loading opportunities">
          <ActivityIndicator color={theme.accent} size="large" />
        </View>
      )}

      {state.kind === "error" && (
        <View style={styles.centerFill}>
          <View style={styles.error} accessibilityLiveRegion="polite">
            <Text style={styles.errorTitle}>Backend not connected</Text>
            <Text style={styles.errorText}>{state.message}</Text>
            <Text style={styles.errorText}>
              Start FastAPI and set your computer IP in constants/config.ts (or
              EXPO_PUBLIC_API_BASE_URL).
            </Text>
            <PressableScale
              style={styles.retryButton}
              onPress={startLoad}
              accessibilityLabel="Retry"
              accessibilityHint="Tries loading opportunities again"
            >
              <Text style={styles.retryText}>Retry</Text>
            </PressableScale>
          </View>
        </View>
      )}

      {state.kind === "timeout" && (
        <View style={styles.centerFill}>
          <View style={styles.error} accessibilityLiveRegion="polite">
            <Text style={styles.errorTitle}>Taking longer than expected</Text>
            <Text style={styles.errorText}>
              Logan didn&apos;t respond in time. Check that the backend is running and reachable.
            </Text>
            <PressableScale
              style={styles.retryButton}
              onPress={startLoad}
              accessibilityLabel="Retry"
              accessibilityHint="Tries loading opportunities again"
            >
              <Text style={styles.retryText}>Retry</Text>
            </PressableScale>
          </View>
        </View>
      )}

      {state.kind === "empty" && (
        <View style={styles.centerFill}>
          <View style={styles.error} accessibilityLiveRegion="polite">
            <Text style={styles.errorTitle}>Nothing to show yet</Text>
            <Text style={styles.errorText}>
              Logan isn&apos;t tracking any opportunities right now.
            </Text>
            <PressableScale
              style={styles.retryButton}
              onPress={startLoad}
              accessibilityLabel="Refresh"
              accessibilityHint="Checks again for opportunities"
            >
              <Text style={styles.retryText}>Refresh</Text>
            </PressableScale>
          </View>
        </View>
      )}

      {state.kind === "loaded" && <AttentionField items={state.response.items} />}

      <Modal
        visible={menuOpen}
        animationType="fade"
        transparent
        onRequestClose={() => setMenuOpen(false)}
      >
        <Pressable
          style={styles.menuBackdrop}
          onPress={() => setMenuOpen(false)}
          accessibilityRole="button"
          accessibilityLabel="Close menu"
        >
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
                accessibilityRole="button"
                accessibilityLabel={screen.label}
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
  retryButton: {
    backgroundColor: theme.accent,
    borderRadius: 13,
    alignItems: "center",
    paddingVertical: 12,
    marginTop: 12,
  },
  retryText: { color: "#FFFFFF", fontWeight: "900" },
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
