# Logan — Opportunity Intelligence Platform

Logan is an AI-powered opportunity intelligence platform, starting in markets, sports betting, prediction
markets (Polymarket), and news. It reasons about what deserves a user's attention and explains why,
building a durable understanding of what a user cares about so that surfaced opportunities feel personally
relevant instead of generic. See [docs/PRODUCT.md](docs/PRODUCT.md) for the full product vision.

> **Architecture note**: Logan's canonical Phase 1 architecture is now the Logan Intelligence System — an
> 18-layer reasoning pipeline documented in [docs/specs/](docs/specs/) and being built in a new
> `logan_core/` directory (see [ADR-014](docs/DECISIONS.md#adr-014-adopt-the-logan-intelligence-system-v10-architecture-as-canonical-retire-the-fastapisqlite-sketch-as-historical)).
> The `backend/`/`mobile/` instructions below still describe the only code that actually runs today — a
> historical prototype, kept running while `logan_core/` is built alongside it. See
> [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how the two relate.

This is being built as a commercial product, not a prototype-and-forget project. Before touching code,
read:

- [docs/PRODUCT.md](docs/PRODUCT.md) — vision, target users, product phases, the analysis-vs-advice
  boundary.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — how the system is built and the principles behind it.
- [docs/specs/](docs/specs/) — the locked Logan Intelligence System architecture, data contracts, and
  implementation plan. Required reading before any `logan_core/` work.
- [docs/STANDARDS.md](docs/STANDARDS.md) — coding standards, git workflow, testing, security,
  documentation.
- [docs/DECISIONS.md](docs/DECISIONS.md) — the ADR log: why things are the way they are.
- [docs/ROADMAP.md](docs/ROADMAP.md) — what's next, by phase.
- [CLAUDE.md](CLAUDE.md) — rules for AI assistants working in this repo.

## What is included

### Mobile app (`mobile/`)
- Clean, minimal home screen
- Personalized opportunity cards
- Ask Logan screen
- Memory Inbox screen
- iPhone and Android support through Expo

### Logan backend (`backend/`) — historical prototype, see architecture note above
- FastAPI service
- SQLite memory database
- Category-linked memory branches
- Importance and confidence scoring
- Memory types and status
- Reinforcement when information repeats
- Memory Inbox for uncertain inferences
- Confirmation and rejection endpoints
- Category-specific memory retrieval

## Memory flow

```text
User information
    ↓
Classify type
    ↓
Score importance + confidence
    ↓
Assign primary app branch
    ↓
Create linked branches
    ↓
Store / Memory Inbox / Ignore
```

Primary categories currently supported:

- Markets / Stocks
- Sports Betting
- Polymarket
- News
- User Profile
- Decision DNA

## Start the backend

From `backend`:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Start the phone app

From `mobile`:

```powershell
npm install
npx expo start
```

Install Expo Go on the phone and scan the QR code.

## Connect the phone to the backend

Update:

```text
mobile/constants/config.ts
```

Replace the sample address with the computer's local IPv4 address:

```ts
export const API_BASE_URL = "http://192.168.1.100:8000";
```

The phone and computer must be on the same Wi-Fi.

This hardcoded-IP setup is a local-development convenience only — see
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#known-gaps-phase-1-prototype--tracked-not-yet-urgent) for
what needs to change before this goes beyond a developer's machine.

## Run the Logan Intelligence System demo

`POST /v1/demo/tesla` bridges the historical backend to the `logan_core` pipeline (see
[ADR-022](docs/DECISIONS.md#adr-022-logan_core-bridged-into-the-historical-backend-via-a-demo-endpoint-not-a-real-api-design))
and runs the Tesla AI-chip-partnership scenario end-to-end on simulated data. The mobile app has a
"Run Logan Demo" button on the home screen that calls it and renders the result.

Backend (from `backend`, after following "Start the backend" above):

```powershell
curl -X POST http://127.0.0.1:8000/v1/demo/tesla
```

Or open `http://127.0.0.1:8000/docs` and try it from the Swagger UI.

Mobile: start the app per "Start the phone app" above, then tap **Run Logan Demo** on the home screen.

## Test memory through the API

Open:

```text
http://127.0.0.1:8000/docs
```

Use `POST /v1/memories` with:

```json
{
  "content": "I normally wait for large selloffs before buying growth stocks.",
  "active_category": "stocks",
  "source": "user_statement",
  "user_confirmed": false
}
```

Then inspect:

- `GET /v1/memories`
- `GET /v1/memories?inbox_only=true`
- `GET /v1/context/stocks`

## Design rule

The app should feel simple even while Logan's backend becomes sophisticated. Technical memory structures
are hidden from the normal user experience, with only the Memory Inbox exposed when confirmation is
useful.

## Contributing

See [docs/STANDARDS.md](docs/STANDARDS.md#git-workflow) for the branching model and commit conventions
before opening a PR.
