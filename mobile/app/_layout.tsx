import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";

import { theme } from "../constants/theme";

export default function RootLayout() {
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
        <Stack.Screen name="ask" options={{ title: "Ask Logan" }} />
        <Stack.Screen name="memory" options={{ title: "Memory" }} />
        <Stack.Screen name="demo" options={{ title: "Logan Demo" }} />
      </Stack>
    </>
  );
}
