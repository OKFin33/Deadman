# Deadman Studio LangGraph Producer LLM Extension v0.1

> Product: Deadman / `要是我来`
> Surface: Deadman Studio producer side
> Status: executable design extension
> Date: 2026-05-25
> Depends on: `docs/goal_spec/Deadman_LangGraph_Producer_Pipeline_v0.1.md`

## Summary

The first LangGraph producer plan wraps the existing deterministic ARS and
producer CLI scripts. That proves a reproducible production workflow, but the
current candidate miner is still mostly ASR plus handwritten mechanism keywords
and scoring.

This extension adds LLM-assisted producer nodes to make Deadman Studio a real AI
production workflow:

```text
ASR / windows
  -> deterministic candidate recall
  -> LLM semantic miner
  -> LLM candidate judge
  -> human review gate
  -> LLM pack drafter
  -> publish reviewed packs
  -> validate runtime bridge
```

LLM output is draft/enrichment evidence only. It must not directly publish
runtime packs or become source truth without human review and validation.

## Current Baseline

The current deterministic flow:

```text
MP4
  -> prepare_assets
  -> ASR / normalized transcript
  -> build_timeline_windows
  -> mine_candidates
  -> cluster_candidates
  -> human review
  -> build_drama_context / publish_p0_bridge
  -> validate_producer_bridge
```

`deadman_mine_candidates.py` currently knows what to look for through a
handwritten interaction ontology:

- mechanism labels such as `resource_crisis`, `exposure_risk`,
  `family_pressure`, `humiliation_reversal`, `system_rule`,
  `relationship_betrayal`, and `status_reversal`;
- mechanism keyword lists;
- default hooks, viewer impulses, and option templates;
- weighted scoring axes including `emotion_heat`, `choice_leverage`,
  `world_constraint_value`, `causal_clarity`, `watch_flow_fit`, and
  `visual_result_fit`.

Product consequence: the current miner is controllable and reproducible, but it
can miss semantically strong moments without obvious keywords and can over-score
keyword coincidences that are not actually good interaction nodes.

## Deterministic Retention Policy

Do not delete the deterministic miner when LLM nodes are added.

The deterministic layer is the production audit baseline, not the semantic
authority. It should answer:

- what a cheap, rule-based replay finds from the same source windows;
- which moments the LLM adds that the rules missed;
- which rule hits the LLM rejects as keyword coincidences;
- where deterministic rank, LLM semantic fit, and LLM judge verdict disagree.

Authority split:

| Layer | Authority |
| --- | --- |
| Deterministic recall | Stable replay baseline and cheap candidate recall. It may propose and rank, but never approve. |
| LLM semantic miner | Primary semantic understanding layer. It may discover, enrich, and explain candidates. |
| LLM candidate judge | Second-pass screening and failure-mode labeling. It may recommend, down-rank, or block for review. |
| Human review gate | Only actor allowed to approve candidates for publish. |
| Validator | Only gate allowed to mark runtime-facing artifacts safe after publish. |

Product consequence: removing deterministic recall would make each run depend too
heavily on one model/prompt snapshot. Keeping it lets the producer report prove
what was reproducible, what was semantic enrichment, and what required human
judgment.

## LLM Node Placement

Add the first LLM nodes after deterministic recall, not before it.

Recommended graph:

```text
prepare_assets
register_media
build_timeline_windows
mine_candidates
llm_semantic_miner
llm_candidate_judge
cluster_candidates
human_review_gate
llm_drama_context_draft
llm_moment_pack_draft
publish_p0_bridge
validate_producer_bridge
final_report
```

`cluster_candidates` runs after `llm_candidate_judge` in the first
implementation so false positives can be down-ranked before clustering. The
report must still distinguish deterministic mechanism buckets, LLM semantic
mining, and LLM judge screening.

## Provider, Prompt, Schema, And Fixture Contract

Provider/model selection is an implementation decision, but it must be explicit
in the run artifact. Do not hide it behind a generic "LLM" label.

