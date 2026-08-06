import { useEffect, useState } from "react";
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from "react-native";

import { API_BASE_URL } from "../constants/config";
import { theme } from "../constants/theme";
import { FadeIn } from "../components/FadeIn";
import { PressableScale } from "../components/PressableScale";

type Memory = {
  id: string;
  content: string;
  primary_branch: string;
  memory_type: string;
  importance: number;
  confidence: number;
  status: string;
};

export default function MemoryInboxScreen() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(true);
  const [pendingId, setPendingId] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/v1/memories?inbox_only=true`);
      setMemories((await response.json()) as Memory[]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const confirm = async (id: string, confirmed: boolean) => {
    setPendingId(id);
    try {
      await fetch(`${API_BASE_URL}/v1/memories/${id}/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirmed }),
      });
      await load();
    } finally {
      setPendingId(null);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={theme.accent} />
      </View>
    );
  }

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Memory inbox</Text>
      <Text style={styles.subtitle}>
        Logan holds uncertain but potentially useful learning here until it is confirmed.
      </Text>

      {memories.length === 0 ? (
        <View style={styles.empty}>
          <Text style={styles.emptyTitle}>Nothing waiting</Text>
          <Text style={styles.emptyText}>
            New high-value inferences will appear here for review.
          </Text>
        </View>
      ) : (
        memories.map((memory, index) => {
          const isPending = pendingId === memory.id;
          return (
            <FadeIn key={memory.id} delay={index * 60}>
              <View style={[styles.card, isPending && styles.cardPending]}>
                <Text style={styles.branch}>{memory.primary_branch}</Text>
                <Text style={styles.contentText}>{memory.content}</Text>
                <Text style={styles.meta}>
                  Importance {memory.importance} · Confidence {memory.confidence}
                </Text>
                <View style={styles.actions}>
                  <PressableScale
                    style={styles.reject}
                    onPress={() => confirm(memory.id, false)}
                    disabled={isPending}
                  >
                    {isPending ? (
                      <ActivityIndicator color={theme.text} size="small" />
                    ) : (
                      <Text style={styles.rejectText}>Reject</Text>
                    )}
                  </PressableScale>
                  <PressableScale
                    style={styles.confirm}
                    onPress={() => confirm(memory.id, true)}
                    disabled={isPending}
                  >
                    {isPending ? (
                      <ActivityIndicator color="#FFFFFF" size="small" />
                    ) : (
                      <Text style={styles.confirmText}>Confirm</Text>
                    )}
                  </PressableScale>
                </View>
              </View>
            </FadeIn>
          );
        })
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: theme.background },
  content: { padding: 18, paddingBottom: 40 },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: theme.background,
  },
  title: { color: theme.text, fontSize: 30, fontWeight: "900" },
  subtitle: {
    color: theme.textSecondary,
    fontSize: 15,
    lineHeight: 22,
    marginTop: 10,
    marginBottom: 24,
  },
  empty: {
    backgroundColor: theme.surface,
    borderColor: theme.border,
    borderWidth: 1,
    borderRadius: 18,
    padding: 18,
  },
  emptyTitle: { color: theme.text, fontSize: 18, fontWeight: "800" },
  emptyText: { color: theme.textSecondary, marginTop: 7, lineHeight: 21 },
  card: {
    backgroundColor: theme.surface,
    borderColor: theme.border,
    borderWidth: 1,
    borderRadius: 18,
    padding: 18,
    marginBottom: 12,
  },
  cardPending: {
    opacity: 0.6,
  },
  branch: { color: theme.accent, fontSize: 10, fontWeight: "900", letterSpacing: 1.1 },
  contentText: {
    color: theme.text,
    fontSize: 17,
    lineHeight: 24,
    fontWeight: "700",
    marginTop: 10,
  },
  meta: { color: theme.textSecondary, fontSize: 12, marginTop: 10 },
  actions: { flexDirection: "row", gap: 10, marginTop: 16 },
  reject: {
    flex: 1,
    borderColor: theme.border,
    borderWidth: 1,
    borderRadius: 13,
    alignItems: "center",
    paddingVertical: 13,
  },
  rejectText: { color: theme.text, fontWeight: "800" },
  confirm: {
    flex: 1,
    backgroundColor: theme.accent,
    borderRadius: 13,
    alignItems: "center",
    paddingVertical: 13,
  },
  confirmText: { color: "#FFFFFF", fontWeight: "900" },
});
