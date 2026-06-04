# Deadman Repo Structure

> Status: pre-v0.4 local baseline organization  
> Purpose: make the standalone checkout usable as both a normal public GitHub
> project and a complete local development workbench.

## Public Candidate Tree

These paths are intended to be normal tracked project content after the
publication review is complete.

| Path | Role | Public status |
| --- | --- | --- |
| `README.md` | Project entry point | public |
| `REPO_STRUCTURE.md` | Repo map and file-management boundary | public |
| `PUBLICATION_REVIEW.md` | Pre-publication checklist and blockers | public until final release, then may stay as history |
| `server.py` | Deployable FastAPI entrypoint | public |
| `requirements.txt` | Backend Python dependencies | public |
| `ms_deploy.json` | ModelScope-style deployment template with blank secrets | public after final review |
| `backend/` | Deadman API, judgment/runtime services, tests | public |
| `frontend/` | React/Vite mobile viewer and companion UI | public |
| `studio/` | Static producer-side Studio prototype | public if positioned as demo/prototype |
| `tools/` | Producer and publication tooling | public, with provider keys env-only |
| `assets/` | Static companion assets | public |
| `data/` | Sanitized schemas, evals, and runtime-readable drama packs | public |
| `docs/` | Current PRDs, runtime contracts, producer contracts, and history | public after archive selection |
| `Deadman/` | Compatibility namespace for old `Deadman.*` imports | public while compatibility imports are needed |

## Local-Only Tree

These paths stay in the same local checkout for development continuity but are
not part of the public GitHub project.

| Path | Why it exists locally | Git status |
| --- | --- | --- |
| `tmp/` | Local media, ASR, keyframes, producer runs, review scratch, screenshots | ignored |
| `.agent/` | Local agent bridge brief, dev log, wiki queue | ignored |
| `local_artifacts/` | Copied source-context docs from the original workspace | ignored |
| `.env`, `.env.*` | Provider/deployment secrets | ignored |
| `node_modules/`, `dist/`, `build/` | Generated dependency/build outputs | ignored |
| `*.mp4`, `*.mov`, `*.mp3`, provider traces, DB/checkpoints | Raw media or local execution state | ignored |

## Repo Boundary Rules

1. Runtime code must not read ignored `tmp/` artifacts during viewer requests.
2. Producer tools may read/write `tmp/`, but promoted runtime packs must be
   validated before handoff.
3. Provider credentials are environment variables only; never put actual values
   in docs, fixtures, scripts, traces, or deployment JSON.
4. Local media may be registered for recording, but public API responses must
   redact producer-only file paths.
5. Owner decision: local producer media metadata does not need to be deleted
   solely for publicization. Raw media files remain ignored, and public API
   redaction remains mandatory.
6. Historical docs may mention ignored artifact paths as provenance. Current
   entry docs should not expose machine-specific absolute paths.
7. Generated files should not be committed unless the directory README names
   them as a deliberate static artifact, as with `studio/assets/`.

## Publication Gate

Before any `git add`, commit, push, or public release:

```bash
python3 tools/check_publication_safety.py
python3 tools/ars/deadman_validate_producer_bridge.py
```

Then inspect the Git candidate list:

```bash
git status --short
git ls-files --cached --others --exclude-standard
```

If `tmp/`, `.agent/`, `local_artifacts/`, `.env`, raw media, provider traces, or
generated build outputs appear, stop and fix `.gitignore` or the file layout
before staging.

## Current Publicization Status

The repo is usable as the local v0.3 baseline and as a public-source candidate
after the publication gate passes. The baseline commit/tag exists locally; no
remote is configured by default.

Remaining non-code release decisions:

- whether to publish without an open-source license for now;
- whether to attach external hosted media separately;
- whether to keep `PUBLICATION_REVIEW.md` as visible provenance after the first
  public push.

Local producer media metadata is intentionally retained for developer and
recording workflows. Machine-specific Vite `@fs` paths and raw videos stay out
of git, and public API redaction is still required.

Historical sprint specs have been archived under `docs/archive/goal_spec/`.
`docs/goal_spec/` keeps only the selected current producer graph specs.
