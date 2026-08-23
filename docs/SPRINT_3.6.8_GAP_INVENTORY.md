# Sprint 3.6.8 Gap Inventory

**Purpose:** a structured, categorized inventory of known implementation gaps as of Sprint 3.6.8's close
(Blocks 1–5), compiled to feed the formal post-3.6.8 code/architecture/product gap analysis. This document
does not propose or begin a new sprint — it is a snapshot of what is currently true, organized so the gap
analysis can prioritize from it directly.

**As of:** 2026-08-23, branch `feat/sprint-3.6.7-stock-signal-expansion`, HEAD after Block 5's local commit.
See `docs/DECISIONS.md` ADR-056 through ADR-060 for the full decision record behind every item below, and
`docs/specs/Logan_Documentation_v3.1.4/23_CURRENT_IMPLEMENTATION_STATE.md` for verified current-state detail.

Each item: **current state** · **why it matters** · **blocker vs. non-blocker** (for a controlled family/
beta test specifically, not public launch) · **suggested next action** · **owner decision required?**

---

## A. LIVE DATA

1. **Only NVDA/TSLA/AAPL have any live-provider path; 8 of 11 production entities remain simulated-only.**
   Current state: `_run_feed_pipeline()` runs `simulated_fixtures()` by default; NVDA/TSLA/AAPL can go live
   via FMP when configured (`STRATUS_LIVE_STOCK_TICKERS`). BTC/FED/NFL/MUSIC/POLY/AI_SECTOR have zero
   provider integration; MARKETS/OIL have no clear single-instrument mapping. Why it matters: this is the
   single largest gap between the current app and a genuinely live-data product. Blocker: **yes**, for any
   beta explicitly framed as "live." Next action: owner selects (or declines) a vendor per domain; a
   separate product decision names what MARKETS/OIL should each track. Owner decision required: **yes**, per
   domain (new external vendor each).

2. **`STOCK_EARNINGS_MISS`/`STOCK_EARNINGS_IN_LINE` do not yet trigger live substitution.** Current state:
   only `STOCK_EARNINGS_BEAT` replaces a ticker's simulated fixture; both MISS/IN_LINE are real, registered
   triggers (ADR-045) that simply aren't checked in `_live_earnings_raw_signal`'s pre-check. Live-verified as
   a real, current gap — TSLA's actual most recent earnings report is a miss (Block 5 live verification,
   2026-08-23). Blocker: no. Next action: extend the pre-check to also substitute on MISS (and decide whether
   IN_LINE, at `confidence_contribution=0.0`, is worth substituting at all). Owner decision required: no —
   parameterization of an existing, already-approved condition, not a new threshold.

