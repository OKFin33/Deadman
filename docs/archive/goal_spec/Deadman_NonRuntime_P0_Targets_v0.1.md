# Deadman Non-Runtime P0 Targets v0.1 Goal Spec

> Status: ready for `/goal` execution  
> Repo: `/Users/okfin3/project/GitHub/OKFin33/OSeria-Alter`  
> Product: Branch 3 / Deadman / `要是我来`  
> Date: 2026-05-25

## Goal Prompt

Paste this into the target execution thread:

```text
/goal
Execute the contract in /Users/okfin3/project/GitHub/OKFin33/OSeria-Alter/docs/goal_spec/Deadman_NonRuntime_P0_Targets_v0.1.md.

Advance Deadman only on non-runtime P0 surfaces while CABRuntime SDK is in progress. Do not implement a Deadman-owned judgment runtime, do not add deterministic fallback for formal judgment, do not connect image generation, and do not promote unreviewed Yunmiao/Lihun nodes into runtime. Create or update the five target artifacts: CABRuntime SDK integration contract, P0 mobile UX acceptance checklist, producer bridge minimum flow, competition technical document skeleton, and migration human-review node table template. Append a [Deadman] dev-log entry and verify that the docs do not instruct future agents to build a duplicate runtime.
```

## Why This Goal Exists

Deadman has reached the backend adapter boundary:

```text
promoted Huangnian packs
  -> v0.3 typed Moment Causality Pack view
  -> deadman_judgment_adapter_input.v0.1
```

CABRuntime is now responsible for the reusable runtime SDK direction. Deadman
should therefore work on surfaces that will not be invalidated when that SDK
lands.

Product consequence: we keep visible demo progress and producer repeatability
without paying for a duplicate runtime that will be thrown away.

## Required Outputs

Create or maintain these tracked documents:

```text
docs/CABRuntime_SDK_Integration_Contract_v0.1.md
docs/P0_Mobile_UX_Acceptance_Checklist_v0.1.md
docs/Producer_Bridge_Minimum_Flow_v0.1.md
docs/Competition_Technical_Doc_Skeleton_v0.1.md
docs/Migration_Human_Review_Node_Table_Template_v0.1.md
```

Also update:

```text
docs/Axis_For_Main_Agent.md
docs/Development_Axis_v0.1.md
docs/Axis_View.html
.agent/dev-log.md
```

Only update axis files if they still point future work toward a duplicate
Deadman runtime or omit the new non-runtime targets.

## Scope

In scope:

- SDK integration contract between Deadman and CABRuntime.
- P0 mobile UX acceptance criteria for the viewer surface.
- Producer-side bridge flow from videos and ARS evidence to published packs.
- Feishu-ready competition technical document skeleton.
- Human review template for Yunmiao and Lihun migration evidence.

Out of scope:

- implementing the CABRuntime SDK;
- implementing a Deadman-owned judgment runtime;
- connecting LLM providers;
- connecting image generation providers;
- changing backend public API behavior;
- changing frontend UI code;
- promoting Yunmiao or Lihun to runtime;
- copying MP4/MOV files into tracked paths;
- adding `.env` files or secrets.

## Non-Negotiable Runtime Rule

Formal judgment must fail closed:

```text
runtime/provider/schema failure -> structured error -> frontend error state
```

It must not silently return deterministic/template output as a formal fallback.

The existing deterministic path may remain a local demo/test boundary until
CABRuntime integration is implemented, but docs must not describe it as the
formal fallback.

## Acceptance

This goal is complete when:

- all five target docs exist and are internally consistent;
- the SDK contract references existing adapter input/output schema paths;
- the UX checklist can be used to accept or reject a frontend PR;
- the producer bridge flow names tracked outputs and ignored/local inputs;
- the competition skeleton covers required submission sections;
- the migration template separates evidence samples from runtime promotion;
- axis docs point to non-runtime next work while CABRuntime SDK is pending;
- `.agent/dev-log.md` has one new `[Deadman]` entry.

## Verification

Run:

```bash
rg -n "deterministic fallback|fail back|build.*hybrid adapter|duplicate runtime" Deadman/docs docs/goal_spec .agent/dev-log.md
rg -n "CABRuntime_SDK_Integration_Contract|P0_Mobile_UX_Acceptance|Producer_Bridge_Minimum_Flow|Competition_Technical_Doc_Skeleton|Migration_Human_Review_Node_Table" Deadman/docs docs/goal_spec
```

Expected:

- no positive instruction to build a duplicate Deadman runtime;
- "deterministic fallback" appears only as a prohibited formal behavior or
  historical/current-demo caveat;
- all five new artifact names are discoverable.
