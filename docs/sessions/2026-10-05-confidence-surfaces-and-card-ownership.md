# Confidence-surface audit and card information ownership

Audit and proposal (2026-10-05), from the code on this branch and the production feed captured that day.
On-device screenshots were not available. "After" columns reflect ADR-077 on this branch, not what is
deployed.

## 1. Confidence-surface audit

### User-facing surfaces

| Surface | Where | What it shows | Derived from |
|---|---|---|---|
| Card at rest (bubble label) | `Vessel.tsx` | "Developing" / "Worth a look" / "High attention" | `delivered_item.surface` — a prioritization outcome, **not** confidence |
| Expanded card badge | `Vessel.tsx` → `AttentionBadge` | the same three-state judgment | same |
| Bubble flicker | `Vessel.tsx` | visual instability | `1 − confidence_score` |
| Notification list row | `app/index.tsx` | was "60%"; now "Moderate evidence" | `confidence_score` → `confidence_label` |
| Notification row accessibility label | `app/index.tsx` | was "60 percent confidence"; now "Moderate evidence" | same |
| Push notification | `notifications.py` | title: entity name; body: the event text. No confidence | — |
| WHAT CHANGED / "since you last looked" | revision `reason` | was "Confidence strengthened from 0.59 to 0.62"; now "The evidence supporting this has strengthened." | `confidence_score` delta |
| Ask STRATUS, "how confident" answers | `ask_engine.py` | "STRATUS has moderate evidence for this — a reasonable read of the current evidence…", plus limiting factors | `confidence_label`, `classification` |
| Ask STRATUS, LLM path | `ask_llm_provider.py` | model context: was label + raw score; now label + classification with a no-percentage instruction | same |
| Legacy field screen | `field-legacy.tsx`, `OpportunityNode.tsx` | bare label ("Moderate"); detail header was "Moderate · 60%", now "Moderate evidence" | `confidence_label` |
| Demo screen | `demo.tsx`, `OpportunityCard.tsx` | was "inference · 60%" and "Moderate · 60%"; now classification / "Moderate evidence" | `classification`, `confidence_label` |

### API fields consumed by presentation

`confidence_score` and `confidence_label` (on the feed item and again on its delivered item),
`classification` and `limiting_factors` (Ask context, demo), `delivered_item.surface`, `freshness_state`,
`lifecycle_state`, `trajectory`, `since_last_looked`.

### Not user-visible but still percentage-shaped

- `mobile/lib/attentionLayout.ts` sizes the bubble label from a percentage string that is no longer shown.
- `mobile/components/ConfidenceRing.tsx` renders a percentage and is imported nowhere.

### Where one value is presented with different semantics

1. **The judgment that replaced the percentage is not confidence.** "Worth a look" comes from the display
   surface, yet it sits exactly where the confidence percentage used to be. A user will reasonably read
   it as STRATUS's confidence. It also does not differentiate: 20 of 22 items read "Worth a look".
2. **Two vocabularies for one score.** The same number becomes Low / Moderate / High (label) and fact /
   inference / hypothesis / speculation (classification). The cut-offs coincide at 0.55 and 0.35, but
   "fact" uses different inputs (source score and corroboration), so the two can disagree at the top.
3. **Three thresholds mean three different things at nearly the same value.** 0.55 is "Moderate", 0.60 is
   "high attention" in the lifecycle, 0.70 is the exploration floor. Every earnings opportunity sits at
   0.595: Moderate, five thousandths short of high attention, and never exploration-eligible.
4. **The score is also the ranking key.** `global_importance = confidence_score` in the Opportunity
   Engine. With 20 opportunities tied at 0.595, their order is a tie-break; the captured feed's first 20
   are in alphabetical order (AAPL, AMGN, AMT, AMZN, BAC, …). The "top five" is therefore the first five
   by name, before diversity caps.
5. **Confidence drives motion.** Bubble flicker is `1 − confidence_score`, so identical scores also look
   identical in motion.
6. **Ask STRATUS says "the underlying signal is moderate"** when explaining why something is shown —
   using an evidence label to answer a relevance question.

## 2. Card information ownership

### What is duplicated today

| Field | Produced by | Content today |
|---|---|---|
| Headline | Presentation, from the World Model summary | "Apple: earnings signal (AAPL reported EPS of 2.02 vs. consensus 1.89)" |
| WHAT CHANGED (`what_happened`) | Presentation ← `reasoning.significance` | **the same sentence as the headline — 22 of 22 items** |
| `why_it_matters` | Presentation ← `reasoning.explanation` | the headline sentence again, plus the personal sentence (the card already avoids rendering it) |
| STRATUS TAKE (`why_it_matters_to_me`) | Reasoning | "Nothing in your current holdings or interests is directly connected to this yet." — **one sentence for all 22** (anonymous feed) |
| WHY IT MATTERS NOW (`why_now`) | Presentation, keyed by interruption level | two templates across 22 items; both describe delivery ("not urgent enough for an interruption"), not the opportunity |
| Push notification body | Notifications, extracted from `what_happened` | the event text again |
| Trajectory + reason | Lifecycle | present in the API on every item; **not rendered** |
| Lifecycle reason, thesis age, price since signal, vs market | Lifecycle / evidence | present in the API; **not rendered** on the card body |

Net effect: three of four text blocks say the same thing or say nothing specific, and the fields that
differ between opportunities are not shown.

### Proposed ownership rule

Each fact has one owner; no other field restates it.

| Field | Owns | Must not contain |
|---|---|---|
| **Headline** | The event, with its defining number: who, what, how much ("Apple beat EPS consensus by 6.9%") | Timing, relevance, evidence strength |
| **WHAT CHANGED** | What is different since the opportunity first appeared or since the user last looked: the latest revision's reason, trajectory and its reason, movement since the signal | The original event sentence |
| **WHY IT MATTERS NOW** | Time-sensitivity of the opportunity itself: how old the thesis is, its lifecycle state, whether it is still developing or cooling | Delivery mechanics ("not urgent enough for an interruption") |
| **STRATUS TAKE** | Personal relevance only: the user's holding, interest or Watch, and why it connects | Anything when there is no connection — then it collapses to one muted line |
| **Trajectory** | Direction of the evidence since the signal, one line under the headline | Lifecycle state (owned by WHY IT MATTERS NOW) |
| **Evidence / proof** | Evidence strength label and its limiting factors; supporting signal families | Any number presented as a likelihood |

### Smallest changes that implement it

| # | Change | Layer | New data needed |
|---|---|---|---|
| 1 | Render trajectory and its reason under the headline | mobile | none |
| 2 | WHAT CHANGED renders the revision reason / since-last-looked detail and movement since the signal, not `what_happened` | mobile | none |
| 3 | STRATUS TAKE collapses to one muted line when `personal_relevance_result.basis` is "none" | mobile | none |
| 4 | WHY IT MATTERS NOW describes thesis age and lifecycle state | backend copy (Presentation), or mobile from existing fields | none |
| 5 | Headline carries the defining number | backend copy (receptor summary) | none |
| 6 | Evidence block shows the label with limiting factors | mobile + one additive feed field (`limiting_factors`) | additive field |

1–3 are mobile-only and ship with the ADR-077 build. 4–5 are copy changes in existing layers; all wording
stays descriptive, never directive, and betting or prediction-market copy would stay strictly neutral.
6 needs an additive API field and is the only item touching the contract.
