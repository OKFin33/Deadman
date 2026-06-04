# Moment Causality Pack v0.2

> Product: Deadman / 要是我来  
> Generated: 2026-05-24  
> Contract: local credible consequence, not continuous alternate timeline.

## 0. Runtime Boundary

A `MomentCausalityPack` answers one local viewer question:

```text
要是我在这一刻这么做，当前局面里可信后果是什么？
```

It must not promise that later episodes follow this branch. It can briefly explain why the original plot remains watchable.

## 1. CoreEnvelope

Required for every promoted Deadman moment:

- `source_window`: Every moment needs episode/time/provenance before backend judgment or frontend marker rendering. Consumer: `producer+backend+frontend`.
- `review_state`: ARS outputs are bridge evidence; every promoted node needs review status and evidence/inference separation. Consumer: `producer+backend`.
- `companion_surface`: The frontstage companion needs marker, hook, and friend-tone entry copy. Consumer: `frontend`.
- `viewer_impulse`: All genres use the same product emotion: validating '要是我来' instinct before judging cost. Consumer: `backend+LLM`.
- `actor_context`: Without local actors and roles, outputs become generic analysis rather than scene consequence. Consumer: `backend+LLM`.
- `local_constraints`: The core product promise is credible consequence, which requires hard local constraints. Consumer: `backend+LLM`.
- `canon_baseline`: Needed to preserve watch flow and explain why original writing remains acceptable. Consumer: `backend+LLM+frontend`.
- `action_space`: Preset and custom action routing both need typed, bounded action space. Consumer: `backend+frontend`.
- `judgment_policy`: Prevents continuous timeline promises, unsupported facts, and unbounded power escalation. Consumer: `backend+LLM`.
- `outcome_response_contract`: Keeps output to short local consequence plus optional original-plot note. Consumer: `backend+LLM+frontend`.
- `score_axes`: Ranking, review, and fallback judgment need stable axes; keep `watch_flow_fit`, not `return_to_plot_fit`. Consumer: `producer+backend`.
- `visual_result_policy`: The product wants图文结合, but keyframes are refs, not visual truth. Consumer: `producer+backend+frontend`.

Minimal JSON shape:

```json
{
  "pack_id": "drama_ep01_m001",
  "schema_version": "moment_causality_pack.v0.2",
  "source_drama": {
    "drama_id": "string",
    "title": "string",
    "episode_id": "string",
    "source_policy": "local media + ASR/keyframe evidence; reviewed before demo"
  },
  "source_window": {
    "start_ms": 0,
    "end_ms": 20000,
    "interaction_window": {
      "notice_at_seconds": 0,
      "start_seconds": 0,
      "end_seconds": 20
    },
    "transcript_refs": [],
    "keyframe_refs": [],
    "contact_sheet_ref": ""
  },
  "review_state": {
    "status": "schema_evidence|keep|demo_candidate|reject",
    "evidence_grade": "low|medium|high",
    "evidence_vs_inference": "string",
    "human_review_required": true
  },
  "companion_surface": {
    "notice_marker": "!|?",
    "hook": "string",
    "friend_tone": "string"
  },
  "viewer_impulse": "string",
  "actor_context": {
    "pov_actor": "string",
    "directly_affected_actors": [],
    "relationship_context": "string"
  },
  "local_constraints": {
    "known_facts": [],
    "hidden_facts": [],
    "hard_constraints": [],
    "risk_notes": []
  },
  "canon_baseline": {
    "original_action": "string",
    "original_rationale": "string",
    "original_plot_note": "string"
  },
  "action_space": {
    "action_type": "string",
    "default_options": [],
    "custom_action_policy": {
      "allowed": true,
      "scope": "local credible consequence only"
    }
  },
  "optional_modules": {},
  "judgment_policy": {
    "must_consider": [],
    "must_not_claim": [
      "later episodes follow this branch",
      "unsupported facts",
      "unbounded power"
    ]
  },
  "outcome_response_contract": {
    "format": "short local consequence + optional original plot note",
    "time_horizon": "current scene or immediate aftermath"
  },
  "visual_result_policy": {
    "preset_image_slot": "optional",
    "custom_image_policy": "realtime_or_text_only_fallback",
    "visual_truth_level": "keyframe_ref|reviewed|generated"
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
    "open_questions": []
  }
}
```

## 2. OptionalCausalityModules

Attach only when the reviewed candidate pressures the mechanism:

- `resource_scarcity`: Strong in 荒年, not universal across cultivation/divorce genres.
- `exposure_and_secrecy`: Appears in system, hidden-power, and status scenes, but not every moment.
- `relationship_pressure`: Common in family/divorce scenes; still absent from pure evidence or power-rule moments.
- `village_or_public_reputation`: Covers public witnesses in famine/village and social humiliation scenes.
- `evidence_or_trap_logic`: Needed whenever反打 depends on proof, accounts, witnesses, or legal/business evidence.
- `system_or_hidden_power_rule`: Shared by system and cultivation-like scenes; not needed for ordinary relationship beats.
- `humiliation_reversal`: Short-drama爽感 staple, but its cost differs by scene mechanism.
- `survival_tradeoff`: Core to famine/survival moments; too specific for universal core.

## 3. GenreExtensions

- `hidden_power_rule`: Needed for 云渺-style hidden power/cultivation constraints.
- `identity_reveal`: Needed where identity truth timing drives leverage.
- `betrayal_divorce_safety`: Needed for 幸得相遇离婚时-style rupture, safety, and evidence timing.
- `status_reversal_bottom_card`: Needed for CEO/offer/legal/business reversal timing.
- `medical_or_pregnancy_risk`: Needed when bodily risk changes the priority between rescue and revenge.

## 4. ProducerReviewFields

- `producer_review_fields`: Keeps ASR/keyframe/inference hygiene explicit.

## 5. NonP0Fields

- `branch_timeline`: Implies continuous alternate plot, which P0 explicitly does not promise.
- `global_inventory`: Only local resource state is needed; global mutation would recreate ArcForge-like continuity.
- `full_social_graph`: Local actors/witnesses are enough for moment-level consequence.
- `auto_visual_truth`: Keyframe refs do not prove object/person claims without human or visual-model review.

## 6. ARS Miner Output Requirements

Before a node can be promoted, ARS must emit:

- timestamped `source_window` with transcript refs and keyframe/contact-sheet refs;
- `trigger_type` plus candidate mechanism bucket;
- scene-specific companion `hook` and 2-3 bounded `default_options`; 
- `canon_baseline` and `original_plot_note` draft;
- field-pressure notes for every optional or genre module it expects;
- review/evidence flags separating ASR text, visual refs, and inference.
