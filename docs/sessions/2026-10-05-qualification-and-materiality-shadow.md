# Qualification, EPS comparability and materiality — shadow design and replay

2026-10-05. Follows the red-team review. Everything here is shadow: the module
`logan_core/trigger_detection/qualification_shadow.py` is imported by nothing in the pipeline (a test
enforces that), and no production behaviour, schema or score changes. Section 2 of
`2026-10-05-magnitude-and-card-design.md` (the logarithmic magnitude function with a 0.5 floor) is
**superseded** by this note and must not be implemented.

## 1. Semantic model

Six separate concepts. None is folded into another; there is no combined scalar.

| Concept | Question | Owner today |
|---|---|---|
| Qualification | Did a governed trigger validly fire? | Trigger detection |
| Evidence strength | How well-supported and usable is the evidence? | Evidence Trust → Conclusion Confidence |
| Event materiality | How large was the validated observed change? | none yet (shadow bands here) |
| Trajectory | How is the evidence changing across revisions? | Lifecycle |
| Personal relevance | Why does this matter to this user? | Reasoning / User Model |
| Priority | What deserves attention first? | Opportunity Engine / Prioritization |

Evidence strength is determined by validity and comparability, completeness, freshness, provenance,
independent corroboration and unresolved conflicts. It is not probability, expected return, direction,
importance, user relevance or event magnitude. The contract is `docs/CONFIDENCE_SEMANTICS.md`.

## 2. Qualification states

| State | Meaning | Emits a trigger? | Has materiality? |
|---|---|---|---|
| `qualified` | Inputs valid and comparable; the rule fired | yes | only for families with a band table |
| `not_qualified` | Inputs valid and comparable; the rule did not fire | no | no |
| `blocked_invalid_input` | An input contradicts a requirement | no | no |
| `blocked_incomparable_basis` | Actual and estimate cannot be shown to be on the same basis | no | no |
| `blocked_stale_or_missing_required_fields` | A required fact is absent or too old | no | no |

- A blocked observation is not weak evidence. It produces no trigger, no label and no score contribution.
- When several problems exist, every reason code is kept and the most severe state governs:
  invalid → incomparable → stale/missing.
- Unknown is never read as fine: every optional fact is "not known" until proven.
- Other families qualify independently: a blocked EPS beat does not stop a valid revenue, price or analyst
  signal for the same issuer.

## 3. EPS comparability contract

An EPS-beat trigger qualifies only if every row is established.

| Requirement | Established by | Current provider (`/earnings`) |
|---|---|---|
| Same issuer | actual and estimate identifiers match | yes — one row, one symbol |
| Same fiscal reporting period | both carry the same fiscal year and quarter | **no** — the row has a report date only |
| Pre-release estimate | estimate captured strictly before the release, at most 45 days earlier | **no** — only a row-level `lastUpdated`, which is after the release |
| Compatible accounting basis | actual and estimate both GAAP, or both adjusted on the same definition | **no** — no basis field for either |
| Basic/diluted compatibility | both basic or both diluted | **no** |
| Same currency | both currencies known and equal | **no** — not in the row |
| No unadjusted split between estimate and release | split history checked, or adjusted | **no** in the row (a separate `/splits` endpoint exists) |
| No unresolved restatement | restatement status known | **no** |
| Provenance retained | source of actual and of estimate recorded | yes |

If any row is not established: no EPS-beat trigger, no discount, no low-confidence version. The result is
`blocked_incomparable_basis` with `earnings_eps_comparability_unresolved` first, followed by the specific
codes. A qualified EPS beat is magnitude-neutral: no size and no band until basis validation is
trustworthy.

## 4. Provider fields and endpoints available today (FMP, current plan)

| Endpoint | Status | Fields relevant here |
|---|---|---|
| `/earnings` | available | `symbol`, `date`, `epsActual`, `epsEstimated`, `revenueActual`, `revenueEstimated`, `lastUpdated` |
| `/earnings-calendar` | available | the same seven fields |
| `/income-statement` (quarter) | available | `period`, `fiscalYear`, `date`, `filingDate`, `acceptedDate`, `reportedCurrency`, `eps`, `epsDiluted`, `revenue`, `operatingIncome`, `totalOtherIncomeExpensesNet` |
| `/income-statement-as-reported` | available | as-filed line items, `period`, `fiscalYear`, `reportedCurrency` |
| `/financial-reports-dates` | available | `fiscalYear`, `period` |
| `/splits` | available | `date`, `numerator`, `denominator` |
| `/analyst-estimates` (annual) | available | `epsAvg/High/Low`, `revenueAvg/High/Low`, `numAnalystsEps`, `numAnalystsRevenue` — no basis field |
| `/analyst-estimates` (quarter) | **402, not on this plan** | — |
| `/earnings-surprises-bulk` | **402, not on this plan** | — |
| `/earnings-surprises`, `/earnings-report` | 404 | — |
| `/quote` | available | `price`, `previousClose`, `changePercentage`, `timestamp`, `volume` |

