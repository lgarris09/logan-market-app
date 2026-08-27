// TEMPORARY UPSTREAM CLERK PACKAGING WORKAROUND -- V2.3A on-device validation
// (2026-08-27). Not a permanent part of this project's architecture.
//
// @clerk/react's package.json exports no "react-native" condition, so Metro
// always resolves "@clerk/expo" -> "@clerk/react" (both its main entry and
// its "./internal" subpath) to universal CJS chunks that eagerly
// `require("react-dom")` / `require("react-dom/client")` at module
// top-level (real code path: web-only DOM-portal/hydration rendering for
// Clerk's web modal UI, never invoked by any of Clerk's React Native
// components -- useAuth/useSSO/<SignedIn> etc. never call into it).
// react-dom is correctly absent from this project, so Metro's static
// resolver fails to build even though nothing on-device ever executes that
// branch. Confirmed via upstream search (clerk/javascript issues/PRs/
// .changeset, 2026-08-27): no filed issue, no shipped fix, no queued
// changeset addresses this -- the existing merged fixes (PR #7579, #7591,
// #8789) only cover npm install-time peer-dependency resolution, not this
// Metro bundle-time resolution failure.
//
// Started as an exact match on "react-dom" alone; broadened same day to
// every "react-dom/*" subpath once "react-dom/client" (imported by
// @clerk/react's main entry, a sibling of the same eager-import block)
// surfaced as the next unresolved module one bundle-attempt later.
// Deliberately still scoped to the react-dom namespace only -- no other
// resolver shims.
//
// REMOVAL CONDITION: delete this file once Clerk ships a native-safe
// "@clerk/react" export path (main entry and "./internal") that does not
// eagerly require any web-only React DOM module on React Native. Re-check
// by removing this override and running
// `eas build --profile preview --platform ios` -- if the eager bundle
// phase no longer fails on react-dom/react-dom/*, this file is obsolete.
// A second, unrelated temporary Expo-packaging compatibility pin lives in
// package.json's "overrides" ({ "expo-crypto": "15.0.9" }), added the same
// V2.3A on-device debug session: expo-auth-session@57.0.9 declares its own
// "expo-crypto": "~57.0.2" dependency, incompatible with this project's
// SDK-54 expo-crypto@15.0.9 -- npm installed a second, nested copy at
// expo-auth-session/node_modules/expo-crypto whose native AES module
// (ExpoCryptoAES) was never autolinked into the compiled binary, causing
// `Cannot find native module 'ExpoCryptoAES'` and a silently-undefined
// `AuthSession` inside @clerk/expo's useSSO.js the moment any OAuth
// (Google/Apple) sign-in was attempted. Confirmed expo-auth-session's own
// PKCE code only ever calls Crypto.getRandomValues()/digestStringAsync(),
// both present in 15.0.9 -- forcing that one resolution everywhere is
// sufficient. REMOVAL CONDITION for that override: once expo-auth-session
// ships a version whose own expo-crypto dependency range is compatible
// with this project's Expo SDK line, delete the "overrides" entry and
// confirm `npm ls expo-crypto` shows a single, undeduped copy.
const { getDefaultConfig } = require("expo/metro-config");

const config = getDefaultConfig(__dirname);

const upstreamResolveRequest = config.resolver.resolveRequest;
config.resolver.resolveRequest = (context, moduleName, platform) => {
  if (moduleName === "react-dom" || moduleName.startsWith("react-dom/")) {
    return { type: "empty" };
  }
  return upstreamResolveRequest
    ? upstreamResolveRequest(context, moduleName, platform)
    : context.resolveRequest(context, moduleName, platform);
};

module.exports = config;
