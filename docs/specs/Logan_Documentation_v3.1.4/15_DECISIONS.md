# Logan Intelligence — Architectural Decisions
**Version:** 3.1.3
*Source: Architecture v1.3 FINAL (2026-07-31). Original: “source_material/15_DECISIONS.md” (historical label).*

**Status labels:** `[LOCKED]` = permanent architectural decision | `[PROVISIONAL]` = working assumption, subject to change | `[RESEARCH REQUIRED]` = decision needed before this area is built | `[DEFERRED]` = intentionally deferred to a future version

Every major decision is recorded here with its rationale and the alternatives that were rejected.
Before changing anything fundamental, read this file. If you're about to undo a decision made here, you need a documented reason that's stronger than the original.

---

## DECISION-001: Execution stays with the user

**Decision:** Logan never places trades, bets, or orders. It is read-only and advisory. The user always executes in the original linked app.

**Rationale:**
- Regulatory simplicity — executing on behalf of users creates money-transmitter, broker-dealer, and gambling operator regulatory requirements in most jurisdictions. Advisory-only avoids this entirely for V1.
- Trust-building — users need to trust Logan's intelligence before they would trust it to act autonomously. Advisory first establishes that trust.
- User control — the product philosophy is "Logan informs, the user decides." Autonomous execution contradicts this.
- Risk reduction — if Logan makes a bad call and a user loses money because Logan executed it, the product relationship is destroyed. If Logan advises and the user chooses to act, the user retains agency.

**Alternative rejected:** Autonomous execution with user permission sliders.
**Reason rejected:** Regulatory complexity, trust requirement not yet established, contradicts core philosophy.

**Status:** `[LOCKED]` — Cannot be reversed without a full product and legal review documented in this file.

---

## DECISION-002: Only the Learning System writes to Memory

**Decision:** All layers in the pipeline are read-only to Memory. Only the Learning System may write.

**Rationale:**
- Prevents hidden state mutation — if any layer could write to memory, debugging unexpected behavior would require tracing writes across 18 layers
- Prevents race conditions — concurrent pipeline runs would corrupt memory if multiple layers could write simultaneously
- Makes reasoning deterministic — given the same inputs and the same memory state, the pipeline produces the same outputs
- Forces explicit learning — changes to the user model must go through deliberate outcome processing, not incidental side effects

**Alternative rejected:** Layers can write to their own memory namespace.
**Reason rejected:** Namespace isolation doesn't prevent the debugging and race condition problems. The discipline of a single writer is the point.

**Status:** `[LOCKED]` — Enforced at infrastructure level.

---

## DECISION-003: Hit Quality and User Value are always separate scores

**Decision:** The objective opportunity strength (Hit Quality) and the personalized user relevance (User Value) are computed and stored separately. They are never collapsed into a single score before the Opportunity Engine decision.

**Rationale:**
- Explainability — users can see that something has high objective quality but low personal relevance, and understand why Logan didn't surface it
- Debugging — separating the scores makes it possible to diagnose whether a surfacing failure was due to objective weakness or personalization mismatch
- Future flexibility — the weighting between Hit Quality and User Value can be tuned without redesigning the scoring pipeline
- User trust — showing both scores builds confidence that Logan's personalization is working correctly

**Alternative rejected:** Single blended score from the start.
**Reason rejected:** Loses explainability and makes debugging nearly impossible.

**Status:** `[LOCKED]` — Locked in the data contract schema (`07_DATA_CONTRACTS.md`).

---

## DECISION-004: All detectors produce the same OpportunityEvidence shape

**Decision:** The Convergence Detector, Divergence Detector, Pattern Engine, and ODSE all produce an `OpportunityEvidence` object with the same schema, regardless of how different their internal logic is.

**Rationale:**
- Downstream uniformity — every layer after Hit Detection can process evidence without knowing which detector produced it
- Extensibility — adding a fifth detector requires no changes to any downstream layer
- Testability — the Evidence Assembler can be tested independently of detector logic

**Alternative rejected:** Each detector produces its own output schema.
**Reason rejected:** Creates a combinatorial complexity problem downstream. Every layer would need to handle N different evidence shapes.

**Status:** `[LOCKED]` — Part of the locked data contract (`07_DATA_CONTRACTS.md`).

---

## DECISION-005: Architecture v1.3 is frozen for implementation

**Decision:** The 18-layer pipeline architecture is declared frozen at v1.3. Future development is 80% implementation, 20% architectural evolution. Structural changes require a documented flaw in the current architecture — not new ideas.

**Rationale:**
- The architecture was designed through multiple iterative critique cycles. It is not a first draft.
- Architectural churn prevents implementation from making progress.
- The value comes from execution quality at this stage, not continued redesign.
- New ideas can be captured in `19_FUTURE_IDEAS.md` and evaluated for future versions.

