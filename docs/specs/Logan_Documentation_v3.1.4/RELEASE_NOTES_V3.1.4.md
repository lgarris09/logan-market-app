# Logan Intelligence — V3.1.4 Release Notes
**Version:** 3.1.4
**Date:** 2026-08-07
*Reader-facing summary of the V3.1.4 pass. For the complete batch-by-batch implementation record, see
`V3.1.4_IMPLEMENTATION_SUMMARY.md`. For a snapshot of what's built vs. not, see
`23_CURRENT_IMPLEMENTATION_STATE.md`.*

---

## Summary

V3.1.4 fixes two scoring correctness issues that had drifted from their governing ADRs, completes contract
and test coverage across every `logan_core` layer, replaces the demo-only API with a real (if
still-simulated-data) `/v1/opportunities` endpoint, and brings the mobile app's live Attention Field
screen up to a testable standard: reduced motion, accessibility labeling, resilient network handling, a
first test suite, and a subordinate Atmosphere background layer.

No new infrastructure was added. No authentication, database persistence, live data receptors,
notifications, WebSockets, or trained ML were introduced — all remain explicitly out of scope, per the
project's engineering-foundation-first phase.

---

## What changed, by area

**Scoring & policy correctness**
- Removed a scoring-formula drift where Mental Model confidence and community momentum could each
  influence ranking in ways ADR-015/ADR-034 prohibit.
- The internal ranking score is now genuinely internal-only; the public API and mobile app see only an
  ordinal position (`rank`), never a raw score.

**Contracts, tests, and tooling**
- Every `logan_core` layer now has direct unit test coverage (95 tests) plus the existing full-pipeline
  integration test.
- Python (Black/Ruff/mypy) and mobile (ESLint/Prettier) tooling and CI added — this is the project's first
  automated CI pipeline.

**Real API**
- `GET /v1/opportunities` now runs the actual `logan_core` pipeline instead of returning a fixed demo
  fixture. Receptors are still simulated (no live external data source), but the ranking, policy, and
  scoring behind each response are real.

**Mobile app**
- The home screen (Attention Field) now calls the real API, shows distinct loading/empty/timeout/error
  states with a retry action, respects the device's Reduce Motion accessibility setting, and carries
  accessibility labels on its interactive elements.
- A subordinate ambient background layer ("Atmosphere") is now integrated behind the live screen, tuned
  to real feed data and capped for performance.
- This is the project's first mobile automated test suite (19 tests), running in CI.

**Documentation**
- The specified-but-not-yet-built TriggerEvent and Opportunity Lifecycle/Decay systems are now clearly
  labeled as such throughout the documentation package, rather than reading as already-implemented.
- The security/privacy document was rewritten to state plainly what protections exist today (very few —
  this remains single-operator, local-only software) versus what's required before any wider testing or
  release.

---

## What's explicitly not in this release

- No user accounts, authentication, or multi-user support.
- No production database — local SQLite only.
- No live market/sports/news data — all domain receptors are simulated fixtures.
- No push notifications, no WebSocket live updates.
- No trained machine-learning model — confidence and trust scores are deterministic.
- No new product domains (culture, personal finance remain documentation-only).

---

## Known limitations at release

- Real-device mobile performance (frame rate, battery, thermal behavior) has not been measured — this
  environment cannot run a physical device or simulator.
- An Apple-signed iOS development build has not yet been produced — the project configuration is ready,
  but producing the actual signed build requires the project owner's own Apple ID/EAS authentication.
- The mobile app has no persistence for feedback (view/watch/remind/dismiss) — actions are acknowledged in
  the UI but not saved between sessions.

---

*This document accompanies `Logan_Documentation_v3.1.4.zip`. See `28_PACKAGE_MANIFEST.md` for the complete
file index.*