Recommended P0 order:

1. implement `--mock-provider` first;
2. add one real provider adapter only after schema validation passes with mocks;
3. record `provider`, `model`, `temperature`, latency, token usage, and failure
   state in `producer_job_manifest.json`.

If the project already has a default CLI/provider wrapper at implementation time,
prefer that wrapper for consistency. Otherwise choose one provider adapter and
document the choice in `.agent/dev-log.md`.

Prompt templates are tracked spec artifacts:

```text
tools/ars/prompts/llm_semantic_miner.md
tools/ars/prompts/llm_candidate_judge.md
tools/ars/prompts/llm_drama_context_draft.md
tools/ars/prompts/llm_moment_pack_draft.md
```

Each prompt must include:

- input artifact contract;
- output JSON schema name;
- product red lines: no future branch claim, no visual proof, no unconditional
  power fantasy, no narrator voice, no plot-impact disclaimer;
- source-evidence rules;
- human-review authority reminder.

Output schemas live under:

```text
data/schemas/producer_llm/llm_semantic_candidates.schema.json
data/schemas/producer_llm/llm_candidate_judgment.schema.json
data/schemas/producer_llm/llm_drama_context_draft.schema.json
data/schemas/producer_llm/llm_moment_pack_drafts.schema.json
```

Mock fixtures live under:

```text
data/fixtures/llm_mock/llm_semantic_candidates.json
data/fixtures/llm_mock/llm_candidate_judgment.json
data/fixtures/llm_mock/llm_drama_context_draft.json
data/fixtures/llm_mock/llm_moment_pack_drafts.json
```

`--mock-provider` must read these fixtures, validate them against the same
schemas, and write normal run artifacts. This lets the LangGraph + human-review
flow be tested before any real model key is available.

Default model policy: use the same model/provider for semantic mining and judge
in P0, but separate prompts and logs. P1 may split judge to a different model if
cost or quality requires it.

## LLM Node Responsibilities

### 1. `llm_semantic_miner`

Purpose: perform primary semantic understanding over timeline windows.

Deterministic mining remains broad recall and audit baseline. It should not be
treated as the main understanding layer once LLM nodes are enabled.

Input:

- timeline windows;
- deterministic candidates;
- transcript snippets;
- keyframe/contact-sheet refs as references only;
- mechanism ontology;
- Moment Field Minimum Set v0.3;
- drama title and optional short synopsis.

Output artifact:

```text
tmp/deadman_producer_runs/{run_id}/llm_semantic_candidates.json
```

Minimum output per proposed candidate:

- `candidate_id`
- `source`: `deterministic_enriched|llm_discovered`
- `source_window_id`
- `semantic_fit`: `strong|medium|weak|reject`
- `scene_summary`
- `viewer_impulse`
- `interaction_hook_suggestion`
- `action_options_suggestion`
- `field_needs`
- `credibility_risks`
- `watch_flow_risks`
- `evidence_refs_used`
- `human_review_note`

Rules:

- Do not invent facts outside the supplied transcript/window/context.
- Do not treat keyframe refs as visual proof unless image understanding is
  explicitly provided later.
- May add `llm_discovered` candidates for semantically strong windows missed by
  deterministic keywords.
- Do not promote candidates; only propose, enrich, rerank, or reject for review.
- If uncertain, mark `semantic_fit=weak` and explain what human review must
  verify.

Product consequence: deterministic recall stays cheap and broad, while the LLM
becomes the primary semantic layer that can explain, supplement, and reject
candidate moments.

### 2. `llm_candidate_judge`

Purpose: screen candidate proposals before human review.

This node acts as LLM-as-judge over both deterministic and semantic candidates.
It should be a separate pass from `llm_semantic_miner` so the producer workflow
has a second model/viewpoint checkpoint before asking a human to review.

Input:

- deterministic candidate table;
- `llm_semantic_candidates.json`;
- transcript refs and source windows;
- Moment Field Minimum Set v0.3;
- product constraints: local consequence only, no future branch claim, no visual
  proof, no unconditional power fantasy.

