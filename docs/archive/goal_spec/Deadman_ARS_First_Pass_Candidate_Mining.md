# Deadman ARS First-Pass Candidate Mining Goal Spec

> Status: ready for `/goal` execution  
> Repo: `/Users/okfin3/project/GitHub/OKFin33/OSeria-Alter`  
> Product: Branch 3 / Deadman / `要是我来`  
> Source drama: `荒年全村啃树皮，我有系统满仓肉` first 20 episodes  
> Date: 2026-05-24

## Goal Prompt

Paste this into the target execution thread:

```text
/goal
Execute the contract in /Users/okfin3/project/GitHub/OKFin33/OSeria-Alter/docs/goal_spec/Deadman_ARS_First_Pass_Candidate_Mining.md.

Implement and run the Deadman ARS first-pass candidate mining pipeline for the local 荒年 20-episode素材. Produce timestamped “要是我来” candidate nodes, a ranked candidate table, mechanism clusters, and first field hypotheses for Moment Causality Pack v0.1. Use existing media_index/audio/keyframe/contact-sheet artifacts and existing Doubao Speech ASR adapters where possible. Keep raw media and provider outputs in ignored tmp paths, do not commit MP4s or secrets, and treat the output as semi-automatic bridge evidence requiring human review.

Before editing or running provider calls, read the contract file and treat it as the source of truth.
```

## Current State

- Source videos are local and ignored:
  - `tmp/视频素材/荒年/*.mp4`
- Existing analysis artifacts:
  - `tmp/ars_huangnian_analysis/media_index.json`
  - `tmp/ars_huangnian_analysis/audio_mp3/*.mp3`
  - `tmp/ars_huangnian_analysis/contact_sheets/*.jpg`
  - `tmp/ars_huangnian_analysis/keyframes_10s/ep*/frame_*.jpg`
- Existing provider adapters:
  - `tools/ars/deadman_volc_asr_flash.py`
  - `tools/ars/deadman_volc_asr_standard.py`
- Existing ARS design docs:
  - `docs/Branch3_ARS_Node_Mining_Dogfood_v0.1.md`
  - `docs/Branch3_要是我来_PRD_v0.2.md`
- Known gap:
  - no current script builds timeline windows;
  - no current script mines candidate intervention nodes;
  - no current script clusters candidate nodes by judgment mechanism;
  - no current candidate table exists.

## Objective

Build the first usable automated ARS pass:

```text
media_index + audio transcripts + keyframes/contact sheets
  -> timeline windows
  -> candidate “要是我来” nodes
  -> ranked candidate table
  -> mechanism clusters
  -> field hypotheses for Moment Causality Pack v0.1
```

This pass should prove the bridge workflow, not pretend to be perfect video understanding.

## Product Semantics

Deadman is not branching the drama into a continuous alternate plot.

Do not use `return_to_plot_fit` as a core score. Replace it with lighter viewing-flow fields:

- `watch_flow_fit`: whether the interaction can finish and return the viewer to the original episode without making the original drama feel stupid or broken;
- `canon_context_note_need`: whether the result needs a short note explaining why the original plot was also reasonable;
- `original_plot_note`: optional short note, max one sentence, explaining the original plot choice.

The system answers:

```text
“要是你在这一刻这么做，当前局面里可信后果是什么？”
```

It does not promise:

```text
“后续剧集真的会沿这个分支发展。”
```

## Required Outputs

Write generated artifacts under:

```text
tmp/ars_huangnian_analysis/candidates/
```

Required files:

1. `huangnian_windows.v0.1.json`
   - timestamped source windows;
   - each window links to episode id, start/end ms, transcript text if available, keyframe refs, and visual/contact-sheet refs.

2. `huangnian_candidates.v0.1.json`
   - structured candidate node list.

3. `huangnian_candidates.v0.1.md`
   - human-readable ranked candidate table.

4. `huangnian_mechanism_clusters.v0.1.json`
   - candidate clusters by judgment mechanism.

5. `huangnian_mechanism_clusters.v0.1.md`
   - readable cluster summary.

6. `huangnian_field_hypotheses.v0.1.md`
   - first-pass field hypotheses for `Moment Causality Pack v0.1`.

