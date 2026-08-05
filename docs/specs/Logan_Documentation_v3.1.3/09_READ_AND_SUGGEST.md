# Logan Intelligence — Read & Suggest
**Version:** 3.1.3
*Source: Architecture v1.3 FINAL (2026-07-31). Original: “source_material/09_READ_AND_SUGGEST.md” (historical label).*

---

## Overview

Read & Suggest is Logan's account intelligence feature. It allows users to securely connect their financial and betting accounts so Logan can analyze their actual positions, exposure, and behavioral patterns — and provide personalized intelligence that no generic app could offer.

**The core philosophy:**
> Logan reads. Logan recommends. The user executes.

Logan is read-only. It never places trades, bets, or orders. Execution always happens in the original linked application. **This is LOCKED and not subject to revision in V1.**

---

## Why This Feature Matters

Most intelligence products work with public data only. They tell you what's happening in the world, but they don't know what you own.

Read & Suggest is what makes Logan's intelligence genuinely personal.

Without it: Logan surfaces what's interesting to the world.
With it: Logan surfaces what matters to *you*, given what you actually hold.

**The difference in practice:**
- Without Read & Suggest: "NVIDIA is up 4% on strong earnings."
- With Read & Suggest: "NVIDIA is up 4%. You have indirect exposure through three positions. Combined with your existing concentration, your AI-sector exposure is now above your historical comfort threshold."

---

## Supported Account Types

### V1

| Account Type | Examples | Data Logan reads |
|---|---|---|
| Brokerage | Robinhood, Fidelity, Schwab, E*TRADE, Alpaca | Positions, cost basis, transaction history, cash balance |
| Prediction Markets | Kalshi, Polymarket | Open positions, closed positions, P&L history |

### V2 (deferred)
- Sports betting direct linking (DraftKings, FanDuel, BetMGM, Caesars) — platform API availability dependent
- Banking accounts (Plaid) for broader financial picture
- Crypto exchanges (Coinbase, Kraken)
- Additional betting platforms

---

## Account Linking

Account linking is handled via OAuth where available, or Plaid for brokerage accounts.

**Logan never stores raw credentials.** The flow:
1. User initiates link in Settings
2. User authenticates directly with the institution (OAuth / Plaid)
3. Institution returns a read-only access token
4. Logan stores the token, not the credentials
5. Token is used for periodic data refresh

**Data refresh frequency (V1 defaults):**
- Brokerage positions: every 15 minutes during market hours, hourly otherwise
- Prediction markets: every 10 minutes

---

## What Logan Analyzes

### Portfolio Intelligence

**Concentration analysis**
Logan maps every position to its underlying themes, sectors, and correlated exposures — not just the surface ticker.

Example: A user who owns NVIDIA stock, an AI ETF, and Microsoft may think they have three different positions. Logan recognizes that all three carry significant AI infrastructure exposure. The actual concentration is higher than it appears.

Output: "42% of your portfolio is indirectly exposed to AI-sector performance across three positions."

**Upcoming catalysts**
Logan cross-references holdings against the event calendar. Earnings, Fed meetings, CPI releases, regulatory decisions — anything that could affect positions is surfaced with context.

Output: "Two of your holdings have earnings within the next 5 days."

**Behavioral patterns**
Over time, Logan learns how this user actually performs across asset classes and strategies.

Patterns Logan discovers:
- "Your long-term technology holdings have outperformed your short-term trades by 34%."
- "You tend to sell within 72 hours of a large gain — often before the full move completes."
- "Your average hold time for losers is 3× longer than for winners."

---

### Betting Intelligence (V2 — deferred until platform API access confirmed)

*Sports betting direct linking is deferred to V2 due to platform API availability. The analysis capabilities below are designed and ready; they activate once account linking is available.*

**Active bet review**
Logan reviews open bets for:
- Exposure concentration (multiple bets on correlated outcomes)
- Conflicts with financial positions (betting against something you own)
- Timing awareness (catalyst events that could affect outcomes)

**Historical pattern analysis**
Logan reviews settled bet history to identify performance patterns:

| Pattern | Example output |
|---|---|
| Sport-specific | "You've won 71% of MLB bets vs. 44% of NFL bets over 90 days." |
| Bet type | "Your moneyline bets outperform your spread bets by 19%." |
| Timing | "Your bets placed more than 24 hours in advance have a 12% higher win rate." |
| Bankroll | "You've recovered your largest single-day losses 78% of the time within 48 hours." |

---

### Cross-Domain Intelligence

This is Logan's unique capability. No single app sees across all your accounts simultaneously.

**Cross-platform conflict detection:**

