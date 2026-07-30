# Logan — Product Vision

## What Logan is

Logan is an **AI-powered opportunity intelligence platform**. It is not a finance app, not a chatbot, and
not another news aggregator — those are all ways people might initially describe it, and all of them miss
the point.

Logan's purpose is to help people recognize meaningful opportunities earlier, understand why they matter,
and confidently decide how much attention they deserve. It starts in markets, sports, and prediction
markets, and is intended to extend over time into business, technology, careers, and other
opportunity-driven areas. The common thread is always the same: **help users discover opportunities they
would have otherwise missed.**

## Mission

The world produces more information than people can process. The problem isn't finding information — it's
knowing what actually matters. Logan exists to filter the world's noise into personalized opportunities
that are meaningful to each individual user.

Every feature should answer one question: **"What actually matters to me right now?"** If a feature
doesn't improve a user's ability to recognize opportunities or make better decisions, it probably doesn't
belong.

## Core product philosophy

Every engineering and UX decision should reinforce these principles:

- Personalization over generic content.
- Understanding over information overload.
- Trust over engagement.
- Simplicity over unnecessary complexity.
- Long-term maintainability over short-term speed.
- User value over feature count.

The objective is never to display more information. The objective is to display the right information.

## Who it's for

Primary audience: 18-35 year olds motivated by discovering opportunities before everyone else, learning
faster, making smarter decisions, staying ahead of trends, and avoiding the feeling of missing something
important. Logan is built to embrace that motivation without becoming manipulative — see
[FOMO as motivation, not manipulation](#fomo-as-motivation-not-manipulation) below.

Phase 1 target user: an individual who actively follows markets, sports betting, and/or prediction
markets, and wants information filtered and framed around their own positions and interests rather than a
generic feed.

## Product phases

### Phase 1 — Prove the loop (current)
- Free to end users. No monetization work yet. See [ADR-001](DECISIONS.md#adr-001-free-growth-first-mvp-before-monetization).
- Focus: does Logan's reasoning make it feel meaningfully more relevant than a generic feed? Do users
  come back?
- Success looks like: regular return usage, users confirming/correcting memory (signal the trust loop
  works), qualitative feedback that Logan "gets" them.

### Phase 2 — Monetize what's proven
- Introduce a premium tier (advanced personalization, higher usage limits, deeper AI features) once
  Phase 1 validates the core loop.
- Consider affiliate revenue where it fits naturally, subject to applicable rules and disclosures.
- Required gate: a legal/compliance review of Logan's FOMO/urgency messaging patterns against
  gambling-marketing and financial-promotion regulations — see [ADR-013](DECISIONS.md#adr-013-fomourgency-risk-tightened--betting-and-prediction-markets-must-stay-objective).
  Also the point to revisit [ADR-006](DECISIONS.md#adr-006-database-and-hosting--open-decision)
  (hosting/database) and multi-user infrastructure.

### Phase 3 — Expand
- Additional revenue streams and product surface area (business, technology, careers, and other
  opportunity-driven domains), scoped once Phase 1 and 2 have real usage data behind them.

## The analysis-vs-advice boundary

This is the most important product constraint in the codebase, treated as an architectural rule enforced
by the Policy & Safety layer, not just a copywriting guideline. See
[ADR-002](DECISIONS.md#adr-002-logan-personalizes-and-contextualizes--it-does-not-give-directive-advice-phase-1),
reaffirmed by [ADR-010](DECISIONS.md#adr-010-advice-boundary-reaffirmed-against-vision-language-confidently-decide-what-to-do-next).

**Logan determines what deserves attention and explains why. The user makes the final decision.**

| Not this (directive) | This (decision support) |
|---|---|
| "Buy Tesla now." | "Tesla announced an AI partnership. You follow AI stocks and hold Nvidia — this may be relevant to your portfolio." |
| "Bet the under on tonight's game." | "The total moved 4 points since open. You've tracked this market before — here's what changed." |

"Confidently decide what to do next" means deciding **how much attention** something deserves — not what
action to take. Any feature, prompt, or UI copy that starts to read as "you should do X" on a specific
position, trade, or bet is out of bounds without a new ADR that explicitly addresses regulatory
obligations, disclosures, and user-expectation risk. In the architecture, this boundary is the Opportunity
Engine's job to *recommend attention* and the Policy & Safety layer's job to *enforce how that gets said*
— see [ARCHITECTURE.md](ARCHITECTURE.md).

## FOMO as motivation, not manipulation

Logan's primary audience is motivated by discovering opportunities before everyone else, learning faster,
and avoiding the feeling of missing something important. Logan embraces that emotional driver without
becoming manipulative. The target feeling is: **"I'm glad Logan showed me this before everyone else,"**
not "I'm anxious because I missed something." The emotional tone is excitement, curiosity, momentum,
confidence, and discovery — not fear.

**This has a hard boundary, tightened per [ADR-013](DECISIONS.md#adr-013-fomourgency-risk-tightened--betting-and-prediction-markets-must-stay-objective):**
sports betting and prediction-market (Polymarket) content stays **objective and data-forward** — no
urgency-driven or persuasive gambling framing, regardless of how well it might otherwise fit the emotional
tone above. Excitement/curiosity framing remains available for stocks, business, technology, and career
content. This distinction exists because urgency-driven marketing aimed at young adults around gambling
content carries specific regulatory and ethical exposure that the rest of the FOMO design doesn't. A
legal/compliance review of this pattern is a required milestone before Phase 2 (real-user scale), not
optional polish.

## Personalized memory as a reasoning engine

Memory is Logan's greatest competitive advantage — and it is a reasoning engine, not a conversation
history. It continuously learns what users consistently care about, what they ignore, their interests,
reasoning patterns, goals, confidence, changing priorities, and the relationships between ideas over time.
Every interaction should make Logan better at understanding that specific user; the longer someone uses
Logan, the more valuable Logan becomes.

Architecturally, this is the Memory System + User Model + Learning System described in
[ARCHITECTURE.md](ARCHITECTURE.md) — only Learning writes durable memory or user-model updates, so that
Logan's understanding of a person changes deliberately, not from every click.

## Opportunity first

Logan should never feel like a news feed. Every opportunity answers: What changed? Why does it matter?
Why does it matter specifically to this user? What should they pay attention to next? The goal is not
faster news — it's better understanding.

## Information architecture: outside world → living tree → opportunity wheel

The structure of Logan's interface represents how intelligence flows from overwhelming information into
personalized insight:

- **The outside world** — the outer edge represents the world's constant stream of information (market
  news, company announcements, social trends, sports, prediction markets, AI developments, economic news,
  and eventually personal calendars, messages, and connected apps). Most of it is irrelevant to any
  individual user; Logan's job is to determine what deserves attention.
- **The living tree** — internally, new information begins on the outer branches and moves inward as
  Logan evaluates it against memory, interests, historical behavior, holdings, goals, and time
  sensitivity. Some information dies on the branches because it isn't meaningful; other information grows
  stronger as signals reinforce it. This reasoning never stops.
- **The opportunity wheel** — the interface visualizes this reasoning as a living, circular wheel. The
  outside holds the largest volume of information; as Logan becomes more confident something matters to a
  specific user, it moves inward. Nothing is manually organized — the interface continuously reorganizes
  itself based on Logan's reasoning. The center represents "what actually matters to me right now" and
  stays clean — only the highest-value opportunities belong there.
- **Water ripple intelligence** — every meaningful event behaves like a stone dropped in water: a ripple
  expands outward as Logan discovers relationships (e.g. Tesla's AI partnership rippling into Nvidia,
  semiconductor suppliers, energy demand, related ETFs, and prediction markets). Users should visually
  understand that opportunities rarely exist in isolation.

**MVP scope**: per [ADR-011](DECISIONS.md#adr-011-opportunity-wheel--living-ripple-ui-is-a-required-mvp-differentiator),
the wheel is a required MVP differentiator, but Phase 1 ships a **technically simplified** version —
confidence-driven radial position and basic ripple propagation, without the full physics-like continuous
animation described above. The full living-tree/ripple ambition is the target to build toward, not a
Phase 1 requirement.

## Visual design philosophy

The interface should feel modern, intelligent, clean, premium, calm, and alive — deliberately avoiding
traditional dashboards full of charts and widgets, and avoiding looking like Bloomberg or Robinhood. Users
should immediately understand what deserves attention, why it deserves attention, how confident Logan is,
and what connections Logan discovered. The interface should reduce cognitive load, not increase it.
Nothing should feel static — information flows, merges, separates, rises, and fades — but animation should
communicate intelligence, never exist purely for decoration.

## AI behavior

Logan explains its reasoning, connects dots, highlights relationships, explains its confidence, and
continuously personalizes itself. **Logan should never blindly agree with users** — if there is a safer,
better-supported, or stronger conclusion, it explains why, the same way this project's engineering
collaboration is expected to work (see [CLAUDE.md](../CLAUDE.md)). Trust matters more than telling users
what they want to hear.

## Core product loop (architecture)

The full pipeline — domain receptors through Feedback/Learning — is documented in
[ARCHITECTURE.md](ARCHITECTURE.md) and specified in detail in [docs/specs/](specs/). In product terms:
information enters through five domains (stocks, sports betting, prediction markets, social trends, and
news), gets evaluated for trust and community momentum, reasoned about against what Logan knows of the
user, scored for confidence, and turned into an attention recommendation that Policy, Prioritization, and
Presentation turn into what the user actually sees.

The Memory Inbox — where Logan asks for confirmation on uncertain inferences — remains the primary trust
mechanism between the user and Logan's memory, and stays visible and easy to act on regardless of how the
underlying write path is implemented (see [ADR-019](DECISIONS.md#adr-019-memory-inbox-confirmation-routes-through-learning-as-a-feedbacksignal)).

## Non-goals (for now)

- Institutional or advisor-facing tooling.
- Directive trade/bet recommendations (see the analysis-vs-advice boundary above).
- Multi-user/team accounts.
- Monetization infrastructure (billing, entitlements) — deferred to Phase 2.
- Full living-tree/ripple animation fidelity — deferred past the Phase 1 simplified wheel.

These are explicit non-goals, not permanent exclusions — revisit via a new ADR when the phase changes.
