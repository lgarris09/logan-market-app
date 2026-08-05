# Logan Intelligence — API Specification
**Version:** 3.1.3
*Source: Architecture v1.3 FINAL (2026-07-31). Original: “source_material/24_API_SPECIFICATION.md” (historical label).*
*All tech stack choices are PROVISIONAL. See `15_DECISIONS.md`.*
*v3.1.3 (ADR-029): `priority_score` removed from both response examples below — it is deprecated as a public score and its replacement, `internal_rank_score`, is explicitly internal-only and never returned via any API response. `hit_quality_score`, `user_value_score`, and `momentum_score` remain the response's scoring fields.*

---

## Base URL

```
Development:  http://localhost:8000/v1
Production:   https://api.loganintelligence.com/v1  (TBD)
```

---

## Authentication

All endpoints require a valid JWT access token.

```
Authorization: Bearer <access_token>
```

**Token lifecycle:**
- Access token: 15 minutes
- Refresh token: 30 days (rotate on use)
- Refresh endpoint: `POST /auth/refresh`

**Error on invalid/expired token:**
```json
{
  "error": "unauthorized",
  "message": "Access token expired or invalid",
  "code": 401
}
```

---

## Common Response Shape

All responses follow this envelope:

```json
{
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "ISO-8601",
    "version": "1.0"
  },
  "error": null
}
```

On error:
```json
{
  "data": null,
  "meta": { "request_id": "uuid", "timestamp": "ISO-8601" },
  "error": {
    "code": 422,
    "type": "validation_error",
    "message": "...",
    "details": []
  }
}
```

---

## Endpoints

### GET /v1/opportunities

Returns the ranked opportunity list for the Opportunity Field.

**Query params:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 20 | Max items returned |
| `min_user_value` | float | 0.0 | Filter by minimum user_value_score |
| `domain` | string | all | Filter by domain. Values: `stocks`, `sports`, `prediction_markets`, `crypto`, `social_trends`, `culture`, `personal_finance` |
| `stage` | string | active | `active` = stages 1-6; `all` = all stages |

**Response:**
```json
{
  "data": {
    "opportunities": [
      {
        "id": "opp_abc123",
        "schema_version": "1.0",
        "entity_id": "entity_nvda",
        "entity_name": "NVIDIA",
        "domain": "stocks",
        "headline": "NVIDIA — Earnings beat + prediction market gap detected",
        "lifecycle_stage": "high_conviction",
        "lifecycle_stage_label": "High Conviction",
        "hit_quality_score": 0.84,
        "user_value_score": 0.71,
        "confidence": 0.78,
        "confidence_label": "High",
        "momentum_score": 0.55,
        "is_action_window": false,
        "action_window_opens": null,
        "action_window_closes": null,
        "watching_since": "2026-07-30T14:22:00Z",
        "last_updated": "2026-08-03T09:15:00Z",
        "field_position": {
          "distance_from_center": 0.24,
          "angle_degrees": 42
        }
      }
    ],
    "portfolio_summary": {
      "total_watching": 14,
      "total_detected": 6,
      "total_emerging": 3,
      "total_building": 3,
      "total_high_conviction": 2,
      "total_action_window": 1
    }
  }
}
```

**Notes:**
- `momentum_score` maps to node edge glow in the Opportunity Field. It does NOT affect node brightness, size, or proximity to center. See DECISION-016.
- `action_window_opens` and `action_window_closes` are ISO 8601 timestamps or null when not in Action Window stage.

---

### GET /v1/opportunities/{id}

Returns full detail for a single opportunity (the Opportunity Card data).

