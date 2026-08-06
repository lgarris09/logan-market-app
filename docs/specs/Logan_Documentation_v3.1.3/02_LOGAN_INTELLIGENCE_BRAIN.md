# Logan Intelligence Brain v2.0
### The Cognitive Architecture Behind Logan Intelligence
*Canonical Reference Document — All development must align with this specification*
**Version:** 3.1.3

---

## Core Philosophy

### Mission

Logan exists to transform overwhelming information into personalized intelligence.

It does not simply answer questions. It continuously reasons about:

- The world
- The user's goals
- Confidence
- Relationships
- Opportunities

…and determines: **What deserves the user's attention right now.**

---

### Fundamental Principles

**1. Logan informs. The user decides.**
Logan never assumes control of money, bets, or decisions. It recommends. The user executes — always in the original linked application. This is **LOCKED** for the current implementation cycle.

**2. Everything is connected.**
News. Markets. Sports. Politics. Economics. Social sentiment. Personal goals. Everything influences everything else. The brain exists to discover those relationships.

**3. Intelligence is continuous.**
Logan never stops reasoning. The UI is only a snapshot of what the intelligence layer is currently thinking.

**4. Personalized, not generic.**
Logan doesn't surface what's interesting to everyone. It surfaces what's relevant to *this* user, given their history, goals, and current exposure.

**5. Explainability is required.**
Every opportunity, suggestion, or recommendation must be traceable to a reason. Logan never says "you should do this" without explaining why.

---

## Cognitive Pipeline

```
External World
      │
      ▼
Domain Receptors  ──→  TriggerEvent emitted on signal arrival (SPECIFIED — NOT IMPLEMENTED, V3.1.4 BATCH-3 / OD-009)
      │
      ▼
Normalization
      │
      ▼
World Model
      │
 ┌────┼────────────┐
 ▼    ▼            ▼
Evidence Trust   Community Intelligence   Hit Detection
      │
      ▼
Domain Analysis
      │
      ▼
Memory
      │
 ┌────┴────┐
 ▼         ▼
User Model   Active Context
      │
      ▼
Reasoning Engine
      │
      ▼
Hypothesis Engine
      │
      ▼
Mental Model Engine
      │
      ▼
Conclusion Confidence
      │
      ▼
Opportunity Engine
      │
      ▼
Policy Layer
      │
      ▼
Attention Engine
      │
      ▼
Presentation
      │
      ▼
Feedback
      │
      ▼
Learning
```

---

## Layer Specifications

### Domain Receptors
**What it does:** Collects structured and unstructured information from every connected source.

**Inputs:**
- Brokerage accounts (positions, history, performance)
- Sportsbooks (active bets, settled bets, history)
- Prediction markets (open positions, resolved markets)
- News feeds and media
- Social media signals
- Economic calendars
- Earnings reports and announcements
- Music and culture streams
- Personal finance feeds
- User-linked services

**Output:** RawSignal — raw, unprocessed signals for normalization. On structured event detection, a TriggerEvent is *specified* to be emitted as a first-class pipeline object; this is design-only and not implemented in `logan_core/` as of V3.1.4 (SPECIFIED — NOT IMPLEMENTED, V3.1.4 BATCH-3 / OD-009). See `TRIGGER_EVENT_FRAMEWORK.md` for the TriggerEvent contract and “TRIGGER_REGISTRY_*.md” (historical label) for all domain trigger codes.

---

### Normalization
**What it does:** Converts every source into a common internal language Logan can reason about.

**Responsibility:** Strips format differences, resolves ambiguities, timestamps everything, and tags domain context.

---

### World Model
**What it does:** Builds a continuously updated representation of reality — independent of the user.

**Key point:** Nothing at this layer is personalized yet. This is ground truth about the world.

---

### Evidence Trust
**What it does:** Evaluates the credibility, confidence, corroboration, and source quality of every piece of information before it enters reasoning.

**Outputs a trust score** for each signal. Low-trust signals can still enter the pipeline but are weighted accordingly.

---

### Community Intelligence
**What it does:** Tracks crowd attention, momentum, sentiment, and unusual activity.

