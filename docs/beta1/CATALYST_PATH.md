# Beta 1 catalyst path — structured SEC Form 8-K events

Technical design for the company-filing catalyst path. Behind `STRATUS_SEC_FILING_CATALYSTS` (default
off). Decision record: ADR-084.

Why it exists: with the EPS comparability gate on (ADR-079), earnings-surprise opportunities no longer
qualify and the feed becomes too thin to evaluate. This path adds one narrow, attributable source. It is
an opportunity input, not a news feed.

## 1. Source

One endpoint: the SEC EDGAR submissions index, `data.sec.gov/submissions/CIK##########.json`. Per company
it lists each filing's form, accession number, acceptance timestamp, filing date, the issuer's stated
event date, and, for Form 8-K, the item numbers the issuer assigned.

- No filing text is fetched or read. No press release, exhibit or third-party publisher.
- One request per company at most every 30 minutes, paced well under the SEC's fair-access limit.
- The SEC requires automated clients to send a User-Agent naming the operator and a contact address.
  That value is operator configuration (`STRATUS_SEC_USER_AGENT`). Without it the provider cannot be
  constructed and no request is made.
- Ticker-to-CIK mapping is a fixed table of the 30 cohort companies, each verified on 2026-10-07 against
  the index's own ticker list. A ticker not in the table is never fetched. A response whose ticker list
  does not contain the requested ticker is refused.

## 2. Categories

Included (14 item numbers, 11 trigger codes). The phrase is what the headline says.

| 8-K item | Category | Headline phrase |
|---|---|---|
| 2.02 | Results reported | financial results furnished |
| 5.02 | Leadership change | director or principal officer change |
| 1.01 | Material agreement | entry into a material definitive agreement |
| 1.02 | Material agreement | termination of a material definitive agreement |
| 2.01 | Acquisition / disposition | completed acquisition or disposition of assets |
| 1.03 | Bankruptcy | bankruptcy or receivership |
| 5.01 | Change in control | change in control |
| 4.01 | Accounting change | change of certifying accountant |
| 4.02 | Accounting change | non-reliance on previously issued financial statements |
| 2.05 | Impairment / exit costs | costs of an exit or disposal activity |
| 2.06 | Impairment / exit costs | material impairment |
| 3.01 | Listing compliance | notice of delisting or listing non-compliance |
| 2.04 | Obligation accelerated | event accelerating a financial obligation |
| 1.05 | Cybersecurity incident | material cybersecurity incident |

Excluded, and why:

| 8-K item | Reason |
|---|---|
| 8.01 Other events | Catch-all. An issuer can file anything under it; the item says nothing deterministic |
| 7.01 Regulation FD | Catch-all, largely investor presentations |
| 9.01 Exhibits | Not an event |
| 2.03 Direct financial obligation | Routine financing for large issuers. Whether one is meaningful cannot be decided from structured fields |
| 1.01 / 1.02 **when filed with 2.03** | That combination is a credit facility or notes offering. Declined as `routine_financing_not_governed` |
| 3.02, 3.03, 5.03, 5.04–5.08, 1.04, 6.x | Governance, administrative or asset-backed items |
| Any other form | Only 8-K and 8-K/A are governed |

"Material financial obligations where clearly meaningful" is the one requested category not delivered:
"clearly meaningful" needs the amount and terms, which are in the filing text. Item 2.04 (an obligation
being accelerated) is included because the designation itself is the event.

## 3. Qualification

One pure function, `qualify_filing()` (`logan_core/trigger_detection/filings.py`). It answers whether a
governed rule validly fired and returns a governed state with stable reason codes:

| State | Reason codes |
|---|---|
| `qualified` | `qualified` |
| `not_qualified` | `no_governed_item`, `routine_financing_not_governed`, `form_not_governed` |
| `blocked_invalid_input` | `issuer_mismatch`, `accession_malformed`, `item_unrecognized`, `filing_in_future` |
| `blocked_stale_or_missing_required_fields` | `accession_missing`, `filing_timestamp_missing`, `items_missing`, `source_missing`, `filing_too_old` |

