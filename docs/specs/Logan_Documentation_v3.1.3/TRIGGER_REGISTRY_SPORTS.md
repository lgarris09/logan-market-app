# Logan Intelligence — TriggerEvent Registry: Sports Domain
**Version:** 3.1.3
*New in v3.1.2. No prior version.*
*Authoritative source for all Sports domain trigger codes. Global index: `TRIGGER_REGISTRY_GLOBAL.md`.*

---

## Domain: `sports`

This registry defines every trigger code that may be emitted by the Sports Domain Receptor or related detectors when operating on sports signals.

**Sports betting note:** Logan's Sports domain covers game and odds intelligence only. Bet placement is never performed by Logan. Logan is read-only. Sports betting account linking is a V2 feature per `09_READ_AND_SUGGEST.md`. All Sports intelligence is subject to gambling compliance requirements per `27_SECURITY_PRIVACY_COMPLIANCE.md`.

---

## SPORTS_LINE_MOVEMENT_SIGNIFICANT

| Field | Value |
|-------|-------|
| **Code** | `SPORTS_LINE_MOVEMENT_SIGNIFICANT` |
| **Status** | ACTIVE |
| **Description** | The betting line (spread or total) moved by a significant amount without an obvious public catalyst (injury announcement, weather update). Suggests sharp/informed money moving the line. |
| **Fire condition** | Line moves ≥ 1.5 points (spread) or ≥ 3 points (total) without a correlated public news event in the prior 2 hours |
| **Confidence contribution** | +0.18 |

**Context shape:**
```json
{
  "line_type": "spread",
  "prior_line": -3.5,
  "current_line": -5.0,
  "line_delta": 1.5,
  "public_catalyst_detected": false,
  "time_to_game_hours": 36
}
```

---

## SPORTS_INJURY_KEY_PLAYER

| Field | Value |
|-------|-------|
| **Code** | `SPORTS_INJURY_KEY_PLAYER` |
| **Status** | ACTIVE |
| **Description** | A starting or key impact player is reported injured, questionable, or doubtful for an upcoming game. |
| **Fire condition** | Injury report filed for player with starter or key_impact designation AND game within 72 hours |
| **Confidence contribution** | +0.20 |

**Context shape:**
```json
{
  "player_name": "Patrick Mahomes",
  "team": "Kansas City Chiefs",
  "injury_status": "questionable",
  "injury_type": "ankle",
  "player_role": "starting_qb",
  "game_hours_away": 48,
  "line_impact_estimated_pct": 12.0
}
```

---

## SPORTS_WEATHER_CONDITION_IMPACT

| Field | Value |
|-------|-------|
| **Code** | `SPORTS_WEATHER_CONDITION_IMPACT` |
| **Status** | ACTIVE |
| **Description** | Game-day weather forecast indicates conditions likely to significantly affect scoring or play style (wind, rain, snow, extreme cold for outdoor venues). |
| **Fire condition** | Wind ≥ 20 mph OR precipitation probability ≥ 70% AND outdoor venue AND game within 48 hours |
| **Confidence contribution** | +0.12 |

**Context shape:**
```json
{
  "venue": "Arrowhead Stadium",
  "venue_type": "outdoor",
  "forecast_wind_mph": 28,
  "forecast_precip_pct": 80,
  "forecast_temp_f": 24,
  "historically_favors": "under"
}
```

---

## SPORTS_PUBLIC_SHARP_DIVERGENCE

| Field | Value |
|-------|-------|
| **Code** | `SPORTS_PUBLIC_SHARP_DIVERGENCE` |
| **Status** | ACTIVE |
| **Description** | The public betting percentage on one side diverges significantly from the direction the line is moving, suggesting sharp (professional) money is betting the other way. |
| **Fire condition** | Public bet pct on Team A ≥ 65% AND line is moving AGAINST Team A by ≥ 1 point |
| **Confidence contribution** | +0.20 |

**Context shape:**
```json
{
  "public_pct_team_a": 72,
  "public_pct_team_b": 28,
  "line_direction": "team_b",
  "line_delta": 1.5,
  "sharp_implied_side": "team_b",
  "divergence_score": 0.76
}
```

---

## SPORTS_CONSENSUS_PICK_EXTREME

| Field | Value |
|-------|-------|
| **Code** | `SPORTS_CONSENSUS_PICK_EXTREME` |
| **Status** | ACTIVE |
| **Description** | Public consensus on one side exceeds 75% of picks. Extreme public consensus is historically a contrarian signal in most sports betting contexts. |
| **Fire condition** | Public bet pct ≥ 75% on one side |
| **Confidence contribution** | +0.10 (contrarian signal — often favors the other side) |
| **Note** | This code alone is weak. Combine with `SPORTS_PUBLIC_SHARP_DIVERGENCE` or `SPORTS_REVERSE_LINE_MOVEMENT` for stronger signal. |

**Context shape:**
```json
{
  "public_pct_favorite": 78,
  "public_pct_underdog": 22,
  "favorite_side": "Chiefs -5.5",
  "historical_fade_win_pct": 0.54
}
```

---

## SPORTS_REVERSE_LINE_MOVEMENT

| Field | Value |
|-------|-------|
| **Code** | `SPORTS_REVERSE_LINE_MOVEMENT` |
| **Status** | ACTIVE |
| **Description** | The line moves against the direction of the majority of bets placed. Public money is on Team A, but the line moves in favor of Team A's opponent. This almost always indicates sharp/professional action. |
| **Fire condition** | ≥ 60% of bet tickets on Team A AND line moves ≥ 0.5 points in direction of Team B |
| **Confidence contribution** | +0.22 |

**Context shape:**
```json
{
  "public_ticket_pct_team_a": 63,
  "line_move_direction": "team_b",
  "line_delta": 1.0,
  "prior_line_team_a": -3.0,
  "current_line_team_a": -2.0
}
```

---

## SPORTS_GAME_STATUS_CHANGE

| Field | Value |
|-------|-------|
| **Code** | `SPORTS_GAME_STATUS_CHANGE` |
| **Status** | ACTIVE |
| **Description** | A game has been postponed, cancelled, or rescheduled. Relevant to any open positions or attention on the game. |
| **Fire condition** | Official status change detected from scheduled source |
| **Confidence contribution** | 0.0 (informational — used to retire or update related opportunities) |

**Context shape:**
```json
{
  "prior_status": "scheduled",
  "new_status": "postponed",
  "reason": "weather",
  "original_date": "2026-08-10",
  "rescheduled_date": "2026-08-11"
}
```

---

*Logan Intelligence TriggerEvent Registry: Sports — v3.1.2 | 2026-08-03*
*New in v3.1.2. 7 codes registered.*
