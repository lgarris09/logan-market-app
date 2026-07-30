# CLAUDE.md

Instructions for Claude Code (and any other AI assistant) working in this repository. This file governs
*how* AI assistants operate here — for what the product is and how the codebase is built, read
[README.md](README.md) and the [docs/](docs/) directory first; don't duplicate that context here.

**Anchor, in one line:** Logan is an opportunity intelligence platform — not a market app, not a chatbot,
not a feed. Every suggestion, feature, or line of copy should be evaluated against "does this help the
user recognize something meaningful they'd otherwise have missed?" See
[PRODUCT.md](docs/PRODUCT.md#mission) for the full mission.

Read the rest based on the task, not always all five:
- Any product/UX-adjacent task, or anything touching Memory, User Model, or reasoning: read
  `docs/PRODUCT.md` and `docs/ARCHITECTURE.md` first.
- **Any work inside `logan_core/`**: read `docs/specs/LOGAN_ARCHITECTURE_v1.0.md`,
  `docs/specs/LOGAN_DATA_CONTRACTS_v1.0.md`, and `docs/specs/LOGAN_IMPLEMENTATION_PLAN.md` first — these
  are the locked, canonical interface/contract specification, not background reading. Do not implement a
  layer without reading its interface section.
- Any task involving code style, git, tests, or security: read `docs/STANDARDS.md`.
- Before any non-trivial change: skim `docs/DECISIONS.md` for recent ADRs that might already cover it.
- `docs/ROADMAP.md` only when the task is about sequencing or scope, not implementation detail.
- A narrow, well-scoped bugfix doesn't need all of these read — use judgment, but when in doubt, read more
  rather than less.

## Collaboration model: propose, human approves everything

Per [ADR-008](docs/DECISIONS.md#adr-008-ai-collaboration-model--propose-human-approves-everything).
This is the current setting, chosen deliberately for this project's maturity — not a generic caution
template. It may loosen over time; check ADR-008's status before assuming it still holds.

**Always requires explicit human confirmation before executing, not just before merging:**
- Any `git commit`, `git push`, or PR merge.
- Any database schema change or migration (`memory_engine.py`'s SQLite schema included).
- Any dependency addition, removal, or version bump (`requirements.txt`, `package.json`).
- Any change to CI/CD, branch protection, or repository settings.
- Any change that touches secrets, auth, or CORS configuration.
- Deleting or overwriting data, including local `backend/data/logan_memory.db`.

**Free to do without asking each time:**
- Reading code, running the app locally, running the existing test suite.
- Researching and proposing a plan or design.
- Drafting code changes in the working tree for the human to review before anything is committed.

If a task seems to require one of the "always confirm" actions to make progress, stop and ask rather
than finding a workaround (e.g. don't switch to editing the SQLite file directly to avoid asking about
a schema change).

## Product guardrail: analysis, not advice

Per [ADR-002](docs/DECISIONS.md#adr-002-logan-personalizes-and-contextualizes--it-does-not-give-directive-advice-phase-1),
reaffirmed by [ADR-010](docs/DECISIONS.md#adr-010-advice-boundary-reaffirmed-against-vision-language-confidently-decide-what-to-do-next)
and [PRODUCT.md](docs/PRODUCT.md#the-analysis-vs-advice-boundary). This is the one product rule worth
repeating here because it's easy for an AI assistant to violate unintentionally while writing copy,
prompts, or response-generation logic: **Logan explains relevance and helps a user decide how much
attention something deserves. It does not tell users what to buy, bet, or trade.** Vision-doc phrases
like "confidently decide what to do next" mean the former, not the latter — treat that distinction as
precise, not loose. If you're generating any user-facing text (API responses, UI copy, prompt templates
for an LLM layer, notification/ripple messaging), check it against that line before proposing it. If a
task seems to require crossing it, stop and flag it rather than writing directive language — that
boundary needs a human decision and a new ADR, not a judgment call made silently while implementing
something else.

**Related, tightened rule:** per
[ADR-013](docs/DECISIONS.md#adr-013-fomourgency-risk-tightened--betting-and-prediction-markets-must-stay-objective),
sports betting and prediction-market (Polymarket) content must stay objective and data-forward — no
urgency-driven or persuasive framing, even though excitement/curiosity framing is fine for other domains
like stocks, business, or careers. If you're generating copy for betting/prediction-market opportunities
specifically, hold it to a stricter, more neutral tone than the rest of the product. A legal/compliance
review of the broader FOMO pattern remains a required milestone before Phase 2 — don't treat it as settled
just because it's in PRODUCT.md.

## Layer ownership rules (`logan_core/`)

The Logan Intelligence System architecture (`docs/specs/`) is built around strict ownership boundaries.
These are architectural guarantees, not style preferences — violating one to "simplify" a change is a bug,
not a shortcut:

- **Only the Learning System writes durable Memory or User Model updates.** Not Reasoning, not the API
  layer, not a convenient direct write from a request handler.
- **Only the System Orchestrator writes Operational History.**
- **Only the Opportunity Engine scores or ranks.** Only **Policy & Safety** suppresses or constrains
  communication. Only **Presentation** chooses surface/format. Only **Presentation** sends notifications.
- If a task seems to require crossing one of these boundaries to work, that's a sign the task needs a
  different design, not a one-off exception — stop and flag it rather than routing around the boundary.
- Full ownership table: `docs/specs/LOGAN_ARCHITECTURE_v1.0.md` → "What no layer may do without
  authorization."

## Engineering standards to follow without being asked

These are documented in full in [docs/STANDARDS.md](docs/STANDARDS.md) — the summary below is not a
substitute for reading it on any non-trivial task:

- Trunk-based git workflow, Conventional Commits, PRs for all changes (even solo).
- Python: Black + Ruff, type hints, `mypy`. TypeScript: `strict` mode, ESLint + Prettier.
- Inside `logan_core/`: unit + contract-validation + pipeline-integration tests are required per layer
  (see [ADR-018](docs/DECISIONS.md#adr-018-stricter-per-layer-testing-bar-adopted-for-the-logan_core-pipeline)).
  Everywhere else (`mobile/`, historical `backend/`): pragmatic, per
  [ADR-005](docs/DECISIONS.md#adr-005-pragmatic-testing-bar-during-mvppre-launch).
- New backend work happens in `logan_core/` (one folder per layer — see
  [ADR-017](docs/DECISIONS.md#adr-017-new-top-level-logan_core-directory-with-one-folder-per-layer)).
  `backend/app/` is a historical prototype, left running and untouched, not a place to add new pipeline
  logic.
- No secrets in source control, ever — including in code you write for tests or examples.
- Don't build against infrastructure that isn't decided (database/hosting — see
  [ADR-006](docs/DECISIONS.md#adr-006-database-and-hosting--open-decision)); flag it as an open
  dependency instead of guessing.
- Business/reasoning logic stays server-side behind the versioned API, with no client-specific
  assumptions baked in — Logan Core is meant to eventually serve mobile, web, and desktop clients (see
  [ADR-012](docs/DECISIONS.md#adr-012-logan-core-keeps-clean-api-boundaries-now-no-multi-client-platform-tooling-yet)).
  This is a discipline to maintain now, not a reason to build multi-client tooling yet.
- Memory is modeled as flat, category-tagged records today, but the product's "ripple" concept
  (one event affecting many related opportunities) is inherently relational/graph-shaped. Don't assume
  the current schema is the final shape of memory — flag data-modeling decisions in this area rather
  than extending the flat-record model further without discussion.

## When you make or discover a decision

If you propose (and the human accepts) a non-trivial technical or product decision, add an ADR to
[docs/DECISIONS.md](docs/DECISIONS.md) using its template as part of the same change — don't leave it
for later. This includes interaction/motion design decisions that look like implementation detail but
actually encode product reasoning — e.g. how confidence maps to an opportunity's position in the wheel,
or ripple propagation rules — not just schema or infra choices. If you notice docs have drifted from what
the code actually does, flag it explicitly rather than silently working around the mismatch.

## Do not modify without being asked

- Anything under `docs/` or this file — these encode human decisions about the project. They are edited
  only through an explicit review conversation like the one that produced this version, never
  autonomously or as a side effect of an unrelated task.
- Existing application code, until the human has reviewed and approved the specific plan for a change —
  per the current engineering-foundation-first phase of this project.