## 5. Can the current provider prove the consensus basis?

**No.** Nothing available on the current plan states what basis `epsEstimated` is on, and no endpoint
returns a matched actual-and-consensus pair with a stated methodology.

- The actual side can be characterised: the income statement gives GAAP basic and diluted EPS, fiscal
  period, currency and the filing acceptance time.
- That shows `epsActual` is GAAP diluted for some issuers (AMZN 5.75 = 5.75, GOOGL 9.11 = 9.11, PLD 1.13 =
  1.13) and something else for others (KO 0.97 against GAAP 1.03). It says nothing about the estimate.
- Knowing the actual's basis without the estimate's does not establish comparability.
- Whether the restricted `earnings-surprises` endpoint carries a methodology statement could not be checked
  from this plan.

What would close each gap, narrowest first:

| Gap | Narrowest fix |
|---|---|
| Fiscal period, currency, release time of the actual | `/income-statement` — already available; one call per ticker per quarter |
| Split status | `/splits` — already available |
| Pre-release estimate timestamp | STRATUS snapshots the upcoming quarter's estimate row itself before the report date (the provider already serves it: AMZN's 2026-10-29 row has `epsEstimated` 1.96 today). Needs a small durable snapshot store — a schema decision |
| Consensus and actual on a stated, matched basis | a provider that publishes estimates and actuals normalised to the same basis with a basis flag. That is a provider decision; no candidate was evaluated here |

## 6. Denominator eligibility

A percentage surprise is computed only when the estimate is finite, positive, and at or above an absolute
floor: `EPS_ESTIMATE_MIN_ABS = 0.10`; revenue estimate must be positive.

- Zero, near-zero and negative estimates produce `estimate_denominator_ineligible`
  (`blocked_incomparable_basis`).
- An ineligible denominator is never capped into the top band. A 0.02 consensus and a 0.30 actual is not
  an exceptional beat; it is not a trigger.
- The 0.10 floor is a proposal, an absolute amount rather than a percentile. It needs review.

## 7. Timestamp and fiscal-period rules

- The estimate must carry a capture time, and it must be strictly before the release. Equal is not before.
- An estimate captured more than 45 days before the release is stale (`estimate_stale`).
- A missing release time, estimate time or fiscal period blocks (`…_missing` / `…_unverified`); a known
  mismatch is an invalid input (`fiscal_period_mismatch`, `estimate_not_pre_release`).
- Price: a quote older than 24 hours is `quote_stale`; a missing price or previous close is
  `quote_missing`; a non-positive previous close is `previous_close_not_positive`.

## 8. Reason codes

Stable lower-case identifiers; each maps to exactly one state; never renamed, only added.

| State | Codes |
|---|---|
| `qualified` | `qualified` |
| `not_qualified` | `below_threshold`, `wrong_direction` |
| `blocked_invalid_input` | `input_non_finite`, `issuer_mismatch`, `fiscal_period_mismatch`, `currency_mismatch`, `estimate_not_pre_release`, `unadjusted_split_between_estimate_and_actual`, `previous_close_not_positive` |
| `blocked_incomparable_basis` | `earnings_eps_comparability_unresolved`, `eps_basis_unknown`, `eps_basis_mismatch`, `eps_share_basis_unknown`, `eps_share_basis_mismatch`, `revenue_definition_unresolved`, `estimate_denominator_ineligible`, `restatement_unresolved` |
| `blocked_stale_or_missing_required_fields` | `actual_missing`, `estimate_missing`, `fiscal_period_unverified`, `estimate_timestamp_unverified`, `estimate_stale`, `release_timestamp_missing`, `currency_unverified`, `split_status_unverified`, `provenance_missing`, `quote_missing`, `quote_stale` |

Blocks are decided before any transformation: no percentage is computed for a blocked observation.

## 9. Materiality bands (revenue, price)

Bands, not scores. Trigger-family-specific. Each bound is a fixed multiple of that family's own
qualification threshold — 1×, 1.5×, 2.5×, 4× — chosen so the rule can be stated in one sentence, not
fitted to any sample.

| Band | Price move (|close-to-close|) | Revenue surprise (|actual − estimate| / estimate) |
|---|---|---|
| not qualified | below 5% | below 2% |
| `barely_qualified` | 5% to under 7.5% | 2% to under 3% |
| `meaningful` | 7.5% to under 12.5% | 3% to under 5% |
| `large` | 12.5% to under 20% | 5% to under 8% |
| `capped_exceptional` | 20% and above | 8% and above |

