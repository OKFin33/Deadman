# Moment Causality Pack v0.3 Draft

> Draft contract generated from Moment Field Minimum Set v0.3 and patched by
> Field Minimum Red Team v0.1. This is an adapter-ready schema draft, not a
> runtime pack promotion.

## Product Boundary

Deadman judges one local `要是我来` consequence and preserves watch flow. It
does not simulate a continuing alternate timeline.

The v0.3 field set stays minimal, but the compressed causal fields now require
typed subkeys so backend judgment does not guess distinctions that were
intentionally fused during field clustering.

## Minimal JSON Shape

```json
{
  "pack_id": "drama_ep01_m001",
  "schema_version": "moment_causality_pack.v0.3.draft",
  "source_window": {},
  "review_and_provenance": {},
  "companion_entry": {},
  "action_space": {},
  "response_contract": {
    "time_horizon": "current_scene_or_immediate_aftermath",
    "allow_future_branch_claims": false,
    "allow_canon_wrong_claims": false
  },
  "visual_result_policy": {
    "result_media_mode": "preset_slot",
    "truth_level": "illustrative_result",
    "proof_eligibility": "never",
    "must_not_be_used_as_proof": true,
    "fallback": "text_only",
    "latency_budget_ms": 0,
    "provider_policy": "not_connected",
    "visual_prompt_plan": {
      "prompt_source": "preset",
      "prompt_text": "",
      "negative_constraints": [],
      "style_policy": "short_drama_result_card",
      "provider_policy": "not_connected"
    }
  },
  "actor_local_state": {},
  "critical_stakes_state": {},
  "local_constraint_state": {},
  "escalation_risk": {},
  "canon_baseline": {},
  "watch_flow_rationale": {},
  "optional_modules": {
    "relationship_state": {},
    "capability_rules": {},
    "information_asymmetry": {},
    "proof_state": {},
    "audience_reputation_state": {}
  },
  "producer_only": {
    "score_axes": {},
    "field_demand_trace": []
  }
}
```

## Required Fields

- Core operational: `source_window`, `review_and_provenance`,
  `companion_entry`, `action_space`, `response_contract`,
  `visual_result_policy`.
- Core causal: `actor_local_state`, `critical_stakes_state`,
  `local_constraint_state`, `escalation_risk`, `canon_baseline`,
  `watch_flow_rationale`.
- Producer-only: `score_axes` may travel with packs for review/ranking, but
  frontend and viewer-facing judgment prompts should ignore it.

## Typed Core Causal Fields

### critical_stakes_state

Distinguishes what kind of stake is being changed by the user's action.

Required subkeys:

- `stake_type`: `resource`, `bodily_safety`, `pregnancy`, `reputation`,
  `relationship`, `legal`, `status`, `power`, or `other`.
- `stake_owner`: actor or group that owns the stake.
- `time_pressure`: `immediate`, `short_term`, `deferred`, `none`, or
  `unknown`.
- `scarcity_or_risk_level`: `low`, `medium`, `high`, or `unknown`.
- `irreversibility`: `reversible`, `costly`, `irreversible`, or `unknown`.
- `risk_if_action`: local risk introduced by acting.
- `risk_if_no_action`: local risk introduced by doing nothing.

Product consequence: this keeps food scarcity, pregnancy danger, bodily safety,
status loss, and relationship collapse under one field without letting the
adapter confuse them.

### escalation_risk

Captures backlash, retaliation, public blowback, legal cost, or watch-flow break
risk.

Required subkeys:

- `risk_type`: `social`, `physical`, `legal`, `resource`, `relationship`,
  `capability_exposure`, `watch_flow`, or `other`.
- `risk_source`: who or what creates the risk.
- `immediacy`: `immediate`, `short_term`, `deferred`, or `unknown`.
- `severity`: `low`, `medium`, `high`, `critical`, or `unknown`.
- `mitigation`: how the result can stay credible.
- `who_can_escalate`: actors or groups able to escalate the cost.

### watch_flow_rationale

Stays separate from `canon_baseline`.

Required subkeys:

- `why_original_still_works`: why the original drama choice remains acceptable.
- `viewer_return_line`: one short line that lets the viewer return to canon.
- `must_not_claim`: blocked claims, including future-branch continuation,
  canon-was-wrong framing, and automatic branch continuation.

## Typed Optional Modules

Optional modules attach only when field demand score is `2` or `3` for the
moment. They are not new core fields.

### relationship_state

Required if present:

- `relationship_type`: `family`, `romantic`, `marriage`, `village`, `enemy`,
  `ally`, `institutional`, or `unknown`.
- `trust_level`: `low`, `medium`, `high`, `broken`, or `unknown`.
- `dependency`: `none`, `emotional`, `resource`, `safety`, `status`, `legal`,
  or `unknown`.
- `protection_priority`: what the actor should protect in the relationship.

### capability_rules

Required if present:

- `capability_type`: `system`, `hidden_power`, `status_power`, `knowledge`,
  `physical`, `social`, `none`, or `other`.
- `hard_limit`: non-negotiable ability limit.
- `activation_cost`: cost of using the capability.
- `visibility_cost`: cost if witnesses observe it.
- `known_to_actor`: whether the POV actor knows the capability.
- `known_to_others`: whether other local actors know it.
- `failure_mode_if_overused`: how overuse backfires.

### information_asymmetry

Required if present:

- `hidden_fact`: the hidden fact or identity.
- `who_knows`: actors currently aware.
- `who_does_not_know`: actors currently unaware.
- `who_would_learn`: actors who learn if the action reveals it.
- `reveal_timing`: `now`, `later`, `avoid`, or `unknown`.
- `leverage_change`: `gain`, `loss`, `mixed`, `none`, or `unknown`.
- `cost_of_reveal`: local cost of revealing.

### proof_state

Required if present:

- `proof_type`: `witness`, `record`, `object`, `medical`, `legal`,
  `business`, `visual_reference`, `none`, or `other`.
- `available_now`: whether proof exists locally now.
- `threshold`: `low`, `medium`, `high`, or `unknown`.
- `holder`: who controls the proof.
- `risk_if_claimed_without_proof`: consequence of unsupported accusation.
- `evidence_refs`: publish-safe references. Generated result images are not
  proof.

### audience_reputation_state

Required if present:

- `audience_scope`: `private`, `family`, `village`, `public`,
  `institutional`, `online`, or `unknown`.
- `audience_alignment`: `supportive`, `hostile`, `mixed`, `neutral`, or
  `unknown`.
- `status_at_stake`: what public status is at stake.
- `humiliation_vector`: how humiliation or face-loss happens.
- `likely_reaction`: expected local audience reaction.

## Visual Result Policy

`visual_result_policy` is required even when the result is text-only. It blocks
visual proof contamination before image generation is connected.

Required semantics:

- `truth_level=illustrative_result`: generated/result media is not evidence.
- `truth_level=source_reference`: media points to a source/keyframe but cannot
  prove new generated consequences.
- `truth_level=reviewed_visual_evidence`: producer-side only and still cannot
  make generated branches canon.
- `proof_eligibility` defaults to `never` for generated media.
- `must_not_be_used_as_proof` must be `true`.
- `fallback` must allow `text_only`.
- top-level `provider_policy` remains `not_connected` until a separate provider
  spike; `visual_prompt_plan.provider_policy` can later narrow prompt-specific
  provider handling.

## Backend Judgment Consumption

The future adapter should:

1. Read core causal fields first.
2. Attach only relevant optional modules.
3. Hide `producer_only.score_axes` from the viewer-facing prompt by default.
4. Enforce `response_contract.time_horizon`.
5. Include `watch_flow_rationale.viewer_return_line` in the output.
6. Block claims that future episodes follow the branch, canon was wrong, or
   generated images prove branch facts.

## Producer ARS Extraction

ARS should extract the core fields for every candidate and record module demand
scores. Candidate-only evidence can reveal missing demand types, but cannot
promote a module to core without reviewed/schema evidence.

## Frontend Consumption

The player needs `source_window`, `companion_entry`, `action_space`,
`response_contract`, and `visual_result_policy`. It should ignore
`producer_only` and should not display raw evidence/provenance unless a producer
review UI is active.
