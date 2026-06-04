# Deadman Drama Context Pack Extraction Goal Spec

> Status: ready for `/goal` execution  
> Repo: `/Users/okfin3/project/GitHub/OKFin33/OSeria-Alter`  
> Product: Branch 3 / Deadman / `要是我来`  
> Source drama: `荒年全村啃树皮，我有系统满仓肉` first 20 episodes  
> Date: 2026-05-24

## Goal Prompt

Paste this into the target execution thread:

```text
/goal
Execute the contract in /Users/okfin3/project/GitHub/OKFin33/OSeria-Alter/docs/goal_spec/Deadman_Drama_Context_Pack_Extraction.md.

Build the production-side Drama Context Pack pipeline for 荒年: extract a lightweight global drama context draft from existing summaries, ASR outputs, reviewed demo nodes, and pack/schema docs; produce an evidence map that separates source evidence from inference; promote a reviewed context pack and the 5 reviewed demo moment packs into tracked runtime data under data/dramas/huangnian/. Do not implement the backend judgment API yet. Keep raw/generated intermediate artifacts under ignored tmp paths, do not commit MP4/MOV files or secrets, and append the required [Deadman] dev-log entry.

Before editing or running scripts, read the contract file and treat it as the source of truth.
```

## Why This Goal Exists

Deadman P0 is moment-level, but each moment still needs a thin global context.
The runtime LLM must know what kind of story it is inside:

- famine survival;
- system/hidden-resource rules;
- family trust repair;
- village/public pressure;
- companion tone and guardrails;
- what would break the short-drama viewing flow.

This is not an ArcForge `World Pack`. It is a lighter `Drama Context Pack`:

```text
Drama Context Pack
  = global genre/story/rule/tone constraints for a drama

Moment Causality Pack
  = local facts and decision contract for one timestamped intervention node
```

Runtime priority:

```text
Moment Causality Pack local facts
  > Drama Context Pack global constraints
  > LLM common sense
```

## Current State

Available inputs:

```text
docs/Byte_AI_Allowed_Drama_Summaries_2026-05-23.md
docs/Moment_Causality_Pack_v0.1_Draft.md
docs/Field_Evidence_Matrix_v0.1.md
tmp/ars_huangnian_analysis/review/huangnian_candidates.reviewed.v0.1.json
tmp/ars_huangnian_analysis/review/huangnian_demo_nodes.v0.1.json
tmp/ars_huangnian_analysis/volc_asr/normalized/*.json
tmp/ars_huangnian_analysis/contact_sheets/
tmp/ars_huangnian_analysis/keyframes_10s/
```

Important reviewed demo moment IDs:

```text
huangnian_ep12_m001
huangnian_ep07_m001
huangnian_ep03_m001
huangnian_ep04_m001
huangnian_ep06_m001
```

Known risk:

- reviewed demo nodes are trustworthy enough for P0 demo ingestion;
- v0.2 automatic candidates are not trustworthy enough to feed runtime directly;
- `candidate_id` is not stable across miner versions, so promoted runtime data must use stable `moment_id + source_window`.

## Objective

Implement the bridge step from reviewed ARS artifacts to runtime-readable data:

```text
summaries + ASR + reviewed demo nodes + schema docs
  -> Drama Context Pack draft
  -> Drama Context evidence map
  -> reviewed/promoted context pack
  -> tracked runtime data:
       data/dramas/huangnian/context.v0.1.json
       data/dramas/huangnian/moments.v0.1.json
       data/dramas/huangnian/manifest.v0.1.json
```

This goal prepares backend judgment API ingestion. It does not build the API.

## Required Production-Side Script

Add:

```text
tools/ars/deadman_build_drama_context.py
```

The script should:

1. read reviewed demo nodes;
2. read the allowed-drama summary document;
3. optionally read normalized ASR snippets referenced by demo nodes;
4. build a draft `Drama Context Pack`;
5. build a Markdown evidence map;
6. build/promote tracked runtime data when `--promote` is passed;
7. avoid provider calls and secrets.

Suggested command:

```bash
python3 tools/ars/deadman_build_drama_context.py \
  --drama-id huangnian \
  --reviewed-demo-nodes tmp/ars_huangnian_analysis/review/huangnian_demo_nodes.v0.1.json \
  --reviewed-candidates tmp/ars_huangnian_analysis/review/huangnian_candidates.reviewed.v0.1.json \
  --summaries docs/Byte_AI_Allowed_Drama_Summaries_2026-05-23.md \
  --out-dir tmp/ars_huangnian_analysis/context \
  --promote-dir data/dramas/huangnian \
  --promote
```

It is acceptable for v0.1 to be deterministic/structured rather than LLM-powered,
as long as every claim is labeled with source and confidence.

## Drama Context Pack Minimum Shape

The promoted context file must be JSON and include at least:

