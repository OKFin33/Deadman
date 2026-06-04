# Moment Causality Pack v0.1 Draft

> Product: Deadman / `要是我来`  
> Basis: reviewed `荒年` ARS candidates in `tmp/ars_huangnian_analysis/review/huangnian_candidates.reviewed.v0.1.json`  
> Status: draft contract for P0 integration, not final production authoring

## 0. Contract Boundary

`MomentCausalityPack v0.1` answers one local question:

```text
要是你在这一刻这么做，当前局面里可信后果是什么？
```

It does not promise that later episodes truly branch. Every pack must keep
evidence separate from reviewed product inference:

- Evidence: source window, ASR excerpt, keyframe/contact-sheet refs, reviewed evidence notes.
- Inference: companion hook, revised options, local consequence framing, scoring and routing.

Do not add `return_to_plot_fit` as a core score. P0 uses `watch_flow_fit`:
whether the interaction can finish and let the viewer keep watching the
original drama without making the original choice look stupid.

## 1. CoreEnvelope

Fields required by every P0 moment node.

```json
{
  "pack_id": "huangnian_ep12_m001",
  "schema_version": "moment_causality_pack.v0.1",
  "source_drama": {
    "title": "荒年全村啃树皮，我有系统满仓肉",
    "episode_id": "huangnian_ep12",
    "source_policy": "local media + ASR/keyframe evidence; reviewed human notes required before demo"
  },
  "source_window": {
    "start_ms": 0,
    "end_ms": 20000,
    "transcript_refs": [],
    "keyframe_refs": [],
    "contact_sheet_ref": ""
  },
  "review_state": {
    "status": "demo_candidate",
    "reviewed_at": "2026-05-24",
    "evidence_grade": "low|medium|high",
    "evidence_notes": "",
    "evidence_vs_inference": ""
  },
  "companion_surface": {
    "notice_marker": "!|?",
    "hook": "",
    "viewer_impulse": "",
    "scene_specificity_check": "must name an object, relation, witness, rule, or decision pressure from the source window"
  },
  "actor_context": {
    "pov_actor": "",
    "directly_affected_actors": [],
    "relationship_context": "",
    "local_emotional_pressure": ""
  },
  "local_constraints": {
    "known_facts": [],
    "unknown_or_hidden_facts": [],
    "hard_constraints": [],
    "risk_notes": []
  },
  "canon_baseline": {
    "original_action": "",
    "original_rationale": "",
    "audience_tension": "",
    "original_plot_note": ""
  },
  "action_space": {
    "action_type": "resource|exposure|relationship|evidence|system_rule|humiliation|survival|other",
    "default_options": [],
    "custom_action_policy": {
      "allowed": true,
      "scope": "local credible consequence only",
      "reject_or_soften": []
    }
  },
  "judgment_policy": {
    "must_consider": [],
    "must_not_claim": [
      "later episodes actually follow this branch",
      "facts not present in source evidence",
      "unbounded system or power escalation"
    ]
  },
  "outcome_response_contract": {
    "format": "short local consequence + why original plot still remains watchable",
    "time_horizon": "current scene or immediate aftermath",
    "include_original_plot_note": true
  },
  "visual_result_policy": {
    "allowed": "result card or still prompt only when object/person is evidenced",
    "keyframe_ref_quality": "none|low|medium",
    "visual_evidence": "low|medium|high"
  },
  "score_axes": {
    "emotion_heat": 0,
    "choice_leverage": 0,
    "causal_clarity": 0,
    "world_constraint_value": 0,
    "watch_flow_fit": 0,
    "visual_result_fit": 0
  },
  "producer_review_fields": {
    "reviewer_notes": "",
    "field_evidence_refs": [],
    "open_questions": [],
    "do_not_promote_reasons": []
  }
}
```

Core fields are not all equally rich in every scene. A gentle relationship
moment may have no `resource` module, but it still needs source provenance,
actor context, local constraints, action space, watch-flow handling, and review
state.

## 2. OptionalCausalityModules

Only attach these modules when the reviewed candidate needs them.

### `resource_scarcity`

Used by `huangnian_ep12_c001`, `huangnian_ep15_c001`, and several kept nodes.

Required when present:

- `resource_type`
- `quantity_or_visibility`
- `scarcity_level`
- `distribution_target`
- `defer_cost`

### `exposure_and_secrecy`

Used by `huangnian_ep06_c001` and system-related nodes.

Required when present:

- `visible_advantage`
- `source_explanation`
- `witness_scope`
- `suspicion_risk`
- `concealment_strategy`

### `relationship_pressure`

Used by `huangnian_ep07_c001`, `huangnian_ep12_c001`, and family repair nodes.

Required when present:

- `relationship_role`
- `prior_trust_damage`
- `care_priority`
- `trust_delta_policy`
- `repair_pace`

### `village_or_public_reputation`

Used by `huangnian_ep04_c001` / `huangnian_ep04_c002`.

Required when present:

- `witnesses`
- `public_claim`
- `reputation_delta`
- `exchange_dependency`
- `escalation_risk`

### `evidence_or_trap_logic`

Used by `huangnian_ep04_c001` and `huangnian_ep20_c003`.

Required when present:

- `evidence_refs`
- `claim_account`
- `counter_claim_shape`
- `counterparty_leverage`
- `proof_threshold`

### `system_or_hidden_power_rule`

Used by `huangnian_ep03_c001`, `huangnian_ep04_c003`, and migration stress
tests for `云渺1`.

Required when present:

- `power_or_system_action`
- `rule_visibility`
- `cost_or_cooldown`
- `world_explanation`
- `power_cap`

### `humiliation_reversal`

Used by `huangnian_ep07_c001` and lower-ranked `huangnian_ep10_c001`.

Required when present:

- `harm_state`
- `retaliation_scale`
- `protected_actor`
- `escalation_risk`
- `dignity_repair`

### `survival_tradeoff`

Used by `huangnian_ep15_c001` and scarcity nodes.

Required when present:

- `survival_need`
- `resource_quality`
- `who_pays_cost`
- `long_term_risk`
- `minimum_safe_action`

## 3. NonP0Fields

Do not add these to v0.1:

- `branch_timeline`: implies continuous alternate-episode simulation.
- `return_to_plot_fit`: old framing; use `watch_flow_fit`.
- `global_inventory`: only local resource notes are needed for P0.
- `full_social_graph`: local actors/witnesses are enough.
- `long_term_relationship_simulation`: P0 can emit local trust deltas only.
- `auto_visual_truth`: keyframes are references unless reviewed or machine-interpreted.

## 4. ProducerReviewFields

These fields exist to stop the bridge from laundering inference into evidence:

- `review_status`: `reject`, `keep`, `demo_candidate`, or `pack_draft`.
- `corrected_trigger_type`: required because first-pass ARS mislabels scenes.
- `evidence_grade`: `low`, `medium`, or `high`.
- `evidence_notes`: must state whether visual refs support the claim or only timestamp it.
- `pack_field_notes`: which fields this candidate pressures.
- `rejection_reason`: required when status is `reject`.
- `original_plot_note_reviewed`: why the original drama remains reasonable.

## 5. Minimum Runtime Use

For the next implementation step, the front end only needs:

- source timestamp and marker;
- companion hook;
- 2-3 default options;
- custom action policy;
- local consequence request payload;
- original plot note;
- evidence/review badge.

The backend judgment API should receive the full pack, but it must answer in
the local time horizon and echo which parts are evidence versus inference.
