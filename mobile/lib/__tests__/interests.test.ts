// V2.3A consumer closeout -- declared Quick Interests persistence. Same
// expo-secure-store mocking convention as lib/__tests__/identity.test.ts.
import * as SecureStore from "expo-secure-store";

import { getDeclaredInterests, saveDeclaredInterests } from "../interests";

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(),
}));

const mockGetItem = SecureStore.getItemAsync as jest.Mock;
const mockSetItem = SecureStore.setItemAsync as jest.Mock;

describe("declared interests", () => {
  beforeEach(() => {
    mockGetItem.mockReset();
    mockSetItem.mockReset();
  });

  it("returns null when the first-run interests step has never been completed", async () => {
    mockGetItem.mockResolvedValue(null);

    expect(await getDeclaredInterests()).toBeNull();
  });

  it("saves the selected categories with a timestamp", async () => {
    await saveDeclaredInterests(["markets", "trends_tech"]);

    expect(mockSetItem).toHaveBeenCalledTimes(1);
    const [key, value] = mockSetItem.mock.calls[0];
    expect(key).toBe("stratus_declared_interests_v1");
    const parsed = JSON.parse(value);
    expect(parsed.categories).toEqual(["markets", "trends_tech"]);
    expect(typeof parsed.selectedAt).toBe("string");
  });

  it("distinguishes a saved empty selection from never having completed the step", async () => {
    mockGetItem.mockResolvedValue(JSON.stringify({ categories: [], selectedAt: "2026-01-01T00:00:00.000Z" }));

    const result = await getDeclaredInterests();

    expect(result).not.toBeNull();
    expect(result?.categories).toEqual([]);
  });

  it("reads back previously-saved categories (simulated restart)", async () => {
    mockGetItem.mockResolvedValue(
      JSON.stringify({ categories: ["culture_media", "other"], selectedAt: "2026-01-01T00:00:00.000Z" })
    );

    const result = await getDeclaredInterests();

    expect(result?.categories).toEqual(["culture_media", "other"]);
  });

  it("treats malformed stored data as never-completed rather than throwing", async () => {
    mockGetItem.mockResolvedValue("not valid json");

    expect(await getDeclaredInterests()).toBeNull();
  });
});
