# Deadman Studio LangGraph Producer Pipeline v0.1

> Product: Deadman / `要是我来`
> Surface: Deadman Studio producer side
> Status: executable spec plan
> Date: 2026-05-25
> External product brief:
> `docs/Deadman_Studio_Zero_Context_Product_Brief_v0.1.md`
> Agentic LLM extension:
> `docs/goal_spec/Deadman_LangGraph_Producer_LLM_Extension_v0.1.md`

## Summary

Split Deadman into two product objects:

- User side: mobile short-drama player, companion notice, action input, judgment result.
- Producer side: Deadman Studio, turning short-drama materials into reviewed runtime packs.

This spec adds a P0+ producer workflow that wraps existing ARS and producer CLI
scripts as LangGraph nodes. It is not a user-side runtime, not a CABRuntime
replacement, and not a full creator platform.

First implementation scope is fixed:

- Huangnian P0 closed loop only.
- CLI plus reports only.
- Human review gate uses pause/resume plus file confirmation.
- No provider integration, no Studio UI, no CABRuntime SDK wiring.

This base spec defines the no-provider LangGraph wrapper around existing CLI
tools. For the agentic producer version with LLM semantic mining, LLM-as-judge
screening, and LLM pack drafting, use
`Deadman_LangGraph_Producer_LLM_Extension_v0.1.md` as the additive contract.

## Key Changes

### Dependency

Add the following Python dependencies to the root `requirements.txt`:

```text
langgraph>=1.2,<2
langgraph-checkpoint-sqlite>=3.1,<4
```

Do not add LangSmith, LangChain Agent, provider SDK, image provider, or CABRuntime
SDK dependencies in this slice.

### Pre-Implementation Spike

Before implementing the full runner, run a minimal LangGraph cold-resume spike.
The spike must verify that the selected LangGraph Functional API and SQLite
checkpointer support this exact lifecycle:

```text
start command
  -> run node A
  -> pause at human_review_gate
  -> process exits
resume command in a fresh process
  -> loads same checkpoint
  -> continues after the gate
```

If this cannot be proven, do not fake pause/resume through ad-hoc state files
while still calling it LangGraph checkpointing. Rewrite the runner contract to
the API shape the spike actually supports.

Spike acceptance:

- a tiny two-node graph can pause, exit, and resume from
  `tmp/deadman_producer_runs/{run_id}/checkpoint.sqlite`;
- `producer_job_manifest.json` records the verified LangGraph package versions
  and the spike command used;
- failure to resume is a blocking implementation issue, not a warning.

### Producer Graph Entry

Add:

```text
tools/ars/deadman_run_producer_graph.py
```

The script should use LangGraph Functional API and wrap existing scripts through
subprocess tasks. Do not refactor the existing ARS scripts into pure functions in
this slice.

Use a SQLite checkpointer under ignored runtime artifacts:

```text
tmp/deadman_producer_runs/{run_id}/checkpoint.sqlite
```

### Fixed Node Order

The graph must run this node sequence:

```text
prepare_assets
register_media
build_timeline_windows
mine_candidates
cluster_candidates
human_review_gate
build_drama_context
publish_p0_bridge
validate_producer_bridge
final_report
```

Implementation rules:

- `prepare_assets` defaults to `reuse_existing=true`; do not pass `--force`.
- `register_media` registers only the five Huangnian P0 episodes already used by
  the player.
- `human_review_gate` is the only node allowed to write `review_request.json`.
  It pauses the graph and emits a review request.
- `build_drama_context`, `publish_p0_bridge`, and `validate_producer_bridge`
  only run after explicit approval.
- Any failed node stops the graph. Do not continue with fallback output.

Before coding each node, inspect the current CLI flags of the corresponding
`tools/ars/*.py` script and record the exact argv in `command_log.jsonl`.
The spec's logical node names are not proof that a child script already exposes
the assumed flags.

### Graph State Contract

The LangGraph state is a production job ledger, not a runtime state object.

Minimum state fields:

```text
run_id
drama_id
drama_title
analysis_dir
video_dir
drama_dir
status
current_node
node_statuses
artifact_paths
review_decision
validation_result
errors
```

Rules:

- `artifact_paths` is the source of truth for downstream node inputs. Do not let
  downstream nodes rediscover paths by convention when an upstream node produced
  an explicit artifact.
- `node_statuses` must record node-local status for every fixed node:
  `planned`, `running`, `waiting_for_review`, `blocked_by_prior_failure`,
  `failed`, or `pass`. These node-local statuses do not extend the terminal run
  status enum below.
