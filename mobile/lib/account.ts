// V2.3A -- Identity & Account Foundation. The mobile-side entry point into
// POST /v1/account/link and DELETE /v1/account (see backend/app/main.py).
import { fetchJson } from "./apiClient";
import { getOrCreateDeviceId } from "./identity";

export type LinkAccountResult = {
  stratusUserId: string;
  upgradedExistingIdentity: boolean;
};

/**
 * Must be called immediately after a first successful Clerk sign-in --
 * before any other authenticated request -- so this device's existing
 * anonymous history has a chance to become the new account's canonical
 * identity rather than being silently orphaned by auto-provisioning (see
 * docs/DECISIONS.md's ADR-069 for the full ordering requirement).
 */
export async function linkAnonymousIdentityToAccount(): Promise<LinkAccountResult | null> {
  const anonymousUserId = await getOrCreateDeviceId();
  const result = await fetchJson<{
    stratus_user_id: string;
    upgraded_existing_identity: boolean;
  }>("/v1/account/link", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ anonymous_user_id: anonymousUserId }),
    retries: 0,
  });
  if (result.status !== "success") {
    return null;
  }
  return {
    stratusUserId: result.data.stratus_user_id,
    upgradedExistingIdentity: result.data.upgraded_existing_identity,
  };
}

/**
 * Purges every piece of the caller's own user-scoped state on the backend
 * (see backend/app/account_lifecycle.py's purge_user_data). Works for both
 * anonymous and authenticated identities -- whichever this device currently
 * resolves to.
 */
export async function deleteAccount(): Promise<boolean> {
  const result = await fetchJson<{ deleted: boolean }>("/v1/account", {
    method: "DELETE",
    retries: 0,
  });
  return result.status === "success" && result.data.deleted === true;
}
