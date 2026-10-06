# Beta 1 runbook: pause notifications, disable a flag, roll back

Status: drafted 2026-10-06. **Not rehearsed.** A live rehearsal would restart production and end the
72-hour Operational Integrity window, so it is a post-window, pre-beta acceptance action (step R below).
App: `stratus-api` on Fly. HOLD is declared by: ____________ (to be assigned).

Every command needs `FLY_API_TOKEN` in the environment. Setting or unsetting a secret restarts the
machine (seconds of downtime); it does not rebuild or redeploy the image.

## 1. Pause notifications

```
flyctl secrets set STRATUS_NOTIFICATIONS_PAUSED=true -a stratus-api
```

- Effect: no new push is sent. Each would-be interruption is recorded as SUPPRESS with reason
  `beta_notifications_paused`. The dispatch loop sends nothing.
- Not affected: the feed, Watch, Ask, lifecycle state, every durable store, the mobile app.
- Already sent: a push already handed to the push provider cannot be recalled.
- Confirm: `flyctl logs -a stratus-api` shows `beta_notifications_paused` on the next alert-level
  decision; `/v1/dev/notification-ledger` shows the reason in its suppression breakdown.

Resume:

```
flyctl secrets unset STRATUS_NOTIFICATIONS_PAUSED -a stratus-api
```

No backlog is released. A revision suppressed while paused is not sent later; only a new material
revision after the resume can notify.

## 2. Disable a problematic feature flag

| Flag | On means | To disable |
|---|---|---|
| `STRATUS_EPS_COMPARABILITY_GATE` | EPS beat / miss only with proven comparability | Leave on. Turning it off re-enables unsupported EPS claims; that is a truthfulness regression, not a rollback |
| `STRATUS_NOTIFICATIONS_PAUSED` | Pushes paused | `flyctl secrets unset ...` |
| `STRATUS_LLM_ASK` | Ask answers through the LLM-grounded path | Set in `fly.toml [env]`; turning it off needs a deploy (Ask then uses the deterministic template) |
| Universe scheduler flag | Scheduled Universe reevaluation | Set in `fly.toml [env]`; changing it needs a deploy |

Flags set in `fly.toml [env]` change only with a deploy. Flags set as secrets change with a restart. A
secret overrides nothing in `[env]` unless the names match; do not define the same name in both.

## 3. Roll back to the last known-good release

```
flyctl releases -a stratus-api --image          # find the previous release and its image
flyctl deploy -a stratus-api --image <image-of-known-good-release>
```

Last known-good as of this draft: v33 (commit `f105a0a`), subject to the 72-hour window closing as PASS.

## 4. Confirm health after any of the above

1. `curl https://stratus-api.fly.dev/health` returns 200, `status: online`.
2. `flyctl status -a stratus-api`: one machine, started, checks passing, the expected release.
3. Feed: `GET /v1/opportunities` returns items, `provider_degraded` false (or true with a known provider
   outage), no simulated entities.
4. Provider: `GET /v1/dev/fmp-budget` shows calls within budget and no sustained failures.
5. Scheduler: read `universe_scheduler_state` with the read-only state script
   (`docs/sessions/2026-10-05-phaseB_state.py`). `last_outcome` is `succeeded` and the next-due time is
   unchanged. A restart must not start a new reevaluation.
6. Memory: RSS settles near 110 MB within about two hours, not rising.
7. Faults: `GET /v1/dev/faults/recent` shows nothing new.

## 5. What makes a rollback unsafe

| Change in the Beta 1 candidate | Rollback to v33 |
|---|---|
| New ledger tables (`notification_candidates`, `notification_decisions`, `notification_dispatches`) | Safe. Additive; v33 does not open the file |
| New telemetry event `opportunity_feedback_submitted` and new context fields | **Degraded.** v33 cannot parse those rows. Its first telemetry request after start fails and its in-memory duplicate index is incomplete; writes still succeed and nothing is lost. Feed, Watch, Ask and notifications are unaffected. The candidate build itself skips unreadable rows |
| New suppression reasons | Safe. Stored as text; v33 never reads them |
| Freshness clock (ADR-075) | Safe. No stored state changes meaning; the V1a evaluator needs the correction date |
| EPS gate | Safe. A flag; no stored state |
| New mobile build against a rolled-back backend | **Degraded.** Feedback reports are refused (the app says so) and Ask telemetry from an opportunity is dropped. Everything else works |

No change in the candidate rewrites or deletes existing rows, so no data rollback is ever needed. Do not
delete `/data` files as part of a rollback.

## 6. Pause the beta

1. Pause notifications (section 1).
2. If the feed itself is untrustworthy: `flyctl scale count 0 -a stratus-api` stops the API. The app then
   shows its unreachable state. `flyctl scale count 1` restores it.
3. Tell participants through the contact channel on the safety card. Say what is paused and that their
   data is intact. Do not give a time for return unless it is known.

## R. Rehearsal, required before Beta Entry Review (after the 72-hour window)

- [ ] Pause, observe a `beta_notifications_paused` decision, resume.
- [ ] Roll back one release and forward again; run section 4 after each.
- [ ] Confirm the scheduler did not rerun on either restart.
- [ ] Record the time each step took.
