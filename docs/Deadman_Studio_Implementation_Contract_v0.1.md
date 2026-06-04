# Deadman Studio Implementation Contract v0.1

> Product: Deadman / `要是我来`  
> Surface: Deadman Studio producer side  
> Status: implementation contract; base runner, all mock/Ark LLM nodes, and cache/batch/parallel optimization paths implemented  
> Date: 2026-06-01  
> Primary goal: make the producer workflow implementable without turning
> Deadman Studio into a second runtime platform.

## 0. Position

Deadman Studio is the offline or semi-offline production surface that turns raw
short-drama material into reviewed, runtime-safe packs for the user-side mobile
player.

This contract is the implementation bridge between:

- product brief: `docs/Deadman_Studio_Zero_Context_Product_Brief_v0.1.md`
- current CLI baseline: `docs/Producer_Bridge_Minimum_Flow_v0.1.md`
- base LangGraph goal spec:
  `docs/goal_spec/Deadman_LangGraph_Producer_Pipeline_v0.1.md`
- LLM extension goal spec:
  `docs/goal_spec/Deadman_LangGraph_Producer_LLM_Extension_v0.1.md`

Product consequence: after this contract, implementation should be a bounded
runner and artifact job system, not another architecture debate.

## 1. Non-Negotiable Boundaries

Deadman Studio owns:

- local producer asset preparation;
- media registration;
- source-window construction;
- deterministic candidate recall;
- optional LLM semantic mining and judging;
- human review pause/resume;
- pack drafting from reviewed evidence;
- publishing reviewed runtime packs;
- validation and final reporting.

Deadman Studio does not own:

- user-side judgment runtime;
- CABRuntime execution semantics;
- companion chat runtime;
- image generation provider integration;
- ASR provider reruns by default;
- arbitrary shell execution;
- fully automatic publication;
- runtime promotion for every tested drama.

Product consequence: Studio can prove an AI production line without claiming
real-time user runtime responsibility.

## 2. Implementation Unit

First implementation file:

```text
tools/ars/deadman_run_producer_graph.py
```

Supporting files allowed in first implementation:

```text
tools/ars/deadman_producer_graph_contract.py
tools/ars/deadman_producer_graph_artifacts.py
tools/ars/deadman_producer_graph_llm.py
data/schemas/producer_graph/
data/fixtures/producer_graph/
```

Do not refactor the existing ARS scripts into pure functions in v0.1. The graph
wraps them as child CLI commands and records exact argv.

Product consequence: the existing reproducible CLI path stays trustworthy while
LangGraph adds resumability, stage naming, and review gates.

## 3. External API Assumptions Checked

Checked against official LangGraph Python docs on 2026-06-01:

- The Studio runner uses LangGraph Graph API / `StateGraph`, not the Functional
  API. The workflow is a named producer graph with shared state, conditional
  routing, and future UI-readable node status; it is not just a checkpointed
  Python script.
- `interrupt()` requires a checkpointer and stable `thread_id` to resume the same
  paused run.
- Resume should pass `Command(resume=...)` using the same thread id.
- Code before `interrupt()` inside the interrupted node may run again on resume.
- SQLite checkpointer support lives in `langgraph-checkpoint-sqlite` and is
  suitable for local/experimental workflows.

Implementation rule: first build a cold-resume spike before implementing the
full producer runner. The spike must lock the `StateGraph` compile/invoke/resume
shape and update this contract if the selected package version requires a
different call pattern.

Product consequence: if pause/resume cannot be proven with the real selected API,
we rewrite the runner contract instead of faking LangGraph checkpointing with
manual state files.

## 4. Dependency Contract

Add only:

```text
langgraph>=1.2,<2
langgraph-checkpoint-sqlite>=3.1,<4
```

Not allowed in the base runner:

- LangSmith dependency;
- LangChain Agent abstraction;
- provider SDK;
- image provider SDK;
- CABRuntime SDK dependency;
- database server requirement.

The base graph should use SQLite checkpointer under:

```text
tmp/deadman_producer_runs/{run_id}/checkpoint.sqlite
```

For v0.1 CLI usage, use one stable LangGraph `thread_id` per `run_id`:

```text
thread_id = deadman-producer:{run_id}
```

Product consequence: local producer runs are restartable without making the P0
demo require infrastructure that the current submission does not need.

## 5. State Model

The graph state is a production job ledger.

The runner should define `ProducerState` as a `TypedDict` for `StateGraph`.
Individual nodes return partial state updates; reducers decide how shared maps
and lists merge.

Minimum typed state:

```python
from typing import Annotated, Literal, TypedDict

class ProducerState(TypedDict):
    run_id: str
    drama_id: str
    drama_title: str
    analysis_dir: str
    video_dir: str
    drama_dir: str
    status: ProducerRunStatus
    current_node: str
    node_statuses: Annotated[dict[str, ProducerNodeStatus], merge_dict]
    artifact_paths: Annotated[dict[str, str], merge_dict]
    review_decision: Literal["pending", "approve", "reject"]
    validation_result: Literal["not_run", "pass", "failed"]
    errors: Annotated[list[ProducerRunError], append_errors]
```

Allowed terminal run statuses:

```text
failed
validation_failed
rejected_by_human_review
pass
```

Allowed non-terminal run statuses:

```text
planned
running
waiting_for_review
publishing
waiting_for_llm
llm_failed
skipped_by_config
```

Node-local statuses:

```text
planned
running
waiting_for_review
blocked_by_prior_failure
failed
pass
```

State rules:

- `artifact_paths` is the only way a downstream node discovers upstream outputs.
- Node functions may read tracked repo files and ignored run artifacts, but may
  not scan arbitrary directories.
- Errors must contain `node`, `code`, `message`, `retryable`, and `artifact_refs`.
- `merge_dict` must merge shallow dictionaries without dropping existing keys.
  If a node needs to delete or invalidate an artifact path, it must write an
  explicit tombstone value and explain it in `errors`.
- `append_errors` must append new errors and preserve old ones. Do not replace
  the whole error list from a node return.
- Scalar fields such as `status`, `current_node`, `review_decision`, and
  `validation_result` use replace semantics.
- The manifest and LangGraph checkpoint must agree on `run_id`, `thread_id`,
  `current_node`, and terminal status. If they disagree, stop.

StateGraph routing rules:

- The base graph uses fixed edges until `human_review_gate`.
- `prepare_human_review` writes or verifies the stable review request and marks
  the run `waiting_for_review` before the interrupting node starts.
