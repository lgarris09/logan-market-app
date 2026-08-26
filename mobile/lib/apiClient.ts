// Centralized fetch for every backend call (V3.1.4 BATCH-5). Before this, each
// screen called `fetch()` directly with no timeout, no retry, and no way to cancel
// an in-flight request when the screen unmounted or the user navigated away mid-
// request -- this is the single place that behavior lives now.
//
// Sprint 3.6.9: also the single, centralized place this install's persistent
// identity (see lib/identity.ts) gets attached to every request, via the
// X-Stratus-User-Id header -- one change point rather than threading it
// through each of the many individual call sites across the app.
//
// V2.3A: also attaches a real Clerk session token (Authorization: Bearer)
// when one exists, alongside -- never instead of -- the anonymous
// X-Stratus-User-Id header. The backend's own resolve_user_id() always
// prefers a verified Bearer token when present; sending both here is what
// lets /v1/account/link (called separately, right after sign-in) still see
// this same anonymous device id on every other concurrent request.
//
// Also awaits authLinkGate's waitForPendingLink() before sending anything --
// closes a real ordering race found in the V2.3A overnight audit: a
// background poll (app/index.tsx) can otherwise reach the backend with a
// brand-new Bearer token before app/account.tsx's own POST /v1/account/link
// call does, silently orphaning this device's anonymous history via
// resolve_user_id()'s auto-provisioning path instead of carrying it forward.
// A no-op whenever no link is currently in flight (the overwhelmingly
// common case).
import { API_BASE_URL } from "../constants/config";
import { waitForPendingLink } from "./authLinkGate";
import { getClerkSessionToken } from "./clerkClient";
import { getOrCreateDeviceId } from "./identity";

const DEFAULT_TIMEOUT_MS = 10000;
const DEFAULT_RETRIES = 2;
const DEFAULT_RETRY_DELAY_MS = 600;

export type ApiResult<T> =
  | { status: "success"; data: T }
  | { status: "error"; message: string }
  | { status: "timeout" }
  | { status: "aborted" };

export type FetchJsonOptions = RequestInit & {
  /** Caller-owned signal (e.g. from a screen's cleanup effect) -- aborting this
   * cancels the request immediately and is never retried, unlike a timeout or a
   * transient network error. */
  signal?: AbortSignal;
  timeoutMs?: number;
  /** Number of retry attempts after the first try. 0 disables retry entirely --
   * used for non-idempotent requests (POST) where re-sending on failure could
   * duplicate a side effect. */
  retries?: number;
  retryDelayMs?: number;
};

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// V2.3A: POST /v1/account/link is itself sent through fetchJson -- it must
// never await its own in-flight gate (that would deadlock: the gate only
// clears once this exact request settles). Every other request waits.
const ACCOUNT_LINK_PATH = "/v1/account/link";

/**
 * Fetches JSON from a `${API_BASE_URL}${path}` endpoint with a timeout, bounded
 * retry on transient failure, and cooperative cancellation. Never throws --
 * every outcome (success, server error, timeout, network failure, caller-
 * initiated abort) is a value in the returned `ApiResult`, so callers can render
 * every state explicitly instead of a bare try/catch around raw `fetch`.
 */
export async function fetchJson<T>(
  path: string,
  options: FetchJsonOptions = {}
): Promise<ApiResult<T>> {
  const {
    signal: callerSignal,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    retries = DEFAULT_RETRIES,
    retryDelayMs = DEFAULT_RETRY_DELAY_MS,
    ...fetchOptions
  } = options;

  if (path !== ACCOUNT_LINK_PATH) {
    await waitForPendingLink();
  }

  // Sprint 3.6.9: never blocks the request if identity storage is
  // unavailable (rare) -- proceeds without the header, and the backend's
  // own resolve_user_id() has a safe mode-aware fallback either way (see
  // backend/app/user_context.py).
  let deviceId: string | null = null;
  try {
    deviceId = await getOrCreateDeviceId();
  } catch {
    deviceId = null;
  }
  // V2.3A: never blocks the request if Clerk isn't configured/loaded/signed
  // in -- getClerkSessionToken() itself never throws, returning null for
  // every one of those cases, so this degrades to the exact pre-V2.3A
  // anonymous-only request shape.
  const sessionToken = await getClerkSessionToken();
  const identityHeaders: Record<string, string> = {
    ...(deviceId ? { "X-Stratus-User-Id": deviceId } : {}),
    ...(sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {}),
  };

  for (let attempt = 0; attempt <= retries; attempt++) {
    if (callerSignal?.aborted) {
      return { status: "aborted" };
    }

    const timeoutController = new AbortController();
    const timer = setTimeout(() => timeoutController.abort(), timeoutMs);
    const onCallerAbort = () => timeoutController.abort();
    callerSignal?.addEventListener("abort", onCallerAbort);

    try {
      const response = await fetch(`${API_BASE_URL}${path}`, {
        ...fetchOptions,
        headers: {
          ...fetchOptions.headers,
          ...identityHeaders,
        },
        signal: timeoutController.signal,
      });

      if (!response.ok) {
        const message = `Server returned ${response.status}`;
        if (attempt < retries) {
          await sleep(retryDelayMs);
          continue;
        }
        return { status: "error", message };
      }

      const data = (await response.json()) as T;
      return { status: "success", data };
    } catch (error) {
      if (callerSignal?.aborted) {
        return { status: "aborted" };
      }
      const isAbort = error instanceof Error && error.name === "AbortError";
      if (isAbort) {
        // The timeout controller fired, not the caller -- this was a timeout,
        // not a cancellation. Retry like any other transient failure.
        if (attempt < retries) {
          await sleep(retryDelayMs);
          continue;
        }
        return { status: "timeout" };
      }
      if (attempt < retries) {
        await sleep(retryDelayMs);
        continue;
      }
      return {
        status: "error",
        message: error instanceof Error ? error.message : "Unable to reach STRATUS.",
      };
    } finally {
      clearTimeout(timer);
      callerSignal?.removeEventListener("abort", onCallerAbort);
    }
  }

  // Unreachable (the loop always returns), but keeps the function's return type
  // total rather than implicitly `undefined` for TypeScript's control-flow analysis.
  return { status: "error", message: "Unable to reach STRATUS." };
}
