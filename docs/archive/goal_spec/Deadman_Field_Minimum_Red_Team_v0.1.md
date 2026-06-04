# Deadman Field Minimum Red Team v0.1 Goal Spec

> Status: ready for `/goal` execution  
> Repo: `/Users/okfin3/project/GitHub/OKFin33/OSeria-Alter`  
> Product: Branch 3 / Deadman / `要是我来`  
> Date: 2026-05-24  

## Goal Prompt

Paste this into the target execution thread:

```text
/goal
Execute the contract in /Users/okfin3/project/GitHub/OKFin33/OSeria-Alter/docs/goal_spec/Deadman_Field_Minimum_Red_Team_v0.1.md.

Run a Deadman-specific red team pass for the Moment Field Minimum Set v0.3. The purpose is not general safety evaluation and not finding more implantable moments. The purpose is to test whether the v0.3 minimum field clustering is too compressed, too broad, or missing any field needed for credible local consequence judgment across 荒年, 云渺, and 幸得相遇离婚时. Use existing v0.3 field-demand matrix and cluster artifacts as inputs. Generate a red-team casebook, field ablation analysis, fusion-risk analysis, and a pass/fail report. Keep scratch outputs in ignored tmp paths. Promote only the final docs/eval JSON/schema under Deadman docs/data. Do not rerun ASR/video ingestion/provider calls unless a required input is missing or corrupt.

Before editing or running scripts, read this contract plus docs/Moment_Field_Minimum_Set_v0.3.md and docs/Field_Demand_Cluster_Report_v0.3.md. Treat 云渺 and 离婚 nodes as schema-evidence only, not runtime-promoted truth.
```

## Why This Red Team Is Necessary

v0.3 reduced Deadman from a broad field list into:

- 6 `CoreOperational` fields;
- 6 `CoreCausal` fields;
- 5 reusable causality modules;
- 1 producer-only field;
- 5 excluded fields.

That compression is useful only if it survives adversarial pressure. A smaller
field set lowers producer cost and backend prompt complexity, but it can fail in
three ways:

1. **Underfit**: a compressed field hides a distinction the judgment actually
   needs, so the model gives plausible but wrong consequences.
2. **Overfit**: a field looks general because the current three dramas happen
   to share it, but it will not generalize.
3. **Boundary leak**: the model uses fields to imply continuous branch
   simulation, visual proof, global world state, or unsupported future changes.

The product consequence is direct: if v0.3 is wrong, users may get outputs that
are爽 but not可信, or outputs that make the original drama feel stupid enough
that they do not want to keep watching.

This is a **field-contract red team**, not a content moderation red team.

## Inputs

Tracked field baseline:

```text
docs/Moment_Field_Minimum_Set_v0.3.md
docs/Field_Demand_Cluster_Report_v0.3.md
docs/Moment_Causality_Pack_v0.3_Draft.md
data/schemas/moment_field_minimum_set.v0.3.json
data/schemas/moment_causality_pack.v0.3.draft.json
```

Ignored matrix/cluster artifacts:

```text
tmp/ars_multidrama_field_minimum_v0.3/node_field_demand_matrix.v0.3.json
tmp/ars_multidrama_field_minimum_v0.3/node_demand_clusters.v0.3.json
tmp/ars_multidrama_field_minimum_v0.3/field_co_necessity.v0.3.json
tmp/ars_multidrama_field_minimum_v0.3/field_fusion_decisions.v0.3.json
```

Optional source references for examples only:

```text
tmp/ars_huangnian_analysis/candidates/
tmp/ars_yunmiao_analysis/candidates/
tmp/ars_lihun_analysis/candidates/
```

Do not use raw videos or provider outputs unless an example needs timestamp
cross-checking. If that happens, document it.

## Objective

Produce a defensible red-team result:

```text
v0.3 minimum field set
  -> representative node corpus by demand cluster
  -> adversarial user-action cases
  -> field ablation checks
  -> accepted-fusion stress checks
  -> rejected-fusion boundary checks
  -> pass/fail findings
  -> required schema or prompt recommendations
```

The red team should answer:

- Are 18 active fields enough?
- Which core fields are truly non-removable?
- Which reusable modules are correctly optional?
- Did any accepted fusion lose a critical distinction?
- Did any rejected fusion deserve reconsideration?
- Are excluded fields still correctly excluded under adversarial pressure?

## Required Outputs

Tracked outputs:

