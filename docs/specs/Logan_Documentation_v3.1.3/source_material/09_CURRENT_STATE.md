# Logan Intelligence System — Current State

**IMPORTANT:** This file must be filled in before implementation begins.
It tells Claude Code what already exists so it does not rebuild what is working
and does not contradict the current architecture.

Update this file at the start of each implementation session.

---

## How to Use This File

1. Fill in every section below with accurate information about the current codebase
2. If a section is "not built yet", write "not built yet" — do not leave it blank
3. Be specific about file names, function names, and data shapes
4. Note anywhere the current implementation conflicts with the v1.3 spec
5. Attach this file to every Claude Code prompt along with the relevant spec files

---

## Tech Stack

```
Language:           [e.g., Python 3.11 / TypeScript / etc.]
Framework:          [e.g., FastAPI / Express / None]
Database:           [e.g., PostgreSQL / SQLite / Redis / None]
Message queue:      [e.g., Redis Streams / Kafka / None]
Frontend:           [e.g., React Native / Flutter / None]
Deployment:         [e.g., local dev only / Docker / etc.]
Package manager:    [e.g., pip + pyproject.toml / npm / etc.]
Test framework:     [e.g., pytest / jest / etc.]
```

---

## Repository Structure

```
[Paste your top-level directory structure here]

Example:
logan/
  backend/
    api/
    pipeline/
    models/
    tests/
  frontend/
    src/
      screens/
      components/
  shared/
    types/
  data/
    simulated/
```

---

## What Is Built and Working

List every component that is implemented and passing tests.
Be specific — "partially built" is not useful. State what exactly works.

```
Component                         Status          File / Module
─────────────────────────────────────────────────────────────────
[e.g.]
Multi-layer signal pipeline        Working         backend/pipeline/core.py
Entity registry (11 entities)      Working         backend/pipeline/entities.py
Normalization layer                Working         backend/pipeline/normalizer.py
Opportunity Field (frontend)       Working         frontend/src/screens/OpportunityField.tsx
Simulated signal generator         Working         data/simulated/generator.py

[Fill in your actual components]
```

---

## What Is Partially Built

List components that exist but are incomplete or have known issues.

```
Component                         What Works          What's Missing
────────────────────────────────────────────────────────────────────
[e.g.]
Convergence Detector               Cross-domain type   Multi-source type
                                                       Temporal type

[Fill in your actual partial builds]
```

---

## What Is Not Built Yet

```
[List all spec components that have not been started]
```

---

## Data Contract Alignment

Check each object against 03_DATA_CONTRACTS.md.
Note any fields that exist in the spec but not in your current implementation,
or fields you have implemented that differ from the spec.

```
Object                  Aligned?    Notes
──────────────────────────────────────────────────────────
RawSignal               [yes/no]    [any differences]
NormalizedSignal        [yes/no]    [any differences]
EnrichedEvent           [yes/no]    [any differences]
EvidenceTrust           [yes/no]    [any differences]
CommunitySignal         [yes/no]    [any differences]
OpportunityEvidence     [yes/no]    [any differences]
DomainAnalysis          [yes/no]    [any differences]
UserModel               [yes/no]    [any differences]
ReasoningResult         [yes/no]    [any differences]
ConclusionConfidence    [yes/no]    [any differences]
AttentionRecommendation [yes/no]    [any differences]
OpportunityLifecycle    [yes/no]    [any differences]
DecayState              [yes/no]    [any differences]
FeedbackSignal          [yes/no]    [any differences]
```

---

## Known Conflicts with v1.3 Spec

List anything in your current implementation that contradicts the architecture spec.
This section is critical — Claude Code needs to know where to reconcile, not just where to build.

```
[Example]
- Current scoring uses a single relevance_score, not Hit Quality / User Value separation
- Memory System currently allows direct writes from Reasoning Engine (violates spec)
- Opportunity Field currently shows 5 items max — spec does not limit this

[Fill in your actual conflicts]
```

---

## Simulated Entities

The current codebase uses simulated entities to develop and test the pipeline
before live data integration.

```
Current entity count:   [e.g., 11]
Domains covered:        [e.g., Stocks, Sports, Crypto]

Entities:
  [List the simulated entities — e.g., NVDA, Lakers vs Celtics, BTC, etc.]
```

---

## API Endpoints (if any)

```
Endpoint                            Method    Status    Notes
────────────────────────────────────────────────────────────────
[e.g.]
/api/opportunities                  GET       Working   Returns ranked list
/api/portfolio                      GET       Not built
/api/opportunities/{id}/why-not     GET       Not built

[Fill in your actual endpoints]
```

---

## Test Coverage

```
Layer                               Test file               Coverage
──────────────────────────────────────────────────────────────────
[Fill in what is tested]
```

---

## Questions for Architecture Review

Use this section to flag anything you are unsure about before proceeding.
Add questions here and answer them before implementing.

```
[Example]
Q: The spec says only Learning System writes to Memory. We currently have Reasoning
   Engine writing to a cache object. Should that cache be restructured?

A: [Answer before implementing]
```

---

## Session Notes

Use this section to track notes between implementation sessions.
Append — do not overwrite.

```
[Date] — [What was accomplished, what is blocked, what to do next]
```
