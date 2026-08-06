# Logan Intelligence — Claude Engineering Guide
**Version:** 3.1.3
*Source: Architecture v1.3 FINAL (2026-07-31). Original: “source_material/17_CLAUDE_ENGINEERING_GUIDE.md” (historical label).*

*This document tells Claude how to think about, work on, and evolve Logan Intelligence. Read it before every session.*
**TriggerEvent status:** rules below that assume a live TriggerEvent registry enforcement mechanism are SPECIFIED — NOT IMPLEMENTED (V3.1.4 BATCH-3, OD-009). There is no TriggerEvent object or registry-validation code in `logan_core/` as of V3.1.4; do not build it as part of V3.1.4 work.

---

## How to Start Every Session

1. Read `00_MASTER_BRIEF.md` — orientation
2. Read this file — how to work
3. Read `15_DECISIONS.md` — what cannot change
4. Read `20_LOGAN_PRINCIPLES.md` — why Logan exists
5. Ask: "What phase are we in?" (refer to `16_ROADMAP.md` and `08_BUILD_ORDER.md`)
6. Do not start coding until you understand which phase gate you're working toward
7. Before any Phase 1 broad build: confirm Sprint 2A vertical slice has passed its gate

---

## What Logan Is

Logan is not a chatbot. It is not a news aggregator. It is not a recommendation engine.

**It is a reasoning operating system.** A continuous intelligence pipeline that builds, tests, updates, and communicates a model of the world on behalf of each individual user.

Every feature, every layer, every line of code should trace back to this definition. If something you're building doesn't serve the reasoning pipeline, the personalization, or the delivery of intelligence — question whether it belongs.

---

## Architecture Philosophy

**The architecture is the product.** Logan's 18-layer pipeline is not an implementation detail — it IS what Logan is. When you implement a layer, you are building the product, not scaffolding for it.

**Implement faithfully.** The architecture was designed through deliberate critique cycles. Your job is to implement it with precision, not to redesign it. If you see a flaw, document it in `15_DECISIONS.md` and raise it — don't silently work around it.

**Vertical slice first.** The first goal of Sprint 2 is a full end-to-end vertical slice (one signal → one opportunity → rendered in app → feedback captured). Do NOT build all domains before proving the pipeline works end-to-end. See `16_ROADMAP.md` Sprint 2A and `08_BUILD_ORDER.md`.

**One phase at a time.** The build order in `08_BUILD_ORDER.md` exists because each phase builds the foundation the next phase needs. Do not build Phase 3 logic inside Phase 2 code. Do not jump ahead. Complete the phase gate before moving on.

**The phase gate is real.** Every phase has a gate with specific criteria. You must verify the gate before declaring a phase complete. The gates are not suggestions — they are the minimum quality bar for each phase.

---

## What Is LOCKED (Cannot Change Without Review)

These rules are LOCKED. Before changing any of them, document why in `15_DECISIONS.md` and get explicit approval.

1. **Only the Learning System writes to Memory.** Enforced at infrastructure level. No exceptions.
2. **Hit Quality and User Value are always separate scores.** Never collapse them before the Opportunity Engine.
3. **All detectors produce OpportunityEvidence.** Same schema, regardless of detector type.
4. **Every layer is stateless** (except Memory System).
5. **The Hypothesis Engine must attempt to disprove** before advancing a hypothesis.
6. **Logan never executes.** Read-only, advisory. No trades, bets, or orders.
7. **Every object carries `schema_version: "1.0"`.** Schema bumps require a review.
8. **No layer calls another layer directly.** All communication through the Orchestrator.
9. **Explicit uncertainty is required.** When confidence is insufficient, Logan says so. Never suppress the "I don't know yet" signal.
10. **TriggerEvent codes must be registered.** No unregistered code may enter the pipeline. Registry is authoritative.
11. **Community momentum maps to node edge glow only.** It does not map to brightness, size, or proximity. This is non-negotiable. (DECISION-016)
12. **`why_it_matters_to_me` is always the first rendered field on the opportunity card.**

---

## What Claude May Improve

Within the LOCKED constraints above, Claude has latitude to improve:

- **Implementation details** — algorithms, data structures, specific logic within a layer
- **Performance optimizations** — caching, query optimization, async patterns
- **Error handling** — resilience, retry logic, graceful degradation
- **Test coverage** — adding tests is always good
- **Code organization** — within the folder structure defined in `14_ENGINEERING_STANDARDS.md`
- **API design** — endpoint structure, response shapes (as long as contracts are honored)
- **Mobile UX details** — animation timing, gesture handling, within the visual language defined in `12_VISUAL_LANGUAGE.md`

When improving, ask: "Does this change preserve the architecture?" If yes, proceed. If unsure, ask first.

---

## Coding Philosophy

**Match the architecture in the code.** Layer names in the architecture should map to class and file names in the code. A reader of the code should be able to navigate to `07_DATA_CONTRACTS.md` and find exact matches.

**Data contracts are truth.** The Pydantic models (backend) and TypeScript interfaces (mobile) must match `07_DATA_CONTRACTS.md` exactly. The code derives from the contracts, not the other way around.

**Stateless by default.** Unless you're working on the Memory System or Learning System, your layer should have no persistent state. If you find yourself adding instance variables that persist between pipeline runs, stop and reconsider.

**Fail explicitly.** Missing data is "data unavailable" — not silently dropped. Failed validation is a rejection with a log entry — not a quiet pass-through. Unexpected states should surface as errors, not be swallowed.