- The price threshold is the existing trigger's 5%. **The 2% revenue threshold is new**: there is no
  revenue-surprise trigger today, so adopting it is a qualification decision of its own.
- `capped_exceptional` is a ceiling on what the band expresses; beyond it, size adds no information.
- Direction is reported separately; bands are symmetric.
- EPS has no band table. Analyst actions have no band table (magnitude-neutral by decision).
- Materiality is not an input to evidence strength and is not a ranking weight here.

## 10. Replay results

Run with `2026-10-05-qualification_shadow_replay.py` on captured provider rows
(`docs/baselines/2026-10-05-qualification-shadow/`).

**EPS, strict (what the provider row establishes): 20 of 20 blocked.** Every current earnings opportunity
is `blocked_incomparable_basis`, each with the same eight reasons: comparability unresolved, EPS basis
unknown, share basis unknown, fiscal period unverified, estimate timestamp unverified, currency
unverified, split status unverified, restatement unresolved.

**Revenue, strict: 20 of 20 blocked** — the same missing facts, plus `revenue_definition_unresolved`. The
definition question is real: the provider's `revenueActual` equals income-statement revenue for AMZN but
not for PLD (2.18B against 2.43B) or KO (13.373B against 13.380B).

**Consequence if the hard gate were switched on today:** the feed would lose its 20 earnings
opportunities and keep the analyst and price items. That is the honest reading of the data, and the
reason this stays in shadow until the provider questions in section 5 are answered.

**Price, today's quotes for the 30 monitored symbols:** all valid, none over 5%; 30 `not_qualified`.

## 11. Shadow distributions

Price, one month of real daily closes (30 symbols, 2026-09-04 → 2026-10-02, 600 symbol-days):

| Band | Symbol-days | Share |
|---|---|---|
| not qualified | 587 | 97.8% |
| `barely_qualified` | 11 | 1.8% |
| `meaningful` | 1 | 0.2% |
| `large` | 1 | 0.2% |
| `capped_exceptional` | 0 | 0% |

Revenue, **hypothetical** (the same 20 rows as if period, timestamp, currency, split, restatement and
definition were all established — not a result, only a look at how the table would distribute):

| Band | Count |
|---|---|
| not qualified (under 2%) | 7 |
| `barely_qualified` | 5 |
| `meaningful` | 2 |
| `large` | 4 |
| `capped_exceptional` | 2 |

Observations, not tuning: the price table puts 11 of 13 qualifying days in the lowest band, which is what
a 5% threshold on large-cap daily moves produces; the revenue table spreads more evenly. Neither table
was adjusted after seeing these numbers. Twenty reports is too few to set the revenue thresholds on.

## 12. Evidence-label rules (recommendation; no thresholds set)

Labels should be defined by named conditions, then calibrated — not by cut-offs on a blended number, and
never by percentile.

| Proposed label | Conditions (all must hold) |
|---|---|
| Strongest | qualified; confirmed by at least one independent evidence origin; latest fetch fresh; all required fields complete; provenance registered; no unresolved conflict |
| Middle | qualified; single origin; latest fetch fresh; complete; no unresolved conflict |
| Limited | qualified, with one or more stated limits: fetch stale-within-grace, optional fields missing, or provenance not registered |
| (no label) | any blocked state — a blocked observation is not shown as low evidence |

- Label names and the exact boundaries come after qualification and materiality have run in shadow and
  the distributions have been inspected. The current 0.35 / 0.55 / 0.80 cut-offs are not carried forward
  automatically.
- Materiality, trajectory and personal relevance are shown beside the label, each in its own words.

## 13. Migration and versioning (design)

- Every assessment carries an **assessment model version**.
- When the model changes, opportunities are recalculated with reason `model_version_change`. That is not
  a revision: no "evidence strengthened/weakened" text, no timeline entry, no notification.
- A user-facing change is produced only when external evidence changed (a new report, a new source, a
  price move, a stale or failed fetch, a provider correction).
- An audit record keeps: prior assessment, current assessment, model version before and after, the
  evidence snapshot and provenance used, and the recalculation reason.
- Where this lands: the lifecycle tracker needs to distinguish "inputs changed" from "model changed"
  before comparing against the 0.05 revision threshold, and the audit record needs a durable home. The
  second is a schema decision and is not made here.
- One versioned transition: qualification gates, self-corroboration fix (ADR-076), materiality bands and
  label rules ship together under one model version, after shadow replay, so history steps once.

## 14. What this note does not decide

The revenue-surprise trigger and its 2% threshold; the EPS denominator floor; the provider question; the
audit-record store; the label names. Each needs Logan and Chuck.
