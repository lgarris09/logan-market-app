# Logan-Powered Mobile App — V1 Clean Build

This build is the first testable mobile foundation with a branch-based memory system.

## What is included

### Mobile app
- Clean, minimal home screen
- Personalized opportunity cards
- Ask Logan screen
- Memory Inbox screen
- iPhone and Android support through Expo

### Logan backend
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

The app should feel simple even while Logan's backend becomes sophisticated. Technical memory structures are hidden from the normal user experience, with only the Memory Inbox exposed when confirmation is useful.
