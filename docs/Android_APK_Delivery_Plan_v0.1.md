# Android APK Delivery Plan v0.1

Product: Deadman / `要是我来`  
Status: P0 delivery plan  
Date: 2026-06-01

## Decision

Deadman P0 should use:

```text
Android APK frontend + FastAPI backend
```

The mobile Web build remains the development and fallback presentation path, but
the primary contest artifact should be an installable Android APK.

## Why

The contest requirement separates frontend presentation from server
implementation:

- frontend presentation can be Android, iOS, or HarmonyOS;
- server implementation language is unrestricted;
- solo participants may choose Web frontend + backend as a lower-difficulty
  fallback.

Product consequence: an Android APK plus backend is a direct fit for the normal
team-delivery track. We do not need to force the entire product into one offline
APK, and we should not move the existing Python/CABRuntime backend into Android.

## Delivery Shape

```text
Deadman APK
  -> bundled Vite/React frontend
  -> vertical short-drama MP4 player
  -> resident tomato companion
  -> moment notice / tap / action / result UI
  -> calls Deadman backend over HTTPS or configured local recording URL

Deadman FastAPI backend
  -> drama catalog and moment packs
  -> registered media serving or external media URLs
  -> resident runtime session/event API
  -> judgment adapter and CABRuntime-backed formal path
  -> Doubao/Volcano provider calls through server-side environment variables

Producer side
  -> ARS/ASR/node mining
  -> reviewed Moment Causality Packs
  -> optional LangGraph Studio runner for the production story
```

## APK Boundary

The APK owns presentation, not model credentials or formal judgment execution.

APK includes:

- built Deadman frontend assets;
- companion sprites and UI assets;
- optional small demo/static assets if legally safe and size-acceptable;
- backend base URL configuration at build time.

APK does not include:

- real API keys in source control;
- Python FastAPI server process;
- CABRuntime checkout or Python package graph;
- raw producer-side local paths;
- large raw short-drama media unless explicitly approved for a private contest
  artifact build.

## Backend Boundary

The backend remains a normal server process. For local recording it can run on a
developer machine. For shareable review it should be deployed and reachable from
the APK.

Required backend environment:

```text
DEADMAN_JUDGMENT_ENGINE=demo_deterministic|cab_runtime
DEADMAN_MEDIA_BASE_URL=<optional external media base>
<provider-specific model keys>
```

Formal CABRuntime claims require:

```bash
python3 tools/ars/deadman_check_submission_readiness.py \
  --require-cab-runtime \
  --report tmp/deadman_submission_readiness_report.cab.md
```

## Frontend Configuration

The APK build must set the backend API base explicitly:

```bash
VITE_DEADMAN_API_BASE_URL=https://<backend-host>/api/deadman npm run build
```

For local Android-device recording, use one of:

- `adb reverse tcp:<port> tcp:<port>` and
  `VITE_DEADMAN_API_BASE_URL=http://127.0.0.1:<port>/api/deadman`;
- a LAN-accessible backend URL plus debug cleartext allowance;
- a deployed HTTPS backend URL.

Product consequence: do not rely on same-origin `/api/deadman` inside APK. The
APK local origin is the Android WebView asset host, not the FastAPI backend.

## Acceptance Gate

Minimum APK spike acceptance:

- `npm test` passes in `frontend`;
- `npm run build` passes;
- `npx cap sync android` passes;
- Android debug APK can be assembled;
- installed APK opens the player shell;
- configured backend health and runtime event APIs are reachable;
- one moment notice can open the companion bubble;
- one preset action returns a one-narrative result or a structured error;
- returning to the player works without manual refresh.

## Fallback

If Android build/signing/WebView networking blocks the deadline, submit:

```text
mobile-first Web frontend + FastAPI backend
```

This fallback is explicitly allowed for solo participation. The Android lane
should not endanger the already working user-side and backend loop.
