# Deadman End-to-End Ingestion and Player P0 Goal Spec

> Status: ready for `/goal` execution  
> Repo: `/Users/okfin3/project/GitHub/OKFin33/OSeria-Alter`  
> Product: Branch 3 / Deadman / `要是我来`  
> Source drama for P0: `荒年全村啃树皮，我有系统满仓肉`  
> Date: 2026-05-24

## Goal Prompt

Paste this into the target execution thread:

```text
/goal
Execute the contract in /Users/okfin3/project/GitHub/OKFin33/OSeria-Alter/docs/goal_spec/Deadman_EndToEnd_Ingestion_Player_P0.md.

Build the first end-to-end Deadman P0 bridge from producer-side local MP4 registration to runtime player consumption. The demo must let a producer register/upload several local short-drama MP4s, run or reuse existing ARS artifacts, review/publish a pack with real interaction windows, source provenance that does not depend on ignored tmp paths, and result-media slots. The viewer player must consume the promoted pack, show the companion state changes during the configured interaction window, open the current bubble UI on tap, post preset/custom actions to the judgment API, and render the natural-language result. Preserve the current UI shape; do not redesign the bubble. Keep raw media/provider outputs in ignored tmp paths, do not commit MP4/MOV files or secrets, add tests, run verification, and append the required [Deadman] dev-log entry.

Before editing or running scripts, read the contract file and treat it as the source of truth.
```

## Product Target

The P0 demo should prove this UX:

```text
Producer side:
upload/register several short-drama videos
  -> generate or reuse ARS analysis
  -> review intervention nodes
  -> publish Drama Context Pack + Moment Causality Packs
  -> prefill preset option image slots

Viewer side:
play the MP4
  -> companion idles half-hidden
  -> companion notices an interaction window, for example 65s to 85s
  -> user taps companion
  -> bubble opens with preset options and custom input
  -> backend computes a result
  -> player renders natural-language consequence
  -> preset actions can show pregenerated images
  -> custom actions have a realtime-image seam with text-only fallback
```

P0 does not need perfect model quality. It must prove that the production
artifact can drive the consumption surface without hard-coded moments.

## Current State

Already implemented:

- `data/dramas/huangnian/context.v0.1.json`
- `data/dramas/huangnian/moments.v0.1.json`
- `data/dramas/huangnian/manifest.v0.1.json`
- `backend` FastAPI app with pack loading and deterministic judgment.
- `frontend` player consuming `/api/deadman/dramas/huangnian/moments`
  and posting `/api/deadman/judgment`.

Known gaps to close:

1. promoted moments lack real `interaction_window` fields, so the player uses
   fallback marker times;
2. promoted source refs still point at ignored `tmp/...` files;
3. producer upload/register is not productized;
4. preset option image slots and custom realtime image seam do not exist;
5. manifest status has been corrected, but future scripts should maintain it.

## Scope

In scope:

- producer-side local media registry;
- a minimal producer bridge command or internal surface that can create/update a
  P0 drama pack from local media and reviewed ARS artifacts;
- promoted `interaction_window` fields;
- publish-safe provenance copied or summarized under tracked `Deadman/data`;
- result-media schema slots for preset and custom actions;
- backend API additions needed by the player and producer bridge;
- frontend player consumption of `interaction_window` and result media slots;
- tests and smoke checks.

Out of scope:

- full cloud upload/storage service;
- auth;
- payment/credits;
- production-grade video transcoding;
- automatic candidate quality guarantee without human review;
- final UI redesign;
- final LLM causality quality;
- final image-generation quality;
- mobile native wrapper.

## Architecture Boundary

Do not mix this with ArcForge `Runtime` backend logic.

Allowed write surfaces:

```text
backend/
frontend/
tools/ars/
data/
docs/
docs/goal_spec/
.agent/dev-log.md
```

Runtime frontend bridge may be touched only to keep the existing compatibility
host working. Do not change ArcForge runtime API contracts.

## Required Functional Split

### Producer Side

#### 1. Media Registration

Provide a deterministic local registry step for P0.

Required output:

