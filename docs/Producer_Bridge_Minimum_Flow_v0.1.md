# Producer Bridge Minimum Flow v0.1

> Product: Deadman / `要是我来`  
> Status: v0.1 flow; acceptable to revise after tool/UI work  
> Date: 2026-05-25

## Purpose

The producer bridge proves that Deadman can turn organizer short-drama material
into runtime-consumable interaction packs.

P0 does not need a polished creator platform. It needs a reproducible path from
local videos and ARS evidence to reviewed packs consumed by the player.

## Minimum Flow

```text
local MP4s in ignored tmp/
  -> media registry
  -> ASR / timeline windows / candidates / clusters
  -> human review
  -> Drama Context Pack
  -> Moment Causality Packs
  -> published runtime data
  -> player consumes moments
```

## Inputs

Allowed local inputs:

```text
tmp/视频素材/{drama}/
tmp/ars_*/
```

Tracked source contracts:

```text
tools/ars/
data/schemas/
docs/Moment_Causality_Pack_v0.3_Draft.md
docs/Moment_Field_Minimum_Set_v0.3.md
```

Do not commit:

- MP4/MOV/M4V;
- raw provider output;
- `.env`;
- API keys;
- local absolute media paths in runtime-facing fields.

## Step 1: Register Media

Purpose: create a stable episode index without copying videos into tracked
paths.

Current tool surface:

```text
tools/ars/deadman_register_media.py
```

Required tracked output:

```text
data/dramas/{drama_id}/media_registry.v0.1.json
```

Runtime-facing fields should use logical URLs or dev-server paths. Local paths
may exist only in `producer_media` metadata and must not be required by the
player/backend.

Current runtime media convention:

```text
/api/deadman/media/{drama_id}/{episode_id}
```

The endpoint serves only episodes registered in the media registry and does not
expose the underlying local path. Public `media-registry` API responses redact
`producer_media`; CLI tools still read the tracked file directly when producer
metadata is needed.

## Step 2: Build Evidence

Purpose: produce enough source windows for candidate node mining.

Evidence can come from:

- Doubao/Volcano ASR when approved and configured;
- local ASR fallback for experiments;
- keyframe extraction;
- transcript windows;
- existing ignored ARS outputs.

P0 rule: ASR/OCR/keyframes are evidence hints, not runtime truth. Promotion
requires human review.

## Step 3: Mine Candidate Nodes

Current tool surfaces:

```text
tools/ars/deadman_build_timeline_windows.py
tools/ars/deadman_mine_candidates.py
tools/ars/deadman_cluster_candidates.py
```

Candidate table should include:

- drama and episode;
- source time window;
- hook candidate;
- user impulse;
- mechanism cluster;
- candidate option actions;
- evidence refs;
- fields likely required;
- `needs_human_review: true`.

## Step 4: Human Review

Human review selects nodes that are safe to publish.

Review must verify:

- timestamp is correct enough for player trigger;
- scene summary matches actual episode;
- user impulse is emotionally legible;
- options are not overpowered or nonsensical unless intentionally routed;
- required fields are present;
- source refs are publish-safe;
- result does not imply continuous alternate branch.

Yunmiao and Lihun remain migration evidence until this review is done.

## Step 5: Publish Packs

Current tool surface:

```text
tools/ars/deadman_publish_p0_bridge.py
```

Required tracked outputs:

```text
data/dramas/{drama_id}/context.v0.1.json
data/dramas/{drama_id}/moments.v0.1.json
data/dramas/{drama_id}/manifest.v0.1.json
data/dramas/{drama_id}/evidence/
```

Published moments must include:

- stable `moment_id`;
- `interaction_window`;
- companion hook;
- preset options;
- source refs that do not require ignored tmp dereferences;
- result media slots or explicit fallback policy;
- review state.

## Step 6: Runtime Consumption Check

The player/backend should prove:

- drama manifest loads;
- moments endpoint returns published moments;
- interaction windows drive notices;
- preset/custom submissions reach judgment endpoint;
- result or structured error is visible in the bubble.

Current producer-pack validation gate:

```bash
python3 tools/ars/deadman_validate_producer_bridge.py \
  --drama-dir data/dramas/huangnian \
  --report tmp/ars_huangnian_analysis/producer_bridge_validation_report.md
```

