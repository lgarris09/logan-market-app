# Logan Intelligence — Trending Engagement Specification
**Version:** 3.1.3
*Source: Architecture v1.3 FINAL (2026-07-31). Original: “source_material/21_TRENDING_ENGAGEMENT.md” (historical label).*

---

## What Trending Engagement Is

Trending Engagement measures **community momentum** — the collective behavior of people paying attention to an entity — distinct from Logan's personal relevance scoring.

Trending ≠ Important. An entity can be trending heavily (high community engagement) while being low personal relevance to a specific user. Logan keeps these separate.

Trending ≠ Signal. Trending is an input, not a conclusion. High trending without supporting evidence is noise. High trending with confirming evidence is a signal amplifier.

**LOCKED:** Community momentum maps to node edge glow only in the Opportunity Field. It does not map to node brightness, size, or proximity to center. Those visual properties encode Logan's independent assessment of opportunity quality and personal relevance. (See DECISION-016 and `11_UI_PHILOSOPHY.md`.)

---

## The Two Axes

```
                    HIGH PERSONAL RELEVANCE
                           │
          3                │              1
   Trending but not        │       Trending AND relevant
   relevant to you         │       → surface (amplified)
                           │
 LOW ───────────────────────┼────────────────────────── HIGH
 TRENDING                  │                        TRENDING
                           │
          4                │              2
   Neither trending        │       Relevant but not trending
   nor relevant            │       → surface normally
                           │
                    LOW PERSONAL RELEVANCE
```

- **Quadrant 1:** Surface at the score `hit_quality_score`/`user_value_score` already produce. Logan notes the momentum as context — momentum does not amplify, adjust, or otherwise touch the score itself (see "Trending as Context, Not Amplifier" below; ADR-034).
- **Quadrant 2:** Surface at normal confidence (trending is not required for surfacing).
- **Quadrant 3:** Do not surface. Note the trend in "Why Not" if user queries.
- **Quadrant 4:** Neither trending nor relevant. Silent monitoring only.

---

## CommunitySignal Object

```json
{
  "entity_id": "string",
  "schema_version": "1.0",
  "engagement_metrics": {
    "volume_30min": 847,
    "volume_24h": 12400,
    "velocity": 3.2,
    "unique_participants": 203,
    "volume_vs_baseline": 4.1
  },
  "lifecycle_state": "building",
  "lifecycle_states": ["nascent", "building", "peak", "dispersing", "dissipated"],
  "quality_flags": {
    "bot_risk": 0.12,
    "coordination_risk": 0.04,
    "sentiment_uniformity": 0.31
  },
  "momentum_score": 0.73,
  "execution_metrics": {},
  "decision_trace": []
}
```

**Note on field name:** The community output field is `momentum_score` (not `trending_score`). The term `momentum_score` aligns with the LOCKED visual rule — it maps to edge glow, which communicates momentum, not personal relevance or conviction.

---

## Momentum Score Calculation

```
momentum_score = (
  volume_vs_baseline  × 0.35   # how much above normal baseline?
  + velocity          × 0.30   # is it accelerating?
  + lifecycle_weight  × 0.20   # building = 1.0, peak = 0.7, dispersing = 0.3
  + unique_ratio      × 0.15   # unique_participants / volume (broad vs. narrow)
) × quality_multiplier

quality_multiplier:
  if bot_risk > 0.50:           × 0.20  (heavy penalty)
  elif bot_risk > 0.25:         × 0.60
  elif coordination_risk > 0.3: × 0.50
  else:                         × 1.0
```

---

## Trending as Context, Not Amplifier

**Amended in v3.1.3 — removed, not replaced.** Through v3.1.2, this section defined a mechanism that multiplied `priority_score` by up to 1.30× when `momentum_score` and `user_value_score` were both high. Per `docs/DECISIONS.md` ADR-034 (clarifying DECISION-016), this mechanism is **confirmed non-compliant** and is removed from this package. It is not silently replaced with another scoring influence — no substitute amplification, multiplier, or bonus of any kind is introduced in its place.

The rule going forward: when an entity is in Trending Quadrant 1 (high momentum AND high personal relevance), Logan surfaces it at exactly the score `hit_quality_score` and `user_value_score` already produce from evidence and personalization alone. `momentum_score` may be shown to the user as context (e.g. a badge, per the UI Contract below) and may inform presentation/format choices, but it never multiplies, adds to, gates, or otherwise numerically influences `hit_quality_score`, `user_value_score`, `priority_score` (itself deprecated per ADR-029), Opportunity confidence, urgency, or recommendation direction — directly or indirectly, at any coefficient.

This also applies to any future population-level learning capability (see `ML_PRIVACY_AND_DATA_SEPARATION.md`): aggregated *accuracy* may inform trust/weight registries; aggregated *popularity* (of which `momentum_score` is an instance) never may.

---

## Lifecycle State Descriptions

| State | Description | Signal Interpretation |
|---|---|---|
| **nascent** | First early signals, below baseline | Too early — monitor only |
| **building** | Accelerating above baseline | Active signal — weight at full |
| **peak** | Maximum engagement | High signal value, but watch for reversal |
| **dispersing** | Engagement falling from peak | Fading — weight reduced |
| **dissipated** | Back to or below baseline | Signal effectively gone |

Logan weights building > peak > dispersing for opportunity surfacing. "Building" indicates something is happening now. "Dispersing" may indicate the opportunity has already played out.

---

## What Trending Does NOT Do

- **Trending alone never surfaces an opportunity.** Community engagement is an input to the signal pipeline, not a shortcut past it.
- **Peak trending is not the right time to surface.** Peak sentiment often precedes reversals. Logan notes lifecycle state explicitly in the reasoning chain.
- **Trending does not override user value.** A hot trending entity in a domain the user doesn't care about stays suppressed.
- **Trending does not control node brightness or proximity.** Community momentum → edge glow only. LOCKED.

---

## "Why Not" — Trending-Related Suppressions

When an entity is trending heavily but suppressed:

```
"NVDA is trending strongly today (4.1× baseline volume, building phase),
but it does not match your watched domains / position history.
You can add Stocks to your watched domains in Settings."
```

When trending quality flags caused suppression:

```
"High social engagement detected on [entity], but the engagement
pattern shows coordination risk (0.67). Logan is treating this
as low-quality trending signal. Watching for organic confirmation."
```

---

*Logan Intelligence Trending Engagement Specification — v3.1.3 | 2026-08-04*
*v3.1.2 changes: LOCKED rule added: community momentum → edge glow only. Field renamed trending_score → momentum_score to align with visual specification. Note added clarifying momentum_score vs. confidence mapping in the UI. "Trending does not control brightness or proximity" added to What Trending Does NOT Do section.*
*v3.1.3 changes: "Trending as Signal Amplifier" section removed per ADR-034 — the `momentum_score`→`priority_score` multiplication was a live, confirmed violation of this document's own LOCKED rule. Not replaced with a substitute mechanism. Quadrant 1 description corrected to match.*


---
## v3.1.2 UI Contract

Trending may appear as a node badge, card badge, or dedicated surface. It must be visually distinct from personal relevance, confidence, and evidence quality. Document privacy thresholds, suspicious-manipulation warnings, numeric-count policy, color-independent cues, screen-reader text, and reduced-motion behavior. Trending may affect a dedicated momentum cue but may not silently increase recommendation quality.
