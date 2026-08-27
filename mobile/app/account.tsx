// V2.3A -- Identity & Account Foundation. Deliberately minimal: prove
// anonymous entry (this screen simply doesn't block anything if you never
// visit it), an account/sign-in path (Apple / Google / passwordless email),
// authenticated state, sign-out, and restoration -- not a designed
// onboarding experience (that belongs with V2.3B's personal-learning UX).
import { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import * as WebBrowser from "expo-web-browser";

import { font, spacing, theme, type } from "../constants/theme";
import { deleteAccount, linkAnonymousIdentityToAccount } from "../lib/account";
import { registerPendingLink } from "../lib/authLinkGate";
import { isClerkConfigured } from "../lib/clerkConfig";

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
import { useAuth, useSignIn, useSignUp, useSSO } from "@clerk/expo";

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
      {isSignedIn ? (
        <SignedInView onSignOut={signOut} />
      ) : (
        <SignInOptions />
      )}
    </ScrollView>
  );
}

function SignedInView({ onSignOut }: { onSignOut: () => Promise<void> }) {
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

  return (
    <View>
      <Text style={styles.heading}>You&rsquo;re signed in</Text>
      <Text style={styles.body}>Your STRATUS intelligence is synced to your account.</Text>
      <TouchableOpacity style={styles.button} onPress={handleSignOut} disabled={busy}>
        <Text style={styles.buttonText}>{busy ? "Signing out..." : "Sign out"}</Text>
      </TouchableOpacity>
      <TouchableOpacity style={styles.dangerButton} onPress={handleDeleteAccount}>
        <Text style={styles.dangerButtonText}>Delete my data</Text>
      </TouchableOpacity>
    </View>
  );
}

