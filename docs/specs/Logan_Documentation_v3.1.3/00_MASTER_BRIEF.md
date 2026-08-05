# Logan Intelligence — Master Brief
**Version:** 3.1.3 | **Architecture:** v1.3 FINAL | **Status:** Ready for Sprint 2A — Vertical Slice First

---

## Vision

A world where every person has access to the same quality of intelligence that institutional investors, professional analysts, and elite decision-makers use every day — but personalized to them, explained in plain language, and available on their phone.

---

## Mission

Logan exists to transform overwhelming information into personalized intelligence.

It does not answer questions. It continuously reasons about the world and the user simultaneously, and determines: **What deserves this person's attention right now — and why?**

---

## Product Overview

Logan Intelligence is the reasoning and intelligence engine behind a consumer-facing mobile application. The consumer-facing app name is **TBD** (candidates: **Riser**, **Apex**). Logan is the internal name for the intelligence engine. These are documented separately and must not be conflated.

The intelligence engine monitors markets, sports, prediction markets, crypto, music and culture, personal finance, and economic signals — then cross-references everything against what it knows about the specific user.

It is not:
- A news aggregator
- A stock screener
- A trading platform
- A chatbot
- A dashboard

It is a **reasoning operating system** — a continuous intelligence layer that builds, tests, updates, and communicates a model of the world on behalf of each individual user.

---

## Naming Structure

| Name | Role | Status |
|------|------|--------|
| **Logan** | Internal intelligence engine name | LOCKED |
| Consumer app name | End-user product name | **TBD** — not selected |
| **Riser** | Candidate consumer app name | CANDIDATE |
| **Apex** | Candidate consumer app name | CANDIDATE |
| **Garris Engineering** | Possible parent or publisher entity | CANDIDATE — not finalized |

Do not refer to "Logan Intelligence" as a finalized app-store name. Do not treat Garris Engineering as a confirmed legal entity.

---

## Core Philosophy

**1. Logan informs. The user decides.**
Logan never places trades, bets, or executes anything. It recommends. The user acts — always in the original linked app. This is **LOCKED** for the current implementation cycle.

**2. Everything is connected.**
News, markets, sports, politics, economics, sentiment, personal goals — Logan's job is to find the relationships between them that no single app would show you.

**3. Intelligence is continuous.**
The UI is a snapshot. The brain never stops. Logan is always reasoning, even when the screen is off.

**4. Personalized, not generic.**
The same world event means something different to different users. Logan knows the difference. A NVIDIA earnings beat means one thing if you own it, another if you have a competing bet, and nothing at all if you don't care about tech.

**5. Explainability is required.**
Every recommendation must have a traceable reason. Logan never says "consider this" without explaining why, how confident it is, and what would change that.

---

## Target Users

**Primary:** Individual investors who also participate in sports betting or prediction markets and want one intelligent layer above all their apps.

**Secondary:** Anyone who feels overwhelmed by information fragmentation — too many apps, too many notifications, no one connecting the dots.

**Persona examples:**
- The active retail investor who also bets on sports and wants cross-platform awareness
- The prediction market participant who wants macro context on their positions
- The professional who wants signal over noise across everything they care about

---

## Competitive Advantage

| What exists elsewhere | What Logan adds |
|---|---|
| Signal detection (quant funds) | Personalization inside the scoring pipeline |
| Cross-domain linking (Palantir — enterprise only) | Consumer-level explainability |
| Explainability (Kensho — institutional only) | Memory and learning per user |
| Personalization (Netflix/Spotify — different domain) | Mental models and hypothesis testing |
| — | Opportunity lifecycle tracking |
| — | Weak signal discovery before headlines |
| — | The Opportunity Field UI |
| — | Read & Suggest cross-platform intelligence |
| — | TriggerEvent framework — one event, multiple domain impacts |

---

## Long-Term Vision

**Near-term:** The best personal intelligence layer for individual investors and bettors.

**Mid-term:** The intelligence operating system for every important decision a person makes — career, real estate, business, health, family.

**Long-term:** A personalized reasoning engine that knows how you think, learns from every decision you make, and becomes the most valuable tool in your life.

The Read & Suggest feature is the beginning. Over time, every domain of a person's life becomes something Logan reasons about.

---

## Roadmap Summary

| Phase | Focus |
|---|---|
| Sprint 1 (complete) | Architecture v1.3, full specification package, brain v2.0 |
| Sprint 2A (current) | **Vertical slice first** — one signal → full pipeline → one opportunity → app → feedback |
| Sprint 2B–F | Broad backend implementation — 6-phase build order |
| Sprint 3 | Read & Suggest account linking, portfolio intelligence |
| Beta | End-to-end working app with 5+ core domains |
| V1 Launch | Consumer release, full domains, Read & Suggest |
| V2 | Behavioral learning depth, Mental Model expansion, enterprise |

> **Sprint 2A overrides all broad phase work.** Do not build all domains, receptors, or cognitive layers before a working end-to-end vertical slice exists. See `08_BUILD_ORDER.md`.

---

## Document Index

### Core Documents

