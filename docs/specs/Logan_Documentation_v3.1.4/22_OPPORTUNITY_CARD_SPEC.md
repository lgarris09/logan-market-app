# Logan Intelligence — Opportunity Card Specification
**Version:** 3.1.3
*Source: Architecture v1.3 FINAL (2026-07-31). Original: “source_material/22_OPPORTUNITY_CARD_SPEC.md” (historical label).*

---

## What the Opportunity Card Is

The Opportunity Card is the primary way a user engages with Logan's intelligence. It expands from a tapped node in the Opportunity Field — rising into view rather than navigating away from the field.

The card is not a report. It is not a dashboard. It is structured intelligence — designed to be understood in under 30 seconds by a user who wants to decide whether to act.

---

## Card Structure

The card has a strict information hierarchy. Items higher in the hierarchy are always visible. Items lower are expanded on demand.

```
┌─────────────────────────────────────────────────────────┐
│  HEADER                                                 │
│  [Domain badge]   [Lifecycle stage]   [Confidence pill] │
│                                                         │
│  HEADLINE                                               │
│  What this opportunity is — one line (max 80 chars)     │
├─────────────────────────────────────────────────────────┤
│  WHY IT MATTERS TO ME          ← ALWAYS FIRST           │
│  Personalized, always rendered before any other field   │
│  "You have 2 positions in AI-adjacent stocks. This      │
│   earnings beat adds a third signal to that cluster."   │
├─────────────────────────────────────────────────────────┤
│  WHAT HAPPENED                                          │
│  The triggering event in 1-2 sentences                  │
├─────────────────────────────────────────────────────────┤
│  WHY NOW                                                │
│  Timing context                                         │
├─────────────────────────────────────────────────────────┤
│  HOW LONG LOGAN HAS BEEN WATCHING                       │
│  "Watching for 4 days · Conviction building since       │
│   2026-07-30 when first weak signals appeared"          │
├─────────────────────────────────────────────────────────┤
│  SUPPORTING EVIDENCE                                    │
│  What confirms this — bullet list                       │
├─────────────────────────────────────────────────────────┤
│  CONTRADICTING EVIDENCE         ← SHOWN WHEN PRESENT    │
│  What argues against — never hidden                     │
├─────────────────────────────────────────────────────────┤
│  CONFIDENCE                                             │
│  [Label]  [Score bar]                                   │
│  Raised by: strong earnings beat, options flow surge    │
│  Limited by: macro uncertainty, sector-wide move        │
├─────────────────────────────────────────────────────────┤
│  SCORES                                                 │
│  Hit Quality: 84  ████████░░  (objective strength)     │
│  User Value:  71  ███████░░░  (personal relevance)      │
├─────────────────────────────────────────────────────────┤
│  ACTION WINDOW                  ← SHOWN WHEN APPLICABLE │
│  Opens: [timestamp]   Closes: [timestamp]               │
├─────────────────────────────────────────────────────────┤
│  SOURCES                                                │
│  Data sources used for this analysis                    │
├─────────────────────────────────────────────────────────┤
│  CORRECTION STATE               ← SHOWN WHEN CHANGED    │
│  "Logan's thesis has changed since first surfaced."     │
│  Correction note explaining what changed and why.       │
├─────────────────────────────────────────────────────────┤
│  [▼ FULL REASONING CHAIN]          [▼ CONNECTED ITEMS]  │
├─────────────────────────────────────────────────────────┤
│  DISCLAIMER                                             │
│  "Logan provides analysis only. Not financial advice.   │
│   Always verify before acting."                         │
└─────────────────────────────────────────────────────────┘
│  [DISMISS]    [NOT RELEVANT]    [REMIND ME]   [ACTED ON]│
└─────────────────────────────────────────────────────────┘
```

---

## Field Definitions

### 1. Header

**Domain badge:** Color-coded pill matching node color. Values: Stocks · Sports · Prediction Markets · Crypto · Social Trends · Culture · Personal Finance · Cross-Domain.

**Lifecycle stage:** Text label. Values: Watching · Detected · Emerging · Building Conviction · High Conviction · Action Window · Outcome · Learning.

**Confidence pill:** Color-coded. Green (high) · Yellow (moderate) · Red (low) · Gray (insufficient data).

### 2. Headline

One line. **Maximum 80 characters.** Enforced at Presentation layer.

Format: `[Entity] — [what happened/is happening]`
Examples:
- "NVIDIA — Earnings beat + prediction market gap detected"
- "Chiefs vs. Bills — Line movement diverges from injury reports"
- "Fed rate decision — Cross-domain convergence building"

### 3. Why It Matters to Me

**Always first after the headline. Always personalized. LOCKED.**

This field MUST reference the user's actual situation — their positions, their history, their stated interests. A generic "this is important" is a failure of this field.

Good:
- "You hold NVDA in your linked Robinhood account. This adds a third signal to your AI cluster."
- "Your open prediction contract on 'NVDA above $120' is directly in play."
- "You've acted on 3 of the last 4 earnings-beat opportunities Logan surfaced. Your accuracy on those: 75%."

Bad:
- "NVIDIA earnings beat matters because earnings drive stock prices."
- "This is relevant to investors."

### 4. What Happened

The triggering event. Objective. 1-3 sentences. No editorializing.

This is what happened in the world, not what Logan thinks about it. That comes next.

### 5. Why Now

Timing context. Why is this the right moment to pay attention?

