# Logan Intelligence — Golden Test Scenarios
**Version:** 3.1.3
*Source: Architecture v1.3 FINAL (2026-07-31). Original: “source_material/26_GOLDEN_TEST_SCENARIOS.md” (historical label).*

*These scenarios are the Phase 6 gate criteria. The full pipeline must pass all 13 before declaring the pipeline complete.*
**TriggerEvent / OpportunityLifecycle status:** every scenario step referencing TriggerEvent emission or lifecycle-stage transitions (including Scenario 11) is SPECIFIED — NOT IMPLEMENTED (V3.1.4 BATCH-3, OD-009). These scenarios are not run against `logan_core/` as of V3.1.4 and are not part of the V3.1.4 release gates.

---

## How to Use This File

Each scenario defines:
- Input conditions (simulated signals)
- Expected pipeline output at each stage
- Pass/fail criteria

All scenarios use simulated data — no real API calls required for gate verification.

Data contracts for all objects: `07_DATA_CONTRACTS.md`.

---

## Scenario 01 — Basic Convergence (Stocks)

**Setup:** NVIDIA receives signals from 3 independent sources (price movement, news article, Reddit mentions) within 30 minutes.

**Expected outputs:**
- Convergence Detector fires: `MULTI_SOURCE`, strength 0.72
- TriggerEvent emitted: `STOCK_CONVERGENCE_MULTI_SOURCE`
- hit_quality_score ≥ 0.55
- Lifecycle: Detected
- Opportunity Engine: surfaces (if user has Stocks in watched domains)

**Pass criteria:**
- [ ] Convergence Detector fires on 3+ sources
- [ ] TriggerEvent `STOCK_CONVERGENCE_MULTI_SOURCE` emitted with correct fields
- [ ] Does not fire on 2 sources from same domain
- [ ] schema_version present on all objects
- [ ] ExecutionMetrics emitted at every layer

---

## Scenario 02 — Cross-Domain Convergence (Stocks + Prediction Markets)

**Setup:** NVIDIA stock shows unusual options volume AND a Kalshi contract "NVDA above $120" shows increased trading volume, simultaneously.

**Expected outputs:**
- Convergence Detector fires: `CROSS_DOMAIN`, strength 0.85 (cross-domain multiplier applied)
- TriggerEvent emitted: `STOCK_OPTIONS_FLOW_SURGE` and/or `PM_ASSET_CONVERGENCE_WITH_STOCK`
- hit_quality_score ≥ 0.70
- Lifecycle: Emerging
- Priority elevated vs. Scenario 01

**Pass criteria:**
- [ ] Cross-domain convergence scores higher than single-domain
- [ ] Both domains reflected in decision_trace
- [ ] domain_count = 2 in EnrichedEvent
- [ ] At least one TriggerEvent code emitted from the registry

---

## Scenario 03 — Divergence (Price vs. Sentiment)

**Setup:** AMD stock price has dropped 8% over 3 days. Social sentiment (Reddit/news) remains positive, showing no corresponding fear.

**Expected outputs:**
- Divergence Detector fires: `PRICE_VS_SENTIMENT`, gap_score ≥ 0.65
- TriggerEvent emitted: `STOCK_DIVERGENCE_PRICE_VS_SENTIMENT`
- hit_quality_score ≥ 0.60
- Decision trace shows divergence gap calculation

**Pass criteria:**
- [ ] Divergence Detector fires
- [ ] TriggerEvent `STOCK_DIVERGENCE_PRICE_VS_SENTIMENT` emitted
- [ ] Does NOT fire when price and sentiment are aligned (negative control)
- [ ] Gap score reflects magnitude of divergence

---

## Scenario 04 — ODSE Weak Signal Accumulation

**Setup:** Over 14 days, a company shows: 3 new ML engineer job postings, 1 patent filing in AI hardware, GitHub repo activity increase of 40%, and search volume anomaly for company name.

**Expected outputs:**
- ODSE fires after reinforcement_count ≥ 3 and weighted_strength ≥ 0.60
- TriggerEvent emitted: `STOCK_ODSE_ACCUMULATION`
- Lifecycle: Watching → Detected
- decision_trace shows 14-day accumulation

**Pass criteria:**
- [ ] ODSE does NOT fire before 3 reinforcing signals
- [ ] ODSE does NOT fire if weighted_strength < 0.60
- [ ] 14-day window enforced correctly (signals older than 14 days excluded)
- [ ] TriggerEvent code present in registry before test runs

---

## Scenario 05 — Hypothesis Engine Disconfirmation

**Setup:** Signals appear to suggest an earnings beat. The Hypothesis Engine generates hypothesis "positive earnings surprise." Then: an announcement reveals the apparent beat was due to a one-time accounting adjustment.

**Expected outputs:**
- Hypothesis Engine generates confirming AND disconfirming evidence search
- Disconfirming evidence found: accounting adjustment flag
- Hypothesis NOT advanced; confidence held at "building"
- decision_trace shows disconfirmation logic
- `contradicting_evidence` array populated in opportunity detail