**Alternative rejected:** Continue evolving architecture while building.
**Reason rejected:** Architectural evolution and implementation are competing for the same attention. Freezing the architecture allows implementation to progress.

**Status:** `[LOCKED]` — Architecture frozen at v1.3. Future major architecture changes require a documented case in this file.

---

## DECISION-006: The interface is a spatial field, not a list or dashboard

**Decision:** Logan's primary UI surface is the Opportunity Field — a radial, spatial canvas. There is no default list view, no dashboard, no feed.

**Rationale:**
- Lists imply equal weight — every item in a list competes equally for attention. Logan's whole purpose is to differentiate importance.
- Dashboards require scanning — the user has to do work to find what matters. Logan should surface what matters without requiring work.
- Spatial layout encodes meaning — proximity to center, brightness, and size are all information channels that a list can't provide.
- Differentiator — every competitor uses a list or a feed. The Opportunity Field is visually and functionally distinct.

**Alternative rejected:** List view with priority indicators.
**Reason rejected:** Priority indicators in lists are visually noisy and still require scanning. The spatial field is a fundamentally better fit for the intelligence model.

**Status:** `[LOCKED]` — Primary surface is the field. A list view may be added as an accessibility option or secondary view in V2, but the Opportunity Field remains primary.

---

## DECISION-007: 8-stage opportunity lifecycle

**Decision:** Every opportunity moves through exactly 8 defined stages: Watching → Detected → Emerging → Building Conviction → High Conviction → Action Window → Outcome → Learning.

**Rationale:**
- Stages communicate conviction, not just status — a user seeing "Building Conviction" understands something different than "Detected"
- Stages enable the Opportunity Portfolio — users can see what Logan is tracking at every level of confidence
- Lifecycle tracking prevents re-surfacing stale opportunities
- The Learning terminal stage closes the feedback loop explicitly

**Alternative rejected:** Simple active/inactive flag.
**Reason rejected:** Loses all nuance about conviction level, timing, and development velocity.

**Status:** `[LOCKED]` — Stage names and transition rules are locked.

---

## DECISION-008: Logan is named like a person, not a feature

**Decision:** The intelligence platform is named "Logan" — a human name — not a feature descriptor like "Pulse," "Signal," or "Radar."

**Rationale:**
- The product is meant to feel like a trusted advisor, not a data tool.
- Human names communicate relationship in a way that feature names cannot.
- "Logan" is direct, strong, and unassuming — it doesn't oversell.
- Competitors all use feature-descriptor names. Logan stands apart.

**Alternative rejected:** Trophy, Medal, Crown, Laurel, Podium, Gold, Signal, Pulse, Radar.
**Reason rejected:** These describe what the product does, not what it is.

**Status:** `[PROVISIONAL]` — Platform name (Logan Intelligence) is stable. Consumer app name is TBD; candidates are Riser, Apex, Logan. Decide before beta (DECISION-012 below). The 'person name' principle holds.

---

## DECISION-009: Hypothesis Engine must test to disprove, not just confirm

**Decision:** The Hypothesis Engine generates multiple candidate explanations and actively searches for evidence that would disprove each one before advancing any hypothesis.

**Rationale:**
- Confirmation bias is the primary failure mode of pattern-matching systems — they find what they're looking for and stop
- A system that only confirms produces overconfident wrong answers
- Requiring disconfirmation evidence before advancing a hypothesis catches the cases where the initial pattern was noise
- This is the scientific method applied to software reasoning

**Alternative rejected:** Generate hypotheses, rank by supporting evidence strength.
**Reason rejected:** Pure confirmation ranking produces confident wrong answers at high frequency.

**Status:** `[LOCKED]` — Part of the Hypothesis Engine specification.

---

## DECISION-010: Mobile-first, React Native

**Decision:** Logan is built as a mobile-first application using React Native with Expo and Skia for rendering.

**Rationale:**
- The target user checks their positions and places bets on mobile
- The Opportunity Field metaphor — an ambient, glanceable intelligence field — is native to mobile form factors
- Skia provides the rendering performance needed for the animated field
- React Native allows a single codebase for iOS and Android

**Alternative rejected:** Web-first, native iOS/Android.
**Reason rejected:** Web cannot match native rendering performance for the Opportunity Field animations. Separate native codebases double the development cost.

**Status:** `[PROVISIONAL]` — Mobile-first principle is solid. Specific framework choices (React Native, Expo, Skia) are working assumptions. Confirm before significant implementation investment.

---

## DECISION-015: TriggerEvent framework is a first-class pipeline object

**Decision:** TriggerEvent is a formally defined, registered pipeline object — not an ad-hoc annotation. Every trigger code must appear in an authoritative domain registry before it can enter the pipeline. Trigger codes follow a `DOMAIN_EVENT_DESCRIPTOR` naming convention (e.g., `STOCK_EARNINGS_BEAT`, `SPORTS_LINE_MOVE_SHARP`).