```json
{
  "schema_version": "deadman_media_registry.v0.1",
  "drama_id": "huangnian",
  "title": "荒年全村啃树皮，我有系统满仓肉",
  "episodes": [
    {
      "episode_id": "huangnian_ep01",
      "title": "第1集",
      "local_media_path": "tmp/视频素材/荒年/xxx.mp4",
      "runtime_video_url": "/assets/branch3/dramas/huangnian/huangnian_ep01.mp4",
      "duration_seconds": 0,
      "checksum": "",
      "status": "registered"
    }
  ]
}
```

Raw MP4 files stay ignored. For the demo, it is acceptable to serve local videos
from the dev server through a copied or symlinked ignored public path, but do
not commit the actual videos.

#### 2. ARS Reuse or Run

The producer pipeline may reuse existing artifacts for `荒年`:

```text
tmp/ars_huangnian_analysis/
```

If media exists and artifacts are missing, the pipeline should be able to run
the current ARS scripts in order:

```text
extract audio / ASR artifacts if available
build timeline windows
mine candidates
cluster mechanism buckets
prepare candidate review table
```

Do not require provider keys during normal tests.

#### 3. Review and Publish

Only reviewed nodes may be promoted.

For P0, use the current 5 reviewed `huangnian` moments unless the user supplies
a new review file. The publish step must:

- write promoted context/moments/manifest under `data/dramas/{drama_id}`;
- preserve stable `moment_id`;
- add real or fallback-but-explicit `interaction_window`;
- add publish-safe `source_refs`;
- add `result_media`;
- update `manifest.ingestion_status`.

#### 4. Image Slots

For each default option, add a result-media slot:

```json
{
  "option_index": 0,
  "status": "placeholder|pregenerated",
  "image_url": "/assets/branch3/dramas/huangnian/moments/huangnian_ep12_m001/option_0.webp",
  "prompt": "",
  "source": "manual_placeholder|provider_generated|not_generated"
}
```

P0 may use placeholder assets if provider image generation is not ready. The
schema must not block later Doubao/Volcano image generation.

Custom action image policy:

```json
{
  "status": "not_requested",
  "mode": "realtime_generate_or_text_only_fallback",
  "timeout_ms": 8000
}
```

### Consumer Side

#### 1. Player Pack Consumption

The player must consume `interaction_window`, not hard-coded fallback times
when the pack provides valid values.

Required frontend behavior:

- before `notice_at_seconds`: companion is idle;
- during `start_seconds <= t <= end_seconds`: companion can show notice;
- after `end_seconds`: notice expires unless the bubble is already open;
- clicking the companion opens the existing bubble UI;
- closing the bubble resumes normal watching.

#### 2. Action Submission

For preset options:

- submit `{source: "preset", text, option_index}`;
- show natural-language result from `judgment.consequence.text`;
- display pregenerated/placeholder image slot if present.

For custom input:

- submit `{source: "custom", text}`;
- show natural-language result from `judgment.consequence.text`;
- call the image-generation seam only if implemented and configured;
- otherwise show text-only fallback, not a broken image.

#### 3. Result Rendering

Current bubble UI can remain. Add only minimal rendering surfaces:

- verdict label;
- consequence text;
- original plot anchor;
- optional result image;
- visible text-only fallback when no image is available.

## Schema Additions

Add these fields to promoted moment packs.

### `interaction_window`

```json
{
  "notice_at_seconds": 65,
  "start_seconds": 65,
  "end_seconds": 85,
  "source": "reviewed_ars|manual_p0_fallback",
  "confidence": "low|medium|high",
  "pause_policy": "pause_on_invite",
  "expire_behavior": "return_to_idle"
}
```

Rules:

- `notice_at_seconds <= start_seconds <= end_seconds`;
- window length should normally be 8 to 30 seconds;
- fallback times must be labeled `manual_p0_fallback`;
- do not hide fallback timing as source evidence.

### Publish-Safe `source_refs`

Do not leave runtime-critical refs that require ignored `tmp/...` files.

Preferred shape:

```json
{
  "source_refs": {
    "reviewed_demo_node": "data/dramas/huangnian/evidence/reviewed_demo_nodes.v0.1.json#huangnian_ep12_m001",
    "transcript_snippets": [
      {
        "id": "huangnian_ep12_u001",
        "episode_id": "huangnian_ep12",
        "start_ms": 0,
        "end_ms": 0,
        "text": "",
        "source": "sanitized_asr_snippet"
      }
    ],
    "keyframe_refs": [
      {
        "id": "huangnian_ep12_k001",
        "episode_id": "huangnian_ep12",
        "time_seconds": 0,
        "description": "keyframe reference only; not psychological proof"
      }
    ]
  }
}
```