```json
{
  "schema_version": "drama_context_pack.v0.1",
  "drama_id": "huangnian",
  "title": "荒年全村啃树皮，我有系统满仓肉",
  "source_scope": {
    "episode_scope": "first_20_episodes",
    "basis": [
      "allowed_drama_summary",
      "reviewed_demo_nodes",
      "asr_snippets",
      "keyframe_contact_sheet_refs"
    ],
    "evidence_status": "reviewed_bridge_artifact"
  },
  "premise": "",
  "genre_contract": [],
  "protagonist": {
    "name": "程弯弯",
    "role": "",
    "capabilities": [],
    "limits": []
  },
  "core_constraints": [],
  "relationship_map": [],
  "tone_policy": {
    "companion_stance": "",
    "preferred": [],
    "avoid": []
  },
  "judgment_guardrails": {
    "must_consider": [],
    "must_not_claim": [],
    "custom_action_handling": ""
  },
  "runtime_priority": [
    "moment_pack_local_facts",
    "drama_context_pack_global_constraints",
    "llm_common_sense"
  ],
  "evidence_map": [],
  "confidence": {
    "overall": "low|medium|high",
    "notes": ""
  },
  "open_questions": []
}
```

Expected `core_constraints` for `荒年`, if supported by summary/reviewed nodes:

- famine resource scarcity;
- food/resource exposure creates suspicion and争抢 risk;
- system/hidden-resource ability should not be publicly over-explained;
- children/family trust repair must be gradual;
- village/public witnesses can amplify reputation and conflict;
- P0 outcomes stay local and do not rewrite later episodes.

## Promoted Moment Pack Shape

`data/dramas/huangnian/moments.v0.1.json` should contain the 5 reviewed
demo moments converted from `tmp/ars_huangnian_analysis/review/huangnian_demo_nodes.v0.1.json`.

Requirements:

- use stable `moment_id`, not unstable candidate order;
- preserve `candidate_id` only as provenance;
- include `source_window`, `companion_hook`, `default_options`, `canon_baseline`,
  `original_plot_note`, evidence notes, required pack fields, and source refs;
- include a `drama_context_ref` pointing to `context.v0.1.json`;
- include `schema_version: "moment_causality_pack.v0.1"`;
- include `review_state.status: "demo_candidate"`;
- do not ingest v0.2 automatic candidates directly.

## Evidence Map Requirements

Write:

```text
tmp/ars_huangnian_analysis/context/huangnian_drama_context.evidence.v0.1.md
```

The evidence map must separate:

- summary-derived claims;
- reviewed-node-derived claims;
- ASR/keyframe-supported claims;
- inference-only product constraints;
- open questions.

Do not present the allowed-drama public summary as timestamp-level evidence.
Do not present keyframe refs as proof of psychological motivation.

## Required Outputs

Ignored intermediate outputs:

```text
tmp/ars_huangnian_analysis/context/huangnian_drama_context.draft.v0.1.json
tmp/ars_huangnian_analysis/context/huangnian_drama_context.evidence.v0.1.md
tmp/ars_huangnian_analysis/context/huangnian_drama_context.run_report.v0.1.md
```

Tracked runtime data:

```text
data/dramas/huangnian/context.v0.1.json
data/dramas/huangnian/moments.v0.1.json
data/dramas/huangnian/manifest.v0.1.json
data/dramas/README.md
```

Optional tracked explanatory doc if useful:

```text
docs/Drama_Context_Pack_v0.1_Draft.md
```

Update `.agent/dev-log.md` with a `[Deadman]` entry.

## Scope Boundaries

In scope:

- production-side context extraction script;
- context draft/evidence/run report;
- promoted tracked runtime data;
- lightweight docs/README;
- validation and dev-log.

Out of scope:

- backend judgment API;
- frontend pack ingestion;
- image generation;
- voice;
- new ASR provider calls;
- LLM runtime prompting beyond data contract notes;
- migration drama context packs.

## Verification Required

Run:

```bash
python3 -m py_compile tools/ars/*.py
python3 -m json.tool tmp/ars_huangnian_analysis/context/huangnian_drama_context.draft.v0.1.json >/dev/null
python3 -m json.tool data/dramas/huangnian/context.v0.1.json >/dev/null
python3 -m json.tool data/dramas/huangnian/moments.v0.1.json >/dev/null
python3 -m json.tool data/dramas/huangnian/manifest.v0.1.json >/dev/null
git status --short
```

Also verify:

- promoted `moments.v0.1.json` contains exactly 5 demo moments;
- all promoted moments have `moment_id`, `source_window`, `companion_hook`,
  `default_options`, `review_state`, and `drama_context_ref`;
- promoted data does not contain raw MP4/MOV paths as runtime dependencies;
- no `.env` files or API keys were added;
- tmp context outputs are ignored;
- docs/data explicitly say this is a lightweight Drama Context Pack, not an
  ArcForge world simulation pack.

If frontend/backend files are not touched, do not run frontend/backend tests in
this goal.

## Acceptance Criteria

- `deadman_build_drama_context.py` exists and can regenerate the context draft
  and promoted data from reviewed artifacts.
- `context.v0.1.json` gives the LLM enough global context for the 5 reviewed
  moments without pretending to be a full world model.
- `moments.v0.1.json` uses the reviewed demo nodes as source of truth and does
  not use v0.2 automatic candidates directly.
- Evidence and inference are labeled clearly.
- Runtime data is tracked under `data/dramas/huangnian/`.
- Generated tmp artifacts remain ignored.
- Dev-log records the work.

## Expected Final Report

The execution thread should report:

- files changed/created;
- context pack fields generated;
- promoted moment IDs;
- artifact paths;
- verification commands/results;
- known debt;
- recommended next step.

Recommended next step after this goal should usually be:

```text
backend judgment API ingestion:
Drama Context Pack + Moment Pack + user action -> structured “要是我来” result
```