Retained for every candidate: source identity, issuer (ticker and CIK), form, items, accession number,
acceptance timestamp, SEC filing date, issuer's event date, filing URL, the state, and the reason codes.
Every filing looked at is logged with its state and codes.

The same function runs twice: when the feed decides whether to admit a signal, and again in trigger
detection from the signal's own fields. A signal altered in between does not fire.

Importance is never inferred. The only materiality used is the issuer's own choice of item. There is no
catalyst score, no magnitude and no band; every filing category carries the same single contribution to
the internal ordering score, and the trigger's direction is neutral.

## 4. Deduplication and revisions

- One filing is one trigger, however many governed items it carries. The primary category follows a
  fixed precedence; the other governed items are recorded with it.
- One opportunity per company. Each poll takes the newest qualified filing inside the 14-day window; an
  older qualified filing is not a second card. A filing joins a company's existing opportunity (analyst,
  price) as an additional signal family.
- The accession number identifies a filing. Re-polling the same filing changes nothing; the index is
  cached, and a test confirms the revision number does not move.
- An amendment (8-K/A) qualifies like any other filing, is worded as an amended disclosure, and updates
  the company's one opportunity.

Limit: a new filing registers as a lifecycle revision when it changes the company's set of categories. A
second filing in the same category replaces the card's content without a new revision number. A durable
per-accession revision record is not built.

No syndicated-news deduplication exists or is needed: there is one source and one identifier.

## 5. Provenance and freshness

- Source is recorded as `sec_filing`, already present in the source-reputation registry.
- Event time is the SEC acceptance timestamp; the issuer's stated event date is carried alongside.
- Freshness is the age of STRATUS's last successful fetch of that company's index (ADR-075): fresh within
  30 minutes, six hours of grace, then unavailable. A failed fetch yields no signal that poll and never
  degrades the rest of the feed.
- Evidence label: one authoritative origin with nothing independent beside it reads **Supported**, not
  Strong, with "One source supports this" shown as the limitation.
- A filing older than 14 days at detection does not start an opportunity. After detection the lifecycle
  tracker ages it: monitored for 48 hours, stale after 7 days, expired after 14.

## 6. User-facing treatment

No separate design. A filing opportunity uses the existing card and detail:

| Section | Content |
|---|---|
| Headline | "Company: company filing (8-K Item 2.02: financial results furnished, filed 2026-10-05)" |
| WHAT CHANGED | The lifecycle delta for the opportunity |
| WHY IT MATTERS NOW | When it was first detected and its lifecycle state |
| STRATUS TAKE | Shown only with a personal basis |
| Trajectory | As for any opportunity |
| Evidence | "Supported evidence" plus limitations |
| Supporting signals | "Results reported", "Company filing", "Analyst action", "Price move" when more than one |

The headline is plain and somewhat mechanical. It says only what the index says. Improving the wording is
Presentation work and is not done here.

## 7. Earnings results without EPS surprise

Item 2.02 is the truthful earnings-result fact: the company furnished its results, on a stated date, in a
filing STRATUS can cite. It is its own signal family (`earnings_result`), separate from the EPS-surprise
family, and makes no comparison to consensus.

Other candidates examined and not available:

| Candidate | Finding |
|---|---|
| Guidance raised / lowered | Not in the index. It is in the press release text |
| Revenue result | Needs an actual and a comparable estimate; comparability is unproven |
| Reported EPS as a bare figure | Basis not stated by the market-data provider |

## 8. What is deliberately out of scope

SEC 8-K alone cannot go further without reading text. In a sample of real filings, items 8.01 and 7.01
appear in most of them and are exactly where the remaining company-specific news sits (product announcements,
litigation, regulatory decisions, guidance). Classifying them means reading the exhibit, which is
NLP-based materiality classification — a stop condition. So are guidance changes, and the size of a
financing or an agreement. Nothing in that direction has been started.

## 9. Configuration

| Variable | Default | Meaning |
|---|---|---|
| `STRATUS_SEC_FILING_CATALYSTS` | off | Enables the path |
| `STRATUS_SEC_USER_AGENT` | unset | Operator name and `contact=<address>`, as the SEC asks of automated clients. Operator configuration, never in source. Without a valid value no request is made |

No schema change and no new store.