**Response:**
```json
{
  "data": {
    "id": "opp_abc123",
    "schema_version": "1.0",
    "entity_id": "entity_nvda",
    "entity_name": "NVIDIA",
    "domain": "stocks",
    "headline": "NVIDIA — Earnings beat + prediction market gap detected",
    "why_it_matters_to_me": "You hold NVDA in your linked Robinhood account. This adds a third signal to your AI cluster.",
    "what_happened": "NVIDIA reported Q3 earnings of $0.81/share, beating estimates by 18%. Revenue guidance raised to $37.5B.",
    "why_now": "Options expiry in 3 days. Prediction market contract 'NVDA above $120' has not repriced yet despite earnings beat.",
    "watching_since": "2026-07-30T14:22:00Z",
    "stage_history": [
      {"stage": "watching", "entered_at": "2026-07-30T14:22:00Z", "trigger": "Initial ODSE signals"},
      {"stage": "detected", "entered_at": "2026-08-01T09:00:00Z", "trigger": "Convergence detector fired — TriggerEvent: STOCK_CONVERGENCE_MULTI_SOURCE"},
      {"stage": "high_conviction", "entered_at": "2026-08-03T07:30:00Z", "trigger": "Earnings beat confirmed — TriggerEvent: STOCK_EARNINGS_BEAT"}
    ],
    "trigger_events": [
      {"code": "STOCK_CONVERGENCE_MULTI_SOURCE", "fired_at": "2026-08-01T09:00:00Z"},
      {"code": "STOCK_EARNINGS_BEAT", "fired_at": "2026-08-03T07:30:00Z"}
    ],
    "confidence": 0.78,
    "confidence_label": "High",
    "confidence_raised_by": ["Strong earnings beat", "Options flow surge", "Cross-domain convergence"],
    "confidence_limited_by": ["Macro uncertainty", "Sector-wide move may dilute signal"],
    "hit_quality_score": 0.84,
    "user_value_score": 0.71,
    "momentum_score": 0.55,
    "supporting_evidence": [
      "Earnings beat of +18% vs. consensus estimates",
      "Revenue guidance raised $2.5B above prior guidance",
      "Options flow shows unusual call buying in 1-week expiry",
      "Prediction market contract 'NVDA above $120' lagging stock move"
    ],
    "contradicting_evidence": [
      "Sector-wide AI optimism may be inflating this specific beat",
      "Macro rate environment adds uncertainty beyond the 2-week window"
    ],
    "sources": ["Alpaca (price data)", "Reddit/WallStreetBets (social signal)", "Kalshi (contract pricing)", "NewsAPI"],
    "lifecycle_stage": "high_conviction",
    "action_window_opens": null,
    "action_window_closes": null,
    "correction_state": "none",
    "correction_note": null,
    "decay_state": {
      "time_decay_rate": 0.04,
      "current_decay": 0.02,
      "days_until_regression": 8
    },
    "decision_trace": [
      {"layer": "trigger_events", "output": "STOCK_CONVERGENCE_MULTI_SOURCE fired; STOCK_EARNINGS_BEAT fired"},
      {"layer": "convergence_detector", "output": "CROSS_DOMAIN: stocks + prediction_market, strength 0.81"},
      {"layer": "domain_analysis", "output": "hit_quality: 0.84, earnings_surprise: +18%, guidance_revision: +12%"},
      {"layer": "reasoning_engine", "output": "Event meaning: positive earnings surprise with upside guidance"},
      {"layer": "opportunity_engine", "output": "Passed all 7 steps. Priority: 0.81"}
    ],
    "connected_items": [
      {"id": "opp_xyz789", "headline": "NVDA above $120 prediction contract — underpriced", "user_value_score": 0.65}
    ],
    "disclaimer": "Logan provides intelligence analysis only. This is not financial, investment, gambling, or legal advice. Always verify information before making any financial decision. Past signal accuracy does not guarantee future results."
  }
}
```

**Field notes:**
- `why_it_matters_to_me` — Always the first rendered field in the Opportunity Card. Always personalized. LOCKED per `22_OPPORTUNITY_CARD_SPEC.md`.
- `supporting_evidence` — Array of strings. May be empty array in early stages.
- `contradicting_evidence` — Array of strings. Never hidden when present. Empty array means none found.
- `sources` — Compact source list. Array of strings.
- `action_window_opens` / `action_window_closes` — ISO 8601 or null. Only populated when `lifecycle_stage = "action_window"`.
- `correction_state` — Values: `"none"` (field not rendered), `"updated"`, `"reversed"`.
- `correction_note` — String or null. Present when `correction_state` is not `"none"`.
- `trigger_events` — Array of TriggerEvent codes that have fired for this opportunity, with timestamps.
- `momentum_score` — Community momentum score (0.0–1.0). Maps to node edge glow only. Not rendered on the card as a score. Present for reference.

---

### POST /v1/feedback

Records a user feedback signal. Every feedback signal is processed by the Learning System.

**Request:**
```json
{
  "opportunity_id": "opp_abc123",
  "interaction_type": "dismiss",
  "reaction_time_ms": 4200,
  "timestamp": "2026-08-03T10:22:00Z"
}
```

**`interaction_type` values:**

| Value | Description | Signal Strength |
|-------|-------------|-----------------|
| `viewed` | User opened the card | Weak positive |
| `dismiss` | User dismissed the opportunity | Moderate negative |
| `not_relevant` | User indicated this type is not relevant to them | Strong negative (calibrates interest weights) |
| `remind` | User asked to be reminded later | Neutral / mild positive |
| `acted` | User marked as acted on | Strong positive (primary learning signal) |
| `expanded_detail` | User expanded full detail | Mild positive |
| `expanded_trace` | User expanded full reasoning chain | Mild positive (advanced user) |

**Response:**
```json
{
  "data": { "recorded": true }
}
```

