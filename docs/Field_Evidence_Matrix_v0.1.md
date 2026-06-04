# Field Evidence Matrix v0.1

> Basis: `tmp/ars_huangnian_analysis/review/huangnian_candidates.reviewed.v0.1.json`  
> Rule: a field is core only when multiple reviewed candidates need it across different mechanisms.

## Review Set

- Reviewed candidates: 25
- Status counts: `demo_candidate=5`, `pack_draft=5`, `keep=11`, `reject=4`
- Selected demo node IDs:
  - `huangnian_ep12_c001`
  - `huangnian_ep07_c001`
  - `huangnian_ep03_c001`
  - `huangnian_ep04_c001`
  - `huangnian_ep06_c001`

## Core Field Decisions

| Field | Evidence | Decision |
|---|---|---|
| `source_window` | Every reviewed node needs episode/time/transcript/keyframe provenance. | Core |
| `review_state` | Every promoted or rejected node needs status, evidence grade, and notes. | Core |
| `companion_surface.hook` | All demo nodes require revised scene-specific hooks; first-pass generic hooks failed review. | Core |
| `viewer_impulse` | Present across resource, humiliation, evidence, system, and exposure nodes. | Core |
| `actor_context` | Needed by `ep12`, `ep07`, `ep04`, `ep06`; without actors the consequence is generic. | Core |
| `local_constraints` | Needed across scarcity, exposure, system, evidence, and relationship pressure. | Core |
| `canon_baseline` | Required to explain why original watching flow still works after an alternate local choice. | Core |
| `action_space.default_options` | Required for the P0 companion button flow. | Core |
| `custom_action_policy` | Required because users can type, but scope must stay local. | Core |
| `judgment_policy` | Required to stop continuous branching and unsupported source claims. | Core |
| `outcome_response_contract` | Required by every node: local credible consequence, not rewritten future episodes. | Core |
| `watch_flow_fit` | Required across all promoted nodes; replaces `return_to_plot_fit`. | Core |
| `visual_result_policy` | Core as a guardrail, but not as a guarantee of visual truth. | Core |
| `producer_review_fields` | Required because ARS outputs are semi-automatic bridge evidence. | Core |

## Optional Field Decisions

| Optional module / field | Reviewed candidates | Evidence strength | Decision |
|---|---|---:|---|
| `resource_scarcity.resource_type` | `ep12_c001`, `ep15_c001`, `ep16_c001`, `ep17_c003` | Strong in `荒年` | Optional module |
| `resource_scarcity.distribution_target` | `ep12_c001`, `ep15_c001`, `ep07_c001` | Strong in `荒年` | Optional module |
| `exposure_and_secrecy.source_explanation` | `ep06_c001`, `ep03_c001`, `ep04_c003` | Strong in `荒年`; expected cross-genre | Optional module now; candidate core axis after migration |
| `relationship_pressure.trust_delta_policy` | `ep07_c001`, `ep12_c001`, `ep14_c001`, `ep01_c001` | Strong in `荒年` | Optional module |
| `village_or_public_reputation.witnesses` | `ep04_c001`, `ep04_c002`, `ep14_c002` | Medium | Optional module |
| `evidence_or_trap_logic.evidence_refs` | `ep04_c001`, `ep20_c003`, `ep04_c005` | Medium | Optional module |
| `system_or_hidden_power_rule.rule_visibility` | `ep03_c001`, `ep04_c003`, `ep03_c002` | Medium in `荒年`; likely strong in `云渺1` | Optional module |
| `humiliation_reversal.retaliation_scale` | `ep07_c001`, `ep10_c001`, `ep09_c002` | Medium | Optional module |
| `survival_tradeoff.minimum_safe_action` | `ep15_c001`, `ep15_c002`, `ep06_c001` | Medium | Optional module |
| `power_cap` | `ep03_c001`, `ep04_c004`, `ep03_c002` | Low-medium; mostly guardrail evidence | Optional guardrail |

## Candidate-to-Field Matrix

| Candidate | Status | Corrected trigger | Core fields stressed | Optional modules stressed |
|---|---|---|---|---|
| `huangnian_ep12_c001` | `demo_candidate` | `resource_visibility` | source window, hook, actors, canon baseline, watch flow, review state | `resource_scarcity`, `relationship_pressure` |
| `huangnian_ep07_c001` | `demo_candidate` | `humiliation_reversal` | hook, actor context, local constraints, action space, outcome contract | `humiliation_reversal`, `relationship_pressure` |
| `huangnian_ep03_c001` | `demo_candidate` | `system_rule` | source window, hidden facts, custom action policy, judgment policy | `system_or_hidden_power_rule`, `exposure_and_secrecy` |
| `huangnian_ep04_c001` | `demo_candidate` | `evidence_or_trap` | witnesses, canon baseline, action routing, review notes | `evidence_or_trap_logic`, `village_or_public_reputation` |
| `huangnian_ep06_c001` | `demo_candidate` | `exposure_risk` | local constraints, canon baseline, watch flow, evidence notes | `exposure_and_secrecy`, `resource_scarcity` |
| `huangnian_ep15_c001` | `pack_draft` | `survival_tradeoff` | original plot note, action space, watch flow | `survival_tradeoff`, `resource_scarcity` |
| `huangnian_ep04_c002` | `pack_draft` | `village_pressure` | public setting, source window, review state | `village_or_public_reputation`, `evidence_or_trap_logic` |
| `huangnian_ep10_c001` | `pack_draft` | `humiliation_reversal` | actor context, local consequence, review state | `humiliation_reversal` |
| `huangnian_ep04_c003` | `pack_draft` | `system_rule` | hook, hidden facts, judgment policy | `system_or_hidden_power_rule` |
| `huangnian_ep20_c003` | `keep` | `evidence_or_trap` | canon baseline, action space, local consequence | `evidence_or_trap_logic`, `relationship_pressure` |

## Fields Not Promoted To Core

- `resource_type`: `荒年` needs it constantly, but revenge and hidden-power genres may not.
- `scarcity_level`: strong for famine, not universal.
- `witness_scope`: common, but absent in intimate family-only scenes; keep optional.
- `power_cap`: essential for system/cultivation moments, not for ordinary relationship beats.
- `trust_delta_policy`: important, but some evidence/trap nodes are primarily public/procedural.
- `visual_evidence.high`: not core because current ARS only knows keyframe refs exist.

## Evidence Caution

The matrix uses reviewed `荒年` candidates as evidence for field pressure. It
does not use summary-based migration stress tests as source evidence. Migration
can change optional/core confidence only after local media or comparable
scene-level evidence exists.
