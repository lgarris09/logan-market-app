// TEMPORARY UPSTREAM CLERK PACKAGING WORKAROUND -- V2.3A on-device validation
// (2026-08-27). Not a permanent part of this project's architecture.
//
// @clerk/react's package.json exports no "react-native" condition, so Metro
// always resolves "@clerk/expo" -> "@clerk/react/internal" -> its universal
// internal.cjs chunk, which contains an unconditional, eager
// `require("react-dom")` at module top-level (real code path: web-only
// DOM-portal rendering for Clerk's web modal UI, never invoked by any of
// Clerk's React Native components -- useAuth/useSSO/<SignedIn> etc. never
// call into it). react-dom is correctly absent from this project, so
// Metro's static resolver fails to build even though nothing on-device ever
// executes that branch. Confirmed via upstream search (clerk/javascript
// issues/PRs/.changeset, 2026-08-27): no filed issue, no shipped fix, no
// queued changeset addresses this -- the existing merged fixes (PR #7579,
// #7591, #8789) only cover npm install-time peer-dependency resolution, not
// this Metro bundle-time resolution failure.
//
// REMOVAL CONDITION: delete this file once Clerk ships a native-safe
// "@clerk/react/internal" (or equivalent) export path that does not eagerly
// require react-dom on React Native. Re-check by removing this override and
// running `eas build --profile preview --platform ios` -- if the eager
// bundle phase no longer fails on `react-dom`, this file is obsolete.
const { getDefaultConfig } = require("expo/metro-config");

const config = getDefaultConfig(__dirname);

const upstreamResolveRequest = config.resolver.resolveRequest;
config.resolver.resolveRequest = (context, moduleName, platform) => {
  if (moduleName === "react-dom") {
    return { type: "empty" };
  }
  return upstreamResolveRequest
    ? upstreamResolveRequest(context, moduleName, platform)
    : context.resolveRequest(context, moduleName, platform);
};

module.exports = config;
