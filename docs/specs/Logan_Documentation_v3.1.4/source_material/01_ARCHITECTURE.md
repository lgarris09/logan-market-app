# Logan Intelligence System — Architecture v1.3 FINAL

---

## System Identity

```
LOGAN INTELLIGENCE SYSTEM — v1.3
"The Logan Brain"

A reasoning operating system that continuously builds, tests,
updates, and communicates a model of the world on behalf of the user.
```

---

## Full Pipeline

```
EXTERNAL WORLD
Markets · Sports · Prediction Markets · Social · News · Crypto
Portfolios · Calendars · Connected Apps · User Activity
Filings · Patents · Hiring Data · App Rankings · Search Trends
                                │
                                ▼
LAYER 1 — DOMAIN RECEPTORS
"Receptors notice."
Stocks · Sports Betting · Poly Markets · Social Trends · Crypto · Future Domains
Stateless. Attach source metadata. Emit RawSignal.
                                │
                                ▼
LAYER 2 — NORMALIZATION
"Normalization standardizes."
Every RawSignal → NormalizedSignal with common schema.
All downstream layers operate on NormalizedSignal only.
                                │
                                ▼
LAYER 3 — WORLD MODEL
"The World Model connects."
Deduplicate · Extract entities · Detect change
Merge signals · Connect downstream effects
Emit EnrichedEvent
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
LAYER 4 — PARALLEL PROCESSING (all three run simultaneously)

┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────────┐
│ EVIDENCE TRUST   │  │   COMMUNITY      │  │   HIT DETECTION SYSTEM       │
│                  │  │   INTELLIGENCE   │  │                              │
│ Evaluates source │  │ Measures         │  │ Four detectors — all produce │
│ credibility      │  │ aggregate        │  │ OpportunityEvidence          │
│ before reasoning │  │ community        │  │                              │
│                  │  │ attention        │  │ · Convergence Detector       │
│ · source cred    │  │                  │  │ · Divergence Detector        │
│ · corroboration  │  │ · volume/velocity│  │ · Pattern Engine             │
│ · recency decay  │  │ · unique users   │  │ · ODSE (weak signals)        │
│ · contradiction  │  │ · lifecycle state│  │                              │
│ · manipulation   │  │ · bot/coord risk │  │ All output:                  │
│ · completeness   │  │                  │  │ OpportunityEvidence {        │
│                  │  │ Never equals     │  │   source_detector            │
│ → EvidenceTrust  │  │ personal         │  │   entity_id                  │
│                  │  │ relevance        │  │   evidence_type              │
│                  │  │                  │  │   strength                   │
│                  │  │ → CommunitySignal│  │   supporting_signals[]       │
│                  │  │                  │  │   narrative                  │
└────────┬─────────┘  └────────┬─────────┘  │   confidence                 │
         │                     │            │   detected_at                │
         │                     │            │ }                            │
         │                     │            └──────────────┬───────────────┘
         └─────────────────────┴───────────────────────────┘
                                          │
                                          ▼
LAYER 5 — DOMAIN ANALYSIS FRAMEWORK
"Same dimensions. Domain-specific implementation."
Five dimensions scored per entity per domain.
hit_quality_score = objective strength — same for every user.
→ DomainAnalysis

HIT QUALITY vs USER VALUE split happens here.
Hit Quality = objective. User Value = personalized.
                                │
                                ▼
LOGAN INTELLIGENCE CORE

┌─────────────────────────────────────────────────────────┐
│ MEMORY SYSTEM                                           │
│ Operational History (all data) + Logan Memory (retained)│
│ Only Learning System may write.                         │
└───────────────────┬─────────────────────────────────────┘
                    │
        ┌───────────┴────────────┐
        ▼                        ▼
 USER MODEL (durable)     ACTIVE CONTEXT (temporary, session-scoped)
 interests · goals        current question · time of day
 holdings · risk          recent activity · live context
 expertise · behavior     expires at session end
 reaction speed           never overwrites User Model
 explanation prefs
 evidence threshold
        │
        ▼
REASONING ENGINE
"Reasoning determines meaning."
What does this event mean — in isolation, and for this user?
→ ReasoningResult
        │
        ▼
HYPOTHESIS ENGINE  [NEW in v1.3]
"Logan applies a scientific method, not just a pipeline."
Generates hypotheses from evidence patterns.
Actively tests each hypothesis.
Knows what would confirm or disprove each belief.
Updates Mental Model with confirmed hypotheses.
→ HypothesisUpdate
        │
        ▼
MENTAL MODEL ENGINE  [V1 active, V2 full signal]
Stores confirmed world understanding.
V1: tracks and stores.
V2: confidence shifts become signals in their own right.
→ MentalModel
        │
        ▼
CONCLUSION CONFIDENCE
How strongly does evidence support this conclusion?
Includes explicit uncertainty — Logan says "I don't know yet."
Produces full confidence explanation:
  raised by · limited by · would strengthen if · would weaken if
→ ConclusionConfidence
        │
        │  ← Community Intelligence arrives as parallel input
        │  ← Hit Quality from Domain Analysis arrives
        │  ← Hypothesis context arrives
        ▼
OPPORTUNITY ENGINE
"The Opportunity Engine recommends attention."
Staged 7-step decision.
Separates Hit Quality from User Value.
Produces Why Not explanation for every suppressed entity.
→ AttentionRecommendation (with dual scores preserved)
        │
        ▼
OPPORTUNITY LIFECYCLE
Watching → Detected → Emerging → Building Conviction
→ High Conviction → Action Window → Outcome → Learning
stage_velocity tracked per item.
        │
        ▼
OPPORTUNITY DECAY ENGINE
Every opportunity loses strength unless evidence refreshes it.
Time-based · Reaction · Contradiction · Crowd decay.
Moves stages backward. Triggers suppression or retirement.
        │
        ▼
OPPORTUNITY PORTFOLIO  [NEW in v1.3]
Living view of all items across all lifecycle stages.
Users see what Logan is tracking, not just what Logan surfaces.
                                │
                                ▼
LAYER 6 — POLICY AND SAFETY
Opportunity Engine decides whether something matters.
Policy decides how Logan may communicate it.
Analysis vs advice language · gambling controls
Jurisdiction · manipulation prevention · risk limits
                                │
                                ▼
LAYER 7 — PRIORITIZATION AND ATTENTION STATE
Rank · Diversify · Deduplicate
Cooldowns · Fatigue detection
Visibility separate from Interruption
                                │
                                ▼
LAYER 8 — PRESENTATION AND DELIVERY
Eight explanation fields per item.
"I don't know yet" surfaced when evidence is insufficient.
Hit Quality and User Value both displayed.
Why Not available for any entity on request.
                                │
                                ▼
USER EXPERIENCE — THE OPPORTUNITY FIELD
Central "L" intelligence core
Opportunity nodes — scored, explained, lifecycle-tracked
Radial layout — proximity = importance × user value
Node brightness and pulse — lifecycle state
Opportunity Portfolio accessible from field
Why Not query available for any entity
                                │
                                ▼
LAYER 9 — FEEDBACK AND PERSONAL LEARNING LOOP
Feedback Layer — interprets behavior, not literal translation
Personal Learning Loop — learns communication style
  reaction speed · explanation preferences
  evidence threshold · macro vs micro preference
Learning System — only writer to Memory and User Model
                                │
                                ▼
MEMORY · USER MODEL · TRUST · HYPOTHESIS · DECAY UPDATES
Loop closes. System improves.
```

