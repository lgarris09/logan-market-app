// API connectivity is environment-based (V3.1.4 BATCH-4), not a single hardcoded
// LAN IP baked into the bundle. Set EXPO_PUBLIC_API_BASE_URL in a local `.env` file
// (see `.env.example`) or as an EAS build-profile env var (see `eas.json`) to point
// at whatever backend the current build should talk to.
//
// EXPO_PUBLIC_-prefixed vars are inlined at build time by Expo SDK 54's Metro
// config -- no extra plugin or expo-constants wiring needed. This works the same
// way in Expo Go, an EAS development-client build, and a future TestFlight/
// production build; only the value differs per environment.
//
// Fallback: this machine's current local Wi-Fi IPv4 (via Get-NetIPAddress), for a
// zero-config `expo start` during local development. It will go stale the moment
// the network or DHCP lease changes -- that's expected; set the env var instead of
// editing this file once a real backend exists to point at.
const DEV_FALLBACK_API_BASE_URL = "http://192.168.86.44:8000";

export const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL ?? DEV_FALLBACK_API_BASE_URL;
