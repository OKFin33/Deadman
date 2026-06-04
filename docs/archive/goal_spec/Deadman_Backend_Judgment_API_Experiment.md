# Deadman Backend Judgment API Experiment Goal Spec

> Status: ready for `/goal` execution  
> Repo: `/Users/okfin3/project/GitHub/OKFin33/OSeria-Alter`  
> Product: Branch 3 / Deadman / `要是我来`  
> Date: 2026-05-24

## Goal Prompt

Paste this into the target execution thread:

```text
/goal
Execute the contract in /Users/okfin3/project/GitHub/OKFin33/OSeria-Alter/docs/goal_spec/Deadman_Backend_Judgment_API_Experiment.md.

Build the first experimental Deadman backend judgment API. It must load the promoted runtime data under data/dramas/huangnian/, expose health/catalog/moment lookup endpoints, and expose a POST judgment endpoint that takes Drama Context Pack + Moment Pack + user action and returns a structured “要是我来” result. Use a deterministic-first judgment path so the demo works without LLM keys; leave clear seams for a later LLM adapter but do not require provider calls. Do not touch ArcForge Runtime backend except for read-only reference. Do not implement frontend ingestion yet. Add tests, run verification, and append the required [Deadman] dev-log entry.

Before editing or running scripts, read the contract file and treat it as the source of truth.
```

## Why This Goal Exists

We now have tracked runtime-readable data:

```text
data/dramas/huangnian/context.v0.1.json
data/dramas/huangnian/moments.v0.1.json
data/dramas/huangnian/manifest.v0.1.json
```

The next risk is whether the runtime can consume it:

```text
Drama Context Pack + Moment Pack + user action
  -> structured judgment result
  -> frontend can render the “要是我来” verdict
```

This goal is an API ingestion experiment, not the final LLM-powered causality
engine. The first version must run without API keys.

## Scope

In scope:

- Deadman-only backend module under `backend/`;
- FastAPI app factory;
- data loader for promoted `data/dramas/*` packs;
- deterministic judgment service;
- request/response models;
- tests;
- README/dev-log updates.

Out of scope:

- frontend integration;
- image generation;
- real LLM/provider calls;
- persistence of user choices;
- aggregate stats;
- auth;
- deployment config;
- modifying ArcForge `Runtime/` backend behavior.

## Required Endpoints

Base prefix:

```text
/api/deadman
```

Required endpoints:

```text
GET  /api/deadman/health
GET  /api/deadman/dramas
GET  /api/deadman/dramas/{drama_id}
GET  /api/deadman/dramas/{drama_id}/moments
GET  /api/deadman/dramas/{drama_id}/moments/{moment_id}
POST /api/deadman/judgment
```

Endpoint behavior:

- `health`: returns `{"status": "ok"}` and basic data load status.
- `dramas`: lists available promoted drama packs.
- `dramas/{drama_id}`: returns context and manifest summary.
- `moments`: returns frontend-friendly moment summaries for the player.
- `moments/{moment_id}`: returns full promoted moment pack.
- `judgment`: returns a structured result for preset or custom user action.

Do not mount this inside `Runtime/api.py` during this goal. Keep a standalone
Deadman app factory so later deployment can mount it deliberately.

## Request Shape

Add Pydantic models for:

```json
{
  "drama_id": "huangnian",
  "moment_id": "huangnian_ep12_m001",
  "action": {
    "source": "preset|custom",
    "text": "今晚分兔肉，先让四蛋确认自己也有份",
    "option_index": 0
  },
  "viewer_profile": {
    "tone": "friend",
    "risk_preference": "balanced"
  }
}
```

Validation rules:

- `drama_id` and `moment_id` must exist.
- `action.text` cannot be empty.
- preset `option_index`, when present, must point to the moment's default option.
- custom action is allowed but must remain local; overpowered or unsupported
  requests should be softened, not hard-rejected, unless the payload is invalid.

## Response Shape

The `judgment` response must be stable enough for frontend ingestion:

```json
{
  "drama_id": "huangnian",
  "moment_id": "huangnian_ep12_m001",
  "action": {
    "source": "preset",
    "text": "今晚分兔肉，先让四蛋确认自己也有份",
    "option_index": 0
  },
  "verdict": {
    "label": "稳，但别摊太大",
    "stance": "support|caution|reject_softly",
    "summary": "..."
  },
  "consequence": {
    "text": "...",
    "time_horizon": "current_scene_or_immediate_aftermath",
    "watch_flow_fit": "high|medium|low"
  },
  "canon_anchor": {
    "original_plot_note": "...",
    "safe_to_continue": true
  },
  "scores": {
    "爽度": 0,
    "可信度": 0,
    "风险": 0,
    "暴露度": 0,
    "关系冲击": 0,
    "回看顺滑度": 0
  },
  "result_card": {
    "mode": "fallback_card",
    "title": "...",
    "prompt": "..."
  },
  "judgment_basis": {
    "evidence_refs": [],
    "applied_constraints": [],
    "inference_notes": [],
    "warnings": []
  },
  "engine": {
    "mode": "deterministic_fallback",
    "schema_version": "deadman_judgment_result.v0.1"
  }
}
```

Field names may be Pythonic internally, but JSON output should preserve the
frontend-friendly structure above.

## Deterministic Judgment Policy

The deterministic path does not need to be smart enough for production. It must
prove ingestion and guardrails.

It should use:

- moment trigger type / optional modules;
- selected action text;
- default option index;
- `original_plot_note`;
- `canon_baseline`;
- drama context `core_constraints`;
- `judgment_guardrails`;
- evidence notes.

Minimum behavior:

1. For normal preset options:
   - return `stance: support` or `caution`;
   - produce a consequence grounded in the moment object/person/witness;
   - include the original plot note;
   - include evidence/inference separation.

2. For custom overpowered/unsupported actions:
   - return `stance: reject_softly` or `caution`;
   - explain that the action is accepted as an impulse but softened because it
     exceeds local evidence or hidden-system limits;
   - do not claim later episodes branch;
   - keep `safe_to_continue: true`.

3. For invalid ids/payloads:
   - return structured 404/422 errors.

Suggested overpowered keywords for v0.1 guardrail:

```text
无限, 全村, 直接公开系统, 杀光, 改写后续, 后面全部, 一键, 开挂, 暴富
```

## Implementation Requirements

Recommended files:

```text
backend/__init__.py
backend/api.py
backend/models.py
backend/pack_store.py
backend/judgment.py
backend/tests/__init__.py
backend/tests/test_judgment_api.py
```

Use existing root dependencies where possible:

```text
fastapi
pydantic
httpx / fastapi.testclient
```

Do not add a new third-party dependency unless strictly necessary.

Data loading:

- default data root should resolve to `data/dramas`;
- allow override via constructor/env only if easy;
- never read ignored `tmp/` artifacts during runtime request handling;
- do not rely on raw video files.

Error shape should be consistent:

```json
{
  "error": {
    "code": "moment_not_found",
    "message": "...",
    "retryable": false
  }
}
```

## Docs

Update:

```text
backend/README.md
```

Must explain:

- how to run the app locally;
- how to call the judgment endpoint with a curl example;
- deterministic demo/test output is intentional for this P0 API experiment;
- formal judgment must later return structured error on runtime/provider
  failure, not deterministic fallback;
- CABRuntime SDK integration is later work.

Append `.agent/dev-log.md` with `[Deadman]`.

## Verification Required

Run:

```bash
python3 -m py_compile backend/*.py backend/tests/*.py
python3 -m unittest Deadman.backend.tests.test_judgment_api -v
```

Also run one smoke call using `TestClient` or `curl` equivalent and report:

- health returns ok;
- dramas lists `huangnian`;
- moments returns 5 moments;
- judgment works for one preset action;
- judgment softens one overpowered custom action;
- invalid moment returns structured error.

Also verify:

- no MP4/MOV files were added;
- no `.env` or API keys were added;
- backend runtime does not read `tmp/`;
- `Runtime/` backend files were not modified.

If frontend files are not touched, do not run frontend tests in this goal.

## Acceptance Criteria

- Deadman backend app can be imported and tested independently.
- API loads `data/dramas/huangnian` promoted packs.
- Required endpoints exist and pass tests.
- `POST /api/deadman/judgment` returns structured result with verdict,
  consequence, canon anchor, scores, result card, judgment basis, and engine
  metadata.
- Deterministic fallback handles preset and custom actions.
- Overpowered custom action is softened rather than allowed to rewrite the
  whole drama.
- No provider keys or raw media dependencies are introduced.
- Dev-log records the work.

## Expected Final Report

The execution thread should report:

- files changed/created;
- endpoints implemented;
- verification commands/results;
- sample judgment response summary;
- known debt;
- recommended next step.

Recommended next step after this goal:

```text
connect frontend player bubble to POST /api/deadman/judgment using the promoted moment ids
```