---

## Final Responsibility Chain

```
Receptors notice.
Normalization standardizes.
The World Model connects.
Evidence Trust evaluates the inputs.                     ┐
Community Intelligence measures momentum.                │
Hit Detection finds structured opportunities.            ├─ parallel
ODSE discovers weak signals before headlines.            ┘
All detectors produce OpportunityEvidence.
Domain Analysis scores five dimensions per entity.
Memory preserves retained knowledge.
The User Model interprets the person over time.
Active Context describes the present moment.
Reasoning determines meaning.
The Hypothesis Engine generates and tests beliefs.
The Mental Model stores confirmed world understanding.
Conclusion Confidence evaluates the reasoning.
Explicit uncertainty surfaces when Logan does not know yet.
The Opportunity Engine separates Hit Quality from User Value.
Why Not explanation available for every suppressed entity.
Opportunity Lifecycle tracks development over time.
Opportunity Portfolio shows the full tracking state.
Opportunity Decay keeps the field current.
Policy controls communication.
Prioritization manages competition and repetition.
Delivery decides where and when it appears.
Feedback reveals response.
Personal Learning Loop tailors communication style.
Learning determines what changes.
```

---

## Architecture Status

| Component | Status |
|-----------|--------|
| Domain Analysis Framework | locked |
| Opportunity Discovery Engine (ODSE) | locked |
| Opportunity Lifecycle | locked |
| Opportunity Decay Engine | locked |
| Hit Quality vs User Value separation | locked |
| OpportunityEvidence abstraction | locked |
| Confidence Explanation | locked |
| Explicit Uncertainty | locked |
| Hypothesis Engine | locked |
| Personal Learning Loop | locked |
| Why Not Explanation | locked |
| Opportunity Portfolio | locked |
| Counterfactual Engine | Phase 3 — extension point reserved |

---

## What Logan Is Not

- Not a news aggregator
- Not a stock screener
- Not a trading platform
- Not a recommendations engine
- Not a chatbot
- Not a dashboard
- Not a finance app with extra features

**An intelligence platform that reasons, remembers, and learns.**
