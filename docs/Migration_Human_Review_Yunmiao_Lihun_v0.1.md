# Migration Human Review Evidence: Yunmiao and Lihun v0.1

> Product: Deadman / `要是我来`  
> Scope: Yunmiao and Lihun migration evidence  
> Status: schema and migration evidence only; no runtime promotion  
> Date: 2026-05-25

## Boundary

This document reviews representative migration candidates from existing ARS,
review, transcript, and keyframe artifacts.

Hard rule:

```text
Every Yunmiao and Lihun node in this document is migration evidence only.
No node is promoted to runtime truth, runtime manifests, or runtime moments.
```

The "future promotion candidate" marker below means "worth product-owner and
human source review next". It does not mean the node is accepted into the
runtime pack.

## Evidence Used

Sanitized review and candidate artifacts:

- `tmp/ars_yunmiao_analysis/review/yunmiao_candidates.reviewed.v0.2.json`
- `tmp/ars_yunmiao_analysis/review/yunmiao_candidates.reviewed.v0.2.md`
- `tmp/ars_yunmiao_analysis/candidates/yunmiao_mechanism_buckets.v0.2.md`
- `tmp/ars_lihun_analysis/review/lihun_candidates.reviewed.v0.2.json`
- `tmp/ars_lihun_analysis/review/lihun_candidates.reviewed.v0.2.md`
- `tmp/ars_lihun_analysis/candidates/lihun_mechanism_buckets.v0.2.md`
- `docs/Field_Demand_Cluster_Report_v0.3.md`
- `docs/Moment_Field_Minimum_Set_v0.3.md`
- `docs/MultiDrama_Field_Induction_Report_v0.2.md`
- `docs/Field_Minimum_Red_Team_Casebook_v0.1.md`

Transcript/keyframe evidence stayed in ignored `tmp/` and is treated only as
review input:

- `tmp/ars_yunmiao_analysis/volc_asr/summary.json`
- `tmp/ars_yunmiao_analysis/volc_asr/normalized/*.normalized.json`
- `tmp/ars_yunmiao_analysis/keyframes_10s/`
- `tmp/ars_yunmiao_analysis/contact_sheets/`
- `tmp/ars_lihun_analysis/volc_asr/summary.json`
- `tmp/ars_lihun_analysis/volc_asr/normalized/*.normalized.json`
- `tmp/ars_lihun_analysis/keyframes_10s/`
- `tmp/ars_lihun_analysis/contact_sheets/`

No ASR, LLM, image, or external provider call was rerun for this review.

## Selection Method

I selected candidates that satisfy at least one of these conditions:

- high-ranked `keep` node in the existing deterministic review sample;
- covers one of the v0.3 reusable modules that matters for migration;
- appears in red-team or matrix evidence as a pressure case;
- represents a different short-drama mechanism rather than duplicating the same
  identity or betrayal beat.

All reviewed nodes below remain `review_status = schema_evidence_only`.

## Batch Review Table

### Yunmiao

| review_id | candidate_id | ep | window | hook | mechanism | v0.3 field/module demand | future promotion candidate | review_status | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `DM-MIG-YM-001` | `yunmiao_ep17_c001` | `yunmiao_ep17` | `40s-60s` | 真实身份要不要现在摊牌？ | `identity_reveal` | Core fields plus `information_asymmetry`, `relationship_state`, `audience_reputation_state`, conditional `proof_state` | yes | `schema_evidence_only` | Best visibility/timing representative; red-team case exists for `visibility_and_timing`; needs source video confirmation before promotion. |
| `DM-MIG-YM-002` | `yunmiao_ep18_c001` | `yunmiao_ep18` | `20s-40s` | 隐藏实力要不要现在亮出来？ | `hidden_power_rule` | Core fields plus `capability_rules`, `information_asymmetry`, `escalation_risk`, conditional `proof_state` | yes | `schema_evidence_only` | Best hidden-power representative; red-team case exists for `capability_bound_visibility`; promotion requires explicit power limits and proof boundary. |
| `DM-MIG-YM-003` | `yunmiao_ep16_c001` | `yunmiao_ep16` | `80s-100s` | 隐藏实力要不要现在亮出来？ | `hidden_power_rule` | Core fields plus `capability_rules`, `proof_state`, `information_asymmetry`, `watch_flow_rationale` | no | `schema_evidence_only` | Strong schema pressure for occult/power rules, but source claim needs careful human verification. |
| `DM-MIG-YM-004` | `yunmiao_ep20_c003` | `yunmiao_ep20` | `40s-60s` | 真实身份要不要现在摊牌？ | `identity_reveal` | Core fields plus `information_asymmetry`, `proof_state`, `audience_reputation_state`, `escalation_risk` | no | `schema_evidence_only` | Public accusation beat is useful for field coverage; not a promotion pick until witnesses/proof are mapped. |
| `DM-MIG-YM-005` | `yunmiao_ep03_c001` | `yunmiao_ep03` | `60s-80s` | 真实身份要不要现在摊牌？ | `identity_reveal` | Core fields plus `information_asymmetry`, `audience_reputation_state`, `escalation_risk` | no | `schema_evidence_only` | Good humiliation plus identity pressure; excerpt is truncated, so source review debt is high. |
| `DM-MIG-YM-006` | `yunmiao_ep11_c001` | `yunmiao_ep11` | `40s-60s` | 真实身份要不要现在摊牌？ | `identity_reveal` | Core fields plus `information_asymmetry`, `watch_flow_rationale`, conditional `capability_rules` | no | `schema_evidence_only` | Good schema evidence for misrecognition; too similar to other identity nodes to prioritize first. |