This gate checks manifest/context/moments/media-registry/reviewed-node
consistency, promoted-node review status, runtime-safe source refs, and the
absence of raw media/env files in tracked drama data.

## Local Recording URLs

Tracked packs use deployment-slot video URLs such as
`/assets/branch3/dramas/huangnian/huangnian_ep12.mp4`; raw MP4 files stay in
ignored local `tmp/` paths. For local demo recording, generate a URL that passes
the producer-only Vite `@fs` URL through the existing player query parameter:

```bash
python3 tools/ars/deadman_print_recording_urls.py \
  --episode-id huangnian_ep12
```

Product consequence: the recording operator can play the real downloaded MP4 in
Vite without committing media files and without exposing local paths through the
runtime API.

For the deployment entrypoint, the player should normally use the same-origin
`/api/deadman/media/...` URL returned by the Deadman moments endpoint. If the
server does not have the ignored local media files, configure
`DEADMAN_MEDIA_BASE_URL` to an external media host before recording/submission.
The Deadman health endpoint reports this readiness explicitly:

```bash
curl http://127.0.0.1:7860/api/deadman/health
```

`media.deployment_ready` must be true before claiming a shareable deployed demo.

## Reproducible CLI Sequence

For the current `huangnian` P0 pack, the minimal rerun path is:

```bash
python3 tools/ars/deadman_prepare_drama_assets.py \
  --drama-id huangnian \
  --drama-title "荒年全村啃树皮，我有系统满仓肉" \
  --video-dir "tmp/视频素材/荒年" \
  --analysis-dir tmp/ars_huangnian_analysis

python3 tools/ars/deadman_register_media.py \
  --media-index tmp/ars_huangnian_analysis/media_index.json \
  --episode-ids huangnian_ep03,huangnian_ep04,huangnian_ep06,huangnian_ep07,huangnian_ep12

python3 tools/ars/deadman_build_timeline_windows.py
python3 tools/ars/deadman_mine_candidates.py --max-candidates <candidate_recall_budget>
python3 tools/ars/deadman_cluster_candidates.py
```

Human review is the required gate between candidates and packs. For the current
P0 pack, reviewed inputs are:

```text
tmp/ars_huangnian_analysis/review/huangnian_demo_nodes.v0.1.json
tmp/ars_huangnian_analysis/review/huangnian_candidates.reviewed.v0.1.json
```

After review:

```bash
python3 tools/ars/deadman_build_drama_context.py \
  --drama-id huangnian \
  --reviewed-demo-nodes tmp/ars_huangnian_analysis/review/huangnian_demo_nodes.v0.1.json \
  --reviewed-candidates tmp/ars_huangnian_analysis/review/huangnian_candidates.reviewed.v0.1.json \
  --summaries docs/Byte_AI_Allowed_Drama_Summaries_2026-05-23.md \
  --out-dir tmp/ars_huangnian_analysis/drama_context \
  --promote \
  --promote-dir data/dramas/huangnian

python3 tools/ars/deadman_publish_p0_bridge.py

python3 tools/ars/deadman_validate_producer_bridge.py \
  --drama-dir data/dramas/huangnian \
  --report tmp/ars_huangnian_analysis/producer_bridge_validation_report.md

python3 tools/ars/deadman_print_recording_urls.py \
  --episode-id huangnian_ep12
```

Product consequence: the future agent has a pass/fail checkpoint. If the final
validator fails, the pack is not ready to claim as runtime-consumable, even if
individual scripts ran.

## Producer Surface P0

The P0 producer surface can be CLI/report based.

Minimum acceptable producer UX:

- one command or documented sequence to register media;
- one command or documented sequence to publish reviewed nodes;
- one markdown/json review table per migration drama;
- clear distinction between ignored evidence and tracked runtime pack.

Do not build a full admin dashboard before viewer P0 is stable.

## Acceptance

The producer bridge is acceptable when:

- a new drama folder can be registered without committing video files;
- reviewed nodes can be promoted into tracked data;
- runtime pack fields are publish-safe;
- ignored tmp paths do not leak into viewer-facing API fields;
- local media paths are nested under producer-only metadata;
- `deadman_validate_producer_bridge.py` passes on the promoted drama dir;
- ARS outputs are explicitly marked as evidence until reviewed;
- the process is documented enough for a subagent to rerun.
