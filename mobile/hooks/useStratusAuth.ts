// V2.3A consumer closeout -- shared auth state machine, extracted from
// app/account.tsx's original SignInOptions so the same logic (and, more
// importantly, the same account-link/session-safety behavior) backs both
// the first-run "Make STRATUS yours" onboarding screen and the standalone
// Account screen reachable from the menu, without duplicating it.
//
// This hook owns ONLY state/behavior -- no JSX. Both call sites render
// their own copy/layout around it (see components/auth/AuthMethodControls
// for the one piece of UI that genuinely is identical between them).
//
// The temporary [oauth-debug] console logging used to diagnose the
// Google/Apple OAuth failures (expo-crypto native module + Clerk Apple
// provider config) has been removed here now that both are confirmed
// working end-to-end on-device -- see git history on app/account.tsx for
// that diagnostic session if it's ever needed again.
import { useCallback, useState } from "react";
import { Alert } from "react-native";
import { useSignIn, useSignUp, useSSO } from "@clerk/expo";

import { linkAnonymousIdentityToAccount } from "../lib/account";
import { registerPendingLink } from "../lib/authLinkGate";

export type EmailStage = "idle" | "email" | "code";
export type EmailFlow = "signIn" | "signUp";

export function useStratusAuth(onAuthComplete?: () => void) {
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
  const [stage, setStage] = useState<EmailStage>("idle");
  // Combined sign-in/sign-up over one email field (V2.3A fix): whichever
  // resource actually owns the in-flight attempt, so handleVerifyCode calls
  // back into the same one handleSendCode started.
  const [flow, setFlow] = useState<EmailFlow>("signIn");
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
        const { createdSessionId, setActive: activate } = await startSSOFlow({ strategy });
        if (createdSessionId && activate) {
          await activate({ session: createdSessionId });
          await finishSignIn();
          onAuthComplete?.();
        }
      } catch (error) {
        Alert.alert("Sign-in failed", error instanceof Error ? error.message : "Please try again.");
      } finally {
        setBusy(false);
      }
    },
    [startSSOFlow, finishSignIn, onAuthComplete]
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
          onAuthComplete?.();
          return;
        }
      } else {
        const { error } = await signIn.emailCode.verifyCode({ code: code.trim() });
        if (!error && signIn.status === "complete") {
          await signIn.finalize();
          await finishSignIn();
          onAuthComplete?.();
          return;
        }
      }
      Alert.alert("Incorrect code", "Please check the code and try again.");
    } catch (error) {
      Alert.alert("Couldn't verify code", error instanceof Error ? error.message : "Please try again.");
    } finally {
      setBusy(false);
    }
  }, [signIn, signUp, code, flow, finishSignIn, onAuthComplete]);

  return {
    stage,
    setStage,
    email,
    setEmail,
    code,
    setCode,
    busy,
    handleOAuth,
    handleSendCode,
    handleVerifyCode,
  };
}
