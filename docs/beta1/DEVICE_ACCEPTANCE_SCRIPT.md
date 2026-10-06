# Beta 1 physical-device acceptance script

Run on a physical device against the final Beta build and the deployed Beta backend. One pass per
platform shipped. Record build number, backend release, device, OS, tester, date. Any unchecked box is a
finding; evidence-integrity findings (marked **EI**) block Beta Entry.

Build ______ · Backend release ______ · Device ______ · OS ______ · Tester ______ · Date ______

## 1. Startup and sign-in
- [ ] Clean install launches to onboarding without error.
- [ ] Existing session relaunches straight to the feed.
- [ ] New sign-in completes and lands on the feed.
- [ ] Expired session recovers (sign in again) without losing the Watch list.
- [ ] Airplane mode at launch shows the unreachable state, not a blank screen or stale data presented as live.
- [ ] Restoring the network recovers without restarting the app.

## 2. Feed
- [ ] Feed loads with real companies only. No simulated or demo entity appears. **EI**
- [ ] Order is stable across two refreshes with no intervening change.
- [ ] Each item shows its signal type.
- [ ] Empty state (no qualifying opportunities) reads as "nothing right now", not as an error.
- [ ] Provider-degraded state is visibly marked when the provider is failing.
- [ ] No confidence percentage or numeric score anywhere on the feed. **EI**
- [ ] No earnings beat / miss wording appears while the EPS gate is on. **EI**

## 3. Opportunity detail
- [ ] Headline states the objective event.
- [ ] WHAT CHANGED describes the change and does not just repeat the headline.
- [ ] WHY IT MATTERS NOW explains timing, with no mention of notification mechanics.
- [ ] STRATUS TAKE appears only when it says something personal; otherwise absent.
- [ ] TRAJECTORY shows a state and a reason, worded about evidence, not price expectations. **EI**
- [ ] EVIDENCE uses the same label as the feed for the same item. **EI**
- [ ] When freshness cannot be confirmed, the detail says so.
- [ ] The analysis-not-advice line appears exactly once.
- [ ] VoiceOver / TalkBack reads no percentage for evidence. **EI**

## 4. Watch
- [ ] Watch an opportunity: the control changes immediately.
- [ ] Force-quit and relaunch: still watched.
- [ ] Unwatch: the control changes immediately and survives a relaunch.
- [ ] Watching does not change the item's evidence label or headline. **EI**
- [ ] Backend shows `watch_created` and `watch_removed` events for this user (section 9).

## 5. Ask STRATUS
- [ ] "Ask STRATUS about this" opens Ask with the company named.
- [ ] The first answer is about the selected opportunity and its current state.
- [ ] Asked "what happened", "why did you surface this", "what changed", "what supports it", "what is
      uncertain", "why might it matter to me": each answer is grounded in the opportunity. **EI**
- [ ] Asked for a recommendation ("should I buy"): Ask declines to advise. **EI**
- [ ] Uncertainty is stated, not smoothed over.
- [ ] Backend shows `ask_started` with the opportunity, company and revision attached (section 9).

## 6. Feedback
For each of the five options, on a real opportunity:
- [ ] This seems wrong
- [ ] This is stale
- [ ] This is not useful to me
- [ ] I do not understand why I got this
- [ ] I expected something else

And:
- [ ] The confirmation appears after sending.
- [ ] With the network off, the app says the report did not go through and offers to try again.
- [ ] A note of several sentences is accepted.
- [ ] Backend shows each report with company, revision, displayed headline, evidence label, trajectory,
      freshness state, app build and model version (section 9).
- [ ] After a report, the opportunity is unchanged: same label, same position logic, same Watch state. **EI**

## 7. Notifications
- [ ] Push permission prompt appears once and registration succeeds.
- [ ] A SEND: a push arrives for a new material revision, and the ledger shows candidate, SEND,
      dispatch row with `dispatch_accepted`.
- [ ] Tapping the push opens that opportunity.
- [ ] A SUPPRESS: the ledger shows a suppression with its reason and no push arrived.
- [ ] No second push for the same revision. **EI**
- [ ] With the provider degraded, no push arrives; the ledger shows the degraded or freshness reason. **EI**
- [ ] Pause switch on: no push arrives; the ledger shows `beta_notifications_paused`. Pause off: no backlog
      is delivered.
- [ ] Push text contains no confidence percentage and no beat / miss claim. **EI**

## 8. Revisions
- [ ] A real external evidence change produces a new revision and an updated card.
- [ ] A provider correction of the same event is shown as a revision, not as corroboration. **EI**
- [ ] A model-version deploy alone produces no push. (Deploy with the pause on; confirm.) **EI**
- [ ] "Since you last looked" reflects a real change and is absent on first view.

## 9. Telemetry round trip
Production recorded no client telemetry between 2026-09-19 and this draft, so this is tested explicitly.
- [ ] `opportunity_opened` recorded for an open on this device.
- [ ] `opportunity_returned_to` recorded on reopening after a revision.
- [ ] `watch_created` / `watch_removed` recorded.
- [ ] `ask_started` / `ask_follow_up` recorded with opportunity context.
- [ ] `opportunity_feedback_submitted` recorded for all five reasons.
- [ ] Every event carries this user's server-resolved identity.
- [ ] Deleting the account removes this user's telemetry, Watch list and ledger rows.

## 10. Restart and recovery (after Operational Integrity has closed)
- [ ] Backend restart: feed returns, Watch list intact, no duplicate push, scheduler does not rerun.
- [ ] App cold start during backend restart shows the unreachable state and recovers.

## 11. Rollback and pause (before Beta Entry)
- [ ] `RUNBOOK_PAUSE_ROLLBACK.md` section R completed and timed.

## Result
- [ ] All boxes checked, or every unchecked box has a written disposition.
- [ ] No open **EI** finding.

Signed ____________ Date ____________
