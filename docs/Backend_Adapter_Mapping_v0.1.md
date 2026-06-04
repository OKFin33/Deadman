# Backend Adapter Mapping v0.1

> Product: Deadman / 要是我来  
> Scope: backend mapper only  
> Provider integration: not connected

## Why This Exists

The promoted Huangnian runtime packs are still `moment_causality_pack.v0.1`.
They are good enough for the current deterministic demo/test path, but not
strict enough for a formal CABRuntime-backed judgment integration.

Product consequence: if an adapter reads v0.1 prose directly, it can re-infer
stake type, proof state, hidden-system limits, watch-flow boundaries, and visual
proof policy. That would throw away the red-team patch that created typed v0.3
subkeys.

The backend now has a fail-closed bridge:

```text
promoted v0.1 runtime moment
  -> moment_causality_pack.v0.3.draft typed view
  -> deadman_judgment_adapter_input.v0.1
```

The current public judgment engine remains deterministic as a demo/test
boundary. No LLM, ASR, image generation, or external provider is connected by
this layer. Formal judgment must not use deterministic fallback; it should
return structured error when runtime/provider execution fails.

## Runtime Boundary

Implementation:

```text
backend/adapter_mapping.py
```

Public API:

```python
build_typed_moment_pack(drama_pack, moment) -> dict
build_adapter_input(request_id, drama_pack, moment, request) -> dict
```

`DeterministicJudgmentService.judge()` invokes the mapper before returning the
existing response. The mapped result is used as validation only; it does not
rewrite current Chinese result text or the frontend response shape.

If mapping fails, the backend returns a structured error instead of silently
falling back to loose v0.1 prose.

## Mapping Table

| v0.1 source | v0.3 / adapter target | Policy |
| --- | --- | --- |
| `moment_id` / `pack_id` | `moment_pack.pack_id` | Required. Missing id fails closed. |
| `source_drama.episode_id`, `source_window.start_ms/end_ms` | `source_window` | Missing start/end fails closed. |
| `review_state`, `provenance`, `source_refs`, transcript/keyframe refs | `review_and_provenance` | Publish-safe refs only; raw `tmp/` paths are dropped. |
| `companion_surface`, `interaction_window` | `companion_entry` | Surface copy, not causal evidence. |
| `action_space.action_type/default_options/custom_action_policy` | `action_space` | Default option labels are preserved; stable ids `preset_0..n` are added. |
| `outcome_response_contract.time_horizon`, `judgment_policy.must_not_claim` | `response_contract`, `watch_flow_rationale` | Only current-scene/immediate aftermath is accepted. |
| `result_media`, old visual policy | `visual_result_policy` | Preset slots remain illustrative; generated proof is blocked. |
| `actor_context` | `actor_local_state` | Missing `pov_actor` defaults to `主角` with a mapping warning. |
| `optional_modules`, `actor_context`, local constraints | `critical_stakes_state`, `escalation_risk` | Uses typed subkeys; unknown enum values are preferred over invented precision. |
| `local_constraints`, context guardrails | `local_constraint_state` | Context evidence map is not copied wholesale into prompt-facing fields. |
| `canon_baseline`, `original_plot_note` | `canon_baseline`, `watch_flow_rationale` | Blocks future-branch and canon-wrong claims. |
| `score_axes` | `producer_only.score_axes`, `debug.score_axes` | Never viewer-facing evidence. |

## Optional Module Mapping

The mapper only creates optional v0.3 modules when v0.1 has supporting source
modules:

| v0.1 module | v0.3 module |
| --- | --- |
| `relationship_pressure` | `relationship_state` |
| `system_or_hidden_power_rule` | `capability_rules` |
| `exposure_and_secrecy` | `information_asymmetry`, `capability_rules` |
| `evidence_or_trap_logic` | `proof_state`, `information_asymmetry` |
| `village_or_public_reputation` | `audience_reputation_state` |
| `humiliation_reversal` | `audience_reputation_state` |
| `resource_scarcity` | core `critical_stakes_state` |

It does not create empty modules to make the schema look complete.

## Fail-Closed Policy

The mapper raises `AdapterMappingError` when:

- required identity or source-window fields are missing;
- preset moments have no action options;
- the time horizon is not local;
- visual policy cannot block proof usage;
- there is no grounded source material for critical stakes;
- watch-flow rationale cannot block future branch claims;
- `score_axes` leaks outside producer/debug fields.

Product consequence: broken promoted pack data stops at the backend boundary,
instead of letting a future model invent missing causal facts.

## Visual And Provider Boundary

Every mapped pack sets:

```json
{
  "truth_level": "illustrative_result",
  "proof_eligibility": "never",
  "must_not_be_used_as_proof": true,
  "provider_policy": "not_connected",
  "visual_prompt_plan": {
    "provider_policy": "not_connected"
  }
}
```

Preset slots are placeholders. Custom actions produce a plan-only adapter
request. Generated images remain blocked as proof.

## Verified Status

The current Huangnian promoted runtime set maps successfully:

```text
huangnian_ep12_m001
huangnian_ep07_m001
huangnian_ep03_m001
huangnian_ep04_m001
huangnian_ep06_m001
```

Status: 5/5 mapped to `deadman_judgment_adapter_input.v0.1`.

Parent validation also checks the mapped `moment_pack` objects against
`moment_causality_pack.v0.3.draft.json`, not only the mapper's lightweight local
validator. This caught and fixed two shape mismatches during review:

- `source_window.source_refs` must be an array of ref objects;
- `producer_only.field_demand_trace` and `proof_state.evidence_refs` must be
  arrays of objects, not loose strings or nested source-ref dictionaries.

## What This Enables Next

This layer makes the future adapter boundary explicit. The next step can be one
of:

1. Define and later wire the CABRuntime SDK integration contract that consumes
   this mapped input.
2. Add a producer migration script that promotes reviewed v0.3 packs directly.
3. Run the separate image/provider spike for latency, quality, likeness safety,
   fallback, and visual-proof contamination.

Do not collapse those steps into this mapper.
