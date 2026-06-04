# Moment Field Minimum Set v0.3

> Product: Deadman / 要是我来
> Generated: 2026-05-24

## Product Boundary

Deadman judges one local `要是我来` consequence and preserves watch flow; it does not simulate a continuing alternate timeline.

The field set is intentionally moment-level. It supports local consequence judgment, not ArcForge-style continuous world simulation.

## Final Field Taxonomy

| Category | Fields |
| --- | --- |
| CoreOperational | `source_window`, `review_and_provenance`, `companion_entry`, `action_space`, `response_contract`, `visual_result_policy` |
| CoreCausal | `actor_local_state`, `critical_stakes_state`, `local_constraint_state`, `escalation_risk`, `canon_baseline`, `watch_flow_rationale` |
| ReusableCausalityModules | `relationship_state`, `capability_rules`, `information_asymmetry`, `proof_state`, `audience_reputation_state` |
| GenreOrStyleExtensions | - |
| ProducerOnlyFields | `score_axes` |
| ExcludedFields | `branch_timeline`, `global_inventory`, `full_social_graph`, `auto_visual_truth`, `return_to_plot_fit` |

## Minimal Field Table

| Field | Category | Purpose |
| --- | --- | --- |
| source_window | CoreOperational | Episode, timestamp, interaction window, and source refs required to locate the moment. |
| review_and_provenance | CoreOperational | Review status and evidence/inference boundary so producer evidence does not become runtime truth. |
| companion_entry | CoreOperational | Notice marker, hook, and friend-tone entry copy for the on-screen companion. |
| action_space | CoreOperational | Preset options plus custom-action policy, bounded to local credible consequence. |
| response_contract | CoreOperational | Short local consequence format and time horizon; no continuous branch promise. |
| visual_result_policy | CoreOperational | Preset/custom result-media policy and visual truth level. |
| actor_local_state | CoreCausal | POV actor, affected actors, roles, local intent, and immediate condition. |
| critical_stakes_state | CoreCausal | What can be lost, saved, spent, exposed, injured, or worsened by the action. |
| local_constraint_state | CoreCausal | Hard scene facts: timing, available tools, known/hidden facts, and non-negotiable limits. |
| escalation_risk | CoreCausal | Backlash, retaliation, social/legal cost, or watch-flow break risk created by the action. |
| canon_baseline | CoreCausal | Original action, original rationale, and immediate plot baseline. |
| watch_flow_rationale | CoreCausal | Why the original drama remains acceptable and the viewer can continue watching. |
| relationship_state | ReusableCausalityModules | Trust, dependency, betrayal, family/romantic pressure, and protection priority. |
| capability_rules | ReusableCausalityModules | System/hidden-power ability limits, costs, cooldowns, visibility, and overpowered guardrails. |
| information_asymmetry | ReusableCausalityModules | Identity, secrecy, hidden facts, reveal timing, and leverage loss/gain. |
| proof_state | ReusableCausalityModules | Evidence, witnesses, records, legal/business proof, and proof threshold. |
| audience_reputation_state | ReusableCausalityModules | Public witnesses, village/social reputation, humiliation, and crowd effect. |
| score_axes | ProducerOnlyFields | Producer ranking/evaluation axes; useful for ARS and QA, not viewer runtime state. |

## v0.2 To v0.3 Mapping

| v0.2 Field | v0.3 Field |
| --- | --- |
| actor_context | actor_local_state |
| affected_actors | actor_local_state |
| relationship_pressure | relationship_state |
| betrayal_divorce_safety | relationship_state + critical_stakes_state + proof_state |
| resource_scarcity | critical_stakes_state |
| survival_tradeoff | critical_stakes_state + escalation_risk |
| medical_or_pregnancy_risk | critical_stakes_state |
| local_constraints | local_constraint_state |
| system_or_hidden_power_rule | capability_rules |
| hidden_power_rule | capability_rules |
| identity_reveal | information_asymmetry |
| exposure_and_secrecy | information_asymmetry |
| evidence_or_trap_logic | proof_state |
| village_or_public_reputation | audience_reputation_state |
| humiliation_reversal | escalation_risk + audience_reputation_state |
| status_reversal_bottom_card | information_asymmetry + proof_state + audience_reputation_state |
| canon_baseline | canon_baseline |
| original_plot_note | watch_flow_rationale |
| producer_review_fields | review_and_provenance |
| score_axes | score_axes |
| visual_result_policy | visual_result_policy |

## Accepted Field Fusions

