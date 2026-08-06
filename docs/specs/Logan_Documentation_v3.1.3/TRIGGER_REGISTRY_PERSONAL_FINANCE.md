# Logan Intelligence — TriggerEvent Registry: Personal Finance Domain
**Version:** 3.1.3
**Status:** SPECIFIED — NOT IMPLEMENTED (V3.1.4 BATCH-3, OD-009) — see `TRIGGER_EVENT_FRAMEWORK.md`.
*New in v3.1.2. No prior version.*
*Authoritative source for all Personal Finance domain trigger codes. Global index: `TRIGGER_REGISTRY_GLOBAL.md`.*

---

## Domain: `personal_finance`

This registry defines every trigger code that may be emitted by the Personal Finance Domain Receptor when operating on macroeconomic signals (Federal Reserve, Bureau of Labor Statistics, Bureau of Economic Analysis, housing market data).

**V1 scope note:** The Personal Finance receptor in V1 covers public macroeconomic signals only — Federal Reserve decisions, inflation reports, employment data, and housing market indicators. Personal financial account linking (bank accounts, credit cards) is a V2 feature. V1 macro signals are personalized using the user's stated interests and linked brokerage/investment account positions.

**What Personal Finance domain intelligence surfaces:** Logan uses macro signals to surface opportunities where macroeconomic events directly affect the user's financial situation — a Fed rate cut when the user is in the market for a mortgage, an inflation surprise when the user holds significant bond positions, a jobs report when the user's industry is affected.

---

## PF_FED_RATE_DECISION_SURPRISE

| Field | Value |
|-------|-------|
| **Code** | `PF_FED_RATE_DECISION_SURPRISE` |
| **Status** | ACTIVE |
| **Description** | The Federal Reserve's rate decision deviates from market consensus expectation (CME FedWatch implied probability). A surprise — either a cut when none was expected, a hold when a cut was expected, or an unexpected change in magnitude. |
| **Fire condition** | Announced decision differs from the highest-probability outcome in CME FedWatch the day prior |
| **Confidence contribution** | +0.24 |

**Context shape:**
```json
{
  "decision": "cut",
  "decision_bps": 50,
  "consensus_expected": "cut_25bps",
  "new_fed_funds_rate": 4.75,
  "prior_fed_funds_rate": 5.25,
  "surprise_type": "larger_than_expected",
  "dot_plot_updated": true,
  "press_conference_scheduled": true,
  "source": "Federal Reserve"
}
```

---

## PF_FED_RATE_DECISION_INLINE

| Field | Value |
|-------|-------|
| **Code** | `PF_FED_RATE_DECISION_INLINE` |
| **Status** | ACTIVE |
| **Description** | The Federal Reserve's rate decision matches market consensus. Useful for clearing hypotheses and noting that no surprise occurred. |
| **Fire condition** | Announced decision matches the highest-probability outcome in CME FedWatch the day prior |
| **Confidence contribution** | 0.0 (informational; used to close waiting hypotheses) |

**Context shape:**
```json
{
  "decision": "hold",
  "new_fed_funds_rate": 5.25,
  "consensus_expected": "hold",
  "source": "Federal Reserve"
}
```

---

## PF_INFLATION_REPORT_SURPRISE

| Field | Value |
|-------|-------|
| **Code** | `PF_INFLATION_REPORT_SURPRISE` |
| **Status** | ACTIVE |
| **Description** | CPI or PCE inflation data surprises versus consensus estimate — either hotter (higher inflation) or cooler (lower inflation) than expected. Directly affects interest rate expectations and asset prices. |
| **Fire condition** | `abs(actual_pct - consensus_pct) >= 0.2` percentage points |
| **Confidence contribution** | +0.20 |