- `human_review_gate` routes to `build_drama_context` on approve.
- `human_review_gate` routes to terminal `rejected_by_human_review` on reject.
- Any node-level failure routes to `final_report` if report generation is safe;
  otherwise the run stops at terminal `failed`.
- The LLM extension inserts nodes by graph construction mode, not by branching
  inside `mine_candidates`.

Product consequence: a future operator can inspect one manifest and know where
the job stopped, what was produced, and whether it is safe to resume.

## 6. Artifact Root

Every run writes ignored artifacts under:

```text
tmp/deadman_producer_runs/{run_id}/
```

Required run artifacts:

```text
producer_job_manifest.json
command_log.jsonl
review_request.json
final_report.md
checkpoint.sqlite
```

Allowed optional artifacts:

```text
llm_semantic_candidates.json
llm_candidate_judgment.json
llm_drama_context_draft.json
llm_moment_pack_drafts.json
provider_trace_redacted.jsonl
llm_batch_manifest.json
llm_semantic_miner_chunks/
llm_candidate_judge_chunks/
```

Allowed cross-run cache root:

```text
tmp/deadman_llm_cache/v0.1/
```

Cache entries are ignored producer artifacts, not runtime data. A cache entry may
store schema-valid normalized node output plus cache metadata, but it must not
store raw provider request, raw provider response, prompt text, API keys, or
local absolute paths. The current run artifact must still be written under
`tmp/deadman_producer_runs/{run_id}/` so downstream nodes do not read the cache
directly.

Never write these to tracked runtime pack files:

- raw provider request or response;
- local absolute paths;
- `tmp/` refs;
- `/@fs` refs;
- `.env`;
- API key fragments;
- prompt text;
- producer-only score/debug fields.

Product consequence: Studio can keep rich production evidence without leaking it
into public player data.

## 7. Base Graph Nodes

The base graph is provider-free and wraps existing CLI scripts.

```text
prepare_assets
register_media
build_timeline_windows
mine_candidates
cluster_candidates
prepare_human_review
human_review_gate
build_drama_context
publish_p0_bridge
validate_producer_bridge
final_report
```

### 7.1 `prepare_assets`

Purpose: convert local MP4s into ignored producer assets.

Inputs:

- `video_dir`
- `analysis_dir`
- `drama_id`
- `drama_title`

Child command:

```bash
python3 tools/ars/deadman_prepare_drama_assets.py \
  --drama-id <drama_id> \
  --drama-title <drama_title> \
  --video-dir <video_dir> \
  --analysis-dir <analysis_dir>
```

Outputs:

- `<analysis_dir>/media_index.json`
- ignored audio/keyframe/contact-sheet artifacts

Failure codes:

- `asset_video_dir_missing`
- `asset_media_index_missing`
- `asset_prepare_failed`

Side-effect rule: do not pass `--force` in the graph runner.

### 7.2 `register_media`

Purpose: produce runtime-safe media registry.

Inputs:

- `<analysis_dir>/media_index.json`
- `drama_dir`

Child command:

```bash
python3 tools/ars/deadman_register_media.py \
  --drama-id <drama_id> \
  --title <drama_title> \
  --media-index <analysis_dir>/media_index.json \
  --out <drama_dir>/media_registry.v0.1.json \
  --episode-ids huangnian_ep03,huangnian_ep04,huangnian_ep06,huangnian_ep07,huangnian_ep12
```

Outputs:

- `<drama_dir>/media_registry.v0.1.json`

Failure codes:

- `media_index_invalid`
- `media_required_episode_missing`
- `media_register_failed`

Side-effect rule: local media paths may exist only under `producer_media`.

### 7.3 `build_timeline_windows`

Purpose: create timestamped source windows.

Inputs:

- media index;
- normalized ASR outputs when available;
- keyframe refs.

Child command:

```bash
python3 tools/ars/deadman_build_timeline_windows.py \
  --analysis-dir <analysis_dir> \
  --out-dir <analysis_dir>/candidates \
  --drama-id <drama_id> \
  --drama-title <drama_title> \
  --version v0.1
```

Outputs:

- `<analysis_dir>/candidates/<drama_id>_windows.v0.1.json`

Failure codes:

- `windows_media_index_missing`
- `windows_build_failed`

Side-effect rule: missing ASR may lower `source_quality`, but the manifest must
record that reduced quality.

### 7.4 `mine_candidates`

Purpose: deterministic broad recall and audit evidence pool. This node is no
longer the final screening authority for Studio UX entry points.

Inputs:

- source windows;
- current mechanism ontology in `deadman_mine_candidates.py`.

Child command:

```bash
python3 tools/ars/deadman_mine_candidates.py \
  --candidate-dir <analysis_dir>/candidates \
  --max-candidates <candidate_recall_budget> \
  --drama-id <drama_id> \
  --drama-title <drama_title> \
  --version v0.1 \
  --out-json <analysis_dir>/candidates/<drama_id>_candidates.v0.1.json \
  --out-md <analysis_dir>/candidates/<drama_id>_candidates.v0.1.md
```

Outputs:

- `<analysis_dir>/candidates/<drama_id>_candidates.v0.1.json`
- `<analysis_dir>/candidates/<drama_id>_candidates.v0.1.md`

Failure codes:

- `candidate_windows_missing`
- `candidate_mine_failed`

Budget policy: `candidate_recall_budget` scales from source media count by
default (`DEADMAN_CANDIDATE_RECALL_PER_SOURCE`) with min/max safety bounds. The
current 20-video Huangnian smoke resolves to 80, but 80 is not a product
constant.

Authority: proposes, ranks, and preserves replayable evidence. Never approves,
and never decides the final shortlist.

### 7.5 `cluster_candidates`

Purpose: group candidates by mechanism and field pressure.

Inputs:

- source windows;
- candidates.

Child command:

```bash
python3 tools/ars/deadman_cluster_candidates.py \
  --candidate-dir <analysis_dir>/candidates \
  --analysis-dir <analysis_dir> \
  --drama-id <drama_id> \
  --drama-title <drama_title> \
  --version v0.1 \
  --windows <analysis_dir>/candidates/<drama_id>_windows.v0.1.json \
  --candidates <analysis_dir>/candidates/<drama_id>_candidates.v0.1.json \
  --out-json <analysis_dir>/candidates/<drama_id>_mechanism_buckets.v0.1.json \
  --out-md <analysis_dir>/candidates/<drama_id>_mechanism_buckets.v0.1.md \
  --field-md <analysis_dir>/candidates/<drama_id>_field_hypotheses.v0.1.md \
  --run-report <analysis_dir>/candidates/run_report.md
```

