import { fireEvent, render, screen, waitFor } from "@testing-library/react-native";

import AccountScreen, { signInMethodLabel } from "../account";

// Same @expo/vector-icons mocking convention as app/__tests__/index.test.tsx.
jest.mock("@expo/vector-icons", () => {
  const { Text } = jest.requireActual("react-native");
  return { Ionicons: (props: { name: string }) => <Text>{`icon:${props.name}`}</Text> };
});

jest.mock("expo-web-browser", () => ({ maybeCompleteAuthSession: jest.fn() }));

jest.mock("../../lib/clerkConfig", () => ({
  isClerkConfigured: () => true,
  CLERK_PUBLISHABLE_KEY: "pk_test_fake",
}));

jest.mock("../../lib/interests", () => {
  const actual = jest.requireActual("../../lib/interests");
  return {
    ...actual,
    getDeclaredInterests: jest.fn().mockResolvedValue(null),
    saveDeclaredInterests: jest.fn().mockResolvedValue(undefined),
  };
});

jest.mock("expo-notifications", () => ({
  PermissionStatus: { GRANTED: "granted", DENIED: "denied", UNDETERMINED: "undetermined" },
  getPermissionsAsync: jest.fn().mockResolvedValue({ status: "granted" }),
}));

const mockSignOut = jest.fn().mockResolvedValue(undefined);

// V2.3A -- Identity & Account Foundation: this test exercises the signed-in
// branch specifically (AccountAndSettings), unlike the global
// __mocks__/@clerk/expo.js manual mock (which hardcodes isSignedIn: false
// so every *other* test's import of @clerk/expo stays a safe no-op) --
// an explicit jest.mock() here overrides that default for this file only.
jest.mock("@clerk/expo", () => ({
  useAuth: () => ({ isLoaded: true, isSignedIn: true, signOut: mockSignOut }),
  useUser: () => ({
    user: {
      fullName: "Ada Lovelace",
      firstName: "Ada",
      lastName: "Lovelace",
      hasImage: false,
      imageUrl: "",
      primaryEmailAddress: { emailAddress: "ada@example.com" },
      externalAccounts: [],
    },
  }),
}));

describe("AccountScreen (signed in)", () => {
  beforeEach(() => {
    mockSignOut.mockClear();
  });

  it("shows the signed-in profile with the real identifier and sign-in method", async () => {
    render(<AccountScreen />);

    await waitFor(() => expect(screen.getByText("ada@example.com")).toBeTruthy());
    expect(screen.getByText("Ada Lovelace")).toBeTruthy();
    expect(screen.getByText("Signed in with Email")).toBeTruthy();
  });

  it("calls Clerk's real signOut when Sign out is pressed", async () => {
    render(<AccountScreen />);
    await waitFor(() => expect(screen.getByText("Ada Lovelace")).toBeTruthy());

    fireEvent.press(screen.getByText("Sign out"));

    await waitFor(() => expect(mockSignOut).toHaveBeenCalledTimes(1));
  });

  it("marks not-yet-implemented sections as SOON rather than presenting them as working", async () => {
    render(<AccountScreen />);
    await waitFor(() => expect(screen.getByText("Ada Lovelace")).toBeTruthy());

    expect(screen.getByText("Saved opportunities")).toBeTruthy();
    expect(screen.getByText("Learned traits")).toBeTruthy();
    expect(screen.getAllByText("SOON").length).toBeGreaterThan(0);
  });

  it("still lets a working action (About STRATUS) navigate normally", async () => {
    render(<AccountScreen />);
    await waitFor(() => expect(screen.getByText("Ada Lovelace")).toBeTruthy());

    expect(screen.getByLabelText("About STRATUS")).toBeTruthy();
  });
});

describe("signInMethodLabel", () => {
  it("labels an email-code sign-in as Email even when a stale Google externalAccount exists", () => {
    // The real bug: a device that once tried Google OAuth (even in an
    // earlier, unrelated test) keeps that externalAccounts entry on the
    // Clerk user forever -- it must never override a later, genuinely
    // email-code sign-in.
    const user = {
      primaryEmailAddress: {
        emailAddress: "ada@example.com",
        verification: { strategy: "email_code" },
      },
      externalAccounts: [{ provider: "google" }],
    } as unknown as Parameters<typeof signInMethodLabel>[0];

    expect(signInMethodLabel(user)).toBe("Email");
  });

  it("labels an email-link sign-in as Email", () => {
    const user = {
      primaryEmailAddress: {
        emailAddress: "ada@example.com",
        verification: { strategy: "email_link" },
      },
      externalAccounts: [],
    } as unknown as Parameters<typeof signInMethodLabel>[0];

    expect(signInMethodLabel(user)).toBe("Email");
  });

  it("labels a genuine Google OAuth sign-in as Google", () => {
    const user = {
      primaryEmailAddress: {
        emailAddress: "ada@example.com",
        verification: { strategy: "oauth_google" },
      },
      externalAccounts: [{ provider: "google" }],
    } as unknown as Parameters<typeof signInMethodLabel>[0];

    expect(signInMethodLabel(user)).toBe("Google");
  });

  it("labels a genuine Apple OAuth sign-in as Apple", () => {
    const user = {
      primaryEmailAddress: {
        emailAddress: "ada@example.com",
        verification: { strategy: "oauth_apple" },
      },
      externalAccounts: [{ provider: "apple" }],
    } as unknown as Parameters<typeof signInMethodLabel>[0];

    expect(signInMethodLabel(user)).toBe("Apple");
  });

  it("falls back to the externalAccounts list when the primary email carries no verification strategy", () => {
    const user = {
      primaryEmailAddress: { emailAddress: "ada@example.com" },
      externalAccounts: [{ provider: "google" }],
    } as unknown as Parameters<typeof signInMethodLabel>[0];

    expect(signInMethodLabel(user)).toBe("Google");
  });

  it("falls back to Email when there is no external account and no verification strategy", () => {
    const user = {
      primaryEmailAddress: { emailAddress: "ada@example.com" },
      externalAccounts: [],
    } as unknown as Parameters<typeof signInMethodLabel>[0];

    expect(signInMethodLabel(user)).toBe("Email");
  });

  it("falls back to a generic label when there is no email and no external account", () => {
    const user = {
      primaryEmailAddress: null,
      externalAccounts: [],
    } as unknown as Parameters<typeof signInMethodLabel>[0];

    expect(signInMethodLabel(user)).toBe("STRATUS account");
  });
});