function SignInOptions() {
  const { startSSOFlow } = useSSO();
  // Clerk's current "Future" resource API (see @clerk/shared's
  // SignInFutureResource/SignUpFutureResource): signIn.emailCode.*/
  // signIn.finalize() and signUp.verifications.*EmailCode/signUp.finalize()
  // replace the older prepareFirstFactor/attemptFirstFactor/setActive shape
  // this app's earlier draft assumed -- verified directly against the
  // installed @clerk/expo package's own type definitions, not guessed from
  // older documentation.
  const { signIn } = useSignIn();
  const { signUp } = useSignUp();
  const [stage, setStage] = useState<"idle" | "email" | "code">("idle");
  // Combined sign-in/sign-up over one email field (V2.3A fix): whichever
  // resource actually owns the in-flight attempt, so handleVerifyCode calls
  // back into the same one handleSendCode started.
  const [flow, setFlow] = useState<"signIn" | "signUp">("signIn");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);

  const finishSignIn = useCallback((): Promise<unknown> => {
    // The one place a first-time sign-in on this device carries its
    // existing anonymous history forward -- must run before any other
    // authenticated request (see docs/DECISIONS.md's ADR-069). Deliberately
    // NOT an `async` function: both statements below must execute in the
    // same synchronous tick as the call site's own `await activate(...)`/
    // `await signIn.finalize()` resolution, with no `await` gap for
    // another macrotask (the background opportunities poll on the
    // underlying index screen, in particular -- Expo Router keeps it
    // mounted under this screen) to sneak a request in with the new Bearer
    // token before this link request does. See lib/authLinkGate.ts.
    const linkPromise = linkAnonymousIdentityToAccount();
    registerPendingLink(linkPromise);
    return linkPromise;
  }, []);

  const handleOAuth = useCallback(
    async (strategy: "oauth_apple" | "oauth_google") => {
      setBusy(true);
      try {
        // TEMPORARY diagnostic logging -- V2.3A Google/Apple OAuth live-debug
        // session (2026-08-27/28). Remove once the callback issue is
        // resolved and confirmed on-device; visible only via a connected
        // Metro dev-client session, never in a preview/production build's
        // console.
        console.log(`[oauth-debug] starting startSSOFlow(${strategy})`);
        const result = await startSSOFlow({ strategy });
        console.log("[oauth-debug] startSSOFlow result", {
          hasCreatedSessionId: Boolean(result.createdSessionId),
          hasSetActive: Boolean(result.setActive),
          authSessionResultType: result.authSessionResult?.type,
          authSessionResultUrl:
            result.authSessionResult && "url" in result.authSessionResult
              ? result.authSessionResult.url
              : undefined,
        });
        const { createdSessionId, setActive: activate } = result;
        if (createdSessionId && activate) {
          await activate({ session: createdSessionId });
          await finishSignIn();
        } else {
          console.log("[oauth-debug] no session created -- flow did not complete");
        }
      } catch (error) {
        console.log("[oauth-debug] threw", error);
        Alert.alert("Sign-in failed", error instanceof Error ? error.message : "Please try again.");
      } finally {
        setBusy(false);
      }
    },
    [startSSOFlow, finishSignIn]
  );

  const handleSendCode = useCallback(async () => {
    if (!signIn || !signUp || !email.trim()) return;
    setBusy(true);
    try {
      const { error } = await signIn.emailCode.sendCode({ emailAddress: email.trim() });
      if (!error) {
        setFlow("signIn");
        setStage("code");
        return;
      }
      // "No account with this email" is the one sign-in failure that means
      // "this is a new user" -- fall back to creating an account with the
      // same email, rather than surfacing this as a dead end. Any other
      // error (rate limit, disabled strategy, etc.) is a real sign-in
      // problem and must not be masked as "try creating an account."
      if (error.code !== "form_identifier_not_found") {
        Alert.alert("Couldn't send a code", error.message || "Please check the address and try again.");
        return;
      }
      const created = await signUp.create({ emailAddress: email.trim() });
      if (created.error) {
        Alert.alert("Couldn't send a code", created.error.message || "Please check the address and try again.");
        return;
      }
      const sent = await signUp.verifications.sendEmailCode();
      if (sent.error) {
        Alert.alert("Couldn't send a code", sent.error.message || "Please try again.");
        return;
      }
      setFlow("signUp");
      setStage("code");
    } catch (error) {
      Alert.alert("Couldn't send a code", error instanceof Error ? error.message : "Please try again.");
    } finally {
      setBusy(false);
    }
  }, [signIn, signUp, email]);

  const handleVerifyCode = useCallback(async () => {
    if (!signIn || !signUp || !code.trim()) return;
    setBusy(true);
    try {
      if (flow === "signUp") {
        const { error } = await signUp.verifications.verifyEmailCode({ code: code.trim() });
        if (!error && signUp.status === "complete") {
          await signUp.finalize();
          await finishSignIn();
          return;
        }
      } else {
        const { error } = await signIn.emailCode.verifyCode({ code: code.trim() });
        if (!error && signIn.status === "complete") {
          await signIn.finalize();
          await finishSignIn();
          return;
        }
      }
      Alert.alert("Incorrect code", "Please check the code and try again.");
    } catch (error) {
      Alert.alert("Couldn't verify code", error instanceof Error ? error.message : "Please try again.");
    } finally {
      setBusy(false);
    }
  }, [signIn, signUp, code, flow, finishSignIn]);

  return (
    <View>
      <Text style={styles.heading}>Secure your STRATUS intelligence</Text>
      <Text style={styles.body}>
        You can keep using STRATUS as a guest. Signing in syncs your intelligence across devices.
      </Text>

      <TouchableOpacity
        style={styles.button}
        onPress={() => handleOAuth("oauth_apple")}
        disabled={busy}
      >
        <Text style={styles.buttonText}>Continue with Apple</Text>
      </TouchableOpacity>
      <TouchableOpacity
        style={styles.button}
        onPress={() => handleOAuth("oauth_google")}
        disabled={busy}
      >
        <Text style={styles.buttonText}>Continue with Google</Text>
      </TouchableOpacity>

      {stage === "idle" && (
        <TouchableOpacity style={styles.secondaryButton} onPress={() => setStage("email")}>
          <Text style={styles.secondaryButtonText}>Continue with email</Text>
        </TouchableOpacity>
      )}

      {stage === "email" && (
        <View style={styles.emailForm}>
          <TextInput
            style={styles.input}
            placeholder="you@example.com"
            placeholderTextColor={theme.muted}
            autoCapitalize="none"
            keyboardType="email-address"
            value={email}
            onChangeText={setEmail}
          />
          <TouchableOpacity style={styles.button} onPress={handleSendCode} disabled={busy}>
            <Text style={styles.buttonText}>{busy ? "Sending..." : "Send code"}</Text>
          </TouchableOpacity>
        </View>
      )}

      {stage === "code" && (
        <View style={styles.emailForm}>
          <TextInput
            style={styles.input}
            placeholder="6-digit code"
            placeholderTextColor={theme.muted}
            keyboardType="number-pad"
            value={code}
            onChangeText={setCode}
          />
          <TouchableOpacity style={styles.button} onPress={handleVerifyCode} disabled={busy}>
            <Text style={styles.buttonText}>{busy ? "Verifying..." : "Verify"}</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
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
  content: { padding: spacing.xl, paddingTop: spacing.xxl, gap: spacing.md },
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
    marginBottom: spacing.lg,
  },
  button: {
    backgroundColor: theme.accent,
    borderRadius: 12,
    paddingVertical: spacing.md,
    alignItems: "center",
    marginBottom: spacing.sm,
  },
  buttonText: { fontFamily: font.headingMedium, color: theme.background, fontSize: 16 },
  secondaryButton: { paddingVertical: spacing.md, alignItems: "center" },
  secondaryButtonText: { fontFamily: font.bodyMedium, color: theme.accent, fontSize: 15 },
  dangerButton: { paddingVertical: spacing.md, alignItems: "center", marginTop: spacing.lg },
  dangerButtonText: { fontFamily: font.bodyMedium, color: "#e0554f", fontSize: 15 },
  emailForm: { gap: spacing.sm },
  input: {
    borderWidth: 1,
    borderColor: theme.border,
    borderRadius: 12,
    padding: spacing.md,
    color: theme.text,
    fontSize: 16,
  },
});