Output artifact:

```text
tmp/deadman_producer_runs/{run_id}/llm_candidate_judgment.json
```

Minimum output per judged candidate:

- `candidate_id`
- `judge_verdict`: `recommend|keep_for_review|reject`
- `judge_score`: integer 0-100
- `reason`
- `failure_mode`: `none|keyword_false_positive|weak_choice|too_global|branch_continuation|visual_proof_risk|overpowered_break|source_unclear|narrator_voice_risk`
- `must_human_verify`
- `recommended_review_priority`

Rules:

- Judge may reject or down-rank candidates, but cannot delete source artifacts.
- Judge may recommend human review priority, but cannot approve publication.
- Any candidate with `source_unclear`, `visual_proof_risk`, or
  `branch_continuation` must remain blocked until human review explicitly clears
  it.
- Any candidate with `narrator_voice_risk` must be rewritten or rejected before
  user-visible hook/action copy can enter a Moment Pack.
- The review request must show deterministic-vs-semantic-vs-judge disagreement.

Product consequence: human review receives a cleaner table with explicit
failure modes, instead of manually inspecting every keyword hit and every LLM
proposal from scratch.

### 3. `llm_drama_context_draft`

Purpose: draft a lightweight Drama Context Pack for producer review.

Input:

- selected episode summaries or transcript windows;
- deterministic, semantic-miner, and candidate-judge evidence;
- known drama synopsis when available;
- current Drama Context Pack schema/shape.

Output artifact:

```text
tmp/deadman_producer_runs/{run_id}/llm_drama_context_draft.json
```

Minimum output:

- `story_premise`
- `main_characters`
- `world_rules_or_genre_constraints`
- `recurring_conflicts`
- `audience_emotional_contract`
- `source_refs`
- `uncertainties`

Rules:

- Mark all inferred fields as draft.
- Do not overwrite tracked `context.v0.1.json` directly.
- Human review decides what enters promoted context.

Product consequence: the later judgment layer gets a compact story/world
orientation without requiring ArcForge-level world modeling.

### 4. `llm_moment_pack_draft`

Purpose: draft Moment Causality Pack fields for human-approved candidates.

Input:

- human-approved candidate IDs;
- source window refs;
- deterministic candidate record;
- LLM semantic-miner output;
- LLM candidate-judge output;
- Drama Context Pack draft or current context;
- Moment Causality Pack v0.3 draft schema;
- visual result policy.

Output artifact:

```text
tmp/deadman_producer_runs/{run_id}/llm_moment_pack_drafts.json
```

Minimum output per approved moment:

- `moment_id`
- `hook`
- `canon_baseline`
- `actor_local_state`
- `critical_stakes_state`
- `local_constraint_state`
- optional module fields when needed;
- `preset_actions`
- `watch_flow_rationale`
- `visual_result_policy`
- `proof_blocking_notes`
- `human_review_required`

Rules:

- Do not write tracked runtime packs directly.
- Do not claim future branch continuation.
- Do not use generated/visual output as proof.
- Do not hide uncertainty; expose uncertainty to human review.
- `hook` must sound like a watching friend, not a narrator or product tooltip:
  max 20 Chinese characters when possible, direct, emotionally responsive, and
  no exposition such as "此处可以进行互动".
- `preset_actions` must be action-language the viewer can plausibly choose, not
  analysis labels. Example good shape: `先稳住四蛋`, `低调分肉`, `直接摊牌`.

Product consequence: pack authoring becomes substantially faster while still
keeping publish authority with the producer review gate and validator.

## Provider Boundary

Provider integration is allowed only inside explicit LLM producer nodes.

Allowed:

- read API keys from environment variables only;
- write raw provider request/response logs only under ignored `tmp/`;
- produce sanitized draft artifacts under `tmp/deadman_producer_runs/{run_id}/`;
- record provider model, latency, token usage, and error state in
  `producer_job_manifest.json`.