7. `run_report.md`
   - commands run;
   - provider status;
   - missing data;
   - number of windows/candidates/clusters;
   - top recommended demo nodes;
   - known reliability issues.

## Candidate Node Shape

Each candidate in `huangnian_candidates.v0.1.json` should follow this minimum shape:

```json
{
  "candidate_id": "ep06_c001",
  "episode_id": "huangnian_ep06",
  "start_ms": 42000,
  "end_ms": 61000,
  "trigger_type": "resource_crisis",
  "notice_marker": "!",
  "hook": "这袋白米要不要拿出来？",
  "why_now": "孩子和家人已经撑不住，但白米来源解释不清，旁人可能起疑。",
  "viewer_impulse": "要是我来，肯定先让孩子吃饱。",
  "canon_baseline": {
    "original_action": "主角没有直接无条件亮出全部资源。",
    "original_rationale": "荒年里突然露富会引来亲戚、村民和外部风险。",
    "audience_tension": "观众会想立刻拿资源救急。"
  },
  "scores": {
    "emotion_heat": 82,
    "choice_leverage": 88,
    "causal_clarity": 76,
    "world_constraint_value": 94,
    "watch_flow_fit": 81,
    "visual_result_fit": 70
  },
  "default_options": [
    "直接拿出来，让孩子先吃饱",
    "少量拿出来，编一个能糊弄过去的来源",
    "先藏住，换成更不显眼的野菜粥"
  ],
  "original_plot_note": "原剧情不亮底牌，是为了保住系统和粮食来源。",
  "source_refs": {
    "transcript_refs": [],
    "keyframe_refs": [],
    "contact_sheet_ref": ""
  },
  "reliability": {
    "asr_quality": "unknown|low|medium|high",
    "visual_evidence": "low|medium|high",
    "needs_human_review": true
  }
}
```

## Mechanism Cluster Labels

Use these initial cluster labels, but allow the script/report to propose new labels if evidence demands it:

- `resource_crisis`
- `exposure_risk`
- `family_pressure`
- `village_pressure`
- `humiliation_reversal`
- `evidence_or_trap`
- `system_rule`
- `survival_tradeoff`
- `nonsense_or_overpowered_break`

Cluster by judgment mechanism, not by plot summary.

Good:

```text
resource visibility under famine scarcity
```

Bad:

```text
episode 6 rice scene
```

## Field Hypotheses

The first field hypothesis document should answer:

- Which fields appear necessary across most candidates?
- Which fields are only needed for specific mechanism clusters?
- Which fields should not enter P0 because they imply continuous branching?
- Which fields require human review or source-window provenance?

Expected direction:

- `CoreEnvelope`
  - source window;
  - hook;
  - viewer impulse;
  - canon baseline;
  - actor/relationship context;
  - constraints;
  - action space;
  - score axes;
  - output policy.
- `OptionalCausalityModules`
  - resource;
  - exposure;
  - relationship pressure;
  - evidence/trap;
  - genre/system rule;
  - social reputation.

## Implementation Requirements

Add scripts under:

```text
tools/ars/
```

Recommended minimal scripts:

1. `deadman_build_timeline_windows.py`
   - reads `media_index.json`;
   - reads available normalized ASR artifacts if present;
   - reads keyframe/contact-sheet paths;
   - writes `huangnian_windows.v0.1.json`.

2. `deadman_mine_candidates.py`
   - reads windows;
   - uses deterministic heuristics and/or an LLM provider if available;
   - writes candidate JSON and Markdown table.

3. `deadman_cluster_candidates.py`
   - reads candidate JSON;
   - clusters by mechanism labels;
   - writes cluster JSON/Markdown and field hypothesis Markdown.

It is acceptable to combine these into one script if the code remains readable and the outputs above are still produced.

## ASR Policy

Use existing ASR artifacts if they are valid.

If not valid:

- run `deadman_volc_asr_flash.py` over `tmp/ars_huangnian_analysis/audio_mp3`;
- read credentials from environment only;
- do not print keys;
- write raw provider responses only under ignored `tmp/` paths;
- normalize transcript output before candidate mining.

If provider calls fail:

- do not block the whole pipeline;
- fall back to keyframe/contact-sheet seeded candidate mining;
- mark `asr_quality` as `low` or `unknown`;
- record the provider failure in `run_report.md`.

## LLM Policy

If using an LLM:

- read API keys from environment only;
- keep raw model outputs under ignored `tmp/`;
- require JSON repair/validation before promoting output;
- never treat LLM-inferred facts as source facts without source refs;
- mark uncertain candidates as `needs_human_review: true`.

If no LLM provider is configured:

- implement a deterministic heuristic first pass using transcript keywords, episode ids, and known visual-scan notes;
- still produce the candidate table and clearly mark confidence limitations.

## Candidate Scoring

Use these scores:

| Score | Meaning |
|---|---|
| `emotion_heat` | viewer impulse to react now |
| `choice_leverage` | whether a choice could plausibly change the local result |
| `causal_clarity` | whether scene facts are clear enough to judge |
| `world_constraint_value` | whether the moment tests famine/system/family/village constraints |
| `watch_flow_fit` | whether user can return to original viewing flow without rejection |
| `visual_result_fit` | whether a result image/card can be generated clearly |

Do not use `return_to_plot_fit` as a score name.

## Ranking Formula

Default:

```text
0.25 emotion_heat
+ 0.22 choice_leverage
+ 0.18 world_constraint_value
+ 0.15 causal_clarity
+ 0.12 watch_flow_fit
+ 0.08 visual_result_fit
```

The script may expose weights as constants.

## Acceptance Criteria

- At least 20 candidate nodes are generated across the 20 episodes, or the report explains exactly why not.
- At least 5 candidates are ranked as plausible demo nodes.
- At least 3 candidates include enough source refs to draft Moment Causality Packs after human review.
- Candidate output uses `watch_flow_fit`, not `return_to_plot_fit`.
- Candidate output includes `canon_baseline` and optional `original_plot_note`.
- Mechanism cluster output exists.
- Field hypothesis document exists.
- No MP4/MOV files are copied or committed.
- No API keys are printed or committed.
- Existing Deadman/Runtime code is not broken.

## Verification Required

Run syntax/basic checks for any new scripts:

```bash
python3 -m py_compile tools/ars/*.py
```

Run the new pipeline from repo root.

Suggested final command shape:

```bash
python3 tools/ars/deadman_build_timeline_windows.py \
  --analysis-dir tmp/ars_huangnian_analysis \
  --out tmp/ars_huangnian_analysis/candidates/huangnian_windows.v0.1.json

python3 tools/ars/deadman_mine_candidates.py \
  --windows tmp/ars_huangnian_analysis/candidates/huangnian_windows.v0.1.json \
  --out-json tmp/ars_huangnian_analysis/candidates/huangnian_candidates.v0.1.json \
  --out-md tmp/ars_huangnian_analysis/candidates/huangnian_candidates.v0.1.md

python3 tools/ars/deadman_cluster_candidates.py \
  --candidates tmp/ars_huangnian_analysis/candidates/huangnian_candidates.v0.1.json \
  --out-json tmp/ars_huangnian_analysis/candidates/huangnian_mechanism_clusters.v0.1.json \
  --out-md tmp/ars_huangnian_analysis/candidates/huangnian_mechanism_clusters.v0.1.md \
  --field-md tmp/ars_huangnian_analysis/candidates/huangnian_field_hypotheses.v0.1.md
```

Actual script names may differ, but the outputs must match.

## Docs And Logs

Update:

- `docs/Branch3_ARS_Node_Mining_Dogfood_v0.1.md`
  - replace `return_to_plot_fit` with `watch_flow_fit`;
  - clarify that Deadman does not run continuous branch continuation;
  - point to the generated first-pass artifacts.
- `.agent/dev-log.md`
  - add one `[Deadman]` entry with scripts added and output paths.

Do not rewrite historical dev-log entries.

## Expected Final Report

The execution thread should report:

- scripts added/changed;
- commands run;
- ASR status;
- number of windows generated;
- number of candidates generated;
- top 5 candidate nodes with episode/time/hook;
- mechanism clusters found;
- field hypotheses summary;
- artifact paths;
- known limitations and next human-review step.
