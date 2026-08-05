# Logan Intelligence — Entity Resolution
**Version:** 3.1.3
*New in v3.1.2. No prior version.*

---

## Purpose

Entity resolution ensures that when the same real-world entity appears in signals from multiple domains or data sources, Logan correctly recognizes it as the same entity — and builds a unified World Model entry for it.

Without entity resolution, NVIDIA appearing in a stock data feed and a prediction market contract would be treated as two separate entities, preventing cross-domain convergence from ever firing.

---

## What an Entity Is

An entity is a real-world subject that Logan tracks. Entities have:
- A stable `entity_id` (assigned by Logan's World Model at first recognition)
- A canonical `entity_name`
- A primary `domain` (the domain where the entity was first or most commonly seen)
- Optional `domain_aliases` — how this entity appears in other domains

---

## Entity ID Assignment

Entities are assigned a unique `entity_id` at World Model creation:

```
entity_{type}_{slug}

Examples:
  entity_stock_nvda
  entity_athlete_mahomes_patrick
  entity_artist_taylor_swift
  entity_contract_nvda_above_120_aug26
  entity_macro_fed_rate_decision_sept26
```

**Type prefixes:**

| Type | Prefix | Description |
|------|--------|-------------|
| Stock / public company | `stock` | Equities, ETFs |
| Sports team | `team` | Any sports franchise |
| Athlete / public figure (sports) | `athlete` | Individual sports persons |
| Prediction market contract | `contract` | Specific contract instance |
| Artist / creator (culture) | `artist` | Music, film, gaming creators |
| Track / album (culture) | `content` | Specific media content |
| Macro event | `macro` | Scheduled economic events |
| Generic entity | `entity` | Catch-all for uncategorized |

---

## Cross-Domain Resolution Rules

The same real-world entity often appears differently in different domains. The entity resolver must normalize these into the same `entity_id`.

### Rule 1: Ticker → Company Name Resolution

Stock ticker symbols and company names must resolve to the same entity.

```
"NVDA" → entity_stock_nvda
"NVIDIA" → entity_stock_nvda
"Nvidia Corporation" → entity_stock_nvda
"$NVDA" (Reddit social) → entity_stock_nvda
```

**Implementation:** Canonical ticker-to-name mapping loaded at startup. Fuzzy match allowed for social signals (with confidence threshold ≥ 0.85).

### Rule 2: Prediction Market Contract → Underlying Entity

A prediction market contract about an asset must be linked to the underlying entity.

```
"NVDA above $120 by Aug 31" → underlying: entity_stock_nvda
"Will the Fed cut rates in September?" → underlying: entity_macro_fed_rate_decision_sept26
"Chiefs to win Super Bowl" → underlying: entity_team_chiefs_kc
```

**Contract linkage:** Stored as `underlying_entity_id` on the prediction market entity. Cross-domain detectors use this linkage to fire convergence triggers.

### Rule 3: Sports Cross-Reference

The same team may appear in different sources with different names. All must resolve to the same entity.

```
"Kansas City Chiefs" → entity_team_chiefs_kc
"KC Chiefs" → entity_team_chiefs_kc
"the Chiefs" (in context) → entity_team_chiefs_kc (context-dependent, lower confidence)
"Chiefs" → entity_team_chiefs_kc (only when sports domain context is active)
```

### Rule 4: Artist / Creator Multi-Platform

The same artist may appear on Spotify, YouTube, Apple Music, and social with slight name variations.

```
"Taylor Swift" (Spotify chart) → entity_artist_taylor_swift
"taylorswift" (Instagram handle) → entity_artist_taylor_swift
"Taylor Swift" (YouTube channel) → entity_artist_taylor_swift
```

**Implementation:** Artist canonical registry seeded at startup. Social handle mapping maintained as a lookup table.

### Rule 5: Macroeconomic Events as Entities

Scheduled macro events are pre-registered as entities before they occur.

```
"September FOMC meeting" → entity_macro_fomc_sept26
"September jobs report" → entity_macro_bls_nfp_sept26
"Q3 GDP advance estimate" → entity_macro_gdp_q3_2026_advance
```

**Implementation:** Macro event calendar populated from BLS, BEA, and Federal Reserve release schedules at the start of each quarter.

---

## Confidence Thresholds for Entity Matching

Not all entity matches are certain. The resolver assigns confidence to each match:

| Match Type | Confidence | Action |
|------------|------------|--------|
| Exact canonical name or ticker | 1.00 | Direct match |
| Known alias or handle | 0.95 | Direct match |
| Fuzzy name match (≥ 0.85 similarity) | 0.85–0.94 | Match with flag |
| Contextual inference (domain active) | 0.70–0.84 | Match with low-confidence flag |
| Below 0.70 | < 0.70 | Create new entity (do not merge) |

When a match has confidence < 0.90, the `entity_match_confidence` field is populated on the NormalizedEvent. Detectors may choose to require higher confidence for cross-domain triggers.

---

## New Entity Creation

When the resolver cannot match a signal's subject to any existing entity above confidence threshold, a new entity is created:

1. A new `entity_id` is generated
2. The entity is added to the World Model with `verification_status: "provisional"`
3. The entity is not eligible for cross-domain convergence triggers until it has been confirmed by a second independent signal
4. After 3 signals from independent sources, `verification_status` is updated to `"confirmed"`

---

## Entity Merging

When two entities in the World Model are later determined to be the same real-world entity (e.g., a company announces a rebrand, or a social handle is confirmed to belong to an artist already in the system), they are merged:

1. All signals and TriggerEvents from both entities are reattributed to the surviving `entity_id`
2. The merged entity's `trigger_events` array is the union of both
3. The deprecated entity ID is stored as an alias
4. Opportunity history is preserved under the surviving entity

---

*Logan Intelligence Entity Resolution — v3.1.2 | 2026-08-03*
*New in v3.1.2.*
