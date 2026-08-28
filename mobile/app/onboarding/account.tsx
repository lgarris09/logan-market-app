// V2.3A consumer closeout -- first-run "Make STRATUS yours" step. Same
// underlying auth logic and same content block as the standalone Account
// screen (see components/auth/MakeStratusYoursCard.tsx) -- this file only
// adds the onboarding-specific framing: a back chevron to the intro screen,
// the guest option (only makes sense here, not on the menu-reached Account
// screen), and advancing to the interests step on either path.
//
// No hard account wall: if Clerk isn't configured for this build at all,
// onboarding skips straight past this step (see app/onboarding/intro.tsx's
// advance target being conditional would be one option, but simpler and
// more robust is handling it here -- see the isClerkConfigured() guard
// below, mirroring app/account.tsx's own).
import { useEffect } from "react";
import { KeyboardAvoidingView, Platform, SafeAreaView, ScrollView, StyleSheet, TouchableOpacity, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";

import { spacing, theme } from "../../constants/theme";
import { isClerkConfigured } from "../../lib/clerkConfig";
import { MakeStratusYoursCard } from "../../components/auth/MakeStratusYoursCard";

function goToInterests() {
  // push, not replace: interests.tsx's back chevron needs a real history
  // entry to return to. Onboarding's history is fully cleared in one shot
  // by interests.tsx's own final router.replace("/"), not per-step here.
  router.push("/onboarding/interests");
}

export default function OnboardingAccountScreen() {
  useEffect(() => {
    // No hard account wall (explicit product requirement): a build with no
    // Clerk configured has nothing for this step to offer, so it must never
    // block onboarding -- skip straight to interests.
    if (!isClerkConfigured()) {
      goToInterests();
    }
  }, []);

  if (!isClerkConfigured()) {
    return <View style={styles.screen} />;
  }

  return <ConfiguredOnboardingAccount />;
}

// Deferred import, same reasoning as app/account.tsx: safe unconditionally,
// this component only ever renders once isClerkConfigured() is already true.
// eslint-disable-next-line import/first
import { useAuth } from "@clerk/expo";

function ConfiguredOnboardingAccount() {
  const { isLoaded, isSignedIn } = useAuth();

  useEffect(() => {
    // Safety net, not the primary path: if this device somehow already has
    // an active session by the time it reaches this step, don't make it
    // sign in again -- just continue the sequence.
    if (isLoaded && isSignedIn) {
      goToInterests();
    }
  }, [isLoaded, isSignedIn]);

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

      <KeyboardAvoidingView
        style={styles.keyboardView}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <MakeStratusYoursCard showGuestOption onGuestContinue={goToInterests} onAuthComplete={goToInterests} />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

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
  keyboardView: { flex: 1 },
  content: { flexGrow: 1, padding: spacing.xl, justifyContent: "center" },
});
