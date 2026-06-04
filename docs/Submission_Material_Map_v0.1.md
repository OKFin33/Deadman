# Deadman Submission Material Map v0.1

> Product: Deadman / `要是我来`  
> Purpose: locate current submission, review, and implementation materials  
> Date: 2026-05-29

## How To Use

This file answers the practical question: "Where do we find the material for
review, documentation, recording, or implementation?"

The column "Where to find it" is evidence-based from the standalone Deadman
repository. Mentions of the old Runtime host are historical source-workspace
context, not a current dependency of this standalone package.

## Core Product Documents

| Needed material | Where to find it | Current status | Notes |
| --- | --- | --- | --- |
| Current UX-core PRD | `docs/Branch3_要是我来_PRD_v0.4_UX_Core.md` | Current | Defines the post-pivot user mind: "我想说一句" as lightweight emotional mouthpiece interaction, with heavier producer/runtime logic underneath. |
| v0.3 baseline PRD | `docs/Branch3_要是我来_PRD_v0.3.md` | Pre-v0.4 baseline | Complete baseline before the UX-core pivot. Use with `docs/V0_3_Completeness_Review_v0.1.md`. |
| Previous full PRD | `docs/Branch3_要是我来_PRD_v0.2.md` | Superseded | Useful history, but does not fully include the latest Deadman Studio / LangGraph producer design. |
| Zero-context producer brief | `docs/Deadman_Studio_Zero_Context_Product_Brief_v0.1.md` | Current for external review | Explains why the producer side exists and why LangGraph belongs there. |
| Competition technical document draft | `docs/Competition_Technical_Doc_Draft_v0.1.md` | Feishu-ready technical draft | Good for module analysis, flowchart, schedule, AI disclosure, and claim boundaries. |
| Android APK delivery plan | `docs/Android_APK_Delivery_Plan_v0.1.md` | Current delivery decision | Makes Android APK + FastAPI backend the primary P0 submission route; Web remains fallback. |
| P0 mobile UX checklist | `docs/P0_Mobile_UX_Acceptance_Checklist_v0.1.md` | Current acceptance checklist | Use for visual/interaction acceptance before recording. |

## User-Side Runtime Materials

| Needed material | Where to find it | Current status | Notes |
| --- | --- | --- | --- |
| Resident companion tech plan | `docs/Resident_Companion_Runtime_Tech_Plan_v0.1.md` | Current implementation plan | Owns viewer session, event API, CAB integration boundary, companion policy, FriendVoiceComposer, and one-narrative result surface. |
| Canonical user-side frontend | `frontend/` | Current canonical package | Standalone Vite React app and Android APK shell source via Capacitor. |
| User-side app entry | `frontend/src/App.tsx` | Implemented | Catalog and direct player entry. |
| Player interaction surface | `frontend/src/player/Branch3PlayerDemo.tsx` | Implemented P0 | Vertical player, marker, companion bubble, preset/custom action, result/error display. |
| Companion state machine | `frontend/src/companion/tomatoCompanionMachine.ts` | Implemented P0 | `idle`, notice, bubble, thinking, verdict, error, dismissed. `runout` remains an unused optional asset state. |
| Companion assets and CSS | `frontend/src/companion/` and `assets/public/assets/branch3/companion/` | Implemented P0 | Source code lives under `frontend/src/companion/`; static avatar assets live under `assets/public/`. |
| Frontend API client | `frontend/src/api/deadmanApi.ts` and `frontend/src/api/deadmanRuntimeApi.ts` | Implemented P0 | `deadmanApi.ts` handles catalog/legacy judgment; `deadmanRuntimeApi.ts` handles viewer session events and runtime result surfaces. |
| Legacy host bridge | Original OSeria-Alter workspace only | Historical compatibility bridge | Not part of the standalone Deadman public package. Deadman owns the canonical frontend here. |
| Android APK shell | `frontend/android/` and `frontend/capacitor.config.ts` | P0 delivery shell | Generated Capacitor Android project. APK build must set `VITE_DEADMAN_API_BASE_URL` to a reachable backend. |

## Backend And Runtime Pack Materials

| Needed material | Where to find it | Current status | Notes |
| --- | --- | --- | --- |
| Deadman API app | `backend/api.py` | Implemented P0 | Health, dramas, moments, media, judgment endpoints. |
| Headless companion runtime | `backend/companion_runtime.py`, `backend/runtime_models.py`, `backend/viewer_session.py`, `backend/friend_voice.py` | Implemented P0 | Event API, in-memory viewer session, backend notice throttling, FriendVoiceComposer, failure-only retry, and structured companion result/error wrapper. |
| Deployment mount | `server.py` | Implemented P0 | Mounts Deadman API into the deployable FastAPI app. |
| Judgment service | `backend/judgment.py` and `backend/runtime_client.py` | Implemented with two modes | Configured formal mode is `cab_runtime`, but deployment claims require the CAB readiness gate to pass in that environment. `DEADMAN_JUDGMENT_ENGINE=demo_deterministic` is an explicit demo/test fallback, not formal judgment. |
| Pack loader | `backend/pack_store.py` | Implemented P0 | Loads tracked runtime packs under `data/dramas`. |
| Adapter mapper | `backend/adapter_mapping.py` | Implemented contract bridge | Maps promoted Huangnian v0.1 moments to v0.3 typed adapter input. |
| Backend tests | `backend/tests/` | Implemented | Use to protect API and adapter mapping behavior. |
| Runtime packs | `data/dramas/huangnian/` | Current P0 demo data | Contains context, manifest, moments, media registry, reviewed evidence. |
| Data schemas | `data/schemas/` | Current contracts | Includes judgment adapter input/output, visual result schemas, moment field schemas. |
| Media serving contract | `data/dramas/huangnian/media_registry.v0.1.json` and `/api/deadman/media/{drama_id}/{episode_id}` | Implemented P0 | Public API redacts producer-local paths. Clean deployment needs `DEADMAN_MEDIA_BASE_URL` or server-local registered media. |