Answers: *What is the broader market / community paying attention to right now?*

**Important distinction:** Community momentum is a separate signal from personal relevance. The UI must render them visually distinct — a node's edge glow reflects community momentum; its brightness and proximity reflect personal relevance. Never conflate them. See `11_UI_PHILOSOPHY.md`.

---

### Hit Detection
**What it does:** Detects meaningful changes that warrant attention.

All four detectors (Convergence, Divergence, Pattern Engine, ODSE) produce `OpportunityEvidence` — the same shape for all. Every detector is *specified* to also emit a `TriggerEvent` whenever a structured trigger code fires; this is design-only and not implemented in `logan_core/` as of V3.1.4 (SPECIFIED — NOT IMPLEMENTED, V3.1.4 BATCH-3 / OD-009). See `TRIGGER_EVENT_FRAMEWORK.md`.

**Examples:**
- Breaking news affecting a user's holdings
- Sudden sentiment shifts in a relevant domain
- Major price movement
- New earnings or economic data

---

### Domain Analysis
**What it does:** Creates expert-level understanding inside each knowledge domain (markets, sports, prediction markets, economics, crypto, culture, personal finance).

Translates raw signals into domain-specific meaning before they reach reasoning. Produces objective `hit_quality_score` — same for all users.

---

### Memory
**What it does:** Stores long-term facts, learned relationships, user history, and reasoning history.

**Architecture:**
- Branch-based (not a flat log)
- Importance-ranked (not everything is retained equally)
- Selective (older low-importance memories decay)

**What gets stored:**
- User decision history
- Outcome data (did the opportunity work out?)
- Learned relationships between events and outcomes
- User preferences and patterns

**Write rule (LOCKED):** Only the Learning System may write to Memory. All other layers read.

---

### User Model
**What it does:** Builds and maintains a rich model of the individual user.

**Learns:**
- Interests and domains of focus
- Risk tolerance (inferred from behavior, not just stated preference)
- Decision style (long-term vs. short-term, conservative vs. aggressive)
- Preferred explanation depth
- Long-term objectives
- Behavioral patterns (e.g., sells winners too early, overreacts after losses)

**Key insight:** The User Model is what separates Logan from a generic intelligence product. The same world event produces a different opportunity for different users.

---

### Active Context
**What it does:** Represents the user's *current* situation at the moment of reasoning.

**Includes:**
- Current portfolio positions
- Active bets and open prediction market positions
- Watchlist
- Recent conversations
- Calendar and upcoming events
- Any ongoing tasks or projects the user has shared

---

### Reasoning Engine
**What it does:** Combines everything currently known and finds causal relationships — not isolated facts.

**Key distinction:** Reasoning Engine asks *why* and *so what*, not just *what*.

---

### Hypothesis Engine
**What it does:** Generates multiple candidate explanations for what is happening, then attempts to both confirm and disprove each before advancing.

**Why it exists:** Simple pattern-matching produces confident wrong answers. The Hypothesis Engine introduces structured skepticism — Logan actively looks for evidence that its best hypothesis is wrong before committing to it.

**Output:** A ranked set of hypotheses with supporting and contradicting evidence attached.

---

### Mental Model Engine
**What it does:** Maintains an internal understanding of:
- How markets behave under different conditions
- How this specific user tends to think and decide
- How different domains interact and influence each other

**V1:** Active but limited — captures basic patterns.
**V2+:** Becomes a richer, continuously evolving representation that improves Logan's ability to anticipate what a user will find relevant before they ask.

---

### Conclusion Confidence
**What it does:** Assigns calibrated confidence scores to every conclusion.

**LOCKED:** Logan never treats all conclusions equally. Every output is tagged with a confidence level, and that confidence is shown to the user. Logan does not pretend to be certain when it isn't.

The `i_dont_know_yet` flag is set when evidence is genuinely insufficient. Logan never fabricates confidence.

---

### Opportunity Engine
**What it does:** Produces actionable, personalized opportunities.

**Not alerts. Not headlines. Actual opportunities.**

An opportunity is defined as: *Something this specific user should consider acting on, given everything Logan knows about them and the world right now.*