**Notes:**
- `not_relevant` is a stronger signal than `dismiss`. It tells Logan to reduce weight for this domain/type in the User Model, not just decay this single opportunity.
- `acted` triggers `inferred_intent: "acting"` flag in the FeedbackSignal processed by the Learning System.
- `remind` re-surfaces the opportunity after a configurable delay (user-facing control, defaults to 24 hours).

---

### GET /v1/portfolio

Returns the Opportunity Portfolio — all opportunities across all lifecycle stages.

**Response:**
```json
{
  "data": {
    "stages": {
      "watching": { "count": 8, "items": [ ... ] },
      "detected": { "count": 4, "items": [ ... ] },
      "emerging": { "count": 2, "items": [ ... ] },
      "building_conviction": { "count": 3, "items": [ ... ] },
      "high_conviction": { "count": 2, "items": [ ... ] },
      "action_window": { "count": 1, "items": [ ... ] },
      "outcome": { "count": 5, "items": [ ... ] },
      "learning": { "count": 12, "items": [ ... ] }
    }
  }
}
```

---

### GET /v1/why-not/{entity_id}

Returns the "Why Not" explanation for any entity Logan knows about but is not surfacing.

**Response:**
```json
{
  "data": {
    "entity_id": "entity_amd",
    "entity_name": "AMD",
    "suppression_reason": "below_user_value_threshold",
    "suppression_detail": "Hit Quality is 0.61 (moderate signal), but User Value is 0.22. AMD is not in your watched domains and you have no AMD positions.",
    "what_would_change": "Adding AMD to watched domains or linking an account with AMD positions would increase User Value score."
  }
}
```

---

### WebSocket /v1/stream

Real-time updates for the Opportunity Field.

**Connection:**
```
ws://localhost:8000/v1/stream
Authorization: Bearer <access_token>  (sent as query param: ?token=<jwt>)
```

**Message types:**

```json
{ "type": "field_update", "data": { "opportunities": [ ... ] } }
{ "type": "node_added", "data": { "opportunity": { ... } } }
{ "type": "node_updated", "data": { "opportunity_id": "...", "changes": { ... } } }
{ "type": "node_removed", "data": { "opportunity_id": "...", "reason": "decayed" } }
{ "type": "stage_transition", "data": { "opportunity_id": "...", "from": "emerging", "to": "building_conviction" } }
{ "type": "trigger_event_fired", "data": { "opportunity_id": "...", "trigger_code": "STOCK_EARNINGS_BEAT", "fired_at": "..." } }
{ "type": "ping", "data": { "timestamp": "..." } }
```

**Notes:**
- `trigger_event_fired` is emitted when a new TriggerEvent code fires for an opportunity. The mobile client may use this to animate a stage transition.
- All `node_updated` payloads include `momentum_score` changes so the mobile client can update edge glow independently of other node properties.

---

## Error Codes

| Code | Type | Description |
|------|------|-------------|
| 400 | bad_request | Malformed request |
| 401 | unauthorized | Missing or invalid token |
| 403 | forbidden | Valid token but insufficient permissions |
| 404 | not_found | Entity or opportunity not found |
| 422 | validation_error | Request body failed validation |
| 429 | rate_limited | Too many requests |
| 500 | internal_error | Pipeline or infrastructure error |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| GET /v1/opportunities | 60/min |
| GET /v1/opportunities/{id} | 120/min |
| POST /v1/feedback | 300/min |
| GET /v1/portfolio | 30/min |
| WS /v1/stream | 1 connection per user |

---

*Logan Intelligence API Specification — v3.1.2 | 2026-08-03*
*v3.1.2 changes: `interaction_type` enum expanded: `not_relevant`, `remind`, `acted` added (replacing ambiguous `acted_on`, `dismissed`). Opportunity detail response expanded: `why_it_matters_to_me`, `supporting_evidence`, `contradicting_evidence`, `sources`, `action_window_opens`, `action_window_closes`, `correction_state`, `correction_note`, `trigger_events` fields added. `momentum_score` added to list response (renamed from `trending_score`). Domain filter values updated to include `culture` and `personal_finance`. `trigger_event_fired` WebSocket message type added. All `interaction_type` values documented with signal strength. Version updated to 3.1.2.*


---
## v3.1.2 Operational Requirements

- Feedback writes require an idempotency key and deterministic duplicate response.
- Cursor pagination examples must show next cursor and stable ordering.
- Request ID and decision trace ID are distinct and returned on every response.
- Validation errors include field paths and machine-readable codes.
- WebSocket events carry sequence number, event ID, schema version, and revision number.
- Clients support reconnect, last-seen sequence resume, duplicate suppression, and full resync when retention is exceeded.
- Trigger revision, opportunity correction, and thesis-changed events are first-class event types.
- Publish an OpenAPI source and define deprecation/version support policy.