| File | Purpose | Read when |
|---|---|---|
| `00_MASTER_BRIEF.md` | This file — orientation | Always first |
| `01_PRODUCT_SPECIFICATION.md` | Full product definition | Product decisions |
| `02_LOGAN_INTELLIGENCE_BRAIN.md` | The brain Bible | All development |
| `03_MEMORY_ARCHITECTURE.md` | Memory system deep spec | Memory implementation |
| `04_WORLD_MODEL.md` | World representation spec | World Model layer |
| `05_SYSTEM_ARCHITECTURE.md` | Full software architecture | System design |
| `06_LAYER_INTERFACE_SPECIFICATION.md` | Per-layer I/O contracts | Before any layer work |
| `07_DATA_CONTRACTS.md` | Every JSON object defined | Before any schema work |
| `08_BUILD_ORDER.md` | Build phases + vertical slice plan | All engineering |
| `09_READ_AND_SUGGEST.md` | Account linking feature | Read & Suggest work |
| `10_OPPORTUNITY_ENGINE.md` | Opportunity lifecycle + decay | Opportunity work |
| `11_UI_PHILOSOPHY.md` | Interface design philosophy | All UI work |
| `12_VISUAL_LANGUAGE.md` | Design system | Visual implementation |
| `13_BRANDING.md` | Brand identity | Brand/marketing |
| `14_ENGINEERING_STANDARDS.md` | Code standards | All engineering |
| `15_DECISIONS.md` | Locked architectural decisions | Before changing anything |
| `16_ROADMAP.md` | Sprint plan and milestones | Planning |
| `17_CLAUDE_ENGINEERING_GUIDE.md` | Product/architecture orientation for AI-assisted sessions — not governing authority (see root `CLAUDE.md` and `docs/DECISIONS.md` ADR-038) | Session orientation |
| `18_SESSION_LOG.md` | Development history | Historical reference |
| `19_FUTURE_IDEAS.md` | Ideas not yet scheduled | Inspiration, backlog |
| `20_LOGAN_PRINCIPLES.md` | The company constitution | All decisions |
| `21_TRENDING_ENGAGEMENT.md` | Community signal spec + UI contract | Trending work |
| `22_OPPORTUNITY_CARD_SPEC.md` | Full card spec with all fields | UI/card work |
| `23_CURRENT_IMPLEMENTATION_STATE.md` | Unverified implementation snapshot | Before coding sessions |
| `24_API_SPECIFICATION.md` | Full API spec with examples | API implementation |
| `25_INTEGRATION_FEASIBILITY.md` | Integration feasibility matrix | Account linking work |
| `26_GOLDEN_TEST_SCENARIOS.md` | 25 machine-readable test scenarios | Testing |
| `27_SECURITY_PRIVACY_COMPLIANCE.md` | Privacy, security, compliance | Before any data handling |
| `28_PACKAGE_MANIFEST.md` | Complete file inventory | Package management |

### TriggerEvent Framework (new in v3.1.2)

| File | Purpose | Read when |
|---|---|---|
| `TRIGGER_EVENT_FRAMEWORK.md` | Global TriggerEvent contract, terminology, states | All signal/detection work |
| `TRIGGER_REGISTRY_GLOBAL.md` | Cross-domain trigger categories and overview | Any trigger work |
| `TRIGGER_REGISTRY_STOCKS.md` | All stock/investing trigger codes | Stocks domain work |
| `TRIGGER_REGISTRY_SPORTS.md` | All sports betting trigger codes | Sports domain work |
| `TRIGGER_REGISTRY_PREDICTION_MARKETS.md` | Prediction market trigger codes | Prediction markets work |
| `TRIGGER_REGISTRY_CRYPTO.md` | Crypto domain trigger codes | Crypto domain work |
| `TRIGGER_REGISTRY_CULTURE.md` | Music, culture, social trend trigger codes | Culture domain work |
| `TRIGGER_REGISTRY_PERSONAL_FINANCE.md` | Personal finance trigger codes | Finance domain work |
| `TRIGGER_SCORING_AND_CONFLICT_RULES.md` | How triggers affect scores, conflict resolution | Scoring/reasoning work |
| `ENTITY_RESOLUTION.md` | Canonical entity graph, aliases, cross-domain relationships | Entity work |
| `NOTIFICATION_POLICY.md` | Complete notification eligibility rules | Notification work |
| `OUTCOME_EVALUATION.md` | Outcome attribution per domain | Learning system work |

### Audit and Package Management

| File | Purpose |
|---|---|
| `DOCUMENTATION_CHANGELOG_v3.1.2.md` | Changes from v3.1 → v3.1.2 |
| `DOCUMENTATION_REFERENCE_AUDIT.md` | Reference scan results, consistency verification |

### Archived Source Specifications

| File | Purpose |
|---|---|
| `source_material/00_MASTER_BRIEF.md` | Original architecture brief (v1.3 session, 2026-07-31) |
| `source_material/01_ARCHITECTURE.md` | Original architecture document |
| `source_material/02_LAYER_INTERFACES.md` | Per-layer I/O contracts (canonical in `06_LAYER_INTERFACE_SPECIFICATION.md`) |
| `source_material/03_DATA_CONTRACTS.md` | All 25+ object schemas (canonical in `07_DATA_CONTRACTS.md`) |
| `source_material/04_HIT_DETECTION.md` | Original hit detection spec |
| `source_material/05_DOMAIN_FRAMEWORK.md` | Original domain framework |
| `source_material/06_OPPORTUNITY_LIFECYCLE.md` | Original lifecycle spec |
| `source_material/07_OPPORTUNITY_DECAY.md` | Original decay engine spec |
| `source_material/08_BUILD_ORDER.md` | Original build order |
| `source_material/09_CURRENT_STATE.md` | Original state file |

---

*Logan Intelligence — v3.1.2 | 2026-08-03*
*v3.1.2 changes: Complete TriggerEvent framework added. Consumer app name clarified as TBD (Riser/Apex candidates). Decision status labels applied throughout. Vertical-slice-first build priority reinforced. All file references corrected. 13 new framework files added to index. See `DOCUMENTATION_CHANGELOG_v3.1.2.md` for full changes.*
