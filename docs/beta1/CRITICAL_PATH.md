# Beta 1 critical path

As of 2026-10-07 13:30 UTC. Governing statement: Master Plan REV4, Section 2A. The Beta Cut Line is
applied: an item is a blocker only if Beta 1 would otherwise be unreliable, untruthful, unusable at its
core, or unmeasurable.

## Active path

| # | Work item | State | Next action | Depends on | Blocker | Evidence that closes it |
|---|---|---|---|---|---|---|
| 1 | 72-hour Operational Integrity window | Running. Interim check done 2026-10-07: one process, no restart, no faults, scheduler state unchanged, memory inside criteria (see REV4 6.3). Three samples missed to workstation DNS, not interpolated | Final check 2026-10-08 20:57 UTC | Nothing touching production | **YES** | Final report: one process, no OOM, RSS within criteria, feed and scheduler state unchanged |
| 2 | **Feed depth with the EPS gate on** | Gate alone: 3 of 21. **Narrow SEC 8-K catalyst path built locally (ADR-084): replay gives 7 to 9 opportunities in three equal families.** Varied, still modest outside a reporting season | Logan / Chuck judge sufficiency (`CATALYST_PATH.md` section 9); supply the SEC User-Agent contact | — | **YES** (core usability) until judged on a device | The gated feed with catalysts seen on a device, and a recorded judgment |
| 3 | Release A: ledger, fail-closed notifications, pause, dispatch states, feedback event | Built and tested. Schema approved 2026-10-06 | Deploy after 1 | 1 | **YES** | Checklist in `LEDGER_SCHEMA_APPROVAL.md` |
| 4 | Rollback and pause rehearsal | Runbook written; not rehearsed | Rehearse after the window | 1, 3 | **YES** | Runbook section R checked and timed |
| 5 | Release B: freshness clock (ADR-075) | Built; local | Deploy after 3; set the correction date | 3 | **YES** | Freshness states sane for old events |
| 6 | Release C: self-corroboration fix, condition-based evidence labels, EPS gate on | Built and tested | Deploy after 5, with notifications paused; verify no SEND; unpause | 3, 5, and the decision in 2 | **YES** | No recalibration push; no beat / miss wording; labels read Supported or Limited |
| 6a | Release D: company-filing catalysts | Built and tested; flag default off | Deploy after 6, paused for the first poll | 6, SEC User-Agent | **YES** | Filing opportunities in the feed with provenance; no first-poll push |
| 7 | Mobile Beta build | Built; 263 mobile tests pass; not run on a device | Internal build after Release A | 3 | **YES** | Device acceptance sections 3, 5, 6 |
| 8 | Physical-device acceptance, including telemetry round trip | Script written | Run on the final build | 3, 6, 7 | **YES** | Signed script, no open evidence-integrity finding |
| 9 | Safety card owners | Card written; owners blank | Logan / Chuck assign | — | **YES** | Names on the card |
| 10 | Participant packet review, including advice wording | Drafted; not sent | Logan / Chuck review; compliance read | — | **YES** (before recruiting) | Approved text |
| 11 | Beta Entry Review | Not started | Hold after 1 to 10 | All above | **YES** | GO / HOLD recorded |

## Closed since the last version

| Item | How it closed |
|---|---|
| Ledger schema approval | Approved 2026-10-06, 120-day retention |
| Recalibration and notifications | Pause procedure for Beta 1; no schema change |
| Evidence label wording | Condition-based labels built (ADR-083) |
| WHAT CHANGED repeats the headline | Detail now shows the lifecycle delta, or omits the section |
| Supporting-signals list lacked an API field | `signal_families` added to the feed item from existing trigger data |
| Vendor inquiry | Drafted for Logan to send; non-blocking by rule |
| Feed-depth decision | Narrow SEC 8-K path directed 2026-10-07 and built locally |

## Decisions waiting

| Decision | Options | Needed by |
|---|---|---|
| SEC User-Agent contact | An operator name and contact address the SEC can reach | Release D |
| Is the catalyst-augmented feed enough? | Proceed / time Beta 1 to a reporting season / reconsider scope with evidence | Beta Entry Review |
| Owner and review date for provisional catalyst parameters | — | Before Release D |

## Not on the path (cannot delay Beta 1)

| Item | Why it is off the path |
|---|---|
| Company news under 8-K items 8.01 / 7.01, guidance changes, size of agreements or financings | Need filing text read and classified; a stop condition |
| EPS-surprise with a matched provider | Disabled for Beta 1 by decision; inquiry runs in parallel |
| Revenue trigger and revenue materiality | Comparability not proven |
| Price materiality bands, qualification gates for price and revenue | Shadow only; the live price rule is unchanged and defensible |
| Lifecycle model-version guard | Post-beta by decision, unless repeated migrations show the need |
| Separating feed order from the confidence score | The score is no longer shown; ordering is unchanged |
| Per-observation record of blocked qualifications | Logged, not stored |
| Delivery receipts from the push provider | Delivery is recorded honestly as unknown |
| Telemetry retention bound | Volume is trivial at beta size |
| V1a proof re-run, candidate-source and exploration conformance gaps | Universe governance, not Beta 1 truthfulness |
| Removing the unused percentage ring component and legacy diagnostic screens | Not reachable in a production build |
| Larger universe, new domains, V4 interface, advanced prioritisation, broad news | Out of scope by REV4 2A |