**Context shape:**
```json
{
  "report_type": "CPI",
  "period": "July 2026",
  "actual_yoy_pct": 2.4,
  "consensus_yoy_pct": 2.8,
  "surprise_direction": "cooler",
  "surprise_magnitude_pp": -0.4,
  "core_actual_pct": 2.1,
  "core_consensus_pct": 2.5,
  "source": "BLS"
}
```

---

## PF_JOBS_REPORT_SURPRISE

| Field | Value |
|-------|-------|
| **Code** | `PF_JOBS_REPORT_SURPRISE` |
| **Status** | ACTIVE |
| **Description** | Non-farm payrolls significantly beat or miss consensus forecast. Strong jobs beats delay rate cuts; misses accelerate them. |
| **Fire condition** | `abs(actual_nfp - consensus_nfp) >= 50000` jobs |
| **Confidence contribution** | +0.18 |

**Context shape:**
```json
{
  "report_period": "July 2026",
  "actual_nfp": 272000,
  "consensus_nfp": 185000,
  "surprise_jobs": 87000,
  "surprise_direction": "beat",
  "unemployment_rate_actual": 3.9,
  "unemployment_rate_prior": 4.0,
  "wage_growth_yoy_pct": 4.2,
  "source": "BLS"
}
```

---

## PF_MORTGAGE_RATE_THRESHOLD

| Field | Value |
|-------|-------|
| **Code** | `PF_MORTGAGE_RATE_THRESHOLD` |
| **Status** | ACTIVE |
| **Description** | The 30-year fixed mortgage rate crosses a threshold that is financially significant for the user — either a level they expressed interest in or a historically significant threshold for affordability. This trigger is more personalized than the others in this domain. |
| **Fire condition** | 30-year fixed rate crosses a user-relevant threshold OR crosses a 6-month or 12-month low/high |
| **Confidence contribution** | +0.20 (higher when user has expressed mortgage-related interest) |

**Context shape:**
```json
{
  "current_rate_pct": 5.875,
  "prior_week_rate_pct": 6.250,
  "rate_delta_pp": -0.375,
  "threshold_crossed": "6_month_low",
  "threshold_value": 5.875,
  "user_threshold_relevant": true,
  "source": "Freddie Mac Weekly Survey"
}
```

---

## PF_GDP_REVISION_SIGNIFICANT

| Field | Value |
|-------|-------|
| **Code** | `PF_GDP_REVISION_SIGNIFICANT` |
| **Status** | ACTIVE |
| **Description** | GDP growth is revised significantly from a prior estimate (initial, second, or third estimate revision). Large revisions affect rate expectations and asset pricing. |
| **Fire condition** | Revision magnitude ≥ 0.5 percentage points from prior estimate |
| **Confidence contribution** | +0.12 |

**Context shape:**
```json
{
  "period": "Q2 2026",
  "estimate_type": "second",
  "prior_estimate_pct": 2.1,
  "revised_estimate_pct": 2.8,
  "revision_pp": 0.7,
  "revision_direction": "upward",
  "source": "BEA"
}
```

---

## PF_SAVINGS_RATE_ANOMALY

| Field | Value |
|-------|-------|
| **Code** | `PF_SAVINGS_RATE_ANOMALY` |
| **Status** | ACTIVE |
| **Description** | The personal savings rate crosses a historically significant threshold — either very high (suggests consumer caution, reduced spending) or very low (suggests consumer stretch, potential credit stress). |
| **Fire condition** | Personal savings rate drops below 3.0% or rises above 8.0% (historically significant thresholds) |
| **Confidence contribution** | +0.10 |

**Context shape:**
```json
{
  "savings_rate_pct": 2.6,
  "prior_month_pct": 3.8,
  "threshold_crossed": "below_3pct",
  "historical_context": "Rate below 3% has preceded recessions in 3 of last 4 cycles",
  "source": "BEA"
}
```

---

*Logan Intelligence TriggerEvent Registry: Personal Finance — v3.1.2 | 2026-08-03*
*New in v3.1.2. 7 codes registered.*
