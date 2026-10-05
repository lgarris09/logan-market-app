# Confidence semantics contract

The reference for what STRATUS's confidence value means. Any proposal to change scoring, labels or how
confidence is shown is checked against this note, and changes this note in the same ADR.

Status: describes the system as of 2026-10-05, with ADR-076 (no self-corroboration) and ADR-077 (no
percentage presentation). The regression suite that enforces it is
`logan_core/tests/test_confidence_semantics_matrix.py`.

## Six concepts, kept separate

Locked 2026-10-05 (ADR-078). These are never collapsed into one number because one number is convenient.

| Concept | Question it answers |
|---|---|
| **Qualification** | Did a governed STRATUS trigger validly fire? |
| **Evidence strength** | How well-supported and usable is STRATUS's evidence for this observation? |
| **Event materiality** | How large was the validated observed change? |
| **Trajectory** | How is the evidence changing across revisions? |
| **Personal relevance** | Why does this matter to this specific user? |
| **Priority** | What deserves attention before something else? |

This note is about evidence strength. Qualification states and materiality bands are specified in
`sessions/2026-10-05-qualification-and-materiality-shadow.md`.

## What it represents

**Evidence strength:** how well-supported and usable STRATUS's evidence is for an observation. It is
determined by validity and comparability, completeness, freshness, provenance, independent corroboration
and unresolved conflicts. It is a statement about the evidence, made the same way for every user.

## What it does not represent

- **Not a probability.** It is not the chance a stock rises, a thesis plays out, or any outcome occurs.
  STRATUS has no calibrated probabilistic model. Until one is built *and validated against outcomes*, the
  value must never be shown or described as a percentage, a likelihood or odds.
- **Not a recommendation**, and not a measure of how much attention something deserves. Attention is
  prioritization's job.
- **Not personal.** Personal relevance never raises or lowers it.
- **Not event magnitude.** A large change is not better evidence than a small one. Size is materiality,
  a separate concept reported as a band.
- **Not direction or expected return.** A miss and a beat are equally well-evidenced.
- **Not importance.** Importance is priority's question.
- **Not a softer form of qualification.** If the inputs are invalid, incomparable or missing, there is no
  trigger and nothing to rate. A blocked observation is not "low evidence".

## Components

| Component | Weight | Meaning | Rules |
|---|---|---|---|
| Source reputation | 35% of trust | How reliable the reporting source is | From the reputation registry. A source not in the registry gets the neutral 0.5; that is a statement of ignorance, not of mediocrity. FMP is not registered today — a decision to make, not a value to leave by default. |
| Corroboration | 25% of trust | How many *independent sources* report the same thing | Saturates at three. Identical re-polls do not count. A source re-reporting changed content does not count (ADR-076). Different kinds of signal from one provider do not count. |
| Recency | 20% of trust | How recently the event happened | Exponential decay, 6-hour half-life, from the provider's event time. Only ever decays. Event age is also expressed by lifecycle aging; freshness (ADR-075) is a different thing: the age of the last successful fetch. |
| Completeness | 20% of trust | Whether the event has its basic facts | Summary, entity and timestamp present. |
| Manipulation penalty | multiplier | Guard for thin, incomplete evidence | Applies only when uncorroborated *and* incomplete. |
| Trigger contribution | added | A verified, registry-defined trigger fired | A fixed constant per trigger code today. When several are attached, the largest is used, never the sum. |
| Contradiction | ×0.7 | Conflicting signals exist | Reserved; nothing populates it today. |

The result is clamped to 0–1.

### Trigger magnitude is not part of evidence strength

A trigger contributes the same amount however far its measured magnitude clears the firing threshold,
and that is correct for evidence strength. Size is expressed separately, as a deterministic materiality
band per trigger family (`barely_qualified`, `meaningful`, `large`, `capped_exceptional`), computed only
from validated, comparable inputs. An earlier proposal to scale the trigger contribution by magnitude
(a logarithmic function with a 0.5 floor) was rejected on review and must not be implemented.

- EPS surprise has no materiality band until actual and estimate can be proven comparable.
- Analyst actions are magnitude-neutral; no rating or target-price magnitude is invented.
- A percentage is never computed on a zero, near-zero or negative denominator, and a pathological
  percentage is never capped into a valid band.

### Corroboration and signal diversity

Corroboration is an independent evidence origin confirming the same claim. A revision from the same
source is a revision. Several kinds of signal on one entity (earnings, an analyst action, a price move)
are evidence dimensions, or supporting signals — not corroboration, and kept out of evidence strength.
The regression suite fixes the bounds any future credit would have to stay within: never below the
strongest single part, never above the sum of the parts.

## Uncertainty

- Uncertainty is stated in words alongside the value: the engine emits limiting factors ("Only one
  independent source has corroborated this so far").
- Weak evidence must stay weak. No change may raise a score to create visual variety. Two opportunities
  with the same evidence must have the same score.
- Missing data earns nothing: no consensus, no reported value, or a zero consensus means no trigger and
  no trigger contribution. Missing data is never filled with a neutral value that scores.

## Labels

| Label | Score |
|---|---|
| High | ≥ 0.80 |
| Moderate | ≥ 0.55 |
| Low | ≥ 0.35 |
| Speculative | below 0.35 |

- Shown as evidence strength ("Moderate evidence"), never as a number.
- With one unregistered provider, "High" is unreachable today: the ceiling is about 0.795. That is a
  property of the current formula, pinned by a test, not a goal.
- These are the thresholds in the code today. They are **not** carried forward automatically. Labels are
  to be redefined by named conditions and then calibrated, after qualification and materiality have run
  in shadow and the distributions have been inspected. Percentile-only labels are never used to force
  differentiation.

## Model changes are not evidence changes

A scoring or model change must not produce "evidence strengthened" or "evidence weakened" for a user
unless external evidence actually changed. Recalculation under a new model version keeps the prior
assessment, the current assessment, the model version, the evidence snapshot and provenance, and the
reason, and normally produces no notification and no timeline event.

## Where the value is used

- Ranking: it is the opportunity's global importance in the Opportunity Engine.
- Lifecycle: changes of 0.05 or more create a revision; 0.60 or more marks high attention.
- Exploration: eligibility uses it (floor 0.70).
- Presentation: the label, and wording about evidence strengthening or weakening.

Because it feeds ranking and revisions, a scoring change is never only cosmetic: it reorders the feed and
writes revision history. Every scoring change needs a stated transition rule for existing opportunities.

## Rules for changing any of this

1. An ADR, and this note updated in the same change.
2. The regression suite's invariants keep passing unedited; its `CURRENT_VALUES` table is updated
   deliberately, in the same change, so the difference is reviewable.
3. A before/after distribution on real opportunities, showing that any new differentiation comes from
   differing evidence.
4. A transition rule for existing opportunities' revision history.
