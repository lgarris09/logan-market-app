// Centralized fetch for every backend call (V3.1.4 BATCH-5). Before this, each
// screen called `fetch()` directly with no timeout, no retry, and no way to cancel
// an in-flight request when the screen unmounted or the user navigated away mid-
// request -- this is the single place that behavior lives now.
import { API_BASE_URL } from "../constants/config";

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
