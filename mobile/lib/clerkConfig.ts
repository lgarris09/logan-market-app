// V2.3A -- Identity & Account Foundation. Authentication is entirely
// optional at build/runtime: EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY is unset in
// every environment until the owner creates a real Clerk project and
// supplies it (see docs/DECISIONS.md's ADR-069) -- mirroring this
// codebase's existing STRATUS_LLM_ASK/ANTHROPIC_API_KEY rollout pattern.
// When unset, `isClerkConfigured()` is false everywhere, `_layout.tsx`
// never mounts `<ClerkProvider>`, and the app behaves byte-for-byte like
// every pre-V2.3A build: anonymous-only, no sign-in UI rendered at all.
//
// 2026-08-27: a real Clerk *test-mode* instance (pk_test_...) was activated
// for on-device V2.3A validation -- set in mobile/.env (local dev, real
// value, gitignored) and eas.json's "preview" build profile only.
// Deliberately still unset in eas.json's "production" profile: pk_test_ is
// not a production credential, and setting one there is its own separate
// owner decision (creating a real Clerk *production* instance, receiving a
// pk_live_... key) -- not something to default into quietly while wiring
// up device validation.
export const CLERK_PUBLISHABLE_KEY: string | undefined =
  process.env.EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY;

export function isClerkConfigured(): boolean {
  return Boolean(CLERK_PUBLISHABLE_KEY && CLERK_PUBLISHABLE_KEY.trim());
}
