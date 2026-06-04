# Local Development Artifact Policy v0.1

> Scope: standalone Deadman extraction  
> Date: 2026-06-03  
> Purpose: keep local development context complete without polluting the public
> GitHub package.

## Local-Only Artifact Boundary

The local checkout may contain development artifacts that are useful for
rebuilds, audits, recording, and producer-side debugging. These artifacts are
kept under ignored paths and must not be committed:

| Path | Purpose | Git status |
| --- | --- | --- |
| `tmp/` | ASR outputs, keyframes, contact sheets, candidate mining, producer runs, local videos, submission screenshots | ignored |
| `.agent/` | local agent bridge brief, dev log, wiki queue | ignored |
| `local_artifacts/` | copied source-context docs from the original OSeria-Alter workspace | ignored |
| `.env`, `.env.*` | local provider credentials and deployment secrets | ignored, not copied |

Current local copy source is the original OSeria-Alter working checkout. In
local notes this may resolve to machine-specific absolute paths, but public docs
should treat it symbolically:

```text
${SOURCE_OSERIA_ALTER_ROOT}/tmp/
${SOURCE_OSERIA_ALTER_ROOT}/.agent/
${SOURCE_OSERIA_ALTER_ROOT}/docs/
${SOURCE_OSERIA_ALTER_ROOT}/Runtime/docs/
```

The copied source `.env` is intentionally excluded. Provider keys must stay in
shell/platform secret management only.

## Public Repo Boundary

A normal public GitHub version may include:

- source code under `backend/`, `frontend/`, `tools/ars/`, `studio/`;
- reviewed runtime data under `data/`;
- public static assets under `assets/`;
- public docs under `docs/`;
- sanitized config examples such as `frontend/env.example`;
- `ms_deploy.json` only when secret values are blank.

A public GitHub version must not include:

- Doubao / Volcengine / Ark / DeepSeek / OpenAI keys;
- `.env` or local secret files;
- `tmp/`, `.agent/`, `local_artifacts/`;
- MP4/MOV/M4V/MP3/WAV media;
- raw provider traces or caches;
- `node_modules`, build outputs, generated Android public assets;
- local APK/AAB/IPA packages;
- private certificates or key files.

## Publication Gate

Before initializing git, staging, committing, or pushing, run:

```bash
python3 tools/check_publication_safety.py
```

Expected result:

```text
PUBLICATION SAFETY CHECK PASSED
```

Then inspect the candidate file list from git before any commit:

```bash
git status --short
git ls-files --cached --others --exclude-standard
```

If any ignored local path appears in the candidate list, stop and fix
`.gitignore` before continuing.

## Key Handling Rule

The Doubao speech key is never a repo asset. The ASR scripts must read it from
environment variables only:

```text
DOUBAO_SPEECH_API_KEY
VOLC_ASR_API_KEY
VOLC_API_KEY
```

Do not put those values in tracked docs, shell scripts, deployment JSON, test
fixtures, provider caches, or screenshots. If a real key is ever accidentally
written into any local artifact, rotate the key before public upload.
