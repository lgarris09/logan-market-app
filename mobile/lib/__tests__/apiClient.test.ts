import { fetchJson } from "../apiClient";
import { getOrCreateDeviceId } from "../identity";

// Sprint 3.6.9: apiClient now attaches this install's identity to every
// request (see lib/identity.ts) -- mocked here at the module boundary
// rather than the underlying expo-secure-store/expo-crypto native modules,
// so these tests stay focused on fetchJson's own retry/timeout/abort
// behavior and don't depend on identity.ts's internals.
jest.mock("../identity", () => ({
  getOrCreateDeviceId: jest.fn().mockResolvedValue("test-device-id-1234"),
}));

// Mocks a fetch that respects its AbortSignal, the way the real one does --
// resolves/rejects immediately on demand, or hangs until aborted (simulating a
// slow/timed-out request) if `hang` is set.
function mockFetch(impl: (signal: AbortSignal) => Promise<Response> | { hang: true }) {
  global.fetch = jest.fn((_url: string, init?: RequestInit) => {
    const signal = init?.signal as AbortSignal;
    const result = impl(signal);
    if ("then" in result) return result;

    return new Promise<Response>((_resolve, reject) => {
      signal.addEventListener("abort", () => {
        const err = new Error("Aborted");
        err.name = "AbortError";
        reject(err);
      });
    });
  }) as unknown as typeof fetch;
}

function jsonResponse(body: unknown, ok = true, status = 200): Response {
  return {
    ok,
    status,
    json: async () => body,
  } as Response;
}

describe("fetchJson", () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("returns success with the parsed body on a 200", async () => {
    mockFetch(() => Promise.resolve(jsonResponse({ hello: "logan" })));

    const result = await fetchJson<{ hello: string }>("/v1/opportunities");

    expect(result).toEqual({ status: "success", data: { hello: "logan" } });
  });

  it("returns an error result for a non-ok response, without retrying", async () => {
    const fetchSpy = jest.fn(() => Promise.resolve(jsonResponse({}, false, 500)));
    global.fetch = fetchSpy as unknown as typeof fetch;

    const result = await fetchJson("/v1/opportunities", { retries: 0 });

    expect(result).toEqual({ status: "error", message: "Server returned 500" });
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it("retries the configured number of times before giving up", async () => {
    const fetchSpy = jest.fn(() => Promise.resolve(jsonResponse({}, false, 503)));
    global.fetch = fetchSpy as unknown as typeof fetch;

    const result = await fetchJson("/v1/opportunities", { retries: 2, retryDelayMs: 1 });

    expect(result).toEqual({ status: "error", message: "Server returned 503" });
    expect(fetchSpy).toHaveBeenCalledTimes(3); // 1 initial + 2 retries
  });

  it("succeeds on a retry after an earlier transient failure", async () => {
    let call = 0;
    global.fetch = jest.fn(() => {
      call += 1;
      if (call === 1) return Promise.resolve(jsonResponse({}, false, 503));
      return Promise.resolve(jsonResponse({ ok: true }));
    }) as unknown as typeof fetch;

    const result = await fetchJson<{ ok: boolean }>("/v1/opportunities", {
      retries: 2,
      retryDelayMs: 1,
    });

    expect(result).toEqual({ status: "success", data: { ok: true } });
  });

  it("returns a timeout result when the request exceeds timeoutMs", async () => {
    mockFetch(() => ({ hang: true }));

    const result = await fetchJson("/v1/opportunities", {
      timeoutMs: 10,
      retries: 0,
    });

    expect(result).toEqual({ status: "timeout" });
  });

  it("returns an aborted result, not a retry, when the caller's own signal fires", async () => {
    mockFetch(() => ({ hang: true }));
    const controller = new AbortController();

    const pending = fetchJson("/v1/opportunities", {
      signal: controller.signal,
      timeoutMs: 5000,
      retries: 3,
    });
    controller.abort();

    const result = await pending;

    expect(result).toEqual({ status: "aborted" });
  });

  it("returns aborted immediately if the caller's signal is already aborted", async () => {
    const fetchSpy = jest.fn();
    global.fetch = fetchSpy as unknown as typeof fetch;
    const controller = new AbortController();
    controller.abort();

    const result = await fetchJson("/v1/opportunities", { signal: controller.signal });

    expect(result).toEqual({ status: "aborted" });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("returns an error result for a generic network failure", async () => {
    global.fetch = jest.fn(() =>
      Promise.reject(new Error("Network request failed"))
    ) as unknown as typeof fetch;

    const result = await fetchJson("/v1/opportunities", { retries: 0 });

    expect(result).toEqual({ status: "error", message: "Network request failed" });
  });

  describe("identity propagation (Sprint 3.6.9)", () => {
    it("attaches X-Stratus-User-Id from getOrCreateDeviceId to every request", async () => {
      const fetchSpy = jest.fn((_url: string, _init?: RequestInit) =>
        Promise.resolve(jsonResponse({}))
      );
      global.fetch = fetchSpy as unknown as typeof fetch;

      await fetchJson("/v1/opportunities");

      const [, init] = fetchSpy.mock.calls[0];
      const headers = (init as RequestInit).headers as Record<string, string>;
      expect(headers["X-Stratus-User-Id"]).toBe("test-device-id-1234");
    });

    it("preserves caller-supplied headers alongside the identity header", async () => {
      const fetchSpy = jest.fn((_url: string, _init?: RequestInit) =>
        Promise.resolve(jsonResponse({}))
      );
      global.fetch = fetchSpy as unknown as typeof fetch;

      await fetchJson("/v1/notifications/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      const [, init] = fetchSpy.mock.calls[0];
      const headers = (init as RequestInit).headers as Record<string, string>;
      expect(headers["Content-Type"]).toBe("application/json");
      expect(headers["X-Stratus-User-Id"]).toBe("test-device-id-1234");
    });

    it("still makes the request, without the identity header, if identity resolution fails", async () => {
      (getOrCreateDeviceId as jest.Mock).mockRejectedValueOnce(
        new Error("SecureStore unavailable")
      );
      const fetchSpy = jest.fn((_url: string, _init?: RequestInit) =>
        Promise.resolve(jsonResponse({ ok: true }))
      );
      global.fetch = fetchSpy as unknown as typeof fetch;

      const result = await fetchJson<{ ok: boolean }>("/v1/opportunities");

      expect(result).toEqual({ status: "success", data: { ok: true } });
      const [, init] = fetchSpy.mock.calls[0];
      const headers = (init as RequestInit).headers as Record<string, string>;
      expect(headers["X-Stratus-User-Id"]).toBeUndefined();
    });
  });
});
