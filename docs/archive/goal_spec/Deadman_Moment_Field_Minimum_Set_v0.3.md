# Deadman Moment Field Minimum Set v0.3 Goal Spec

> Status: ready for `/goal` execution  
> Repo: `/Users/okfin3/project/GitHub/OKFin33/OSeria-Alter`  
> Product: Branch 3 / Deadman / `要是我来`  
> Date: 2026-05-24  

## Goal Prompt

Paste this into the target execution thread:

```text
/goal
Execute the contract in /Users/okfin3/project/GitHub/OKFin33/OSeria-Alter/docs/goal_spec/Deadman_Moment_Field_Minimum_Set_v0.3.md.

Build Deadman's Moment Field Minimum Set v0.3 from the existing three-drama ARS/review artifacts for 荒年, 云渺, and 幸得相遇离婚时. Do not mine more nodes as the primary goal. Convert reviewed and high-signal candidate nodes into an explainable field-demand matrix, cluster nodes by computational field needs, cluster fields by co-necessity and substitutability, fuse overlapping fields where defensible, and produce the smallest field combination that can support credible local consequence judgment across most short-drama genres. Keep all scratch matrices, clustering reports, and intermediate review artifacts in ignored tmp paths. Promote only the final docs/schema under Deadman/docs and data/schemas. Do not commit raw media, MP4/MOV, provider outputs, API keys, local .env files, or unreviewed candidate facts as runtime truth.

Before editing or running scripts, read this contract plus docs/Moment_Causality_Pack_v0.2.md and docs/Field_Evidence_Matrix_v0.2.md. Treat v0.2 as input evidence, not final truth.
```

## Why This Goal Exists

v0.2 proved that three local short-drama sets can produce source-based ARS
artifacts and a broad field evidence matrix. That is still too thick for the
runtime contract.

This goal answers a narrower product question:

```text
What is the smallest general-purpose field combination needed for a model to
judge "要是我来" consequences credibly across most short-drama genres?
```

Nodes are evidence samples, not the deliverable. The deliverable is a minimal,
computable field set that can be consumed by:

- producer-side ARS extraction;
- backend judgment API;
- LLM judgment prompts;
- frontend result rendering.

If this step is skipped, the product risk is field bloat: every new genre adds
one-off fields, the prompt becomes harder to control, production packs become
harder to author, and the product drifts back toward ArcForge-scale world
modeling instead of Deadman moment-level consequence.

## Current Inputs

Use existing artifacts only. Do not rerun ASR unless an input is missing or
corrupt.

Source ARS candidate inputs:

```text
tmp/ars_huangnian_analysis/candidates/huangnian_candidates.v0.2.json
tmp/ars_huangnian_analysis/candidates/huangnian_mechanism_buckets.v0.2.json
tmp/ars_huangnian_analysis/candidates/huangnian_windows.v0.2.json

tmp/ars_yunmiao_analysis/candidates/yunmiao_candidates.v0.2.json
tmp/ars_yunmiao_analysis/candidates/yunmiao_mechanism_buckets.v0.2.json
tmp/ars_yunmiao_analysis/candidates/yunmiao_windows.v0.2.json

tmp/ars_lihun_analysis/candidates/lihun_candidates.v0.2.json
tmp/ars_lihun_analysis/candidates/lihun_mechanism_buckets.v0.2.json
tmp/ars_lihun_analysis/candidates/lihun_windows.v0.2.json
```

Review inputs:

```text
tmp/ars_huangnian_analysis/review/huangnian_candidates.reviewed.v0.1.json
tmp/ars_yunmiao_analysis/review/yunmiao_candidates.reviewed.v0.2.json
tmp/ars_lihun_analysis/review/lihun_candidates.reviewed.v0.2.json
```

Tracked baseline docs:

```text
docs/Moment_Causality_Pack_v0.2.md
docs/Field_Evidence_Matrix_v0.2.md
docs/MultiDrama_Field_Induction_Report_v0.2.md
data/schemas/moment_causality_pack.v0.2.json
```

Known input scale from v0.2:

| Drama | Windows | Candidates | Reviewed sample |
|---|---:|---:|---:|
| `huangnian` | 135 | 80 | 25 |
| `yunmiao` | 138 | 67 | 20 |
| `lihun` | 155 | 80 | 18 |

