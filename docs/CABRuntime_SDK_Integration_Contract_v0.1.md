# CABRuntime SDK Integration Contract v0.1

> Product: Deadman / `要是我来`  
> Status: v0.1 contract plus current env-activated integration boundary  
> Date: 2026-05-25

## Purpose

This contract defines how Deadman hands a moment-level judgment task to
CABRuntime without building a duplicate runtime inside Deadman.

Deadman owns:

- short-drama material registration and bridge artifacts;
- Drama Context Pack and Moment Causality Pack production;
- mapping promoted packs into typed adapter input;
- mobile viewer UX and result rendering;
- structured user-facing error display.

CABRuntime SDK owns:

- model/provider execution;
- runtime trace and schema enforcement mechanics;
- provider timeout/error handling;
- any reusable harness behavior shared with other projects.

Product consequence: Deadman stays a short-drama product instead of becoming a
second runtime platform.

## Current Deadman Boundary

Existing tracked contracts:

```text
backend/adapter_mapping.py
data/schemas/deadman_judgment_adapter_input.v0.1.json
data/schemas/deadman_judgment_adapter_output.v0.1.json
data/schemas/moment_causality_pack.v0.3.draft.json
data/schemas/visual_result_plan.v0.1.json
```

Current local endpoint:

```text
POST /api/deadman/judgment
```

Current deterministic behavior is allowed only as a demo/test boundary. It is
not the formal judgment fallback. The formal path is enabled with
`DEADMAN_JUDGMENT_ENGINE=cab_runtime` and must pass the CAB readiness gate before
being claimed.

## Integration Shape

Deadman keeps CABRuntime behind a narrow adapter, not scattered SDK calls across
the backend.

Current file boundary:

```text
backend/adapter_mapping.py
  -> build_adapter_input(...)

backend/runtime_client.py
  -> call CABRuntime host adapter
  -> return adapter output or structured runtime error

backend/judgment.py
  -> keep public API shape stable
  -> translate runtime output/error into viewer response/error state
```

Product consequence: replacing or upgrading CABRuntime later should not require
rewriting the player, pack store, or producer bridge.

## Formal Failure Rule

Formal judgment is fail-closed:

```text
runtime unavailable
provider timeout
schema validation failure
guardrail violation
pack mapping failure
  -> structured error
  -> frontend renders error state
```

No formal path may silently return deterministic/template judgment as fallback.

## SDK Request Envelope

Deadman should call CABRuntime with an envelope shaped like:

```json
{
  "sdk_contract_version": "cab_deadman_judgment.v0.1",
  "task_type": "deadman_moment_judgment",
  "request_id": "uuid-or-request-id",
  "adapter_input": {
    "$schema_ref": "data/schemas/deadman_judgment_adapter_input.v0.1.json"
  },
  "execution_policy": {
    "time_budget_ms": 8000,
    "output_language": "zh-CN",
    "time_horizon": "current_scene_or_immediate_aftermath",
    "allow_future_branch_claims": false,
    "allow_visual_as_proof": false,
    "allow_external_web_fetch": false,
    "fail_closed": true,
    "deterministic_fallback": false
  },
  "trace_policy": {
    "include_runtime_trace": true,
    "include_prompt_fingerprint": true,
    "include_provider_metadata": true,
    "expose_trace_to_viewer": false
  }
}
```

The actual SDK type names can change. The semantic fields above should not.

Deadman must send the actual `adapter_input` object, not a schema-reference
placeholder. The schema reference in this document is only illustrative.

## Adapter Input

The `adapter_input` object is produced by:

```text
backend/adapter_mapping.py
```

It must validate against:

```text
data/schemas/deadman_judgment_adapter_input.v0.1.json
```

Required semantic constraints:

- `moment_pack` is a v0.3 typed pack, not loose v0.1 prose.
- `runtime_policy.time_horizon` is `current_scene_or_immediate_aftermath`.
- `runtime_policy.allow_future_branch_claims` is `false`.
- `runtime_policy.allow_visual_as_proof` is `false`.
- producer-only fields, including `score_axes`, are not viewer evidence.

## SDK Success Output

On success, CABRuntime SDK returns an object that validates against:

```text
data/schemas/deadman_judgment_adapter_output.v0.1.json
```

Minimum viewer-usable fields:

- `verdict`
- `result_text`
- `companion_reaction`
- `why_this_happens`
- `watch_flow_rationale`
- `blocked_claims`
- `visual_result_plan`