**Observability everywhere.** Every layer emits `ExecutionMetrics`. Every layer can append to `decision_trace`. This is not optional. The pipeline must be debuggable.

**TriggerEvent codes come only from the registry.** Before emitting a TriggerEvent in any receptor or detector, verify the code exists in the appropriate domain registry (`TRIGGER_REGISTRY_STOCKS.md`, etc.) and in `TRIGGER_REGISTRY_GLOBAL.md`. Unregistered codes are rejected, not passed through.

---

## UI Philosophy in Code

**The Opportunity Field is the product's defining experience.** When working on the mobile app:

- Performance is non-negotiable. 60fps minimum. 120fps on ProMotion. If an animation can't hit 60fps, remove it.
- The field should feel alive. Node drift is ambient and continuous, not event-triggered.
- Glass effects are for cards and overlays, not the Skia canvas.
- The empty field is correct behavior — do not add placeholder content, loading spinners, or "nothing here yet" messages to the field itself. Calm is the point.
- **Edge glow = community momentum.** Do not route community momentum to any other visual property. This is LOCKED.
- **Reduced-motion mode is required.** All animations must have a static/reduced fallback. Drift → stationary. Pulse → static glow. Ripple → skip. The intelligence is still visible; only the motion is removed.

**Never add a list as the primary interface.** If you find yourself building a list of opportunities as the home screen, stop. That is not Logan.

---

## How to Handle Ambiguity

When the specification is unclear:

1. **Check `15_DECISIONS.md` first** — many ambiguous situations were already decided
2. **Check `07_DATA_CONTRACTS.md`** — if the object shape is defined, implement exactly that
3. **Check `06_LAYER_INTERFACE_SPECIFICATION.md`** — if the layer's allowed/forbidden behaviors are defined, follow them
4. **Check the relevant TriggerEvent registry** — if the trigger code behavior is defined, follow it
5. **When genuinely unclear:** implement the simpler interpretation, flag it clearly in a comment, and raise it for review. Do not invent complex behavior to fill ambiguous gaps.

---

## How to Propose Changes

If you identify something that should change in the architecture:

1. Do not silently implement the change
2. Document the proposed change: what, why, what alternatives you considered
3. Add it to `15_DECISIONS.md` as a proposed decision
4. Continue implementing the current spec until the change is approved

This keeps the documentation synchronized with the actual architecture. Silent divergence between docs and code is worse than the original flaw.

---

## Common Mistakes to Avoid

- **Collapsing Hit Quality and User Value** — they stay separate until the Opportunity Engine decision
- **Writing to Memory from a non-Learning-System layer** — this is a hard error, not a warning
- **Building breadth before proving vertical slice** — Sprint 2A proves end-to-end first
- **Building Phase N+1 logic inside Phase N** — complete the gate first
- **Adding business logic to the Orchestrator** — the Orchestrator wires layers, it does not decide
- **Skipping ExecutionMetrics** — every layer emits them, every time
- **Treating the empty Opportunity Field as an error state** — calm is correct
- **Adding a list view as the primary UI surface** — the field is primary
- **Emitting an unregistered TriggerEvent code** — verify against registry before emitting
- **Routing community momentum to node brightness or proximity** — edge glow only, always (LOCKED)
- **Omitting why_it_matters_to_me or rendering it below other fields** — it is always first

---

## Source Material

The `source_material/` folder contains the original spec files from the architecture v1.3 session (2026-07-31). When in doubt about technical spec details, check `source_material/` — those files are the ground truth from the architecture session.

Key files:
- `source_material/02_LAYER_INTERFACES.md` — per-layer I/O contracts (canonical in `06_LAYER_INTERFACE_SPECIFICATION.md`)
- `source_material/03_DATA_CONTRACTS.md` — all object schemas (canonical in `07_DATA_CONTRACTS.md`)
- `source_material/08_BUILD_ORDER.md` — original build order (canonical in `08_BUILD_ORDER.md`)

The TriggerEvent framework files (`TRIGGER_EVENT_FRAMEWORK.md`, all “TRIGGER_REGISTRY_*.md” (historical label)) are new in v3.1.2 and have no prior v3.1 source material equivalents. They are authoritative as written.

---

## Session End Protocol

At the end of a working session:
1. Update `18_SESSION_LOG.md` with what was accomplished, what changed, and what's next
2. Update `23_CURRENT_IMPLEMENTATION_STATE.md` — document what is built and verified
3. Verify phase gate progress — document which gate criteria are met
4. Flag any open questions or decisions that need to be made
5. Note any deviations from the spec that were made and why

This keeps the documentation synchronized and makes it easy to pick up in the next session.

---

*Logan Intelligence Claude Engineering Guide — v3.1.2 | 2026-08-03*
*v3.1.2 changes: LOCKED list expanded: TriggerEvent registry enforcement (rule 10), Community momentum edge-glow-only (rule 11), why_it_matters_to_me first (rule 12). "Non-negotiable" replaced with LOCKED throughout. TriggerEvent registry check added to "How to Handle Ambiguity". TriggerEvent coding rule added. Community momentum UI coding rule added (LOCKED). Reduced-motion requirement added to UI section. Common mistakes expanded with three new items. Sprint 2A check added to session start protocol.*


---
## v3.1.2 Trigger Rules

- Use stable TriggerEvent identity and linked revisions.
- Deduplicate by underlying event before scoring.
- Treat domain impacts as one event, not duplicate catalysts.
- Enforce conflict/override and policy gates.
- Log provenance and recommendation contribution.
- Build Slice 0 deterministic fixture before Slice 1 live receptor.
