// V2.3A -- Identity & Account Foundation. Authentication is entirely
// optional at build/runtime: EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY is unset in
// every environment until the owner creates a real Clerk project and
// supplies it (see docs/DECISIONS.md's ADR-069) -- mirroring this
// codebase's existing STRATUS_LLM_ASK/ANTHROPIC_API_KEY rollout pattern.
// When unset, `isClerkConfigured()` is false everywhere, `_layout.tsx`
// never mounts `<ClerkProvider>`, and the app behaves byte-for-byte like
// every pre-V2.3A build: anonymous-only, no sign-in UI rendered at all.
export const CLERK_PUBLISHABLE_KEY: string | undefined =
  process.env.EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY;

export function isClerkConfigured(): boolean {
  return Boolean(CLERK_PUBLISHABLE_KEY && CLERK_PUBLISHABLE_KEY.trim());
}
