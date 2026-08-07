# Logan Intelligence System — Master Brief
**Version:** 1.3 FINAL
**Status:** Architecture frozen. Ready for implementation.

---

## What Logan Is

Logan is a personalized intelligence layer that continuously discovers, prioritizes, and explains opportunities relevant to each user.

Not a news app. Not a stock screener. Not a trading platform. Not a chatbot. Not a dashboard.

**A reasoning operating system that continuously builds, tests, updates, and communicates a model of the world on behalf of the user.**

Most AI products answer questions.
Most finance products display information.
Logan does neither. It reasons.

---

## What You Are Building

You are implementing the Logan Intelligence System backend. The architecture is fully specified in this package. Your job is to implement it faithfully — not to redesign it.

The frontend is a visual interface called the **Opportunity Field** — a spatial, radial display of what matters to the user and why. The backend feeds it through a ranked opportunity endpoint.

---

## How to Read This Package

| File | Read When |
|------|-----------|
| `00_MASTER_BRIEF.md` | First — always |
| `08_BUILD_ORDER.md` | Second — before writing any code |
| `09_CURRENT_STATE.md` | Third — understand what already exists |
| `01_ARCHITECTURE.md` | Full system picture |
| `02_LAYER_INTERFACES.md` | Before implementing any layer |
| `03_DATA_CONTRACTS.md` | Before defining any object or schema |
| `04_HIT_DETECTION.md` | Before implementing detectors |
| `05_DOMAIN_FRAMEWORK.md` | Before implementing scoring |
| `06_OPPORTUNITY_LIFECYCLE.md` | Before implementing lifecycle tracking |
| `07_OPPORTUNITY_DECAY.md` | Before implementing decay logic |

**Implement one phase at a time per the build order. Ask before moving to the next phase.**

---

## The Core Concept

Logan works across five domains — Stocks, Sports Betting, Prediction Markets, Crypto, Social Trends — with a framework that supports any future domain.

For each domain, Logan:

1. **Notices** — receptors observe raw signals from the external world
2. **Understands** — normalization and the World Model connect entities and events
3. **Detects** — four detectors find structured opportunity patterns
4. **Scores** — Domain Analysis evaluates five dimensions per entity
5. **Reasons** — Reasoning Engine and Hypothesis Engine determine meaning
6. **Prioritizes** — Opportunity Engine separates Hit Quality from User Value
7. **Tracks** — Opportunity Lifecycle follows development over time
8. **Delivers** — Presentation layer explains what, why, and how confident
9. **Learns** — Feedback and Learning System improve over time

---

## Core Rules — Non-Negotiable

- Every layer is **stateless** except the Memory System
- **Only the Learning System** writes to Memory and User Model
- **All detectors** produce `OpportunityEvidence` — the same shape regardless of detector type
- **Hit Quality and User Value are always separate scores** — never collapsed before decision
- Every object includes `schema_version: "1.0"`
- Every layer emits `ExecutionMetrics` for observability
- Every layer may append to `decision_trace` for explainability
- The Opportunity Engine **recommends** — it does not choose presentation format
- Policy and Safety controls **how** Logan communicates — not whether something matters

---

## The Three Critical Separations

```
Reasoning Engine      Answers: What does this event mean?
User Model            Answers: Who is this user right now, and what matters to them?
Opportunity Engine    Answers: Of everything Logan understands, what deserves attention now?
```

Understanding an event does not mean surfacing it.
Being personally relevant does not mean being urgent enough to interrupt.

---

## Hit Quality vs User Value

This separation is fundamental to Logan's personalization.

| | Hit Quality | User Value |
|--|-------------|------------|
| **What it measures** | Objective opportunity strength | Value to this specific user |
| **Same for all users?** | Yes | No |
| **Computed from** | Domain dimensions, evidence strength, trust | Hit Quality × user interest × timing × risk alignment |
| **Example** | Biotech hit: 96% | Same user: 22% → suppressed |

Logan never surfaces a low User Value hit regardless of Hit Quality.

---

## What Already Exists

See `09_CURRENT_STATE.md` for the full current codebase description.

---

## Development Posture

```
80%   implementation and refinement
20%   architectural evolution
```

Architecture is frozen at v1.3. Future structural changes require a clear identified flaw — not new ideas. The value now comes from execution quality, not architectural invention.

---

## The Differentiator

| What exists elsewhere | What Logan adds |
|----------------------|-----------------|
| Signal detection (quant funds) | Personalization inside the scoring pipeline |
| Cross-domain linking (Palantir — enterprise only) | Consumer-level explainability |
| Explainability (Kensho — institutional only) | Memory and learning per user |
| Personalization (Netflix/Spotify — different domain) | Mental models and hypothesis testing |
| — | Opportunity lifecycle tracking |
| — | Weak signal discovery before headlines |
| — | The Opportunity Field UI |

Nobody has combined these for a consumer audience.
The quant world has the intelligence but no interface.
The consumer apps have the interface but no intelligence.
Logan builds both and connects them through personalization and memory.
