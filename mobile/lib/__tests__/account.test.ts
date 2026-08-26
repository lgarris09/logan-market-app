import { deleteAccount, linkAnonymousIdentityToAccount } from "../account";
import { fetchJson } from "../apiClient";

jest.mock("../apiClient", () => ({
  fetchJson: jest.fn(),
}));

jest.mock("../identity", () => ({
  getOrCreateDeviceId: jest.fn().mockResolvedValue("anon-device-xyz"),
}));

describe("linkAnonymousIdentityToAccount", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it("posts the current anonymous device id and returns the parsed result", async () => {
    (fetchJson as jest.Mock).mockResolvedValueOnce({
      status: "success",
      data: { stratus_user_id: "anon-device-xyz", upgraded_existing_identity: true },
    });

    const result = await linkAnonymousIdentityToAccount();

    expect(fetchJson).toHaveBeenCalledWith(
      "/v1/account/link",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ anonymous_user_id: "anon-device-xyz" }),
      })
    );
    expect(result).toEqual({
      stratusUserId: "anon-device-xyz",
      upgradedExistingIdentity: true,
    });
  });

  it("returns null when the backend call fails", async () => {
    (fetchJson as jest.Mock).mockResolvedValueOnce({ status: "error", message: "boom" });

    const result = await linkAnonymousIdentityToAccount();

    expect(result).toBeNull();
  });
});

describe("deleteAccount", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it("returns true when the backend confirms deletion", async () => {
    (fetchJson as jest.Mock).mockResolvedValueOnce({
      status: "success",
      data: { deleted: true },
    });

    const result = await deleteAccount();

    expect(fetchJson).toHaveBeenCalledWith("/v1/account", expect.objectContaining({ method: "DELETE" }));
    expect(result).toBe(true);
  });

  it("returns false when the backend call fails", async () => {
    (fetchJson as jest.Mock).mockResolvedValueOnce({ status: "error", message: "boom" });

    const result = await deleteAccount();

    expect(result).toBe(false);
  });
});
