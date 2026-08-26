import { registerPendingLink, waitForPendingLink } from "../authLinkGate";

describe("authLinkGate", () => {
  it("resolves immediately when no link is registered", async () => {
    const start = Date.now();
    await waitForPendingLink();
    expect(Date.now() - start).toBeLessThan(50);
  });

  it("waits for a registered link to settle before resolving", async () => {
    let linkResolved = false;
    let resolveLink!: () => void;
    const linkPromise = new Promise<void>((resolve) => {
      resolveLink = () => {
        linkResolved = true;
        resolve();
      };
    });

    registerPendingLink(linkPromise);

    const waitPromise = waitForPendingLink().then(() => {
      // By the time waitForPendingLink() resolves, the link itself must
      // already have settled -- this is the exact ordering guarantee that
      // prevents a background request from racing ahead of /v1/account/link.
      expect(linkResolved).toBe(true);
    });

    // Give the microtask queue a tick -- waitForPendingLink() must NOT have
    // resolved yet, since the link hasn't settled.
    await Promise.race([waitPromise, Promise.resolve("still-pending")]).then((result) => {
      expect(result).toBe("still-pending");
    });

    resolveLink();
    await waitPromise;
  });

  it("clears the gate after the link settles, even on failure", async () => {
    const failingLink = Promise.reject(new Error("link failed"));
    registerPendingLink(failingLink);

    // Must never throw, and must not leave future callers blocked forever.
    await waitForPendingLink();
    await waitForPendingLink();
  });

  it("a later registration replaces the earlier gate", async () => {
    let resolveFirst!: () => void;
    const first = new Promise<void>((resolve) => {
      resolveFirst = resolve;
    });
    registerPendingLink(first);

    const second = Promise.resolve();
    registerPendingLink(second);

    // The second (already-resolved) registration means waitForPendingLink()
    // resolves immediately, without needing `first` to ever settle.
    const start = Date.now();
    await waitForPendingLink();
    expect(Date.now() - start).toBeLessThan(50);

    resolveFirst();
  });
});
