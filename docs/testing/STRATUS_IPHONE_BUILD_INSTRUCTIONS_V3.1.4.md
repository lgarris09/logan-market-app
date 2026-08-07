# STRATUS — Building and Installing on Your iPhone (V3.1.4)

These steps get a real, Apple-signed STRATUS build running on your iPhone, connected to a backend running
on your computer. This is **not** Expo Go — it's a native development-client build, the direction this
project committed to for V3.1.4 onward.

Everything up through "Trigger the build" can be done ahead of time. **Steps 4 and 5 require your own
Apple ID and Expo account** — nobody else can do those for you. Everything after the build finishes is
yours to run whenever you want to test.

---

## Before you start

- **A paid Apple Developer Program membership** ($99/year, enrolled at developer.apple.com) is required to
  install a signed build on a real iPhone. Without one, `eas build` can still produce an iOS **simulator**
  build, but that only runs in Xcode's Simulator on a Mac, not on your actual phone.
- **A free Expo account** (create one at expo.dev if you don't have one) — this is separate from your
  Apple ID and is how `eas build` identifies your project.
- Your iPhone and your computer must be able to reach the same Wi-Fi network when you actually test.
- Node.js and npm must be installed on the computer running these commands.

---

## 1. Install dependencies

```powershell
cd mobile
npm install
```

## 2. Confirm the project configuration (already done, nothing to change here)

Already set and verified as of V3.1.4 — you don't need to touch these:

| Setting | Value | File |
|---|---|---|
| iOS bundle identifier | `com.garrisengineeringllc.loganmarketmobile` | `app.json` |
| EAS project ID | `2b139ca5-1cca-47fe-ab08-8f7e654f8a7e` | `app.json` |
| Development build profile | `developmentClient: true`, internal distribution | `eas.json` |
| App display name | `STRATUS` | `app.json` |

## 3. Log in to Expo

```powershell
npx eas-cli@latest login
```

This asks for your Expo account email/password (or opens a browser to log in). This is your Expo
account, **not** your Apple ID — that comes later.

## 4. Register your iPhone for internal distribution — requires you

```powershell
npx eas-cli@latest device:create
```

- This prints a link and a QR code.
- **On your iPhone**, open that link (or scan the QR code with the Camera app) in Safari.
- Follow the on-screen steps to install a small registration profile — go to **Settings → General → VPN &
  Device Management** afterward and confirm/trust it if prompted.
- This registers your iPhone's unique device ID so Apple will allow a signed development build to run on
  it. You only need to do this once per device.

## 5. Trigger the build — requires you (Apple ID)

```powershell
npx eas-cli@latest build --profile development --platform ios
```

You'll be walked through a few interactive prompts. Here's what to expect and what to pick:

- **"Select platform"** — already answered by `--platform ios`; you won't see this if it's specified.
- **Simulator or device build?** — choose **device** (not simulator). We want this to run on your actual
  iPhone.
- **Apple sign-in** — log in with your Apple ID. If your account has two-factor authentication (it should),
  you'll get a verification code on a trusted Apple device — enter it when asked.
- **"Select an Apple Team"** — if your Apple ID belongs to more than one team (personal + an organization),
  pick the one you want this build associated with. If you only see one option, EAS picks it automatically.
- **"Would you like EAS to handle Distribution Certificate / Provisioning Profile management?"** — choose
  **yes / let EAS handle it**. This is the recommended path and avoids manually generating certificates in
  the Apple Developer portal.
- The build then runs on Expo's build servers — typically 10–20 minutes for iOS. The command prints a URL
  where you can watch progress in a browser; you can also just wait for the terminal to finish.

## 6. Install the build on your iPhone

When the build finishes, EAS prints an install link and QR code.

- **On your iPhone**, open the link (or scan the QR code) — this opens Apple's over-the-air install page.
- Tap **Install**.
- If iOS shows an "Untrusted Developer" warning the first time you open the app: go to **Settings →
  General → VPN & Device Management**, find the developer profile, and tap **Trust**.
- A **STRATUS** icon appears on your home screen. It will use a generic/default icon for now — a custom
  app icon hasn't been finalized yet (see the branding audit in the completion report), this doesn't affect
  functionality.

You only need to repeat steps 3–6 when the native app itself changes (new native dependencies, icon,
permissions, etc.) — not for ordinary code changes, which reload live over the network (next step).

---

## Running STRATUS day-to-day (after the build is installed once)

## 7. Point the app at your backend

Copy the example environment file and set your computer's local network address:

```powershell
cd mobile
copy .env.example .env
```

Edit `.env` and set:

```text
EXPO_PUBLIC_API_BASE_URL=http://<this computer's local IPv4 address>:8000
```

Find your computer's local IPv4 address with `ipconfig` (Windows) — look for something like
`192.168.1.100`. **Do not use `localhost` or `127.0.0.1`** — the phone is a separate device and needs your
computer's address on the shared Wi-Fi network.

No source file needs editing — `.env` is read automatically, and changes take effect the next time you
start Metro (step 9), no rebuild required.

## 8. Start the backend

```powershell
cd backend
.venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

`--host 0.0.0.0` is required — it's what allows your phone to reach this server; `127.0.0.1` alone would
only accept connections from the computer itself.

## 9. Start Metro (the JavaScript server)

```powershell
cd mobile
npx expo start --dev-client
```

## 10. Open STRATUS on your iPhone

Open the STRATUS app already installed on your phone (step 6). It should connect to the Metro server
automatically if your phone and computer are on the same Wi-Fi network and it has connected before. If it
opens to a blank "development client" launcher screen instead of the app, scan the QR code shown in your
terminal from step 9 with your iPhone's camera.

## 11. Confirm it's working

You should see:
- A brief loading indicator, then
- The Attention Field populated with opportunities (simulated data, not live market data — this is
  expected for V3.1.4).

If you instead see "Unable to reach STRATUS" or it spins and then times out:
- Confirm the backend (step 8) is still running and didn't print an error.
- Confirm the phone and computer are on the same Wi-Fi network (not one on cellular/hotspot).
- Confirm `.env`'s IP address matches what `ipconfig` shows right now — it changes if you reconnect to
  Wi-Fi or switch networks.
- Retry using the app's own **Retry** button — no need to restart anything for a simple retry.

Once you can see the Attention Field, you're ready for the acceptance test:
[docs/testing/STRATUS_IPHONE_ACCEPTANCE_TEST_V3.1.4.md](STRATUS_IPHONE_ACCEPTANCE_TEST_V3.1.4.md).