Outputs:

- `<analysis_dir>/candidates/<drama_id>_mechanism_buckets.v0.1.json`
- `<analysis_dir>/candidates/<drama_id>_mechanism_buckets.v0.1.md`
- `<analysis_dir>/candidates/<drama_id>_field_hypotheses.v0.1.md`
- `<analysis_dir>/candidates/run_report.md`

Failure codes:

- `cluster_candidates_missing`
- `cluster_failed`

Authority: explains field pressure. Never extends runtime schema by itself.

### 7.6 `prepare_human_review`

Purpose: persist the review request before the interrupting node starts.

Inputs:

- deterministic candidate table;
- mechanism buckets;
- field hypotheses;
- expected reviewed demo node path;
- expected reviewed candidate path.

Outputs:

- `tmp/deadman_producer_runs/{run_id}/review_request.json`
- manifest state with `status = waiting_for_review`
- `human_review_gate` node status set to `waiting_for_review`

Implementation requirements:

- compute `request_hash` from the whitelisted stable payload;
- write `review_request.json` if absent, or verify the existing hash;
- fail with `review_request_drift` instead of overwriting a different request;
- route to `human_review_gate` after the waiting state is checkpointed.

Product consequence: the operator can close the terminal after `start` and still
see a truthful waiting state in both the checkpointed graph and the manifest.

### 7.7 `human_review_gate`

Purpose: pause the graph before publishable state changes.

Inputs:

- deterministic candidate table;
- mechanism buckets;
- optional LLM reports;
- expected reviewed demo node path;
- expected reviewed candidate path.

Outputs:

- `tmp/deadman_producer_runs/{run_id}/review_request.json`

Implementation requirements:

- use LangGraph `interrupt()` for the pause;
- the interrupt payload must be JSON-serializable;
- resume must use `Command(resume=...)` with the same `thread_id`;
- because code before `interrupt()` may run again on resume, this node must only
  verify the already persisted review request before interrupting.

Execution order:

```text
verify persisted review_request hash
  -> interrupt(payload)
  -> on resume, validate resume payload
  -> if approve, verify reviewed artifacts and route to build_drama_context
  -> if reject, set terminal rejected_by_human_review
```

Idempotency rule:

- If `review_request.json` does not exist, write it and record `request_hash`.
- If it exists, recompute the would-be request and verify hash equality.
- If hash differs, fail with `review_request_drift` instead of overwriting.

Hash input whitelist:

- `run_id`
- `drama_id`
- `drama_title`
- base graph mode: `base` or `llm`
- ordered node list up to `human_review_gate`
- candidate table artifact path and content hash
- mechanism bucket artifact path and content hash
- field hypotheses artifact path and content hash when present
- LLM semantic candidates artifact path and content hash when present
- LLM candidate judgment artifact path and content hash when present
- deterministic candidate count
- LLM candidate count when present
- review policy version
- expected reviewed demo node path
- expected reviewed candidate path

Hash exclusions:

- `generated_at`, wall-clock timestamps, or duration fields;
- absolute local paths;
- provider raw trace paths;
- stdout/stderr summaries;
- current process id;
- checkpoint sqlite path;
- reviewer note;
- any field that can change between `start` and `resume` without changing the
  substance of the review request.

Allowed resume payload:

```json
{
  "decision": "approve",
  "reviewed_demo_nodes": "tmp/ars_huangnian_analysis/review/huangnian_demo_nodes.v0.1.json",
  "reviewed_candidates": "tmp/ars_huangnian_analysis/review/huangnian_candidates.reviewed.v0.1.json",
  "reviewer_note": "string"
}
```

Reject payload:

```json
{
  "decision": "reject",
  "reviewer_note": "string"
}
```

Reject is terminal for the current `run_id`. Re-review requires a new run id so
old rejected artifacts cannot be silently converted into a publishable run.

Failure codes:

- `review_request_drift`
- `review_resume_invalid`
- `review_artifact_missing`

Authority: only human review can approve candidates for publish.

### 7.7 `build_drama_context`

Purpose: turn reviewed evidence into context and moment pack source material.

Inputs:

- reviewed demo nodes;
- reviewed candidates;
- approved summary source;
- `drama_dir`.

Child command:

```bash
python3 tools/ars/deadman_build_drama_context.py \
  --drama-id <drama_id> \
  --reviewed-demo-nodes <reviewed_demo_nodes> \
  --reviewed-candidates <reviewed_candidates> \
  --summaries docs/Byte_AI_Allowed_Drama_Summaries_2026-05-23.md \
  --out-dir <analysis_dir>/drama_context \
  --promote \
  --promote-dir <drama_dir>
```

Outputs:

- `<analysis_dir>/drama_context/*`
- promoted context/moment source material under `<drama_dir>/`

Failure codes:

- `context_review_not_approved`
- `context_reviewed_artifact_missing`
- `context_build_failed`

Authority: builds from reviewed inputs only.

### 7.8 `publish_p0_bridge`

Purpose: publish runtime-readable pack files.

Inputs:

- media registry;
- reviewed demo nodes;
- reviewed candidates.

Child command:

```bash
python3 tools/ars/deadman_publish_p0_bridge.py \
  --drama-dir <drama_dir> \
  --reviewed-demo-nodes <reviewed_demo_nodes> \
  --reviewed-candidates <reviewed_candidates> \
  --media-registry <drama_dir>/media_registry.v0.1.json
```

Outputs:

- `<drama_dir>/manifest.v0.1.json`
- `<drama_dir>/context.v0.1.json`
- `<drama_dir>/moments.v0.1.json`
- `<drama_dir>/evidence/reviewed_demo_nodes.v0.1.json`

Failure codes:

- `publish_input_not_reviewed`
- `publish_media_registry_missing`
- `publish_failed`

Authority: writes tracked runtime pack files only from reviewed inputs.

### 7.9 `validate_producer_bridge`

Purpose: block unsafe runtime-facing artifacts.

Child command:

```bash
python3 tools/ars/deadman_validate_producer_bridge.py \
  --drama-dir <drama_dir> \
  --report <analysis_dir>/producer_bridge_validation_report.md
```

Outputs:

- `<analysis_dir>/producer_bridge_validation_report.md`
- manifest `validation_result`

