# Logan Intelligence — Security, Privacy & Compliance
**Version:** 3.1.3
*Source: Architecture v1.3 FINAL (2026-07-31). Original: “source_material/27_SECURITY_PRIVACY_COMPLIANCE.md” (historical label).*

---

## Core Privacy Principles

Logan's privacy posture flows directly from its business model and values:

1. **User data is never monetized.** Logan does not sell, share, or license user data to third parties.
2. **Linked account data is for intelligence only.** Position data from linked accounts is used exclusively to personalize Logan's intelligence for that user.
3. **No advertising.** Logan does not serve ads. User data is never used for ad targeting.
4. **Privacy is a feature, not a checkbox.** The privacy model is a selling point — users share sensitive financial context with Logan only because they trust it will never be misused.
5. **User controls are real.** Opt-in means opt-in. Deletion means deletion. These are not dark patterns.

For the complete statement of privacy values, see Principle 11 in `20_LOGAN_PRINCIPLES.md`.

---

## Data Classification

| Data Type | Sensitivity | Retention | Sharing |
|-----------|-------------|-----------|---------|
| Account positions (from Plaid) | HIGH | Session + 90-day history | Never |
| Bet/trade history (from linked accounts) | HIGH | Session + 90-day history | Never |
| User behavioral patterns | MEDIUM | Rolling 90-day window | Never |
| Opportunity engagement history | MEDIUM | 1 year | Never (aggregate analytics only) |
| User interest weights | MEDIUM | Retained; user-deletable | Never |
| Pipeline execution metrics | LOW | 30-day rolling | Aggregate, anonymized only |
| User email/identity | MEDIUM | Account lifetime | Never |
| TriggerEvent performance data (per user) | LOW | Rolling 90-day window | Aggregate, anonymized only |
| Cross-domain data associations (opt-in only) | MEDIUM | While opt-in is active; deleted on revoke | Never |

**Note on cross-domain data:** When a user links accounts across multiple domains (e.g., brokerage + prediction market), Logan may associate positions across those domains to surface cross-domain intelligence. This association is **opt-in only** and explained plainly during onboarding. See User Controls section below.

---

## User Controls

### Opt-In Controls

Users must actively opt in to the following; no data association occurs without explicit confirmation:

| Control | Description | Default |
|---------|-------------|---------|
| **Account linking** | Link brokerage, prediction market, or bank accounts | Off — user initiates |
| **Cross-domain data association** | Logan may associate your positions across linked accounts to surface cross-domain opportunities | Off — explained and confirmed at linking |
| **Behavioral pattern learning** | Logan observes your engagement to improve personalization | On (core product feature) — may be disabled |
| **Domain intelligence** | Receive intelligence for specific domains (e.g., Sports, Culture) | Off for new domains — user enables per domain |

**Each domain toggle is independent.** A user who links a brokerage account but disables Sports intelligence will not receive sports-related opportunities. Domain toggles are accessible at Settings → Intelligence → Domains.

### Account Disconnect and Data Deletion

When a user disconnects a linked account:
1. The linked account token is revoked immediately via the provider (Plaid, Kalshi OAuth, etc.)
2. Position data pulled from that account is deleted within 24 hours
3. Cross-domain associations derived from that account are removed within 24 hours
4. Engagement history referencing that account's data is anonymized (not deleted, unless user requests full deletion)
5. Logan's personalization for that domain degrades gracefully — it no longer has position data but retains domain interest weights

**The user does not lose their full history when disconnecting one account.** Only data sourced from that specific account is affected.

When a user fully deletes their account:
1. All linked account tokens revoked immediately
2. User Model deleted within 24 hours
3. Behavioral history deleted within 30 days
4. Engagement history anonymized (retained for aggregate analytics) or deleted on request
5. Confirmation email sent

Users may request full data deletion beyond these defaults. Logan does not hold data hostage to functionality.

---

## Authentication and Authorization

**JWT-based auth:**
- Access tokens: 15-minute lifetime, RS256 signed
- Refresh tokens: 30-day lifetime, single-use (rotate on refresh)
- All tokens user-scoped — no cross-user token reuse possible

**Account linking:**
- Brokerage credentials: handled entirely by Plaid (Logan never receives raw credentials)
- Prediction market OAuth: standard OAuth 2.0 flow; Logan stores access token, not credentials
- Tokens stored encrypted at rest
- Revocable by user at any time; revocation propagated immediately

---

## Data Encryption

