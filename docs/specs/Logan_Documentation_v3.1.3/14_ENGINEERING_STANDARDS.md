# Logan Intelligence — Engineering Standards
**Version:** 3.1.3
*Source: Architecture v1.3 FINAL (2026-07-31). Original: “source_material/14_ENGINEERING_STANDARDS.md” (historical label).*
**TriggerEvent status:** the `trigger_registry/` module, `TriggerEvent` data contract class, and TriggerEvent-specific tests referenced below are SPECIFIED — NOT IMPLEMENTED (V3.1.4 BATCH-3, OD-009). None of these exist in `logan_core/` as of V3.1.4.

---

## Philosophy

Logan's engineering standards exist for one reason: the intelligence pipeline is complex. Without standards, complexity accumulates as technical debt that eventually makes the system slower to reason about, harder to debug, and dangerous to change.

**Every standard in this document traces back to a real risk:**
- Schema consistency → prevents silent data corruption across layers
- Stateless layers → makes the pipeline testable and debuggable in isolation
- Single writer to memory → prevents race conditions and hidden state mutation
- Explicit uncertainty → prevents false confidence from propagating downstream
- TriggerEvent registry enforcement → prevents undefined trigger codes from entering the pipeline

Standards are not bureaucracy. They are the lessons from building complex systems, applied before the mistakes happen.

---

## Language and Runtime

| Component | Technology | Status |
|---|---|---|
| Backend / Brain | Python 3.11+ | PROVISIONAL |
| Mobile | React Native (TypeScript) | PROVISIONAL |
| API | FastAPI | PROVISIONAL |
| Database | PostgreSQL | PROVISIONAL |
| Cache | Redis | PROVISIONAL |
| Testing | pytest (backend), Jest + React Testing Library (mobile) | PROVISIONAL |

All stack choices are working assumptions. See `15_DECISIONS.md` for locked vs. provisional decisions.

---

## Folder Structure

### Backend
```
logan/
├── api/
│   ├── routes/          # FastAPI route handlers
│   ├── models/          # Pydantic request/response models
│   └── middleware/      # Auth, rate limiting, logging
├── brain/
│   ├── orchestrator.py  # Pipeline orchestrator — no business logic
│   ├── layers/          # One file per layer
│   │   ├── receptors/
│   │   │   ├── stocks.py
│   │   │   ├── sports.py
│   │   │   ├── prediction_markets.py
│   │   │   ├── social_trends.py
│   │   │   ├── crypto.py
│   │   │   ├── culture.py
│   │   │   └── personal_finance.py
│   │   ├── normalization.py
│   │   ├── world_model.py
│   │   ├── evidence_trust.py
│   │   ├── community_intelligence.py
│   │   ├── hit_detection/
│   │   │   ├── convergence.py
│   │   │   ├── divergence.py
│   │   │   ├── pattern_engine.py
│   │   │   └── odse.py
│   │   ├── domain_analysis.py
│   │   ├── reasoning.py
│   │   ├── hypothesis.py
│   │   ├── mental_model.py
│   │   ├── conclusion_confidence.py
│   │   ├── opportunity_engine.py
│   │   ├── lifecycle.py
│   │   ├── decay.py
│   │   ├── policy.py
│   │   ├── prioritization.py
│   │   └── presentation.py
│   ├── contracts/       # All data contract schemas (Pydantic)
│   └── trigger_registry/  # TriggerEvent code registry + validation
├── memory/
│   ├── store.py         # Memory System read interface
│   ├── learning.py      # Learning System — sole writer
│   └── branches/        # One module per memory branch
├── integrations/
│   ├── stocks/
│   ├── sports/
│   ├── predictions/
│   ├── crypto/
│   ├── culture/
│   ├── personal_finance/
│   ├── news/
│   └── linked_accounts/ # Plaid, OAuth connectors
├── analytics/
├── tests/
│   ├── unit/            # Per-layer tests
│   ├── integration/     # Pipeline integration tests
│   └── fixtures/        # Simulated signal sets
└── config/
```