> *"You're long Tesla stock in your brokerage. You have an active prediction market position that EV adoption will slow in 2026. These positions may conflict — is the divergence intentional?"*

> *"Your current prediction market positions and your stock portfolio both depend significantly on the Federal Reserve not cutting rates aggressively. A surprise rate cut could affect both simultaneously."*

**Correlated exposure discovery:**
Logan surfaces hidden correlations the user would never notice across fragmented apps.

---

## Read & Suggest Feedback Feature

The feedback feature provides direct, personalized analysis on demand or when Logan detects something worth surfacing.

### Feedback types

| Category | Description | Example |
|---|---|---|
| Concentration Risk | User is more concentrated than they realize | "42% of your portfolio is tied to AI across 3 positions." |
| Behavioral Pattern | Logan has detected a consistent decision pattern | "Your best decisions are long-term technology investments." |
| Cross-Platform Conflict | Positions across apps create an unintended conflict | "Your prediction position and your stock position are both bearish on the same event." |
| Upcoming Catalyst | Event scheduled that affects multiple positions | "An event affecting 2 holdings is scheduled this week." |
| Opportunity Alignment | Current opportunity matches user's historical success pattern | "This fits the pattern where you've performed best historically." |
| Behavioral Warning | Current action resembles a historically poor decision pattern | "You've underperformed when chasing momentum moves in the first hour of market open. This matches that pattern." |

---

## User Controls

Users have full control over how their account data is used within Logan.

**Opt-in controls (per account type):**
- **Personal finance data in investing recommendations** — opt-in required before Logan uses brokerage behavioral patterns to influence opportunity relevance scoring. Off by default.
- **Betting activity in other recommendations** — opt-in required before Logan uses betting history or active bet exposure to influence non-betting opportunities. Off by default.

**Data management:**
- Users can disconnect any linked account at any time
- Disconnecting an account deletes all data associated with that account from Logan's memory — positions, history, behavioral patterns
- Users can request deletion of all Read & Suggest data without disconnecting accounts
- Deletion is immediate and permanent

These controls are defined in full in `27_SECURITY_PRIVACY_COMPLIANCE.md`.

---

## Read-Only Philosophy

Logan's read-only stance is not a technical limitation. It is a deliberate product and regulatory decision.

**Why read-only:**
1. **User control** — Logan informs. The user decides. Taking action on someone's behalf is a different product with different risks.
2. **Regulatory simplicity** — Read-only advisory products have significantly simpler regulatory requirements than execution platforms.
3. **Trust** — Users need to trust Logan's intelligence before they would trust it to act. Advisory first builds that trust.
4. **V1 scope** — The intelligence layer needs to prove its value before adding execution complexity.

The user always executes in the original app. Logan opens the door; the user walks through it.

**LOCKED: Logan never executes. Logan never places trades, bets, or orders on behalf of the user. This applies in V1 and all future versions unless an explicit architecture decision is made and documented in `15_DECISIONS.md`.**

---

## Privacy Principles

- Logan reads position data to generate intelligence. It does not share position data with any third party.
- Behavioral patterns are computed per-user and stored only in that user's Memory branch.
- Users can disconnect any linked account at any time — all associated data is deleted.
- Logan never displays raw account credentials, account numbers, or sensitive identifiers.

Full privacy model: `27_SECURITY_PRIVACY_COMPLIANCE.md`.

---

## V1 Build Scope

**Build in V1:**
- Brokerage account linking via Plaid
- Prediction market linking (Kalshi, Polymarket direct API)
- Portfolio concentration analysis
- Behavioral pattern detection (basic — win rates, hold time, asset class performance)
- Cross-domain conflict detection (brokerage + prediction markets)
- Upcoming catalyst cross-reference
- Read & Suggest screen in mobile app (tabs: Portfolio, Predictions, Cross-Domain)
- User opt-in controls for cross-domain data use
- Account disconnect with full data deletion

**Defer to V2:**
- Sports betting direct linking (platform API availability dependent)
- Banking account context
- Advanced behavioral learning (sentiment-based, time-of-day patterns)
- User-controlled feedback on Logan's pattern detection ("that's not right")
- Behavioral pattern export

---

*Logan Intelligence Read & Suggest — v3.1.2 | 2026-08-03*
*v3.1.2 changes: "permanent and non-negotiable" → LOCKED language. Sports betting moved to V2 (deferred). User opt-in controls section added. Data deletion controls added. Privacy model reference added to `27_SECURITY_PRIVACY_COMPLIANCE.md`. Cross-domain examples updated for V1 scope (removed sports betting conflicts).*
