# Deadman Huangnian Review, Pack Schema, and Migration Probe Goal Spec

> Status: ready for `/goal` execution  
> Repo: `/Users/okfin3/project/GitHub/OKFin33/OSeria-Alter`  
> Product: Branch 3 / Deadman / `要是我来`  
> Foundation source drama: `荒年全村啃树皮，我有系统满仓肉` first 20 episodes  
> Date: 2026-05-24

## Goal Prompt

Paste this into the target execution thread:

```text
/goal
Execute the contract in /Users/okfin3/project/GitHub/OKFin33/OSeria-Alter/docs/goal_spec/Deadman_Huangnian_Review_Schema_Migration.md.

Refine the first-pass 荒年 ARS outputs into reviewed demo candidates, induce the Moment Causality Pack v0.1 minimum schema from evidence, patch the ARS miner/schema issues exposed by review, and then run a conditional migration probe on two other allowed-drama genres if local media materials exist. Treat migration as validation of the refined pipeline, not as a substitute for reviewing 荒年. Keep raw media and provider outputs in ignored tmp paths, do not commit MP4/MOV files or secrets, and make every output explicit about evidence vs inference.

Before editing or running scripts, read the contract file and treat it as the source of truth.
```

## Why This Is One Goal

This goal intentionally combines four steps because they depend on each other:

1. `荒年` candidate review finds what is actually usable.
2. The reviewed candidates induce the minimum `Moment Causality Pack` fields.
3. The field and review gaps define what the ARS miner must fix.
4. Migration probes test the fixed pipeline, instead of multiplying first-pass noise.

Do not run the migration pass before the `荒年` review and miner/schema patch.

## Current State

First-pass outputs already exist under:

```text
tmp/ars_huangnian_analysis/candidates/
```

Known first-pass result:

- Doubao Speech flash ASR succeeded for 20 / 20 episodes.
- Windows: 135.
- Candidate nodes: 64.
- Mechanism clusters: 8.
- Plausible `rank_score >= 70`: 39.
- All candidates are semi-automatic bridge evidence and require review.

Known first-pass weaknesses to fix:

- Current cluster output is closer to mechanism buckets than true emergent clustering.
- `resource_crisis` is over-selected because broad food keywords such as `吃` are too loose.
- Candidate hooks/options are too templated and repeat across unrelated scenes.
- `visual_evidence: high` can be misleading when it only means keyframe references exist.
- Candidate limit behavior is not a hard cap when episode coverage backfill appends extra candidates.

Relevant files:

```text
tools/ars/deadman_build_timeline_windows.py
tools/ars/deadman_mine_candidates.py
tools/ars/deadman_cluster_candidates.py
docs/Branch3_ARS_Node_Mining_Dogfood_v0.1.md
docs/Branch3_要是我来_PRD_v0.2.md
docs/Byte_AI_Allowed_Drama_Summaries_2026-05-23.md
docs/goal_spec/Deadman_ARS_First_Pass_Candidate_Mining.md
```

## Objective

Produce a reviewed, evidence-grounded bridge package that can drive the next implementation step:

```text
first-pass 荒年 candidates
  -> reviewed candidate table
  -> selected 3-5 demo nodes
  -> Moment Causality Pack v0.1 draft schema
  -> patched ARS miner/schema
  -> conditional migration probe on two genre targets
```

The goal is not to finalize production authoring. The goal is to create a trustworthy v0.1 contract for front-end/back-end integration work.

## Product Semantics

Deadman P0 does not branch the whole drama.

The product answers:

```text
要是你在这一刻这么做，当前局面里可信后果是什么？
```

It does not promise:

```text
后续剧集真的沿这个分支发展。
```

Keep these fields and concepts central:

- `watch_flow_fit`
- `canon_context_note_need`
- `original_plot_note`
- source-window provenance
- local credible consequence

Do not reintroduce `return_to_plot_fit` as a core score.

## Phase 1 - Review `荒年` Candidates

Review at least the top 20 first-pass candidates, plus any lower-ranked candidate needed for mechanism diversity.

Inputs:

```text
tmp/ars_huangnian_analysis/candidates/huangnian_candidates.v0.1.json
tmp/ars_huangnian_analysis/candidates/huangnian_candidates.v0.1.md
tmp/ars_huangnian_analysis/candidates/huangnian_windows.v0.1.json
tmp/ars_huangnian_analysis/volc_asr/
tmp/ars_huangnian_analysis/keyframes_10s/
tmp/ars_huangnian_analysis/contact_sheets/
tmp/视频素材/荒年/
```

