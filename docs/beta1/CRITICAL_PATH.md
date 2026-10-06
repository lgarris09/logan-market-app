# Beta 1 critical path

As of 2026-10-06 00:45 UTC. Governing statement: Master Plan REV4, Section 2A. The Beta Cut Line is
applied: an item is a blocker only if Beta 1 would otherwise be unreliable, untruthful, unusable at its
core, or unmeasurable.

## Active path

| # | Work item | State | Next action | Depends on | Blocker | Evidence that closes it |
|---|---|---|---|---|---|---|
| 1 | 72-hour Operational Integrity window | Running; healthy at every sample so far | Interim check 2026-10-06 20:57 UTC; final 2026-10-08 20:57 UTC | Nothing touching production | **YES** | Final report: one process, no OOM, RSS within criteria, feed and scheduler state unchanged |
| 2 | Schema approval: Decision Ledger tables | Built locally; awaiting approval | Logan / Chuck approve the three tables and 120-day retention | — | **YES** | Recorded approval |
| 3 | Release A: ledger, fail-closed notifications, pause, dispatch states, feedback event | Built and tested on `beta1/candidate` | Deploy after 1 and 2 | 1, 2 | **YES** | Ledger rows in production; pause observed working |
| 4 | Rollback and pause rehearsal | Runbook written; not rehearsed | Rehearse after the window | 1, 3 | **YES** | Runbook section R checked and timed |
| 5 | Release B: freshness clock (ADR-075) | Built; local | Deploy after 3; set the correction date | 3 | **YES** | Freshness states sane for old events; evaluator boundary set |
| 6 | Release C: self-corroboration fix, no-percentage copy, EPS gate on | Built and tested; gate default off | Deploy with the pause on | 3, 5 | **YES** | No recalibration push; no beat / miss wording in production |
| 7 | Feed depth with the EPS gate on | **Not assessed on a device.** Earnings family leaves the feed | Look at the live feed with the gate on; decide whether it is enough to evaluate | 6 | **YES** (core usability) | A judgment by Logan / Chuck from a real device |
| 8 | Mobile Beta build: feedback control, trajectory, evidence, Ask context | Built; 260 mobile tests pass; not run on a device | Internal build after Release A | 3 | **YES** | Device acceptance sections 3, 5, 6 |
| 9 | Physical-device acceptance, including telemetry round trip | Script written | Run on the final build | 3, 6, 8 | **YES** | Signed script, no open evidence-integrity finding |
| 10 | Safety card owners | Card written; owners blank | Logan / Chuck assign | — | **YES** | Names on the card |
| 11 | Participant packet review, including advice wording | Drafted; not sent | Logan / Chuck review; compliance read | — | **YES** (before recruiting) | Approved text |
| 12 | Beta Entry Review | Not started | Hold after 1 to 11 | All above | **YES** | GO / HOLD recorded |

## Decisions waiting

| Decision | Options | Needed by |
|---|---|---|
| Ledger schema | Approve as built / change | Release A |
| Recalibration and notifications | Rely on the pause procedure for Beta 1 / add a model-version column to lifecycle state (schema) | Release C |
| Feed depth without EPS surprise | Accept price and analyst signals only / add the narrow SEC 8-K catalyst path first | Item 7 |
| Evidence label wording | Keep "High / Moderate / Low / Speculative evidence" for Beta 1 / adopt the quality-condition labels (specified, not built) | Before the mobile build |
| Vendor inquiry | Send the drafted Intrinio inquiry / do not | Not blocking |

## Not on the path (cannot delay Beta 1)

| Item | Why it is off the path |
|---|---|
| EPS-surprise with a matched provider | Disabled for Beta 1 by decision; vendor inquiry may run in parallel |
| Revenue trigger and revenue materiality | Comparability not proven |
| Price materiality bands, qualification gates for price and revenue | Shadow only; current price rule is unchanged and defensible |
| Quality-condition evidence labels | Specified; the existing label is truthful as worded |
| Supporting-signals list on the detail view | Needs a new API field; trajectory and evidence are shown |
| Per-observation record of blocked qualifications | Logged, not stored |
| Delivery receipts from the push provider | Delivery is recorded honestly as unknown |
| Telemetry retention bound | Volume is trivial at beta size |
| V1a proof re-run, candidate-source and exploration conformance gaps | Universe governance, not Beta 1 truthfulness |
| Removing the unused percentage ring component and legacy diagnostic screens | Not reachable in a production build |
| Larger universe, new domains, V4 interface, advanced prioritisation, broad news | Out of scope by REV4 2A |
