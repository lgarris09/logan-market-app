# Provider magnitude audit, magnitude-aware trigger design, signal diversity, and card changes

Design and recommendation only (2026-10-05). Nothing in this note is implemented. The code on this branch
is limited to ADR-076 (self-corroboration) and ADR-077 (no percentage presentation).

## 1. Provider magnitude audit

Traced live for AMZN, GOOGL and 18 other current earnings opportunities, from the FMP `/earnings` payload
through to the calculated beat.

| Stage | Finding |
|---|---|
| Provider payload | Fields per row: `date`, `epsActual`, `epsEstimated`, `revenueActual`, `revenueEstimated`, `lastUpdated`, `symbol` |
| Row selection | The latest row with a non-null `epsActual` — correct; the upcoming quarter is skipped |
| Reported EPS | `epsActual`, read as-is |
| Consensus EPS | `epsEstimated`, read as-is |
| Normalization | No unit conversion or transformation; values pass through unchanged |
| Qualification | `actual > consensus` and beat ≥ 5% |
| Beat magnitude | `(actual − consensus) / |consensus| × 100` — arithmetic is correct |

**Root cause: the provider's `epsActual` is not on a consistent basis across issuers, and for some issuers
it is not on the same basis as the consensus estimate.** It is not a unit error, a field mix-up, or a
STRATUS ingestion or transformation defect.

| Symbol | `epsActual` | GAAP diluted EPS (income statement) | `epsEstimated` | Non-operating income vs operating income | EPS beat | Revenue surprise |
|---|---|---|---|---|---|---|
| AMZN | 5.75 | 5.75 | 1.82 | $53.4B vs $27.5B | 216% | +1.8% |
| GOOGL | 9.11 | 9.11 | 2.87 | $98.0B vs $40.8B | 217% | +2.8% |
| PLD | 1.13 | 1.13 | 0.747 | $0.27B vs $0.96B | 51% | +0.7% |
| KO | 0.97 | 1.03 | 0.92 | $0.8B vs $4.7B | 5.4% | +1.5% |

- For AMZN and GOOGL, `epsActual` equals GAAP diluted EPS, and that quarter's GAAP result includes
  non-operating income larger than operating income. The consensus plainly does not include it. The
  figures are valid GAAP numbers compared against an estimate on a different basis.
- For KO, `epsActual` (0.97) is *not* GAAP diluted EPS (1.03): there the provider reports an adjusted
  figure. So the basis varies by issuer.
- PLD is a REIT: GAAP EPS including property gains against a lower consensus, with revenue within 1%.
- The same pattern is visible in earlier quarters (AMZN +71%, GOOGL +94% the quarter before).

**This also touches qualification, not only magnitude.** An earnings "beat" computed on mismatched bases
may not be a beat at all. That is outside this block and is flagged for a separate decision.

## 2. Proposed magnitude function — SUPERSEDED

> **Superseded on review (2026-10-05, ADR-078). Do not implement.** Magnitude is not part of evidence
> strength. The 0.5 floor and the logarithmic function are dropped; EPS comparability is a hard
> qualification gate, not a discount; size is expressed as materiality bands. See
> `2026-10-05-qualification-and-materiality-shadow.md`. The text below is kept as the record of what
> was proposed.

```
contribution = C × (F + (1 − F) × s)

C = the trigger's existing registry constant (the cap; never exceeded)
F = 0.5            share of C earned by qualifying at all
s = clamp( ln(m / T) / ln(M / T), 0, 1 )      strength from the measured magnitude m
T = the trigger's existing firing threshold;  M = the magnitude at which strength saturates
```

| Trigger | C | T | M (proposed) |
|---|---|---|---|
| Earnings beat | 0.22 | 5% | 20% |
| Earnings miss | 0.20 | 5% | 20% |
| Price move | 0.10 | 5% | 15% |
| Analyst upgrade / downgrade | 0.08 | — | no magnitude dimension; proposed unchanged |

Properties, each a test:

- The current constant is the maximum; nothing scores higher than it does today.
- Weak qualifying evidence gets less: at the threshold the contribution is half the constant.
- Monotonic: a larger magnitude never scores lower.
- Saturating: beyond M the value is constant, so an extreme or distorted magnitude cannot dominate.
- Missing magnitude gets no magnitude share (s = 0).
- Deterministic; identical inputs give identical outputs.
- Logarithmic, so equal ratios of magnitude give equal steps.

**Basis guard for earnings (proposed):** when the EPS surprise is beyond saturation (> M) and the revenue
surprise in the same provider row is under the threshold (|revenue surprise| < T), treat the magnitude as
unverified and give no magnitude share (s = 0). Revenue is reported on a consistent basis, so a very large
EPS surprise with an ordinary revenue surprise is the signature of the mismatch above. It requires
carrying `revenueActual` / `revenueEstimated` on `EarningsReport` (two optional fields; no schema change).

### Against the 20 real earnings opportunities (all 0.595 "Moderate" today)

