# Logan Intelligence — Integration Feasibility Matrix
**Version:** 3.1.3
*Source: Architecture v1.3 FINAL (2026-07-31). Original: “source_material/25_INTEGRATION_FEASIBILITY.md” (historical label).*
*All provider choices are PROVISIONAL. Confirm before building integrations.*

---

## Overview

This document assesses the feasibility of each planned V1 data integration — what each provider offers, what's required to access it, known constraints, and risks.

Logan's 8 domains in V1: Stocks · Sports · Prediction Markets · Crypto · Social Trends · Culture · Personal Finance · News (restored v3.1.3, ADR-037).

**Note:** a News-domain integration assessment (provider choice, cost, feasibility) is not included in this matrix — it is `RESEARCH REQUIRED`, not assessed as part of this reconciliation pass.

---

## Brokerage / Account Linking

### Plaid
| Factor | Assessment |
|--------|-----------|
| **What it provides** | Read-only access to brokerage positions, transactions, balances via Plaid Investments |
| **API availability** | Generally available; requires Plaid account and application review |
| **Auth model** | OAuth via Plaid Link (user authenticates directly with their bank/broker) |
| **Logan never receives** | Credentials; Plaid tokens only |
| **Supported brokers** | Robinhood, Fidelity, Schwab, TD Ameritrade, Vanguard, and ~12,000 institutions |
| **Cost** | Paid per call; see Plaid pricing |
| **Risk** | Plaid may change terms or pricing; broker coverage varies |
| **Status** | PROVISIONAL — application required |

---

## Stock Market Data

### Alpaca Markets
| Factor | Assessment |
|--------|-----------|
| **What it provides** | Real-time and historical stock prices, trades, news |
| **API availability** | Free tier (delayed data); paid for real-time |
| **Auth model** | API key |
| **Real-time** | Yes (paid tier) |
| **Risk** | Rate limits on free tier may be insufficient for V1 |
| **Status** | PROVISIONAL |

### Polygon.io
| Factor | Assessment |
|--------|-----------|
| **What it provides** | Real-time stocks, options, forex, crypto |
| **API availability** | Free tier (delayed); paid for real-time websocket |
| **Real-time** | Yes (paid) |
| **Status** | PROVISIONAL — good alternative to Alpaca |

### IEX Cloud
| Factor | Assessment |
|--------|-----------|
| **What it provides** | Stock data, fundamentals, news sentiment |
| **Status** | PROVISIONAL |

---

## Sports Data

### Sportradar
| Factor | Assessment |
|--------|-----------|
| **What it provides** | Live scores, injuries, team/player stats, odds feeds |
| **API availability** | Paid; enterprise pricing |
| **Auth model** | API key |
| **Cost** | Significant — not suitable for early MVP without budget |
| **Alternative** | The Odds API (cheaper, odds-focused) |
| **Status** | PROVISIONAL — evaluate The Odds API first for MVP cost |

### The Odds API
| Factor | Assessment |
|--------|-----------|
| **What it provides** | Aggregated sports odds from 40+ bookmakers |
| **Cost** | Free tier (500 requests/month); paid tiers available |
| **Status** | PROVISIONAL — suitable for MVP |

---

## Prediction Markets

### Kalshi
| Factor | Assessment |
|--------|-----------|
| **What it provides** | Contract prices, volumes, market data |
| **API availability** | Public API available; account required |
| **Account linking** | Yes — Kalshi has an API for authorized partners |
| **Regulatory note** | US CFTC-regulated prediction market |
| **Status** | PROVISIONAL — viable for V1 |

### Polymarket
| Factor | Assessment |
|--------|-----------|
| **What it provides** | Prediction market contract prices, volumes |
| **API availability** | Public read API available |
| **Account linking** | Web3/wallet-based; harder to link than Kalshi |
| **Regulatory note** | US users may face access restrictions |
| **Status** | PROVISIONAL — regulatory risk; secondary to Kalshi |

---

## News and Sentiment

### NewsAPI
| Factor | Assessment |
|--------|-----------|
| **What it provides** | Headlines from 80,000+ sources, full-text search |
| **Free tier** | Yes (limited); paid for real-time and higher volume |
| **Status** | PROVISIONAL — good for V1 news receptor |

