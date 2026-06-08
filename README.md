# Deadman · 看剧搭子

A short-drama watching **companion**. While you watch, the moment a scene makes
you want to say something, the companion catches that beat: one friend-style
opener, three "things I want to say", and a reply that catches your feeling back.

```text
我想说一句。
```

The viewer is not choosing a story branch — they are saying the line the scene
made them want to say. **No typing required, and it never interrupts playback.**

## Architecture

```text
agentic authoring backstage · deterministic frontstage · bounded runtime adaptation
```

- **Studio (backstage)** — agentic authoring (LangGraph + CAB) turns reviewed
  drama moments into audited companion-exchange packs.
- **Stage (frontstage)** — a light, deterministic mobile-first player renders the
  reviewed packs; runtime model use is bounded and only after the viewer opts in.

The primary runtime contract is `companion_exchange.reply_candidates`: a
friend-style lead, three reviewed reply candidates, and a selected echo.

## Layout

| Path | Purpose |
| --- | --- |
| `frontend/` | Mobile-first React/Vite player + tomato companion |
| `backend/` | FastAPI APIs, viewer runtime, judgment adapter, CAB client |
| `studio/` | Producer-side Studio prototype |
| `tools/` | Producer/authoring pipeline, validation, publication checks |
| `data/` | Reviewed drama packs, schemas, and the taste dataset |
| `assets/` | Static companion assets |
| `server.py` | Deployable FastAPI entrypoint |
| `ms_deploy.json` | Deployment env template (secrets omitted) |

## Run locally

Backend:

```bash
python3 -m pip install -r requirements.txt
uvicorn server:app --host 127.0.0.1 --port 7861
```

Frontend:

```bash
cd frontend
npm install
VITE_DEADMAN_API_PROXY_TARGET=http://127.0.0.1:7861 npm run dev -- --host 127.0.0.1 --port 5175
```

Open `http://127.0.0.1:5175/?branch3_player=1`.

## Runtime modes

```bash
DEADMAN_JUDGMENT_ENGINE=cab_runtime         # formal judgment via sibling CABRuntime
DEADMAN_JUDGMENT_ENGINE=demo_deterministic  # tests / demo fallback only
```

Formal runtime failure fails closed with a structured error — it never silently
returns deterministic/template judgment as formal judgment.

## Media & secrets

Raw media (`*.mp4`), provider keys, `.env`, caches and build outputs are never
committed. Public deployment either configures an external media base URL
(`DEADMAN_MEDIA_BASE_URL`) or serves registered local media outside git.
**Provider credentials are environment variables only** (`ARK_API_KEY`, …).

## Checks

```bash
python3 -m unittest discover -s backend/tests
python3 tools/ars/deadman_validate_producer_bridge.py --drama-dir data/dramas/huangnian
python3 tools/check_publication_safety.py
cd frontend && npm test && npm run build
```