The reviewed migration samples are deterministic schema-evidence samples. They
are valid for field induction, but not final runtime truth.

## Objective

Produce an explainable minimum field set:

```text
three-drama reviewed/candidate nodes
  -> node-level field demand matrix
  -> demand-pattern node clusters
  -> field co-necessity clusters
  -> field fusion decisions
  -> minimum core + reusable modules + true extensions + excluded fields
  -> Moment Field Minimum Set v0.3
```

## Required Outputs

Tracked outputs:

```text
docs/Moment_Field_Minimum_Set_v0.3.md
docs/Field_Demand_Cluster_Report_v0.3.md
docs/Moment_Causality_Pack_v0.3_Draft.md
data/schemas/moment_field_minimum_set.v0.3.json
data/schemas/moment_causality_pack.v0.3.draft.json
```

Ignored scratch outputs:

```text
tmp/ars_multidrama_field_minimum_v0.3/
tmp/ars_multidrama_field_minimum_v0.3/node_field_demand_matrix.v0.3.json
tmp/ars_multidrama_field_minimum_v0.3/node_field_demand_matrix.v0.3.csv
tmp/ars_multidrama_field_minimum_v0.3/node_demand_clusters.v0.3.json
tmp/ars_multidrama_field_minimum_v0.3/field_co_necessity.v0.3.json
tmp/ars_multidrama_field_minimum_v0.3/field_fusion_decisions.v0.3.json
tmp/ars_multidrama_field_minimum_v0.3/run_report.md
```

Required script additions or updates:

```text
tools/ars/deadman_build_field_demand_matrix.py
tools/ars/deadman_induce_minimum_field_set.py
```

If one combined script is cleaner, that is acceptable, but the final run report
must document exact commands and inputs.

## Field Demand Model

Do not use opaque embedding clustering for the P0 contract. Use an explainable
discrete demand matrix.

Each candidate node receives a score for each candidate field:

| Score | Meaning | Runtime consequence |
|---:|---|---|
| `0` | Not needed | Field can be absent with no material loss. |
| `1` | Helpful context | Improves tone or detail, but judgment still works. |
| `2` | Important | Missing field makes output generic, softer, or less credible. |
| `3` | Required | Missing field prevents credible local consequence judgment. |

Each score must include a short `why_needed` note when score is `2` or `3`.

Required per-node structure:

```json
{
  "node_id": "lihun_ep06_c001",
  "drama_id": "lihun",
  "source_refs": {
    "candidate_ref": "tmp/...",
    "review_ref": "tmp/...",
    "source_window": {"start_ms": 0, "end_ms": 20000}
  },
  "node_summary": "",
  "trigger_type": "",
  "field_needs": {
    "field_name": {
      "need_score": 0,
      "why_needed": "",
      "evidence_basis": "review|candidate|transcript|inference",
      "confidence": "low|medium|high"
    }
  }
}
```

## Candidate Field Vocabulary To Test

Start from v0.2 fields, but test whether they can be fused.

Operational fields:

- `source_window`
- `review_and_provenance`
- `companion_entry`
- `action_space`
- `response_contract`
- `visual_result_policy`
- `score_axes`

Causal computation fields:

- `actor_local_state`
- `relationship_state`
- `critical_stakes_state`
- `local_constraint_state`
- `capability_rules`
- `information_asymmetry`
- `proof_state`
- `audience_reputation_state`
- `escalation_risk`
- `canon_baseline`
- `watch_flow_rationale`

Seed mapping from v0.2 to test:

| v0.2 fields | Candidate v0.3 fusion |
|---|---|
| `actor_context`, affected actors | `actor_local_state` |
| `relationship_pressure`, betrayal/family pressure | `relationship_state` |
| `resource_scarcity`, `survival_tradeoff`, `medical_or_pregnancy_risk`, safety/injury pressure | `critical_stakes_state` |
| `local_constraints`, hard scene facts, minimum safe action | `local_constraint_state` |
| `system_or_hidden_power_rule`, `hidden_power_rule`, power cap/cooldown | `capability_rules` |
| `identity_reveal`, `exposure_and_secrecy`, hidden facts | `information_asymmetry` |
| `evidence_or_trap_logic`, legal/business proof, witness proof | `proof_state` |
| `village_or_public_reputation`, public humiliation, witness/audience pressure | `audience_reputation_state` |
| `humiliation_reversal`, retaliation scale, backlash risk | `escalation_risk` |
| `canon_baseline`, `original_plot_note` | split into `canon_baseline` + `watch_flow_rationale` if both are needed |