- Every child CLI invocation must be copied into `command_log.jsonl` before the
  process starts. A failed child process should still leave an argv record.
- Producer-only local paths may appear only in ignored run artifacts or explicitly
  producer-only fields such as `producer_media`. Runtime-facing fields must use
  deployable logical refs such as `runtime_video_url`.
- The graph must be restartable from the checkpoint plus
  `producer_job_manifest.json`. If those disagree, stop and require operator
  repair instead of guessing.

### Base Node Contracts

#### `prepare_assets`

Purpose: convert one local drama folder into ignored, reusable producer assets.

Inputs:

- `drama_id`
- `drama_title`
- `video_dir`
- `analysis_dir`

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
- extracted audio, keyframe refs, and contact sheets under `<analysis_dir>/`

Rerun policy:

- default to reuse existing artifacts;
- do not pass `--force` from the graph;
- if `media_index.json` is missing or invalid, fail closed.

Product consequence: this node proves a new drama can enter the producer
workflow without committing raw media or manual path assumptions.

#### `register_media`

Purpose: create the player-facing media registry without copying raw video.

Inputs:

- `<analysis_dir>/media_index.json`
- fixed Huangnian P0 episode ids
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

Rerun policy:

- allowed to overwrite the registry for the same `run_id` and same input media
  index;
- if any required P0 episode is absent or `missing_local_file`, mark the node
  failed for recording-quality runs.

Product consequence: the runtime can play registered episodes through logical
media URLs, while local file paths stay producer-only and redacted from public
APIs.

#### `build_timeline_windows`

Purpose: convert ASR and media refs into timestamped source windows.

Inputs:

- `<analysis_dir>/media_index.json`
- normalized ASR artifacts under `<analysis_dir>/volc_asr/normalized/`
- keyframe/contact-sheet refs under `<analysis_dir>/`

Child command:

```bash
python3 tools/ars/deadman_build_timeline_windows.py \
  --analysis-dir <analysis_dir> \
  --out-dir <analysis_dir>/candidates \
  --drama-id <drama_id> \
  --drama-title <drama_title>
```

Outputs:

- `<analysis_dir>/candidates/<drama_id>_windows.v0.1.json`

Rerun policy:

- deterministic and safe to rerun;
- if ASR is missing, the node may still emit windows from media duration, but the
  manifest must record reduced `source_quality`.

Product consequence: every later candidate can point back to a small source
window instead of claiming whole-episode understanding.

#### `mine_candidates`

Purpose: deterministic broad recall over timeline windows.

Inputs:

- `<analysis_dir>/candidates/<drama_id>_windows.v0.1.json`
- handwritten mechanism ontology inside `deadman_mine_candidates.py`

Child command:

```bash
python3 tools/ars/deadman_mine_candidates.py \
  --candidate-dir <analysis_dir>/candidates \
  --max-candidates 80 \
  --drama-id <drama_id> \
  --drama-title <drama_title>
```

Outputs:

- `<analysis_dir>/candidates/<drama_id>_candidates.v0.1.json`
- `<analysis_dir>/candidates/<drama_id>_candidates.v0.1.md`

Rerun policy:

- deterministic for the same source windows and code revision;
- do not treat high score as approval for publication.

Product consequence: deterministic recall is the audit baseline. It gives human
reviewers and LLM nodes a stable "what the rules found" table, not final semantic
truth.

#### `cluster_candidates`

Purpose: group candidate moments by mechanism and field pressure.

Inputs:

- source windows JSON
- candidate JSON

Child command:

```bash
python3 tools/ars/deadman_cluster_candidates.py \
  --candidate-dir <analysis_dir>/candidates \
  --analysis-dir <analysis_dir> \
  --drama-id <drama_id> \
  --drama-title <drama_title>
```

Outputs:

- `<analysis_dir>/candidates/<drama_id>_mechanism_buckets.v0.1.json`
- `<analysis_dir>/candidates/<drama_id>_mechanism_buckets.v0.1.md`
- `<analysis_dir>/candidates/<drama_id>_field_hypotheses.v0.1.md`
- `<analysis_dir>/candidates/run_report.md`

Rerun policy:

- deterministic for the same candidates;
- may be moved after LLM judge in the LLM extension, but the base graph keeps it
  after deterministic recall.

Product consequence: this node exposes repeated field demand before schema or
runtime pack edits, so P0 does not grow fields just because one scene was noisy.

