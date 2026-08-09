import { useEffect } from "react";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import * as SplashScreen from "expo-splash-screen";
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

  useEffect(() => {
    if (fontsLoaded || fontError) SplashScreen.hideAsync().catch(() => {});
  }, [fontsLoaded, fontError]);

  // Falls through to the system font (never a blank screen) if font loading
  // genuinely fails on-device rather than blocking the app forever.
  if (!fontsLoaded && !fontError) return null;

  return (
    <>
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
        {/* headerShown:false -- ask.tsx renders its own SafeAreaView/topbar
            (mirroring index.tsx) so KeyboardAvoidingView fully owns and
            correctly measures its tree. Round 2 (real-device screenshots):
            relying on the native Stack header here was the likely cause of
            the keyboard covering the input -- KeyboardAvoidingView had no
            way to know that header's height. */}
        <Stack.Screen name="ask" options={{ headerShown: false }} />
        <Stack.Screen name="about" options={{ title: "About STRATUS" }} />
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
    </>
  );
}
