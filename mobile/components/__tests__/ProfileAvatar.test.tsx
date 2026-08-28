import { render, screen } from "@testing-library/react-native";

import { ProfileAvatar, ProfileAvatarUser } from "../ProfileAvatar";

// Same @expo/vector-icons mocking convention as app/__tests__/index.test.tsx
// -- renders as plain text so the guest fallback's glyph is assertable.
jest.mock("@expo/vector-icons", () => {
  const { Text } = jest.requireActual("react-native");
  return { Ionicons: (props: { name: string }) => <Text>{`icon:${props.name}`}</Text> };
});

function fakeUser(overrides: Partial<ProfileAvatarUser>): ProfileAvatarUser {
  return {
    hasImage: false,
    imageUrl: "",
    fullName: null,
    firstName: null,
    lastName: null,
    primaryEmailAddress: null,
    ...overrides,
  };
}

describe("ProfileAvatar", () => {
  it("renders a person glyph for a guest (no user at all)", () => {
    render(<ProfileAvatar user={null} />);

    expect(screen.getByText("icon:person-outline")).toBeTruthy();
  });

  it("renders the real Clerk profile image when the user has one", () => {
    render(<ProfileAvatar user={fakeUser({ hasImage: true, imageUrl: "https://example.com/me.jpg" })} />);

    const image = screen.getByLabelText("Your profile");
    expect(image.props.source).toEqual({ uri: "https://example.com/me.jpg" });
  });

  it("falls back to first+last initials when there's no image", () => {
    render(<ProfileAvatar user={fakeUser({ firstName: "Ada", lastName: "Lovelace" })} />);

    expect(screen.getByText("AL")).toBeTruthy();
  });

  it("falls back to a single initial from firstName alone", () => {
    render(<ProfileAvatar user={fakeUser({ firstName: "Ada" })} />);

    expect(screen.getByText("A")).toBeTruthy();
  });

  it("falls back to fullName's first letter when no first/last name is set", () => {
    render(<ProfileAvatar user={fakeUser({ fullName: "Grace Hopper" })} />);

    expect(screen.getByText("G")).toBeTruthy();
  });

  it("falls back to the email address's first letter as a last resort", () => {
    render(
      <ProfileAvatar user={fakeUser({ primaryEmailAddress: { emailAddress: "grace@example.com" } })} />
    );

    expect(screen.getByText("G")).toBeTruthy();
  });

  it("never shows a placeholder-only Clerk image (hasImage false) even if imageUrl is set", () => {
    // Clerk always returns *some* imageUrl (a generated default) even when
    // hasImage is false -- rendering that would show a meaningless generic
    // graphic instead of the honest initials/guest fallback.
    render(
      <ProfileAvatar
        user={fakeUser({ hasImage: false, imageUrl: "https://img.clerk.com/default.png", firstName: "Ada" })}
      />
    );

    expect(screen.queryByLabelText("Your profile")).toBeNull();
    expect(screen.getByText("A")).toBeTruthy();
  });
});
