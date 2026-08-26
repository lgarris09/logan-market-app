// V2.3A -- Identity & Account Foundation. `apiClient.ts` is a plain
// function module, not a React component -- it can't call `useAuth()`
// directly. Clerk's own documented pattern for this exact situation is
// `getClerkInstance()`, which returns the same singleton `<ClerkProvider>`
// initializes, accessible from anywhere: see
// https://clerk.com/docs (Expo quickstart, "outside of React" section).
import { getClerkInstance } from "@clerk/expo";

import { CLERK_PUBLISHABLE_KEY, isClerkConfigured } from "./clerkConfig";

/**
 * The current Clerk session's JWT, or `null` when authentication isn't
 * configured for this build, no session exists yet, or the user is signed
 * out. Never throws -- a failure here should degrade to "send this request
 * anonymously," never break the request entirely (see apiClient.ts's own
 * identical discipline for the anonymous device-id header).
 */
export async function getClerkSessionToken(): Promise<string | null> {
  if (!isClerkConfigured()) {
    return null;
  }
  try {
    const clerk = getClerkInstance({ publishableKey: CLERK_PUBLISHABLE_KEY });
    const token = await clerk.session?.getToken();
    return token ?? null;
  } catch {
    return null;
  }
}
