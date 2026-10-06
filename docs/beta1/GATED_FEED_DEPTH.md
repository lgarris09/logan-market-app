# Feed depth with the EPS comparability gate on

2026-10-06. Read-only replay; production was not queried or changed for it.

## Method and its limits

Sources: the production feed captured at the start of the 72-hour window (2026-10-05 20:57 UTC, 21
items), and the production snapshots taken the same day (`lifecycle_state`, `opportunity_revisions`,
`universe_daily_telemetry`). Script: `docs/sessions/2026-10-06-gated_feed_replay.py`. Output:
`docs/baselines/2026-10-06-gated-feed/gated_feed_replay.json`.

The gate was applied by removing every earnings beat / miss / in-line trigger from each opportunity's
recorded trigger codes and keeping the opportunity only if another trigger remained. That is exactly
what the gate does with the current provider, which supplies no comparability proof.

This is a replay, not a live run. The candidate was **not** run against the live provider: it would use
the same provider key and rate budget as production, and provider behaviour is part of what the 72-hour
window is measuring. A live look at the gated feed is a post-window step.

## Result

| Measure | Current feed | With the gate on |
|---|---|---|
| Opportunities in the feed | 21 | **3** |
| Removed | — | **18 (86%)** |
| Unique companies | 21 | 3 (ABT, CAT, DE) |
| Earnings-surprise opportunities | 20 primary | 0 |
| Analyst opportunities | 1 primary (ABT), plus 2 carried under earnings (CAT, DE) | 3 |
| Price opportunities | 0 | 0 |
| Earnings-result opportunities that remain without EPS surprise | — | 0 |

Why no price opportunities at the snapshot: a price opportunity exists only while a governed 5% move is
in effect. Five companies in lifecycle state (TSLA, BA, ADBE, BKNG, ACN) had price as their only trigger,
but none was in the feed at that moment.

Why no earnings-result opportunities remain: the only defensible facts left are that results were
released and for which quarter. There is no trigger for that, by decision.

### Lifecycle and trajectory of the three that remain

All three rest on an analyst upgrade. ABT is about three days old and cooling. CAT (monitoring) and DE
(cooling) were first detected about 32 days ago as earnings opportunities and carry the analyst upgrade as a
second trigger; with the gate on they would be presented on the analyst action alone. Trajectory is present
for each (it is computed for every lifecycle-tracked opportunity), so revision and trajectory content is
available, on three cards.

### Over the last 32 days (cohort of 30, 2026-09-04 to 2026-10-05)

| Measure | Value |
|---|---|
| Revisions recorded | 526 |
| Revisions resting on EPS surprise alone | 310 (59%) |
| Revisions with a non-EPS trigger | 216: 99 price, 104 analyst, 13 both |
| Companies that ever had a non-EPS trigger | 18 of 30 |
| Days with at least one company gaining a non-EPS revision | 28 of 32 |
| Companies with a new non-EPS revision per day | median 2.5, mean 2.9, range 0 to 9 |
| Last 10 days | 2, 0, 2, 2, 2, 2, 3, 1, 1, 1 |
| Share of feed impressions by family | earnings 93.9%, analyst 4.5%, price 1.6% |

## Is the result testable?

Not as a test of the product's central claim.

- Three standing cards, all the same kind, all cooling, is not enough for a participant to form a view on
  whether STRATUS saves monitoring effort. Scorecard row 11 ("enough to judge") would fail first.
- New material arrives for one to three companies a day across the whole cohort. A participant whose
  interests overlap a handful of the 30 would see something new every few days at best.
- A push needs a new material revision on something relevant to that participant, so interruptions would
  be rare enough that "are interruptions earned" could not be assessed.

What it would still test: comprehension of a card, the evidence wording, Watch, Ask from an opportunity,
the feedback control. Those are real, and they are the smaller part of what Beta 1 is for.

The finding is not that the gate is wrong. The current 21-item feed is 20 parts a comparison STRATUS
cannot substantiate. The gate removes a claim that should not be made; what it exposes is that the feed
had almost nothing else in it.

## Options, narrowest first

None is started. This is a product decision.

1. **A neutral earnings fact.** "X reported results for its fiscal quarter" from the release date and
   quarter the provider already supplies, with no beat / miss, no EPS figure and no materiality. One new
   trigger code and its copy; no new provider, no new store. It would return roughly the 20 companies
   to the feed with a true statement, and price or analyst signals would then attach to them as
   supporting evidence. Its weakness: "results were released" is a fact a participant may already know,
   so on its own it tests timeliness more than insight.
2. **A matched EPS source.** The vendor inquiry. Restores the original content truthfully. Not in hand,
   and not on a Beta 1 timescale by its terms.
3. **The narrow SEC 8-K path.** Structured, attributable, timestamped. A new category rather than a
   repair of this one; the largest of the three.
4. **Proceed thin.** Run Beta 1 on analyst and price signals, with participants chosen for overlap with
   the cohort, and treat it as a comprehension-and-trust beta rather than a monitoring-effort beta. The
   scorecard question would have to be narrowed to match.

Options 1 and 4 are compatible. Option 1 is the smallest change that makes the feed deep enough to
evaluate without making a claim STRATUS cannot support.

## What can be inspected on a device, and when

The mobile candidate renders whatever the backend returns, so the gated feed needs no mobile change. It
needs a backend running with the gate on against live data, which cannot be done before the window
closes without sharing production's provider budget. After the window: enable the gate on the deployed
candidate with notifications paused and look at the feed on a device before deciding (deployment
sequence, Release C). That is the first moment the real gated feed can be seen.
