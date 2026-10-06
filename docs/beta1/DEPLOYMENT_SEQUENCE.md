# Beta 1 post-window deployment sequence

For approval by Logan and Chuck. Nothing here is executed. Every production step needs its own explicit
go-ahead; this document is the proposed order and the reasons for it.

Starting point: production is Fly v33 (`f105a0a`). The candidate is local branch `beta1/candidate`.

## Order

| # | Step | Kind | Why here |
|---|---|---|---|
| 0 | Close Operational Integrity: 72-hour final check, verdict recorded in REV4 | Evidence | Nothing else may touch production first |
| 1 | Rehearse pause and rollback is **not** possible yet (the pause is not deployed). Rehearse rollback v33 → v32 → v33 | Production, restart | Proves rollback before anything new depends on it |
| 2 | **Release A — safety and instrumentation.** Decision Ledger (three tables), notification fail-closed rules, pause switch, dispatch states, telemetry feedback event and account deletion fix, demo routes closed in live mode | Backend deploy, schema | Additive and behaviour-narrowing only. Gives every later step a pause and an audit trail. Requires schema approval |
| 3 | Verify A: ledger rows appear; a suppression reason is recorded; pause on / off works; rollback checklist passes | Production check | The pause must be proven before step 5 relies on it |
| 4 | **Release B — freshness clock (ADR-075).** Set `FRESHNESS_CLOCK_CORRECTED_FROM` to the deploy date in the same change | Backend deploy | Separate so its effect on freshness ratios and on the new freshness suppression rule is observable alone |
| 5 | **Release C — evidence truth.** Pause notifications **first**. Deploy self-corroboration fix (ADR-076), no-percentage copy (ADR-077), EPS gate on (ADR-079, `STRATUS_EPS_COMPARABILITY_GATE`). Wait one full poll cycle. Unpause | Backend deploy, flag | Recalibration changes stored confidence; see "Must not ship together" |
| 6 | Full test suites on the exact deployed commit | Local | |
| 7 | Internal mobile build from the same commit | Mobile build | After the backend it depends on |
| 8 | Physical-device acceptance (`DEVICE_ACCEPTANCE_SCRIPT.md`) | Acceptance | Includes the telemetry round trip and the pause |
| 9 | Beta Entry Review: GO / HOLD | Decision | |

Releases A, B and C can each be cut as a branch from `beta1/candidate`'s commits; the candidate branch
contains all three merged and tested together.

## Schema changes (all additive, all need explicit approval)

| Store | Change | Retention |
|---|---|---|
| `notification_ledger.db` (exists today, 0 bytes) | Creates `notification_candidates`, `notification_decisions`, `notification_dispatches` | 120 days, purged at startup and daily |
| `telemetry_events.db` | No table change. New event name and new keys inside the existing JSON `context` column | None today; a bound should be set before wider release |
| Everything else | None | |

No migration step is needed: tables are created on first open, and nothing rewrites existing rows.

## Backward compatibility

| Pairing | Result |
|---|---|
| New backend, current mobile build | Works. Nothing the current app sends is refused |
| New mobile build, current backend (v33) | **Do not ship.** Feedback is refused and Ask telemetry from an opportunity is dropped, because v33 rejects the new fields. Backend first, always |
| New backend rolled back to v33 after feedback exists | Degraded telemetry only; see the runbook, section 5 |

## Must not ship together, or without the pause

1. **The evidence change without the pause.** Removing self-corroboration lowers the stored confidence of
   affected opportunities. The lifecycle tracker treats a drop of 0.15 or more as a notification-worthy
   `confidence_decreased` revision. Without the pause, a model change would push to users as if the
   market had changed. Deploy with the pause on; lift it after one full poll.
2. **The mobile build before Release A.**
3. **Freshness and the evidence change in one release.** Both move what users see and what suppresses a
   push; separately, each effect can be attributed.
4. **The EPS gate before the ledger.** With the gate on, earnings-driven opportunities disappear from
   the feed. That should be visible in the audit trail when it happens.

## Rollback boundaries

- After A: roll back to v33 freely. New tables are ignored.
- After B: roll back to A freely.
- After C: roll back to B restores self-corroboration and unsupported EPS claims. Treat as a
  truthfulness regression; prefer pausing notifications and fixing forward.
- After feedback rows exist: rolling back past A degrades telemetry on the old build (not the feed).

## Expected visible effect on the feed

- EPS gate on: with the current provider, no earnings-surprise opportunity qualifies. In the 2026-10-05
  production snapshot the earnings family accounted for 20 opportunities. The feed then rests on price
  and analyst signals. **This is the largest user-visible change in the sequence and should be looked at
  on a device before Beta Entry**: a thin feed is a core-usability question, and row 11 of the scorecard
  ("enough to judge") depends on it.
- Freshness: items fetched recently stop being marked unavailable merely because the event is old.
- Evidence: confidence values fall where the same source was counted more than once.

## Open decisions this sequence needs

1. Schema approval for the three ledger tables.
2. Whether the EPS gate is turned on at Beta Entry given the feed-thinning above, or whether a narrow
   catalyst path (SEC 8-K) is wanted first for category breadth. The gate itself is a truthfulness
   requirement; the open point is what else fills the feed.
3. Whether to add the lifecycle model-version column (schema) so recalibration can never notify, or to
   rely on the pause procedure for Beta 1.
4. Owner names on the safety card.