### Lihun

| review_id | candidate_id | ep | window | hook | mechanism | v0.3 field/module demand | future promotion candidate | review_status | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `DM-MIG-LH-001` | `lihun_ep06_c001` | `lihun_ep06` | `0s-20s` | 怀孕要不要先救再算账？ | `medical_or_pregnancy_risk` | Core fields plus `critical_stakes_state`, `relationship_state`, `proof_state`, `escalation_risk` | yes | `schema_evidence_only` | Best bodily-risk/proof representative; red-team case exists for `critical_stakes_with_proof`; promotion requires human source verification. |
| `DM-MIG-LH-002` | `lihun_ep01_c001` | `lihun_ep01` | `80s-100s` | 面对这次背叛要不要当场撕破脸？ | `relationship_betrayal` | Core fields plus `relationship_state`, `proof_state`, `critical_stakes_state`, `escalation_risk` | yes | `schema_evidence_only` | Best opening betrayal/rupture representative; promotion requires proof threshold and watch-flow wording. |
| `DM-MIG-LH-003` | `lihun_ep12_c001` | `lihun_ep12` | `40s-60s` | 孩子要不要先救再算账？ | `medical_or_pregnancy_risk` | Core fields plus `critical_stakes_state`, `proof_state`, `relationship_state`, `watch_flow_rationale` | no | `schema_evidence_only` | Strong pregnancy-harm evidence, but overlaps `DM-MIG-LH-001`; use as comparison case. |
| `DM-MIG-LH-004` | `lihun_ep19_c001` | `lihun_ep19` | `80s-100s` | 公司要不要现在打出去？ | `status_reversal` | Core fields plus `information_asymmetry`, `proof_state`, `audience_reputation_state`, `escalation_risk` | no | `schema_evidence_only` | Good status/bottom-card pressure; company leverage and public consequence need more source context. |
| `DM-MIG-LH-005` | `lihun_ep13_c001` | `lihun_ep13` | `0s-20s` | 面对小三要不要当场撕破脸？ | `relationship_betrayal` | Core fields plus `relationship_state`, `audience_reputation_state`, `proof_state`, `escalation_risk` | no | `schema_evidence_only` | Public humiliation case is useful, but needs careful safety/escalation review before any pack draft. |
| `DM-MIG-LH-006` | `lihun_ep04_c002` | `lihun_ep04` | `20s-40s` | 这笔账要不要现在摊开算？ | `evidence_or_trap` | Core fields plus `proof_state`, `information_asymmetry`, `relationship_state`, `watch_flow_rationale` | no | `schema_evidence_only` | Useful proof/trap schema evidence; not emotionally as clean as the top two candidates. |

## Detailed Review Tables

### `DM-MIG-YM-001` / `yunmiao_ep17_c001`

