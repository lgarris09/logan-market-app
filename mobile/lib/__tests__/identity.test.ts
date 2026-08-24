// Sprint 3.6.9 -- Persistent Mobile Identity. Mocks expo-secure-store and
// expo-crypto directly (not through apiClient) so these tests exercise
// getOrCreateDeviceId()'s own generate-once/persist/reuse contract in
// isolation.
import * as Crypto from "expo-crypto";
import * as SecureStore from "expo-secure-store";

import { _resetDeviceIdCacheForTests, getOrCreateDeviceId } from "../identity";

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(),
}));

jest.mock("expo-crypto", () => ({
  randomUUID: jest.fn(),
}));

const mockGetItem = SecureStore.getItemAsync as jest.Mock;
const mockSetItem = SecureStore.setItemAsync as jest.Mock;
const mockRandomUUID = Crypto.randomUUID as jest.Mock;

describe("getOrCreateDeviceId", () => {
  beforeEach(() => {
    _resetDeviceIdCacheForTests();
    mockGetItem.mockReset();
    mockSetItem.mockReset();
    mockRandomUUID.mockReset();
  });

  it("generates and persists a new id on first use when none is stored", async () => {
    mockGetItem.mockResolvedValue(null);
    mockRandomUUID.mockReturnValue("11111111-1111-1111-1111-111111111111");

    const id = await getOrCreateDeviceId();

    expect(id).toBe("11111111-1111-1111-1111-111111111111");
    expect(mockSetItem).toHaveBeenCalledWith(
      "stratus_device_id",
      "11111111-1111-1111-1111-111111111111"
    );
  });

  it("reuses an already-persisted id instead of generating a new one", async () => {
    mockGetItem.mockResolvedValue("22222222-2222-2222-2222-222222222222");

    const id = await getOrCreateDeviceId();

    expect(id).toBe("22222222-2222-2222-2222-222222222222");
    expect(mockRandomUUID).not.toHaveBeenCalled();
    expect(mockSetItem).not.toHaveBeenCalled();
  });

  it("only reads/writes SecureStore once across repeated calls in the same process", async () => {
    mockGetItem.mockResolvedValue(null);
    mockRandomUUID.mockReturnValue("33333333-3333-3333-3333-333333333333");

    const first = await getOrCreateDeviceId();
    const second = await getOrCreateDeviceId();
    const third = await getOrCreateDeviceId();

    expect(first).toBe(second);
    expect(second).toBe(third);
    expect(mockGetItem).toHaveBeenCalledTimes(1);
    expect(mockSetItem).toHaveBeenCalledTimes(1);
  });

  it("a fresh install (cache reset, nothing stored) generates a new id independently", async () => {
    mockGetItem.mockResolvedValue(null);
    mockRandomUUID.mockReturnValue("44444444-4444-4444-4444-444444444444");
    const first = await getOrCreateDeviceId();

    _resetDeviceIdCacheForTests();
    mockGetItem.mockResolvedValue(null);
    mockRandomUUID.mockReturnValue("55555555-5555-5555-5555-555555555555");
    const second = await getOrCreateDeviceId();

    expect(first).toBe("44444444-4444-4444-4444-444444444444");
    expect(second).toBe("55555555-5555-5555-5555-555555555555");
  });
});
