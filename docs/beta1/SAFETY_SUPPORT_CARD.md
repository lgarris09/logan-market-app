# Beta 1 safety and support card

One page. Names are assigned by Logan and Chuck; roles are filled in where a name is not yet decided.
Procedures: `RUNBOOK_PAUSE_ROLLBACK.md`.

## Owners

| Responsibility | Owner |
|---|---|
| Beta incident intake (reads in-app reports and the contact inbox daily) | ____________ |
| Evidence-integrity incident owner (decides what was wrong and what users are told) | ____________ |
| App / reliability incident owner | ____________ |
| Notification pause authority | ____________ |
| Rollback authority | ____________ |
| GO / HOLD authority | ____________ |
| Independent review of an evidence-integrity finding before it is closed | ____________ |

Escalation: intake owner → the incident owner for that type → GO / HOLD authority. Anyone on this card
may pause notifications first and explain afterwards.

## Two kinds of incident

**Evidence-integrity incident.** STRATUS stated or implied something about the world that was false,
stale, mis-attributed or unsupported. Examples: a wrong figure; an old event shown as current; a
comparison STRATUS cannot substantiate; a push that cannot be explained from the Decision Ledger; an
evidence label read by a user as a recommendation because of how STRATUS worded it.

In-app reports with reason "This seems wrong", "This is stale" or "I do not understand why I got this"
are treated as evidence-integrity until shown otherwise.

**Normal app defect.** Everything else: a crash, a layout problem, sign-in trouble, slow loading, a
missed tap. Fixed in the ordinary way; no pause needed.

## Response to an evidence-integrity incident

1. Pause notifications for as long as the cause is unknown.
2. Reconstruct from durable records: the feedback report (what was displayed), the opportunity's
   revisions, the ledger decision and dispatch rows, provider state at the time.
3. Correct it or disable the affected signal family. Replay the fix against the recorded case before
   resuming.
4. Tell the affected participant what was wrong, plainly.
5. Record the incident and what changed.

## What users see

| Situation | What the user sees |
|---|---|
| Provider degraded | The feed keeps what it can vouch for and marks the degraded state. No push is sent for affected items |
| Freshness cannot be established | The opportunity detail says STRATUS cannot currently confirm how recent the data is, or that it may be out of date. No push |
| Notifications paused | Nothing. The feed works normally; pushes do not arrive |
| Beta paused | The app's unreachable state, plus a message through the contact channel |
| An EPS comparison STRATUS cannot substantiate | Nothing in its place. STRATUS says less rather than state an unsupported comparison |

## How a report is tied to its opportunity

Each in-app report records the opportunity, the stable company identifier, the revision, the headline,
evidence label, trajectory and freshness state as displayed, the app build, the time, and the evidence
model version in force. Investigation starts from that record, not from the participant's memory of it.

## How a pause is communicated

One contact channel given to every participant at onboarding: ____________. A pause notice says what is
paused, that their data and Watch list are intact, and when the next update will come.

## Open operational gaps (to close before Beta Entry Review)

1. **The notification pause exists in the candidate build but is not deployed.** Today, stopping pushes
   means a deploy or stopping the application.
2. **Rollback has not been rehearsed.** The procedure is written and untested.
3. Owners above are unassigned.
