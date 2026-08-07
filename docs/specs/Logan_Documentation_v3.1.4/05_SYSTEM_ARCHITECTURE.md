# Logan Intelligence — System Architecture
**Version:** 3.1.3

> **⚠ PROVISIONAL TECH STACK** — Technology choices here are working assumptions for V1 MVP development. They have NOT been locked through formal decision review. All stack choices (FastAPI, PostgreSQL, Redis, S3, Zustand, React Query, Skia, Docker, JWT, Plaid, cloud provider) are subject to change before implementation begins. See `15_DECISIONS.md` for locked vs. provisional decisions.

**TriggerEvent status:** references below to the pipeline running "on TriggerEvent arrival" and to TriggerEvent-based analytics/learning are SPECIFIED — NOT IMPLEMENTED (V3.1.4 BATCH-3, OD-009). The orchestrator in `logan_core/orchestrator/` runs synchronously per call as of V3.1.4; there is no event-driven trigger arrival model.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  MOBILE APP                         │
│         React Native + Expo (iOS / Android)         │
│  Opportunity Field · Portfolio · Read & Suggest     │
│  Skia rendering · Reanimated · Gesture Handler      │
└──────────────────────┬──────────────────────────────┘
                       │  HTTPS / WebSocket
                       ▼
┌─────────────────────────────────────────────────────┐
│                    API LAYER                        │
│              FastAPI (Python 3.11+)                 │
│  REST endpoints · WebSocket feed · Auth · Rate limit│
│  JWT authentication · Per-user session management  │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│                  BRAIN SERVICE                      │
│         Logan Intelligence Pipeline                 │
│  Orchestrator · All 18 layers · Async processing   │
│  Pipeline runs on TriggerEvent arrival + scheduled  │
└────────┬──────────────┬──────────────┬──────────────┘
         │              │              │
         ▼              ▼              ▼
┌──────────────┐ ┌─────────────┐ ┌──────────────────┐
│   MEMORY     │ │INTEGRATIONS │ │    ANALYTICS     │
│   SERVICE    │ │   SERVICE   │ │    SERVICE       │
│              │ │             │ │                  │
│ PostgreSQL   │ │ Plaid (bank)│ │ Outcome tracking │
│ Redis cache  │ │ Alpaca/IEX  │ │ Accuracy metrics │
│ Logan Memory │ │ (stocks)    │ │ Pipeline perf    │
│ Op. History  │ │ Sportradar  │ │ User analytics   │
│ User Models  │ │ (sports)    │ │                  │
│ Hypotheses   │ │ Kalshi API  │ │                  │
└──────────────┘ │ Polymarket  │ └──────────────────┘
                 │ News APIs   │
                 │ Social APIs │
                 │ Music APIs  │
                 └─────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│                  STORAGE LAYER                      │
