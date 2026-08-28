// V2.3A consumer closeout -- first-run Quick Interests. Declared cold-start
// preference only (see lib/interests.ts's own extensive documentation of
// the V2.3B boundary this deliberately stops short of) -- optional, and the
// last step before onboarding is marked complete and the user lands on the
// real Attention Field.
import { useState } from "react";
import { SafeAreaView, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";

import { font, radius, spacing, theme, type } from "../../constants/theme";
import { markOnboardingComplete } from "../../lib/onboarding";
import { INTEREST_CATEGORIES, InterestCategoryId, saveDeclaredInterests } from "../../lib/interests";

export default function InterestsScreen() {
  const [selected, setSelected] = useState<Set<InterestCategoryId>>(new Set());
  const [busy, setBusy] = useState(false);

  const toggle = (id: InterestCategoryId) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const finish = async () => {
    setBusy(true);
    try {
      await saveDeclaredInterests(Array.from(selected));
      await markOnboardingComplete();
      router.replace("/");
    } finally {
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={styles.screen}>
      <TouchableOpacity
        style={styles.backButton}
        onPress={() => router.back()}
        hitSlop={12}
        accessibilityRole="button"
        accessibilityLabel="Back"
      >
        <Ionicons name="chevron-back" size={20} color={theme.textSecondary} />
      </TouchableOpacity>

      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.heading}>
          What matters to you <Text style={styles.headingAccent}>right now?</Text>
        </Text>
        <Text style={styles.subhead}>This helps STRATUS focus on what&rsquo;s most important to you.</Text>

        <View style={styles.grid}>
          {INTEREST_CATEGORIES.map((category) => {
            const isSelected = selected.has(category.id);
            return (
              <TouchableOpacity
                key={category.id}
                style={[styles.card, isSelected && styles.cardSelected]}
                onPress={() => toggle(category.id)}
                accessibilityRole="button"
                accessibilityState={{ selected: isSelected }}
                accessibilityLabel={category.label}
              >
                <View style={styles.cardTopRow}>
                  <Ionicons name={category.icon} size={20} color={isSelected ? theme.accent : theme.textSecondary} />
                  {isSelected && (
                    <View style={styles.checkBadge}>
                      <Ionicons name="checkmark" size={12} color={theme.background} />
                    </View>
                  )}
                </View>
                <Text style={styles.cardLabel}>{category.label}</Text>
                <Text style={styles.cardDescription}>{category.description}</Text>
              </TouchableOpacity>
            );
          })}
        </View>

        <TouchableOpacity style={styles.continueButton} onPress={finish} disabled={busy}>
          <Text style={styles.continueButtonText}>{busy ? "Saving..." : "Continue to STRATUS"}</Text>
          <Ionicons name="arrow-forward" size={18} color={theme.background} />
        </TouchableOpacity>
        <Text style={styles.footnote}>You can update these anytime later.</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const CARD_WIDTH = "48%";

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: theme.background },
  backButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: "center",
    justifyContent: "center",
    marginLeft: spacing.lg,
    marginTop: spacing.sm,
  },
  content: { padding: spacing.xl, paddingBottom: spacing.xxl },
  heading: { fontFamily: font.heading, fontSize: type.title + 4, color: theme.text, marginBottom: spacing.sm },
  headingAccent: { color: theme.accent },
  subhead: { fontFamily: font.body, fontSize: type.body, color: theme.textSecondary, marginBottom: spacing.xl },
  grid: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between", gap: spacing.sm },
  card: {
    width: CARD_WIDTH,
    backgroundColor: theme.surface,
    borderWidth: 1,
    borderColor: theme.border,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  cardSelected: { borderColor: theme.accent, backgroundColor: theme.accentSoft },
  cardTopRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: spacing.sm },
  checkBadge: {
    width: 18,
    height: 18,
    borderRadius: 9,
    backgroundColor: theme.accent,
    alignItems: "center",
    justifyContent: "center",
  },
  cardLabel: { fontFamily: font.bodyMedium, fontSize: type.body, color: theme.text, marginBottom: 2 },
  cardDescription: { fontFamily: font.body, fontSize: type.micro + 1, color: theme.muted, lineHeight: 15 },
  continueButton: {
    flexDirection: "row",
    gap: spacing.sm,
    backgroundColor: theme.accent,
    borderRadius: radius.md,
    paddingVertical: spacing.md,
    alignItems: "center",
    justifyContent: "center",
    marginTop: spacing.lg,
  },
  continueButtonText: { fontFamily: font.headingMedium, color: theme.background, fontSize: 16 },
  footnote: {
    fontFamily: font.body,
    fontSize: type.label,
    color: theme.muted,
    textAlign: "center",
    marginTop: spacing.sm,
  },
});