May include:
- Calendar events (options expiry, earnings, game time)
- Comparative timing (prediction market hasn't moved yet, but stock has)
- Historical precedent ("In the last 6 quarters, NVDA moved +8% on average after this pattern")
- Decay context (if Action Window, "window closes in approximately 2 days")

### 6. How Long Logan Has Been Watching

Communicates that Logan's conviction was earned, not sudden.

Format: `Watching for [N] days · [Stage history summary]`

This field builds trust. When Logan says "I've been watching this for 8 days and conviction is still building," the user knows this is not a knee-jerk reaction to a single headline.

### 7. Supporting Evidence

Bullet list of what confirms Logan's thesis. 1-5 points. Sources referenced.

Required when confidence >= EMERGING stage.

### 8. Contradicting Evidence

Bullet list of what argues against Logan's thesis. Shown when present. **Never hidden.**

If Logan has high confidence but contradicting evidence exists, both are shown. The contradicting evidence does not override Logan's assessment — but the user deserves to see it.

If no contradicting evidence exists, this field is omitted (not shown as empty).

### 9. Confidence

Visual bar + label + raised_by + limited_by.

Labels: Very High · High · Moderate · Building · Insufficient data.

**raised_by:** 1-3 bullet points explaining what increased confidence.
**limited_by:** 1-2 bullet points explaining what is preventing higher confidence.

### 10. Hit Quality and User Value (both visible)

Both scores are always shown. Users learn the difference over time.

If Hit Quality is high but User Value is moderate: "Strong objective signal — your exposure in this area is moderate."
If both are high: "Strong signal, high relevance to your portfolio."

### 11. Action Window

Shown only when the opportunity is at ACTION WINDOW stage.

Displays `action_window_opens` and `action_window_closes` timestamps with a human-readable label:
- "Action window: Now → Jan 15, 4pm EST"
- "Earnings in 6 hours"
- "Contract resolves tomorrow"

### 12. Sources

Compact list of data sources used in this analysis. Not detailed citation — just source names. Builds trust and allows users to verify independently.

Example: "Alpaca (price data), Reddit/WallStreetBets (social signal), Kalshi (contract pricing)"

### 13. Correction State

Shown only when Logan's thesis has changed since the opportunity was first surfaced.

`correction_state` values: `none` (field omitted) · `updated` · `reversed`.

When `updated`: "Logan's understanding of this has changed. [correction_note explaining what changed and why]"
When `reversed`: "Logan's thesis has reversed. [correction_note explaining the reversal]"

Logan surfaces changes to its own thesis openly. It does not silently overwrite its prior position.

### 14. Full Reasoning Chain (expandable)

The complete `decision_trace` — all layers that contributed to this recommendation, with their outputs.

Advanced users will expand this. Most users won't. It must be complete and accurate.

### 15. Connected Items (expandable)

Other opportunities or entities that Logan is also watching that relate to this one.

### 16. Required Disclaimer

Compact. At bottom. **Never skipped.**

"Logan provides intelligence analysis only. This is not financial, legal, or gambling advice. Verify all information before acting. Past intelligence accuracy does not guarantee future results."

---

## Feedback Actions

**[DISMISS]:** Dismisses the opportunity. Logan records the dismiss. The opportunity decay engine applies reaction decay. Default FeedbackSignal `interaction_type: "dismiss"`.

**[NOT RELEVANT]:** Signals that this type of opportunity isn't relevant to the user. Stronger signal than dismiss — helps Logan calibrate interest weights. `interaction_type: "not_relevant"`.

**[REMIND ME]:** Re-surfaces this opportunity at a later time. `interaction_type: "remind"`.

**[ACTED ON]:** Marks the opportunity as acted upon. Strongest positive signal. `interaction_type: "acted"`. Used for behavioral pattern learning and outcome tracking.

---

## Card Behavior

**Expansion:** Card rises from the tapped node position. Duration: 350ms, ease-out-back (slight overshoot). The field dims (not hides) in background.

**Dismissal:** Swipe down or tap outside. Duration: 250ms, ease-in. Node returns to original state.

**Acted On:** Marks the opportunity. Logan records for learning. `inferred_intent: "acting"` flagged in FeedbackSignal.

**Share:** Copies the reasoning chain as plain text. Does not include user-specific position data.

---

## Empty Fields

Some fields will be empty in early pipeline stages:

| Stage | "Why it matters to me" | Supporting Evidence | How long watching |
|---|---|---|---|
| Detected | Basic (entity match only) | Minimal (1 item) | Short (just detected) |
| Building Conviction | Personalized | 2-3 items | Building |
| High Conviction | Fully personalized | 3-5 items | Extended |
| Action Window | Fully personalized + urgency | Full + action window | Full history |

Logan never shows an empty field without explanation. If "Why it matters to me" is weak because the user model is still learning: "Logan is still learning your patterns — this surfaced based on your watched domains. Personalization improves over time."

---

*Logan Intelligence Opportunity Card Specification — v3.1.2 | 2026-08-03*
*v3.1.2 changes: Headline max changed 120 → 80 characters. Why It Matters to Me marked LOCKED (always first). Supporting Evidence field added. Contradicting Evidence field added (never hidden). Action Window field added (opens/closes timestamps). Sources field added. Correction State field added (updated/reversed). Feedback actions expanded: NOT RELEVANT and REMIND ME buttons added. Domain badge expanded to include Culture and Personal Finance. FeedbackSignal interaction types documented on buttons.*


---
## v3.1.2 Required Card Contract

Every full card must support: headline; why it matters to this user; confidence; supporting and contradicting evidence; source provenance; timing and action-window expiration; current and cross-domain exposure; invalidation conditions; suggested next step; external parent-app link when policy permits; lifecycle; trending indicator distinct from quality; risk/uncertainty; save/watch; dismiss; not relevant; remind later; already acted; correction/thesis-changed state. “Acted” is not the preferred or only meaningful action.