│  PostgreSQL (primary) · Redis (cache/session)       │
│  S3-compatible (logs, exports, large objects)       │
└─────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│                 LEARNING SERVICE                    │
│        Async · Scheduled · Sole writer to Memory   │
│  Processes feedback · Computes outcomes            │
│  Updates User Models · Updates confidence scores  │
│  Updates source reliability · Updates hypotheses  │
└─────────────────────────────────────────────────────┘
```

---

## Mobile App

**Framework:** React Native with Expo `[PROVISIONAL]`
**Rendering:** Skia `[PROVISIONAL]` (via React Native Skia) for Opportunity Field animations
**Animation:** Reanimated 3 `[PROVISIONAL]` for smooth transitions and gesture response
**Navigation:** Expo Router `[PROVISIONAL]` (file-based routing)
**State:** Zustand `[PROVISIONAL]` for local state, React Query for server state

### Key screens
- Opportunity Field (home) — Skia canvas, radial layout, animated nodes
- Opportunity Detail — gesture-driven card expansion
- Opportunity Portfolio — list + stage breakdown
- Read & Suggest — account intelligence tabs
- Settings — account linking, preferences, data controls

### Communication with API
- REST for static/paginated data (portfolio, settings, history)
- WebSocket for live Opportunity Field updates (node additions, confidence changes, lifecycle transitions)

### Accessibility requirements
- Reduced-motion mode: disable continuous drift and ripple animations; retain static positions and brightness
- Every node must have a text label and VoiceOver/TalkBack description
- Color-independent status: node shape or ring pattern distinguishes domain when color is unavailable

---

## API Layer

**Framework:** FastAPI (Python 3.11+) `[PROVISIONAL]`
**Authentication:** JWT with refresh tokens `[PROVISIONAL]`
**Rate limiting:** Per-user, per-endpoint
**Deployment:** Containerized (Docker) `[PROVISIONAL]`, orchestrated (Kubernetes or Railway for MVP)

### Core endpoints (summary — see `24_API_SPECIFICATION.md` for full spec)

```
GET  /v1/opportunities          Ranked opportunity list for Opportunity Field
GET  /v1/opportunities/{id}     Full detail for a single opportunity
GET  /v1/portfolio              Opportunity Portfolio (all lifecycle stages)
GET  /v1/why-not/{entity_id}    Why Not explanation for any entity
POST /v1/feedback               User feedback signal (view, dismiss, act, etc.)
GET  /v1/read-suggest/overview  Portfolio intelligence overview
GET  /v1/read-suggest/bets      Betting intelligence
GET  /v1/read-suggest/cross     Cross-domain analysis
POST /v1/accounts/link          Initiate account linking (OAuth)
GET  /v1/accounts               Linked accounts list
WS   /v1/stream                 Real-time Opportunity Field updates
```

---

## Brain Service

**Language:** Python 3.11+ `[PROVISIONAL]`
**Execution model:** Async pipeline with concurrent parallel layers
**Trigger:** TriggerEvent arrival (event-driven) + scheduled cycles (every N minutes)
**Observability:** ExecutionMetrics emitted per layer per run, logged to Analytics

### Pipeline execution order

**18-layer synchronous pipeline (authoritative count):**
```
1.  Domain Receptors         (parallel, continuous polling)
2.  Normalization
3.  World Model
4-6. Parallel: Evidence Trust, Community Intelligence, Hit Detection
7.  Domain Analysis
8.  Memory read (User Model + Active Context)
9.  Reasoning Engine
10. Hypothesis Engine
11. Mental Model Engine
12. Conclusion Confidence
13. Opportunity Engine (+ Why Not generation)
14. Opportunity Lifecycle + Decay
15. Policy + Safety
16. Prioritization + Attention State
17. Presentation + Delivery
18. WebSocket push to connected clients
```

**Supporting infrastructure (async, NOT inline pipeline layers):**
```
Memory System    — persistent storage; read by all pipeline layers
Feedback Layer   — async; captures user behavior signals after delivery
Learning System  — async; sole writer to Memory; runs after feedback accumulates
```

> **Layer count note:** The pipeline has exactly **18 synchronous layers**. Memory System, Feedback Layer, and Learning System are infrastructure supporting the pipeline asynchronously — they are not numbered pipeline layers. Any prior reference to '20 steps' was counting infrastructure as layers; 18 is correct.

### Layer isolation rules
- Every layer is stateless (except Memory)
- No layer calls another layer directly — all communication through Orchestrator
- Every layer emits ExecutionMetrics
- Every layer appends to decision_trace

---

## Memory Service

**Primary store:** PostgreSQL `[PROVISIONAL]`
- User Models
- Memory Records (all branches)
- Operational History
- Outcome Records
- Hypothesis Records

**Cache:** Redis `[PROVISIONAL]`
- User Model hot cache (< 10ms reads)
- Active session context
- Pipeline run state
- WebSocket connection registry

**Write rules:** All writes route through Learning System authorization check. Direct writes from any other service fail.

---

## Integrations Service

**Purpose:** Manages all external data connections. Isolated from the Brain Service to prevent API failures from affecting the intelligence pipeline.

### V1 integrations

| Domain | Provider | Data |
|---|---|---|
| Stocks | Alpaca / IEX Cloud / Polygon | Prices, news, fundamentals |
| Sports Betting | Sportradar / The Odds API | Odds, lines, injuries, scores |
| Prediction Markets | Kalshi API, Polymarket API | Contracts, prices, volume |
| News | NewsAPI / RSS aggregation | Headlines, articles |
| Social | Reddit API, limited X/Twitter | Trend signals, sentiment |
| Music / Culture | Spotify API, Apple Music charts, YouTube trends | Charts, trending artists, viral signals |
| Linked accounts | Plaid (brokerage/bank), direct OAuth (DraftKings, Kalshi) | Positions, history |

### Resilience rules
- Each integration runs independently with its own retry and backoff
- Integration failure emits degraded signal, not pipeline halt
- Missing data is explicit ("data unavailable") not silent

---

## Analytics Service

**Purpose:** Tracks Logan's performance over time — not user analytics, but intelligence quality metrics.

Tracks:
- Pipeline execution time per layer
- Detector hit rates by domain
- TriggerEvent accuracy by trigger code and domain
- Opportunity accuracy (predicted direction vs. actual)
- User engagement by opportunity type
- Confidence calibration (are 80% confidence calls right 80% of the time?)

**Storage:** Time-series (PostgreSQL with partitioning, or InfluxDB if scale requires)

---

## Learning Service

**Execution:** Async, scheduled (runs after feedback signals accumulate or on outcome resolution)
**Sole writer to Memory (LOCKED):** Enforced at service boundary
**Operations:**
- Process FeedbackSignals
- Compute OutcomeRecords when events resolve
- Update User Model (reaction speed, explanation preference, interest weights)
- Update source reliability scores
- Update detector hit rates
- Update TriggerEvent outcome performance records
- Update pattern confidence scores
- Write HypothesisUpdates to Hypothesis Memory branch

---

## Storage Summary

| Store | Technology | Data |
|---|---|---|
| Primary DB | PostgreSQL `[PROV]` | All persistent data |
| Cache | Redis `[PROV]` | Hot-path reads, sessions |
| Object storage | S3-compatible `[PROV]` | Logs, exports, large objects |

---

## Deployment (V1 MVP)

- **Containerized:** Docker Compose for local dev, single-server deploy for MVP
- **Upgrade path:** Each service scales independently when needed
- **Cloud:** [TBD — AWS, GCP, or Railway depending on team preference]
- **CI/CD:** GitHub Actions → automated tests → deploy

---

## Security

- JWT authentication, short-lived access tokens, rotating refresh tokens
- All linked account credentials stored via OAuth (Logan never holds raw account credentials)
- Plaid handles brokerage credential security
- TLS everywhere
- User data isolated per user_id — no cross-user data leakage
- See `27_SECURITY_PRIVACY_COMPLIANCE.md` for full security and privacy spec

---

*Logan Intelligence System Architecture — v3.1.2 | 2026-08-03*
*v3.1.2 changes: Pipeline trigger updated from "signal arrival" to "TriggerEvent arrival". Music/Culture integration added. TriggerEvent accuracy tracking added to Analytics Service. TriggerEvent outcome performance added to Learning Service. Accessibility requirements added to Mobile App. File reference updated to 24_API_SPECIFICATION.*