### RSS Aggregation
| Factor | Assessment |
|--------|-----------|
| **What it provides** | Direct feed from financial news sources (Reuters, Bloomberg, CNBC) |
| **Cost** | Free for public RSS |
| **Risk** | Some sources restrict RSS; content may be delayed |
| **Status** | Good supplement to NewsAPI |

---

## Social Signals

### Reddit API
| Factor | Assessment |
|--------|-----------|
| **What it provides** | Posts, comments, upvotes from subreddits (r/wallstreetbets, r/investing, etc.) |
| **API availability** | Available; rate-limited |
| **Auth** | OAuth app required |
| **Note** | Reddit changed API pricing in 2023; verify current terms |
| **Status** | PROVISIONAL |

### X (Twitter) API
| Factor | Assessment |
|--------|-----------|
| **What it provides** | Real-time posts, trending topics |
| **Cost** | Paid API only; significant cost for real-time volume |
| **Risk** | API terms have changed significantly; high cost |
| **Status** | DEFERRED to V2+ unless budget available |

---

## Culture Domain

The Culture domain tracks entertainment momentum, media trends, and cultural event signals. Sources span music streaming, video platforms, and entertainment industry data.

### Spotify API
| Factor | Assessment |
|--------|-----------|
| **What it provides** | Track streaming counts, chart positions, artist follower growth, playlist adds |
| **API availability** | Public API available; OAuth app registration required |
| **Auth model** | OAuth 2.0 (Client Credentials for public data; Authorization Code for user data) |
| **Real-time** | Daily chart updates; streaming counts delayed ~24 hours |
| **Relevant signals** | Track velocity (streams accelerating), chart entry, viral playlist add surge |
| **Logan usage** | Culture receptor reads public chart/trend data only; not user listening history |
| **Risk** | Spotify rate limits; terms may restrict automated chart tracking |
| **Status** | PROVISIONAL — viable for V1 culture receptor |

### Apple Music / iTunes Charts
| Factor | Assessment |
|--------|-----------|
| **What it provides** | Song and album chart positions across categories and regions |
| **API availability** | MusicKit JS / Apple Music API; requires Apple Developer account |
| **Auth model** | JSON Web Token (developer token + user token for personal data) |
| **Real-time** | Charts update hourly |
| **Logan usage** | Public charts only — cross-reference with Spotify for convergence signal |
| **Risk** | Apple Music API has stricter access rules than Spotify |
| **Status** | PROVISIONAL — secondary to Spotify |

### YouTube Data API
| Factor | Assessment |
|--------|-----------|
| **What it provides** | View counts, trending video lists, channel subscriber counts, engagement metrics |
| **API availability** | Google Cloud Console; generous free quota |
| **Auth model** | API key (public data); OAuth for user data |
| **Real-time** | View counts and trending updated frequently |
| **Relevant signals** | Video going viral (view velocity), trending topic emergence, artist/creator momentum |
| **Logan usage** | Culture receptor reads public trend data; specifically trending video categories and velocity |
| **Risk** | Quota limits (10,000 units/day on free tier); trending list limited to ~50 items |
| **Status** | PROVISIONAL — good for culture domain V1 |

### Billboard / Chartmetric
| Factor | Assessment |
|--------|-----------|
| **What it provides** | Chart history, streaming aggregations, artist momentum across platforms |
| **API availability** | Chartmetric has a paid API; Billboard has unofficial scrapers only |
| **Cost** | Chartmetric is paid; Billboard official API access not publicly available |
| **Status** | DEFERRED — Spotify + Apple Music + YouTube covers most needs for V1 |

---

## Personal Finance Domain

The Personal Finance domain tracks macroeconomic signals and personal finance milestones relevant to the user's situation. Sources are public government data and news signals.