| Field | Value |
| --- | --- |
| `review_id` | `DM-MIG-YM-001` |
| `drama_id` | `yunmiao` |
| `drama_title` | `云渺` |
| `episode_id` | `yunmiao_ep17` |
| `source_start_seconds` | `40` |
| `source_end_seconds` | `60` |
| `candidate_hook` | 真实身份要不要现在摊牌？ |
| `scene_summary` | Existing review evidence shows a family/elder discussion about the deceased mother's unwillingness to leave and whether the stated explanation is true. The node pressures reveal timing and witness management. |
| `user_impulse` | Stop the family from hiding behind a false explanation; reveal enough truth to force accountability. |
| `why_this_is_a_good_moment` | The user's action can change the immediate confrontation without promising a new timeline. It tests whether `information_asymmetry` and public/family reputation are enough to judge a local consequence. |
| `preset_action_a` | 当场摊牌：直接指出亡母不肯走的真实原因。 |
| `preset_action_b` | 控制透露：只抛出一个关键线索，让对方自己露出破绽。 |
| `preset_action_c` | 暂不摊牌：先观察谁最害怕真相被说出来。 |
| `expected_action_types` | `reveal_now`, `controlled_hint`, `delay_reveal`, `challenge_false_story` |
| `likely_verdict_range` | Smart if reveal scope is bounded and proof/witness state is named; rash if the action invents proof or collapses later reveal value. |
| `required_core_fields` | `source_window`, `review_and_provenance`, `companion_entry`, `action_space`, `response_contract`, `visual_result_policy`, `actor_local_state`, `critical_stakes_state`, `local_constraint_state`, `escalation_risk`, `canon_baseline`, `watch_flow_rationale` |
| `required_optional_modules` | `information_asymmetry`, `relationship_state`, `audience_reputation_state`, conditional `proof_state` |
| `genre_constraints` | Hidden identity/truth timing must have cost. The result cannot use omniscience, cannot invent proof, and cannot turn a reveal into a full alternate timeline. |
| `information_asymmetry` | High. The decision is when and how much truth to reveal, who hears it, and what leverage is lost by revealing now. |
| `proof_or_evidence_state` | Weak-to-usable. Transcript and keyframes identify the beat, but they are not proof of the in-world truth. Human video review must confirm names, speaker roles, and what is known versus inferred. |
| `relationship_or_reputation_state` | Family/elder witness pressure is central; public or household reputation affects whether a reveal lands or backfires. |
| `capability_or_power_rules` | Not primary unless the action invokes supernatural authority. If invoked, it must route through `capability_rules` rather than treating power as proof. |
| `watch_flow_rationale` | A local reveal or withheld reveal can change immediate pressure while the original drama's larger reveal chain remains acceptable. |
| `source_transcript_refs` | `tmp/ars_yunmiao_analysis/review/yunmiao_candidates.reviewed.v0.2.json`; `tmp/ars_yunmiao_analysis/volc_asr/normalized/yunmiao_ep17.normalized.json` |
| `source_keyframe_refs` | `tmp/ars_yunmiao_analysis/keyframes_10s/ep17/`; `tmp/ars_yunmiao_analysis/contact_sheets/ep17_sheet.jpg` |
| `asr_quality` | `usable` |
| `visual_evidence_quality` | `usable` |
| `review_status` | `schema_evidence_only` |
| `future_promotion_candidate` | `yes`; not promoted |
| `reviewer_notes` | Best Yunmiao visibility/timing representative. Human review debt: confirm scene context, speaker identities, and whether the excerpt is enough for a local consequence pack. |

### `DM-MIG-YM-002` / `yunmiao_ep18_c001`