### Mobile
```
mobile/
├── app/                 # Expo Router screens
│   ├── (tabs)/
│   │   ├── index.tsx    # Opportunity Field
│   │   ├── portfolio.tsx
│   │   └── read-suggest/
│   └── opportunity/[id].tsx
├── components/
│   ├── field/           # Opportunity Field Skia components
│   ├── cards/           # Detail cards, opportunity cards
│   └── shared/          # Reusable UI components
├── stores/              # Zustand state stores
├── hooks/               # Custom React hooks
├── api/                 # API client (React Query)
├── constants/           # Design tokens, config
└── types/               # TypeScript types
```

---

## Naming Conventions

### Python (backend)
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `SCREAMING_SNAKE_CASE`
- Layer classes: Named for their layer (e.g., `ReasoningEngine`, `HypothesisEngine`)
- Data contract classes: Match contract names exactly (e.g., `OpportunityEvidence`, `DomainAnalysis`, `TriggerEvent`)
- TriggerEvent codes: `SCREAMING_SNAKE_CASE` (e.g., `STOCK_EARNINGS_BEAT`, `SPORTS_LINE_MOVE`)

### TypeScript (mobile)
- Files: `PascalCase.tsx` for components, `camelCase.ts` for utilities
- Components: `PascalCase`
- Functions/hooks: `camelCase`, hooks prefixed with `use`
- Constants: `SCREAMING_SNAKE_CASE`
- Types/interfaces: `PascalCase`, interfaces prefixed with `I` only when needed for disambiguation

### Database
- Tables: `snake_case`, plural (e.g., `memory_records`, `user_models`, `trigger_events`)
- Columns: `snake_case`
- Indexes: `idx_{table}_{column}`
- Foreign keys: `fk_{table}_{referenced_table}`

---

## Data Contracts

**Every object that crosses a layer boundary is defined in `07_DATA_CONTRACTS.md`.**

Rules:
- All contract objects include `schema_version: "1.0"`
- Validation is enforced on input — objects with missing required fields are rejected, not silently passed
- Unknown optional fields are tolerated (forward compatibility)
- Schema bumps require a review — minor for additive changes, major for breaking changes

In Python: use Pydantic models for all contract objects. Pydantic validators enforce required fields.
In TypeScript: use TypeScript interfaces with strict null checks enabled.

---

## TriggerEvent Registry

All TriggerEvent codes must be registered before use.

Rules:
- No unregistered trigger code may enter the pipeline. Any code not in `TRIGGER_REGISTRY_GLOBAL.md` is rejected at reception.
- Registries are authoritative: `TRIGGER_REGISTRY_STOCKS.md`, `TRIGGER_REGISTRY_SPORTS.md`, `TRIGGER_REGISTRY_PREDICTION_MARKETS.md`, `TRIGGER_REGISTRY_CRYPTO.md`, `TRIGGER_REGISTRY_CULTURE.md`, `TRIGGER_REGISTRY_PERSONAL_FINANCE.md`
- Adding a new trigger code requires adding it to the domain registry AND `TRIGGER_REGISTRY_GLOBAL.md`
- ML-based trigger code discovery is deferred to V2 — V1 uses manual registry only
- Trigger code scoring adjustments are in `TRIGGER_SCORING_AND_CONFLICT_RULES.md`

---

## Layer Rules

These rules apply to every layer in the pipeline without exception:

1. **Stateless** — no layer maintains internal state between pipeline runs, except the Memory System
2. **Single responsibility** — each layer does exactly one thing (see `06_LAYER_INTERFACE_SPECIFICATION.md`)
3. **No direct layer-to-layer calls** — all communication goes through the Orchestrator
4. **ExecutionMetrics on every output** — every layer emits timing, success, and warning data
5. **decision_trace on every output** — every layer may append reasoning entries
6. **Memory write forbidden** — all layers except Learning System are read-only to memory (enforced at infrastructure level)
7. **No business logic in Orchestrator** — Orchestrator wires and sequences; layers decide
8. **Community Intelligence visual rule** — Community Intelligence output `momentum_score` maps to node edge glow only. No layer may route it to brightness or proximity. (LOCKED — see `11_UI_PHILOSOPHY.md`)