Failure codes:

- `validation_failed`
- `validation_report_missing`

Authority: only this node can mark published runtime pack artifacts safe.

### 7.10 `final_report`

Purpose: write the operator and reviewer summary.

Inputs:

- manifest;
- command log;
- review request;
- validation report;
- final pack paths.

Outputs:

- `tmp/deadman_producer_runs/{run_id}/final_report.md`

The report must state:

- final status;
- node table;
- child commands;
- review decision;
- validation result;
- runtime pack paths;
- producer-only artifacts intentionally excluded;
- whether LLM enrichment ran, skipped, or failed.

Failure codes:

- `final_report_failed`

Authority: report only. It cannot change published runtime data.

## 8. LLM Extension Nodes

LLM nodes are optional in v0.1 and mandatory only for runs explicitly started
with `--enable-llm`.

Recommended order:

```text
mine_candidates
llm_semantic_miner
cluster_candidates
llm_candidate_judge
human_review_gate
llm_drama_context_draft
llm_moment_pack_draft
build_drama_context
publish_p0_bridge
```

### 8.1 Deterministic Retention

Do not delete deterministic recall.

Authority split:

| Layer | Authority |
| --- | --- |
| Deterministic recall | Stable replay baseline and cheap candidate recall. |
| LLM semantic miner | Primary semantic understanding and candidate proposal. |
| LLM candidate judge | Second-pass screening and failure-mode labels. |
| Human review gate | Only approval authority. |
| Validator | Runtime safety authority after publish. |

Product consequence: Studio can show what was reproducible, what the model
added, what the model rejected, and what a human approved.

### 8.2 `llm_semantic_miner`

Purpose: find semantically strong interaction moments that keyword recall missed
or underexplained.

Inputs:

- timeline windows;
- deterministic candidate table;
- mechanism ontology;
- Moment Field Minimum Set v0.3;
- drama title/context.

Output:

```text
tmp/deadman_producer_runs/{run_id}/llm_semantic_candidates.json
```

Required behavior:

- validate output JSON schema;
- distinguish `deterministic_enriched` from `llm_discovered`;
- mark uncertainty and evidence refs;
- never write runtime packs.

Current v0.1 implementation:

- available with `--enable-llm --mock-provider`;
- available with `--enable-llm` against Ark/OpenAI-compatible chat completions
  when Ark environment variables are present;
- writes `tmp/deadman_producer_runs/{run_id}/llm_semantic_candidates.json`;
- validates against
  `data/schemas/producer_graph/llm_semantic_candidates.v0.1.schema.json`;
- adds the semantic candidate artifact hash and candidate count to
  `review_request.json` when present;
- never writes runtime packs.

### 8.3 `llm_candidate_judge`

Purpose: semantic shortlist gate between deterministic recall and human review.

Inputs:

- deterministic candidates;
- semantic candidates;
- source windows;
- product constraints.

Output:

```text
tmp/deadman_producer_runs/{run_id}/llm_candidate_judgment.json
```

Required behavior:

- treat deterministic candidates as an input pool, not as a table that must be
  judged row by row;
- select only moments where a viewer would feel emotional fluctuation and want
  to speak up immediately for the "要是我来" product entry;
- output a small shortlist using `recommend` or `keep_for_review`; `reject` is
  allowed for provider compatibility, but omitted candidates simply remain
  audit-only recall evidence;
- label failure modes;
- preserve source artifacts;
- send the shortlist and policy to `review_request.json`.

Current v0.1 implementation:

- available with `--enable-llm --mock-provider`;
- available with `--enable-llm` against Ark/OpenAI-compatible chat completions
  when `ARK_API_KEY` and `ARK_MODEL` or `ARK_ENDPOINT_ID` are present in the
  environment;
- writes `tmp/deadman_producer_runs/{run_id}/llm_candidate_judgment.json`;
- validates against
  `data/schemas/producer_graph/llm_candidate_judgment.v0.1.schema.json`;
- receives deterministic recall candidates and semantic-miner candidates under
  dynamic pool budgets with provider safety caps;
- computes `shortlist_target` from source count and input-pool size by default,
  rather than using a fixed dataset-size assumption;
- accepts `LLM_CANDIDATE_JUDGE_SHORTLIST_LIMIT` only as an explicit operator
  override for a run;
- adds the LLM judgment artifact hash, decision summary, shortlist ids, and
  shortlist policy to `review_request.json`;
- never promotes runtime packs before human approval.

### 8.4 `llm_drama_context_draft`

Purpose: draft context material for producer review.

Output:

```text
tmp/deadman_producer_runs/{run_id}/llm_drama_context_draft.json
```

Required behavior:

- mark inferred fields as draft;
- preserve uncertainty;
- never overwrite tracked `context.v0.1.json` directly.

Current v0.1 implementation:

- runs only after `human_review_gate` approves;
- available with `--enable-llm --mock-provider`;
- available with `--enable-llm` against Ark/OpenAI-compatible chat completions
  when Ark environment variables are present;
- writes `tmp/deadman_producer_runs/{run_id}/llm_drama_context_draft.json`;
- validates against
  `data/schemas/producer_graph/llm_drama_context_draft.v0.1.schema.json`;
- normalizes provider scalar drift that is type-preserving in meaning, such as
  numeric confidence strings, before schema validation;
- never overwrites tracked context packs.

### 8.5 `llm_moment_pack_draft`

Purpose: draft Moment Pack fields for human-approved candidates.

Output:

```text
tmp/deadman_producer_runs/{run_id}/llm_moment_pack_drafts.json
```

Required behavior:

- use only approved candidate ids;
- keep hook/options viewer-language, not analysis labels;
- never claim future branch continuation;
- never use visual output as proof;
- never publish directly.

Current v0.1 implementation:

- runs only after `human_review_gate` approves;
- available with `--enable-llm --mock-provider`;
- available with `--enable-llm` against Ark/OpenAI-compatible chat completions
  when Ark environment variables are present;
- writes `tmp/deadman_producer_runs/{run_id}/llm_moment_pack_drafts.json`;
- validates against
  `data/schemas/producer_graph/llm_moment_pack_drafts.v0.1.schema.json`;
- forces every generated draft to `requires_human_review = true`;
- never publishes directly.

### 8.6 LLM Cache, Batching, And Parallelism Contract

This section defines production-side optimization. It must not change runtime
pack semantics, human review authority, or final artifact schemas.

