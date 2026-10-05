# Beta 1: earnings-data path, decision support, category breadth and critical path

2026-10-05. Recommendation and design only. No production, schema or scoring change; the qualification
gates stay in shadow. Analysis data: `docs/baselines/2026-10-05-beta-decision-support/analysis.json`
(30 monitored symbols; 600 reported quarters back to late 2021; 7,560 symbol-days of prices).

Governing rule (Master Plan REV4, Section 2A): nothing delays Beta 1 unless it is required for
reliability, truthfulness / data integrity, core usability, or measuring whether STRATUS is useful.

## 1. Recommended earnings-data path

1. **Now (no new provider): turn EPS-beat qualification off wherever the basis cannot be proven — which
   today is everywhere.** Keep earnings in Beta 1 as a *results* category built on evidence that can be
   validated: the fact and time of the report, and revenue against estimate for issuers whose revenue
   definition matches the filed statement.
2. **In parallel: evaluate one narrow add-on dataset** for matched EPS (Section 3). It is not required to
   enter beta.
3. **Start capturing pre-release estimates** (Section 5) as soon as the store is approved. Every report
   date that passes without a snapshot is a comparison that can never be proven afterwards; 30 monitored
   symbols report between 2026-10-14 and early November.

## 2. Current-provider capability findings (FMP, current plan)

- `/earnings` and `/earnings-calendar` return actual and estimated EPS and revenue, a report date and a
  row-level `lastUpdated`. No basis, share basis, fiscal period, currency or estimate timestamp.
- **No endpoint on the current plan states the consensus basis or returns a matched pair with a stated
  methodology.**
- The restricted `earnings-surprises` family (402 on this plan) is documented as returning the date,
  estimated EPS, actual EPS and the surprise. The documentation found says nothing about GAAP versus
  adjusted or about how the consensus is formed. On that evidence it would **not** solve the problem: it
  is the same pair with the subtraction done. I could not open the full FMP documentation page (403) or
  call the endpoint, so this is a reading of the public description, not a test.
- Quarterly analyst estimates are also restricted (402); the annual version carries averages and analyst
  counts with no basis field.
- What the current plan *can* establish, for the actual side only: fiscal period, currency, filing
  acceptance time, GAAP basic and diluted EPS, revenue (`/income-statement`), and splits (`/splits`).
- Measured over 600 quarters: `epsActual` equals GAAP diluted EPS in 203 and differs in 397; 18 of 30
  symbols are equal in some quarters and different in others. The provider's actual is not on one basis
  even within an issuer, so it cannot be classified by a rule.

## 3. Minimal alternate source, if matched EPS is wanted

**Zacks EPS Surprises, delivered through Intrinio's API** — a single dataset, not a provider migration.