Required review dimensions:

- whether the moment is genuinely interactive;
- whether the trigger type is correct;
- whether the hook is scene-specific;
- whether the default options are plausible and emotionally legible;
- whether the original plot note helps viewers return to watching;
- whether keyframe/contact-sheet evidence supports the claim or only supplies timestamp context;
- whether the candidate should be rejected, kept, promoted to demo candidate, or turned into a pack draft.

Review status enum:

```text
reject
keep
demo_candidate
pack_draft
```

Required outputs:

```text
tmp/ars_huangnian_analysis/review/huangnian_candidates.reviewed.v0.1.json
tmp/ars_huangnian_analysis/review/huangnian_candidates.reviewed.v0.1.md
tmp/ars_huangnian_analysis/review/huangnian_demo_nodes.v0.1.json
tmp/ars_huangnian_analysis/review/huangnian_demo_nodes.v0.1.md
```

Each reviewed candidate must include:

```json
{
  "candidate_id": "huangnian_ep12_c001",
  "review_status": "demo_candidate",
  "corrected_trigger_type": "resource_visibility",
  "scene_specific_hook": "兔子肉要不要现在下锅？",
  "revised_default_options": [],
  "why_now_reviewed": "",
  "canon_baseline_reviewed": {},
  "original_plot_note_reviewed": "",
  "evidence_grade": "low|medium|high",
  "evidence_notes": "",
  "rejection_reason": "",
  "pack_field_notes": []
}
```

Select 3-5 `demo_candidate` nodes. Prefer diversity over a list of five near-duplicate food scenes.

## Phase 2 - Induce Moment Causality Pack v0.1

Use the reviewed `荒年` candidates to draft the minimum pack contract.

Required tracked outputs:

```text
docs/Moment_Causality_Pack_v0.1_Draft.md
docs/Field_Evidence_Matrix_v0.1.md
```

The draft must separate:

- `CoreEnvelope`: fields required by every P0 node.
- `OptionalCausalityModules`: fields required only by specific judgment mechanisms.
- `NonP0Fields`: fields that imply continuous branching or long-term simulation and should not be added now.
- `ProducerReviewFields`: fields that exist to keep evidence/provenance honest.

Expected core areas:

- source window;
- companion/front-end hook copy;
- viewer impulse;
- actor and relationship context;
- local constraints;
- canon baseline;
- action type and routing;
- default options;
- custom action policy;
- judgment policy;
- outcome response contract;
- visual result policy;
- scoring axes;
- watch-flow fields;
- provenance and review status.

Expected optional modules:

- resource scarcity / resource visibility;
- exposure and secrecy;
- relationship pressure;
- village/public reputation pressure;
- evidence/trap logic;
- system or hidden-power rule;
- humiliation/reversal;
- survival tradeoff.

The `Field Evidence Matrix` must show which reviewed candidates require which fields. Do not claim a field is core unless multiple reviewed candidates actually need it.

## Phase 3 - Patch ARS Miner and Schema

Patch the ARS scripts based on the review.

Minimum fixes:

1. Reduce broad-keyword false positives.
   - `吃` alone must not classify a scene as `resource_crisis`.
   - Require co-occurrence such as hunger, scarcity, food quantity, food source, distribution pressure, exposure risk, or family/village pressure.

2. Generate scene-specific hooks.
   - Avoid repeated generic hooks such as `这口吃的要不要现在拿出来？`.
   - Hooks should include the concrete object, relation, or decision pressure visible in the source window.

3. Rename or downgrade visual evidence.
   - If the script only knows keyframes exist, call this `keyframe_ref_quality` or mark `visual_evidence` no higher than `medium`.
   - Reserve `visual_evidence: high` for actually reviewed or machine-interpreted visual claims.

4. Make candidate limit behavior explicit.
   - If `--max-candidates` is a hard cap, enforce it.
   - If diversity backfill may exceed it, rename/report the behavior clearly.

5. Be honest about clustering.
   - If clustering is still label-bucket aggregation, call it `mechanism_buckets`.
   - Only call it clustering if the implementation compares candidates beyond the preassigned label.

Required outputs:

