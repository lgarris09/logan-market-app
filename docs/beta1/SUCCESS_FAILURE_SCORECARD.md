# Beta 1 success / failure scorecard

The question Beta 1 answers:

**Does STRATUS save users meaningful monitoring effort by surfacing and explaining stock changes worth
knowing?**

No numeric targets are set here. There is no user data to set them from, and a threshold invented now
would be defended later instead of examined. Each row names the evidence to collect and where it comes
from. Counts are reported as counts, with the number of participants and opportunities behind them.

## Evidence to collect

| # | Signal | Positive evidence | Negative evidence | Source |
|---|---|---|---|---|
| 1 | Would have missed it | A participant names a specific opportunity they would not otherwise have seen | Participants say they already knew everything shown | Interview; opened opportunities |
| 2 | Monitoring effort | Participant reports checking other sources less for watched names | Participant browses the feed but still monitors as before | Interview |
| 3 | Understands why it appeared | Participant can say in their own words why a card appeared | "I do not understand why I got this" reports; cannot explain in interview | Feedback reason `unclear_why`; interview |
| 4 | Evidence is not read as advice | Participant describes an evidence label as how well-supported the observation is | Participant reads a label as buy / sell, or as a probability | Interview, asked directly |
| 5 | Timeliness | Opportunities seen while still current | "This is stale" reports; stale events presented as current | Feedback reason `stale`; freshness state recorded with the report |
| 6 | Truthfulness | No confirmed evidence-integrity incident | Any confirmed incident; "This seems wrong" reports that are upheld | Feedback reason `seems_wrong`; incident log |
| 7 | Notifications earned | Participant judges the pushes they received appropriately timed | Pushes described as arbitrary or noisy; pushes that cannot be explained from the ledger | Decision Ledger; interview |
| 8 | Watch means intent | Watched names are ones the participant says they want monitored; watched names get opened | Watch used as a bookmark and ignored; Watch changes nothing they notice | Watch / unwatch events; opens |
| 9 | Returns on revision | Participant reopens an opportunity after a material revision | Material revisions go unopened | `opportunity_returned_to` events |
| 10 | Ask clarifies | Ask from an opportunity resolves the participant's question | Ask answers are generic or miss the selected opportunity | Ask events with opportunity context; interview |
| 11 | Enough to judge | Each participant saw enough meaningful events to form a view | Too few events to evaluate the product | Count of opportunities and revisions per participant |
| 12 | Relevance | Few "not useful to me" reports relative to opens | "Not useful" dominates | Feedback reason `not_useful` |

Row 11 comes first. If participants did not see enough to judge, the other rows are not evidence either
way and the finding is "insufficient exposure", not success or failure.

## Decision outputs

| Output | What would justify it |
|---|---|
| **GO / EXPAND** | Rows 1 and 2 show positive evidence from most participants, from specific named opportunities rather than general approval. Rows 3 to 6 show no unresolved red flag. No upheld evidence-integrity incident remains open. Row 11 is satisfied |
| **ITERATE** | The core value shows up for some participants, and the shortfalls are identifiable and bounded: explanations unclear, too few events, a signal family misfiring, notifications mistimed. The fix is a change to the product as built |
| **HOLD** | An evidence-integrity problem is confirmed and not yet corrected; or labels are being read as recommendations; or reliability prevented a fair test. Nothing else is evaluated until it is fixed |
| **RETHINK** | Cards are clear and trusted, and participants still do not monitor less. The product works as designed and the design does not deliver the value. This is a legitimate outcome and is not softened into ITERATE |

## Rules for reading the evidence

- A participant's statement about a specific opportunity outweighs any general statement of liking it.
- Feed browsing is not value. Row 2 is the test.
- One upheld truthfulness incident outweighs many positive comments until it is corrected.
- Behavioural counts are read alongside interviews, never as conclusions on their own.
- The scorecard is filled in by someone other than the person who built the feature under review.
