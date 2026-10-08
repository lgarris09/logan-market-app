# Provisional parameter register — Beta 1 catalyst path

Per Master Plan REV4 2A.8. Every value here is provisional.

- **Technical evidence owner:** Dave.
- **Product / governance approval:** Logan and Chuck.
- **No automatic adaptation.** None of these values is tuned from production or beta behaviour by any
  code path. A change is a decision, recorded here and in an ADR, after review.
- **Review point:** after the first two weeks of Beta 1, or once a useful body of real catalyst
  observations exists, whichever gives enough evidence for a meaningful review. Not before launch.

Replay evidence referred to below: 48 real Form 8-K / 8-K/A index rows for the 30-company cohort, filed
2026-08-01 to 2026-10-06 (`logan_core/tests/data/sec_8k_cohort_sample_2026-10-07.json`), replayed by
`docs/sessions/2026-10-07-catalyst_feed_replay.py`; output in
`docs/baselines/2026-10-07-catalyst-feed/`.

| # | Parameter | Value | Where | Rationale | Replay evidence | Adopted | Review status |
|---|---|---|---|---|---|---|---|
| 1 | Filing age limit at detection | 14 days | `FILING_MAX_AGE_AT_DETECTION`, `trigger_detection/filings.py` | A filing older than this is not news when first seen; matches the expiry window so a filing cannot be detected after it would already have expired | With 14 days: 7 opportunities at 2026-10-05, 9 at 2026-10-07; standing filing opportunities 1 to 5 a day, median 3, over 33 days | 2026-10-07 | Provisional; unreviewed |
| 2 | SEC index cache lifetime | 30 minutes | `SEC_FILINGS_CACHE_TTL_SECONDS`, `providers/sec_edgar.py` | Filings arrive a few times a quarter per company; 30 minutes bounds detection lag while keeping requests to about 30 companies per half hour | Not a replay quantity. Request volume follows from the cohort size | 2026-10-07 | Provisional; unreviewed |
| 3 | Freshness grace for filings | 6 hours | `SIGNAL_FRESHNESS_CONTRACTS["company_filing"]`, `providers/freshness.py` | Same as analyst grades: infrequent data where a few hours' lag does not change what the filing says | None; no live fetch history exists yet | 2026-10-07 | Provisional; unreviewed |
| 4 | Lifecycle: monitored window | 48 hours | `_MONITORING_WINDOW_HOURS`, `opportunity_lifecycle/tracker.py` | A dated disclosure is actively current for about two trading days | At 2026-10-07: 3 of 6 filing opportunities inside 48 hours | 2026-10-07 | Provisional; unreviewed |
| 5 | Lifecycle: stale after | 168 hours (7 days) | `_STALE_WINDOW_HOURS`, same file | Same as an analyst action | At 2026-10-07: 1 of 6 between 2 and 7 days | 2026-10-07 | Provisional; unreviewed |
| 6 | Lifecycle: expires after | 336 hours (14 days) | `_EXPIRE_WINDOW_HOURS`, same file | Slightly shorter than an analyst action (15 days); a filing with no further evidence should not outlive its relevance | At 2026-10-07: 2 of 6 between 7 and 14 days. With 14 days the feed has 7 to 9 items; a shorter window would thin it, a longer one would fill it with stale cards | 2026-10-07 | Provisional; unreviewed |
| 7 | Shared contribution to the internal ordering score | 0.10 for every filing category | `_FILING_CONFIDENCE_CONTRIBUTION`, `trigger_detection/stocks.py` | A filing has no magnitude and the categories are not ranked against each other; one value avoids precision STRATUS does not have. Equal to a price move, above an analyst action (0.08) | Not evaluated: the replay measures which filings qualify, not how they rank against analyst and price items | 2026-10-07 | Provisional; unreviewed. **Ranking effect not yet observed** |
| 8 | Minimum spacing between SEC requests | 0.25 seconds | `SEC_MIN_SECONDS_BETWEEN_REQUESTS`, `providers/sec_edgar.py` | Far below the SEC's fair-access limit of 10 requests a second | None needed | 2026-10-07 | Provisional; unreviewed |
| 9 | SEC request timeout | 6 seconds | `SEC_REQUEST_TIMEOUT_SECONDS`, same file | Long enough for the index, short enough not to hold a poll | None; the sample fetch completed in under a second per company | 2026-10-07 | Provisional; unreviewed |

Not parameters, and not provisional: the governed item list and the routine-financing rule. Those are
the accepted Beta 1 taxonomy (ADR-084) and change only by decision.

## What the review should look at

1. Did filings arrive and surface within an acceptable time of acceptance by the SEC (values 2, 3)?
2. Did filing cards linger after they stopped being useful, or vanish while still being opened
   (values 4 to 6)? Source: opens and returns by lifecycle state, and "This is stale" reports.
3. Where did filing items rank against analyst and price items, and did participants agree with that
   order (value 7)? Source: feed position at open, "not useful" reports, interviews.
4. Did any filing surface that should not have, or fail to surface when it should have? That is a
   question about the taxonomy, not these values, and goes to Logan and Chuck separately.

## Change log

| Date | Parameter | From | To | Decided by | Evidence |
|---|---|---|---|---|---|
| 2026-10-07 | All | — | Values above | Logan, Chuck (accepted 2026-10-08 as provisional) | Replay cited above |
