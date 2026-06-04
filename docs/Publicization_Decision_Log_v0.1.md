# Deadman Publicization Decision Log v0.1

> Status: owner decisions accepted  
> Date: 2026-06-05  
> Scope: standalone Deadman repo, before v0.4 development starts.

## Decisions

| Area | Decision | Execution consequence |
| --- | --- | --- |
| GitHub visibility | Start private, public only after final leak/public-claim scan. | Do not push public directly from the local baseline. |
| Baseline history | Make v0.3 pre-v0.4 baseline the first visible project state; v0.4 pivot becomes later iteration. | Initialize local git, commit/tag baseline, then start v0.4 branch. |
| Repo name | Keep `Deadman` as the internal/public repo codename for now. | Do not rename paths before v0.4. README explains the codename. |
| Historical docs | Keep useful history, but archive/generalize noisy sprint specs before public release. | `docs/goal_spec/` keeps selected current producer specs; noisy sprint specs move to `docs/archive/goal_spec/`. |
| Local media files | Keep all local short-drama videos in ignored paths. | `tmp/视频素材/` and MP4/MOV/M4V files stay gitignored. |
| Local media metadata | Do not delete local producer media metadata solely for publicization. | `producer_media` metadata may stay available for local recording/dev; public API redaction remains mandatory. |
| Public demo media | Use local ignored media for recording; use external media base URL only if a shareable public demo needs playable media. | `DEADMAN_MEDIA_BASE_URL` stays empty in tracked config until deployment-specific setup. |
| Deployment config | Keep sanitized deploy config, with blank secrets/private URLs. | `ms_deploy.json` may remain tracked if it contains no real provider key or private URL. |
| License | Do not add a broad permissive license until IP/media/asset boundaries are checked. | Public release can proceed as source-visible review repo, but not as broadly licensed open-source code yet. |
| CABRuntime | Keep CABRuntime as formal judgment mode, not bundled in this repo. | Public claims require CAB readiness evidence; `demo_deterministic` remains explicit demo/test fallback only. |
| Producer graph dependencies | Treat LangGraph as a declared producer-side dependency. | Clean verification should use a fresh environment that installs `requirements.txt`. |
| Studio | Keep `studio/` in the repo as a static producer-side prototype. | README must position it as prototype/producer surface, not user runtime. |
| GitHub Actions | Add after baseline, starting with safety + backend + frontend checks. | Producer graph CI can wait until dependency install is stable. |
| Local artifacts | Keep `.agent/`, `tmp/`, and `local_artifacts/` in the local checkout but ignored. | Local development remains complete; GitHub candidate list must stay clean. |
| Public claims | Keep submission/competition docs after refinement; delete or downgrade unverified claims. | Image generation, multi-drama runtime promotion, real aggregate stats, autonomous ingestion, and CABRuntime formal success are gated claims. |

## Media Metadata Clarification

The owner decision is to preserve local media metadata. The publicization rule
is therefore:

- do not commit raw video/audio media;
- keep media files under ignored paths;
- keep backend/public API redaction of producer-only metadata;
- do not treat local producer media metadata as a deletion blocker by itself;
- still run final safety checks for secrets, credentials, private URLs, and
  accidental media files before any push.