| Symbol | EPS beat | Revenue surprise | Strength | Basis | Contribution | Score | Label |
|---|---|---|---|---|---|---|---|
| SHW | 5.1% | +2.8% | 0.02 | ok | 0.112 | 0.487 | Low |
| KO | 5.4% | +1.5% | 0.06 | ok | 0.117 | 0.492 | Low |
| NEE | 5.5% | −7.1% | 0.07 | ok | 0.118 | 0.493 | Low |
| AAPL | 6.9% | +0.3% | 0.23 | ok | 0.135 | 0.510 | Low |
| BAC | 7.1% | +2.5% | 0.25 | ok | 0.138 | 0.513 | Low |
| CMCSA | 7.2% | +2.4% | 0.26 | ok | 0.139 | 0.514 | Low |
| SLB | 7.6% | +3.5% | 0.31 | ok | 0.144 | 0.519 | Low |
| DE | 8.7% | +16.6% | 0.40 | ok | 0.154 | 0.529 | Low |
| CVX | 9.2% | +11.7% | 0.44 | ok | 0.158 | 0.533 | Low |
| BLK | 9.6% | +5.3% | 0.47 | ok | 0.162 | 0.537 | Low |
| DUK | 10.0% | −0.9% | 0.50 | ok | 0.165 | 0.540 | Low |
| DIS | 10.8% | −0.6% | 0.55 | ok | 0.171 | 0.546 | Low |
| COP | 11.7% | +3.9% | 0.61 | ok | 0.178 | 0.553 | Moderate |
| GM | 11.9% | +2.2% | 0.63 | ok | 0.179 | 0.554 | Moderate |
| AMGN | 11.9% | +6.7% | 0.63 | ok | 0.179 | 0.554 | Moderate |
| AMT | 18.5% | +1.8% | 0.94 | ok | 0.214 | 0.589 | Moderate |
| CAT | 31.4% | +6.2% | 1.00 | ok | 0.220 | 0.595 | Moderate |
| PLD | 51.3% | +0.7% | 1.00 | unverified | 0.110 | 0.485 | Low |
| AMZN | 215.9% | +1.8% | 1.00 | unverified | 0.110 | 0.485 | Low |
| GOOGL | 217.4% | +2.8% | 1.00 | unverified | 0.110 | 0.485 | Low |

Result: 17 distinct scores instead of one; 15 Low and 5 Moderate; maximum unchanged at 0.595.

Open points for decision:

1. **F, M and the guard thresholds are judgment calls**, chosen so that the firing threshold earns half
   and four times the threshold earns everything. They are not derived from data.
2. **Fifteen of twenty drop from Moderate to Low.** That follows from the 0.55 label boundary sitting just
   below today's constant. The labels should be re-set deliberately at the same time, or the change will
   read as a downgrade of the whole feed.
3. **A one-time step in history.** Every existing earnings opportunity would record a
   `confidence_decreased` revision on deploy. That needs a transition rule so a model correction is not
   shown as the evidence weakening.
4. **The basis guard is a heuristic.** A stronger check would compare against the income statement, at
   the cost of one more provider call per ticker per quarter.
5. This overrides the Sprint 3.6.6D owner decision that trigger contributions are fixed registry
   constants, and needs its own ADR.

## 3. Signal diversity (recommendation only)

Earnings, an analyst action and a price move on one entity are different kinds of evidence from one
provider. They are not independent sources, so they should not feed corroboration.

Recommended: a separate, explicit concept — **evidence dimensions** — the count and list of distinct
signal families currently attached to an opportunity (for example "earnings + analyst action").

- Presented, not scored, at first: shown on the card as supporting signals beside the primary thesis.
- Kept out of `confidence_score` until there is evidence it should move it. If it later affects anything,
  prioritization (how much attention) is a more honest home than confidence (how well supported).
- Already derivable: the event carries every attached trigger, and the lifecycle snapshot stores the
  trigger codes. Two production opportunities are co-qualified today (CAT, DE: earnings + analyst).
- Exposing it needs one additive field on the feed item (the list of attached signal families).

## 4. Card changes (smallest set; no redesign)

From the mobile code and the feed captured on 2026-10-05; on-device screenshots were not available.

| # | Change | Where | Data needed |
|---|---|---|---|
| 1 | Show trajectory and its reason as one line under the headline ("Weakening — relative performance declined 1.4pp") | `Vessel.tsx` | `trajectory`, `trajectory_reason` — already on the feed item |
| 2 | WHAT CHANGED shows what actually changed: the latest revision's reason, or "since you last looked" detail, plus price since the signal and versus the market | `Vessel.tsx` | `lifecycle_reason`, `since_last_looked.detail`, `evidence.price_change_since_trigger_pct`, `evidence.relative_to_market_pct` — already on the feed item |
| 3 | Stop rendering `what_happened` under WHAT CHANGED, where it is the headline again (22 of 22 items) | `Vessel.tsx` | none |
| 4 | When there is no personal relevance (`personal_relevance_result.basis == "none"`), render STRATUS TAKE as one muted line instead of the bordered hero panel | `Vessel.tsx` | already on the feed item |
| 5 | Later, server-side: put the differentiating fact in the headline text ("beat consensus by 6.9%") | `stocks_earnings.py` summary | already computed |

Changes 1–4 are mobile-only, need no API change, and would ship in one build with the ADR-077 percentage
removal. All copy stays descriptive (what happened, how it has moved), never directive.
