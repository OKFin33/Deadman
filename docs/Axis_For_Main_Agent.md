# Deadman Axis For Main Agent

> Read first when a Deadman thread resumes or hands work to a subagent.  
> Updated: 2026-05-25

## Current Station

Deadman is at:

```text
backend adapter boundary complete -> waiting for CABRuntime SDK contract
```

What this means:

- We have a mobile-shaped viewer shell.
- We have `荒年` promoted runtime moments.
- We have v0.3 minimum fields and typed subkeys.
- We have backend mapping from promoted v0.1 moments to v0.3 typed adapter
  input.
- We are not building a Deadman-owned judgment runtime while CABRuntime SDK is
  in progress.
- Formal judgment must fail with structured errors when provider/runtime
  execution fails. There is no deterministic fallback for the formal path.

## Current Micro Slice

Previous:

```text
typed schema + visual provider-policy contract
```

Current:

```text
backend adapter mapping is complete and parent-validated
```

Next:

```text
write the CABRuntime SDK integration contract and harden P0 surfaces
```

## Active Recommendation

Do not implement the judgment runtime inside Deadman right now. Keep work on
surfaces that will not be thrown away when CABRuntime SDK lands:

- CABRuntime SDK integration contract: adapter input, output, structured
  errors, trace, guardrail boundaries, and no viewer-facing debug leakage.
- P0 mobile product hardening: catalog, vertical player, companion states,
  bubble/result/error states, and recording-safe viewport behavior.
- Producer bridge hardening: register videos, run ARS, review nodes, publish
  packs, and make runtime consumption reproducible.
- Migration evidence: human-review Yunmiao/Lihun nodes before any runtime
  promotion.
- Submission packaging: keep the Feishu technical document and demo script
  aligned with the actual build.

Do this before image generation or voice.

## Do Not Do

- Do not wire image generation first.
- Do not turn Deadman into a continuous branch simulator.
- Do not promote `云渺` or `幸得相遇离婚时` to runtime before human review.
- Do not expose `score_axes` as viewer-facing evidence.
- Do not put new Deadman product code into `Runtime/` except compatibility
  bridge work.
- Do not commit MP4/MOV, raw provider output, `.env`, or keys.

## Last Reliable Validation

Backend adapter mapping:

- 5/5 `荒年` promoted moments map successfully.
- mapped packs pass formal `moment_causality_pack.v0.3.draft.json`.
- `score_axes` stays producer/debug only.
- public judgment response shape is unchanged.
- no LLM, ASR, image-generation, or external provider is connected.

Tests last known green:

```text
python3 -m py_compile backend/*.py backend/tests/*.py
python3 -m unittest Deadman.backend.tests.test_adapter_mapping -v
python3 -m unittest Deadman.backend.tests.test_judgment_api -v
cd frontend && npm test
cd Runtime/frontend && npm test
```

## Files To Inspect First

```text
docs/Axis_For_Main_Agent.md
docs/Axis_View.html
docs/Development_Axis_v0.1.md
.agent/dev-log.md
docs/WORKSPACE_MAP.md
backend/adapter_mapping.py
data/schemas/deadman_judgment_adapter_input.v0.1.json
data/schemas/deadman_judgment_adapter_output.v0.1.json
docs/CABRuntime_SDK_Integration_Contract_v0.1.md
docs/P0_Mobile_UX_Acceptance_Checklist_v0.1.md
docs/Producer_Bridge_Minimum_Flow_v0.1.md
docs/Competition_Technical_Doc_Skeleton_v0.1.md
docs/Migration_Human_Review_Node_Table_Template_v0.1.md
docs/archive/goal_spec/Deadman_NonRuntime_P0_Targets_v0.1.md
```

## Prompt Seed For Next Subagent

```text
Update or implement a non-runtime Deadman P0 slice. CABRuntime SDK is in
progress elsewhere, so do not build a Deadman-owned judgment runtime and do not
add deterministic fallback for formal judgment. Valid targets are: CABRuntime
SDK integration contract, P0 mobile product hardening, producer bridge
hardening, submission documentation, or reviewed migration evidence for
Yunmiao/Lihun. Do not connect image generation, do not promote unreviewed
dramas to runtime, do not claim future episode branching, and do not expose
score_axes as viewer evidence.
```

## When To Update This File

Update this file when the current station changes.

Do not update it for routine bug fixes or every test run. The long background
map is `docs/Development_Axis_v0.1.md`.
