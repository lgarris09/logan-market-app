describe("getClerkSessionToken", () => {
  afterEach(() => {
    jest.resetModules();
    delete process.env.EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY;
  });

  it("returns null without ever touching @clerk/expo when unconfigured", async () => {
    delete process.env.EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY;
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { getClerkSessionToken } = require("../clerkClient");

    const token = await getClerkSessionToken();

    expect(token).toBeNull();
  });

  it("returns the session token from the Clerk singleton when configured", async () => {
    process.env.EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY = "pk_test_fake";
    jest.doMock("@clerk/expo", () => ({
      getClerkInstance: () => ({
        session: { getToken: async () => "a-real-looking-jwt" },
      }),
    }));

    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { getClerkSessionToken } = require("../clerkClient");
    const token = await getClerkSessionToken();

    expect(token).toBe("a-real-looking-jwt");
  });

  it("returns null (never throws) if the Clerk singleton throws", async () => {
    process.env.EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY = "pk_test_fake";
    jest.doMock("@clerk/expo", () => ({
      getClerkInstance: () => {
        throw new Error("not initialized yet");
      },
    }));

    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { getClerkSessionToken } = require("../clerkClient");
    const token = await getClerkSessionToken();

    expect(token).toBeNull();
  });
});