---

## Testing Requirements

### Unit tests
- Every layer has unit tests
- Tests use simulated signal sets from `tests/fixtures/`
- Minimum coverage: 80% line coverage per layer
- All Phase Gates from `08_BUILD_ORDER.md` have corresponding test assertions
- TriggerEvent: test that unregistered codes are rejected at layer 1

### Integration tests
- Full pipeline end-to-end with 11+ simulated entities
- Phase gates verified as integration tests, not just manually
- Memory write authorization tested — unauthorized writes must fail
- Vertical slice test: single STOCK_EARNINGS_BEAT trigger through full pipeline to FeedbackSignal

### Contract tests
- Every data contract object has a schema validation test
- Tests verify that required fields are rejected when missing
- Tests verify that unknown optional fields are tolerated
- TriggerEvent schema validated end-to-end

### Performance tests
- Memory read latency tested against targets in `03_MEMORY_ARCHITECTURE.md`
- Pipeline end-to-end latency benchmarked per phase

---

## Versioning

**Semantic versioning:** `MAJOR.MINOR.PATCH`
- MAJOR: Breaking architecture change (requires full review)
- MINOR: New feature, non-breaking
- PATCH: Bug fix, performance improvement

**Schema versioning:** `schema_version` field on all contract objects
- `"1.0"` is current
- Minor bumps: additive only — new optional fields
- Major bumps: breaking changes — require migration path

**API versioning:** All endpoints under `/v1/` prefix. Breaking changes introduce `/v2/` alongside, with deprecation notice on `/v1/`.

---

## Performance Targets

| Operation | Target |
|---|---|
| Opportunity Field endpoint | < 200ms p95 |
| User Model read | < 10ms |
| Full pipeline run (cold) | < 5s |
| Full pipeline run (hot, cached) | < 1s |
| WebSocket push latency | < 100ms |
| Memory write (Learning System) | < 500ms |

---

## Error Handling

- **Transient failures:** Retry up to 3 times with exponential backoff
- **Layer timeout:** Skip layer, flag in ExecutionTrace, continue pipeline — don't halt
- **Critical failure:** Halt pipeline, emit alert, log full trace
- **Missing data:** Explicit "data unavailable" signal — never silent
- **Validation failure:** Reject at boundary with clear error, log, never pass corrupted data downstream
- **Unregistered TriggerEvent code:** Reject at reception layer, log, never enter pipeline

---

## Documentation Standards

- Every public function/class has a docstring
- Complex business logic gets inline comments explaining *why*, not *what*
- Architecture decisions go in `15_DECISIONS.md`, not in code comments
- Data contracts are the source of truth — code must match contracts, not the other way around
- Decision status labels in docs: **LOCKED** / **PROVISIONAL** / **RESEARCH REQUIRED** / **DEFERRED**

---

## Git Workflow

- **Branch naming:** `feature/description`, `fix/description`, `refactor/description`
- **Commit messages:** Imperative mood, present tense ("Add hypothesis confidence tracking")
- **PR size:** Keep PRs focused — prefer small, reviewable changes over large batch commits
- **Phase gates:** Each phase gate from `08_BUILD_ORDER.md` gets its own PR and review
- **Vertical slice:** Sprint 2A vertical slice is its own PR — must pass all gate criteria before Phase 1 broad work begins

---

*Logan Intelligence Engineering Standards — v3.1.2 | 2026-08-03*
*v3.1.2 changes: TriggerEvent registry section added. Folder structure expanded: culture, personal_finance receptors, trigger_registry module. TriggerEvent code naming convention added. TriggerEvent contract and registry tests added to testing requirements. Community Intelligence visual rule added to layer rules. Decision status label standard added. Vertical slice PR process added to git workflow. Technology stack status column added (PROVISIONAL).*
