# Logan Intelligence — Product Specification
**Version:** 3.1.3

---

## User Personas

### Persona 1 — The Cross-Platform Investor
**Profile:** 28–45 years old. Has a brokerage account (Robinhood, Fidelity, or Schwab), bets on sports via DraftKings or FanDuel, and occasionally uses prediction markets. Feels like their financial life is fragmented across 5+ apps with no one connecting the dots.

**Pain point:** "I know I'm exposed to AI stocks and I also bet on tech-adjacent things but I have no idea how connected those positions actually are."

**What Logan gives them:** Cross-platform awareness, concentration alerts, behavioral pattern recognition, and a single intelligence layer above all their apps.

---

### Persona 2 — The Prediction Market Participant
**Profile:** 25–40 years old. Actively trades on Kalshi or Polymarket. Analytically minded. Already consumes a lot of information but struggles with signal-to-noise.

**Pain point:** "I spend hours researching before placing a position but I still feel like I'm missing something."

**What Logan gives them:** World model context, weak signal detection, hypothesis-driven analysis, and confidence-calibrated recommendations.

---

### Persona 3 — The Overwhelmed Professional
**Profile:** 30–50 years old. Busy career, some investments, follows sports, wants to be smarter about decisions but doesn't have hours to research.

**Pain point:** "There's too much information and I don't know what actually matters to me."

**What Logan gives them:** Attention-filtered intelligence, calm UI, and only surfaces what genuinely deserves their attention.

---

## Core Workflows

### Workflow 1 — Morning Intelligence Check
1. User opens the app
2. Opportunity Field renders — Logan's current understanding is visible
3. Active opportunities condensed toward center based on priority
4. User taps a node to read the full explanation: what, why, confidence, how long Logan has been watching it
5. User decides to act, save, dismiss, or mark as not relevant
6. Logan learns from the interaction

### Workflow 2 — Account Link & Portfolio Review
1. User links brokerage account
2. Logan analyzes positions, concentration, behavioral patterns
3. Read & Suggest intelligence appears in the Opportunity Field
4. Logan surfaces: concentration risks, cross-platform conflicts, upcoming catalysts
5. User reviews personalized analysis
6. Execution remains in original linked app

### Workflow 3 — Opportunity Deep Dive
1. User taps high-conviction node in Opportunity Field
2. Full detail card opens: headline, what happened, why it matters, why it matters to *them*, supporting and contradicting evidence, timing, action window, how long Logan has been tracking it, confidence breakdown
3. User can expand "reasoning chain" to see full decision trace
4. User can ask "why isn't X on here?" — Logan provides Why Not explanation
5. User can save, dismiss, mark not relevant, act, or remind later

### Workflow 4 — Portfolio Intelligence Review
1. User opens Opportunity Portfolio
2. Sees full tracking state: Watching (N), Detected (N), Emerging (N), etc.
3. Can explore what Logan is monitoring before it surfaces
4. Historical outcomes visible — how accurate Logan's previous calls were

### Workflow 5 — Correction / Thesis Change
1. Logan surfaces a recommendation
2. New evidence changes the underlying event
3. If user already viewed: visible "changed" state on the card
4. If action window changes materially: correction notification sent
5. If user already acted: post-action risk guidance surfaced

---

## User Stories

### Onboarding
- As a new user, I want to understand that Logan will never trade or bet for me — it only advises
- As a new user, I want to link my brokerage account so Logan can personalize its intelligence to my actual positions
- As a new user, I want to set my domains of interest (stocks, sports, crypto, prediction markets, culture, personal finance)
- As a new user, I want to know that Logan doesn't share my data with third parties

### Home Screen / Opportunity Field
- As a user, I want to see what Logan thinks deserves my attention right now, without noise
- As a user, I want to understand *why* something is on the Opportunity Field, not just that it is
- As a user, I want to know how long Logan has been tracking something before it surfaced
- As a user, I want to see confidence levels so I know when Logan is certain vs. still building a picture
- As a user, I want to dismiss something and have Logan learn I'm not interested
- As a user, I want to mark something as not relevant without it affecting my dismissal history for similar items

### Opportunity Card
- As a user, I want to see both supporting and contradicting evidence — not just the bullish case
- As a user, I want to know when an action window opens and when it closes
- As a user, I want to see the sources Logan used, so I can verify them myself
- As a user, I want to know if Logan's recommendation changed because the underlying event changed
- As a user, I want to provide feedback: Acted On, Not Relevant, Dismiss, Save, Remind Later

### Read & Suggest
- As a user, I want Logan to tell me if my positions across apps are more correlated than I realize
- As a user, I want to know if a new opportunity conflicts with something I already have open
- As a user, I want to understand my own behavioral patterns — where I perform well and poorly
- As a user, I want Logan's analysis to stay read-only — I always want to execute in the original app

### Opportunity Portfolio
- As a user, I want to see everything Logan is tracking, not just what it's surfacing
- As a user, I want to know when something is in "Action Window" so I know timing matters
- As a user, I want to review outcomes — how did Logan's past calls work out?

