# Vendor inquiry — Intrinio, Zacks EPS Surprises

Status: ready to send. **Not sent.** It goes from Logan's address; nothing in this session can send
email, and a first contact with a vendor should come from the account owner.

Internal rule (Logan and Chuck, 2026-10-06): this inquiry does not block Beta 1. If the answer is not
practical at beta scale, Beta 1 proceeds with unsupported EPS-surprise disabled. No provider migration
is started on the strength of a reply.

---

**Subject:** Zacks EPS Surprises feed — methodology and small-scale licensing questions

Hello,

We are evaluating the Zacks EPS Surprises data feed for a consumer mobile app in private beta. The app
tells a user when a company they follow reports earnings and whether the result was above or below
consensus. We will only state that comparison when the two figures are on the same basis, so the
methodology matters more to us than coverage. Our universe is about 100 US large-cap companies.

Could you confirm the following?

1. **Actual EPS.** How is `eps_actual` derived? Is it always the company's non-GAAP figure as adjusted
   by Zacks, and how is a company that reports only GAAP handled?
2. **Consensus EPS.** On what basis is `eps_mean_estimate` compiled, and is it the consensus as it stood
   immediately before the release?
3. **Basis match.** For a given row, are the actual and the estimate guaranteed to be on the same basis
   (accounting basis and share count)? If there are exceptions, is there a field that flags them?
4. **Fiscal period.** Does each row identify the fiscal year and quarter for both the actual and the
   estimate, so the two can be matched to the same period?
5. **Timing.** How soon after a company's release does the row become available through the API? Is the
   timestamp of the last consensus update available?
6. **Revisions.** If a company restates, or Zacks revises an actual or an adjustment after the fact, is
   the row updated in place, and is the change visible?
7. **Access.** Which plan includes this feed for a universe of about 100 tickers without history?
8. **Display licence.** May these values, or a beat / miss statement derived from them, be shown to end
   users in a consumer app, including during a small private beta of under ten users?
9. **Price** for that scope.

A short written answer is all we need at this stage. Thank you.

Logan Garris