#### 8.6.1 Optimization Order

Implement in this order:

1. cache at the shared `run_llm_json_node` boundary;
2. batching for `llm_candidate_judge`;
3. batching for `llm_semantic_miner`;
4. bounded chunk-level parallelism inside batched LLM nodes.

Do not parallelize the whole StateGraph in v0.1. The graph-level order stays
stable; optimization happens inside explicit LLM nodes.

#### 8.6.2 Cache Contract

Purpose: avoid paying latency/cost for identical producer-only LLM work across
reruns, resumes, and contract-only changes that do not affect the prompt or
schema.

Cache applies to:

- `llm_semantic_miner`;
- `llm_candidate_judge`;
- `llm_drama_context_draft`;
- `llm_moment_pack_draft`;
- future chunk calls inside those nodes.

Cache key input:

```text
node
chunk_id or "single"
provider
model
temperature
seed
schema_hash
prompt_hash
prompt_contract_version
source_artifact_hashes
normalizer_version
```

Rules:

- `prompt_hash` is computed from canonical JSON of the provider prompt, but the
  prompt text itself is never written to cache metadata or traces.
- `source_artifact_hashes` must include every upstream artifact whose content
  materially affects the prompt. Path strings alone are not enough.
- cache hit output must be schema-validated before it is copied into the current
  run artifact.
- cache hit must still write the normal current-run output path; downstream
  nodes never read cache paths directly.
- cache miss falls through to the provider and writes cache only after schema
  validation passes.
- failed provider calls, schema-invalid outputs, retry traces, raw provider
  payloads, and partial chunks are never cache entries.
- cache entries must be provider/model specific. A result from one model cannot
  satisfy another model's key.
- cache bypass must be explicit through environment config; bypassed runs still
  write regular artifacts and traces.

Cache trace statuses:

```text
cache_hit
cache_miss
cache_write
cache_bypass
cache_invalid
provider_retry
provider_failed
schema_invalid
pass
```

`provider_trace_redacted.jsonl` must record `cache_key_hash`, `node`,
`chunk_id`, `provider`, `model`, `status`, `latency_ms`, `token_usage`, and
`artifact_ref` when available. It must not record prompt text or key fragments.

#### 8.6.3 Batch Manifest Contract

Batched nodes write a run-local manifest:

```text
tmp/deadman_producer_runs/{run_id}/llm_batch_manifest.json
```

Required manifest fields:

```json
{
  "schema_version": "deadman_llm_batch_manifest.v0.1",
  "run_id": "string",
  "nodes": {
    "llm_semantic_miner": {
      "mode": "single|batched",
      "chunk_count": 0,
      "chunk_strategy": "episode|window_range|candidate_pool",
      "chunk_artifacts": [],
      "merge_artifact": "string",
      "merge_policy": {}
    },
    "llm_candidate_judge": {
      "mode": "single|batched",
      "chunk_count": 0,
      "chunk_strategy": "candidate_pool",
      "chunk_artifacts": [],
      "merge_artifact": "string",
      "merge_policy": {}
    }
  }
}
```

The review request must hash-lock the final merged LLM artifacts. If batching is
enabled, it must also include the batch manifest `content_hash` so the reviewer
can audit how merged outputs were produced.

#### 8.6.4 `llm_semantic_miner` Batching

Batch trigger:

- batch when `LLM_SEMANTIC_MINER_BATCH_MODE` is enabled, or when source windows
  exceed the configured single-prompt window cap;
- otherwise keep the existing single-call path.

Chunk strategy:

- primary: episode-level chunks;
- fallback: stable window-range chunks when an episode has too many windows;
- chunk ids must be stable: `semantic_ep_{episode_id}` or
  `semantic_window_{start_index}_{end_index}`.

Chunk output:

```text
tmp/deadman_producer_runs/{run_id}/llm_semantic_miner_chunks/{chunk_id}.json
```

Merge output remains:

```text
tmp/deadman_producer_runs/{run_id}/llm_semantic_candidates.json
```

Merge rules:

- normalize every chunk through the existing semantic candidate normalizer;
- drop candidates with missing source refs or missing evidence excerpt;
- dedupe by `semantic_candidate_id` when present;
- otherwise dedupe by `(episode_id, window_id, normalized hook, evidence hash)`;
- if duplicates conflict, keep the higher confidence item and merge source refs;
- preserve `origin`, `linked_candidate_id`, uncertainty, and failure modes;
- sort by confidence descending, then episode id, start time, candidate id;
- final merged artifact must validate
  `llm_semantic_candidates.v0.1.schema.json`;
- chunk artifacts are producer evidence only and must not appear in runtime
  packs.

Failure rule: if any required semantic chunk fails, the whole
`llm_semantic_miner` node fails unless the run was explicitly started with
LLM-skip behavior. Do not silently merge a partial semantic set.

#### 8.6.5 `llm_candidate_judge` Batching

Batch trigger:

- batch when selected judge input exceeds `LLM_CANDIDATE_JUDGE_BATCH_SIZE`;
- otherwise keep the existing single-call path.

Chunk strategy:

- construct the deterministic/semantic input pool first;
- compute the global `shortlist_target` before chunking;
- partition candidate pool by stable rank/source order;
- chunk ids must be stable: `judge_candidates_{start_index}_{end_index}`.

Chunk output:

```text
tmp/deadman_producer_runs/{run_id}/llm_candidate_judge_chunks/{chunk_id}.json
```

Merge output remains:

```text
tmp/deadman_producer_runs/{run_id}/llm_candidate_judgment.json
```

Chunk prompt rule:

- each chunk may return a local shortlist;
- each chunk must preserve original `candidate_id`;
- omitted chunk candidates remain audit-only recall evidence;
- chunk-local shortlist size is not the final product shortlist size.

Global merge rules:

- normalize every chunk through the existing candidate judgment normalizer;
- drop judgments whose `candidate_id` is not in the original input pool;
- dedupe by `candidate_id`;
- if duplicates conflict, decision priority is
  `recommend > keep_for_review > reject`, then higher confidence wins;
- global sort order is `recommend` first, confidence descending, deterministic
  rank ascending when available, source order, candidate id;
- apply global dynamic `shortlist_target` only after all chunk outputs are
  merged;
- final `decisions_summary`, `judgment_count`, `input_candidate_count`, and
  `shortlist_policy` must describe the merged artifact, not any chunk;
- final merged artifact must validate
  `llm_candidate_judgment.v0.1.schema.json`.