### Federal Reserve / FRED (St. Louis Fed)
| Factor | Assessment |
|--------|-----------|
| **What it provides** | Interest rates (Fed Funds Rate, mortgage rates), economic indicators (CPI, PCE), money supply data |
| **API availability** | FRED API — free, public, high-reliability |
| **Auth model** | API key (free to obtain) |
| **Real-time** | Policy updates real-time; economic releases on scheduled calendar |
| **Relevant signals** | Rate decision (hike/hold/cut), inflation report beat/miss, unexpected rate guidance |
| **Status** | PROVISIONAL — high confidence, viable for V1 |

### Bureau of Labor Statistics (BLS)
| Factor | Assessment |
|--------|-----------|
| **What it provides** | Employment data (jobs report), inflation (CPI), wage growth |
| **API availability** | Free public API; no key required for basic access; key for higher volume |
| **Real-time** | Releases on scheduled calendar (first Friday of month for jobs) |
| **Relevant signals** | Jobs beat/miss, CPI surprise, wage growth acceleration |
| **Status** | PROVISIONAL — free and reliable |

### Bureau of Economic Analysis (BEA)
| Factor | Assessment |
|--------|-----------|
| **What it provides** | GDP growth, personal income, personal savings rate |
| **API availability** | Free public API; API key required |
| **Real-time** | Quarterly GDP, monthly personal income data |
| **Relevant signals** | GDP revision, personal savings rate change |
| **Status** | PROVISIONAL — supplement to BLS for macro picture |

### Mortgage / Housing Data
| Factor | Assessment |
|--------|-----------|
| **What it provides** | 30-year fixed mortgage rate, home price index, housing starts |
| **Sources** | Freddie Mac weekly survey (public), Case-Shiller (S&P via FRED) |
| **API availability** | Available via FRED |
| **Relevant signals** | Mortgage rate crossing thresholds relevant to user (e.g., "rates dropped below your pre-approval estimate") |
| **Status** | PROVISIONAL |

**Note on Personal Finance account linking:** Personal Finance account linking (bank accounts, credit cards) is deferred to V2. V1 Personal Finance receptor uses public macro data only — no user financial account access in V1. See `09_READ_AND_SUGGEST.md` for account linking scope.

---

## Sports Betting Account Linking

### DraftKings / FanDuel
| Factor | Assessment |
|--------|-----------|
| **What it provides** | Bet history, open positions, balance |
| **API availability** | No public API for third-party account access |
| **Current approach** | Not feasible via API; requires screen scraping or official partnership |
| **Status** | DEFERRED — no viable API path for V1. Sports betting account linking is a V2 feature per `09_READ_AND_SUGGEST.md`. |

---

## Integration Build Priority (V1)

| Priority | Provider | Domain | Why |
|----------|---------|--------|-----|
| 1 | Polygon.io or Alpaca | Stocks | Vertical slice requires this |
| 2 | NewsAPI + RSS | Stocks, Social | News signals for stocks domain |
| 3 | Reddit API | Social | Community signals |
| 4 | Kalshi | Prediction Markets | Prediction market domain |
| 5 | The Odds API | Sports | Sports domain odds signals |
| 6 | Plaid | Personal (Read & Suggest) | Sprint 3 account linking |
| 7 | Spotify API | Culture | Culture domain receptor |
| 8 | YouTube Data API | Culture | Culture convergence signal |
| 9 | FRED API | Personal Finance | Macro signal receptor |
| 10 | BLS API | Personal Finance | Jobs/inflation signals |
| 11 | Polymarket | Prediction Markets | Secondary to Kalshi |

---

*Logan Intelligence Integration Feasibility Matrix — v3.1.2 | 2026-08-03*
*v3.1.2 changes: Culture domain section added (Spotify API, Apple Music, YouTube Data API, Billboard/Chartmetric). Personal Finance domain section added (Federal Reserve/FRED, BLS, BEA, Mortgage/Housing). Sports betting account linking note updated: deferred to V2 per `09_READ_AND_SUGGEST.md`. Integration Build Priority table expanded to include culture and personal finance providers. 7-domain note added to overview.*


---
## v3.1.2 Verification Metadata

Every provider row must include `date_verified`, `source`, `verification_owner`, and `recheck_date`. Unverified availability, pricing, OAuth, data scope, jurisdiction, and terms remain RESEARCH REQUIRED. Do not promise account linking until verified.
