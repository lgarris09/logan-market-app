// Sprint 3.6.9 Block 1: the mobile-side half of the "a preview/production
// STRATUS build must never silently use a hardcoded private LAN backend
// address" invariant (see docs/DECISIONS.md's Sprint 3.6.9 Block 1 ADR).
// Tests the pure resolveApiBaseUrl/isLanOrLocalUrl functions directly rather
// than reimporting constants/config.ts with different process.env values --
// EXPO_PUBLIC_-prefixed vars are inlined at build time, so re-mocking
// process.env after module load would not reflect how this actually behaves
// in a real build anyway.
import { isLanOrLocalUrl, resolveApiBaseUrl } from "../../constants/config";

describe("isLanOrLocalUrl", () => {
  test.each([
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://192.168.1.100:8000",
    "http://192.168.86.44:8000",
    "http://10.0.0.5:8000",
    "http://172.16.0.1:8000",
    "http://172.31.255.255:8000",
  ])("flags %s as LAN/local", (url) => {
    expect(isLanOrLocalUrl(url)).toBe(true);
  });

  test.each([
    "https://stratus-api.fly.dev",
    "https://api.example.com",
    "http://203.0.113.5:8000", // public IP, not RFC 1918
    "https://172.32.0.1", // just outside the 172.16/12 private block
  ])("does not flag %s as LAN/local", (url) => {
    expect(isLanOrLocalUrl(url)).toBe(false);
  });

  test("an unparsable value is treated as unsafe (LAN/local)", () => {
    expect(isLanOrLocalUrl("not a url")).toBe(true);
  });
});

describe("resolveApiBaseUrl", () => {
  describe("development (and unrecognized) app envs", () => {
    test("uses an explicit configured URL when set", () => {
      expect(resolveApiBaseUrl("development", "http://192.168.1.50:8000")).toBe(
        "http://192.168.1.50:8000"
      );
    });

    test("falls back to the LAN dev default when unset", () => {
      expect(resolveApiBaseUrl("development", undefined)).toBe(
        "http://192.168.86.44:8000"
      );
    });

    test("falls back to the LAN dev default for an unrecognized app env", () => {
      expect(resolveApiBaseUrl("staging", undefined)).toBe(
        "http://192.168.86.44:8000"
      );
    });
  });

  describe.each(["preview", "production"])("%s app env", (appEnv) => {
    test("throws when EXPO_PUBLIC_API_BASE_URL is unset", () => {
      expect(() => resolveApiBaseUrl(appEnv, undefined)).toThrow(
        /EXPO_PUBLIC_API_BASE_URL is not set/
      );
    });

    test("throws when EXPO_PUBLIC_API_BASE_URL is blank", () => {
      expect(() => resolveApiBaseUrl(appEnv, "   ")).toThrow(
        /EXPO_PUBLIC_API_BASE_URL is not set/
      );
    });

    test("throws for a LAN-shaped address rather than silently using it", () => {
      expect(() =>
        resolveApiBaseUrl(appEnv, "http://192.168.86.44:8000")
      ).toThrow(/private LAN\/local address/);
    });

    test("throws for a non-HTTPS externally reachable address", () => {
      expect(() => resolveApiBaseUrl(appEnv, "http://api.example.com")).toThrow(
        /must use HTTPS/
      );
    });

    test("accepts a real HTTPS externally reachable address", () => {
      expect(resolveApiBaseUrl(appEnv, "https://stratus-api.fly.dev")).toBe(
        "https://stratus-api.fly.dev"
      );
    });
  });
});

// Sprint 3.6.9 Remote STRATUS mobile closeout: eas.json's own preview/production
// EXPO_PUBLIC_API_BASE_URL values (now the real, deployed https://stratus-api.fly.dev)
// must themselves pass this validation -- read directly from the committed file so a
// future accidental edit reintroducing a LAN/local URL there is caught here, not just
// discovered by a build silently failing.
describe("eas.json's configured release API URLs", () => {
  const easConfig = require("../../eas.json");

  test.each(["preview", "production"])("%s profile's URL resolves without throwing", (profile) => {
    const env = easConfig.build[profile].env;
    expect(() => resolveApiBaseUrl(env.EXPO_PUBLIC_APP_ENV, env.EXPO_PUBLIC_API_BASE_URL)).not.toThrow();
    expect(isLanOrLocalUrl(env.EXPO_PUBLIC_API_BASE_URL)).toBe(false);
  });
});
