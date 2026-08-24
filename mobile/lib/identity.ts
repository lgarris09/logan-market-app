// Sprint 3.6.9 -- Persistent Mobile Identity + Beta Security Boundary.
//
// Before this, the mobile app sent no X-Stratus-User-Id header at all on
// any request -- every caller silently resolved to the backend's founder
// default (backend/app/user_context.py's resolve_user_id()), which was
// harmless on a local-only backend nobody else could reach, but became a
// real information-disclosure exposure the moment the backend was hosted
// publicly (see docs/DECISIONS.md's Sprint 3.6.9 Mobile Identity + Beta
// Security ADR for the full reasoning, including the companion backend fix
// that stops honoring the founder constant from an unauthenticated client
// at all in beta/production mode).
//
// This is real per-install IDENTITY, not authentication: a stable, random,
// non-guessable UUID generated once and persisted in the platform keychain
// (expo-secure-store -- iOS Keychain / Android Keystore-backed encrypted
// storage), so the same install keeps the same identity across app
// restarts. Nothing verifies this value actually belongs to a specific
// person -- it only gives the backend a stable identifier to scope this
// install's own data to, which is the entire point: without it, the
// backend had no real caller identity to scope anything to at all.
import * as Crypto from "expo-crypto";
import * as SecureStore from "expo-secure-store";

const DEVICE_ID_STORAGE_KEY = "stratus_device_id";

let cachedDeviceId: string | null = null;

/**
 * Returns this install's stable identifier, generating and persisting one
 * on first call if none exists yet. Cached in memory after the first real
 * read/write so every subsequent call in the same process resolves without
 * touching SecureStore again.
 */
export async function getOrCreateDeviceId(): Promise<string> {
  if (cachedDeviceId) {
    return cachedDeviceId;
  }

  const existing = await SecureStore.getItemAsync(DEVICE_ID_STORAGE_KEY);
  if (existing) {
    cachedDeviceId = existing;
    return existing;
  }

  const generated = Crypto.randomUUID();
  await SecureStore.setItemAsync(DEVICE_ID_STORAGE_KEY, generated);
  cachedDeviceId = generated;
  return generated;
}

/**
 * Test-only reset hook -- clears the in-memory cache so a test can exercise
 * a "fresh install" scenario without real state carrying over between test
 * cases. Never called from application code.
 */
export function _resetDeviceIdCacheForTests(): void {
  cachedDeviceId = null;
}
