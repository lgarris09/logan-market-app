import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Stack, router } from "expo-router";
import { StatusBar } from "expo-status-bar";
import * as SplashScreen from "expo-splash-screen";
import { ClerkProvider } from "@clerk/expo";
import {
  useFonts,
  Inter_400Regular,
  Inter_500Medium,
  Inter_600SemiBold,
} from "@expo-google-fonts/inter";
import {
  InterTight_500Medium,
  InterTight_600SemiBold,
  InterTight_700Bold,
} from "@expo-google-fonts/inter-tight";

import { theme } from "../constants/theme";
import { CLERK_PUBLISHABLE_KEY, isClerkConfigured } from "../lib/clerkConfig";
import { clerkTokenCache } from "../lib/clerkTokenCache";
import { hasCompletedOnboarding } from "../lib/onboarding";

// V2.3A -- Identity & Account Foundation. `<ClerkProvider>` is mounted only
// when a real publishable key is configured -- unconfigured (every
// environment until the owner supplies real Clerk credentials, see
// docs/DECISIONS.md's ADR-069) means this component is a pure passthrough,
// and the app is byte-for-byte the pre-V2.3A anonymous-only experience: no
// sign-in UI, no Clerk network calls, no behavior change at all.
function AuthProvider({ children }: { children: ReactNode }) {
  if (!isClerkConfigured()) {
    return <>{children}</>;
  }
  return (
    <ClerkProvider
      publishableKey={CLERK_PUBLISHABLE_KEY as string}
      tokenCache={clerkTokenCache}
    >
      {children}
    </ClerkProvider>
  );
}

// Sprint 3.6 (brand-fidelity pass): the reference's typography panel
// specifies Inter/Inter Tight as the actual brand typeface (previously
// deliberately deferred as an unnecessary dependency -- see git history --
// added now with explicit sign-off since the reference calls for it by
// name and the system-font approximation couldn't reproduce its character).
// Keeping the splash screen up until fonts resolve avoids a flash of
// system-font text on first paint.
SplashScreen.preventAutoHideAsync().catch(() => {});

export default function RootLayout() {
  const [fontsLoaded, fontError] = useFonts({
    Inter_400Regular,
    Inter_500Medium,
    Inter_600SemiBold,
    InterTight_500Medium,
    InterTight_600SemiBold,
    InterTight_700Bold,
  });

  // V2.3A consumer closeout -- first-run onboarding gate. Checked once,
  // alongside font loading, behind the same held splash screen so a device
  // that needs onboarding never flashes the real Attention Field first.
  // `needsOnboarding` starts `false` (not `null`) deliberately: the default
  // must be "don't redirect" so a check that somehow never resolves fails
  // open into the existing anonymous-first experience, never into a stuck
  // splash or a forced redirect loop.
  const [onboardingChecked, setOnboardingChecked] = useState(false);
  const [needsOnboarding, setNeedsOnboarding] = useState(false);

  useEffect(() => {
    let cancelled = false;
    hasCompletedOnboarding()
      .then((completed) => {
        if (!cancelled) setNeedsOnboarding(!completed);
      })
      .catch(() => {
        // SecureStore unavailable is the same "fail open" case as above.
      })
      .finally(() => {
        if (!cancelled) setOnboardingChecked(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const ready = (fontsLoaded || fontError) && onboardingChecked;

  useEffect(() => {
    if (ready) SplashScreen.hideAsync().catch(() => {});
  }, [ready]);

  useEffect(() => {
    if (ready && needsOnboarding) router.replace("/onboarding/intro");
  }, [ready, needsOnboarding]);

  // Falls through to the system font (never a blank screen) if font loading
  // genuinely fails on-device rather than blocking the app forever.
  if (!ready) return null;

  return (
    <AuthProvider>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: theme.background },
          headerTintColor: theme.text,
          headerShadowVisible: false,
          contentStyle: { backgroundColor: theme.background },
        }}
      >
        <Stack.Screen name="index" options={{ headerShown: false }} />
        {/* V2.3A consumer closeout -- first-run onboarding sequence. Each
            screen renders its own back chevron (or none, for intro) rather
            than the native Stack header -- see app/onboarding/*.tsx. */}
        <Stack.Screen name="onboarding/intro" options={{ headerShown: false }} />
        <Stack.Screen name="onboarding/account" options={{ headerShown: false }} />
        <Stack.Screen name="onboarding/interests" options={{ headerShown: false }} />
        {/* headerShown:false -- ask.tsx renders its own SafeAreaView/topbar
            (mirroring index.tsx) so KeyboardAvoidingView fully owns and
            correctly measures its tree. Round 2 (real-device screenshots):
            relying on the native Stack header here was the likely cause of
            the keyboard covering the input -- KeyboardAvoidingView had no
            way to know that header's height. */}
        <Stack.Screen name="ask" options={{ headerShown: false }} />
        <Stack.Screen name="about" options={{ title: "About STRATUS" }} />
        {/* V2.3A -- reachable from index.tsx's menu regardless of whether
            Clerk is configured: shows "Continue as guest" info when it
            isn't, and the real sign-in/sign-out UI when it is. */}
        <Stack.Screen name="account" options={{ title: "Account" }} />
        {/* Developer/Diagnostics only -- reachable only via app/index.tsx's
            single __DEV__-gated "Developer / Diagnostics" menu row. */}
        <Stack.Screen name="dev-diagnostics" options={{ title: "Developer / Diagnostics" }} />
        <Stack.Screen
          name="atmosphere-preview"
          options={{ title: "Diagnostics: Atmosphere (Sprint 1)" }}
        />
        <Stack.Screen
          name="field-legacy"
          options={{ title: "Diagnostics: Opportunity Field (previous)" }}
        />
        <Stack.Screen name="classic" options={{ title: "Diagnostics: Classic Briefing" }} />
        <Stack.Screen name="memory" options={{ title: "Diagnostics: Memory Inbox" }} />
        <Stack.Screen name="demo" options={{ title: "Diagnostics: STRATUS Demo" }} />
      </Stack>
    </AuthProvider>
  );
}