Failure rule: if any judge chunk fails, the whole `llm_candidate_judge` node
fails. Do not route a partial shortlist to human review.

#### 8.6.6 Chunk-Level Parallelism

Parallelism is allowed only inside batched LLM nodes.

Rules:

- default concurrency is `1`;
- concurrency must be bounded by `LLM_CHUNK_CONCURRENCY`;
- provider retry/backoff applies per chunk;
- merge order must be deterministic and independent of chunk completion order;
- trace records must include `chunk_id`;
- cache hits and provider calls can be mixed in one batched node;
- a chunk failure fails the parent node after retry exhaustion;
- no runtime pack is written from chunk outputs.

Allowed in v0.1 optimization:

- parallel chunks in `llm_semantic_miner`;
- parallel chunks in `llm_candidate_judge`.

Not allowed in v0.1 optimization:

- graph-level parallel routing around `human_review_gate`;
- parallelizing `llm_drama_context_draft` with `llm_moment_pack_draft`, because
  the moment-pack draft reads the context-draft summary;
- publishing before all required LLM chunks and human review are complete.

#### 8.6.7 Cache/Batch/Parallel Product Consequence

Cache reduces repeated-run cost, batching prevents large datasets from
overflowing prompt/context limits, and chunk-level parallelism reduces producer
waiting time without changing user-side runtime behavior. The user-side player
still reads only reviewed and validated runtime packs.

## 9. Provider Boundary

Provider integration is allowed only inside explicit LLM nodes.

Required first implementation order:

1. `--mock-provider` with local fixtures.
2. Schema validation over mock outputs.
3. One real provider adapter only after mock validation passes.

Current provider status:

- Mock providers are implemented for all four explicit LLM nodes:
  `llm_semantic_miner`, `llm_candidate_judge`,
  `llm_drama_context_draft`, and `llm_moment_pack_draft`.
- Ark providers are implemented for all four explicit LLM nodes through
  OpenAI-compatible chat completions and environment variables only.
- Ark is the current real-provider adapter because the competition-side
  endpoint is Doubao/Ark. This repo has no active Bailian-primary rule in
  `CLAUDE.md` or `AGENTS.md`; if another provider is added later, it must stay
  behind the same explicit LLM-node boundary.

Ark environment contract:

```text
ARK_API_KEY=<provided outside repo/logs>
ARK_MODEL=<endpoint id or model id>
# or ARK_ENDPOINT_ID=<endpoint id>
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
ARK_TEMPERATURE=0.0
# optional, only sent when explicitly configured:
ARK_SEED=<integer>
# optional compatibility extensions, off by default for Doubao-Seed:
ARK_ENABLE_JSON_RESPONSE_FORMAT=1
ARK_DISABLE_THINKING=1
ARK_TIMEOUT_SECONDS=120
LLM_PROVIDER_MAX_ATTEMPTS=3
LLM_PROVIDER_RETRY_BASE_SECONDS=1.0
# deterministic recall budget; exact override is optional:
DEADMAN_CANDIDATE_RECALL_LIMIT=<optional exact integer>
DEADMAN_CANDIDATE_RECALL_PER_SOURCE=4.0
DEADMAN_CANDIDATE_RECALL_MIN=20
DEADMAN_CANDIDATE_RECALL_MAX=400
# LLM input-pool safety caps; exact per-run overrides are optional:
LLM_CANDIDATE_JUDGE_POOL_LIMIT=<optional exact integer>
LLM_CANDIDATE_JUDGE_POOL_MAX=240
LLM_CANDIDATE_JUDGE_SEMANTIC_POOL_LIMIT=<optional exact integer>
LLM_CANDIDATE_JUDGE_SEMANTIC_POOL_MAX=120
# LLM shortlist budget; exact limit is optional, otherwise dynamic:
LLM_CANDIDATE_JUDGE_SHORTLIST_LIMIT=<optional exact integer>
LLM_CANDIDATE_JUDGE_SHORTLIST_MIN=3
LLM_CANDIDATE_JUDGE_SHORTLIST_MAX=60
LLM_CANDIDATE_JUDGE_SHORTLIST_PER_SOURCE=0.5
LLM_CANDIDATE_JUDGE_SHORTLIST_POOL_RATIO=0.10
# cross-run LLM cache:
DEADMAN_LLM_CACHE_MODE=read_write
DEADMAN_LLM_CACHE_ROOT=tmp/deadman_llm_cache/v0.1
# allowed values: off, read, write, read_write, refresh
# batching:
LLM_SEMANTIC_MINER_BATCH_MODE=auto
LLM_SEMANTIC_MINER_WINDOW_CAP=40
LLM_CANDIDATE_JUDGE_BATCH_SIZE=40
# chunk-level parallelism:
LLM_CHUNK_CONCURRENCY=1
```

The API key must never be written into this contract, source files, manifest,
final report, command log, review request, provider trace, or tracked data
packs.

Every real provider call must record in the manifest:

- provider;
- model;
- temperature;
- latency;
- token usage;
- schema validation status;
- retryability;
- redacted trace path.

Every cache hit or chunk call must record in the redacted trace:

- `node`;
- `chunk_id` or `single`;
- `status`;
- `cache_key_hash` when cache is consulted;
- `artifact_ref`;
- provider/model if a provider call occurred;
- latency and token usage if a provider call occurred.

Failure behavior:

```text
provider unavailable / exhausted timeout/429/5xx retry / schema invalid
  -> node status = llm_failed or skipped_by_config
  -> graph stops unless --allow-llm-skip was explicitly passed
  -> final report says LLM enrichment did not complete
```

Product consequence: model outages cannot silently become deterministic-only
success while the report claims AI semantic production happened.

`content_hash` stays in review requests as the tamper/audit lock. Human-readable
summary fields are additive; they do not replace artifact hashing.

Doubao-Seed-2.0-lite does not support `response_format.type=json_object` on the
competition Ark endpoint. The adapter therefore defaults to prompt-only strict
JSON and schema validation, with `response_format` and `thinking` extensions
available only through explicit opt-in environment flags.

## 10. CLI Contract

Base commands:

```bash
python3 tools/ars/deadman_run_producer_graph.py dry-run \
  --run-id langgraph_p0_dry \
  --verify-argv

python3 tools/ars/deadman_run_producer_graph.py start \
  --run-id langgraph_p0_smoke

python3 tools/ars/deadman_run_producer_graph.py resume \
  --run-id langgraph_p0_smoke \
  --review-decision approve
```