The execution agent may propose different names, but must preserve the mapping
from old fields to new fields and explain every merge or split.

## Phase 1 - Build Node Corpus

Use all reviewed candidates from:

- `huangnian`: 25 reviewed nodes;
- `yunmiao`: 20 reviewed nodes;
- `lihun`: 18 reviewed nodes.

Also include high-signal unreviewed candidates only when needed for mechanism
coverage. Keep them explicitly labeled:

```text
reviewed
schema_evidence
candidate_only
```

Hard rule:

- reviewed nodes may influence final minimum-set decisions;
- `candidate_only` nodes may reveal missing demand types, but cannot alone
  promote a field to core.

## Phase 2 - Score Field Demand Per Node

For each node, score every candidate field from `0` to `3`.

Scoring questions:

- Would the backend/LLM judge the consequence incorrectly without this field?
- Would the output become unconditional爽 or generic commentary without it?
- Would the user stop believing "I chose this, so this consequence follows"?
- Does the field only support presentation, or does it affect causal judgment?
- Is this field a genre-specific surface detail, or a reusable computation?

Required checks:

- every score `2` or `3` has `why_needed`;
- every field with no score `3` anywhere must be challenged before entering
  core;
- every drama must have at least one representative node in every high-level
  cluster it contributes to;
- do not let drama title alone drive clustering.

## Phase 3 - Cluster Nodes By Field Demand

Cluster nodes by the discrete demand matrix, not by plot summary wording.

Recommended deterministic approach:

- convert each node to a vector of need scores;
- use cosine similarity or weighted Jaccard over fields with score `>= 2`;
- produce 4-8 demand clusters;
- name clusters by computation need, not genre.

Good cluster names:

```text
visibility_and_timing
critical_stakes_tradeoff
proof_before_reversal
capability_bound_action
public_escalation
relationship_rupture
```

Bad cluster names:

```text
divorce drama cluster
famine drama cluster
yunmiao cluster
```

Each cluster report must include:

- member node ids;
- drama distribution;
- top required fields;
- representative examples;
- fields missing from v0.2 or over-specific in v0.2;
- product implication for judgment quality.

## Phase 4 - Cluster Fields By Co-Necessity

Cluster fields by how they are required together.

Required analyses:

- high-score co-occurrence: how often two fields are both `>= 2`;
- required co-occurrence: how often two fields are both `3`;
- substitutability: whether two fields answer the same computation question;
- conflict: whether fusing them would hide meaningful differences.

Field fusion rule:

A merge is allowed only when:

1. the fields answer the same judgment question;
2. no reviewed node requires both fields with conflicting semantics;
3. the fused field can represent both cases with subkeys or typed values;
4. the merge reduces runtime/prompt complexity without losing credibility.

Example acceptable fusions to test:

- `resource_scarcity` + bodily safety + survival risk -> `critical_stakes_state`;
- `identity_reveal` + exposure/secrecy -> `information_asymmetry`;
- `evidence_or_trap_logic` + legal/business proof -> `proof_state`;
- public reputation + witness/audience pressure -> `audience_reputation_state`;
- system rules + hidden power limits -> `capability_rules`.

Example non-merge cases to watch:

- `canon_baseline` may need to stay separate from `watch_flow_rationale`;
- `source_window` should not merge with evidence review metadata;
- frontend companion copy should not merge with causal judgment fields.

## Phase 5 - Derive Minimum Set

Classify final fields into:

```text
CoreOperational
CoreCausal
ReusableCausalityModules
GenreOrStyleExtensions
ProducerOnlyFields
ExcludedFields
```

Classification rules:

- `CoreOperational`: required to locate, review, route, or display every
  moment, even if not causal.
- `CoreCausal`: required by most reviewed nodes or by the base judgment loop.
- `ReusableCausalityModules`: not universal, but useful across multiple genres
  or computation clusters.
