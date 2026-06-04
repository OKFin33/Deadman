# Submission Readiness Runbook v0.1

Product: Deadman / 要是我来  
Status: P0 submission runbook  
Date: 2026-05-25

## Purpose

This runbook is the final pre-recording and pre-submission gate. It checks that
Deadman is not merely runnable in split local dev mode, but works through the
same frontend/backend boundary used for the submitted artifact.

## First-Principles Target

A mobile viewer can install/open the Android APK, watch a registered drama
moment, choose or type "if it were me", receive a credible local consequence or
a clear failure from the configured backend, and return to watching. Producer
artifacts must make the moment reproducible without committing media files or
secrets.

## Required Gate

From the repo root:

```bash
python3 tools/ars/deadman_check_submission_readiness.py \
  --report tmp/deadman_submission_readiness_report.md
```

The command must end with:

```text
Overall: PASS
```

To validate the formal CABRuntime-backed judgment path instead of the local demo
engine, run:

```bash
python3 tools/ars/deadman_check_submission_readiness.py \
  --require-cab-runtime \
  --report tmp/deadman_submission_readiness_report.cab.md
```

Product consequence: the default deploy remains easy to start in a clean
environment, while the CABRuntime claim has its own strict gate. Do not claim
formal CABRuntime judgment in a recording or submission unless this CAB gate
passes in the same environment.

For clean shareable deployment without local `tmp/` media on the server, require
an external media host:

```bash
python3 tools/ars/deadman_check_submission_readiness.py \
  --require-external-media-base \
  --report tmp/deadman_submission_readiness_report.external.md
```

Product consequence: local recording can pass with registered local MP4s, but a
clean ModelScope deployment should not be claimed shareable unless
`DEADMAN_MEDIA_BASE_URL` is configured.

## Local Recording URL

The current local deployment smoke path is:

```bash
python3 -m uvicorn server:app --host 127.0.0.1 --port 7860
```

For a CABRuntime-backed recording path:

```bash
DEADMAN_JUDGMENT_ENGINE=cab_runtime \
  python3 -m uvicorn server:app --host 127.0.0.1 --port 7860
```

Open:

```text
http://127.0.0.1:7860/demo/?branch3_player=1&episodeId=huangnian_ep12
```

Expected:

- the video source is `/api/deadman/media/huangnian/huangnian_ep12`;
- the video loads from registered local `tmp` media;
- companion notice appears;
- preset action returns consequence text and one compact percentage cue;
- closing the bubble returns to the player.

## Android APK Recording Path

The primary contest frontend artifact is the Android APK built from
`frontend`.

For a backend running on the same development machine:

```bash
python3 -m uvicorn server:app --host 127.0.0.1 --port 7860
adb reverse tcp:7860 tcp:7860
cd frontend
VITE_DEADMAN_API_BASE_URL=http://127.0.0.1:7860/api/deadman npm run android:debug
```

Install the debug APK from:

```text
frontend/android/app/build/outputs/apk/debug/app-debug.apk
```

For a shareable APK, build against a deployed HTTPS backend:

```bash
cd frontend
VITE_DEADMAN_API_BASE_URL=https://<backend-host>/api/deadman npm run android:debug
```

Product consequence: the APK is the frontend artifact. The backend remains a
normal service and holds provider credentials in environment variables.

For Vite-only local recording, generate an explicit `videoUrl`:

```bash
python3 tools/ars/deadman_print_recording_urls.py \
  --episode-id huangnian_ep12 \
  --deadman-api-base http://127.0.0.1:7860
```

## Media Deployment Contract

Raw short-drama MP4 files are not committed.

There are two valid ways to make media available:

1. Local recording: keep the downloaded MP4s under ignored `tmp/视频素材/...`.
2. Shareable deployment: configure `DEADMAN_MEDIA_BASE_URL` in platform
   environment management.

`ms_deploy.json` declares `DEADMAN_MEDIA_BASE_URL` with an empty value. Do not
put real secrets or private URLs into tracked deployment config.

## Git Packaging Boundary

Include:

- root source directories: `backend/`, `frontend/`, `tools/`, `studio/`,
  `assets/`, `data/`, `docs/`, and the compatibility namespace `Deadman/`;
- `frontend/android/` Capacitor Android shell;
- `server.py`;
- `ms_deploy.json` without secret values;
- docs and goal specs required to explain the build.

Do not include:

- `tmp/`;
- `output/`;
- `.env` or `.env.*`;
- raw MP4/MOV/M4V;
- provider raw outputs;
- local machine credentials.

## Final Recording Script

1. Start deployment app: `python3 -m uvicorn server:app --host 127.0.0.1 --port 7860`.
2. Open `/demo/?branch3_player=1&episodeId=huangnian_ep12`.
3. Show mobile player and loaded video.
4. Trigger companion notice.
5. Choose `今晚分兔肉，先让四蛋确认自己也有份`.
6. Show the companion result as one natural response, optionally mentioning one
   supporting cue such as `有52%其他观众也这么想`.
7. Close bubble and return to watching.
8. Mention boundary:
   - CABRuntime recording claims require `cab_runtime` plus a passing CAB gate
     in the same environment;
   - demo/test fallback is valid only when started with
     `DEADMAN_JUDGMENT_ENGINE=demo_deterministic`;
   - formal CABRuntime failure shows structured error instead of fake success.

## Stop Conditions

Do not record or submit if:

- readiness check fails;
- `/api/deadman/health` does not include `media.deployment_ready=true`;
- public API responses expose `tmp/`, `/Users/`, `/@fs`, `producer_media`, or
  `producer_refs`;
- any tracked config contains a real API key;
- the player requires manual browser query edits beyond the documented URL.
- the Android APK cannot reach the configured backend without manual devtools
  intervention.
