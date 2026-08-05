# Logan Intelligence — ML Privacy and Data Separation
**Version:** 3.1.3
*New in v3.1.3. Consolidates the per-user isolation fix (ADR-033) and the population-learning boundary clarification (ADR-034) in one place.*

---

## Per-user data isolation

**Finding this document resolves:** through v3.1.2, `MemoryRecord` had no `user_id` field at all, and the reference implementation's `MemoryStore` was a single global, unpartitioned store. This blocked both personal learning and any privacy-safe population-level aggregation, and the retrofit cost only grows as real data accumulates unpartitioned.

**Decision (ADR-033):** `MemoryRecord` gains a required `user_id` field this release. This is a schema-shape and privacy decision, independent of the storage-backend decision (`docs/DECISIONS.md` ADR-006, still open). It does not require choosing a database or building full multi-tenancy infrastructure — see `MODEL_CONTRACTS.md`'s scoping note and the corresponding code change in `logan_core/contracts/memory.py`.

**Local/founder-only workflow:** the current single-operator local workflow uses an explicit, stable local user identifier for this field rather than an anonymous or empty value. See the implementation log for the exact identifier used.

---

## Population-level learning boundary (DECISION-016, clarified)

**Finding this document resolves:** DECISION-016, as literally worded through v3.1.2, locked only a UI-encoding rule (`momentum_score` maps to node edge glow, never brightness/size/proximity) — it said nothing about the Learning System or aggregated trigger/source accuracy. Separately, `21_TRENDING_ENGAGEMENT.md`'s "Trending as Signal Amplifier" mechanism let `momentum_score` multiply `priority_score` directly by up to 1.30×, a live violation of DECISION-016's own spirit.

**Decision (ADR-034):**

- Privacy-safe population-level learning about **verified accuracy, calibration, and source reliability** may be permitted, computed from aggregated, anonymized outcomes across users. It may inform the Learning System's trust/weight registries (e.g. `source_reliability`) as a supporting prior.
- Popularity, engagement, community momentum, and crowd behavior **may not become evidence** of truth, confidence, urgency, recommendation direction, or personal relevance, for any individual opportunity, under any mechanism — direct or amplified.
- The `momentum_score`→`priority_score` amplification mechanism in `21_TRENDING_ENGAGEMENT.md` is confirmed **non-compliant** and is removed from this package (see the amended file), not silently replaced with another scoring influence.
- The distinction that matters: aggregated *accuracy* (was a trigger/source historically right) is a track-record signal about correctness. Community *momentum* (how much attention something is getting) is a popularity signal about attention. These are structurally different and must never share a code path, a registry, or a scoring term.

**What remains unbuilt:** no cohort/population concept distinct from a single `UserModel` exists yet, and no aggregation mechanism (k-anonymity threshold, algorithm, data flow) is specified — population-level learning stays deferred per ADR-032 pending both the per-user isolation fix above and the ADR-006 database decision.

---

## Account deletion implications

Not implemented this release (no persistence layer exists to delete from — see `docs/specs/09_CURRENT_STATE.md`). Recorded as a requirement for when personal learning or durable storage exists: any per-user learned state must be deletable on account deletion within a bounded window, and the exact retention windows are a `RESEARCH REQUIRED` item, not invented here.

---

*Logan Intelligence ML Privacy and Data Separation — v3.1.3 | 2026-08-04*
*New in v3.1.3.*