**Pass criteria:**
- [ ] Hypothesis Engine searches for disconfirming evidence
- [ ] Hypothesis does not advance when strong disconfirming evidence found
- [ ] "I don't know yet" surfaces if net evidence is insufficient
- [ ] Does NOT confirm the hypothesis prematurely
- [ ] `contradicting_evidence` in API response is non-empty and accurate

---

## Scenario 06 — User Personalization

**Setup:** Two users. Same NVIDIA signal. User A holds NVDA. User B has no tech holdings and has dismissed every tech stock opportunity in the past 30 days.

**Expected outputs:**
- hit_quality_score: same for both users
- user_value_score: User A >> User B
- User A: opportunity surfaces at higher priority
- User B: opportunity suppressed (below user_value_threshold) with Why Not explanation
- `why_it_matters_to_me` for User A is personalized to their NVDA position

**Pass criteria:**
- [ ] hit_quality_score is identical for both users
- [ ] user_value_score differs significantly
- [ ] User B receives Why Not explanation
- [ ] Why Not correctly identifies user_value_threshold as reason
- [ ] `why_it_matters_to_me` for User A references their specific NVDA holding (not generic)

---

## Scenario 07 — Time Decay (Stocks)

**Setup:** A stock opportunity enters Detected stage. No new confirming signals arrive for 7 days (stocks time decay rate: 0.05/day).

**Expected outputs:**
- confidence decreases each day without new signals
- At day ~6: stage regresses from Detected to Watching
- decision_trace shows decay calculation

**Pass criteria:**
- [ ] Confidence decreases at configured rate
- [ ] Stage regression triggers at correct confidence threshold
- [ ] Does NOT regress if new confirming signals arrive

---

## Scenario 08 — Action Window Pulse + Retirement

**Setup:** An opportunity reaches Action Window stage (time-sensitive event in 48 hours). `action_window_opens` and `action_window_closes` are populated. No user action after the event passes.

**Expected outputs:**
- Lifecycle stage: Action Window
- `is_action_window: true` in API response
- `action_window_opens` and `action_window_closes` populated with valid ISO 8601 timestamps
- After event: stage transitions to Outcome
- After learning period: stage transitions to Learning
- Eventually: retired

**Pass criteria:**
- [ ] `is_action_window: true` in API response
- [ ] `action_window_opens` and `action_window_closes` are non-null and valid timestamps
- [ ] Stage transitions to Outcome after event timestamp passes
- [ ] Learning System records outcome
- [ ] Opportunity retired after Learning stage completes

---

## Scenario 09 — Crowd Manipulation Detection

**Setup:** A stock suddenly receives 10,000 social mentions in 30 minutes, all from newly-created accounts with similar posting patterns.

**Expected outputs:**
- Community Intelligence: bot_risk > 0.70, coordination_risk > 0.60
- momentum_score severely penalized (quality_multiplier = 0.20)
- Opportunity Engine suppresses (Step 6: dangerous crowd conditions)
- Why Not: "Suspicious coordination pattern detected in engagement signals"

**Pass criteria:**
- [ ] Bot risk and coordination risk flags fire correctly
- [ ] momentum_score penalized (not zero, but heavily reduced)
- [ ] Opportunity does not surface despite high raw volume
- [ ] Why Not message references coordination risk
- [ ] Node edge glow remains low (momentum_score low); node brightness unaffected by the raw volume

---

## Scenario 10 — Read & Suggest Cross-Domain Conflict

**Setup:** User has linked a brokerage account. They hold NVDA long (stock). They also have an open "NVDA below $100" prediction contract (bearish).

**Expected outputs:**
- Cross-domain conflict detected in Read & Suggest layer
- User presented with: "Your NVDA long position conflicts with your bearish prediction contract"
- Both positions visible in Read & Suggest overview

**Pass criteria:**
- [ ] Conflict detected correctly
- [ ] Both positions reflected in conflict explanation
- [ ] Logan does not recommend closing either position (advisory only — LOCKED)
- [ ] Conflict does not affect the Opportunity Field intelligence

---

## Scenario 11 — TriggerEvent Pipeline (Earnings Beat)

**Setup:** NVIDIA reports an earnings beat. The Stocks Domain Receptor detects the earnings data. The TriggerEvent framework evaluates whether `STOCK_EARNINGS_BEAT` conditions are met.

**Expected outputs:**
- Domain Receptor emits raw event
- TriggerEvent evaluation: `STOCK_EARNINGS_BEAT` conditions met (actual EPS > consensus by ≥ X%)
- TriggerEvent `STOCK_EARNINGS_BEAT` emitted with correct fields: `trigger_code`, `entity_id`, `fired_at`, `source_event_id`, `context`, `schema_version`
- TriggerEvent attaches to WorldModel entity's `trigger_events` array
- Opportunity Engine receives TriggerEvent and uses it in scoring
- `trigger_events` array in opportunity detail response includes `STOCK_EARNINGS_BEAT`