- `GenreOrStyleExtensions`: useful for one genre/style but not yet proven
  general.
- `ProducerOnlyFields`: needed for ARS/review hygiene, not for viewer runtime.
- `ExcludedFields`: fields that imply continuous alternate branching, global
  simulation, auto-visual truth, or excessive ArcForge-style world modeling.

Minimum-set acceptance target:

- all reviewed nodes must be representable without adding one-off fields;
- every node with a score-3 demand must be covered by either core or module;
- no field enters core only because it is common in one drama;
- no genre-specific field enters core if it can be represented by a fused
  generic field;
- final core should be small enough to fit comfortably in a backend prompt and
  producer form.

If the execution agent cannot satisfy these targets, it must write a blocker
section explaining which node types force extra fields.

## Phase 6 - Produce v0.3 Docs And Schemas

`Moment_Field_Minimum_Set_v0.3.md` must include:

- one-paragraph product boundary;
- final field taxonomy;
- final minimal field table;
- old-to-new field mapping from v0.2;
- merge/split decisions;
- excluded fields and why;
- coverage summary by drama and demand cluster;
- examples showing how 荒年 / 云渺 / 离婚 nodes map into the same fields.

`Field_Demand_Cluster_Report_v0.3.md` must include:

- corpus counts;
- node demand clusters;
- field co-necessity clusters;
- merge candidates accepted/rejected;
- coverage/unmet-demand table;
- methodology notes explaining why no embedding vector was used.

`Moment_Causality_Pack_v0.3_Draft.md` must include:

- minimal JSON shape;
- required fields;
- optional module shape;
- how backend judgment should consume fields;
- how producer ARS should extract fields;
- how frontend should ignore producer-only fields.

Schemas:

- `moment_field_minimum_set.v0.3.json` describes field taxonomy and mapping.
- `moment_causality_pack.v0.3.draft.json` describes the draft pack shape.

Keep schema strict enough to guide agents, but not so strict that every module
requires a full nested ontology.

## Non-Goals

Do not:

- rerun video ingestion unless existing artifacts are missing;
- promote 云渺 or 离婚 moments to runtime packs;
- redesign frontend UI;
- modify backend judgment behavior;
- introduce embedding vector DBs;
- build an ArcForge-style full world model;
- add global inventory, full social graph, or branch timeline;
- claim visual truth from keyframes without review.

## Verification

Required commands:

```bash
python3 -m py_compile tools/ars/*.py backend/*.py backend/tests/*.py
python3 -m unittest Deadman.backend.tests.test_judgment_api -v
cd frontend && npm test
cd Runtime/frontend && npm test
python3 -m json.tool data/schemas/moment_field_minimum_set.v0.3.json >/dev/null
python3 -m json.tool data/schemas/moment_causality_pack.v0.3.draft.json >/dev/null
find Deadman Runtime/frontend docs/goal_spec -type f \( -iname '*.mp4' -o -iname '*.mov' -o -iname '.env' \) -print
rg -n --glob '!Runtime/frontend/dist/**' --glob '!frontend/dist/**' 'ark-[A-Za-z0-9-]{20,}|[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}' Deadman Runtime/frontend docs/goal_spec 2>/dev/null || true
find Deadman -type d -name __pycache__ -print
```

Expected:

- Python compile passes.
- Backend tests still pass.
- Frontend compatibility tests still pass.
- Both schemas parse as JSON.
- No MP4/MOV/.env files are added under tracked areas.
- Secret scan finds no literal keys; if it finds only regex text in this spec,
  document that as non-secret.
- Remove any generated `__pycache__` before final report.

## Required Final Report

The execution agent final report must include:

- files changed;
- corpus counts by drama;
- reviewed vs candidate-only node counts;
- node demand clusters and field clusters;
- final minimum set summary;
- accepted and rejected field fusions;
- coverage gaps or unresolved disagreements;
- verification command results;
- safety scan result;
- dev-log entry confirmation.

## Dev Log Requirement

Append one chronological entry to `.agent/dev-log.md` with `[Deadman]` prefix.

Required content:

- v0.3 minimum-field goal executed;
- whether it consumed only existing ARS/review artifacts or reran any provider;
- final tracked docs/schema names;
- the main field-compression decision;
- any remaining field-design debt.
