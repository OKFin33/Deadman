# Field Minimum Red Team v0.1

> Product: Deadman / 要是我来
> Generated: 2026-05-24
> Verdict: `pass_with_required_patch`

## Why This Exists

v0.3 compressed Deadman's field set into a small moment-level contract. This red team checks whether that compression loses the distinctions needed for credible local consequence judgment.

This is not general safety moderation. It tests field sufficiency, field ablation, fusion boundaries, adversarial viewer actions, and pressure to re-add excluded non-P0 fields.

## Method

- Used existing v0.3 matrix and cluster artifacts only.
- Did not rerun video ingestion, ASR, or providers.
- Selected representative valid reviewed/schema-evidence nodes by demand cluster and drama coverage.
- Generated deterministic user-action attacks for each representative node.
- Ran field ablation and fusion stress at the schema-contract level.

## Corpus

| Metric | Value |
| --- | --- |
| Matrix nodes | 69 |
| Valid nodes for minimum set | 59 |
| Representative nodes | 21 |
| Red-team cases | 126 |
| Cases by drama | {"huangnian": 54, "yunmiao": 30, "lihun": 42} |
| Cases by attack type | {"reasonable_smart": 21, "rash_wrong": 21, "overpowered_cheat": 21, "cross_episode_meta": 21, "unsupported_proof": 21, "visual_truth_trap": 21} |

## Pass/Fail Summary

Verdict: `pass_with_required_patch`.

The 18 active v0.3 fields are sufficient for P0 local judgment, but the backend adapter should not consume them as flat prose. Several accepted fusions need typed subkeys to preserve the distinction they intentionally compressed.

## High/Critical Findings

| ID | Severity | Title | Recommendation |
| --- | --- | --- | --- |
| FMRT-001 | high | Accepted fusions survive only if schemas require typed subkeys. | Do not split these fields. Patch the v0.3 draft schema and adapter prompt with required typed subkeys. |
| FMRT-002 | high | response_contract and watch_flow_rationale are non-removable boundary fields. | Keep return_to_plot_fit excluded; enforce local consequence plus one-line watch-flow rationale in judgment output. |
| FMRT-003 | high | visual_result_policy must explicitly block visual proof claims. | Keep auto_visual_truth excluded and add truth_level/fallback fields before image generation is wired. |

## Field Sufficiency Result

Every represented demand cluster and every attack type has a field defense in the v0.3 set. No one-off genre field was required for 荒年, 云渺, or 幸得相遇离婚时.

## Fusion Stress Result

| Accepted Fusion | Decision | Required Subkeys | Severity If Unpatched |
| --- | --- | --- | --- |
| critical_stakes_state | keep_with_typed_subkeys | stake_type, stake_owner, time_pressure, scarcity_or_risk_level, irreversibility | high |
| information_asymmetry | keep_with_typed_subkeys | hidden_fact, who_knows, who_would_learn, reveal_timing, leverage_change | high |
| capability_rules | keep_with_typed_subkeys | capability_type, hard_limit, activation_cost, visibility_cost, known_to_actor, known_to_others | high |
| proof_state | keep_with_typed_subkeys | proof_type, available_now, threshold, holder, risk_if_claimed_without_proof | medium |
| audience_reputation_state | keep_with_typed_subkeys | audience_scope, audience_alignment, status_at_stake, humiliation_vector | medium |
| escalation_risk | keep_with_typed_subkeys | risk_type, risk_source, immediacy, severity, mitigation | high |

Rejected fusions still hold:

| Rejected Merge | Still Holds | Failure If Merged |
| --- | --- | --- |
| canon_baseline, watch_flow_rationale | True | Baseline states what happened in canon; watch-flow rationale explains why returning to canon remains acceptable. Merging hides a product-critical distinction. |
| source_window, review_and_provenance | True | Time location is runtime routing; review provenance is producer trust hygiene. They fail differently. |
| companion_entry, actor_local_state | True | Companion copy is surface UX; actor state is causal input. Merging would pollute judgment prompts with UI text. |
| visual_result_policy, proof_state | True | A generated/keyframe visual is not proof. This boundary prevents auto-visual truth claims. |
| relationship_state, audience_reputation_state | True | Private trust pressure and public reputation can co-occur but drive different consequences. |
| capability_rules, information_asymmetry | True | Hidden power often implies secrecy, but ability limits and reveal timing are separate computations. |
| score_axes, field_needs | True | Score axes evaluate candidates; field needs are causal/context requirements for judgment. |

## Excluded-Field Pressure Result

| Excluded Field | Result | Fallback Policy |
| --- | --- | --- |
| branch_timeline | field_not_needed | Keep excluded. Use response_contract to produce only a local consequence and explicitly avoid future branch promises. |
| global_inventory | field_not_needed | Keep excluded. Use critical_stakes_state and local_constraint_state for moment-local resources. |
| full_social_graph | field_not_needed | Keep excluded. Use actor_local_state, relationship_state, and audience_reputation_state for local actors and witnesses. |
| auto_visual_truth | field_not_needed | Keep excluded. Use visual_result_policy to label images as illustrative/result media, not evidence. |
| return_to_plot_fit | field_not_needed | Keep excluded. Use watch_flow_rationale to explain why canon remains acceptable without simulating return-to-plot. |

## Recommended Changes Before Backend Adapter

1. Patch the v0.3 draft schema with typed subkeys for accepted fusions.
2. Keep `score_axes` producer-only and out of the viewer judgment prompt.
3. Enforce `response_contract` plus `watch_flow_rationale` in the adapter output format.
4. Add explicit `visual_result_policy.truth_level` before wiring generated images.
5. Keep excluded fields excluded for P0.