#### `human_review_gate`

Purpose: pause the graph and ask a human to approve or reject publishable inputs.

Inputs:

- deterministic candidate table
- mechanism bucket report
- expected reviewed node and reviewed candidate paths

Action:

- write `review_request.json`;
- checkpoint graph state;
- exit `start` with `status=waiting_for_review`.

Outputs:

- `tmp/deadman_producer_runs/{run_id}/review_request.json`

Rerun policy:

- this is the only base node allowed to create or overwrite
  `review_request.json`;
- `resume --review-decision approve` must verify reviewed artifacts exist before
  continuing;
- `resume --review-decision reject` must stop without publishing.

Product consequence: no automatic miner, deterministic or LLM, can directly
promote runtime packs.

#### `build_drama_context`

Purpose: convert human-reviewed evidence into runtime-pack source material.

Inputs:

- reviewed demo nodes
- reviewed candidates
- approved summaries file
- `drama_dir`

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

Rerun policy:

- allowed only after `review_decision=approve`;
- if reviewed artifacts are missing, stale, or not listed in `review_request.json`,
  fail closed.

Product consequence: publication starts from reviewed evidence, not raw ASR,
keyword hits, or model drafts.

#### `publish_p0_bridge`

Purpose: publish reviewed P0 data into the runtime-readable Deadman drama pack.

Inputs:

- `<drama_dir>/media_registry.v0.1.json`
- reviewed demo nodes
- reviewed candidates

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
- publish report

Rerun policy:

- allowed only after `build_drama_context` passes;
- must not publish if any child input is outside the reviewed allowlist.

Product consequence: this is the first point where producer work becomes
player-consumable runtime data.

#### `validate_producer_bridge`

Purpose: block unsafe or inconsistent runtime-facing artifacts.

Inputs:

- `drama_dir`

Child command:

```bash
python3 tools/ars/deadman_validate_producer_bridge.py \
  --drama-dir <drama_dir> \
  --report <analysis_dir>/producer_bridge_validation_report.md
```

Outputs:

- `<analysis_dir>/producer_bridge_validation_report.md`
- `validation_result` in `producer_job_manifest.json`

Rerun policy:

- always safe to rerun;
- any validation error maps to terminal `validation_failed`, not `pass`.

Product consequence: if this node fails, the team cannot claim the pack is safe,
runtime-ready, or reproducible.

#### `final_report`

Purpose: write the operator/reviewer summary for the completed run.

Inputs:

- `producer_job_manifest.json`
- `command_log.jsonl`
- `review_request.json`
- validation report
- final runtime pack paths

Outputs:

- `tmp/deadman_producer_runs/{run_id}/final_report.md`

Rerun policy:

- safe to regenerate after terminal states;
- must state whether the run ended as `pass`, `failed`, `validation_failed`, or
  `rejected_by_human_review`.

Product consequence: this is the artifact that lets a competition reviewer or
future operator understand exactly what was produced and what was skipped.

### CLI Interface

The entry script should expose three commands:

```bash
python3 tools/ars/deadman_run_producer_graph.py dry-run --run-id langgraph_p0_dry
python3 tools/ars/deadman_run_producer_graph.py start --run-id langgraph_p0_smoke
python3 tools/ars/deadman_run_producer_graph.py resume --run-id langgraph_p0_smoke --review-decision approve
```

Required behavior:

- `dry-run` prints the command plan and artifact plan without running child
  scripts.
- `start` runs until `human_review_gate`, writes checkpoint/run artifacts, then
  exits successfully with status `waiting_for_review`.
- `resume --review-decision approve` resumes from the same checkpoint and runs
  publish plus validation.
- `resume --review-decision reject` stops without publishing and records
  `rejected_by_human_review`.

Default parameters:

```text
drama_id=huangnian
drama_title=荒年全村啃树皮，我有系统满仓肉
analysis_dir=tmp/ars_huangnian_analysis
video_dir=tmp/视频素材/荒年
drama_dir=data/dramas/huangnian
```

### Run Artifacts

Each run writes to:

```text
tmp/deadman_producer_runs/{run_id}/
```

Required artifacts:

```text
producer_job_manifest.json
command_log.jsonl
review_request.json
final_report.md
checkpoint.sqlite
```

`producer_job_manifest.json` must include:

- `run_id`
- `drama_id`
- current status
- node list and per-node status
- input paths
- output paths
- failed node and error summary when failed
- checkpoint path
- final validation status when available
- verified LangGraph package versions and cold-resume spike status