**Rationale:**
- Prevents undefined trigger codes from entering the pipeline and causing downstream scoring errors
- Makes trigger logic auditable — every registered code has a defined TTL, payload schema, and scoring adjustment
- Enables systematic outcome tracking per trigger code — Logan can learn which triggers have historically high or low predictive accuracy
- ML-based trigger code discovery would require knowing what a "valid" trigger looks like — the registry defines that ground truth

**Alternative rejected:** Freeform event tags emitted by receptors.
**Reason rejected:** Freeform tags can't be systematically scored, can't be tracked for outcome accuracy, and create debugging nightmares when two receptors emit slightly different strings for the same event type.

**Status:** `[LOCKED]` — TriggerEvent codes must be registered. No unregistered code may enter the pipeline.

---

## DECISION-016: Community momentum maps to edge glow only

**Decision:** Community Intelligence `momentum_score` maps exclusively to node edge glow in the Opportunity Field. It does NOT map to node brightness, size, or proximity to center. Those properties are reserved for Logan's assessed opportunity quality and user value.

**Rationale:**
- Conflating crowd activity with opportunity quality is one of the most dangerous failure modes for an intelligence product — it turns Logan into a social sentiment mirror instead of an independent reasoner
- A crowded, hyped opportunity with low objective quality should look low-priority in Logan's field, even if social volume is high
- Users must be able to trust that proximity and brightness represent Logan's independent assessment, not what everyone else is doing

**Alternative rejected:** Community momentum as a partial input to brightness or node size.
**Reason rejected:** Even partial conflation erodes the independence signal. The visual separation must be complete and consistent.

**Status:** `[LOCKED]` — Enforced in UI specification (`11_UI_PHILOSOPHY.md`), layer interface (`06_LAYER_INTERFACE_SPECIFICATION.md`), and visual language (`12_VISUAL_LANGUAGE.md`).

**v3.1.3 clarification:** This decision, as literally worded, locked only a UI-encoding rule. It said
nothing about the Learning System or aggregated trigger/source accuracy — a gap `21_TRENDING_ENGAGEMENT.md`'s
"Trending as Signal Amplifier" mechanism exploited (letting `momentum_score` multiply `priority_score`
directly, a live violation of this decision's spirit). `docs/DECISIONS.md` ADR-034 clarifies the full
boundary — popularity/momentum can never affect evidence, confidence, urgency, ranking, relevance,
recommendation direction, brightness, size, or proximity, under any mechanism — and records the removal
of that amplifier. Read this entry together with ADR-034; ADR-034 is authoritative on scope.

---

## Open Decisions — Research Required

### DECISION-011: Backend technology stack
`[RESEARCH REQUIRED]`

FastAPI + PostgreSQL + Redis is the current working assumption. Formal evaluation not yet completed. Decide before Phase 1 implementation begins.

### DECISION-012: Consumer app name
`[RESEARCH REQUIRED]`

Candidates: Riser, Apex, Logan (direct). Requires: app store name search, trademark clearance, domain check, user testing. Decide before beta launch. Do not use candidate names as if final in any code or external material.

### DECISION-013: Parent entity legal structure
`[RESEARCH REQUIRED]`

"Garris Engineering" is a candidate name. No legal entity established. Decide before any external-facing launch materials are published. Do not use "Garris Engineering" in external materials until this decision is LOCKED.

### DECISION-014: Cloud provider
`[DEFERRED]`

AWS, GCP, and Railway are all viable. Decision deferred until MVP is ready for deployment.

---

*Logan Intelligence Architectural Decisions — v3.1.2 | 2026-08-03*
*v3.1.2 changes: DECISION-015 added — TriggerEvent framework as first-class pipeline object (LOCKED). DECISION-016 added — Community momentum maps to edge glow only (LOCKED). "Permanent" language replaced with LOCKED throughout. Data contracts reference updated to 07_DATA_CONTRACTS.md. Status label legend updated: "permanent" removed, LOCKED defined clearly.*
*Add new decisions at the bottom with the next sequential number.*


---
## DECISION-017 — Stable TriggerEvent Identity with Versioned Revisions
**Status:** LOCKED for current implementation cycle

One underlying real-world event uses one stable `underlying_event_key`. Material changes create immutable linked revisions, not unrelated replacement events. Cross-domain impacts attach to the same TriggerEvent identity. Changes require ADR and user approval.

## DECISION-018 — Temporal Context Is Explicit
**Status:** LOCKED for current implementation cycle

Time of year, sessions, domain seasons, known-event countdowns, freshness, decay, and action-window timing are structured inputs. No generic monthly multiplier is permitted.