| Field | Value |
| --- | --- |
| `review_id` | `DM-MIG-YM-002` |
| `drama_id` | `yunmiao` |
| `drama_title` | `云渺` |
| `episode_id` | `yunmiao_ep18` |
| `source_start_seconds` | `20` |
| `source_end_seconds` | `40` |
| `candidate_hook` | 隐藏实力要不要现在亮出来？ |
| `scene_summary` | Existing evidence shows a confrontation where Yunmiao's authority or abnormality is challenged, with language around her cold gaze and outsider status. |
| `user_impulse` | Use hidden power or authority to stop disrespect and force the opposing family to take the truth seriously. |
| `why_this_is_a_good_moment` | It is the cleanest Yunmiao pressure case for preventing overpowered actions from becoming cheat outcomes. |
| `preset_action_a` | 亮出一点能力：只压住当前挑衅，不直接解决整件事。 |
| `preset_action_b` | 不亮能力：用话术逼对方暴露矛盾。 |
| `preset_action_c` | 后撤取证：先保留身份和能力，转去确认可被人类复核的线索。 |
| `expected_action_types` | `bounded_power_use`, `verbal_pressure`, `defer_for_evidence`, `protect_secret` |
| `likely_verdict_range` | Smart when power use is narrow and costly; risky or wrong when it solves everything, creates fake proof, or makes the drama unwatcheable. |
| `required_core_fields` | `source_window`, `review_and_provenance`, `companion_entry`, `action_space`, `response_contract`, `visual_result_policy`, `actor_local_state`, `critical_stakes_state`, `local_constraint_state`, `escalation_risk`, `canon_baseline`, `watch_flow_rationale` |
| `required_optional_modules` | `capability_rules`, `information_asymmetry`, `relationship_state`, conditional `proof_state`, conditional `audience_reputation_state` |
| `genre_constraints` | Hidden power must have limits, visibility consequences, and watch-flow cost. Power cannot be treated as legal or factual proof by itself. |
| `information_asymmetry` | High. The actor may possess hidden knowledge/power, but revealing it changes how others interpret identity and credibility. |
| `proof_or_evidence_state` | Weak-to-usable. Existing ARS text identifies the confrontation but does not establish all factual claims. |
| `relationship_or_reputation_state` | Household/family authority and outsider suspicion determine whether the action humiliates, escalates, or persuades. |
| `capability_or_power_rules` | Required. The pack must state power state, rule visibility, cost/cooldown, and power cap before any future promotion. |
| `watch_flow_rationale` | A bounded display can change the immediate scene while preserving the larger mystery/reveal arc. An unbounded display breaks the genre. |
| `source_transcript_refs` | `tmp/ars_yunmiao_analysis/review/yunmiao_candidates.reviewed.v0.2.json`; `tmp/ars_yunmiao_analysis/volc_asr/normalized/yunmiao_ep18.normalized.json` |
| `source_keyframe_refs` | `tmp/ars_yunmiao_analysis/keyframes_10s/ep18/`; `tmp/ars_yunmiao_analysis/contact_sheets/ep18_sheet.jpg` |
| `asr_quality` | `usable` |
| `visual_evidence_quality` | `usable` |
| `review_status` | `schema_evidence_only` |
| `future_promotion_candidate` | `yes`; not promoted |
| `reviewer_notes` | Best Yunmiao capability-boundary representative. Human review debt: verify exact power rules and avoid treating visual/keyframe evidence as proof. |

### `DM-MIG-LH-001` / `lihun_ep06_c001`

| Field | Value |
| --- | --- |
| `review_id` | `DM-MIG-LH-001` |
| `drama_id` | `lihun` |
| `drama_title` | `幸得相遇离婚时` |
| `episode_id` | `lihun_ep06` |
| `source_start_seconds` | `0` |
| `source_end_seconds` | `20` |
| `candidate_hook` | 怀孕要不要先救再算账？ |
| `scene_summary` | Existing review evidence shows a drug/pregnancy-harm setup: one party says the medicine has been swapped and frames pregnancy as the obstacle to divorce. |
| `user_impulse` | Protect the pregnant spouse/child first, while preserving enough proof to hold the harmful party accountable. |
| `why_this_is_a_good_moment` | The local consequence is clear: rescue, evidence preservation, confrontation timing, and immediate backlash can all be judged inside the scene. |
| `preset_action_a` | 先救人：阻止服药并立刻留下药物证据。 |
| `preset_action_b` | 先取证：录下关键对话，再阻止危险升级。 |
| `preset_action_c` | 当场摊牌：逼对方承认换药，但不让药物离开视线。 |
| `expected_action_types` | `rescue_first`, `evidence_preservation`, `controlled_confrontation`, `call_for_help` |
| `likely_verdict_range` | Smart if bodily safety and proof are both preserved; wrong if the action delays rescue for revenge or invents legal proof. |
| `required_core_fields` | `source_window`, `review_and_provenance`, `companion_entry`, `action_space`, `response_contract`, `visual_result_policy`, `actor_local_state`, `critical_stakes_state`, `local_constraint_state`, `escalation_risk`, `canon_baseline`, `watch_flow_rationale` |
| `required_optional_modules` | `relationship_state`, `proof_state`, conditional `audience_reputation_state`, conditional `information_asymmetry` |
| `genre_constraints` | Revenge cannot erase medical/legal cost. The result must keep rescue priority, evidence chain, and immediate social/legal risk explicit. |
| `information_asymmetry` | Medium. The hidden fact is the swapped medicine and intent; reveal timing matters, but proof and bodily risk dominate. |
| `proof_or_evidence_state` | Required. Medicine, recorded dialogue, witnesses, and chain of custody determine whether the counter-move is credible. |
| `relationship_or_reputation_state` | Betrayal/divorce pressure is central; the actor's dependence, pregnancy, and household power imbalance must be stated. |
| `capability_or_power_rules` | Not applicable for P0; no hidden-power rule should be introduced. |
| `watch_flow_rationale` | A local intervention can prevent immediate harm or preserve proof while the original divorce/revenge arc remains watchable. |
| `source_transcript_refs` | `tmp/ars_lihun_analysis/review/lihun_candidates.reviewed.v0.2.json`; `tmp/ars_lihun_analysis/volc_asr/normalized/lihun_ep06.normalized.json` |
| `source_keyframe_refs` | `tmp/ars_lihun_analysis/keyframes_10s/ep06/`; `tmp/ars_lihun_analysis/contact_sheets/ep06_sheet.jpg` |
| `asr_quality` | `usable` |
| `visual_evidence_quality` | `usable` |
| `review_status` | `schema_evidence_only` |
| `future_promotion_candidate` | `yes`; not promoted |
| `reviewer_notes` | Best Lihun critical-stakes/proof representative. Human review debt: confirm medicine action, pregnancy status, who hears what, and legal/proof wording. |