| Need | Field (per Intrinio's documentation) |
|---|---|
| Issuer | ticker, FIGI, company id |
| Fiscal period | `fiscal_year`, `fiscal_quarter` |
| Pre-release consensus | `eps_mean_estimate` — "the pre-earnings release mean EPS estimate"; plus count and standard deviation of estimates |
| Final actual | `eps_actual` — "the actual Non-GAAP EPS figure released by the company, interpreted by Zacks" |
| Basis | actual stated as non-GAAP; `eps_actual_zacks_adj` gives the adjustment back to GAAP |
| Release time | `actual_reported_date`, `actual_reported_time`, before-open / during / after-close code |
| Revenue equivalent | Zacks Sales Surprises: `sales_actual`, `sales_mean_estimate`, adjustment, count, deviation |

Zacks describes its consensus as before non-recurring items, the same basis as its actuals. Not verified:
pricing, whether the licence allows showing derived results in a consumer app, coverage of the 30 symbols,
update latency after a release, and whether the estimate basis is stated per record or only as
methodology. Those are the questions to put to the vendor before any integration. No other candidate was
evaluated.

## 4. Beta-safe fallback (what Beta 1 does without matched EPS)

- **No EPS-beat or EPS-miss trigger.** No "beat consensus by X%" claim anywhere. Reason code recorded:
  `earnings_eps_comparability_unresolved`.
- **Earnings stays visible as "reported results".** A report is a real, dated, verifiable event. STRATUS can
  say a company reported, show the reported figures as the company's, and show how the price has moved
  since — without asserting a surprise.
- **Revenue surprise may qualify** for issuers whose `revenueActual` matches the filed statement, once a
  pre-release estimate snapshot exists (Sections 5 and 6). Until snapshots exist it is also unproven.
- **Analyst actions and price moves are unaffected** and keep qualifying on their own.
- **Company news / catalysts** enter from filings (Section 10).
- The feed gets smaller. That is accepted: the goal is not to preserve volume at the expense of truth.

Turning the EPS trigger off is itself a qualification change and a visible one: 20 of today's 22
opportunities are EPS beats. It needs Logan and Chuck's decision and the neutral migration in Section 9.

## 5. Pre-release estimate snapshot — minimum durable design

One append-only table in its own SQLite file (same pattern as the other stores; gated behind the existing
persistence flag). **Not created.** A schema change needs explicit approval.

| Column | Meaning |
|---|---|
| `symbol` | issuer |
| `fiscal_period` | fiscal year and quarter if the source gives it; otherwise the scheduled report date is stored and the period marked unverified |
| `scheduled_report_date` | the provider's date for the upcoming report |
| `metric` | `eps` or `revenue` |
| `estimate_value` | the estimate as served |
| `estimate_basis` | `gaap`, `adjusted`, or null when unknown — never guessed |
| `captured_at` | STRATUS's own UTC clock at capture: the fact being proven |
| `source` | provider and endpoint |
| `source_last_updated` | the provider's own row timestamp, if any |
| `capture_version` | version of the capture rule |

- Written by the existing earnings fetch when the row has an estimate and no actual yet. No extra provider
  calls: the cohort's earnings rows are already fetched every six hours.
- A new row only when the value changes or daily, whichever is first. Roughly 30 symbols × 2 metrics ×
  a few rows per quarter: a few hundred rows a year.
- At release, the snapshot used is the last one strictly before the release time.
- Append-only; never updated. Retention: keep.
- This proves *when* the estimate was held. It does not prove its basis.

## 6. Revenue trigger recommendation

**Do not adopt 2%. If a revenue-surprise trigger is adopted, 5% is the defensible threshold, restricted to
issuers whose revenue definition matches, and only once pre-release snapshots exist.**

Comparability, 600 quarters: the provider's `revenueActual` equals filed revenue (within 0.05%) in 511. The
89 that differ are concentrated: AXP 20 of 20, BAC 19 of 20, PLD 18 of 20, then CVX, DUK, COP 4–5 each.
Fifteen symbols match in every quarter. So revenue is reliably comparable for most industrial, consumer,
technology and healthcare issuers, and not for banks, card issuers and REITs. The statement cross-check is
available on the current plan and decides it per quarter.

Frequency by threshold (absolute surprise, all 600 reports; the definition-matched subset is within a
point of these):

| Threshold | Share of reports | Per quarter across 30 symbols |
|---|---|---|
| 1% | 69% | 21 |
| 2% | 47% | 14 |
| 3% | 33% | 10 |
| 4% | 26% | 8 |
| 5% | 21% | 6 |
| 8% | 12% | 3–4 |

The median absolute surprise is 1.8%. A 2% threshold would mark an ordinary quarter as an event. 5% marks
about the top fifth and matches the existing 5% used for EPS and price, so the rule stays one sentence. I
am not recommending 5% because it yields a convenient count; 3% and 4% are also defensible and the table
is there for the decision. 72% of surprises are positive, so a revenue "beat" alone is weak information —
another reason for a high threshold. Bands, if adopted at 5%: 5 / 7.5 / 12.5 / 20, the same multiples as
price.

## 7. Price-materiality recommendation

**Keep the 5% threshold and the 1× / 1.5× / 2.5× / 4× bands.** One year, 30 symbols, 7,560 symbol-days:

| | Result |
|---|---|
| Days at or above 5% | 148 (2.0%) — about 3 a week across the cohort |
| Trading days with no qualifying move | 154 of 252 |
| `barely_qualified` (5–7.5%) | 116 |
| `meaningful` (7.5–12.5%) | 27 |
| `large` (12.5–20%) | 5 |
| `capped_exceptional` (20%+) | 0 |
| Symbols with no qualifying day all year | 3 |
| Threshold sweep, events per week | 3% → 13.6; 4% → 6.2; 5% → 2.9; 6% → 1.7; 7.5% → 0.6 |

- 5% is rare enough to mean something and frequent enough to occur. 3% would be more than two a day.
- The top band was never reached by this large-cap cohort in a year. That is correct behaviour for a
  ceiling, not a reason to lower it.
- 46 of the 148 qualifying days fall within two days after that symbol's earnings report. A price move
  right after results is another dimension of the same event, not independent evidence — consistent with
  keeping signal families out of corroboration.

## 8. Parameter recommendations

| Parameter | Proposed | Evidence | Recommendation |
|---|---|---|---|
| EPS denominator floor | $0.10 | 600 reports: 20 have a zero or negative estimate; 5 more are under $0.10; 11 under $0.25; median $1.73 | Lock "zero or negative is ineligible" — unarguable. Leave the positive floor **unlocked**: $0.10 and $0.25 differ by six reports in five years in this cohort, which is not enough to choose. Moot while EPS magnitude is blocked |
| Estimate staleness window | 45 days | Consecutive reports are 62–124 days apart (median 91); reports come 11–58 days after period end | Lock the principle: the window must be shorter than the shortest report cycle (62 days), so a snapshot cannot belong to the previous quarter. 45 satisfies it. Once STRATUS captures its own snapshots at least daily, tighten to 7 days |
| Quote staleness | 24 hours on the quote's own timestamp | Conflicts with existing behaviour: the quote freshness contract is 30 min + 15 min grace on *fetch age* (ADR-075), and a Friday close is legitimately over 60 hours old on Monday morning | **Do not lock.** Replace with: fetch age within the existing quote freshness contract, and the quote belongs to the latest trading session |

## 9. Model-migration audit record — minimum design

One append-only table. **Not created**; schema approval needed. Never read by presentation, never counted
as a revision, never notified.

| Column | Meaning |
|---|---|
| `entity_id` | the opportunity |
| `recalculated_at` | UTC |
| `prior_model_version`, `new_model_version` | assessment model versions |
| `recalculation_reason` | e.g. `model_version_change` |
| `prior_assessment`, `new_assessment` | JSON: qualification state and reason codes, evidence label, score, materiality band |
| `evidence_snapshot` | JSON: the inputs used and their provenance (source, fetch time, values) |

The lifecycle tracker compares assessments only within one model version. On a version change it rebases
silently: no revision number advance, no "strengthened / weakened", no timeline entry.

## 10. Beta 1 Stocks category matrix

| Category | Implemented? | Trustworthy enough for beta? | Missing work | Blocking? | Provider / data dependency | Planned beta behaviour |
|---|---|---|---|---|---|---|
| **Earnings / results** | Yes — EPS beat and miss triggers | **No.** The EPS comparison is not on a proven basis | Turn off unproven EPS triggers; present results as reported; optional revenue surprise | **Yes** (truthfulness) | Current provider for the report itself; snapshots for revenue; add-on dataset only if matched EPS is wanted | "Reported results" with the company's figures and the move since; no surprise claim unless proven |
| **Analyst actions** | Yes — upgrades and downgrades | Yes: a dated action by a named firm; magnitude-neutral | None required. Optional: show firm and rating change on the card | No | Current provider (`/grades`) | Unchanged |
| **Price / market moves** | Yes — 5% move | Yes | Fix the quote-staleness rule to fetch age and latest session; bands in shadow | No (the staleness rule ships with the freshness correction) | Current provider (`/quote`) | Unchanged, with materiality band shown once bands leave shadow |
| **Company news / catalysts** | **No** | — | Design and build a catalyst input from primary filings; classify by event type; validate; explain | **Yes** (required category breadth) | SEC 8-K filings. The current provider lists filings with form type, acceptance time and link, but not the 8-K item numbers that say what happened; those come from SEC EDGAR itself. A provider decision | Material company events as opportunities, each tied to its filing. No article feed |
| **Revisions / trajectory** | Yes — lifecycle revisions and trajectory with reasons | Mostly. Trajectory is computed and never shown; revisions are sometimes recorded with change type "none" | Show trajectory and reason on the card; stop or classify the "none" revisions | **Yes** for showing it (core usability); the "none" defect is truthfulness of history | None | Trajectory and what changed are visible on every card |

### Catalysts as opportunity inputs

Proposed scope for Beta 1, from 8-K item types, each a deterministic trigger with the filing as provenance:

| Catalyst | 8-K item | Notes |
|---|---|---|
| Material agreement / contract | 1.01, 1.02 | entry into or termination of a material agreement |
| M&A development | 2.01, and 1.01 where applicable | completion of an acquisition or disposition |
| Results release | 2.02 | corroborates the earnings-results event from a primary source |
| Guidance change | 7.01, 2.02 exhibits | hardest to classify deterministically; may need to wait |
| Leadership change | 5.02 | departure or appointment of directors and officers |
| Regulatory / legal | 8.01, 3.01, 4.02 | delisting notices, non-reliance on prior statements; legal proceedings are often only in periodic reports |
| Other material events | 8.01 | shown as an event with its filing, without a category claim |

- Available on the current plan: the filing list per symbol and the 8-K feed. Not available: press releases
  (402). Aggregated news articles are available but come from third-party publishers of mixed quality;
  they are context at most, never the trigger.
- Qualification is "a filing of this type exists for this issuer, accepted at this time". Evidence strength
  is high by construction (primary source), and there is no magnitude.
- This is the largest piece of unbuilt Beta 1 scope.

## 11. Remaining work that can legitimately block Beta 1

| Work | Cut-line reason |
|---|---|
| Operational Integrity: Phase A verdict, Phase B, 72-hour window | reliability |
| EPS-beat truthfulness: turn off unproven EPS qualification and present earnings as reported results | truthfulness |
| Self-corroboration fix (ADR-076) | truthfulness |
| Freshness correction (ADR-075) | truthfulness / timeliness |
| No percentage presentation (ADR-077) and the three mobile card changes (trajectory, WHAT CHANGED, quiet STRATUS TAKE) | core usability, truthfulness |
| Company news / catalysts category | required category breadth |
| Neutral model migration (so the corrections above do not write false history) | truthfulness |
| Beta instrumentation: can we tell whether it is useful | measurability |
| Beta Entry Review | governance |

Post-beta: matched EPS via an add-on dataset; revenue-surprise trigger; materiality bands in the product;
evidence-label recalibration; signal diversity; magnitude of any kind for EPS; provider migration;
Notification Decision Ledger; Universe expansion; other domains.
