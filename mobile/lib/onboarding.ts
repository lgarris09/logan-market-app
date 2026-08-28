// V2.3A consumer closeout -- first-run onboarding completion flag.
//
// Device-scoped (not account-scoped), same SecureStore-backed pattern as
// lib/identity.ts's device id: "has this device finished the intro/account/
// interests sequence" is a fact about the install, not about which account
// (if any) ends up authenticated on it. This deliberately means a device
// that already completed onboarding anonymously and later signs in never
// sees the sequence again -- there is exactly one first-run experience per
// install, matching the product requirement that returning users are never
// forced through it a second time.
import * as SecureStore from "expo-secure-store";

const ONBOARDING_COMPLETE_KEY = "stratus_onboarding_complete_v1";

let cachedComplete: boolean | null = null;

/**
 * Whether this device has already finished first-run onboarding. Cached in
 * memory after the first real read so repeated checks (e.g. every cold
 * start) don't re-hit SecureStore.
 */
export async function hasCompletedOnboarding(): Promise<boolean> {
  if (cachedComplete !== null) {
    return cachedComplete;
  }
  const value = await SecureStore.getItemAsync(ONBOARDING_COMPLETE_KEY);
  cachedComplete = value === "true";
  return cachedComplete;
}

/**
 * Marks this device as having finished first-run onboarding -- called once,
 * at the end of the interests step (whether the user signed in, signed up,
 * or continued as a guest).
 */
export async function markOnboardingComplete(): Promise<void> {
  cachedComplete = true;
  await SecureStore.setItemAsync(ONBOARDING_COMPLETE_KEY, "true");
}

/**
 * Test-only reset hook -- see lib/identity.ts's identical convention.
 * Never called from application code.
 */
export function _resetOnboardingCacheForTests(): void {
  cachedComplete = null;
}
