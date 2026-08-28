// V2.3A consumer closeout -- the standard account affordance: a circular
// profile avatar in the Attention Field header's top-right, replacing the
// previous ambiguous pulsing orange dot (which doubled, confusingly, as
// both a decorative "live" indicator and the notification tap target).
// Shows Clerk's real profile image when the signed-in user actually has one
// (`hasImage` -- Clerk's own field for "not just a generated placeholder"),
// initials derived from their name/email as the fallback, and a plain
// person glyph for a guest (no Clerk user at all) -- every state routes to
// the same Account & Settings screen, so this is also how a guest
// discovers sign-in without digging through the menu.
import { Image, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { font, theme } from "../constants/theme";

// Mirrors @clerk/shared's UserResource shape narrowly -- only the fields
// this component actually reads, so it works whether the caller passes a
// real Clerk UserResource or (in tests) a plain object literal.
export interface ProfileAvatarUser {
  hasImage: boolean;
  imageUrl: string;
  fullName: string | null;
  firstName: string | null;
  lastName: string | null;
  primaryEmailAddress: { emailAddress: string } | null;
}

function initialsFor(user: ProfileAvatarUser): string {
  const first = user.firstName?.trim()?.[0];
  const last = user.lastName?.trim()?.[0];
  if (first && last) return `${first}${last}`.toUpperCase();
  if (first) return first.toUpperCase();

  const fullNamePart = user.fullName?.trim()?.[0];
  if (fullNamePart) return fullNamePart.toUpperCase();

  const emailPart = user.primaryEmailAddress?.emailAddress?.trim()?.[0];
  if (emailPart) return emailPart.toUpperCase();

  return "?";
}

export function ProfileAvatar({ user, size = 30 }: { user: ProfileAvatarUser | null; size?: number }) {
  const dimension = { width: size, height: size, borderRadius: size / 2 };

  if (user?.hasImage && user.imageUrl) {
    return (
      <Image
        source={{ uri: user.imageUrl }}
        style={[styles.circle, dimension]}
        accessibilityRole="image"
        accessibilityLabel="Your profile"
      />
    );
  }

  if (user) {
    return (
      <View style={[styles.circle, styles.initialsCircle, dimension]}>
        <Text style={[styles.initialsText, { fontSize: size * 0.4 }]}>{initialsFor(user)}</Text>
      </View>
    );
  }

  return (
    <View style={[styles.circle, styles.guestCircle, dimension]}>
      <Ionicons name="person-outline" size={size * 0.55} color={theme.textSecondary} />
    </View>
  );
}

const styles = StyleSheet.create({
  circle: {
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
  },
  initialsCircle: {
    backgroundColor: theme.accentSoft,
    borderWidth: 1,
    borderColor: theme.accent,
  },
  initialsText: {
    color: theme.accent,
    fontFamily: font.headingMedium,
  },
  guestCircle: {
    backgroundColor: theme.surface,
    borderWidth: 1,
    borderColor: theme.border,
  },
});
