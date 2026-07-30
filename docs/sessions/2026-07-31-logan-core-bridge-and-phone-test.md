# Session note — 2026-07-31 — logan_core bridged to backend + mobile, verified on phone

## What was completed

- Bridged the `logan_core` Phase 1 vertical slice into the historical FastAPI backend via a new
  `POST /v1/demo/tesla` endpoint (`backend/app/logan_demo.py`), logged as
  [ADR-022](../DECISIONS.md#adr-022-logan_core-bridged-into-the-historical-backend-via-a-demo-endpoint-not-a-real-api-design).
  It runs the simulated Tesla AI-chip-partnership scenario through the full pipeline and returns the
  `DeliveredItem`, `ConclusionConfidence`, `PolicyResult`, and an execution-trace summary.
- Added mobile UI to exercise it end-to-end, with no hardcoded card content:
  `mobile/types/loganDemo.ts`, `mobile/components/LoganOpportunityCard.tsx`, `mobile/app/demo.tsx`,
  and a "Run Logan Demo" button wired in from `mobile/app/index.tsx` (route registered in `_layout.tsx`).
- Started both servers for real phone testing: FastAPI on `0.0.0.0:8000`, Expo/Metro on the LAN.
  Detected the host machine's LAN IPv4 (`192.168.86.44`, Wi-Fi adapter) and updated
  `mobile/constants/config.ts` to point at it instead of the placeholder IP.
- Generated a scannable QR code (`exp://192.168.86.44:8081`) and walked through the exact Expo Go steps.
- **User confirmed the phone test worked successfully.**
- Servers stopped cleanly at end of session (see below) and scratch log files removed.

## Verification results

- Backend: `curl http://192.168.86.44:8000/health` → `200`, confirming reachability over the LAN
  interface, not just `localhost`.
- Backend: `curl -X POST http://.../v1/demo/tesla` → full `TeslaDemoResponse`,
  `execution_trace.all_succeeded: true`, 19 layers in the correct documented order.
- Metro: `curl http://192.168.86.44:8081/status` → `packager-status:running`, confirming LAN reachability.
- Mobile type-check (`npx tsc --noEmit -p .`): all new files clean.
- Mobile bundle: forced a real iOS bundle via Metro (`.../entry.bundle?platform=ios&dev=true`) →
  `Bundled 6622ms ... (1108 modules)`, no errors; confirmed `app/demo.tsx` and
  `components/LoganOpportunityCard` present in the compiled output.
- `logan_core` test suite: 28/28 passing, unaffected by the bridge work.
- **Real phone test via Expo Go over the QR code: user-confirmed working.**

## Known issues / carried-forward risks

- **Nothing in this entire engagement has been committed to git yet.** `git status` at session end shows
  the repo still sitting at the original `Initial Logan baseline` commit on `main`, with all
  documentation, `logan_core/`, and the backend/mobile bridge work as uncommitted working-tree changes
  (modified + untracked). This wasn't asked for this session, so nothing was committed, but it's worth
  flagging clearly: a lot of work currently exists only in the working directory.
- `mobile/app/ask.tsx` has 3 pre-existing TypeScript errors (`theme.panel` / `theme.muted` don't exist in
  `theme.ts`) — confirmed via `git diff` to predate this session's changes. Not fixed (out of scope, not
  introduced by this work).
- The `sys.path` shim in `backend/app/logan_demo.py` is a local-dev bridge, not real packaging — see
  ADR-022. `logan_core` has no `pyproject.toml` yet.
- `192.168.86.44` is DHCP-assigned. It may change after this Windows restart or if the network changes —
  re-run the IP detection command below before assuming `mobile/constants/config.ts` is still correct.
- All `logan_core` stores (Operational History, Memory, Attention State) are in-memory only and reset
  every time the backend process restarts — expected per [ADR-006](../DECISIONS.md#adr-006-database-and-hosting--open-decision)
  (still open) and noted in `logan_core/docs/UNRESOLVED_QUESTIONS.md`.
- The external API contract between `logan_core` and a real client is still undesigned — `/v1/demo/tesla`
  is explicitly a demo endpoint, not that design (see ADR-022's own caution against growing it by
  accretion).

## Exact commands to resume

Re-check the LAN IP first — it may have changed after the restart:

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notlike '169.254.*' } | Select-Object InterfaceAlias, IPAddress
```

If it differs from `192.168.86.44`, update `mobile/constants/config.ts` accordingly before testing on a
phone again.

**Backend:**
```powershell
cd backend
.venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Mobile:**
```powershell
cd mobile
npx expo start
```

**Verify:**
```powershell
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/v1/demo/tesla
```

**Backend logan_core tests:**
```powershell
python -m pytest logan_core/tests -v
```

**Mobile type-check:**
```powershell
cd mobile
npx tsc --noEmit -p .
```