Deadman backend may adapt this into the existing public response shape, but it
must not expose raw runtime trace or producer-only scores to the viewer.

`engine_metadata.mode` in the current output schema can remain `llm` or
`hybrid` for the first SDK wiring. Do not introduce a schema migration only to
rename the mode to `cab_runtime_sdk`; record the SDK identity in provider or
additional metadata until a broader schema update is justified.

## SDK Error Output

On failure, CABRuntime SDK should return a structured error:

```json
{
  "request_id": "same-request-id",
  "status": "error",
  "error": {
    "code": "provider_timeout",
    "message": "provider did not return within the time budget",
    "retryable": true,
    "user_facing_message": "这次判定卡住了，先继续看，晚点再试一次。",
    "stage": "provider_execution"
  },
  "trace": {
    "runtime_trace_id": "opaque-id",
    "schema_version": "cab_deadman_judgment.v0.1"
  }
}
```

Recommended error codes:

| Code | Retryable | Product meaning |
| --- | --- | --- |
| `pack_mapping_failed` | false | source pack is broken; producer must fix artifact |
| `adapter_input_invalid` | false | Deadman sent invalid typed input |
| `runtime_unavailable` | true | SDK/service is unavailable |
| `provider_timeout` | true | model did not return fast enough for synchronous UX |
| `provider_error` | true | provider failed without usable output |
| `output_schema_invalid` | true | model returned malformed judgment |
| `guardrail_violation` | false | output claimed forbidden branch/future/proof |
| `visual_policy_violation` | false | output treated image as proof |

Frontend copy must not pretend that a judgment happened when the formal path
failed.

Deadman public API should represent this as an error response or a clearly
typed result state, not as a successful judgment payload with generic fallback
text.

## Prompt and Guardrail Boundary

Deadman can provide prompt principles, but CABRuntime should own prompt assembly
mechanics.

Prompt constraints:

- judge only the current scene or immediate aftermath;
- keep the result scoped to the current viewing moment;
- explain why the user action works or backfires from local fields;
- do not claim the whole future branch continues;
- do not say the generated image proves what happened;
- do not expose producer-only scores as evidence;
- keep companion voice friend-like, not analyst-like.

## Integration Acceptance

Integration is acceptable when:

- Deadman can build valid adapter input for all promoted Huangnian moments;
- CABRuntime SDK call returns either valid adapter output or structured error;
- formal runtime failure is visible as error, not deterministic fallback;
- frontend has a product-safe error state;
- trace is stored server-side or debug-only;
- no provider key reaches frontend;
- no MP4/MOV, `.env`, raw provider output, or secrets are committed.

Minimum test matrix:

| Case | Expected behavior |
| --- | --- |
| valid Huangnian preset action | valid adapter output becomes viewer result |
| valid Huangnian custom action | valid adapter output or structured SDK error |
| missing/malformed pack field | `pack_mapping_failed` or `adapter_input_invalid` |
| SDK unavailable | `runtime_unavailable`, retryable |
| provider timeout | `provider_timeout`, retryable |
| malformed model output | `output_schema_invalid`, retryable |
| future-branch claim | `guardrail_violation`, not retryable without prompt/logic fix |
| visual-as-proof claim | `visual_policy_violation`, not retryable without prompt/logic fix |

Acceptance must include mobile UX verification that error states are visible and
do not trap the user inside the bubble.

## Phased Adoption

Phase 0, current default:

- keep deterministic demo/test boundary;
- maintain typed adapter mapping;
- harden frontend and producer surfaces.

Phase 1, implemented env-activated path:

- use `runtime_client.py` as the thin adapter;
- wire one non-streaming judgment call behind `DEADMAN_JUDGMENT_ENGINE=cab_runtime`;
- validate success and structured-error paths with `--require-cab-runtime`;
- keep public frontend response shape stable except for explicit error state.

Phase 2, formal P0 recording path:

- use CABRuntime for formal judgment when the CAB readiness gate passes;
- remove any language that presents deterministic output as formal fallback;
- preserve deterministic tests as unit tests, not user-facing proof.

## Open Items For CABRuntime

These remain open for hardening:

- provider profile naming;
- trace storage location;
- streaming versus non-streaming text result;
- retry policy;
- packaging strategy for clean public deployments without a sibling CABRuntime
  checkout.
