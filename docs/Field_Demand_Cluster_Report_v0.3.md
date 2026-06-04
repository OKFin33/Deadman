# Field Demand Cluster Report v0.3

> Method: discrete `0-3` field-demand matrix. No embedding vectors were used.

## Corpus Counts

| Drama | Candidates | Reviewed/Input | Candidate-Only Added | Valid For Minimum Set |
| --- | --- | --- | --- | --- |
| huangnian | 80 | 25 | 2 | 21 |
| yunmiao | 67 | 20 | 2 | 20 |
| lihun | 80 | 18 | 2 | 18 |

- Total matrix nodes: 69
- Valid reviewed/schema-evidence nodes: 59
- Source tier counts: {'reviewed': 25, 'candidate_only': 6, 'schema_evidence': 38}

## Node Demand Clusters

| Cluster | Nodes | Drama Distribution | Top Required Fields | Product Implication |
| --- | --- | --- | --- | --- |
| capability_bound_visibility | 6 | huangnian:2, yunmiao:3, lihun:1 | `capability_rules`, `watch_flow_rationale` | Prevents hidden-power scenes from becoming unbounded cheats; the model must price both power limits and secrecy. |
| critical_stakes_tradeoff | 10 | huangnian:9, lihun:1 | `critical_stakes_state`, `escalation_risk` | For survival/resource moments, the core question is what is saved now and what cost appears immediately after. |
| critical_stakes_with_proof | 6 | huangnian:1, yunmiao:1, lihun:4 | `critical_stakes_state` | For rescue/safety moments, credible爽感 requires both immediate stakes and evidence/accountability timing. |
| proof_before_reversal | 6 | huangnian:3, lihun:3 | `proof_state` | Reversal scenes need proof state; otherwise the output becomes empty revenge copy. |
| public_escalation | 12 | huangnian:5, yunmiao:3, lihun:4 | `escalation_risk`, `audience_reputation_state`, `watch_flow_rationale`, `capability_rules` | Public humiliation scenes need audience and backlash fields to keep爽感 credible. |
| relationship_rupture | 10 | huangnian:4, yunmiao:1, lihun:5 | `relationship_state`, `escalation_risk` | Relationship scenes require trust/dependency state or the result collapses into generic breakup advice. |
| visibility_and_timing | 19 | huangnian:3, yunmiao:14, lihun:2 | `information_asymmetry`, `watch_flow_rationale` | Identity or secrecy moments depend on when information is revealed, not just whether the viewer can win. |

## Field Co-Necessity Clusters

| Field Cluster | Fields | Reason |
| --- | --- | --- |
| runtime_surface_and_routing | `source_window`, `companion_entry`, `action_space`, `response_contract`, `visual_result_policy` | These fields locate, invite, route, and present the interaction. |
| producer_trust_and_selection | `review_and_provenance`, `score_axes` | These fields keep ARS/review evidence auditable and help pick/promote moments. |
| base_local_causality | `actor_local_state`, `critical_stakes_state`, `local_constraint_state`, `escalation_risk`, `canon_baseline`, `watch_flow_rationale` | These are the minimum fields needed to answer local credible consequence without branching the story. |
| information_power_and_proof | `information_asymmetry`, `capability_rules`, `proof_state` | These often co-occur in reversal scenes but remain separable computations. |
| social_pressure_modules | `relationship_state`, `audience_reputation_state` | Private relation pressure and public reputation pressure are reusable modules, not universal core. |

## Highest Variable Field Co-Occurrences

| Field Pair | Both Score >= 2 | Both Score = 3 |
| --- | --- | --- |
| `information_asymmetry`, `watch_flow_rationale` | 40 | 14 |
| `audience_reputation_state`, `escalation_risk` | 27 | 7 |
| `escalation_risk`, `watch_flow_rationale` | 59 | 3 |
| `audience_reputation_state`, `watch_flow_rationale` | 27 | 3 |
| `capability_rules`, `watch_flow_rationale` | 9 | 3 |
| `relationship_state`, `escalation_risk` | 41 | 2 |
| `critical_stakes_state`, `escalation_risk` | 59 | 1 |
| `critical_stakes_state`, `watch_flow_rationale` | 59 | 0 |
| `relationship_state`, `critical_stakes_state` | 41 | 0 |
| `relationship_state`, `watch_flow_rationale` | 41 | 0 |
| `critical_stakes_state`, `information_asymmetry` | 40 | 0 |
| `information_asymmetry`, `escalation_risk` | 40 | 0 |
| `critical_stakes_state`, `audience_reputation_state` | 27 | 0 |
| `information_asymmetry`, `audience_reputation_state` | 23 | 0 |
| `relationship_state`, `information_asymmetry` | 22 | 0 |
| `critical_stakes_state`, `proof_state` | 19 | 0 |

## Accepted Merge Candidates

| Target | Sources | Reason |
| --- | --- | --- |
| critical_stakes_state | resource_scarcity, survival_tradeoff, medical_or_pregnancy_risk, bodily_safety, rescue_priority | All answer the same judgment question: what material or bodily stake changes if the viewer acts now? |
| information_asymmetry | identity_reveal, exposure_and_secrecy, hidden_facts, reveal_scope | Identity, secrecy, and exposure all price the timing of revealing information. |
| capability_rules | system_or_hidden_power_rule, hidden_power_rule, power_cap, cost_or_cooldown | System and hidden-power beats both need bounded capability rules to avoid cheat outcomes. |
| proof_state | evidence_or_trap_logic, legal_proof, business_proof, witness_proof, evidence_needed | These fields all decide whether a counter-move is provable rather than reckless accusation. |
| audience_reputation_state | village_or_public_reputation, witness_scope, public_effect, humiliation_context | Public witnesses and reputation pressure are the same social-visibility computation at moment scale. |
| escalation_risk | humiliation_reversal, retaliation_scale, backlash_risk, watch_flow_break_risk | 爽点 needs a visible cost/backlash channel; retaliation fields are best treated as risk, not a separate genre module. |

## Rejected Merge Candidates

| Rejected Merge | Reason |
| --- | --- |
| canon_baseline, watch_flow_rationale | Baseline states what happened in canon; watch-flow rationale explains why returning to canon remains acceptable. Merging hides a product-critical distinction. |
| source_window, review_and_provenance | Time location is runtime routing; review provenance is producer trust hygiene. They fail differently. |
| companion_entry, actor_local_state | Companion copy is surface UX; actor state is causal input. Merging would pollute judgment prompts with UI text. |
| visual_result_policy, proof_state | A generated/keyframe visual is not proof. This boundary prevents auto-visual truth claims. |
| relationship_state, audience_reputation_state | Private trust pressure and public reputation can co-occur but drive different consequences. |
| capability_rules, information_asymmetry | Hidden power often implies secrecy, but ability limits and reveal timing are separate computations. |
| score_axes, field_needs | Score axes evaluate candidates; field needs are causal/context requirements for judgment. |

## Coverage And Gaps

- All valid reviewed/schema-evidence nodes are representable without adding one-off fields.
- Candidate-only nodes are used only as missing-mechanism probes and do not promote fields to core.
- `relationship_state`, `capability_rules`, `information_asymmetry`, `proof_state`, and `audience_reputation_state` remain reusable modules because they are cross-genre but not universal.
- Human review is still required before promoting 云渺 or 离婚 nodes into runtime packs.

## Why No Embedding Vector

The target is a minimum computable contract, not semantic retrieval. Embeddings would cluster by topic and wording; the discrete matrix clusters by what the judgment actually needs.