### `DM-MIG-LH-002` / `lihun_ep01_c001`

| Field | Value |
| --- | --- |
| `review_id` | `DM-MIG-LH-002` |
| `drama_id` | `lihun` |
| `drama_title` | `幸得相遇离婚时` |
| `episode_id` | `lihun_ep01` |
| `source_start_seconds` | `80` |
| `source_end_seconds` | `100` |
| `candidate_hook` | 面对这次背叛要不要当场撕破脸？ |
| `scene_summary` | Existing review evidence shows a cheating/divorce call while the spouse is being reassured separately, with pregnancy and economic pressure in the same window. |
| `user_impulse` | Confront the betrayal immediately instead of letting the spouse continue lying. |
| `why_this_is_a_good_moment` | It is a clear relationship-rupture node with proof timing and watch-flow cost, not just generic revenge. |
| `preset_action_a` | 当场揭穿：直接让通话双方知道谎言已暴露。 |
| `preset_action_b` | 留证不撕破：保存通话证据，先稳住孕期和家庭资源。 |
| `preset_action_c` | 反向试探：假装不知道，逼对方说出更多可验证信息。 |
| `expected_action_types` | `immediate_confrontation`, `evidence_preservation`, `delay_for_leverage`, `protect_self_and_child` |
| `likely_verdict_range` | Smart when proof and safety improve; emotionally satisfying but risky if confrontation destroys evidence or worsens dependency. |
| `required_core_fields` | `source_window`, `review_and_provenance`, `companion_entry`, `action_space`, `response_contract`, `visual_result_policy`, `actor_local_state`, `critical_stakes_state`, `local_constraint_state`, `escalation_risk`, `canon_baseline`, `watch_flow_rationale` |
| `required_optional_modules` | `relationship_state`, `proof_state`, `critical_stakes_state`, conditional `audience_reputation_state`, conditional `information_asymmetry` |
| `genre_constraints` | The result must preserve credible divorce/legal/social cost. It cannot become pure catharsis without accounting for pregnancy, dependency, and proof. |
| `information_asymmetry` | Medium. The betrayed spouse may know or suspect less than the viewer; action quality depends on whether the lie is exposed now or saved. |
| `proof_or_evidence_state` | Required. Call record, witness scope, and what can be proved determine whether confrontation helps. |
| `relationship_or_reputation_state` | Required. Trust rupture, pregnancy, family resource dependence, and third-party pressure all shape the consequence. |
| `capability_or_power_rules` | Not applicable. |
| `watch_flow_rationale` | The user can change the immediate rupture/proof path without requiring Deadman to simulate the whole divorce branch. |
| `source_transcript_refs` | `tmp/ars_lihun_analysis/review/lihun_candidates.reviewed.v0.2.json`; `tmp/ars_lihun_analysis/volc_asr/normalized/lihun_ep01.normalized.json` |
| `source_keyframe_refs` | `tmp/ars_lihun_analysis/keyframes_10s/ep01/`; `tmp/ars_lihun_analysis/contact_sheets/ep01_sheet.jpg` |
| `asr_quality` | `usable` |
| `visual_evidence_quality` | `usable` |
| `review_status` | `schema_evidence_only` |
| `future_promotion_candidate` | `yes`; not promoted |
| `reviewer_notes` | Best Lihun relationship-rupture representative. Human review debt: verify whether the POV actor can hear/know the call and define proof threshold before pack drafting. |