LLM commands:

```bash
python3 tools/ars/deadman_run_producer_graph.py dry-run \
  --run-id langgraph_llm_dry \
  --enable-llm \
  --verify-argv

python3 tools/ars/deadman_run_producer_graph.py start \
  --run-id langgraph_llm_mock \
  --enable-llm \
  --mock-provider

ARK_API_KEY=... ARK_MODEL=... \
python3 tools/ars/deadman_run_producer_graph.py start \
  --run-id langgraph_llm_ark \
  --enable-llm
```

Required CLI options:

```text
--run-id
--drama-id
--drama-title
--analysis-dir
--video-dir
--drama-dir
--enable-llm
--mock-provider
--allow-llm-skip
--verify-argv
--review-decision approve|reject
--reviewed-demo-nodes
--reviewed-candidates
```

`resume` and `spike-resume` must restore graph-affecting configuration from
the existing run manifest for the given `--run-id`, including graph mode,
provider mode, artifact paths, and reviewed artifact paths. The operator should
not have to repeat `--enable-llm`, `--mock-provider`, or path flags during human
review resume; the only new resume decision input is `--review-decision` plus an
optional `--reviewer-note`.

Default P0 values:

```text
drama_id=huangnian
drama_title=荒年全村啃树皮，我有系统满仓肉
analysis_dir=tmp/ars_huangnian_analysis
video_dir=tmp/视频素材/荒年
drama_dir=data/dramas/huangnian
```

## 11. Manifest Contract

`producer_job_manifest.json` must include:

```json
{
  "run_id": "string",
  "thread_id": "deadman-producer:string",
  "status": "planned",
  "drama_id": "huangnian",
  "drama_title": "荒年全村啃树皮，我有系统满仓肉",
  "graph": {
    "mode": "base|llm",
    "node_order": [],
    "current_node": "",
    "node_statuses": {}
  },
  "paths": {
    "analysis_dir": "",
    "video_dir": "",
    "drama_dir": "",
    "checkpoint": "",
    "command_log": "",
    "review_request": "",
    "final_report": ""
  },
  "artifacts": {},
  "review": {
    "decision": "pending|approve|reject",
    "request_hash": "",
    "reviewer_note": ""
  },
  "llm": {
    "enabled": false,
    "provider": "",
    "model": "",
    "mock_provider": false,
    "allow_skip": false,
    "nodes": {}
  },
  "validation": {
    "status": "not_run|pass|failed",
    "report": ""
  },
  "errors": []
}
```

The manifest is not a replacement for the LangGraph checkpoint. It is the human
and tool-readable job ledger.

`review_request.json` and all LLM artifacts are runtime-validated against
producer graph schemas under:

```text
data/schemas/producer_graph/
```

## 12. Command Log Contract

`command_log.jsonl` appends one JSON record when a child process starts and one
terminal JSON record when it completes, fails, or times out. Writes use an
exclusive file lock so concurrent producer runs cannot interleave partial JSON
lines.

Minimum fields:

```text
run_id
node
argv
cwd
status
started_at
ended_at
duration_ms
exit_code
stdout_summary
stderr_summary
artifact_refs
```

Write the first command log record before process execution with
`status=started`. Append a second terminal record with `status=completed`,
`failed`, or `timeout`. If the process crashes before a terminal record is
written, the started record still proves what was attempted.

## 13. Failure Policy

All failures are fail-closed.

If a node fails:

- stop the graph;
- set run status to `failed` or `validation_failed`;
- preserve stdout/stderr summary;
- preserve partial artifacts;
- do not publish new runtime packs;
- do not substitute fallback outputs;
- write final report if possible.

Retryable failures:

- provider timeout;
- provider HTTP 429;
- provider HTTP 5xx;
- temporary file lock;
- child process timeout before confirmed mutation.

Non-retryable failures:

- review request drift;
- validation error;
- reviewed artifact missing after approval;
- runtime-facing local path leak;
- schema invalid after provider success;
- child process non-zero exit after mutation risk is unknown;
- secret or `.env` found in tracked data.

Product consequence: a broken production run is visible and recoverable, not
silently converted into a misleading demo asset.

## 14. Security And Hygiene

Do not commit:

- MP4/MOV/M4V;
- provider raw outputs;
- `.env`;
- API keys or key fragments;
- checkpoint databases;
- run artifacts under `tmp/`;
- local absolute paths in runtime-facing tracked JSON.

Check before claiming pass:

```bash
python3 tools/ars/deadman_validate_producer_bridge.py \
  --drama-dir data/dramas/huangnian

python3 tools/ars/deadman_check_submission_readiness.py
```

If CABRuntime formal mode is part of the claim:

```bash
python3 tools/ars/deadman_check_submission_readiness.py \
  --require-cab-runtime
```

## 15. Implementation Phases

### Phase A: Cold-Resume Spike

Goal: prove LangGraph pause/exit/resume with SQLite and the selected API.

Acceptance:

- graph pauses at a review node;
- process exits;
- fresh process resumes with the same `thread_id`;
- implementation uses Graph API / `StateGraph`, with reducer behavior proven for
  `node_statuses`, `artifact_paths`, and `errors`;
- node behavior accounts for code before `interrupt()` being rerun;
- `review_request.json` hash is stable across start/resume when review inputs do
  not change;
- checkpoint and manifest agree.

No production ARS scripts should run in this phase.

### Phase B: Base Runner Dry Run

Goal: build command/artifact plan without executing child scripts.

Acceptance:

- prints all base nodes;
- writes or prints manifest plan;
- does not modify tracked runtime packs;
- no child process launches.

### Phase C: Base Runner Start/Resume

Goal: wrap existing CLI scripts through human review.

Acceptance:

- `start` reaches `waiting_for_review`;
- `review_request.json` exists and is idempotent;
- `resume approve` runs context build, publish, validation, and final report;
- `resume reject` does not publish.

### Phase D: LLM Mock Provider

Goal: add LLM nodes with fixtures only.

Acceptance:

- LLM artifacts are schema-valid;
- review request shows deterministic/LLM disagreements or, for the first
  candidate-judge slice, LLM decision summary plus artifact hash;
- no provider call occurs;
- no runtime pack is modified before approval.

Current status: Phase D is implemented for all four explicit LLM nodes with
mock providers and schema validation.

### Phase E: Real Provider Adapter

Goal: one real model adapter for producer-only semantic work.

Acceptance:

