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
// Sprint 3.6.9 Block 1: EXPO_PUBLIC_APP_ENV (set per-profile in eas.json) decides
// which of two behaviors applies below. "development" (the default when unset,
// matching every pre-Block-1 local `expo start`) permits the LAN fallback --
// zero-config for a phone/simulator on the same network as the dev machine.
// "preview"/"production" do NOT: those builds must have a real, explicit,
// externally-reachable EXPO_PUBLIC_API_BASE_URL, or this module throws at load
// time rather than silently falling back to a LAN address that is guaranteed
// unreachable off the developer's network. See docs/DECISIONS.md's Sprint 3.6.9
// Block 1 ADR for the full reasoning -- this is a hard product invariant, not a
// style preference: a beta tester's build silently pointing at an unreachable
// address is indistinguishable from "the app is broken," with no diagnostic short
// of reading source code.
export const APP_ENV = (process.env.EXPO_PUBLIC_APP_ENV ?? "development").trim();

// Fallback: this machine's current local Wi-Fi IPv4 (via Get-NetIPAddress), for a
// zero-config `expo start` during local development. It will go stale the moment
// the network or DHCP lease changes -- that's expected; set the env var instead of
// editing this file once a real backend exists to point at. Only ever used when
// APP_ENV is "development" (or unset) -- see resolveApiBaseUrl below.
const DEV_FALLBACK_API_BASE_URL = "http://192.168.86.44:8000";

const RELEASE_APP_ENVS = new Set(["preview", "production"]);

// Private-network / loopback hostnames a real hosted backend can never be --
// RFC 1918 (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16), loopback, and
// "localhost" itself. Deliberately conservative (hostname-only, no CIDR math)
// -- this only needs to catch the shape of address this codebase's own dev
// fallback and `.env.example` already use, not serve as a general-purpose
// IP-classification utility.
const LAN_OR_LOCAL_HOSTNAME_PATTERN =
  /^(localhost|127\.\d+\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+|192\.168\.\d+\.\d+)$/i;

export function isLanOrLocalUrl(url: string): boolean {
  let hostname: string;
  try {
    hostname = new URL(url).hostname;
  } catch {
    // Not a parsable URL at all -- never treat that as a valid externally
    // reachable address either.
    return true;
  }
  return LAN_OR_LOCAL_HOSTNAME_PATTERN.test(hostname);
}

/**
 * Pure and unit-tested (see lib/__tests__/config.test.ts) precisely because
 * this enforces the one invariant Sprint 3.6.9 Block 1 was explicit about:
 * a preview/production build must never silently use a hardcoded private LAN
 * backend address. Throws (rather than falling back) for a release build
 * with a missing, LAN-shaped, or non-HTTPS API base URL -- a loud startup
 * crash with a readable message is the intended failure mode, not a request
 * that silently times out against an address the build could never reach.
 */
export function resolveApiBaseUrl(
  appEnv: string,
  configuredUrl: string | undefined
): string {
  const trimmed = (configuredUrl ?? "").trim();

  if (!RELEASE_APP_ENVS.has(appEnv)) {
    // Development (or any unrecognized value -- treated the same as
    // "development" rather than silently falling into the stricter release
    // path, since only eas.json's own "preview"/"production" profiles ever
    // set EXPO_PUBLIC_APP_ENV to those exact values): an explicit .env value
    // wins; otherwise the zero-config LAN fallback, exactly as before Block 1.
    return trimmed || DEV_FALLBACK_API_BASE_URL;
  }

  if (!trimmed) {
    throw new Error(
      `STRATUS misconfiguration: EXPO_PUBLIC_API_BASE_URL is not set for a "${appEnv}" ` +
        "build. A preview/production build must never silently fall back to a " +
        "development LAN address -- set EXPO_PUBLIC_API_BASE_URL in eas.json's " +
        `env block for the "${appEnv}" profile before building.`
    );
  }
  if (isLanOrLocalUrl(trimmed)) {
    throw new Error(
      `STRATUS misconfiguration: EXPO_PUBLIC_API_BASE_URL ("${trimmed}") looks like a ` +
        `private LAN/local address, which is unreachable outside the developer's own ` +
        `network. A "${appEnv}" build must point at a real, externally reachable HTTPS ` +
        "backend URL."
    );
  }
  if (!trimmed.toLowerCase().startsWith("https://")) {
    throw new Error(
      `STRATUS misconfiguration: EXPO_PUBLIC_API_BASE_URL ("${trimmed}") must use HTTPS ` +
        `for a "${appEnv}" build.`
    );
  }
  return trimmed;
}

export const API_BASE_URL = resolveApiBaseUrl(
  APP_ENV,
  process.env.EXPO_PUBLIC_API_BASE_URL
);
