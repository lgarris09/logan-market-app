// V2.3A consumer closeout -- the one piece of sign-in UI that's genuinely
// identical between the first-run "Make STRATUS yours" screen and the
// standalone Account screen (reached later from the menu): the Apple/
// Google/Email method rows and the email/code sub-forms. Deliberately
// styled as one coherent auth surface (graphite rows, not three unrelated
// buttons) per the owner's brand-closeout direction -- no solid-orange
// buttons here; orange is reserved for the one primary action per screen
// (e.g. onboarding's "Continue to STRATUS"), not every row.
import { ActivityIndicator, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { font, radius, spacing, theme, type } from "../../constants/theme";
import { EmailStage } from "../../hooks/useStratusAuth";

function MethodRow({
  icon,
  label,
  onPress,
  disabled,
}: {
  icon: React.ComponentProps<typeof Ionicons>["name"];
  label: string;
  onPress: () => void;
  disabled?: boolean;
}) {
  return (
    <TouchableOpacity
      style={styles.methodRow}
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityLabel={label}
    >
      <Ionicons name={icon} size={19} color={theme.text} style={styles.methodIcon} />
      <Text style={styles.methodLabel}>{label}</Text>
    </TouchableOpacity>
  );
}

export function AuthMethodControls({
  stage,
  setStage,
  email,
  setEmail,
  code,
  setCode,
  busy,
  onOAuth,
  onSendCode,
  onVerifyCode,
}: {
  stage: EmailStage;
  setStage: (stage: EmailStage) => void;
  email: string;
  setEmail: (email: string) => void;
  code: string;
  setCode: (code: string) => void;
  busy: boolean;
  onOAuth: (strategy: "oauth_apple" | "oauth_google") => void;
  onSendCode: () => void;
  onVerifyCode: () => void;
}) {
  return (
    <View>
      <MethodRow icon="logo-apple" label="Continue with Apple" onPress={() => onOAuth("oauth_apple")} disabled={busy} />
      <MethodRow icon="logo-google" label="Continue with Google" onPress={() => onOAuth("oauth_google")} disabled={busy} />

      {stage === "idle" && (
        <MethodRow icon="mail-outline" label="Continue with Email" onPress={() => setStage("email")} disabled={busy} />
      )}

      {stage === "email" && (
        <View style={styles.emailForm}>
          <TextInput
            style={styles.input}
            placeholder="you@example.com"
            placeholderTextColor={theme.muted}
            autoCapitalize="none"
            keyboardType="email-address"
            value={email}
            onChangeText={setEmail}
            accessibilityLabel="Email address"
          />
          <TouchableOpacity style={styles.primaryButton} onPress={onSendCode} disabled={busy}>
            {busy ? (
              <ActivityIndicator color={theme.background} />
            ) : (
              <Text style={styles.primaryButtonText}>Send code</Text>
            )}
          </TouchableOpacity>
        </View>
      )}

      {stage === "code" && (
        <View style={styles.emailForm}>
          <TextInput
            style={styles.input}
            placeholder="6-digit code"
            placeholderTextColor={theme.muted}
            keyboardType="number-pad"
            value={code}
            onChangeText={setCode}
            accessibilityLabel="Verification code"
          />
          <TouchableOpacity style={styles.primaryButton} onPress={onVerifyCode} disabled={busy}>
            {busy ? (
              <ActivityIndicator color={theme.background} />
            ) : (
              <Text style={styles.primaryButtonText}>Verify</Text>
            )}
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  methodRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: theme.surface,
    borderWidth: 1,
    borderColor: theme.border,
    borderRadius: radius.md,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    marginBottom: spacing.sm,
  },
  methodIcon: { width: 26 },
  methodLabel: { fontFamily: font.bodyMedium, color: theme.text, fontSize: type.body + 1 },
  emailForm: { gap: spacing.sm, marginBottom: spacing.sm },
  input: {
    borderWidth: 1,
    borderColor: theme.border,
    backgroundColor: theme.surface,
    borderRadius: radius.md,
    padding: spacing.md,
    color: theme.text,
    fontSize: 16,
  },
  primaryButton: {
    backgroundColor: theme.accent,
    borderRadius: radius.md,
    paddingVertical: spacing.md,
    alignItems: "center",
  },
  primaryButtonText: { fontFamily: font.headingMedium, color: theme.background, fontSize: 16 },
});
