# Beta 1 post-window deployment package

Final draft, 2026-10-08. For approval by Logan and Chuck. Nothing here is executed, and every
production step needs its own explicit go-ahead. Supersedes the earlier drafts of this file.

- Production today: Fly v33, commit `f105a0a`.
- Candidate: local branch `beta1/candidate` (unpushed). 1,890 Python tests and 263 mobile tests pass.
- Decisions already made are listed in section 8 and are not re-opened here.

## 1. One fact that shapes the plan

The candidate cannot be split into separate release branches by cherry-pick. I tried: the commit that
adds the pause switch and fail-closed rules also adds the EPS gate, which depends on the qualification
module from the evidence branch. The pieces were built and tested together.

So there are two ways to deploy. Both are safe; they differ in what can be attributed afterwards.

| | Option 1 — one build, staged flags (recommended) | Option 2 — re-cut into separate releases |
|---|---|---|
| What deploys first | The whole candidate, with the EPS gate off, catalysts off, notifications paused | Safety and instrumentation only |
| Then | Flags turned on one at a time, with a check between each | Freshness, then evidence, then flags, each its own release |
| Work before the first deploy | None beyond approval | Re-cut the commits into three branches and re-run every suite on each. Roughly a day, and it produces code that has not been tested in that shape before |
| Attribution | The flagged changes (EPS gate, catalysts) are attributable. The unflagged ones arrive together | Each change attributable |
| Rollback | One step to v33 | One step per release |

Unflagged changes that arrive together under option 1: Decision Ledger, notification fail-closed rules,
dispatch states, the freshness clock, the self-corroboration fix, condition-based evidence labels, the
feedback event, demo routes closed, new feed fields.

Recommendation: option 1. What is deployed is exactly what was tested. The cost is that an unexpected
change in freshness ratios or confidence values after the deploy could come from either the freshness
clock or the self-corroboration fix; the ledger and logs record enough to tell them apart after the
fact, but not at a glance. If you want that separation up front, choose option 2 and accept the day.

## 2. Sequence (option 1)

| # | Step | Kind | Check before moving on |
|---|---|---|---|
| 0 | Close Operational Integrity: final review recorded in REV4 | Evidence | Verdict is PASS by the locked criteria |
| 1 | Rehearse rollback: v33 → v32 → v33 | Production, restarts | Runbook section 4 after each; scheduler does not rerun |
| 2 | Push `beta1/candidate`; open the PR | Git | Approved explicitly |
| 3 | **Deploy the candidate build** with `STRATUS_NOTIFICATIONS_PAUSED=true`, EPS gate unset, catalysts unset | Backend deploy; creates three ledger tables | Health; feed returns; ledger has three tables and rows; every would-be push recorded as `beta_notifications_paused`; no SEND |
| 4 | Let one full poll complete. Validate the recalculation | Observation | Confidence fell only where a source was counted more than once; revisions are explained; freshness states are sane for old events; labels read Supported or Limited |
| 5 | Lift the pause. Confirm no backlog | Flag (restart) | No SEND for any revision created while paused |
| 6 | Watch memory for the same warm-up period as Phase A (about three hours) | Observation | Plateau comparable to v33 |
| 7 | Pause. Turn the EPS gate on (`STRATUS_EPS_COMPARABILITY_GATE=true`) | Flag (restart) | Earnings-surprise opportunities leave the feed; no beat / miss wording anywhere |
| 8 | Set `STRATUS_SEC_USER_AGENT`, then `STRATUS_SEC_FILING_CATALYSTS=true` | Flags (restart); new outbound provider | Filing opportunities appear with provenance; log shows declined filings with reason codes; feed is 7 to 9 items in three families, or an explained difference |
| 9 | Let one full poll complete, then lift the pause | Flag (restart) | No first-poll push for the filings that appeared at once |
| 10 | Rehearse the pause and rollback (runbook section R) | Production | Timed and recorded |
| 11 | Set `FRESHNESS_CLOCK_CORRECTED_FROM` to the step-3 date on the V1a evaluator branch | Local | Evaluator recognises the boundary |
| 12 | Internal mobile build from the deployed commit | Mobile build | Builds |
| 13 | Physical-device acceptance (`DEVICE_ACCEPTANCE_SCRIPT.md`) | Acceptance | Signed, no open evidence-integrity finding |
| 14 | Beta Entry Review | Decision | GO / HOLD |

Steps 7 and 8 can share one restart if you prefer fewer restarts to finer attribution.

Each flag change is a Fly secret and restarts the machine. Steps 3 to 9 involve about five restarts over
a day; the restart-safety work of Phase B is what makes that routine.

## 3. Schema (approved 2026-10-06)

