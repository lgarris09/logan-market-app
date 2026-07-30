# Logan — Engineering Standards

This document is the day-to-day rulebook: how code gets written, reviewed, merged, tested, and secured.
See [ARCHITECTURE.md](ARCHITECTURE.md) for system design principles and [DECISIONS.md](DECISIONS.md) for
the reasoning behind these rules.

## Coding standards

Defaults per [ADR-007](DECISIONS.md#adr-007-industry-standard-formatting-linting-and-type-checking-defaults).

**Backend (Python)**
- Formatting: [Black](https://black.readthedocs.io/), default settings.
- Linting: [Ruff](https://docs.astral.sh/ruff/).
- Type hints on all new functions/methods; check with `mypy`. Existing untyped code is migrated
  opportunistically, not all at once.
- Pydantic models are the source of truth for API request/response shapes (already the pattern in
  `models.py` / `memory_models.py`) — keep it that way.

**Mobile (TypeScript / React Native)**
- `tsconfig.json` `strict: true`.
- Linting/formatting: ESLint + Prettier.
- Business logic (scoring, classification) does not belong in mobile components — it calls the backend
  API. Mobile code is presentation and interaction, not decision-making.

**General**
- Prefer clarity over cleverness. Logan's value is the product, not the code being impressive.
- No dead code, commented-out blocks, or speculative abstractions for hypothetical future needs — see
  [ARCHITECTURE.md](ARCHITECTURE.md) principle 6.
- Naming should describe what something *is*, not the history of how it got there.

## Git workflow

Per [ADR-004](DECISIONS.md#adr-004-trunk-based-development-with-conventional-commits).

- **Trunk-based development.** `main` is always deployable. Work happens on short-lived branches named
  `type/short-description` (e.g. `feat/memory-inbox-filters`, `fix/cors-config`).
- **Conventional Commits** for commit messages and PR titles: `feat:`, `fix:`, `chore:`, `docs:`,
  `refactor:`, `test:`, `perf:`. This keeps history scannable and enables changelog generation later.
- **All changes land via PR**, even solo — self-review by re-reading your own diff before merging is
  non-negotiable. This is process infrastructure for the team Logan is growing into, per
  [ADR-003](DECISIONS.md#adr-003-build-process-for-a-small-team-even-while-solo).
- **Squash merge** to keep `main` history one commit per logical change.
- Branch protection on `main`: no direct pushes, PR required. (Set this up in GitHub repo settings when
  the remote exists.)
- Keep branches short-lived — days, not weeks. Long-lived branches defeat the point of trunk-based
  development.

## Architecture principles

See [ARCHITECTURE.md](ARCHITECTURE.md) in full. In summary: the memory engine is the core asset and gets
the most scrutiny, the API is a versioned contract, infrastructure that isn't decided yet shouldn't be
assumed, business logic stays server-side, and config/secrets are never hardcoded.

## Security practices

Logan handles a user's personal behavioral and financial-interest data (the memory store) and touches
domains adjacent to financial advice and gambling — see
[ADR-002](DECISIONS.md#adr-002-logan-personalizes-and-contextualizes--it-does-not-give-directive-advice-phase-1).
Security is treated as a product-trust issue, not just a technical one.

- **No secrets in source control.** `.env` files are gitignored (already the case). API keys, tokens, and
  credentials are never committed, logged, or hardcoded — including in test fixtures.
- **The analysis-vs-advice boundary is a security-relevant product constraint**, not just marketing copy
  — see [PRODUCT.md](PRODUCT.md#the-analysis-vs-advice-boundary). Code review should flag anything that
  moves the product from contextual to directive.
- **Known current gaps** (acceptable for a single-developer local prototype, not beyond it) are tracked
  explicitly in [ARCHITECTURE.md](ARCHITECTURE.md#known-gaps-phase-1-prototype--tracked-not-yet-urgent):
  no auth, open CORS, no secrets management pattern yet. Do not let these silently persist into a
  multi-user or public deployment — closing them is a prerequisite, not a nice-to-have.
- **Dependencies**: keep `requirements.txt` / `package.json` lean; review new dependencies for
  maintenance status before adding them. Dependency and security-sensitive changes always get explicit
  human confirmation — see [CLAUDE.md](../CLAUDE.md).
- **User data**: memory content is sensitive by nature (it encodes financial behavior and preferences).
  Treat it accordingly in logging — never log full memory content at info level or above.

## Testing expectations

Two different bars apply, split by codebase — see
[ADR-018](DECISIONS.md#adr-018-stricter-per-layer-testing-bar-adopted-for-the-logan_core-pipeline).

**Inside `logan_core/`** (the Logan Intelligence System pipeline): the stricter bar applies, because
18 independently-owned, contract-bound layers are only maintainable if each is independently verified.
- Unit tests for every layer's core logic (e.g. `trust_score`/`priority_score` formulas, classification
  thresholds, dedup/entity-extraction rules, Policy language-enforcement rules).
- Contract validation tests for every typed object — schema, required fields, value constraints.
- Pipeline integration tests — the Tesla scenario end-to-end, and the feedback-loop scenario (see
  [docs/specs/LOGAN_IMPLEMENTATION_PLAN.md](specs/LOGAN_IMPLEMENTATION_PLAN.md)).
- A regression suite that runs before any contract/schema change ships.

**Everywhere else** (`mobile/`, the historical `backend/`): the original pragmatic bar from
[ADR-005](DECISIONS.md#adr-005-pragmatic-testing-bar-during-mvppre-launch) continues to apply — tests
required for the highest-risk logic, no blanket coverage percentage target, manual verification
acceptable for UI during active product exploration.

- **Test tooling**: `pytest` for both `backend/` and `logan_core/`. **Mobile test tooling**: not yet
  established — decide when mobile logic grows beyond thin presentation components; record the choice as
  an ADR.
- Revisit the `logan_core` bar as the architecture stabilizes; revisit the pragmatic bar before public
  launch, per ADR-005.

## Documentation standards

- **`docs/specs/` is locked architecture, not living documentation.** The Logan Intelligence System specs
  there are treated as source of truth per their own ground rules — don't edit an interface or contract
  casually. If implementation reveals a genuine issue, document the rationale as a new ADR in
  [DECISIONS.md](DECISIONS.md) *before* changing the spec, per the same discipline the original package
  required.
- **This `docs/` set (outside `docs/specs/`) is living documentation.** If a decision changes, update the relevant doc *and* add
  an ADR to [DECISIONS.md](DECISIONS.md) — don't let docs silently drift from reality.
- **Every non-trivial decision gets an ADR**, added at decision time, not retroactively reconstructed.
  See the template in [DECISIONS.md](DECISIONS.md#how-to-add-a-decision).
- **Code comments** explain *why*, not *what* — if a comment just restates the code, delete it. Reserve
  comments for non-obvious constraints, workarounds, or invariants.
- **README.md** stays a fast path to running the app locally — deeper context belongs in `docs/`, linked
  from the README, not duplicated into it.
- **PR descriptions** should state what changed and why, and link the relevant ADR if the change
  reflects or requires one.
