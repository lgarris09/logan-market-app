// V2.3A consumer closeout -- the "Make STRATUS yours" content block, shared
// between the first-run onboarding account step (app/onboarding/account.tsx)
// and the standalone Account screen reached later from the menu
// (app/account.tsx). One design, one copy, two contexts -- the only
// difference between them is whether the guest option is shown (only makes
// sense during first-run; someone who already opened this screen from the
// menu is, by definition, already using STRATUS as a guest) and what
// happens after a successful auth/guest choice.
import { Text, TouchableOpacity, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { font, radius, spacing, theme, type } from "../../constants/theme";
import { useStratusAuth } from "../../hooks/useStratusAuth";
import { AuthMethodControls } from "./AuthMethodControls";

export function MakeStratusYoursCard({
  showGuestOption = false,
  onGuestContinue,
  onAuthComplete,
}: {
  showGuestOption?: boolean;
  onGuestContinue?: () => void;
  onAuthComplete?: () => void;
}) {
  const auth = useStratusAuth(onAuthComplete);

  return (
    <View>
      <Text style={styles.heading}>
        Make <Text style={styles.headingAccent}>STRATUS</Text> yours.
      </Text>
      <Text style={styles.subhead}>
        Create an account to keep your intelligence synced and personalized across devices.
      </Text>

      <AuthMethodControls
        stage={auth.stage}
        setStage={auth.setStage}
        email={auth.email}
        setEmail={auth.setEmail}
        code={auth.code}
        setCode={auth.setCode}
        busy={auth.busy}
        onOAuth={auth.handleOAuth}
        onSendCode={auth.handleSendCode}
        onVerifyCode={auth.handleVerifyCode}
      />

      {showGuestOption && (
        <>
          <View style={styles.divider}>
            <View style={styles.dividerLine} />
            <Text style={styles.dividerText}>OR</Text>
            <View style={styles.dividerLine} />
          </View>
          <TouchableOpacity
            style={styles.guestRow}
            onPress={onGuestContinue}
            accessibilityRole="button"
            accessibilityLabel="Continue as guest"
          >
            <Ionicons name="person-outline" size={19} color={theme.textSecondary} style={styles.guestIcon} />
            <View>
              <Text style={styles.guestLabel}>Continue as guest</Text>
              <Text style={styles.guestSublabel}>Explore STRATUS without an account.</Text>
            </View>
          </TouchableOpacity>
        </>
      )}

      <View style={styles.privacyRow}>
        <Ionicons name="shield-checkmark-outline" size={14} color={theme.muted} />
        <Text style={styles.privacyText}>We never share your data. Ever.</Text>
      </View>

      <Text style={styles.disclaimer}>
        New here? We&rsquo;ll create your account automatically. Already have one? We&rsquo;ll sign you in.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  heading: {
    fontFamily: font.heading,
    fontSize: type.display - 4,
    color: theme.text,
    marginBottom: spacing.sm,
  },
  headingAccent: { color: theme.accent },
  subhead: {
    fontFamily: font.body,
    fontSize: type.body,
    color: theme.textSecondary,
    lineHeight: 21,
    marginBottom: spacing.xl,
  },
  divider: { flexDirection: "row", alignItems: "center", marginVertical: spacing.md },
  dividerLine: { flex: 1, height: StyleSheet.hairlineWidth, backgroundColor: theme.border },
  dividerText: {
    fontFamily: font.metadata,
    fontSize: type.micro,
    color: theme.muted,
    marginHorizontal: spacing.sm,
  },
  guestRow: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderColor: theme.border,
    borderRadius: radius.md,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    marginBottom: spacing.lg,
  },
  guestIcon: { width: 26 },
  guestLabel: { fontFamily: font.bodyMedium, color: theme.text, fontSize: type.body },
  guestSublabel: { fontFamily: font.body, color: theme.muted, fontSize: type.label, marginTop: 2 },
  privacyRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    marginTop: spacing.sm,
  },
  privacyText: { fontFamily: font.body, color: theme.muted, fontSize: type.label },
  disclaimer: {
    fontFamily: font.body,
    color: theme.muted,
    fontSize: type.label,
    textAlign: "center",
    lineHeight: 17,
    marginTop: spacing.md,
  },
});
