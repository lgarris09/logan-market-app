// V2.3A -- Identity & Account Foundation. Clerk's own persisted-session
// token, backed by the platform keychain (expo-secure-store), the same
// storage mechanism this app already uses for its anonymous per-install
// identity (see lib/identity.ts). This is what makes "close the app, reopen
// it, still signed in" (acceptance item 11: session restoration) work --
// Clerk reads this cache on launch and restores the session before
// `useAuth()` ever reports `isSignedIn`.
import * as SecureStore from "expo-secure-store";
import type { TokenCache } from "@clerk/expo";

export const clerkTokenCache: TokenCache = {
  async getToken(key: string) {
    try {
      return await SecureStore.getItemAsync(key);
    } catch {
      // A real keychain read failure (rare) degrades to "no cached session"
      // rather than crashing the app -- the user simply needs to sign in
      // again, exactly the same UX as a genuinely fresh install.
      return null;
    }
  },
  async saveToken(key: string, value: string) {
    try {
      await SecureStore.setItemAsync(key, value);
    } catch {
      // Best-effort -- a failed write means the session won't survive a
      // restart this one time, not that sign-in itself fails.
    }
  },
  async clearToken(key: string) {
    try {
      await SecureStore.deleteItemAsync(key);
    } catch {
      // Best-effort, same reasoning as above.
    }
  },
};
