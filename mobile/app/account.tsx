// V2.3A -- Identity & Account Foundation, consumer closeout pass. Reached
// two ways: from the menu at any time (this file), and as the first-run
// onboarding account step (app/onboarding/account.tsx) -- both share the
// same underlying auth logic (hooks/useStratusAuth.ts) and the same "Make
// STRATUS yours" content (components/auth/MakeStratusYoursCard.tsx); this
// file's own job is just the standalone-screen shell around it (native
// Stack header from _layout.tsx, signed-in state, sign-out, deletion).
import { useCallback, useState } from "react";
import { ActivityIndicator, Alert, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import * as WebBrowser from "expo-web-browser";

import { font, radius, spacing, theme, type } from "../constants/theme";
import { deleteAccount } from "../lib/account";
import { isClerkConfigured } from "../lib/clerkConfig";
import { MakeStratusYoursCard } from "../components/auth/MakeStratusYoursCard";

// Required once, at module scope, by Clerk's own documented Expo OAuth
// pattern -- completes a pending browser-based auth session if the app was
// backgrounded mid-flow and is now foregrounding via the OAuth redirect.
WebBrowser.maybeCompleteAuthSession();

export default function AccountScreen() {
  if (!isClerkConfigured()) {
    return <GuestOnlyNotice />;
  }
  return <ConfiguredAccountScreen />;
}

/** Every environment until the owner supplies real Clerk credentials (see
 * docs/DECISIONS.md's ADR-069) -- the anonymous-only experience is complete
 * and correct on its own; this is purely informational. */
function GuestOnlyNotice() {
  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <View style={styles.guestIconCircle}>
        <Ionicons name="person-outline" size={22} color={theme.textSecondary} />
      </View>
      <Text style={styles.heading}>You&rsquo;re using STRATUS as a guest</Text>
      <Text style={styles.body}>
        STRATUS works fully without an account. Sign-in will appear here once it&rsquo;s configured
        for this build.
      </Text>
    </ScrollView>
  );
}

// Deferred to a dynamic import inside ConfiguredAccountScreen's own module
// scope guard would be unnecessarily indirect here -- @clerk/expo's hooks
// are safe to import unconditionally; they simply require a ClerkProvider
// ancestor, which _layout.tsx only ever mounts when isClerkConfigured().
// eslint-disable-next-line import/first
import { useAuth, useUser } from "@clerk/expo";

function ConfiguredAccountScreen() {
  const { isLoaded, isSignedIn, signOut } = useAuth();

  if (!isLoaded) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator color={theme.accent} />
      </View>
    );
  }

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      {isSignedIn ? <SignedInView onSignOut={signOut} /> : <MakeStratusYoursCard />}
    </ScrollView>
  );
}

function SignedInView({ onSignOut }: { onSignOut: () => Promise<void> }) {
  const { user } = useUser();
  const [busy, setBusy] = useState(false);

  const handleSignOut = useCallback(async () => {
    setBusy(true);
    try {
      await onSignOut();
    } finally {
      setBusy(false);
    }
  }, [onSignOut]);

  const handleDeleteAccount = useCallback(() => {
    Alert.alert(
      "Delete account data",
      "This permanently removes your STRATUS interaction history, watch state, and notification settings. This cannot be undone.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: async () => {
            const ok = await deleteAccount();
            if (ok) {
              await onSignOut();
            } else {
              Alert.alert("Something went wrong", "Please try again.");
            }
          },
        },
      ]
    );
  }, [onSignOut]);

  const identifier =
    user?.primaryEmailAddress?.emailAddress ?? user?.externalAccounts?.[0]?.provider ?? "your account";

  return (
    <View>
      <View style={styles.profileHeader}>
        <View style={styles.profileAvatar}>
          <Ionicons name="checkmark" size={22} color={theme.accent} />
        </View>
        <Text style={styles.heading}>You&rsquo;re signed in</Text>
        <Text style={styles.identifierText}>{identifier}</Text>
        <Text style={styles.body}>Your STRATUS intelligence is synced to this account.</Text>
      </View>

      <TouchableOpacity style={styles.signOutButton} onPress={handleSignOut} disabled={busy}>
        <Text style={styles.signOutButtonText}>{busy ? "Signing out..." : "Sign out"}</Text>
      </TouchableOpacity>

      <View style={styles.dangerZone}>
        <Text style={styles.dangerZoneLabel}>DATA &amp; PRIVACY</Text>
        <TouchableOpacity style={styles.dangerRow} onPress={handleDeleteAccount}>
          <Ionicons name="trash-outline" size={17} color={theme.warning} style={styles.dangerIcon} />
          <Text style={styles.dangerRowText}>Delete my data</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: theme.background },
  centered: {
    flex: 1,
    backgroundColor: theme.background,
    alignItems: "center",
    justifyContent: "center",
  },
  content: { padding: spacing.xl, paddingTop: spacing.xxl, gap: spacing.md },
  heading: {
    fontFamily: font.heading,
    fontSize: type.title,
    color: theme.text,
    marginBottom: spacing.sm,
  },
  body: {
    fontFamily: font.body,
    fontSize: type.body,
    color: theme.muted,
  },
  guestIconCircle: {
    width: 48,
    height: 48,
    borderRadius: radius.pill,
    backgroundColor: theme.surface,
    borderWidth: 1,
    borderColor: theme.border,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.lg,
  },
  profileHeader: { alignItems: "center", marginBottom: spacing.xl, gap: 4 },
  profileAvatar: {
    width: 64,
    height: 64,
    borderRadius: radius.pill,
    backgroundColor: theme.accentSoft,
    borderWidth: 1,
    borderColor: theme.border,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.md,
  },
  identifierText: {
    fontFamily: font.bodyMedium,
    fontSize: type.body,
    color: theme.textSecondary,
  },
  signOutButton: {
    borderWidth: 1,
    borderColor: theme.border,
    borderRadius: radius.md,
    paddingVertical: spacing.md,
    alignItems: "center",
    marginBottom: spacing.xxl,
  },
  signOutButtonText: { fontFamily: font.bodyMedium, color: theme.textSecondary, fontSize: 15 },
  dangerZone: { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: theme.border, paddingTop: spacing.lg },
  dangerZoneLabel: {
    fontFamily: font.metadata,
    fontSize: type.micro,
    color: theme.muted,
    letterSpacing: 1.4,
    marginBottom: spacing.sm,
  },
  dangerRow: { flexDirection: "row", alignItems: "center", paddingVertical: spacing.sm },
  dangerIcon: { marginRight: spacing.sm },
  dangerRowText: { fontFamily: font.bodyMedium, color: theme.warning, fontSize: 15 },
});
