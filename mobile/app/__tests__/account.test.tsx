import { fireEvent, render, screen, waitFor } from "@testing-library/react-native";

import AccountScreen from "../account";

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
      // Deliberately non-empty, mirroring the real bug scenario: an
      // account-wide externalAccounts entry from an earlier/different
      // sign-in method must never resurrect a "Signed in with X" badge --
      // there shouldn't be one at all anymore (see account.tsx's own
      // removal comment for why no Clerk data reliably answers "how was
      // *this* session established").
      externalAccounts: [{ provider: "google" }],
    },
  }),
}));

describe("AccountScreen (signed in)", () => {
  beforeEach(() => {
    mockSignOut.mockClear();
  });

  it("shows the signed-in profile with the real identifier", async () => {
    render(<AccountScreen />);

    await waitFor(() => expect(screen.getByText("ada@example.com")).toBeTruthy());
    expect(screen.getByText("Ada Lovelace")).toBeTruthy();
  });

  it("never shows a 'Signed in with X' provider badge", async () => {
    // Regression test: no Clerk data reliably identifies which method
    // established the *current* session (see account.tsx's own removal
    // comment) -- the badge must stay gone, not silently reappear derived
    // from the account-wide externalAccounts list this mock deliberately
    // includes.
    render(<AccountScreen />);
    await waitFor(() => expect(screen.getByText("Ada Lovelace")).toBeTruthy());

    expect(screen.queryByText(/Signed in with/i)).toBeNull();
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