**Pass criteria:**
- [ ] `STOCK_EARNINGS_BEAT` code exists in `TRIGGER_REGISTRY_STOCKS.md` before test runs
- [ ] TriggerEvent object has all required fields per `07_DATA_CONTRACTS.md`
- [ ] TriggerEvent does NOT fire if earnings beat threshold not met
- [ ] TriggerEvent fires exactly once per qualifying event (no duplicate emissions)
- [ ] `trigger_events` array populated correctly in API response
- [ ] `decision_trace` shows TriggerEvent as an input to Opportunity Engine

---

## Scenario 12 — Correction State

**Setup:** An opportunity surfaces with thesis "NVIDIA earnings beat signals upside." Three days later, new data emerges: the beat was driven entirely by a one-time tax benefit, not core operating performance. Logan's Hypothesis Engine updates its assessment.

**Expected outputs:**
- Opportunity `correction_state` transitions from `"none"` → `"updated"`
- `correction_note` populated: explains what changed and why
- Opportunity Card renders the Correction State section
- FeedbackSignal history shows prior engagement with original thesis

**Pass criteria:**
- [ ] `correction_state` updates to `"updated"` correctly
- [ ] `correction_note` is non-null and explains the change
- [ ] Prior thesis is NOT silently deleted (correction is additive, not overwriting)
- [ ] Correction state `"reversed"` fires correctly when thesis fully inverts

---

## Scenario 13 — Full End-to-End (11+ Entities, 8 Domains)

**Setup:** Simulate a realistic environment with 11+ entities across all 8 domains, each with varied signal states:
- 2 entities: Action Window (high conviction, time-sensitive, both with action_window_opens/closes populated)
- 3 entities: Building Conviction
- 4 entities: Detected or Emerging
- 2 entities: Watching (low signal)
- 3 entities: Suppressed (below user threshold)
- Domain distribution: at least 1 entity in each of the 8 domains

**Expected outputs:**
- Opportunity Field: 9 nodes (suppressed entities not shown)
- Field positions: Action Window items near center, Watching items at edge
- All card fields populated for Action Window items (including `why_it_matters_to_me`, `supporting_evidence`, `contradicting_evidence`, `sources`, `action_window_opens/closes`)
- Why Not explanations available for all 3 suppressed entities
- Portfolio summary: correct counts per stage
- Feedback recorded for one engagement
- Learning System processes feedback and updates User Model
- At least one TriggerEvent emitted during the simulation

**Pass criteria:**
- [ ] Correct count of surfaced vs. suppressed entities
- [ ] Action Window items nearest to center in field_position data
- [ ] All card fields populated for Action Window items (no nulls on required fields)
- [ ] `why_it_matters_to_me` is personalized for each user (not generic)
- [ ] `contradicting_evidence` shown when present; omitted when absent (not shown as empty)
- [ ] Why Not available for every suppressed entity
- [ ] Portfolio summary counts match actual entity states
- [ ] Feedback signal updates User Model via Learning System only
- [ ] Full pipeline end-to-end latency < 2s for field update
- [ ] At least one TriggerEvent code in `trigger_events` for the highest-conviction item
- [ ] All 8 domains represented in the entity set

---

*Logan Intelligence Golden Test Scenarios — v3.1.2 | 2026-08-03*
*v3.1.2 changes: Total scenarios updated from 11 to 13. Scenario 11 added: TriggerEvent Pipeline (Earnings Beat) — verifies STOCK_EARNINGS_BEAT fires correctly and attaches to WorldModel and opportunity. Scenario 12 added: Correction State — verifies correction_state and correction_note lifecycle. Scenario 13 updated (previously 11): full end-to-end now covers 7 domains (was 5), includes action_window_opens/closes, all new card fields, TriggerEvent presence, and personalized why_it_matters_to_me. Scenario 09 updated: `trending_score` renamed to `momentum_score`. Data contracts reference updated from `source_material/03_DATA_CONTRACTS.md` to `07_DATA_CONTRACTS.md`. TriggerEvent emitted noted in Scenarios 01, 02, 03, 04. `contradicting_evidence` check added to Scenario 05. `why_it_matters_to_me` personalization check added to Scenario 06.*
*v3.1.3 changes (ADR-037): Scenario 13 domain count corrected from 7 to 8 — News restored, matching ADR-020 and the running code's Domain literal.*


---
## v3.1.2 Machine-Readable Fixture Contract

Each scenario requires `scenario_N_input.json` and `scenario_N_expected.json`, expected TriggerEvent revision/domain impacts/state, score ranges, lifecycle, recommendation effect, notification and policy decisions, required trace entries, assertions, and pass/fail criteria. Required coverage includes syndication deduplication; rumor confirmed/disproved; conflict; high engagement/weak evidence; staleness; expiration; overexposure override; sports+prediction injury; stock+crypto regulation; culture+public-company trend; weather cross-domain; misleading seasonality; provider disagreement; corrected event revision; jurisdiction gate; insufficient-sample behavioral warning; prediction-market resolution risk; manipulation; and cold start.