| Target | Sources | Reason |
| --- | --- | --- |
| critical_stakes_state | resource_scarcity, survival_tradeoff, medical_or_pregnancy_risk, bodily_safety, rescue_priority | All answer the same judgment question: what material or bodily stake changes if the viewer acts now? |
| information_asymmetry | identity_reveal, exposure_and_secrecy, hidden_facts, reveal_scope | Identity, secrecy, and exposure all price the timing of revealing information. |
| capability_rules | system_or_hidden_power_rule, hidden_power_rule, power_cap, cost_or_cooldown | System and hidden-power beats both need bounded capability rules to avoid cheat outcomes. |
| proof_state | evidence_or_trap_logic, legal_proof, business_proof, witness_proof, evidence_needed | These fields all decide whether a counter-move is provable rather than reckless accusation. |
| audience_reputation_state | village_or_public_reputation, witness_scope, public_effect, humiliation_context | Public witnesses and reputation pressure are the same social-visibility computation at moment scale. |
| escalation_risk | humiliation_reversal, retaliation_scale, backlash_risk, watch_flow_break_risk | 爽点 needs a visible cost/backlash channel; retaliation fields are best treated as risk, not a separate genre module. |

## Rejected Field Fusions

| Rejected Merge | Reason |
| --- | --- |
| canon_baseline, watch_flow_rationale | Baseline states what happened in canon; watch-flow rationale explains why returning to canon remains acceptable. Merging hides a product-critical distinction. |
| source_window, review_and_provenance | Time location is runtime routing; review provenance is producer trust hygiene. They fail differently. |
| companion_entry, actor_local_state | Companion copy is surface UX; actor state is causal input. Merging would pollute judgment prompts with UI text. |
| visual_result_policy, proof_state | A generated/keyframe visual is not proof. This boundary prevents auto-visual truth claims. |
| relationship_state, audience_reputation_state | Private trust pressure and public reputation can co-occur but drive different consequences. |
| capability_rules, information_asymmetry | Hidden power often implies secrecy, but ability limits and reveal timing are separate computations. |
| score_axes, field_needs | Score axes evaluate candidates; field needs are causal/context requirements for judgment. |

## Excluded Fields

| Field | Why Excluded |
| --- | --- |
| branch_timeline | Would imply the story truly follows the alternate branch. |
| global_inventory | Moment-level consequence only needs local resource/stake state. |
| full_social_graph | Local actors and witnesses are enough for P0. |
| auto_visual_truth | Generated/keyframe visuals are not evidence by themselves. |
| return_to_plot_fit | Use `watch_flow_rationale`; the product is not forcing return-to-plot simulation. |

## Fields Challenged Before Inclusion

Fields with no score-3 demand were challenged before entering the final taxonomy.

| Field | Final Category | Decision |
| --- | --- | --- |
| companion_entry | CoreOperational | No causal score 3 by design; it remains core because without a companion hook the viewer never enters the feature. |
| visual_result_policy | CoreOperational | No causal score 3; it remains core for P0 because result media needs truth-level/fallback rules even when causal judgment is text-first. |
| score_axes | ProducerOnlyFields | No runtime score 3; it is explicitly demoted from core and kept only for ARS ranking, QA, and later evaluation. |

## Coverage By Demand Cluster

| Cluster | Nodes | Drama Distribution | Top Required Fields |
| --- | --- | --- | --- |
| capability_bound_visibility | 6 | huangnian:2, yunmiao:3, lihun:1 | `capability_rules`, `watch_flow_rationale` |
| critical_stakes_tradeoff | 10 | huangnian:9, lihun:1 | `critical_stakes_state`, `escalation_risk` |
| critical_stakes_with_proof | 6 | huangnian:1, yunmiao:1, lihun:4 | `critical_stakes_state` |
| proof_before_reversal | 6 | huangnian:3, lihun:3 | `proof_state` |
| public_escalation | 12 | huangnian:5, yunmiao:3, lihun:4 | `escalation_risk`, `audience_reputation_state`, `watch_flow_rationale`, `capability_rules` |
| relationship_rupture | 10 | huangnian:4, yunmiao:1, lihun:5 | `relationship_state`, `escalation_risk` |
| visibility_and_timing | 19 | huangnian:3, yunmiao:14, lihun:2 | `information_asymmetry`, `watch_flow_rationale` |

## Cross-Genre Examples

- 荒年 resource/survival nodes map to `critical_stakes_state`, `local_constraint_state`, and `escalation_risk`; food/resource specifics no longer become standalone core fields.
- 云渺 identity/hidden-power nodes map to `information_asymmetry` plus optional `capability_rules`; cultivation surface terms stay outside core.
- 离婚 pregnancy/evidence/status nodes map to `critical_stakes_state`, `proof_state`, `relationship_state`, and `audience_reputation_state`; divorce-specific labels are not required by the runtime core.
