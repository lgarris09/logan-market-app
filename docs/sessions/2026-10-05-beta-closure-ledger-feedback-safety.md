# Beta closure: Decision Ledger gap audit, contextual feedback, safety card, EPS time-box

Date: 2026-10-05. Non-production work done while the 72-hour Operational Integrity window runs
(2026-10-05 20:57:06 UTC to 2026-10-08 20:57:06 UTC). Nothing here is deployed, wired or committed.
Governing statement: Master Plan REV4, Section 2A.

## 1. Decision Ledger gap audit (REV4 2A.9)

Compared: the 2A.9 attribution list against (a) what production v33 records today and (b) what the
undeployed Notification Ledger commit `b10c100` (ADR-071) would add.

| 2A.9 item | Production v33 today | Added by `b10c100` | Remaining gap |
|---|---|---|---|
| Opportunity ID | `event_id` in feed and telemetry; regenerated on every process start | `event_id`, `entity_id`, `thesis_id`, deterministic `candidate_id` | None for beta if `entity_id` + revision is the join key; `event_id` is not stable across restarts |
| Revision ID | `opportunity_revisions` (durable), `opportunity_revision` on telemetry | `RevisionSnapshot` | None |
| Model version | Not recorded | Contract `schema_version` only | **Gap.** No field says which scoring / qualification rules produced a decision |
| Category | Signal family in revisions (`trigger_codes`) | `signal_family` | None |
| Qualification outcome | Not recorded per opportunity (aggregate attempt counts only) | Not recorded | **Gap.** The five-state outcome and reason code exist only in the shadow module (ADR-078) |
| Evidence snapshot / provenance | Revision row: confidence, trigger codes, reason | `EvidenceCredibilitySnapshot`, `market_evidence`, `EarnedNotificationInputs` | Partial: no provider name, endpoint or fetch time per evidence item |
| External-event time | Not durable | `source_captured_at` (optional) | Partial: fetch time and event time are not separated |
| Detection time | `first_seen_at` (lifecycle) | `created_at` | None |
| Opportunity creation time | `first_seen_at`; revision `created_at` | Same | None |
| Freshness / degraded state | Aggregate ratios only | `freshness_state`, `provider_degraded` per candidate | None once the ledger is on (meaning changes with ADR-075, not yet deployed) |
| Notification candidacy | Not recorded | `notification_candidates` | None |
| SEND / SUPPRESS | Dispatched IDs only; suppressions leave no record | `notification_decisions`, append-only on transition | None |
| Deterministic reason | Not recorded | 8 suppression reasons + 1 send reason, all reused from live policy | None |
| Delivery state | "Dispatched" is recorded after the HTTP call returns, without reading the response | Not addressed | **Gap.** No Expo ticket or receipt is read; a rejected push is recorded as sent |
| Exposure / open | `impression` via `/v1/interactions`; `opportunity_opened` telemetry | — | Impression durability not verified in this audit |
| Detail view | `opportunity_opened` (durable, with revision) | — | None |
| Watch / unwatch | `watch_created` / `watch_removed`, `watches.db` | Watch state at decision time | None |
| Ask with opportunity context | `ask_started` / `ask_follow_up` carry a session ID only | — | **Gap.** The event schema forbids an opportunity ID on Ask events |
| Explicit usefulness feedback | Server accepts `usefulness_feedback_submitted` (boolean) | — | **Gap.** No mobile screen sends it |
| Dismissal / not-useful feedback | `dismiss` interaction type exists | — | **Gap.** No reason is captured; see section 2 |
| Return behaviour | `opportunity_returned_to` with previous revision | — | None |

Findings that matter for sequencing:

1. `b10c100` covers the notification half of 2A.9 well and is shadow-only. It does not cover model
   version, qualification outcome, delivery state, Ask context or feedback.
2. It applies to the production commit `f105a0a` with one conflict, in `docs/DECISIONS.md` only (ADR
   numbering). Code merges cleanly. Its tests have not been re-run on that base.
3. It creates two tables (`notification_candidates`, `notification_decisions`) in
   `/data/notification_ledger.db`, the file that exists today at 0 bytes. That is a schema change and
   needs explicit approval.
4. It has no retention bound (stated in its own docstring). Decisions append only on a transition, so
   growth is slow, but after this sprint's memory work an unbounded store should not ship without a
   stated bound.
