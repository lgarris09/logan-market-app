# Logan Intelligence — Security, Privacy & Compliance
**Version:** 3.1.3
*Source: Architecture v1.3 FINAL (2026-07-31). Original: “source_material/27_SECURITY_PRIVACY_COMPLIANCE.md” (historical label).*

---

## Reading this document (V3.1.4 BATCH-3 rewrite, P0)

The V3.1.4 gap review found this document written entirely in the present/required tense — as if JWT auth,
Plaid integration, encryption at rest, and GDPR/CCPA data-rights flows were built or actively enforced.
**None of that exists in the repository as of V3.1.4.** Every control below is now explicitly tagged with
one of four statuses so a reader can tell what's actually true today from what's aspirational:

| Tag | Meaning |
|-----|---------|
| **CURRENT** | True of the repository right now, verifiable by reading the code. |
| **LOCAL-DEV LIMITATION** | A gap that is acceptable *only* because Logan runs as a single-operator local process today. Not a decision anyone made on purpose — a consequence of not having built the alternative yet. |
| **REQUIRED — TRUSTED ALPHA** | Must exist before Logan is run by anyone other than the single local operator, even a small group of trusted testers. Not built. Auth and multi-user persistence are explicitly excluded from V3.1.4 scope (see `docs/DECISIONS.md` and the V3.1.4 scope notes) — this table exists so the gap is documented, not so it gets built this release. |
| **FUTURE — PRODUCTION** | Required before any public launch (App Store, public URL, real user data at scale). Legal review required regardless of technical readiness. |

Nothing in this document should be read as a claim about what V3.1.4 shipped. See
`23_CURRENT_IMPLEMENTATION_STATE.md` for the verified current state of `logan_core/`, `backend/app/`, and
`mobile/`.

---

## Core Privacy Principles

Logan's privacy posture flows directly from its business model and values — these are commitments the
product intends to honor once built, not a description of enforcement mechanisms that exist today:

1. **User data is never monetized.** Logan does not sell, share, or license user data to third parties. **CURRENT** in the sense that there is no monetization code of any kind; **FUTURE — PRODUCTION** as an enforceable commitment once there is a real business and real user data.
2. **Linked account data is for intelligence only.** **FUTURE — PRODUCTION.** No account linking exists yet (`backend/app/` has no Plaid/OAuth integration; `logan_core/receptors/simulated.py` is the only receptor implementation).
3. **No advertising.** **CURRENT** — there is no ad code, ad SDK, or ad-related data flow anywhere in the repository.
4. **Privacy is a feature, not a checkbox.** Product value statement, not a control — no status tag applies.
5. **User controls are real.** **REQUIRED — TRUSTED ALPHA** and beyond. Today there is exactly one implicit user (`LOCAL_FOUNDER_USER_ID = "demo_user"` in `logan_core/contracts/common.py`); there are no opt-in toggles, no deletion flow, and nothing for a "user control" to act on yet.

For the complete statement of privacy values, see Principle 11 in `20_LOGAN_PRINCIPLES.md`.

---

## Current State (V3.1.4) — what's actually true today

- **CURRENT:** Logan runs as a single local process on the operator's machine. `logan_core`'s
  `MemoryRecord.user_id` and `ActiveContext.user_id` (ADR-033, V3.1.4 BATCH-2) are required, non-empty
  fields — but the only value ever supplied in this codebase is the hardcoded `LOCAL_FOUNDER_USER_ID`
  constant. There is no login, no session, no per-user isolation enforced beyond that constant string
  matching itself, and no way for a second distinct user to exist.
