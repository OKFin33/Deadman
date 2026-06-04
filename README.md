# Deadman

Deadman is the internal codename for OSeria Branch 3 / `要是我来`: a
short-drama watching companion prototype.

The current UX core is:

```text
我想说一句。
```

The viewer is not choosing a story branch. The viewer is saying the line that
the scene made them want to say. The system stays light on the surface and
heavier underneath: reviewed scene packs, a resident companion runtime, and a
CABRuntime-backed formal judgment path with environment-specific readiness
gates.

## Repository Status

This standalone repo is the public-source candidate for the Deadman v0.3
baseline before the v0.4 UX-core iteration. It excludes local media files,
provider secrets, agent logs, and generated build artifacts.

Publication boundary docs start from:

- `PUBLICATION_REVIEW.md`
- `REPO_STRUCTURE.md`
- `docs/README.md`
- `docs/Publicization_Decision_Log_v0.1.md`
- `docs/Local_Development_Artifact_Policy_v0.1.md`
- `docs/V0_3_Completeness_Review_v0.1.md`
- `docs/Branch3_UX_Core_Pivot_Log_v0.1.md`
- `docs/Branch3_要是我来_PRD_v0.4_UX_Core.md`
- `docs/Submission_Material_Map_v0.1.md`

## Layout

| Path | Purpose |
| --- | --- |
| `REPO_STRUCTURE.md` | Repo-wide public/local file boundary and publication blockers |
| `Deadman/` | Compatibility namespace for historical `Deadman.*` imports |
| `frontend/` | Mobile-first React/Vite player and tomato companion UI |
| `backend/` | FastAPI Deadman APIs, viewer runtime, judgment adapter, CAB client |
| `data/` | Reviewed drama context, moment packs, schemas, and fixtures |
| `tools/` | Producer-side ARS scripts, graph tooling, validation, publication checks |
| `studio/` | Static producer-side Studio prototype |
| `assets/` | Static companion assets and public art |
| `docs/` | PRD, tech plans, producer contracts, reviews, and submission docs |
| `server.py` | Deployable FastAPI entrypoint that mounts Deadman routes |
| `ms_deploy.json` | ModelScope-style deployment env template, with secrets omitted |

## Documentation

Start from `docs/README.md`. It separates current entry points from historical
goal specs and local-only artifact references.

The short rule:

- current product/runtime contracts stay tracked;
- historical specs may stay tracked only with archive context;
- raw producer artifacts, local agent logs, media files, provider caches, and
  copied source-context folders stay ignored.

## Current Product Direction

The latest complete baseline before the UX-core pivot is:

```text
docs/Branch3_要是我来_PRD_v0.3.md
```

The standalone extraction has been checked against that baseline in:

```text
docs/V0_3_Completeness_Review_v0.1.md
```

The current source PRD is:

```text
docs/Branch3_要是我来_PRD_v0.4_UX_Core.md
```

Key direction:

- user-side UI stays one-level and lightweight;
- three preset strips become reviewed `mouthpiece_candidates`, not branch
  choices;
- Deadman runtime turns user choice into a governed runtime event;
- CABRuntime executes/checks the formal semantic event path;
- Deadman Studio produces and validates scene-grounded mouthpiece candidates.

## Local Development

Backend:

```bash
python3 -m pip install -r requirements.txt
uvicorn server:app --host 127.0.0.1 --port 7860
```

Frontend:

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5177
```

Open:

```text
http://127.0.0.1:5177/?branch3_player=1
```

## Runtime Modes

Formal mode uses CABRuntime:

```bash
DEADMAN_JUDGMENT_ENGINE=cab_runtime
```

The demo deterministic engine exists only for tests/demo fallback and must not
be claimed as formal judgment:

```bash
DEADMAN_JUDGMENT_ENGINE=demo_deterministic
```

Formal runtime failure must fail closed with a structured error. It must not
silently return deterministic/template judgment.

Do not claim formal CABRuntime judgment for a deployment unless the CABRuntime
readiness gate passes in that same environment.

## Media Boundary

This repository does not include local MP4/MOV media files. Public deployment
must either:

- configure an external media base URL, or
- provide registered local media files on the server outside git.

Do not commit:

- `.env`;
- provider keys;
- `tmp/`;
- `.agent/`;
- `local_artifacts/`;
- MP4/MOV/M4V files;
- raw provider traces;
- local cache/checkpoint outputs;
- `node_modules`;
- frontend/backend build outputs.

## Verification Pointers

Useful checks before publication:

```bash
python3 -m py_compile backend/*.py
python3 -m unittest discover -s backend/tests -v
python3 tools/ars/deadman_validate_producer_bridge.py
cd frontend && npm test && npm run build
python3 tools/check_publication_safety.py
```

Some checks require sibling CABRuntime or local media files and should be
reported honestly if unavailable in a clean public checkout.
