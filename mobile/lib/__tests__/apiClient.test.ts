import { fetchJson } from "../apiClient";

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
});
