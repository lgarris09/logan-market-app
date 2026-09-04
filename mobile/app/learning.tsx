// Consumer Learning Controls (STRATUS 3.6.12 V1a closeout) -- the mobile
// UI for the existing GET /v1/learning/summary and POST /v1/learning/suppress
// backend capabilities (see lib/learningControls.ts). Reached from
// account.tsx's PERSONALIZATION section ("Learned traits").
//
// Deliberately minimal, per the approved scope: a plain-language list of
// what STRATUS has learned, with an explicit/inferred distinction and a
// "Stop using this reason" action where the backend allows it -- no
// strength meters, no trait editing, no new preference categories beyond
// what the backend already exposes. This screen never computes or decides
// anything about learning itself; it only renders and forwards user intent
// to the two existing endpoints.
import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { font, radius, spacing, theme, type } from "../constants/theme";
import { FadeIn } from "../components/FadeIn";
import { PressableScale } from "../components/PressableScale";
import {
  LearningSummary,
  LearningTrait,
  getLearningSummary,
  suppressLearningReason,
} from "../lib/learningControls";

type LoadState = "loading" | "loaded" | "error";

export default function LearningControlsScreen() {
  const [state, setState] = useState<LoadState>("loading");
  const [summary, setSummary] = useState<LearningSummary | null>(null);
  const [suppressingId, setSuppressingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setState("loading");
    const result = await getLearningSummary();
    if (result === null) {
      setState("error");
      return;
    }
    setSummary(result);
    setState("loaded");
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleSuppress = async (trait: LearningTrait) => {
    if (suppressingId) return; // one in flight at a time -- no double-tap races
    setSuppressingId(trait.entityId);
    const ok = await suppressLearningReason(trait.entityId);
    if (ok) {
      // Re-fetches rather than removing `trait` from local state directly --
      // a suppression can affect more than the tapped row (see
      // lib/learningControls.ts's own comment), so the server's fresh view
      // is the one source of truth for what's still learned.
      await load();
    }
    setSuppressingId(null);
  };

  if (state === "loading") {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={theme.accent} />
      </View>
    );
  }

  if (state === "error") {
    return (
      <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
        <View style={styles.empty}>
          <Ionicons name="cloud-offline-outline" size={22} color={theme.textSecondary} />
          <Text style={styles.emptyTitle}>Couldn&rsquo;t load this right now</Text>
          <Text style={styles.emptyText}>
            STRATUS couldn&rsquo;t reach the server to show what it&rsquo;s learned. Check your
            connection and try again.
          </Text>
          <PressableScale style={styles.retryButton} onPress={load}>
            <Text style={styles.retryButtonText}>Try again</Text>
          </PressableScale>
        </View>
      </ScrollView>
    );
  }

  const traits = summary?.traits ?? [];

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Text style={styles.title}>What STRATUS has learned</Text>
      {!!summary?.explanation && <Text style={styles.explanation}>{summary.explanation}</Text>}

      {traits.length === 0 ? (
        <View style={styles.empty}>
          <Ionicons name="sparkles-outline" size={22} color={theme.textSecondary} />
          <Text style={styles.emptyTitle}>Nothing learned yet</Text>
          <Text style={styles.emptyText}>
            As you watch, correct, or return to opportunities, STRATUS will start noticing patterns
            and explain them here.
          </Text>
        </View>
      ) : (
        traits.map((trait, index) => (
          <FadeIn key={trait.entityId} delay={index * 60}>
            <TraitCard
              trait={trait}
              isSuppressing={suppressingId === trait.entityId}
              onSuppress={() => handleSuppress(trait)}
            />
          </FadeIn>
        ))
      )}
    </ScrollView>
  );
}

function TraitCard({
  trait,
  isSuppressing,
  onSuppress,
}: {
  trait: LearningTrait;
  isSuppressing: boolean;
  onSuppress: () => void;
}) {
  const basisLabel =
    trait.basis === "explicit" ? "You told STRATUS this" : "Noticed from your activity";

  return (
    <View style={styles.card}>
      <View style={styles.basisPill}>
        <Text style={styles.basisPillText}>{basisLabel}</Text>
      </View>
      <Text style={styles.traitDescription}>{trait.description}</Text>
      {trait.canSuppress && (
        <PressableScale
          style={styles.suppressButton}
          onPress={onSuppress}
          disabled={isSuppressing}
          accessibilityRole="button"
          accessibilityLabel={`Stop using this reason: ${trait.description}`}
          accessibilityState={{ disabled: isSuppressing, busy: isSuppressing }}
        >
          {isSuppressing ? (
            <ActivityIndicator color={theme.textSecondary} size="small" />
          ) : (
            <Text style={styles.suppressButtonText}>Stop using this reason</Text>
          )}
        </PressableScale>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: theme.background },
  center: {
    flex: 1,
    backgroundColor: theme.background,
    alignItems: "center",
    justifyContent: "center",
  },
  content: { padding: spacing.xl, paddingBottom: spacing.xxl, gap: spacing.md },
  title: { fontFamily: font.heading, fontSize: type.title, color: theme.text },
  explanation: {
    fontFamily: font.body,
    fontSize: type.body,
    color: theme.muted,
    lineHeight: 21,
    marginBottom: spacing.sm,
  },
  empty: {
    backgroundColor: theme.surface,
    borderColor: theme.border,
    borderWidth: 1,
    borderRadius: radius.md,
    padding: spacing.lg,
    alignItems: "center",
    gap: spacing.sm,
  },
  emptyTitle: { fontFamily: font.bodyMedium, color: theme.text, fontSize: type.body },
  emptyText: {
    fontFamily: font.body,
    color: theme.muted,
    fontSize: type.micro + 1,
    lineHeight: 20,
    textAlign: "center",
  },
  retryButton: {
    borderWidth: 1,
    borderColor: theme.border,
    borderRadius: radius.md,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg,
    marginTop: spacing.xs,
  },
  retryButtonText: { fontFamily: font.bodyMedium, color: theme.text, fontSize: type.micro + 1 },
  card: {
    backgroundColor: theme.surface,
    borderColor: theme.border,
    borderWidth: 1,
    borderRadius: radius.md,
    padding: spacing.lg,
    gap: spacing.sm,
  },
  basisPill: {
    alignSelf: "flex-start",
    backgroundColor: theme.surfaceSoft,
    borderRadius: radius.pill,
    paddingVertical: 3,
    paddingHorizontal: spacing.sm,
  },
  basisPillText: {
    fontFamily: font.metadata,
    fontSize: 10,
    color: theme.muted,
    letterSpacing: 0.6,
    textTransform: "uppercase",
  },
  traitDescription: {
    fontFamily: font.body,
    fontSize: type.body,
    color: theme.text,
    lineHeight: 22,
  },
  suppressButton: {
    borderWidth: 1,
    borderColor: theme.border,
    borderRadius: radius.md,
    paddingVertical: spacing.sm,
    alignItems: "center",
    marginTop: spacing.xs,
  },
  suppressButtonText: { fontFamily: font.bodyMedium, color: theme.textSecondary, fontSize: 14 },
});
