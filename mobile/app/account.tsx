// V2.3A -- Identity & Account Foundation, consumer closeout pass. Reached
// three ways: from the menu at any time, as the header avatar's tap target
// (app/index.tsx), and as the first-run onboarding account step
// (app/onboarding/account.tsx) -- the sign-in path shares the same
// underlying auth logic and content block (hooks/useStratusAuth.ts,
// components/auth/MakeStratusYoursCard.tsx) across all three; this file's
// own job is the standalone-screen shell plus, once signed in, the full
// Account & Settings hub (profile, interests, notifications, privacy,
// help, sign-out).
import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Linking,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import * as Notifications from "expo-notifications";
import { router } from "expo-router";
import * as WebBrowser from "expo-web-browser";

import { font, radius, spacing, theme, type } from "../constants/theme";
import { deleteAccount } from "../lib/account";
import { isClerkConfigured } from "../lib/clerkConfig";
import {
  DeclaredInterests,
  INTEREST_CATEGORIES,
  InterestCategoryId,
  getDeclaredInterests,
  saveDeclaredInterests,
} from "../lib/interests";
import { MakeStratusYoursCard } from "../components/auth/MakeStratusYoursCard";
import { ProfileAvatar, ProfileAvatarUser } from "../components/ProfileAvatar";

// Required once, at module scope, by Clerk's own documented Expo OAuth
// pattern -- completes a pending browser-based auth session if the app was
// backgrounded mid-flow and is now foregrounding via the OAuth redirect.
WebBrowser.maybeCompleteAuthSession();

export default function AccountScreen() {
  if (!isClerkConfigured()) {
    return <GuestOnlyNotice />;
  }
  return <ConfiguredAccountScreen />;
}

/** Every environment until the owner supplies real Clerk credentials (see
 * docs/DECISIONS.md's ADR-069) -- the anonymous-only experience is complete
 * and correct on its own; this is purely informational. */
function GuestOnlyNotice() {
  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <View style={styles.guestIconCircle}>
        <Ionicons name="person-outline" size={22} color={theme.textSecondary} />
      </View>
      <Text style={styles.heading}>You&rsquo;re using STRATUS as a guest</Text>
      <Text style={styles.body}>
        STRATUS works fully without an account. Sign-in will appear here once it&rsquo;s configured
        for this build.
      </Text>
    </ScrollView>
  );
}

// Deferred to a dynamic import inside ConfiguredAccountScreen's own module
// scope guard would be unnecessarily indirect here -- @clerk/expo's hooks
// are safe to import unconditionally; they simply require a ClerkProvider
// ancestor, which _layout.tsx only ever mounts when isClerkConfigured().
// eslint-disable-next-line import/first
import { useAuth, useUser } from "@clerk/expo";

function ConfiguredAccountScreen() {
  const { isLoaded, isSignedIn, signOut } = useAuth();

  if (!isLoaded) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator color={theme.accent} />
      </View>
    );
  }

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      {isSignedIn ? <AccountAndSettings onSignOut={signOut} /> : <MakeStratusYoursCard />}
    </ScrollView>
  );
}

export function signInMethodLabel(user: ReturnType<typeof useUser>["user"]): string {
  // Bug fix: user.externalAccounts is account-wide -- every OAuth provider
  // ever linked to this Clerk user, for the account's entire lifetime, not
  // "how did I sign in this session." A device that once tried Google
  // OAuth (even in an earlier test) keeps that externalAccounts entry
  // forever, so checking it first showed "Signed in with Google" for a
  // later, genuinely email-code sign-in. The primary email's own
  // verification.strategy is the real signal for how *that specific
  // identifier* was verified ("email_code"/"email_link" vs
  // "oauth_google"/"oauth_apple"/...) -- check that first, and only fall
  // back to the account-wide externalAccounts list when the primary email
  // itself carries no verification info at all (e.g. no primary email
  // exists yet).
  const emailStrategy = user?.primaryEmailAddress?.verification?.strategy;
  if (emailStrategy === "email_code" || emailStrategy === "email_link") {
    return "Email";
  }
  if (emailStrategy?.startsWith("oauth_")) {
    const provider = emailStrategy.slice("oauth_".length);
    return provider.charAt(0).toUpperCase() + provider.slice(1);
  }
  const externalProvider = user?.externalAccounts?.[0]?.provider;
  if (externalProvider) {
    return externalProvider.charAt(0).toUpperCase() + externalProvider.slice(1);
  }
  if (user?.primaryEmailAddress) {
    return "Email";
  }
  return "STRATUS account";
}