Not allowed:

- commit provider outputs;
- print or commit API keys;
- let LLM output directly mutate tracked runtime packs;
- treat provider success as human approval;
- silently fall back to deterministic output and mark the LLM node successful.

Failure rule:

```text
provider unavailable / timeout / schema invalid
  -> LLM node status = failed or skipped_by_config
  -> graph stops unless run was explicitly started with --allow-llm-skip
  -> report states that semantic LLM enrichment was not completed
```

Default for competition-quality runs should be fail-closed, not
`--allow-llm-skip`.

## Human Review Gate

Human review must see both deterministic and LLM evidence.

`review_request.json` should include:

- deterministic candidate table path;
- LLM semantic candidates path;
- LLM candidate judgment path;
- candidate IDs recommended by deterministic rank;
- candidate IDs discovered or recommended by LLM semantic mining;
- candidate IDs recommended, kept, or rejected by LLM-as-judge;
- disagreements between deterministic rank, LLM semantic fit, and LLM judge
  verdict;
- fields requiring human verification;
- approve/reject instructions.

Human approval remains required before:

- building promoted context;
- drafting final moment packs for publish;
- writing tracked runtime files.

## Updated Graph Statuses

Producer job manifest should extend the base spec statuses with:

```text
waiting_for_llm
llm_failed
skipped_by_config
```

Terminal statuses still use the base spec's shared enum:
`failed`, `validation_failed`, `rejected_by_human_review`, or `pass`.

Each LLM node must log:

- provider/model identifier;
- input artifact refs;
- output artifact refs;
- schema validation result;
- blocked claims or uncertainty count;
- retryability.

## Producer Authority Model

Recommended authority split:

| Layer | Authority |
| --- | --- |
| Deterministic recall | Finds cheap/auditable possible windows; never final. |
| LLM semantic miner | Primary semantic understanding and candidate proposal. |
| LLM candidate judge | Pre-human screening and failure-mode labeling. |
| Human review gate | Only actor allowed to approve candidates for publish. |
| Publish script | Writes tracked runtime packs from reviewed inputs only. |
| Validator | Blocks unsafe or inconsistent runtime-facing artifacts. |

Agentic production means the LLM performs semantic labor and draft generation.
It does not mean the LLM owns publication authority.

## Test Plan

### No-provider dry run

```bash
python3 tools/ars/deadman_run_producer_graph.py dry-run \
  --run-id langgraph_llm_dry \
  --enable-llm
```

Expected:

- command/artifact plan includes the four LLM nodes;
- no provider call is made;
- no tracked runtime pack is modified.

### Provider-disabled run

```bash
python3 tools/ars/deadman_run_producer_graph.py start \
  --run-id langgraph_llm_disabled \
  --enable-llm
```

Expected when no provider env is configured:

- graph stops at first LLM node with structured `llm_failed`, or marks
  `skipped_by_config` only if `--allow-llm-skip` was explicitly passed;
- final report does not claim LLM semantic analysis ran.

### Mock-provider run

Use a local mock provider fixture that returns schema-valid LLM artifacts.

Expected:

- `llm_semantic_candidates.json` exists;
- `llm_candidate_judgment.json` exists;
- `review_request.json` includes deterministic/LLM disagreement fields;
- `resume --review-decision approve` still requires human approval before
  publish;
- producer validation remains 0 errors / 0 warnings.

### Hygiene

Verify:

- no raw provider response is committed;
- no `.env` or key literal is committed;
- tracked runtime JSON does not include provider trace, prompt text, tmp path,
  local path, or secret-bearing fields;
- public APIs do not expose producer-only LLM artifacts.

## Assumptions

- The first LLM implementation can use a mock provider before real provider
  wiring.
- Deterministic miner remains the broad recall layer.
- LLM nodes are semantic enrichment and drafting layers, not source of truth.
- Human review and producer validation remain mandatory before runtime
  consumption.