```text
tmp/ars_huangnian_analysis/candidates/huangnian_candidates.v0.2.json
tmp/ars_huangnian_analysis/candidates/huangnian_candidates.v0.2.md
tmp/ars_huangnian_analysis/candidates/huangnian_mechanism_buckets_or_clusters.v0.2.json
tmp/ars_huangnian_analysis/candidates/huangnian_mechanism_buckets_or_clusters.v0.2.md
tmp/ars_huangnian_analysis/candidates/run_report.v0.2.md
```

Update the ARS dogfood doc with a short section summarizing:

- what first-pass assumptions failed;
- what was fixed;
- what still requires human review.

## Phase 4 - Conditional Migration Probe

Migration is required only after Phase 1-3 are complete.

Target genres:

1. revenge / humiliation / relationship conflict:
   - prefer `幸得相遇离婚时`;
   - fallback `撕夜`.
2. cultivation / hidden-power / overpowered identity:
   - prefer `云渺1：我修仙多年强亿点怎么了`;
   - fallback `天下第一纨绔` if no `云渺1` media exists.

First search for local materials under:

```text
tmp/视频素材/
```

If local media exists:

- run the refined ARS pipeline on up to the first 5 episodes per migration drama;
- keep provider outputs under ignored tmp paths;
- produce the migration outputs below.

If local media does not exist:

- do not fabricate ASR or scene evidence;
- do not block the entire goal;
- produce a migration material gap report;
- run only a summary-based schema stress test using `docs/Byte_AI_Allowed_Drama_Summaries_2026-05-23.md`, explicitly labeled as inference, not evidence.

Required migration outputs:

```text
tmp/ars_migration_analysis/<drama_slug>/candidates.v0.1.json
tmp/ars_migration_analysis/<drama_slug>/candidates.v0.1.md
tmp/ars_migration_analysis/<drama_slug>/field_stress_test.v0.1.md
tmp/ars_migration_analysis/migration_probe_report.v0.1.md
```

The migration probe report must answer:

- which modules transferred cleanly;
- which modules were missing from `荒年`;
- which fields should become optional rather than core;
- whether the selected `荒年` demo nodes still look like a good foundation after seeing the other genres;
- what media is missing for a real migration run.

## Scope Boundaries

In scope:

- review artifacts;
- pack/schema docs;
- ARS script refinements;
- ignored tmp outputs;
- dev-log update;
- short updates to Deadman docs.

Out of scope:

- front-end integration of packs into the player;
- backend API implementation;
- image generation integration;
- voice interaction;
- Android/iOS packaging;
- continuous branch simulation;
- committing raw media or provider raw logs.

## Verification Required

Run:

```bash
python3 -m py_compile tools/ars/*.py
python3 -m json.tool tmp/ars_huangnian_analysis/review/huangnian_candidates.reviewed.v0.1.json >/dev/null
python3 -m json.tool tmp/ars_huangnian_analysis/review/huangnian_demo_nodes.v0.1.json >/dev/null
python3 -m json.tool tmp/ars_huangnian_analysis/candidates/huangnian_candidates.v0.2.json >/dev/null
git status --short
```

Also verify:

- no MP4/MOV files were added outside ignored tmp media paths;
- no `.env` files or API keys were added;
- generated tmp outputs are ignored;
- tracked docs do not claim summary-based migration stress tests are source evidence.

If frontend files are not touched, do not spend time on frontend test/build in this goal.

## Acceptance Criteria

- At least 20 first-pass candidates are reviewed.
- 3-5 `荒年` demo candidates are selected with scene-specific hooks and revised options.
- No selected demo candidate relies on a generic repeated hook.
- `Moment_Causality_Pack_v0.1_Draft.md` defines core, optional, non-P0, and producer-review fields.
- `Field_Evidence_Matrix_v0.1.md` ties fields back to reviewed candidates.
- ARS miner/schema is patched for the known first-pass weaknesses.
- v0.2 candidate outputs are generated.
- Migration is handled honestly:
  - real probe if local media exists;
  - explicit gap report plus inference-labeled stress test if it does not.
- Final report separates evidence, inference, known debt, and next implementation step.

## Expected Final Report

The execution thread should report:

- files changed;
- review counts and selected demo node IDs;
- pack schema docs created;
- ARS fixes made;
- migration status for each target genre;
- verification commands and results;
- remaining debt;
- whether the next step should be front-end pack ingestion, backend judgment API, or another ARS iteration.
