# Decision Ledger schema — approved for Beta 1

Approved by Logan and Chuck on 2026-10-06: the three additive tables below as designed, 120-day
retention with a startup purge and a daily purge, and feedback through the existing telemetry event
path. This document is the reference for executing Release A after the 72-hour window. It is not to be
re-decided at deployment; a change to anything here is a new decision.

Scope limit, also approved: this is not an analytics store and is not to be extended into one.

## Where

File: `/data/notification_ledger.db` (SQLite). It exists in production today at 0 bytes and is created
empty by nothing currently deployed. Path override: `STRATUS_NOTIFICATION_LEDGER_DB_PATH`. The store
opens only when durable persistence is enabled (`STRATUS_PERSIST_MEMORY`, already on in production) and
lifecycle tracking is active.

Tables are created with `CREATE TABLE IF NOT EXISTS` on first open. There is no migration step and no
existing row anywhere is rewritten.

## Table 1: `notification_candidates`

One row per (user, opportunity, revision): what STRATUS knew when it decided whether to interrupt.

| Column | Type | Notes |
|---|---|---|
| `candidate_id` | TEXT, primary key | Deterministic (UUIDv5 of user, event, revision). Re-evaluation replaces the row |
| `user_id` | TEXT, not null | Server-resolved identity |
| `event_id` | TEXT, not null | Opportunity ID for this process lifetime |
| `entity_id` | TEXT, not null | Stable company identifier |
| `ticker` | TEXT | |
| `signal_family` | TEXT | |
| `thesis_id` | TEXT, not null | Equal to `entity_id` today |
| `thesis_revision` | INTEGER | |
| `is_watched` | INTEGER, not null | |
| `watch_route` | TEXT, not null | |
| `communication_mode` | TEXT, not null | |
| `interruption` | TEXT, not null | |
| `created_at` | TEXT, not null | ISO 8601 UTC |
| `payload` | TEXT, not null | The full candidate as JSON: Watch, prioritisation, revision and evidence snapshots, freshness and degraded state, model version, qualifying trigger codes |

Index: `idx_notification_candidates_user (user_id)`.

## Table 2: `notification_decisions`

The SEND / SUPPRESS verdict and its reason. Append-only; a row is written only when the outcome or
reason changes for the same (user, event, revision), so a retried or repeated poll adds nothing.

| Column | Type | Notes |
|---|---|---|
| `decision_id` | TEXT, primary key | |
| `candidate_id` | TEXT, not null | |
| `user_id` | TEXT, not null | |
| `event_id` | TEXT, not null | |
| `thesis_revision` | INTEGER | |
| `outcome` | TEXT, not null | `SEND` or `SUPPRESS` |
| `reason` | TEXT, not null | One send reason; twelve suppression reasons |
| `decided_at` | TEXT, not null | ISO 8601 UTC |
| `payload` | TEXT, not null | The full decision as JSON, including the shadow evaluation |

Index: `idx_notification_decisions_lookup (user_id, event_id, thesis_revision, decided_at)`.

Reasons. Send: `new_material_revision`. Suppress: `policy_suppressed`, `view_cooldown_active`,
`interruption_budget_exhausted`, `insufficient_personal_relevance_or_urgency`, `no_material_delta`,
`same_revision_suppressed`, `cooldown_suppressed`, `provider_degraded_suppressed`,
`beta_notifications_paused`, `freshness_unestablished_suppressed`, `stale_evidence_suppressed`,
`revision_unattributable_suppressed`.

## Table 3: `notification_dispatches`

What happened to a SEND. One row per dispatch attempt per opportunity.

| Column | Type | Notes |
|---|---|---|
| `dispatch_id` | TEXT, primary key | |
| `user_id` | TEXT, not null | |
| `event_id` | TEXT, not null | |
| `entity_id` | TEXT, not null | |
| `thesis_revision` | INTEGER | |
| `state` | TEXT, not null | `dispatch_attempted`, `dispatch_accepted`, `dispatch_rejected`, `dispatch_failed` |
| `accepted_count` | INTEGER, not null | Tokens the push provider accepted |
| `rejected_count` | INTEGER, not null | Tokens it refused |
| `detail` | TEXT | Provider error codes, at most 500 characters. No token is stored |
| `delivery_state` | TEXT, not null | Always `unknown`. No delivery receipt is read |
| `attempted_at` | TEXT, not null | ISO 8601 UTC |

Index: `idx_notification_dispatches_lookup (user_id, event_id, attempted_at)`.

## Retention

- 120 days, by `created_at`, `decided_at` and `attempted_at` respectively.
- Purged when the store opens at startup, and at most once every 24 hours thereafter from the recording
  path. A restart purges again; the purge is idempotent.
- Override: `STRATUS_NOTIFICATION_LEDGER_RETENTION_DAYS`, minimum 7. Not to be set for Beta 1 without a
  decision.
- Account deletion removes that user's rows from all three tables immediately.

## Size

Candidates: at most one row per user, company and revision. Decisions: one per change of outcome.
Dispatches: one per send attempt. At beta scale (single-digit users, 30 companies, a few revisions per
company per week) this is thousands of rows over 120 days, well under a megabyte per user-month.

## Telemetry (no table change)

Feedback and Ask context use the existing `telemetry_events` table. The addition is one event name,
`opportunity_feedback_submitted`, and new keys inside the existing JSON `context` column. No column, index
or table is added. Telemetry rows are now removed with the account.

## What is recorded about a person

User identifier, which opportunities were evaluated for them, their Watch state at decision time, and
the outcome. No push token, no message content beyond what the feed already shows, no location, no
device identifier. The aggregate developer report never lists a user.

## Execution checklist for Release A

- [ ] 72-hour window closed and recorded.
- [ ] Deployed commit contains the three `CREATE TABLE IF NOT EXISTS` statements above and nothing else
      that creates or alters a table.
- [ ] After deploy: the file is non-empty and has exactly three tables.
- [ ] After the first poll with a lifecycle-tracked opportunity: candidate and decision rows exist.
- [ ] Pause on: a `beta_notifications_paused` decision row appears. Pause off.
- [ ] `/health`, feed, scheduler state and memory checked per the runbook, section 4.