| Store | Change | Retention |
|---|---|---|
| `notification_ledger.db` (0 bytes today) | Creates `notification_candidates`, `notification_decisions`, `notification_dispatches` | 120 days; purged at startup and daily |
| `telemetry_events.db` | No table change; one new event name and new keys in the existing JSON column | None today |

Reference and execution checklist: `LEDGER_SCHEMA_APPROVAL.md`. No migration step; nothing rewrites
existing rows. The catalyst path adds no schema and no store.

## 4. Configuration introduced

| Variable | Default | Set at | Meaning |
|---|---|---|---|
| `STRATUS_NOTIFICATIONS_PAUSED` | off | Step 3 on, 5 off, 7 on, 9 off | Suppresses every new push; recorded reason `beta_notifications_paused` |
| `STRATUS_EPS_COMPARABILITY_GATE` | off | Step 7 | No earnings beat / miss / in-line without proven comparability |
| `STRATUS_SEC_FILING_CATALYSTS` | off | Step 8 | SEC Form 8-K catalyst path |
| `STRATUS_SEC_USER_AGENT` | unset | Step 8 | `STRATUS Beta 1 / Garris Engineering LLC; contact=<company-controlled address>`. Without a valid value no SEC request is made. Never in source |
| `STRATUS_NOTIFICATION_LEDGER_RETENTION_DAYS` | 120 | Not set | Leave at the approved default |

## 5. Compatibility

| Pairing | Result |
|---|---|
| New backend, current mobile build | Works. New feed fields are additive; the old label field is still served |
| New mobile build, backend v33 | **Do not ship.** Feedback is refused and Ask telemetry from an opportunity is dropped. Backend first |
| Rolled back to v33 after feedback rows exist | Telemetry degraded on v33 only; feed, Watch, Ask, notifications unaffected (runbook section 5) |

## 6. Rules that are not optional

1. **Notifications are paused across every step that changes what qualifies or how evidence is scored**
   (steps 3 to 5 and 7 to 9). The evidence transition can lower stored confidence by enough to count as
   a notification-worthy revision, and the catalyst path makes up to two weeks of filings appear at
   once. Neither is market news. Procedure: pause, deploy or flip, let one poll recalculate, verify no
   SEND and no backlog, validate feed and revision state, re-enable.
2. **Backend before mobile.**
3. **The EPS gate is not turned on without the catalyst path following in the same session.** Between
   steps 7 and 9 the feed is about three items; that state should last minutes, not days.
4. **No SEC request without a configured, valid User-Agent.** Enforced in code.

## 7. Rollback boundaries

| After step | Roll back by | Note |
|---|---|---|
| 3 to 6 | Redeploy the v33 image | New tables are ignored by v33. Restores self-corroboration and the old freshness clock |
| 7 | Unset the EPS gate | Restores unsupported beat / miss claims. A truthfulness regression; prefer pausing and fixing forward |
| 8 to 9 | Unset the catalyst flag | Filing signals stop on the next poll; opportunities resting only on a filing age out |
| Any | Pause notifications first | Always available once step 3 is live |

No step requires a data rollback. Do not delete `/data` files.

## 8. Decisions already made

| Date | Decision |
|---|---|
| 2026-10-05 | Unsupported EPS-surprise is disabled for Beta 1; a vendor answer does not block |
| 2026-10-05 | Notifications fail closed and can be paused |
| 2026-10-06 | Ledger schema approved: three additive tables, 120-day retention |
| 2026-10-06 | Recalibration handled by the pause procedure; no lifecycle model-version field |
| 2026-10-06 | Evidence labels are condition-based |
| 2026-10-07 | Narrow SEC 8-K catalyst path, taxonomy and fail-closed behaviour accepted |
| 2026-10-08 | A 7 to 9 item feed is sufficient for the Beta 1 candidate; category scope stops here |
| 2026-10-08 | SEC User-Agent format fixed; contact value to come from Logan |
| 2026-10-08 | Catalyst parameters stay provisional; review after about two weeks of beta evidence (`PROVISIONAL_PARAMETERS.md`) |

## 9. What this package still needs from Logan and Chuck

1. Option 1 or option 2 (section 1).
2. The company-controlled contact address for the SEC User-Agent.
3. Approval to push the branch and open the PR (step 2), after the window closes.
4. Whether steps 7 and 8 share a restart.
5. Owner names on the safety card.

## 10. Not verified by anything in this package

- Nothing has run on a device.
- The candidate has not run against live providers: not the market-data provider with the gate on, and
  not the SEC. The feed composition in `CATALYST_PATH.md` is a replay.
- Memory behaviour of the candidate build in production is unknown. It adds ledger writes and a second
  provider client; step 6 exists to look.
- The pause and rollback have not been rehearsed.