### Intelligence Depth
- As a user, I want to ask "why isn't X on here?" and get an explanation
- As a user, I want to see the reasoning chain behind any recommendation
- As a user, I want Logan to tell me when it doesn't know yet, rather than guessing

---

## Core Screens

### Opportunity Field (Home)
The primary surface. A spatial, radial display of what matters to the user right now.

- Central "L" intelligence core — pulses when Logan is actively reasoning
- Opportunity nodes orbit the center — proximity = importance × user value
- Node size = confidence level
- Node brightness = lifecycle stage (dim outer = Detected, bright inner = High Conviction)
- Node edge glow = trending / community momentum (separate from personal relevance)
- Node pulse animation = Action Window (time-sensitive)
- Ripple = new evidence has just arrived
- Breaking news entry: node appears at field edge and moves inward as evidence builds
- Tap a node = full explanation card
- No list view by default — the field IS the interface
- Calm by default — empty field means nothing deserves attention right now
- Reduced-motion mode: disable continuous drift and ripple animations; retain static positions and brightness
- Accessibility: every node has a text label and VoiceOver/TalkBack description
- Color-independent status: node shape or ring pattern distinguishes domain when color is unavailable

### Opportunity Detail Card
Opens from any node tap. Rises from the tapped node — 350ms ease-out-back. Field dims (does not hide) in background.

See `22_OPPORTUNITY_CARD_SPEC.md` for the complete field-by-field specification.

Fields:
- Domain badge, lifecycle stage, confidence pill
- Headline (max 80 chars)
- Why it matters to me (personalized first — always)
- What happened (triggering event, objective)
- Why now (timing context, action-window countdown)
- Supporting evidence (source-linked, verified)
- Contradicting evidence (explicitly shown — not hidden)
- Sources and citations
- How long Logan has been watching
- Action-window start and expiration
- Current user exposure
- Related exposure in other domains
- Invalidation conditions
- Suggested next step
- External parent-app execution link (blocked if legal/geographic restriction applies)
- Lifecycle stage indicator
- Trending/community indicator (visually distinct from personal relevance)
- Risk and uncertainty disclosure
- Confidence bar + raised_by + limited_by
- Hit Quality score (objective)
- User Value score (personalized)
- Full reasoning chain (expandable)
- Connected items (expandable)
- Save / Watch
- Dismiss
- Not relevant
- Remind later
- Already acted
- Feedback / correction controls
- Required disclaimer

**Disclaimer (required on every card):**
> "Logan provides intelligence analysis only. This is not financial, investment, gambling, or legal advice. Always verify information before making any financial decision. Past signal accuracy does not guarantee future results."

### Opportunity Portfolio
The full tracking view. Accessible from the main field.

Sections:
- Watching (count)
- Detected (entity list)
- Emerging (entity list + brief summary)
- Building Conviction (entity list + hypothesis summary)
- High Conviction (full detail)
- Action Window (time context + countdown)
- Recent Outcomes (last 30 days)

### Read & Suggest
Account intelligence hub.

Tabs:
- Portfolio Overview (concentration, exposure breakdown)
- Bet Review (active bets, win/loss patterns by category)
- Prediction Review (open positions, market context)
- Cross-Domain (conflicts, correlated exposures, behavioral patterns)
- Behavioral Insights (Logan's learned patterns about this user)

### Settings / Profile
- Linked accounts management
- Domain settings (enabled/disabled per domain)
- Followed entities
- Notification threshold (how certain does Logan need to be before pushing?)
- Quiet hours
- Risk limits
- Behavioral warnings on/off
- Cross-domain analysis on/off
- Use of personal-finance data in investing recommendations (opt-in)
- Use of betting activity in other recommendations (opt-in)
- Sensitive-data permissions
- Trending visibility
- Explanation depth preference (brief vs. detailed)
- Reminder behavior
- Privacy — My Data (view what Logan has collected)
- Data export
- Data deletion
- Trigger correction / dispute

---

## Advisory-Only Requirement

**LOCKED for the current implementation cycle.**

Logan never places trades, bets, orders, or any transaction in any system. It is an analysis and advisory tool.

Onboarding must clearly state:
> "Logan is an intelligence advisor. It never places trades, bets, or orders on your behalf. You always execute in your own apps. Logan reads your accounts to personalize its intelligence — it never writes to your accounts."

Every Opportunity Card must display the required disclaimer.

Execution links open the user's linked app — they do not execute anything within Logan.

---

## Future Modules (not in V1)

- **Projects** — Career, real estate, business decisions with persistent memory and AI analysis
- **Intelligence Feed** — Browsable context without the Opportunity Field pressure
- **Expert Workspace** — Structured analysis templates Logan can learn from
- **Chat** — Direct conversation with Logan's reasoning layer
- **Enterprise** — Company-licensed version with shared intelligence and team memory
- **Hardware** — Ambient intelligence device (long-term vision)

---

*Logan Intelligence Product Specification — v3.1.2 | 2026-08-03*
*v3.1.2 changes: Workflow 5 (correction) added. Card fields expanded to full set per brief section 9. User controls section added. Advisory-only section formalized. Opportunity Field UI contract added. Branding clarified.*
