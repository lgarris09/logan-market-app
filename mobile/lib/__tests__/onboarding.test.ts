// V2.3A consumer closeout -- same expo-secure-store mocking convention as
// lib/__tests__/identity.test.ts, exercising the onboarding-completion
// flag's own generate-once/cache/fail-safe contract in isolation.
import * as SecureStore from "expo-secure-store";

import {
  _resetOnboardingCacheForTests,
  hasCompletedOnboarding,
  markOnboardingComplete,
} from "../onboarding";

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(),
}));

const mockGetItem = SecureStore.getItemAsync as jest.Mock;
const mockSetItem = SecureStore.setItemAsync as jest.Mock;

describe("onboarding completion flag", () => {
  beforeEach(() => {
    _resetOnboardingCacheForTests();
    mockGetItem.mockReset();
    mockSetItem.mockReset();
  });

  it("reports incomplete when nothing is stored yet (fresh install)", async () => {
    mockGetItem.mockResolvedValue(null);

    expect(await hasCompletedOnboarding()).toBe(false);
  });

  it("reports complete once markOnboardingComplete() has been called", async () => {
    mockGetItem.mockResolvedValue(null);
    await markOnboardingComplete();

    expect(mockSetItem).toHaveBeenCalledWith("stratus_onboarding_complete_v1", "true");
    expect(await hasCompletedOnboarding()).toBe(true);
  });

  it("reads a previously-persisted completion across a fresh cache (simulated restart)", async () => {
    mockGetItem.mockResolvedValue("true");

    expect(await hasCompletedOnboarding()).toBe(true);
  });

  it("only reads SecureStore once across repeated calls in the same process", async () => {
    mockGetItem.mockResolvedValue("true");

    await hasCompletedOnboarding();
    await hasCompletedOnboarding();
    await hasCompletedOnboarding();

    expect(mockGetItem).toHaveBeenCalledTimes(1);
  });

  it("a fresh install (cache reset) re-checks SecureStore independently", async () => {
    mockGetItem.mockResolvedValue("true");
    expect(await hasCompletedOnboarding()).toBe(true);

    _resetOnboardingCacheForTests();
    mockGetItem.mockResolvedValue(null);
    expect(await hasCompletedOnboarding()).toBe(false);
  });
});