**Scores separately:**
- `hit_quality_score` — objective, same for all users
- `user_value_score` — personalized to this user's model

**Examples of what an opportunity is NOT:**
- "NVIDIA is up 3% today." (That's news.)
- "The Fed meeting is this week." (That's a calendar.)

**Examples of what an opportunity IS:**
- "You have significant indirect AI exposure through three positions. NVIDIA's move today increases your concentration risk above your historical comfort threshold."
- "You've won 8 of your last 10 MLB bets. There's a high-confidence matchup tonight that fits your pattern."

---

### Policy Layer
**What it does:** Applies safety constraints, legal requirements, user-defined preferences, and explanation requirements before anything reaches the user.

**Enforces:**
- No recommendations to execute trades or place bets directly
- Jurisdiction-appropriate language around financial and betting content
- User-set content filters
- Geographic/legal restrictions on external execution links
- Minimum explanation depth requirements

---

### Attention Engine
**What it does:** Determines what deserves the user's attention, how urgent it is, and when to surface it.

**Drives the atmospheric UI** — rather than a notification list, the Attention Engine determines how the visual field condenses around high-priority intelligence.

**Manages:**
- Notification eligibility (see `NOTIFICATION_POLICY.md` for rules)
- Cooldown states
- Attention fatigue protection

---

### Presentation
**What it does:** Transforms intelligence into experience.

The atmosphere represents Logan's current understanding. As confidence and importance increase, intelligence naturally condenses into focus. No traditional dashboard required.

**Design principles:**
- Calm by default
- Surfaces only what deserves attention
- Explainable — every surfaced item can be expanded to show reasoning
- Beautiful

**Correction handling:** If new evidence materially changes an item after delivery:
- If user viewed but didn't act: update the card, show "Updated" state
- If action window changes materially: re-eligible for notification with correction flag
- If user already acted: surface post-action risk guidance

---

### Feedback
**What it does:** Measures user interaction, ignored opportunities, accepted suggestions, and — over time — outcome quality.

**Captures:**
- Which opportunities the user acted on (Acted On)
- Which opportunities were dismissed (Dismiss)
- Not relevant (signals this topic class is not interesting)
- Save / Watch (positive engagement without action)
- Remind later
- Duration of engagement

---

### Learning
**What it does:** Updates the User Model, confidence calibration, memory, and reasoning strategies based on feedback.

This is what makes Logan smarter over time — not just about the world, but about this specific user.

**LOCKED:** Learning System is the only layer permitted to write to Memory.

---

## Read & Suggest

### Overview

Read & Suggest is a core Logan feature that connects personal financial and betting accounts to the intelligence pipeline. It gives Logan the context needed to produce *genuinely personalized* intelligence rather than generic recommendations.

### Linked Account Types (V1)

| Account Type | Examples |
|---|---|
| Brokerage | Robinhood, Fidelity, Schwab, E*TRADE |
| Sports Betting | DraftKings, FanDuel, BetMGM, Caesars |
| Prediction Markets | Kalshi, Polymarket, Manifold |
| Banking (future) | Checking, savings — for broader financial picture |

### What Logan Analyzes

**Portfolio Intelligence**
- Current positions and asset allocation
- Concentration by theme, sector, or correlated exposure
- Performance history and behavioral patterns
- Upcoming catalysts (earnings, economic events, news) affecting holdings

**Betting Intelligence**
- Active bets and open prediction market positions
- Win/loss patterns by sport, bet type, or market category
- Exposure overlaps across platforms

**Cross-Market Intelligence**
This is where Logan's value becomes unique. Examples:

> *"You just bet on the Chiefs to win the Super Bowl. You also own DraftKings stock and several sports media holdings that could be affected by the same news cycle."*

> *"You're bullish on Tesla in your brokerage but bearish on EV adoption in a prediction market. These positions may conflict — is that intentional?"*

> *"Most of your current exposure depends on the same AI-growth theme, across three different positions you may not have connected."*

### Read & Suggest Philosophy

**Logan reads. Logan recommends. The user executes.**

- Logan is read-only for the current implementation cycle. **LOCKED.**
- Execution always happens in the original linked application.
- This preserves user control while delivering high-value intelligence.
- V1 is intentionally advisory — the trust and value is established before any deeper integration is considered.

### User Controls

Users control which data Logan uses:
- Each linked account can be disconnected at any time — all associated data deleted
- Opt-in: use of personal-finance data in investing recommendations
- Opt-in: use of betting activity in other domain recommendations
- Behavioral warnings can be disabled
- Cross-domain analysis can be disabled per domain pair

See `01_PRODUCT_SPECIFICATION.md` (Settings / Profile) and `27_SECURITY_PRIVACY_COMPLIANCE.md` for the full privacy model.

---

## Behavioral Learning

Over time, Logan learns how the user makes decisions — not to take over, but to give better advice.

**Patterns Logan discovers:**
- "You hold winners for a long time but sell too early after large gains."
- "Your best investments consistently come from AI and technology."
- "You're more accurate at long-term investing than short-term sports betting."
- "You tend to overreact to losses and make lower-quality decisions in the 48 hours after a significant loss."

**What Logan does with this:**

> *"Based on your history, your highest-confidence decisions have been long-term technology investments. This opportunity is more aligned with that pattern than with your typical short-term trades."*

This is the defining capability: Logan doesn't just answer "What's happening?" — it answers **"Given everything I know about you, here's what I think deserves your attention — and here's why."**

---

## Design Philosophy

### The Attention Field

The interface is not a dashboard. It is a living attention field.

The atmosphere represents Logan's current understanding. As confidence and importance increase, intelligence naturally condenses into the user's focus. Nothing competes for attention unless it deserves it.

### Atmospheric UI Principles

- **Calm by default** — no noise, no unnecessary pings
- **Condensation model** — high-confidence, high-importance intelligence rises naturally
- **Explainable** — every surfaced item expands to show full reasoning
- **Minimal friction** — acting on an opportunity should take as few steps as possible
- **Beautiful** — the experience should feel like a premium intelligence tool

---

## Non-Negotiable Principles (LOCKED)

These cannot be changed without a full architectural review:

1. **Explainable reasoning** — every recommendation has a traceable reason
2. **Personalized intelligence** — generic alerts are not acceptable outputs
3. **User control over execution** — Logan never acts; the user always acts
4. **Continuous learning** — the system must improve over time from feedback
5. **Branch-based memory** — flat logs are not acceptable
6. **Confidence-aware conclusions** — uncertainty is always surfaced, never hidden
7. **Cross-domain reasoning** — siloed domain analysis is not acceptable
8. **Minimal friction** — complexity stays inside the brain, not in the UI
9. **Beautiful, calm presentation** — the experience must match the intelligence quality

---

## What Claude Is Allowed to Improve

- Implementation details within any layer
- Specific algorithms and models
- UI/UX patterns within the Attention Field framework
- Data connectors for new account types
- Feedback loop mechanics
- Memory retrieval and ranking strategies
- TriggerEvent registry entries (adding new triggers within the framework)

## What Must Not Change Without Review

- The core pipeline order
- The principle that Logan is read-only and advisory (LOCKED)
- The Hypothesis Engine's confirm/disconfirm requirement
- The non-negotiable principles above
- The Read & Suggest execution philosophy (Logan reads, user executes)
- The TriggerEvent framework contract (`TRIGGER_EVENT_FRAMEWORK.md`)

---

## Document History

| Version | Date | Summary |
|---|---|---|
| v1.0 | — | Initial brain architecture |
| v1.3 | — | Added Hypothesis Engine, Mental Model Engine, updated pipeline ordering |
| v2.0 | 2026-08-03 | Full canonical rewrite. Added Read & Suggest framework, behavioral learning, cross-market intelligence, feedback feature, attention field design philosophy, implementation rules. |
| v3.1.2 | 2026-08-03 | TriggerEvent framework added. "Permanent" language updated to LOCKED. Community Intelligence / personal relevance distinction clarified. User controls section added. Culture and personal finance domains added to Domain Receptors. Correction handling added to Presentation. |

---

*This document is the single source of truth for Logan's intelligence architecture. All Claude sessions, sprints, and development decisions must align with this specification.*