5. Production has no client telemetry since 2026-09-19 (`telemetry_events.db` last written then), no
   push dispatch record since 2026-09-03 and no Watch change since 2026-09-10. The instrumentation paths
   have not been exercised recently; physical-device acceptance should include a telemetry round trip.

Smallest set that closes 2A.9 (proposal, not started):

- A. Deploy `b10c100` rebased on production, with a retention bound added.
- B. Add `model_version` (one constant string, bumped with any scoring or qualification change) to
  candidates, revisions and feedback.
- C. Record the qualification state and reason code per opportunity when the ADR-078 gates are wired.
  Until then record nothing rather than a guess.
- D. Read the Expo push ticket and store accepted / rejected per message. Receipts can wait.
- E. Allow `opportunity_id` on Ask events when Ask is opened from a card.
- F. Contextual feedback, section 2.

A to F touch contracts, a new store, and the mobile client. Each needs approval; A and F need schema
approval.

## 2. Opportunity-linked beta feedback design (REV4 2A.10)

Entry point: one "Something off?" control on the opportunity detail view, not on feed cards.
Five options, single select, optional free-text note (500 characters):

| Label shown | Stored code |
|---|---|
| This seems wrong | `seems_wrong` |
| This is stale | `stale` |
| This is not useful to me | `not_useful` |
| I do not understand why I got this | `unclear_why` |
| I expected something else | `expected_else` |

Confirmation copy: "Thanks. This report is attached to this opportunity so we can look into it."
No promise of a reply or a fix.

Record, captured at submission and never reconstructed later:

- report ID (client-generated UUID, idempotent on resubmission), user ID (server-resolved), submitted time;
- entity ID, opportunity revision, event ID;
- reason code, note;
- displayed evidence as the user saw it: headline, evidence label, trigger codes, freshness / degraded
  state, `as_of` time of the feed response;
- model version (section 1, item B);
- surface (detail view, notification-opened);
- app build.

Rules:

- Raw fact only. A report does not change scoring, ranking, Watch state or the user model. Only the
  Learning System writes durable user-model updates, and nothing here routes to it.
- `not_useful` is the only code about personal relevance; the other four are about evidence or
  explanation and are reviewed as possible truthfulness incidents (section 3).
- Deleted with the account, like every other user-scoped store.
- Bounded: note length capped, one row per report ID, retention stated up front.

Implementation shape: extend the existing telemetry event vocabulary with one event
(`opportunity_feedback_submitted`) and typed context fields, rather than adding a new store. This keeps
one durable event history and reuses its identity, idempotency and account-deletion handling. It changes
a closed, versioned contract, so it needs approval; the displayed-evidence snapshot is the only part that
may justify its own table.

Open decision: whether the existing boolean `usefulness_feedback_submitted` is kept alongside or
replaced. Recommendation: keep it in the schema, do not build UI for it.

## 3. Beta safety / support card (REV4 2A.12)

Draft. Owner cells are left blank for Logan / Chuck to assign; the mechanisms are what exists today.

**Two operational gaps, to be resolved before the Beta Entry Review:**

1. **No simple notification pause switch.** Stopping pushes today means a deploy or stopping the app.
2. **Rollback has not been rehearsed.** The procedure below is written, not tested.

The smallest acceptable solution for each is a Logan / Chuck decision.

| Item | Owner | Proposed mechanism |
|---|---|---|
| Who receives beta incident reports | | In-app reports (section 2) plus one stated contact address given to participants |
| Who investigates truthfulness / evidence incidents | | Reconstruct from revisions, ledger and the feedback record; independent review before closing |
| Who can pause notifications | | **No pause switch exists today**: pausing means a deploy or stopping the app. A config-level notification pause is recommended before beta |
| Provider degradation | | Feed shows the degraded state; pushes are suppressed (`provider_degraded_suppressed` already exists); 2A.11 fail-closed applies |
| What users see when freshness cannot be established | | A delayed / degraded marker on the feed; no push. Copy to be approved; it must not imply the data is current |
| How the beta is paused | | Notifications off first; then, if needed, the app stopped on Fly. Participants told through the contact channel. Needs a stated owner and a tested procedure |
| HOLD authority | | |
| App bug vs evidence-integrity incident | | Evidence-integrity: STRATUS stated or implied something about the world that was false, stale, mis-attributed or unsupported (wrong number, stale event shown as current, a beat / miss that is not comparable, a push that cannot be explained from the ledger). Everything else (crash, layout, sign-in, slow load) is an app bug. In-app codes `seems_wrong`, `stale`, `unclear_why` are treated as evidence-integrity until shown otherwise |
| Rollback / pause procedure | | Roll back to the previous Fly release image; the durable stores are additive, so no data rollback. To be rehearsed once before beta, outside the integrity window |

