// V2.3A -- Identity & Account Foundation. Closes a real ordering race found
// during the overnight identity re-audit: `app/index.tsx`'s background
// 60-second opportunities poll stays mounted underneath `/account` in Expo
// Router's stack, so it keeps running while a user completes sign-in there.
// Once `activate()`/`signIn.finalize()` establishes a real Clerk session,
// there is a real (if narrow -- one request's duration out of a 60s
// interval) window before `POST /v1/account/link` sends, during which any
// OTHER authenticated request (that background poll included) would carry
// the same new Bearer token and hit `resolve_user_id()`'s auto-provisioning
// path first -- silently consuming the "first link" opportunity and
// orphaning this device's existing anonymous history under a fresh,
// separate account id (see docs/DECISIONS.md's ADR-069 ordering
// requirement).
//
// This is a plain in-memory synchronization gate, not a second identity
// system: `apiClient.ts`'s `fetchJson()` awaits `waitForPendingLink()`
// before sending *any* request whenever a link is in flight, guaranteeing
// `/v1/account/link` is always the first authenticated request to actually
// reach the network after a new session is established -- as long as
// `registerPendingLink()` is called synchronously (no `await` in between)
// immediately after the session is created, which `app/account.tsx` does.
let pendingLink: Promise<unknown> | null = null;

/**
 * Must be called synchronously (no `await` between session activation and
 * this call) so no other macrotask (a `setInterval` tick, in particular)
 * can run a request in the gap. The gate clears itself once `promise`
 * settles, success or failure -- a failed link must never wedge every
 * future request behind a permanently-pending gate.
 */
export function registerPendingLink(promise: Promise<unknown>): void {
  const settled = promise.catch(() => undefined);
  pendingLink = settled;
  settled.finally(() => {
    if (pendingLink === settled) {
      pendingLink = null;
    }
  });
}

/**
 * Resolves immediately when no link is in flight; otherwise waits for the
 * currently-registered link to settle (never rejects, regardless of
 * whether the link itself succeeded -- a failed link must not block
 * ordinary requests forever, it just means this device stays on its
 * current identity, exactly as if `/link` had never been called).
 */
export async function waitForPendingLink(): Promise<void> {
  if (pendingLink) {
    await pendingLink;
  }
}