- provider/model details are recorded;
- raw traces stay ignored and redacted;
- schema invalid output blocks the graph;
- final report clearly states whether LLM enrichment ran.

Current status: Phase E adapter support is implemented for all four explicit
LLM nodes through Ark environment variables. Calls default to
`ARK_TEMPERATURE=0.0`, optionally send `ARK_SEED` only when configured, retry
provider timeout/429/5xx failures, and write only redacted provider traces. Real
provider smoke requires operator-supplied env vars; secrets must not be written
into command logs, tracked files, or run artifacts.

### Phase F: Studio UI Or Approval API

Not in P0 runner scope.

Only start after the CLI/report loop is stable. The UI should read the same
manifest, review request, and final report artifacts instead of inventing a
parallel workflow.

### Phase G: LLM Cache, Batching, And Chunk Parallelism

Goal: make large producer runs cheaper and bounded without changing graph-level
authority.

Acceptance:

- `run_llm_json_node` supports schema-validated cache hits and cache writes;
- cache metadata records hashes and status, never prompt text, raw provider
  payloads, local absolute paths, or secrets;
- cache hit writes the normal current-run artifact and records `cache_hit` in
  `provider_trace_redacted.jsonl`;
- `llm_candidate_judge` supports chunked local judgments plus deterministic
  global merge and final dynamic shortlist;
- `llm_semantic_miner` supports episode/window chunks plus deterministic merge;
- chunk outputs remain ignored producer artifacts;
- final merged artifacts keep the existing public schema names and pass schema
  validation;
- `review_request.json` hash-locks merged LLM artifacts and the batch manifest
  when batching is enabled;
- `LLM_CHUNK_CONCURRENCY=1` and `LLM_CHUNK_CONCURRENCY>1` produce the same
  merged candidate ids for the same mock inputs;
- any required chunk failure fails the parent node instead of sending a partial
  shortlist to human review.

Current status: Phase G is implemented in
`tools/ars/deadman_run_producer_graph.py` with schema coverage in
`data/schemas/producer_graph/llm_batch_manifest.v0.1.schema.json` and
regression coverage in `tools/ars/tests/test_producer_graph.py`. The
current verified mock CLI replay writes cache once and then replays all four LLM
nodes from cache (`31` `cache_hit` trace records: `20` semantic chunks, `9`
candidate-judge chunks, `1` drama-context draft, `1` moment-pack draft).

## 16. Verification Matrix

Run for implementation regression:

```bash
python3 -m py_compile tools/ars/*.py
python3 tools/ars/deadman_run_producer_graph.py dry-run --run-id langgraph_p0_dry --verify-argv
python3 tools/ars/deadman_run_producer_graph.py start --run-id langgraph_p0_smoke
python3 tools/ars/deadman_run_producer_graph.py resume --run-id langgraph_p0_smoke --review-decision approve
python3 tools/ars/deadman_validate_producer_bridge.py --drama-dir data/dramas/huangnian
python3 tools/ars/deadman_check_submission_readiness.py
```

Additional Phase G verification:

```bash
python3 -m unittest discover tools/ars/tests -v
DEADMAN_LLM_CACHE_MODE=read_write python3 tools/ars/deadman_run_producer_graph.py start --run-id langgraph_cache_smoke --enable-llm --mock-provider
DEADMAN_LLM_CACHE_MODE=read python3 tools/ars/deadman_run_producer_graph.py start --run-id langgraph_cache_hit_smoke --enable-llm --mock-provider
LLM_CANDIDATE_JUDGE_BATCH_SIZE=20 LLM_CHUNK_CONCURRENCY=1 python3 tools/ars/deadman_run_producer_graph.py start --run-id langgraph_batch_serial_smoke --enable-llm --mock-provider
LLM_CANDIDATE_JUDGE_BATCH_SIZE=20 LLM_CHUNK_CONCURRENCY=2 python3 tools/ars/deadman_run_producer_graph.py start --run-id langgraph_batch_parallel_smoke --enable-llm --mock-provider
```

Expected:

- dry-run does not execute child scripts;
- start stops at review gate;
- resume approve reaches terminal `pass`;
- validation report has zero errors and zero warnings;
- public API redacts producer-only fields;
- no media/env/provider artifacts are tracked;
- sample at least three published `companion_surface.hook`,
  `viewer_impulse`, or `preset_actions` strings and verify they read like a
  watching friend, not narrator exposition or an analyst label;
- sampled hook strings should target 20 Chinese characters or fewer when the
  scene allows it;
- sampled viewer-facing strings must not contain producer/debug terms such as
  `mechanism`, `field`, `score`, `cluster`, `evidence grade`, `source window`,
  or `schema`;
- cache-hit runs record `cache_hit` and do not call the provider for matching
  cached node/chunk keys;
- batched serial and batched parallel mock runs produce the same merged
  shortlist ids;
- failed chunks stop the parent node and do not create review requests with
  partial LLM output.

## 17. Product Claim Rules

Allowed after Phase C passes:

- "Deadman Studio has a reproducible producer workflow from local drama material
  to reviewed runtime packs."
- "LangGraph wraps the producer workflow for named stages, checkpointing, human
  review, and reporting."
- "Published Huangnian hooks/actions passed a sample friend-voice review" only if
  the verification matrix voice-tone sample was actually run.

Allowed after Phase D/E passes:

- "LLM nodes assist semantic mining, candidate judging, and drafting before human
  review."

Allowed after Phase G passes:

- "Producer-side LLM work supports cache reuse, chunked large-input processing,
  and bounded chunk-level parallelism."

Not allowed:

- "Studio automatically publishes new dramas."
- "LLM output is source truth."
- "LangGraph is the user-side runtime."
- "Large-scale LLM production is parallelized" before Phase G verification
  passes.
- "Deadman guarantees friend-tone hooks for every future drama" unless that
  drama's reviewed pack passes the same voice-tone acceptance check.
- "Yunmiao/Lihun are runtime-promoted" unless their human review and validation
  actually pass.

## 18. Open Decisions

These should not block Phase A-C:

- real provider choice for LLM nodes;
- Studio UI versus approval API;
- whether Postgres checkpointer is needed after local P0;
- whether Yunmiao/Lihun promotion happens before or after LLM judge.

These block implementation if unresolved:

- cold-resume spike fails;
- existing CLI flags no longer match the node contract;
- reviewed artifact paths are unavailable for Huangnian;
- validation gate cannot pass after publish.