| Layer | Encryption |
|-------|-----------|
| Data in transit | TLS 1.3 required (no TLS 1.2) |
| Data at rest | AES-256 (database encryption at storage layer) |
| Linked account tokens | Encrypted at application layer before database storage |
| User behavioral data | Encrypted at rest |
| Backup data | Encrypted; access-controlled |

---

## User Rights (GDPR / CCPA-aligned)

| Right | Implementation |
|-------|---------------|
| **Access** | User can request export of all their data |
| **Deletion** | User can delete account; all data purged within 30 days. User may also request deletion of specific data categories without full account deletion. |
| **Correction** | User can correct explicit corrections (stored in User Memory) |
| **Portability** | User can export memory and engagement history as JSON |
| **Opt-out** | User can unlink any account at any time; user can disable any domain or cross-domain association |

---

## Consent and Transparency

**On first use:**
- Clear explanation of what Logan reads from linked accounts
- Explicit confirmation before any account is linked
- Explicit confirmation before cross-domain data association is enabled
- Plain-language description of how behavioral data is used

**Ongoing:**
- User can view what data Logan has collected about them (Settings → Privacy → My Data)
- User can see what accounts are linked and what data was read
- User can clear their behavioral history without deleting their account
- User can see which domains have intelligence enabled and toggle them

**Logan never makes cross-domain inferences using linked account data without the user explicitly opting in to cross-domain association.** If a user links a brokerage account but does not enable cross-domain association, Logan uses that account for personalization within the Stocks domain only — it does not associate those positions with the user's prediction market contracts.

---

## Advisory-Only Disclaimer Requirements

**Every Opportunity Card must display:**
> "Logan provides intelligence analysis only. This is not financial, investment, gambling, or legal advice. Always verify information before making any financial decision. Past signal accuracy does not guarantee future results."

**Onboarding must clearly state:**
> "Logan is an intelligence advisor. It never places trades, bets, or orders on your behalf. You always execute in your own apps. Logan reads your accounts to personalize its intelligence — it never writes to your accounts."

These disclaimers are non-negotiable. See `20_LOGAN_PRINCIPLES.md` (Principle 1: Logan informs. The user decides.) and `22_OPPORTUNITY_CARD_SPEC.md` (Section 16: Required Disclaimer).

---

## Gambling Compliance

Sports betting and prediction market intelligence creates regulatory exposure.

**Required controls:**
- Responsible gambling disclosure in onboarding
- "Set a limit" prompt after N opportunities acted on in betting domains
- Ability to restrict betting domain intelligence from Logan's outputs
- No content targeting users under 18 (age verification on account creation)
- Jurisdiction awareness: certain jurisdictions prohibit sports betting apps entirely

**Jurisdiction blocking (V1 minimum):**
- Countries/states where sports betting is fully prohibited: block sports domain receptor output for those users
- Implementation: user location at account creation; IP verification

---

## Operational Security

**Infrastructure:**
- No direct database access from public internet
- API layer is the only public-facing surface
- Internal services communicate over private network
- Secrets management: environment variables from secrets manager (not hardcoded)
- Production credentials never in source code or documentation

**Incident response (planned):**
- Data breach notification: within 72 hours of discovery (GDPR requirement)
- User notification: within 7 days if personal data affected
- Post-incident review required before resuming affected service

---

## Compliance Status (V1)

| Regulation | Status | Notes |
|-----------|--------|-------|
| GDPR (EU) | PLANNED | Required before EU launch |
| CCPA (California) | PLANNED | Required for California users |
| FINRA/SEC (US financial advice) | PROVISIONAL — advisory only | Advisory-only posture avoids most obligations; legal review required |
| State gambling regulations | RESEARCH REQUIRED | Varies significantly by state |
| App Store privacy policies | PLANNED | Required before submission |

**Before any public launch, conduct a formal legal review of:**
1. Whether Logan's output constitutes "financial advice" under relevant regulations
2. Gambling regulations in target launch markets
3. GDPR/CCPA compliance for data handling practices
4. Cross-domain data association disclosures and consent requirements

---

*Logan Intelligence Security, Privacy & Compliance — v3.1.2 | 2026-08-03*
*v3.1.2 changes: User Controls section added: opt-in controls table (account linking, cross-domain association, behavioral learning, domain toggles); account disconnect data deletion procedure added; cross-domain data deletion behavior documented. Data Classification table expanded: TriggerEvent performance data row added; cross-domain data associations row added. Principle 5 added to Core Privacy Principles: user controls are real. Cross-domain association consent and transparency language added to Consent and Transparency section. Compliance Status legal review item 4 added (cross-domain association disclosures). Version updated to 3.1.2.*