function AccountAndSettings({ onSignOut }: { onSignOut: () => Promise<void> }) {
  const { user } = useUser();
  const [busy, setBusy] = useState(false);

  const handleSignOut = useCallback(async () => {
    setBusy(true);
    try {
      await onSignOut();
    } finally {
      setBusy(false);
    }
  }, [onSignOut]);

  const handleDeleteAccount = useCallback(() => {
    Alert.alert(
      "Delete account data",
      "This permanently removes your STRATUS interaction history, watch state, and notification settings. This cannot be undone.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: async () => {
            const ok = await deleteAccount();
            if (ok) {
              await onSignOut();
            } else {
              Alert.alert("Something went wrong", "Please try again.");
            }
          },
        },
      ]
    );
  }, [onSignOut]);

  const identifier = user?.primaryEmailAddress?.emailAddress ?? user?.fullName ?? "your account";

  return (
    <View>
      <View style={styles.profileHeader}>
        <ProfileAvatar user={(user as ProfileAvatarUser | null) ?? null} size={72} />
        <Text style={styles.profileName}>{user?.fullName || identifier}</Text>
        <Text style={styles.identifierText}>{identifier}</Text>
        <View style={styles.methodPill}>
          <Text style={styles.methodPillText}>Signed in with {signInMethodLabel(user)}</Text>
        </View>
      </View>

      <InterestsSection />
      <TrackedOpportunitiesSection />
      <NotificationPreferencesSection />
      <PersonalizationSection />
      <PrivacySection onDeleteAccount={handleDeleteAccount} />
      <HelpSection />

      <TouchableOpacity style={styles.signOutButton} onPress={handleSignOut} disabled={busy}>
        <Text style={styles.signOutButtonText}>{busy ? "Signing out..." : "Sign out"}</Text>
      </TouchableOpacity>
    </View>
  );
}

// --- Shared section/row presentation -----------------------------------

function SettingsSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionLabel}>{title}</Text>
      <View style={styles.sectionCard}>{children}</View>
    </View>
  );
}

function SettingsRow({
  icon,
  label,
  sublabel,
  onPress,
  trailing,
  soon,
  destructive,
}: {
  icon: React.ComponentProps<typeof Ionicons>["name"];
  label: string;
  sublabel?: string;
  onPress?: () => void;
  trailing?: React.ReactNode;
  soon?: boolean;
  destructive?: boolean;
}) {
  const disabled = soon || !onPress;
  return (
    <TouchableOpacity
      style={styles.row}
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityLabel={soon ? `${label}, coming soon` : label}
      accessibilityState={{ disabled }}
    >
      <Ionicons
        name={icon}
        size={17}
        color={destructive ? theme.warning : theme.textSecondary}
        style={styles.rowIcon}
      />
      <View style={styles.rowTextGroup}>
        <Text style={[styles.rowLabel, destructive && styles.rowLabelDestructive]}>{label}</Text>
        {sublabel && <Text style={styles.rowSublabel}>{sublabel}</Text>}
      </View>
      {soon ? (
        <View style={styles.soonPill}>
          <Text style={styles.soonPillText}>SOON</Text>
        </View>
      ) : (
        trailing ?? (onPress && <Ionicons name="chevron-forward" size={15} color={theme.muted} />)
      )}
    </TouchableOpacity>
  );
}

