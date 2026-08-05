# Logan Intelligence — Principles
**Version:** 3.1.3
*Source: Architecture v1.3 FINAL (2026-07-31). Original: “source_material/20_LOGAN_PRINCIPLES.md” (historical label).*

*The company constitution. These principles define why Logan exists, how it behaves, and what it will never become. Every feature, every architectural decision, every product choice should be traceable to one of these principles.*

---

## The Principles

---

### 1. Logan informs. The user decides.

Logan never assumes control of money, bets, decisions, or attention. It recommends. It explains. It surfaces what matters.

The user always executes.

This is not a limitation of the product. It is the product's defining philosophy.

An advisor who takes over your decisions is no longer an advisor. Logan exists to make you a better decision-maker — not to make decisions for you.

---

### 2. Intelligence before information.

There is no shortage of information in the world. There is a profound shortage of intelligence.

Information tells you what happened.
Intelligence tells you what it means — for you, specifically.

Logan does not show you more. It shows you less, better.

Every feature that adds noise instead of clarity violates this principle.

---

### 3. Explain every recommendation.

Logan never says "consider this" without explaining why.

If Logan cannot explain it, Logan does not say it.

This means every recommendation carries:
- What triggered it
- Why it matters to this user (always first — before any other explanation field)
- How confident Logan is
- What would change that confidence
- What evidence supports it and what argues against it

Unexplained recommendations are not intelligence. They are guesses wearing a suit.

---

### 4. Confidence is never hidden.

When Logan is certain, it says so.
When Logan is uncertain, it says so.
When Logan does not know yet, it says so.

Pretending to be more confident than the evidence supports is a betrayal of trust. Users make better decisions when they know what they're working with.

Logan's credibility comes from honesty — not from projecting certainty it doesn't have.

This includes: showing contradicting evidence when it exists. Never hiding the case against Logan's own thesis.

---

### 5. Learning never stops.

Logan gets smarter over time — about the world, and about the user.

Not by taking over. Not by automating. By observing, adapting, and continuously improving the relevance and accuracy of its intelligence.

A Logan that knows you at month 12 should be meaningfully more valuable than Logan at month 1.

---

### 6. Beautiful software should reduce cognitive load.

Logan's interface should make the world feel simpler, not more complex.

Every visual element, every animation, every color choice is in service of one thing: directing the user's attention to what genuinely deserves it — and getting out of the way of everything else.

Beauty is not decoration. In Logan's case, beauty is function. A calm, clear interface reduces the cognitive overhead of processing intelligence.

An interface that is noisy, cluttered, or demanding is a broken interface — regardless of how good the intelligence underneath it is.

---

### 7. Every feature must make users better decision-makers.

This is the filter for every product decision.

Not: "Is this cool?"
Not: "Is this technically impressive?"
Not: "Would users use this?"

But: "Does this make users better at making decisions in the domains they care about?"

If the answer is no, the feature doesn't belong in Logan.

---

### 8. The interface is a living intelligence, not a dashboard.

Dashboards display. Logan thinks.

A dashboard is static — it shows you what it was told to show. A living intelligence changes as the world changes. It surfaces what matters now, not what a designer thought would matter when they built the layout.

The Opportunity Field exists because the way information is organized communicates meaning. The closer to center, the more it matters. The brighter, the more confident Logan is. The pulse means: now.

A list cannot communicate any of this.

---

### 9. The user's attention is a finite resource. Treat it accordingly.

Every notification, every alert, every surface item costs the user something.

Logan earns the right to interrupt by surfacing only what genuinely deserves attention. It does not surface things to stay top-of-mind. It does not fill empty states with low-quality content. It does not notify because it's been quiet for too long.

An empty Opportunity Field is Logan saying: "Nothing deserves your attention right now." That is a correct answer. It is not a failure.

Logan respects that attention is the scarcest resource its users have.

---

### 10. Personalization is earned, not assumed.

Logan's personalization improves through observation and feedback — not through a setup wizard or a questionnaire.

In the beginning, Logan knows little about a user. It learns through:
- What they engage with and what they dismiss
- What they act on and what they ignore
- What accounts they link and what positions they hold
- What they explicitly correct

Over time, the intelligence becomes genuinely personal. But it never pretends to know more than it does. Early Logan is honest about having a limited user model. Mature Logan has earned its personalization.

---

### 11. Privacy is a feature, not a compliance checkbox.

What users share with Logan — their portfolio, their bets, their behavioral patterns — is sensitive. It is also what makes Logan valuable.

The implicit contract: users share context, Logan gives them better intelligence. If that context were ever misused, the contract is broken and the product is destroyed.

Logan never shares user-specific data with third parties.
Logan never uses user data to serve advertisers.
Logan's intelligence is a tool for the user, not a commodity to monetize.
Users can delete their data. Logan does not hold data hostage to functionality.

---

### 12. One Logan. Every user.

Logan's architecture is universal — the same intelligence pipeline serves every user. But the output is different for every person.

This is the core technical achievement: a system that is simultaneously general (works for every domain, every user type) and deeply personal (produces different intelligence for different people from the same events).

A NVIDIA earnings beat is an event. What it means for you specifically — given your portfolio, your bets, your history, your goals — is Logan's job.

---

### 13. Community momentum is not personal relevance.

What everyone else is excited about is not the same as what matters to you.

Logan tracks community activity (trending, crowd momentum, social volume) as one signal among many. It never conflates crowd excitement with opportunity quality or personal relevance.

An opportunity that is going viral but has low objective quality should not appear bright or central in Logan's field because of the crowd. Community momentum maps to one visual property (edge glow) and nothing more.

Logan is an independent reasoner. Its job is to protect the user from crowds, not to amplify them.

---

*Logan Intelligence Principles — v3.1.2 | 2026-08-03*
*v3.1.2 changes: Principle 3 expanded: "why it matters to me" always first; supporting and contradicting evidence both shown. Principle 4 expanded: showing contradicting evidence explicitly stated. Principle 11 expanded: user deletion right stated. Principle 13 added: Community momentum is not personal relevance (reflects DECISION-016).*
