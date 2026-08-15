import { StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { font, radius, theme, tracking, type } from "../constants/theme";
import { Recommendation, RecommendationRisk } from "../types/loganFeed";

const RISK_LABEL: Record<RecommendationRisk, string> = {
  low: "LOW RISK",
  moderate: "MODERATE RISK",
  high: "HIGH RISK",
  speculative: "SPECULATIVE",
};

// STRATUS Recommendation + Risk -- the presentation foundation for a future
// premium capability (Sprint 3.6, sections 9-14). Free STRATUS explains what
// is happening, what changed, and why it matters (the sections above this
// one in Vessel.tsx); this is the boundary where a future paid tier would
// additionally answer "what should I consider doing about it." No backend
// today populates `recommendation` (see types/loganFeed.ts), so this always
// renders the locked teaser branch in the current app -- honestly, rather
// than fabricating an action/risk/condition. The unlocked branch exists so
// the component doesn't need to be rebuilt once a real recommendation
// exists server-side; it isn't reachable from any current API response, and
// nothing here assumes who a future subscription check would come from.
//
// Confidence vs. risk (section 11): CONFIDENCE (rendered in the card
// header, from confidence_score/confidence_label) measures how strongly
// STRATUS supports the underlying opportunity/conclusion. RISK here
// measures how much uncertainty/downside is associated with *acting* on the
// recommendation -- a different axis, not a second copy of the same number.
// Always labeled "RECOMMENDATION RISK" (never a bare "MODERATE"/"HIGH"
// alone) specifically so the two can't be mistaken for the same
// measurement when both appear on one card.
//
// Deliberately not Pressable: a locked section that does nothing on tap is
// the same class of fake affordance this product's rules forbid for a
// non-functional mic icon or a fake "SOON" link -- this becomes tappable
// (opening a real subscription/feature explanation) only once that surface
// actually exists.
//
// Opportunity Card redesign (owner rendering reference): always
// theme.accent (burnt orange), not the entity's domain color -- this panel
// means "timing/action, premium gate," a fixed meaning independent of which
// entity it's attached to, same reasoning as STRATUS TAKE/WHY IT MATTERS
// NOW/WHAT CHANGED's own fixed section colors in Vessel.tsx. The bordered
// panel treatment (vs. the plain inline sections above it) marks this as
// the one section that leads somewhere -- a distinct call-to-action, not
// just more analysis text.
export function RecommendationPanel({ recommendation }: { recommendation?: Recommendation }) {
  if (!recommendation) {
    return (
      <View style={styles.panel}>
        <View style={styles.lockedHeaderRow}>
          <View style={styles.lockedHeaderLeft}>
            <Ionicons name="lock-closed" size={13} color={theme.accent} />
            <Text style={styles.label}>STRATUS RECOMMENDATION</Text>
          </View>
          <Ionicons name="arrow-forward" size={16} color={theme.accent} />
        </View>
        <Text style={styles.teaser}>
          See the recommended action, risk level, and what could change the recommendation with
          STRATUS+.
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.panel}>
      <View style={[styles.lockedHeaderLeft, styles.unlockedHeaderLeft]}>
        <Ionicons name="star" size={13} color={theme.accent} />
        <Text style={styles.label}>STRATUS RECOMMENDATION</Text>
      </View>
      <Text style={styles.action}>{recommendation.action}</Text>

      <View style={[styles.riskPill, { borderColor: theme.accent }]}>
        <Text style={[styles.riskPillText, { color: theme.accent }]}>
          RECOMMENDATION RISK · {RISK_LABEL[recommendation.risk]}
        </Text>
      </View>

      {!!recommendation.whatWouldChangeThis && (
        <View style={styles.changeBlock}>
          <Text style={styles.changeLabel}>WHAT WOULD CHANGE THIS</Text>
          <Text style={styles.teaser}>{recommendation.whatWouldChangeThis}</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  panel: {
    borderWidth: 1,
    borderColor: theme.accent,
    borderRadius: radius.md,
    padding: 14,
    marginBottom: 16,
  },
  lockedHeaderRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 8,
  },
  lockedHeaderLeft: { flexDirection: "row", alignItems: "center", gap: 7 },
  unlockedHeaderLeft: { marginBottom: 8 },
  label: {
    color: theme.accent,
    fontSize: type.micro,
    fontFamily: font.metadata,
    letterSpacing: tracking.label,
  },
  teaser: { color: theme.textSecondary, fontSize: 13, fontFamily: font.body, lineHeight: 19 },
  action: {
    color: theme.text,
    fontSize: 14,
    fontFamily: font.bodyMedium,
    lineHeight: 20,
    marginBottom: 8,
  },
  riskPill: {
    alignSelf: "flex-start",
    borderWidth: 1,
    borderRadius: radius.pill,
    paddingHorizontal: 8,
    paddingVertical: 3,
    marginBottom: 10,
  },
  riskPillText: { fontSize: 9, fontFamily: font.metadata, letterSpacing: tracking.metadata },
  changeBlock: { marginTop: 2 },
  changeLabel: {
    color: theme.muted,
    fontSize: 9,
    fontFamily: font.metadata,
    letterSpacing: tracking.metadata,
    marginBottom: 4,
  },
});