// --- Interests ------------------------------------------------------------

function InterestsSection() {
  const [selected, setSelected] = useState<Set<InterestCategoryId> | null>(null);

  useEffect(() => {
    let cancelled = false;
    getDeclaredInterests()
      .then((stored: DeclaredInterests | null) => {
        if (!cancelled) setSelected(new Set(stored?.categories ?? []));
      })
      .catch(() => {
        if (!cancelled) setSelected(new Set());
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const toggle = (id: InterestCategoryId) => {
    setSelected((prev) => {
      const next = new Set(prev ?? []);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      saveDeclaredInterests(Array.from(next)).catch(() => {});
      return next;
    });
  };

  return (
    <SettingsSection title="INTERESTS">
      {selected === null ? (
        <View style={styles.rowPad}>
          <ActivityIndicator color={theme.accent} />
        </View>
      ) : (
        <View style={styles.chipWrap}>
          {INTEREST_CATEGORIES.map((category) => {
            const isSelected = selected.has(category.id);
            return (
              <TouchableOpacity
                key={category.id}
                style={[styles.chip, isSelected && styles.chipSelected]}
                onPress={() => toggle(category.id)}
                accessibilityRole="button"
                accessibilityState={{ selected: isSelected }}
                accessibilityLabel={category.label}
              >
                <Ionicons
                  name={category.icon}
                  size={13}
                  color={isSelected ? theme.accent : theme.textSecondary}
                />
                <Text style={[styles.chipText, isSelected && styles.chipTextSelected]}>
                  {category.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
      )}
    </SettingsSection>
  );
}

function TrackedOpportunitiesSection() {
  return (
    <SettingsSection title="TRACKED OPPORTUNITIES">
      <SettingsRow icon="bookmark-outline" label="Saved opportunities" soon />
    </SettingsSection>
  );
}

// --- Notifications ----------------------------------------------------

function NotificationPreferencesSection() {
  const [permission, setPermission] = useState<Notifications.PermissionStatus | null>(null);

  useEffect(() => {
    let cancelled = false;
    Notifications.getPermissionsAsync()
      .then((result) => {
        if (!cancelled) setPermission(result.status);
      })
      .catch(() => {
        if (!cancelled) setPermission(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const enabled = permission === Notifications.PermissionStatus.GRANTED;

  return (
    <SettingsSection title="NOTIFICATIONS">
      <SettingsRow
        icon="notifications-outline"
        label="Push notifications"
        sublabel={
          permission === null
            ? "Checking..."
            : enabled
              ? "Enabled for this device"
              : "Disabled -- open Settings to enable"
        }
        onPress={enabled ? undefined : () => Linking.openSettings()}
        trailing={
          <Switch
            value={enabled}
            disabled
            trackColor={{ true: theme.accent, false: theme.border }}
          />
        }
      />
      <SettingsRow icon="options-outline" label="Per-category alert preferences" soon />
    </SettingsSection>
  );
}

// --- Personalization (V2.3B boundary -- placeholder only) --------------

function PersonalizationSection() {
  return (
    <SettingsSection title="PERSONALIZATION">
      <SettingsRow
        icon="sparkles-outline"
        label="Learned traits"
        sublabel="STRATUS will explain what it's learned about your interests here"
        soon
      />
      <SettingsRow icon="thumbs-down-outline" label="Corrections & not-interested history" soon />
    </SettingsSection>
  );
}

// --- Privacy -------------------------------------------------------------

function PrivacySection({ onDeleteAccount }: { onDeleteAccount: () => void }) {
  return (
    <SettingsSection title="PRIVACY & DATA">
      <SettingsRow icon="document-text-outline" label="Privacy policy" soon />
      <SettingsRow
        icon="trash-outline"
        label="Delete my data"
        onPress={onDeleteAccount}
        destructive
      />
    </SettingsSection>
  );
}

// --- Help ------------------------------------------------------------------

function HelpSection() {
  return (
    <SettingsSection title="HELP">
      <SettingsRow icon="information-circle-outline" label="About STRATUS" onPress={() => router.push("/about")} />
    </SettingsSection>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: theme.background },
  centered: {
    flex: 1,
    backgroundColor: theme.background,
    alignItems: "center",
    justifyContent: "center",
  },
  content: { padding: spacing.xl, paddingTop: spacing.xxl, paddingBottom: spacing.xxl, gap: spacing.md },
  heading: {
    fontFamily: font.heading,
    fontSize: type.title,
    color: theme.text,
    marginBottom: spacing.sm,
  },
  body: {
    fontFamily: font.body,
    fontSize: type.body,
    color: theme.muted,
  },
  guestIconCircle: {
    width: 48,
    height: 48,
    borderRadius: radius.pill,
    backgroundColor: theme.surface,
    borderWidth: 1,
    borderColor: theme.border,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.lg,
  },
  profileHeader: { alignItems: "center", marginBottom: spacing.lg, gap: 4 },
  profileName: {
    fontFamily: font.heading,
    fontSize: type.title,
    color: theme.text,
    marginTop: spacing.md,
  },
  identifierText: {
    fontFamily: font.body,
    fontSize: type.label,
    color: theme.muted,
  },
  methodPill: {
    marginTop: spacing.sm,
    backgroundColor: theme.surface,
    borderWidth: 1,
    borderColor: theme.border,
    borderRadius: radius.pill,
    paddingVertical: 4,
    paddingHorizontal: spacing.md,
  },
  methodPillText: { fontFamily: font.metadata, fontSize: type.micro, color: theme.textSecondary },
  section: { marginBottom: spacing.lg },
  sectionLabel: {
    fontFamily: font.metadata,
    fontSize: type.micro,
    color: theme.muted,
    letterSpacing: 1.4,
    marginBottom: spacing.sm,
  },
  sectionCard: {
    backgroundColor: theme.surface,
    borderWidth: 1,
    borderColor: theme.border,
    borderRadius: radius.md,
    overflow: "hidden",
  },
  rowPad: { padding: spacing.lg, alignItems: "center" },
  row: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: theme.border,
  },
  rowIcon: { width: 24 },
  rowTextGroup: { flex: 1 },
  rowLabel: { fontFamily: font.bodyMedium, color: theme.text, fontSize: type.body },
  rowLabelDestructive: { color: theme.warning },
  rowSublabel: { fontFamily: font.body, color: theme.muted, fontSize: type.micro + 1, marginTop: 2 },
  soonPill: {
    backgroundColor: theme.surfaceSoft,
    borderRadius: radius.pill,
    paddingVertical: 3,
    paddingHorizontal: spacing.sm,
  },
  soonPillText: { fontFamily: font.metadata, fontSize: 9, color: theme.muted, letterSpacing: 1 },
  chipWrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    padding: spacing.md,
    gap: spacing.xs,
  },
  chip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    borderWidth: 1,
    borderColor: theme.border,
    borderRadius: radius.pill,
    paddingVertical: 6,
    paddingHorizontal: spacing.sm,
  },
  chipSelected: { borderColor: theme.accent, backgroundColor: theme.accentSoft },
  chipText: { fontFamily: font.bodyMedium, fontSize: type.micro + 1, color: theme.textSecondary },
  chipTextSelected: { color: theme.accent },
  signOutButton: {
    borderWidth: 1,
    borderColor: theme.border,
    borderRadius: radius.md,
    paddingVertical: spacing.md,
    alignItems: "center",
    marginTop: spacing.md,
  },
  signOutButtonText: { fontFamily: font.bodyMedium, color: theme.textSecondary, fontSize: 15 },
});