Response rule proposed for an evidence-integrity incident: pause notifications for the affected category,
reconstruct the decision from durable records, correct or disable the category, then tell the affected
participant what was wrong. Do not resume the category on the strength of a fix that has not been replayed.


## 4. EPS provider contract investigation (time-boxed, REV4 2A.5)

Step A (current provider) is closed: FMP's `epsActual` basis is inconsistent across issuers (GAAP diluted
for AMZN, GOOGL, PLD; adjusted for KO) and no endpoint on the current plan states the consensus basis.

Step B (narrowest alternate), from public documentation only, no account opened and no vendor contacted:

- Intrinio "Zacks EPS Surprises" documents `eps_actual` as the non-GAAP figure released by the company
  as interpreted by Zacks, `eps_mean_estimate` as the pre-release mean estimate, and
  `eps_actual_zacks_adj` as the adjustments reconciling to GAAP. Actual and estimate come from one vendor
  with a stated basis, which is what the comparability gate requires.
- Intrinio's product page lists the feed as available on an Enterprise plan only, with history charged
  separately. No price is published.
- Not established from public pages: price; whether display to end users in a consumer app is licensed;
  how soon after a release the row appears (the page says daily updates, which may be too slow for an
  earnings-day signal); fiscal-period identifiers; estimate count and timestamp.

Reading: the data contract looks right, the commercial terms look wrong for Beta 1. An enterprise-only
feed with daily updates is unlikely to pass "quickly and reliably".

**Decision (Logan / Chuck, 2026-10-05): step C.** Unsupported EPS-surprise qualification is not required
for Beta 1. Where the actual / consensus basis cannot be proven: no EPS beat / miss trigger, no EPS
materiality, no beat / miss language. Other validated earnings-result facts and all independently valid
analyst, price, revision / trajectory, Watch, Ask and notification behaviour are retained. One vendor
inquiry may be sent; its answer does not block Beta 1. No broad provider migration.

Draft inquiry (not sent):

> We are evaluating the Zacks EPS Surprises feed for a consumer mobile app that shows, per company, whether
> reported EPS was above or below consensus. Could you confirm: (1) that `eps_actual` and
> `eps_mean_estimate` are always on the same non-GAAP basis for a given row, and how exceptions are
> flagged; (2) how long after a company's release the row is available through the API; (3) whether each
> row carries the fiscal period, the number of estimates and the time the consensus was last updated;
> (4) whether displaying these values to end users in a consumer app is permitted, and under which plan;
> (5) pricing for roughly 100 US large-cap tickers without history. Thank you.

Sources: https://intrinio.com/products/eps-surprises ,
https://docs.intrinio.com/documentation/web_api/get_security_zacks_eps_surprises_v2

## 5. Beta Critical Path, as of this note

| # | Item | State |
|---|---|---|
| 1 | Memory stability (Phase A) | PASS |
| 2 | Scheduler restart safety (Phase B) | PASS |
| 3 | 72-hour Operational Integrity window | Running, ends 2026-10-08 20:57:06 UTC |
| 4 | Freshness = fetch age (ADR-075) | Built, local; deploy after the window |
| 5 | Self-corroboration fix (ADR-076) | Built, local |
| 6 | No-percentage presentation (ADR-077) | Built, local |
| 7 | EPS: disable unsupported EPS-surprise for Beta 1 | Decided; change not yet built |
| 8 | Qualification gates (ADR-078) | Shadow only; wiring not approved |
| 9 | Decision Ledger, narrow | `b10c100` approved as the post-window basis, with conditions; five gaps to close or account for |
| 10 | Contextual feedback | Approved to build locally |
| 11 | Notification fail-closed + pause switch | Partly present; pause switch missing |
| 12 | Safety / support card | Drafted (section 3); owners unnamed |
| 13 | Success / failure and participant criteria | In REV4; no work |
| 14 | Physical-device acceptance | Pending; add a telemetry round trip |
| C | News / catalysts (conditional) | Decision needed on the 8-K path |
