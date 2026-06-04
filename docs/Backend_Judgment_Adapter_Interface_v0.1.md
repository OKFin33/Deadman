# Backend Judgment Adapter Interface v0.1

> Product: Deadman / 要是我来  
> Scope: interface contract only  
> Runtime behavior change: none

## Boundary

This interface prepares the future backend judgment adapter. It does not replace
the current deterministic service and does not call an LLM provider.

The adapter's product job is narrow:

1. Accept a reviewed Moment Causality Pack.
2. Accept a preset or custom viewer action.
3. Judge one local consequence within the current scene or immediate aftermath.
4. Return a friend-tone result plus watch-flow rationale.
5. Never promise that future episodes follow the branch.

## Input Schema

Tracked schema:

```text
data/schemas/deadman_judgment_adapter_input.v0.1.json
```

Required top-level fields:

- `request_id`
- `drama_id`
- `moment_pack`
- `user_action`
- `runtime_policy`
- `requested_output`

`moment_pack` references `moment_causality_pack.v0.3.draft.json`.

`runtime_policy` enforces:

- `time_horizon=current_scene_or_immediate_aftermath`
- `allow_future_branch_claims=false`
- `allow_visual_as_proof=false`
- `output_language=zh-CN`

`producer_only` fields may exist inside the pack for debug/review, but should
not be included in the viewer-facing judgment prompt by default.

## Output Schema

Tracked schema:

```text
data/schemas/deadman_judgment_adapter_output.v0.1.json
```

Required top-level fields:

- `request_id`
- `verdict`
- `result_text`
- `companion_reaction`
- `why_this_happens`
- `time_horizon`
- `watch_flow_rationale`
- `used_fields`
- `blocked_claims`
- `visual_result_plan`
- `engine_metadata`

Allowed verdicts:

- `credible_win`
- `credible_costly_win`
- `mixed`
- `backfires`
- `invalid_or_overpowered`

## Required Output Discipline

The adapter output must always include:

- a local time horizon;
- a watch-flow rationale;
- blocked claims, especially future-branch claims and visual-proof claims;
- a provider-neutral `visual_result_plan`.

## Non-Goals

This interface does not:

- implement LLM routing;
- change backend behavior;
- change frontend UI;
- call image generation;
- promote 云渺 or 离婚 packs;
- expose `score_axes` as viewer evidence.

## Implementation Note For The Next Goal

The next backend adapter goal should build a mapper from the existing promoted
runtime moment format to this adapter input. That mapper should fail closed when
required typed subkeys are missing, instead of letting the model infer them from
loose prose.
