# Logan Intelligence — Notification Policy
**Version:** 3.1.3
*New in v3.1.2. No prior version.*

---

## Core Principle

Logan notifies when something genuinely deserves attention. It does not notify to stay top-of-mind, to fill silence, or because an opportunity has been waiting without a notification.

An empty notification is a broken notification. Every notification must be actionable or genuinely informative.

This flows directly from Logan's Principles: *"The user's attention is a finite resource. Treat it accordingly."* (Principle 9, `20_LOGAN_PRINCIPLES.md`)

---

## Notification Types

| Type | Trigger | Default State | User-Controllable |
|------|---------|---------------|-------------------|
| `ACTION_WINDOW_OPEN` | Opportunity enters Action Window stage | ON | Yes — per-domain |
| `STAGE_TRANSITION_HIGH_CONVICTION` | Opportunity advances to High Conviction | ON | Yes |
| `CORRECTION_STATE_CHANGED` | Logan's thesis has changed on a surfaced opportunity | ON | No — always notify |
| `REMIND_ME_DUE` | User requested a reminder; time has arrived | ON | Yes — set by user |
| `NEW_OPPORTUNITY_SURFACED` | New opportunity crosses user_value_score threshold | OFF | Yes — opt-in |
| `WEEKLY_BRIEF` | Weekly summary of active and closed opportunities | OFF | Yes — opt-in |

---

## Notification Fire Rules

### ACTION_WINDOW_OPEN

**Fires when:** An opportunity advances to Action Window stage.

**Conditions to fire:**
- `lifecycle_stage` transitions to `action_window`
- `user_value_score >= 0.50`
- User has not already dismissed this opportunity

**Notification content:**
```
"[Entity] — Action window open"
"[Headline, max 80 chars]"
"Window closes: [human-readable time, e.g., 'Jan 15, 4pm ET']"
```

**Rate limit:** Maximum 3 `ACTION_WINDOW_OPEN` notifications per 24-hour period across all opportunities. If more than 3 would fire in 24 hours, queue by `internal_rank_score` descending (renamed from `priority_score` in v3.1.3, ADR-029 — this is exactly the internal-only operational tie-breaking use the field exists for; still never exposed via any API).

---

### STAGE_TRANSITION_HIGH_CONVICTION

**Fires when:** An opportunity advances to High Conviction stage.

**Conditions to fire:**
- `lifecycle_stage` transitions to `high_conviction`
- `user_value_score >= 0.60`
- `confidence >= 0.70`
- User has not dismissed this opportunity

**Rate limit:** Maximum 2 `STAGE_TRANSITION_HIGH_CONVICTION` notifications per 24-hour period.

---

### CORRECTION_STATE_CHANGED

**Fires when:** Logan's thesis on a surfaced opportunity changes.

**Conditions to fire:**
- `correction_state` changes from `none` to `updated` or `reversed`
- Opportunity was previously viewed by the user (they have seen the original thesis)

**No rate limit.** Corrections are always delivered because the user may have acted on the original thesis.

**Notification content:**
```
"Logan's view on [Entity] has changed"
"[correction_note summary, max 120 chars]"
```

---

### REMIND_ME_DUE

**Fires when:** A user previously selected "Remind Me" on an opportunity and the scheduled time has arrived.

**Conditions to fire:**
- User explicitly requested the reminder
- Opportunity is still active (not decayed, not dismissed)

**No rate limit.** User explicitly requested this.

---

### NEW_OPPORTUNITY_SURFACED (opt-in)

**Fires when:** A new opportunity crosses the user's relevance threshold.

**Conditions to fire:**
- `user_value_score >= user_notification_threshold` (default 0.75; user-configurable)
- Opportunity has not been notified before
- Cooldown since last `NEW_OPPORTUNITY_SURFACED` notification has elapsed (default: 4 hours)

**Rate limit:** Maximum 1 per 4 hours (configurable). If multiple qualify, send the highest `internal_rank_score` (renamed from `priority_score` in v3.1.3, ADR-029) and queue the rest.

---

## Quiet Hours

**Default quiet hours:** 10:00 PM – 8:00 AM local time. No notifications sent during quiet hours.

**Exception:** `CORRECTION_STATE_CHANGED` when `correction_state = "reversed"` — a full reversal is important enough to break quiet hours, but only for Action Window opportunities.

**User control:** Quiet hours are user-configurable. Users may disable quiet hours entirely.

---

## Delivery Channel

V1 notification delivery: Push notification via mobile app (iOS/Android).

The notification payload includes:
- `opportunity_id` — for deep-linking to the opportunity card
- `notification_type` — for analytics and UX routing
- `headline` — notification body text

Future channels (V2): Email digest, watch complication.

---

## Do Not Notify Rules

Logan NEVER sends a notification for:

1. **An opportunity in Watching stage** — too early; not yet meaningful
2. **An opportunity the user dismissed** — respect the dismiss signal
3. **An opportunity the user marked Not Relevant** — respect the not_relevant signal even more strongly
4. **The same opportunity within 12 hours** of a prior notification on that opportunity (except CORRECTION_STATE_CHANGED)
5. **Trending momentum alone** — community engagement is never a sufficient reason to notify. An opportunity must meet user_value_score threshold independently. See DECISION-016.
6. **"Nothing has changed" updates** — Logan does not send notifications to stay top-of-mind

---

## Notification vs. Opportunity Field

Notifications are a secondary surface. The Opportunity Field is the primary surface.

A user who opens the app will see every active opportunity in the field — they do not need a notification for each one. Notifications exist for time-sensitive events (Action Window) and changes to prior information (Correction State).

If in doubt, do not send a notification. The user will see the Opportunity Field.

---

*Logan Intelligence Notification Policy — v3.1.2 | 2026-08-03*
*New in v3.1.2.*
