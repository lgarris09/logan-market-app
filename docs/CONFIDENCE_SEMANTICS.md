# Confidence semantics contract

The reference for what STRATUS's confidence value means. Any proposal to change scoring, labels or how
confidence is shown is checked against this note, and changes this note in the same ADR.

Status: describes the system as of 2026-10-05, with ADR-076 (no self-corroboration) and ADR-077 (no
percentage presentation). The regression suite that enforces it is
`logan_core/tests/test_confidence_semantics_matrix.py`.

## What it represents

**Evidence strength:** how well supported STRATUS's observation is — that a specific, verifiable thing
happened and has been reliably observed. It is a statement about the evidence, made the same way for
every user.

## What it does not represent

- **Not a probability.** It is not the chance a stock rises, a thesis plays out, or any outcome occurs.
  STRATUS has no calibrated probabilistic model. Until one is built *and validated against outcomes*, the
  value must never be shown or described as a percentage, a likelihood or odds.
- **Not a recommendation**, and not a measure of how much attention something deserves. Attention is
  prioritization's job.
- **Not personal.** Personal relevance never raises or lowers it.
- **Not a prediction of magnitude or direction.** A miss and a beat of the same size are equally
  well-evidenced.

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

### Trigger magnitude

Today a trigger contributes the same amount however far its measured magnitude clears the firing
threshold. A bounded, magnitude-aware contribution is designed (see
`sessions/2026-10-05-magnitude-and-card-design.md`) and not implemented. Its binding rules, if adopted:
the registry constant is the cap; weaker qualifying evidence earns less; nothing earns more than today;
magnitude that is missing or on an unverified basis earns no magnitude share; the function is monotonic,
saturating and deterministic.

### Signal diversity

Several kinds of signal on one entity (earnings, an analyst action, a price move) are more evidence
dimensions, not more independent sources. They are not corroboration and do not change the score today.
If they are ever credited, it is as a separately named concept, within the bounds the regression suite
already fixes: never below the strongest single part, never above the sum of the parts.

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
- Thresholds are re-examined whenever the formula changes; a formula change that shifts most of the feed
  across a boundary changes the labels' meaning and must say so.

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