It is acceptable to keep raw local paths in `producer_refs`, but not as runtime
evidence the backend/frontend must dereference.

### `result_media`

```json
{
  "result_media": {
    "preset_options": [
      {
        "option_index": 0,
        "status": "placeholder",
        "image_url": "",
        "prompt": "",
        "source": "not_generated"
      }
    ],
    "custom_action": {
      "status": "not_requested",
      "mode": "realtime_generate_or_text_only_fallback",
      "timeout_ms": 8000
    }
  }
}
```

Backend judgment responses should echo the matching media slot when available.

## Backend Requirements

Add or update models/endpoints as needed.

Minimum additions:

- moment summaries include `interaction_window` and `result_media` summary;
- full moment endpoint returns publish-safe evidence and media fields;
- judgment response includes optional media result:

```json
{
  "media": {
    "type": "image",
    "status": "placeholder|pregenerated|not_available|generation_pending|generation_failed",
    "image_url": "",
    "prompt": "",
    "source": ""
  }
}
```

If adding this field to `JudgmentResponse`, keep backward compatibility with
current tests.

## Frontend Requirements

Update `frontend` player:

- load `interaction_window`;
- derive marker positions from `notice_at_seconds` or `start_seconds`;
- show notice only in the active window;
- use backend-provided media slot in the result card;
- keep the current bubble layout and companion assets;
- retain local fallback behavior only when the backend pack lacks the new
  fields, and label it in dev diagnostics or code comments.

Update `Runtime/frontend` bridge tests if the shared Deadman component changes.

## Producer Surface Requirement

P0 can be a thin internal page, CLI, or both. Choose the smallest implementation
that proves the product chain.

Acceptable P0:

- CLI script registers local media and publishes pack fields;
- optional internal web page lists registered episodes and promoted moments.

Not required for P0:

- drag-and-drop upload polish;
- cloud object storage;
- async job queue UI.

## Verification

Run at minimum:

```bash
python3 -m py_compile tools/ars/*.py backend/*.py backend/tests/*.py
python3 -m unittest Deadman.backend.tests.test_judgment_api -v
cd frontend && npm test
cd frontend && npm run build
cd Runtime/frontend && npm test
cd Runtime/frontend && npm run build
```

Add tests for:

- promoted moment has valid `interaction_window`;
- runtime refs do not require `tmp/...` dereference;
- moment summary endpoint returns `interaction_window`;
- player uses pack timing when present;
- preset action result can include a media slot;
- custom action has text-only fallback when no image provider is configured.

Smoke checks:

- start backend on `127.0.0.1:8013`;
- start frontend on `127.0.0.1:5175`;
- open player at mobile widths `390x844`, `393x852`, `430x932`;
- verify companion idle/notice/open/result states;
- verify one preset action returns text and media slot;
- verify one custom action returns text even without image.

## Acceptance Criteria

This goal is complete only when:

- producer-side command/surface can register local MP4 metadata without
  committing media;
- promoted `huangnian` pack has valid `interaction_window` for all 5 P0 moments;
- promoted runtime evidence does not require ignored `tmp` files;
- promoted moment packs include `result_media`;
- backend APIs expose the new fields;
- frontend consumes timing from the pack instead of fallback times when present;
- judgment result renders natural language and handles media slot fallback;
- tests/builds pass;
- `.agent/dev-log.md` has a `[Deadman]` entry;
- no MP4/MOV, `.env`, API keys, raw provider payloads, or secrets are added.

## Report Back

Final report must include:

- files changed;
- exact commands run and results;
- whether timing is source-derived or manual P0 fallback;
- whether evidence refs are publish-safe;
- whether image slots are placeholders or generated;
- remaining debt before competition submission.

## Next Suggested Goal

After this, the next goal should be one of:

```text
Deadman_LLM_Judgment_Adapter_P0
Deadman_Image_Generation_Provider_Probe
Deadman_Producer_UI_Polish_P0
```