## Field Demand Comparison Against v0.3

### Yunmiao

Yunmiao does not require new core fields beyond the v0.3 minimum set.

The old v0.2-style genre labels map cleanly:

| Existing pressure | v0.3 handling | Product consequence |
| --- | --- | --- |
| `identity_reveal`, `reveal_scope`, `leverage_loss` | `information_asymmetry` | The product judges reveal timing, not whether the player "wins" by dumping all truth at once. |
| `hidden_power_rule`, `power_state`, `power_cap` | `capability_rules` | Hidden power remains bounded; otherwise Yunmiao becomes a cheat-button fantasy and the judgment is meaningless. |
| `exposure_and_secrecy`, source explanation | `information_asymmetry` plus `proof_state` when claims need evidence | The system must separate "I know this" from "the scene can prove this". |
| public accusation or humiliation reversal | `audience_reputation_state` plus `escalation_risk` | Public爽点 must price backlash and witnesses, or it becomes generic face-slapping. |

Minimum required module profile for future Yunmiao pack drafting:

- Always: full CoreOperational and CoreCausal fields.
- Usually: `information_asymmetry`, `watch_flow_rationale`.
- Often: `capability_rules`, `escalation_risk`, `audience_reputation_state`.
- Conditional: `proof_state` when the node asserts cause, guilt, ritual effect,
  or public accusation.

### Lihun

Lihun also does not require new core fields beyond the v0.3 minimum set.

The old v0.2-style genre labels map cleanly:

| Existing pressure | v0.3 handling | Product consequence |
| --- | --- | --- |
| `medical_or_pregnancy_risk`, `rescue_priority`, `accountability_delay` | `critical_stakes_state` plus `proof_state` | The product must decide rescue versus evidence timing; revenge cannot delay safety. |
| `betrayal_divorce_safety`, `rupture_cost`, `evidence_needed` | `relationship_state`, `critical_stakes_state`, `proof_state` | Divorce/revenge scenes stay credible only if dependency, safety, and proof are explicit. |
| `status_reversal_bottom_card`, `institutional_leverage`, `future_reversal_value` | `information_asymmetry`, `proof_state`, `audience_reputation_state` | Bottom-card爽点 needs public/legal/business consequence, not just a surprise identity flip. |
| `evidence_or_trap_logic`, `proof_threshold` | `proof_state` | The system needs to know what makes accusation stick. |

Minimum required module profile for future Lihun pack drafting:

- Always: full CoreOperational and CoreCausal fields.
- Usually: `relationship_state`, `proof_state`, `escalation_risk`.
- Often: `critical_stakes_state`, `audience_reputation_state`.
- Conditional: `information_asymmetry` when affairs, status, contract leverage,
  or hidden knowledge drives timing.

## Review Debt Before Any Promotion

- Human video review must verify each selected source window against the actual
  episode, not just ARS excerpts.
- Speaker identities, POV actor, visible witnesses, and known/hidden facts must
  be filled before pack drafting.
- ASR excerpts are usable for locating beats but remain review evidence, not
  in-world truth.
- Keyframes/contact sheets are visual references only. They cannot prove guilt,
  medicine status, pregnancy status, ritual effect, or legal facts.
- Promotion would require new reviewed artifacts under
  `data/dramas/{drama_id}/evidence/`, product-owner acceptance, complete
  v0.3 pack fields, adapter validation, and no runtime dependency on ignored
  `tmp/` paths.

## Safety Confirmation

- No Yunmiao or Lihun runtime manifests were created.
- No Yunmiao or Lihun runtime moments were created.
- No Huangnian runtime data was modified.
- No frontend, backend, SDK contract, or competition technical document files
  were modified for this review.
- No MP4/MOV/M4V, `.env`, raw provider output, or secrets were added.
- No external ASR, LLM, image, or provider calls were made.