3. **Price-move/analyst-grade-only live opportunities are not currently possible.** Current state: a live
   price-move or analyst-grade signal is only attached when that ticker's earnings *also* went live the same
   poll (Block 5's own fully-live-or-fully-simulated fix). Why it matters: a ticker with a real, qualifying
   price move but no earnings event that day never surfaces live. Blocker: no. Next action: a deliberate
   design decision about whether/how to let a non-earnings live signal become a ticker's own primary
   opportunity. Owner decision required: recommended — this changes what "a live opportunity" can be
   composed of.

4. **`STRATUS_RUNTIME_MODE` (live-data-only mode) is not wired into any real deployment.** Current state:
   the mechanism exists and is tested, but nothing sets it outside test fixtures. Blocker: no (it's inert
   until used). Next action: decide when/whether a real beta deployment sets it. Owner decision required: no,
   mechanical once a hosting/deployment decision (below) is made.

---

## B. BETA/DEPLOYMENT

1. **`eas.json` has no `EXPO_PUBLIC_API_BASE_URL` for any build profile.** Current state: a real
   `preview`/`production` EAS build today would ship with a stale, unreachable local dev IP baked in
   (Block 4 finding). Blocker: **yes**, for any real device build reaching real testers. Next action: set
   the env var once a real backend host exists. Owner decision required: blocked on item B.2 below.

2. **No hosting/deployment decision exists (ADR-006 remains open).** Current state: the backend runs only as
   a local process the operator controls; SQLite, not a hosted database. Blocker: **yes** for any beta
   involving a device that isn't on the operator's own network. Next action: owner picks a hosting target.
   Owner decision required: **yes**.

3. **No Apple Developer/signing/push-credential setup performed.** Current state: `eas.json` has build
   profiles configured but no signing has been attempted (deliberately, per this sprint's own stop
   conditions). Blocker: **yes** for TestFlight specifically. Next action: owner performs Apple Developer
   account setup and `eas credentials`. Owner decision required: **yes** (irreversible external action, not
   attempted).

4. **Advisory-only disclaimer copy specified but not shipped to any mobile screen.** Current state:
   `27_SECURITY_PRIVACY_COMPLIANCE.md` already specifies the required copy; no Opportunity Card or onboarding
   flow displays it. Blocker: **yes**, required before any non-operator sees the app per that document's own
   stated policy. Next action: implement the disclaimer UI. Owner decision required: no — copy is already
   approved, this is implementation.

---

## C. MOBILE/UX

1. **No client-side per-device identity persistence.** Current state: the mobile app never sends
   `X-Stratus-User-Id`; every real request still resolves to the founder default (ADR-057). Why it matters:
   real multi-tester isolation (Block 2's own guarantee) can't be exercised by real devices until this
   exists. Blocker: **yes**, for a beta with more than one real tester. Next action: add a persisted
   per-device identifier. Owner decision required: **yes** — requires a new client-side storage dependency
   (e.g. `expo-secure-store`), itself a dependency-addition decision.

2. **No visual distinction between an LLM-composed and a deterministic Ask STRATUS answer.** Current state:
   `GroundedAnswer.used_llm`/`llm_model` stay internal, never reach `AskResponse`. Blocker: no. Next action:
   decide if/how to surface this (e.g. a subtle badge). Owner decision required: recommended (product/UX
   call, not just implementation).

3. **`22_OPPORTUNITY_CARD_SPEC.md`'s full card spec remains only partially built.** Current state, carried
   forward from earlier sprints, unchanged by 3.6.8: the consolidated `OpportunityCard` doesn't implement
   every field/section the full spec describes. Blocker: no for a controlled beta. Next action: gap-analysis
   candidate. Owner decision required: no immediate action needed.

---

## D. SECURITY/AUTH

1. **No authentication of any kind exists.** Current state: `X-Stratus-User-Id` is entirely client-asserted
   and unverified (ADR-057/059's own precise correction to `27_SECURITY_PRIVACY_COMPLIANCE.md`). Why it
   matters: the real, tested state isolation Block 2 built protects honest/cooperating identities from each
   other — it is not a security boundary against an adversarial caller. Blocker: **yes** for any beta beyond
   the operator and fully-trusted testers on a private network. Next action: this is `27_SECURITY_
   PRIVACY_COMPLIANCE.md`'s own "REQUIRED — TRUSTED ALPHA" auth section, entirely unbuilt. Owner decision
   required: **yes** — authentication architecture is explicitly named as a stop condition in every block of
   this sprint.

2. **No encryption in transit or at rest beyond OS-level file permissions.** Current state: local HTTP, no
   TLS; SQLite file has no database- or application-layer encryption. Blocker: **yes**, once networked (item
   B.2). Non-blocker while the backend stays on `localhost`. Next action: part of the hosting decision.
   Owner decision required: **yes** (bundled with B.2).

3. **No secrets manager; `FMP_API_KEY`/future `ANTHROPIC_API_KEY` live only in local `.env`.** Current state:
   fine for local-dev-only operation (never committed, per this codebase's own enforced hygiene). Blocker:
   no at current scale; yes for any real hosted deployment. Next action: part of the hosting decision. Owner
   decision required: **yes** (bundled with B.2).

---

## E. STATE/PERSISTENCE

1. **`PrioritizationEngine`'s `AttentionState` (Watch fatigue/cooldown/notification-review) is never
   persisted, regardless of `STRATUS_PERSIST_MEMORY`.** Current state: documented and tested as an explicit,
   intentional restart-safety boundary (Block 4's own restart-safety matrix). Blocker: no. Next action: none
   required; flag as a candidate if durable Watch state across restarts becomes a real product requirement.
   Owner decision required: no, unless the desired behavior changes.

2. **`_user_models`/`_opportunity_context_caches` grow unbounded across every distinct `user_id` the process
   has ever seen.** Current state: no eviction, unlike `_ask_sessions`'s own bounded cap (Block 4 finding).
   Blocker: no at controlled-beta scale (a handful of known testers). Next action: add bounded eviction only
   if/when real multi-tester scale makes it a real memory concern. Owner decision required: no.

3. **Ask STRATUS conversation history is never persisted, by design (ADR-055/058).** Current state:
   deliberate — session continuity is short-lived UI convenience, not durable preference data. Blocker: no.
   Next action: none; revisit only if the product wants conversations to survive a restart. Owner decision
   required: no, unless the desired behavior changes.

4. **Push token registration and dispatch/review state are never persisted.** Current state: in-memory only,
   resets on every restart. Blocker: no at current scale (Block 4 finding, unrelated to isolation
   correctness — tokens simply need re-registering after a restart). Next action: durable token storage if
   real multi-device beta testing makes frequent backend restarts disruptive. Owner decision required:
   recommended when relevant, an ADR-006-scale decision.

---

## F. PERFORMANCE/SCALING

1. **One process-wide `_state_lock` serializes every user's pipeline run.** Current state: correct, not a
   regression — coarse-grained by design at current scale. Blocker: no. Next action: revisit only if real
   concurrent-user load becomes a measured problem. Owner decision required: no.

2. **The notification poller now runs a full pipeline once per registered user, per cycle.** Current state:
   a real, necessary consequence of per-user personalized alert eligibility (Block 2), now correctly
   offloaded to a thread so it no longer blocks the event loop (Block 4 fix), but cost still scales linearly
   with registered-user count. Blocker: no at current/controlled-beta scale. Next action: revisit if
   registered-user count grows meaningfully. Owner decision required: no.

3. **Live-data-only mode with multiple configured tickers means multiple sequential, bounded (10s each) FMP
   calls per poll.** Current state: each call is independently timeout-bounded and thread-offloaded, but
   wall-clock latency per poll grows with the number of live tickers. Blocker: no at NVDA/TSLA/AAPL scale.
   Next action: consider parallelizing live fetches if the live ticker list grows substantially. Owner
   decision required: no.

---

## G. PRODUCT LOGIC

1. **`DomainPref.weight` remains a required-but-unread contract field with no consumer anywhere in the
   pipeline** (ADR-057 finding, unresolved). Current state: inert, documented as such at both construction
   sites. Blocker: no. Next action: either give it a real meaning (a per-domain weighting design) or make
   the field genuinely optional (a contract change). Owner decision required: recommended, not urgent.

2. **MARKETS/OIL entities represent aggregate/commodity concepts with no defined real-instrument mapping.**
   Current state: simulated only; going live requires a product decision about what each should actually
   track. Blocker: no (they're not currently claimed as live-capable). Next action: see A.1. Owner decision
   required: **yes**, product-level (what does "MARKETS"/"OIL" mean as a trackable real instrument?).

3. **What composes "a live opportunity" is currently earnings-anchored only** (see A.3). Current state: a
   deliberate, narrower behavior chosen during Block 5's bug fix, not the only possible design. Blocker: no.
   Next action: revisit if/when non-earnings-anchored live opportunities are wanted. Owner decision required:
   recommended.

---

## H. TECHNICAL DEBT

1. **A pre-existing `**dict[str, object]` mypy pattern spans 4 Ask STRATUS test fixture helper functions**
   (`test_ask_engine.py`, `test_ask_route.py`, `test_ask_llm.py`, `test_ask_conversation.py`) — cosmetic
   typing noise from `**overrides` dict-unpacking, not a runtime bug, flagged repeatedly since Block 1 and
   never fixed. Blocker: no. Next action: a small typed builder function instead of dict-unpacking. Owner
   decision required: no.

2. **`27_SECURITY_PRIVACY_COMPLIANCE.md`'s large body of target-design sections remain entirely unbuilt** —
   encryption, the full JWT auth design, GDPR/CCPA data-subject rights, gambling-compliance controls. All
   already well-documented as FUTURE/REQUIRED-TRUSTED-ALPHA, not new findings from this sprint, but real,
   substantial, and load-bearing for anything beyond the current controlled scope. Blocker: mixed (see
   sections D and B above for the pieces that are). Next action: the gap analysis this document feeds. Owner
   decision required: **yes**, multiple (auth architecture, encryption/hosting, legal review timing).

3. **The historical `backend/app/` prototype (`memory_engine.py`, `logan_memory.db`) remains untouched,
   parallel infrastructure alongside `logan_core`.** Current state: unchanged since ADR-014/017, still
   backing the legacy `/v1/memories`/`/v1/briefing` routes and the generic (no-context) Ask STRATUS fallback.
   Blocker: no. Next action: gap-analysis candidate for eventual consolidation or formal deprecation. Owner
   decision required: no immediate action needed.