```text
docs/Field_Minimum_Red_Team_v0.1.md
docs/Field_Minimum_Red_Team_Casebook_v0.1.md
docs/Field_Minimum_Red_Team_Findings_v0.1.md
data/evals/field_minimum_red_team.v0.1.json
data/schemas/field_minimum_red_team_case.v0.1.json
```

Ignored scratch outputs:

```text
tmp/ars_multidrama_field_redteam_v0.1/
tmp/ars_multidrama_field_redteam_v0.1/red_team_cases.v0.1.json
tmp/ars_multidrama_field_redteam_v0.1/field_ablation.v0.1.json
tmp/ars_multidrama_field_redteam_v0.1/fusion_stress.v0.1.json
tmp/ars_multidrama_field_redteam_v0.1/run_report.md
```

Required script:

```text
tools/ars/deadman_redteam_field_minimum.py
```

The script may be deterministic. Do not add a provider dependency unless the
run report explains why deterministic red-team construction was insufficient.

## Red Team Scope

### Lane A - Field Sufficiency

For every demand cluster in v0.3, pick representative nodes and ask whether the
current field set can represent the consequence without one-off fields.

Minimum coverage:

- every v0.3 node demand cluster;
- every `CoreCausal` field;
- every `ReusableCausalityModules` field;
- all three dramas;
- at least 60 red-team cases.

Preferred corpus:

- 2-3 representative valid nodes per demand cluster;
- at least 5 valid nodes from each drama;
- candidate-only nodes may be used as edge probes but cannot determine pass/fail.

### Lane B - Field Ablation

For each active field, generate at least one ablation check:

```text
If this field is absent or collapsed into another field, what exact failure
would appear in judgment?
```

Examples:

- remove `proof_state` from a proof-before-reversal node;
- remove `watch_flow_rationale` from an identity-reveal node;
- remove `critical_stakes_state` from a survival or pregnancy-risk node;
- remove `capability_rules` from a hidden-power node.

The output must classify the ablation result:

```text
no_material_loss
degrades_quality
breaks_credibility
breaks_runtime
```

### Lane C - Fusion Stress

Stress every accepted fusion from v0.3:

- `critical_stakes_state`;
- `information_asymmetry`;
- `capability_rules`;
- `proof_state`;
- `audience_reputation_state`;
- `escalation_risk`.

For each fusion:

- find at least two nodes from different dramas or mechanisms;
- state what the fused field preserves;
- state what distinction might be lost;
- decide whether to keep the fusion, split it, or add typed subkeys.

Also stress rejected fusions:

- `canon_baseline` vs `watch_flow_rationale`;
- `source_window` vs `review_and_provenance`;
- `visual_result_policy` vs `proof_state`;
- `relationship_state` vs `audience_reputation_state`;
- `capability_rules` vs `information_asymmetry`.

The report must say whether each rejection still holds.

### Lane D - User Action Attacks

For selected nodes, generate adversarial user actions:

| Attack Type | Example intent | Expected field defense |
|---|---|---|
| `reasonable_smart` | User makes a plausible better choice. | Core fields should yield satisfying consequence. |
| `rash_wrong` | User acts emotionally but badly. | `escalation_risk`, `relationship_state`, `critical_stakes_state`. |
| `overpowered_cheat` | User asks to solve everything instantly. | `capability_rules`, `response_contract`, `watch_flow_rationale`. |
| `cross_episode_meta` | User uses future knowledge or asks later plot to change. | `response_contract`, `canon_baseline`, excluded `branch_timeline`. |
| `unsupported_proof` | User claims evidence/witnesses that do not exist. | `proof_state`, `review_and_provenance`. |
| `visual_truth_trap` | User treats generated/keyframe image as proof. | `visual_result_policy`, excluded `auto_visual_truth`. |

Each case must include:

```json
{
  "case_id": "rt_v01_0001",
  "node_id": "",
  "drama_id": "",
  "demand_cluster": "",
  "attack_type": "",
  "user_action": "",
  "expected_required_fields": [],
  "expected_failure_if_missing": [],
  "should_pass": true,
  "red_team_rationale": "",
  "severity_if_failed": "low|medium|high|critical"
}
```

### Lane E - Excluded Field Pressure

Try to force the system to need excluded fields:

- `branch_timeline`;
- `global_inventory`;
- `full_social_graph`;
- `auto_visual_truth`;
- `return_to_plot_fit`.

The expected result is not to add these fields. The expected result is a clear
fallback policy:

- local consequence only;
- no global mutation;
- no continuous branch promise;
- no visual proof claim;
- use `watch_flow_rationale`, not `return_to_plot_fit`.

If a case genuinely cannot be handled without an excluded field, mark it as a
blocker and explain the product cost.

## Pass/Fail Criteria

The v0.3 field set passes this red team only if:

- every valid reviewed/schema-evidence node can be represented by core fields
  plus optional modules;
- every attack type has an expected field defense;
- no accepted fusion creates a high-severity ambiguity without a proposed subkey;
- every rejected fusion still has a clear failure mode if merged;
- excluded fields are not needed for P0 behavior;
- `watch_flow_rationale` remains enough to preserve viewer return-to-drama.

Severity definitions:

| Severity | Meaning |
|---|---|
| `low` | Wording or UX clarity issue. |
| `medium` | Output gets generic or less emotionally satisfying. |
| `high` | Consequence becomes materially implausible or loses key scene logic. |
| `critical` | Product boundary breaks: continuous alternate timeline, unsupported truth, or unconditional cheat. |

If there are high/critical findings, do not hide them under a pass label. Mark
the field set as `pass_with_required_patch` or `fail_pending_schema_revision`.

## Required Documents

### `Field_Minimum_Red_Team_v0.1.md`

Must include:

- why red team is necessary after field compression;
- methodology;
- corpus selection;
- pass/fail summary;
- field sufficiency result;
- fusion stress result;
- excluded-field pressure result;
- recommended changes before backend adapter consumes v0.3.

### `Field_Minimum_Red_Team_Casebook_v0.1.md`

Must include:

- all red-team cases in table form;
- node id, drama, cluster, attack type;
- expected required fields;
- expected failure if missing;
- severity.

### `Field_Minimum_Red_Team_Findings_v0.1.md`

Must include:

- findings ordered by severity;
- affected fields;
- affected clusters;
- concrete product consequence;
- recommended fix or decision to accept risk.

### `field_minimum_red_team.v0.1.json`

Must include:

- metadata;
- corpus counts;
- case list;
- ablation results;
- fusion stress results;
- excluded-field pressure results;
- final verdict.

### `field_minimum_red_team_case.v0.1.json`

Must define the red-team case schema.

## Non-Goals

Do not:

- turn this into general safety moderation;
- run a full LLM output eval unless explicitly needed;
- modify backend judgment behavior;
- modify frontend UI;
- promote 云渺 or 离婚 runtime packs;
- rerun video ingestion/ASR by default;
- add embedding or vector DB infrastructure;
- add excluded fields just because an attack asks for them.

## Verification

Required commands:

```bash
python3 -m py_compile tools/ars/*.py backend/*.py backend/tests/*.py
python3 -m unittest Deadman.backend.tests.test_judgment_api -v
cd frontend && npm test
cd Runtime/frontend && npm test
python3 -m json.tool data/evals/field_minimum_red_team.v0.1.json >/dev/null
python3 -m json.tool data/schemas/field_minimum_red_team_case.v0.1.json >/dev/null
find Deadman Runtime/frontend docs/goal_spec -type f \( -iname '*.mp4' -o -iname '*.mov' -o -iname '.env' \) -print
rg -n --glob '!Runtime/frontend/dist/**' --glob '!frontend/dist/**' 'ark-[A-Za-z0-9-]{20,}|[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}' Deadman Runtime/frontend docs/goal_spec 2>/dev/null || true
find Deadman -type d -name __pycache__ -print
```

Expected:

- Python compile passes.
- Backend/frontend tests still pass.
- Red-team JSON and schema parse.
- No MP4/MOV/.env files are added under tracked areas.
- Secret scan finds no literal keys; if it only finds regex text in this spec,
  document it as non-secret.
- Remove generated `__pycache__` before final report.

## Dev Log Requirement

Append one chronological entry to `.agent/dev-log.md` with `[Deadman]` prefix.

Required content:

- red team executed for v0.3 minimum field clustering;
- whether it used only existing matrix/ARS artifacts or reran any provider;
- tracked docs/eval outputs;
- verdict;
- required schema/adapter follow-up.

## Required Final Report

The execution agent final report must include:

- files changed;
- whether provider/video processing was rerun;
- corpus counts and case counts;
- pass/fail verdict;
- high/critical findings;
- accepted/rejected fusion status;
- excluded-field pressure result;
- recommended follow-up before backend adapter work;
- verification results;
- safety scan result;
- dev-log confirmation.
