// V2.3A -- Identity & Account Foundation.
//
// Jest manual mock for `@clerk/expo`, picked up automatically for every
// test in this project (Jest's node_modules manual-mock convention: a file
// at __mocks__/<package>.js next to node_modules, no explicit jest.mock()
// call needed). Required because @clerk/react's real CJS build reaches into
// a web-only `react-dom` dependency during plain Node module resolution --
// broken under Jest's Node test environment even though Expo/Metro's real
// bundler resolves the correct native entry point at build/run time and
// never hits this path on a real device.
//
// None of this project's existing Jest tests exercise real Clerk sign-in
// behavior (that requires a real device/simulator + a real Clerk project --
// see the V2.3A report's own "not independently verifiable in this
// environment" note) -- this mock exists solely so files that import
// `@clerk/expo` (lib/clerkClient.ts, app/_layout.tsx, app/account.tsx) don't
// crash the whole test suite at import time. Every export here is a safe,
// inert no-op.
module.exports = {
  getClerkInstance: () => ({ session: undefined }),
  ClerkProvider: ({ children }) => children,
  useAuth: () => ({
    isLoaded: true,
    isSignedIn: false,
    userId: null,
    getToken: async () => null,
    signOut: async () => {},
  }),
  useSignIn: () => ({ signIn: undefined }),
  useSSO: () => ({ startSSOFlow: async () => ({ createdSessionId: null }) }),
};