Allowed base statuses:

```text
planned
running
waiting_for_review
rejected_by_human_review
publishing
validation_failed
failed
pass
```

The LLM extension may add `waiting_for_llm`, `llm_failed`, and
`skipped_by_config`, but it must still map terminal states back to `failed`,
`validation_failed`, `rejected_by_human_review`, or `pass`.

`command_log.jsonl` must include one record per child script:

- node name
- command argv
- start/end timestamp or duration
- exit code
- stdout summary
- stderr summary

`review_request.json` must include:

- candidate table paths
- reviewed nodes path expected on approval
- reviewed candidates path expected on approval
- human instructions

`review_request.json` must be generated by `human_review_gate`; earlier nodes may
write candidate/evidence artifacts but must not create or overwrite the gate
request.

`final_report.md` should be readable in the competition technical document and
record the graph stages, human gate result, validation result, and runtime pack
paths.

## Boundaries

Deadman Studio owns producer workflow coordination only:

- register media
- build evidence
- mine and cluster candidates
- pause for human review
- publish reviewed packs
- validate runtime bridge

It must not own:

- user-side judgment runtime
- CABRuntime SDK execution
- image generation provider integration
- ASR provider reruns by default
- arbitrary shell/code execution beyond the predeclared script commands
- Yunmiao/Lihun runtime promotion

Product consequence: Deadman can present a real AI production workflow in the
competition without becoming a second runtime platform.

## Failure Rules

All producer graph failures are fail-closed.

If a child script returns non-zero:

- stop the graph
- record `status=failed`
- record `failed_node`
- preserve stdout/stderr summaries
- do not publish new runtime packs
- do not substitute deterministic fallback artifacts

Runtime-facing tracked files must not contain:

- `tmp/`
- `/@fs`
- `/Users/`
- raw media paths
- `.env`
- API keys or secret-bearing literals

## Documentation Updates

Add or update:

```text
docs/LangGraph_Producer_Pipeline_v0.1.md
docs/Producer_Bridge_Minimum_Flow_v0.1.md
.agent/dev-log.md
```

The executable source of truth stays in `docs/goal_spec/`. The
`docs/LangGraph_Producer_Pipeline_v0.1.md` document, if added, is a
production-facing summary derived from this spec for reviewers and future
operators. Do not let the two documents drift on node order, failure rules, or
claim boundaries.

`LangGraph_Producer_Pipeline_v0.1.md` should explain:

- Deadman Studio versus user-side player
- why LangGraph is only used for backend production workflow
- how the human review gate works
- how CABRuntime can later call this as a typed producer action

`Producer_Bridge_Minimum_Flow_v0.1.md` should keep the old CLI sequence as the
underlying tool chain and mark the LangGraph runner as the P0+ orchestration
entry.

## Test Plan

Run:

```bash
python3 -m py_compile tools/ars/*.py
python3 -m py_compile backend/*.py backend/tests/*.py
```

Dry-run smoke:

```bash
python3 tools/ars/deadman_run_producer_graph.py dry-run --run-id langgraph_p0_dry
```

Expected:

- prints all 10 fixed nodes
- writes or prints artifact plan
- does not execute child scripts
- does not modify tracked runtime packs

Human gate smoke:

```bash
python3 tools/ars/deadman_run_producer_graph.py start --run-id langgraph_p0_smoke
python3 tools/ars/deadman_run_producer_graph.py resume --run-id langgraph_p0_smoke --review-decision approve
```

Expected:

- `start` reaches `waiting_for_review`
- `review_request.json` exists
- `resume` completes publish and validation
- final manifest status is `pass`

Regression gates:

```bash
python3 tools/ars/deadman_validate_producer_bridge.py \
  --drama-dir data/dramas/huangnian

python3 tools/ars/deadman_check_submission_readiness.py
```

Also keep existing backend/frontend build and test gates passing when this work
is implemented.

Hygiene checks:

- no MP4/MOV/M4V files added to tracked work areas
- no `.env` files added
- no literal API keys
- no raw provider output committed
- public API still redacts `producer_media` and `producer_refs`

## Assumptions

- Huangnian P0 reviewed artifacts already exist and remain the only publishable
  runtime source for this slice.
- Yunmiao and Lihun remain migration evidence only.
- The first human review gate is file-based pause/resume; a future approval API
  can reuse `review_request.json` and `producer_job_manifest.json`.
- Existing CLI scripts remain the source of truth for production work; LangGraph
  is the orchestration wrapper.