- **CURRENT:** `backend/app/`'s SQLite database (`logan_memory.db`) is a local file with OS-level
  filesystem permissions only — no database-level access control, no encryption at rest, no network
  exposure by default (it isn't reachable unless something binds the backend to a non-localhost address).
- **CURRENT:** No authentication of any kind exists — no JWT, no session cookie, no API key. Any process
  that can reach the local backend port can call it.
- **CURRENT:** No account linking exists (no Plaid, no brokerage/sportsbook/prediction-market OAuth). All
  receptor data is `logan_core/receptors/simulated.py` — synthetic, not real user financial data.
- **CURRENT:** No encryption in transit is configured (local HTTP, not TLS) and none is needed for a
  process talking to itself on localhost — but this must not be mistaken for a TLS decision made for a
  networked deployment.
- **LOCAL-DEV LIMITATION:** All of the above are acceptable *only* because the intended device-validation
  target for V3.1.4 (Apple-signed iOS development build, per the mobile deployment clarification) still
  talks to a backend the operator runs and controls directly — it is not a publicly reachable service.
  Treating any of this as a security posture for a shared or public deployment would be a mistake.

---

## Data Classification (target design — FUTURE, mixed REQUIRED — TRUSTED ALPHA / PRODUCTION)

The table below is the target design for when Logan has real linked-account data and more than one user.
None of these retention/sharing rules are implemented — there is no retention job, no deletion job, and no
per-category data store distinct from the single local SQLite file today.

| Data Type | Sensitivity | Target Retention | Target Sharing | Status |
|-----------|-------------|-----------|---------|--------|
| Account positions (from Plaid) | HIGH | Session + 90-day history | Never | FUTURE — no Plaid integration exists |
| Bet/trade history (from linked accounts) | HIGH | Session + 90-day history | Never | FUTURE — no linked accounts exist |
| User behavioral patterns | MEDIUM | Rolling 90-day window | Never | REQUIRED — TRUSTED ALPHA — no retention/expiry job exists; memory records persist indefinitely in local SQLite today |
| Opportunity engagement history | MEDIUM | 1 year | Never (aggregate analytics only) | FUTURE — no analytics pipeline exists |
| User interest weights | MEDIUM | Retained; user-deletable | Never | REQUIRED — TRUSTED ALPHA — no deletion mechanism exists |
| Pipeline execution metrics | LOW | 30-day rolling | Aggregate, anonymized only | FUTURE |
| User email/identity | MEDIUM | Account lifetime | Never | FUTURE — no identity/auth system exists |
| TriggerEvent performance data (per user) | LOW | Rolling 90-day window | Aggregate, anonymized only | Doubly future: depends on TriggerEvent itself, which is SPECIFIED — NOT IMPLEMENTED (OD-009) |
| Cross-domain data associations (opt-in only) | MEDIUM | While opt-in is active; deleted on revoke | Never | FUTURE — no cross-domain association mechanism, opt-in or otherwise, exists |

**Note on cross-domain data:** When a user links accounts across multiple domains (e.g., brokerage +
prediction market), Logan may associate positions across those domains to surface cross-domain
intelligence. This association is designed to be **opt-in only**. None of this exists yet — see User
Controls below.

---

## User Controls (target design — FUTURE / REQUIRED — TRUSTED ALPHA)

### Opt-In Controls (target design, not built)

None of the controls in this table exist as UI, API, or data-model concepts today. They describe the
target design for when Logan supports more than the single local operator.

| Control | Description | Default | Status |
|---------|-------------|---------|--------|
| **Account linking** | Link brokerage, prediction market, or bank accounts | Off — user initiates | FUTURE |
| **Cross-domain data association** | Logan may associate your positions across linked accounts to surface cross-domain opportunities | Off — explained and confirmed at linking | FUTURE |
| **Behavioral pattern learning** | Logan observes your engagement to improve personalization | On (core product feature) — may be disabled | REQUIRED — TRUSTED ALPHA (the learning itself is partially built; the ability to disable it is not) |
| **Domain intelligence** | Receive intelligence for specific domains (e.g., Sports, Culture) | Off for new domains — user enables per domain | FUTURE |

**Each domain toggle is independent** in the target design. Not built.

### Account Disconnect and Data Deletion (target design, not built)

No account linking exists, so there is nothing to disconnect. No deletion flow exists — a
`logan_memory.db` file can only be deleted manually by the operator today, which is not a substitute for a
real deletion flow once real user data exists. The step-by-step procedures below (token revocation, 24-hour
deletion windows, anonymization) are the target design for **REQUIRED — TRUSTED ALPHA** and beyond, carried
forward unmodified from the prior version of this document as the intended shape — not as evidence they
exist:

1. The linked account token is revoked immediately via the provider (Plaid, Kalshi OAuth, etc.)
2. Position data pulled from that account is deleted within 24 hours
3. Cross-domain associations derived from that account are removed within 24 hours
4. Engagement history referencing that account's data is anonymized (not deleted, unless user requests full deletion)
5. Logan's personalization for that domain degrades gracefully — it no longer has position data but retains domain interest weights

When a user fully deletes their account (target design):
1. All linked account tokens revoked immediately
2. User Model deleted within 24 hours
3. Behavioral history deleted within 30 days
4. Engagement history anonymized (retained for aggregate analytics) or deleted on request
5. Confirmation email sent

---

## Authentication and Authorization — REQUIRED — TRUSTED ALPHA, not built

**CURRENT: none of this exists.** There is no JWT issuance, no token store, no refresh flow, and no
account-linking credential handling anywhere in `logan_core/` or `backend/app/`. Auth is explicitly
excluded from V3.1.4 scope. The design below is preserved as the target shape for when auth work begins —
implementing it is a dedicated future pass, not an incidental V3.1.4 change:

**Target: JWT-based auth:**
- Access tokens: 15-minute lifetime, RS256 signed
- Refresh tokens: 30-day lifetime, single-use (rotate on refresh)
- All tokens user-scoped — no cross-user token reuse possible

**Target: Account linking:**
- Brokerage credentials: handled entirely by Plaid (Logan never receives raw credentials)
- Prediction market OAuth: standard OAuth 2.0 flow; Logan stores access token, not credentials
- Tokens stored encrypted at rest
- Revocable by user at any time; revocation propagated immediately

---

## Data Encryption — target design, not built

**CURRENT:** the local SQLite file has no application-layer or database-layer encryption; there is no TLS
because there is no network-facing deployment. Both are appropriate for a single-operator local process
and inappropriate the moment this runs anywhere else, which is why every row below is at minimum
**REQUIRED — TRUSTED ALPHA**.

| Layer | Target Encryption | Status |
|-------|-----------|--------|
| Data in transit | TLS 1.3 required (no TLS 1.2) | REQUIRED — TRUSTED ALPHA (once networked) |
| Data at rest | AES-256 (database encryption at storage layer) | REQUIRED — TRUSTED ALPHA |
| Linked account tokens | Encrypted at application layer before database storage | FUTURE (depends on account linking existing at all) |
| User behavioral data | Encrypted at rest | REQUIRED — TRUSTED ALPHA |
| Backup data | Encrypted; access-controlled | FUTURE — no backup process exists |

---

## User Rights (GDPR / CCPA-aligned) — FUTURE, PRODUCTION

None of these rights have an implementation surface yet — there is no export endpoint, no per-category
deletion, and no correction UI beyond raw memory records. Required before any launch in a jurisdiction
where GDPR/CCPA apply.

| Right | Target Implementation |
|-------|---------------|
| **Access** | User can request export of all their data |
| **Deletion** | User can delete account; all data purged within 30 days. User may also request deletion of specific data categories without full account deletion. |
| **Correction** | User can correct explicit corrections (stored in User Memory) |
| **Portability** | User can export memory and engagement history as JSON |
| **Opt-out** | User can unlink any account at any time; user can disable any domain or cross-domain association |

---

## Consent and Transparency — FUTURE, PRODUCTION

No onboarding flow, account linking, or cross-domain association exists, so none of the consent language
below has anywhere to be shown yet. Preserved as target copy/behavior for when those flows are built:

**On first use (target):**
- Clear explanation of what Logan reads from linked accounts
- Explicit confirmation before any account is linked
- Explicit confirmation before cross-domain data association is enabled
- Plain-language description of how behavioral data is used

**Ongoing (target):**
- User can view what data Logan has collected about them (Settings → Privacy → My Data)
- User can see what accounts are linked and what data was read
- User can clear their behavioral history without deleting their account
- User can see which domains have intelligence enabled and toggle them

---

## Advisory-Only Disclaimer Requirements — CURRENT (product principle, ADR-002/010), UI copy not yet shipped

The advisory-only boundary itself is enforced today at the product-reasoning level (ADR-002, reaffirmed
ADR-010 — see `CLAUDE.md`'s "Product guardrail: analysis, not advice"). The specific disclaimer copy below
has **not** been added to any mobile screen yet — there is no Opportunity Card built to the full
`22_OPPORTUNITY_CARD_SPEC.md`, and no onboarding flow exists at all. Required before any external user
(including trusted alpha testers) sees the app:

**Every Opportunity Card must display (REQUIRED — TRUSTED ALPHA):**
> "Logan provides intelligence analysis only. This is not financial, investment, gambling, or legal advice. Always verify information before making any financial decision. Past signal accuracy does not guarantee future results."

**Onboarding must clearly state (REQUIRED — TRUSTED ALPHA):**
> "Logan is an intelligence advisor. It never places trades, bets, or orders on your behalf. You always execute in your own apps. Logan reads your accounts to personalize its intelligence — it never writes to your accounts."

These disclaimers are non-negotiable once any non-operator sees the product. See `20_LOGAN_PRINCIPLES.md`
(Principle 1: Logan informs. The user decides.) and `22_OPPORTUNITY_CARD_SPEC.md` (Section 16: Required
Disclaimer).

---

## Gambling Compliance — FUTURE, PRODUCTION (partially REQUIRED — TRUSTED ALPHA if Sports/prediction-market content is shown to anyone but the operator)

Sports betting and prediction market intelligence creates regulatory exposure once shown to real users.
The tone requirement (ADR-013 — objective, data-forward, no urgency-driven framing for betting/prediction
content) is a **CURRENT** product-copy rule that already applies to any Sports/prediction-market text
written in this codebase, independent of whether the controls below are built.

**Target controls, not built:**
- Responsible gambling disclosure in onboarding
- "Set a limit" prompt after N opportunities acted on in betting domains
- Ability to restrict betting domain intelligence from Logan's outputs
- No content targeting users under 18 (age verification on account creation)
- Jurisdiction awareness: certain jurisdictions prohibit sports betting apps entirely

**Jurisdiction blocking (V1 minimum, target, not built):**
- Countries/states where sports betting is fully prohibited: block sports domain receptor output for those users
- Implementation: user location at account creation; IP verification

A formal legal/compliance review of the FOMO/tone pattern and gambling exposure remains a required
milestone before any Phase 2 work, per `docs/PRODUCT.md` — it is not treated as settled by this document.

---

## Operational Security — REQUIRED — TRUSTED ALPHA and beyond, not built

**CURRENT:** none of the infrastructure below exists — there is no deployed public-facing API layer, no
private network, no secrets manager. `backend/app/` runs locally with no secrets beyond what's in local
`.env`-style config (never committed — see `CLAUDE.md`'s "no secrets in source control" rule, which *is*
enforced today as a repo hygiene practice, independent of the infrastructure below not existing).

**Target infrastructure:**
- No direct database access from public internet
- API layer is the only public-facing surface
- Internal services communicate over private network
- Secrets management: environment variables from secrets manager (not hardcoded)
- Production credentials never in source code or documentation

**Target incident response (planned, not built):**
- Data breach notification: within 72 hours of discovery (GDPR requirement)
- User notification: within 7 days if personal data affected
- Post-incident review required before resuming affected service

---

## Compliance Status (V1)

| Regulation | Status | Notes |
|-----------|--------|-------|
| GDPR (EU) | PLANNED | Required before EU launch. No implementation started. |
| CCPA (California) | PLANNED | Required for California users. No implementation started. |
| FINRA/SEC (US financial advice) | PROVISIONAL — advisory only | Advisory-only posture avoids most obligations; legal review required. The advisory boundary itself is enforced today at the product-reasoning/copy level (ADR-002/010), independent of the regulatory review status. |
| State gambling regulations | RESEARCH REQUIRED | Varies significantly by state |
| App Store privacy policies | PLANNED | Required before submission — relevant now that V3.1.4 targets an Apple-signed development build and eventual TestFlight/App Store distribution |

**Before any public launch, conduct a formal legal review of:**
1. Whether Logan's output constitutes "financial advice" under relevant regulations
2. Gambling regulations in target launch markets
3. GDPR/CCPA compliance for data handling practices
4. Cross-domain data association disclosures and consent requirements

**Before any trusted-alpha distribution (TestFlight or otherwise) to anyone other than the operator,** at
minimum: ship the advisory-only disclaimer copy above, confirm no real financial credentials can reach the
app (none are wired up as of V3.1.4), and confirm testers understand this is local-dev-grade software with
no auth, no encryption, and no data-deletion guarantees.

---

*Logan Intelligence Security, Privacy & Compliance — v3.1.2 | 2026-08-03*
*v3.1.2 changes: User Controls section added: opt-in controls table (account linking, cross-domain association, behavioral learning, domain toggles); account disconnect data deletion procedure added; cross-domain data deletion behavior documented. Data Classification table expanded: TriggerEvent performance data row added; cross-domain data associations row added. Principle 5 added to Core Privacy Principles: user controls are real. Cross-domain association consent and transparency language added to Consent and Transparency section. Compliance Status legal review item 4 added (cross-domain association disclosures). Version updated to 3.1.2.*
*V3.1.4 BATCH-3 rewrite (2026-08-06, P0 gap-review item): entire document restructured to separate CURRENT / LOCAL-DEV LIMITATION / REQUIRED — TRUSTED ALPHA / FUTURE — PRODUCTION status for every control, principle, and table row. No target-design content was deleted — all prior v3.1.2 language is preserved, now explicitly labeled as target design rather than presented as built or enforced. New "Current State (V3.1.4)" section added describing what is actually true of the repository today (single local operator, no auth, no encryption, no account linking, simulated receptors only).*