## Producer-Side Materials

| Needed material | Where to find it | Current status | Notes |
| --- | --- | --- | --- |
| Producer bridge minimum flow | `docs/Producer_Bridge_Minimum_Flow_v0.1.md` | Current baseline | CLI/report path from local MP4s to runtime pack. |
| Producer tools | `tools/ars/` | Implemented scripts | Prepare assets, register media, build windows, mine candidates, cluster, review, publish, validate. |
| Producer tool README | `tools/ars/README.md` | Current command reference | Includes current Huangnian rerun sequence. |
| Deadman Studio implementation contract | `docs/Deadman_Studio_Implementation_Contract_v0.1.md` | Current implementation contract | Single engineering boundary for LangGraph runner state, nodes, artifacts, pause/resume, LLM extension, and verification. |
| LangGraph producer base spec | `docs/goal_spec/Deadman_LangGraph_Producer_Pipeline_v0.1.md` | Planned executable spec | Wraps existing CLI/scripts as LangGraph nodes. |
| LLM producer extension | `docs/goal_spec/Deadman_LangGraph_Producer_LLM_Extension_v0.1.md` | Planned extension | Adds LLM semantic mining, LLM-as-judge screening, and LLM pack drafting before human review. |
| Deadman Studio product brief | `docs/Deadman_Studio_Zero_Context_Product_Brief_v0.1.md` | Current external explanation | Best entry for reviewers who do not know the producer-side design. |
| Producer validation gate | `tools/ars/deadman_validate_producer_bridge.py` | Implemented | Must pass before claiming runtime pack is consumable. |
| Submission readiness gate | `tools/ars/deadman_check_submission_readiness.py` | Implemented | Final local readiness check. Use `--require-cab-runtime` to validate the formal CABRuntime path. |
| Submission runbook | `docs/Submission_Readiness_Runbook_v0.1.md` | Current | Recording URL, media deployment contract, stop conditions. |

## Field, Schema, And Evaluation Materials

| Needed material | Where to find it | Current status | Notes |
| --- | --- | --- | --- |
| Moment Field Minimum Set | `docs/Moment_Field_Minimum_Set_v0.3.md` | Current field contract | Current minimum field set after multi-drama induction. |
| Moment Causality Pack draft | `docs/Moment_Causality_Pack_v0.3_Draft.md` | Current draft | Typed field/subkey shape for moment-level judgment. |
| Field demand cluster report | `docs/Field_Demand_Cluster_Report_v0.3.md` | Current evidence | Explains field-demand clusters. |
| Red-team report | `docs/Field_Minimum_Red_Team_v0.1.md` and `docs/Field_Minimum_Red_Team_Findings_v0.1.md` | Current validation evidence | Required typed-subkey patch was applied. |
| Backend adapter mapping report | `docs/Backend_Adapter_Mapping_v0.1.md` | Current bridge evidence | Explains v0.1 promoted moments to v0.3 typed input. |
| Visual interface prep | `docs/Visual_Result_Interface_Prep_v0.1.md` | Current boundary | Provider not connected; visual cannot be proof. |
| Migration evidence | `docs/Migration_Human_Review_Yunmiao_Lihun_v0.1.md` | Evidence only | Yunmiao/Lihun are not runtime-promoted demos. |

## Source And Local Materials

| Needed material | Where to find it | Current status | Notes |
| --- | --- | --- | --- |
| Local short-drama MP4s | `tmp/视频素材/` | Local ignored files | Not committed. Used for recording and producer analysis. |
| Huangnian ARS outputs | `tmp/ars_huangnian_analysis/` | Local ignored artifacts | Source windows, ASR, keyframes, candidate/review scratch. |
| Yunmiao/Lihun ARS outputs | `tmp/ars_yunmiao_analysis/`, `tmp/ars_lihun_analysis/` | Local ignored artifacts | Used for field induction evidence, not runtime promotion. |
| Recording URL generator | `tools/ars/deadman_print_recording_urls.py` | Implemented | Prints local Vite recording URLs without committing raw media. |

## Claim Boundaries For Review

- Configured formal backend judgment mode is `cab_runtime`.
- `demo_deterministic` is only an explicit demo/test fallback via
  `DEADMAN_JUDGMENT_ENGINE=demo_deterministic`.
- Do not claim CABRuntime judgment for a deployment unless
  `deadman_check_submission_readiness.py` or
  `deadman_check_submission_readiness.py --require-cab-runtime` passes in that
  environment.
- Clean tracked deployment config may declare `DEADMAN_JUDGMENT_ENGINE=cab_runtime`;
  any formal claim requires a usable CABRuntime checkout and a passing readiness
  gate in the same environment.
- Image generation provider is not connected.
- Generated/fallback visuals cannot be used as proof.
- P0 does not generate a continuing alternate branch timeline.
- Yunmiao and Lihun are migration evidence, not runtime-promoted demos.
- Deadman Studio producer workflow can use LangGraph; user-side runtime should
  stay player-first and synchronous/error-visible.
- Primary contest delivery is Android APK frontend + FastAPI backend. The
  mobile Web frontend remains a fallback allowed by solo-participant rules.
