# Deadman Development Axis v0.1

> Product: Deadman / 要是我来  
> Purpose: agent collaboration reorientation  
> Updated: 2026-05-25  

This document is the map to read when a thread loses position.

It has two lenses:

- Macro axis: where Deadman is on the whole development line.
- Micro axis: what the current slice is, what came before it, what comes after
  it, and what technical plan is active.

It is not a changelog. For chronological evidence, read `.agent/dev-log.md`.
It is not a task contract. For current producer execution details, read
`docs/goal_spec/`. For historical sprint execution evidence, read
`docs/archive/goal_spec/`.

## Current Position

Deadman is past initial substrate building and is now at the submission delivery
boundary.

Plain state:

```text
raw short-drama materials
  -> ARS / candidate nodes
  -> cross-drama minimum field set
  -> red-team-required typed schema
  -> backend adapter mapping from promoted packs
  -> resident runtime + CABRuntime formal gate
  -> CURRENT: Android APK delivery shell + productized submission path
```

Product consequence:

The system can now prove that reviewed `荒年` moments can be converted into a
typed judgment input and exercised through the resident runtime API. Formal
CABRuntime judgment can be claimed only when the CAB readiness gate passes in
the same environment. The immediate submission risk has moved from backend
contract existence to Android delivery, stable recording, and productized UI.

Non-runtime target documents now exist for the safe waiting period before
CABRuntime SDK integration:

```text
docs/CABRuntime_SDK_Integration_Contract_v0.1.md
docs/P0_Mobile_UX_Acceptance_Checklist_v0.1.md
docs/Producer_Bridge_Minimum_Flow_v0.1.md
docs/Competition_Technical_Doc_Skeleton_v0.1.md
docs/Migration_Human_Review_Node_Table_Template_v0.1.md
```

## Macro Axis

| Phase | Product question | Status | Main artifacts | Notes |
| --- | --- | --- | --- | --- |
| 0. Branch split | Is Deadman separate from ArcForge/Runtime? | Done | `Deadman/`, `docs/WORKSPACE_MAP.md` | `Runtime/` remains compatibility host only. |
| 1. Viewer shell | Can a mobile-shaped short-drama player show a companion and interaction node? | Done for P0 | `frontend/`, `Runtime/frontend` bridge | UI design still needs product pass. |
| 2. Source material dogfood | Can we mine interaction nodes from actual short-drama episodes? | Done for first pass | `tools/ars/`, ignored `tmp/` outputs | `荒年` is runtime-promoted; `云渺`/`离婚` are schema evidence only. |
| 3. Minimum field induction | What fields are needed across different genres? | Done v0.3 | `Moment_Field_Minimum_Set_v0.3.md`, schemas | Field count compressed; not all nodes are runtime truth. |
| 4. Red team | Does the minimum field set survive adversarial cases? | Done with required patches | `Field_Minimum_Red_Team_v0.1.md` | Required typed subkeys and visual proof boundaries. |
| 5. Typed interface prep | Are pack, judgment, and visual interfaces explicit enough? | Done | v0.3 draft pack schema, adapter input/output schema | No provider connected. |
| 6. Backend adapter mapping | Can current promoted packs become typed adapter inputs? | Done, parent-validated | `backend/adapter_mapping.py` | 5/5 `荒年` moments map and pass formal v0.3 schema. |
| 7. Judgment runtime integration | Can Deadman hand typed judgment work to CABRuntime SDK without owning a duplicate runtime? | Done behind readiness gate | `backend/runtime_client.py`, readiness checker | Formal judgment fails with structured errors; no deterministic fallback. |
| 8. Result media | Can images be generated or selected fast enough without proof pollution? | Future spike | visual result schemas only | Current provider policy is `not_connected`. |
| 9. Production surface | Can a producer upload episodes and get packs/nodes? | Partial CLI only | ARS scripts, runtime data | Needs internal UI or CLI flow hardening. |
| 10. Submission package | Can we show, record, and document the demo for the contest? | Current | Android APK, FastAPI backend, GitHub, demo recording, Feishu tech doc | APK is primary; Web is fallback. |

## Branches Off The Axis

These are side branches, not the main current position.

| Branch | Status | Rejoin condition |
| --- | --- | --- |
| Companion/pet avatar | Concept direction chosen, asset work separate | Rejoins frontend polish when P0 loop is stable. |
| Voice interaction/TTS/ASR | P1 | Rejoins after text judgment quality is stable. |
| Image generation | Interface prepared only | Rejoins after latency/quality/proof-contamination spike. |
| Android/iOS shell | Android current, iOS deferred | Android APK is now the primary frontend delivery route; iOS stays out of scope. |
| Yunmiao/Lihun runtime promotion | Deferred | Rejoins after human review selects runtime demo nodes. |

## Micro Axis

The current micro slice is:

```text
previous: typed schema and visual provider-policy contract
current: backend adapter mapping is complete and validated
next: CABRuntime SDK integration contract plus P0 product/producer hardening
```

### Previous Slice

Problem:

The v0.3 minimum field set was compressed enough to be useful, but several
fields were too loose for backend/LLM consumption.

Solution:

Typed subkeys were added for stakes, escalation, watch flow, capability rules,
information asymmetry, proof state, audience reputation, and visual result
policy.

Product consequence:

The model should not guess the difference between "food shortage", "public
proof", "hidden system exposure", and "relationship backlash" from prose alone.

### Current Slice

Problem:

Runtime-promoted `荒年` moments are still v0.1 packs, while future judgment
expects the v0.3 typed adapter input.

Solution:

`backend/adapter_mapping.py` maps promoted v0.1 moments into
`moment_causality_pack.v0.3.draft` and wraps them as
`deadman_judgment_adapter_input.v0.1`.

Validation:

- 5/5 promoted `荒年` moments map.
- mapped packs pass the formal v0.3 JSON Schema.
- `score_axes` stays producer/debug only.
- public judgment response shape is unchanged.
- no LLM, ASR, image-generation, or external provider is connected.

Product consequence:

The next adapter can consume a typed input instead of loose pack prose. If a
promoted pack is broken, the backend fails closed instead of letting the model
invent missing causal facts.

### Next Slice

Decision needed:

Choose which non-runtime surface to harden while CABRuntime SDK is in progress.

Pragmatic recommendation:

Do not build a Deadman-owned judgment runtime now. Prepare the contract and
visible demo surfaces:

```text
typed adapter input
  -> CABRuntime SDK request contract
  -> runtime/provider execution outside Deadman
  -> schema-shaped adapter output
  -> structured error when runtime/provider fails
  -> existing frontend response shape
```

Why this path:

- It uses the v0.3 mapping immediately.
- It avoids duplicating runtime work while CABRuntime SDK is being built.
- It preserves the product's actual promise: "my action has a credible local
  consequence."
- It makes failure explicit instead of silently returning template output.
- It keeps visible progress on the P0 demo and producer bridge.

Do not do next:

- Do not implement a parallel Deadman judgment runtime.
- Do not add deterministic fallback to formal judgment.
- Do not wire image generation first.
- Do not promote `云渺`/`离婚` to runtime before human review.
- Do not turn Deadman into a continuous branch simulator.
- Do not expose `score_axes` to viewer-facing prompts.

## Active Technical Plan

Current backend plan:

```text
backend/pack_store.py
  -> loads promoted drama/context/moment packs

backend/adapter_mapping.py
  -> creates typed adapter input

Future adapter
  -> consumes typed input
  -> returns deadman_judgment_adapter_output.v0.1

backend/judgment.py
  -> remains the current demo/test boundary until CABRuntime integration is tested
```

Current frontend plan:

```text
frontend
  -> canonical standalone mobile-shaped player

Runtime/frontend
  -> compatibility host bridge only
```

Current producer plan:

```text
local videos in ignored tmp/
  -> ASR/ARS scripts
  -> reviewed candidates
  -> Drama Context Pack + Moment Causality Pack
  -> backend runtime data
```

## Reading Order For A New Agent

For Deadman work, read in this order:

1. `docs/Development_Axis_v0.1.md`
2. `.agent/dev-log.md` tail
3. `docs/WORKSPACE_MAP.md`
4. the relevant selected `docs/goal_spec/*.md`, or archived
   `docs/archive/goal_spec/*.md` if reconstructing old work
5. only then inspect code

This prevents an agent from starting in the wrong layer.

## Update Rules

Update this file when:

- the current macro phase changes;
- a side branch becomes part of the main line;
- a `/goal` changes what "current" means;
- a validation result changes confidence in the active plan;
- a deferred item becomes the recommended next step.

Do not update this file for:

- every bug fix;
- every test run;
- temporary subagent progress;
- raw ARS output counts unless they change product direction.

When updating, change three places:

1. `Current Position`
2. `Macro Axis`
3. `Micro Axis`

Then add one `[Deadman]` entry to `.agent/dev-log.md`.

## Micro Axis Template

Use this block at the top of a new execution thread if context is weak:

```text
Macro position:
- Phase:
- Completed before this:
- Current layer:
- Next likely layer:

Micro position:
- Previous slice:
- Current slice:
- Next slice:
- Active technical plan:
- Do not do:

Validation state:
- Last passed checks:
- Known debt:
- Files to inspect first:
```

## Current Known Debt

| Debt | Product consequence | Recommended handling |
| --- | --- | --- |
| CABRuntime packaging required by default | Text judgment now defaults to `cab_runtime`; if the runner lacks CABRuntime, the judgment path fails closed instead of silently using demo text. | Keep CABRuntime checkout/config in the recording/deploy environment, or explicitly set `DEADMAN_JUDGMENT_ENGINE=demo_deterministic` only for demo/test fallback. |
| Image generation not connected | Custom result images are placeholders/text-only. | Separate spike after text judgment. |
| Producer surface is CLI/script-heavy | Demo can show pipeline but not polished upload UI. | Build only after P0 loop stabilizes. |
| `云渺`/`离婚` are not runtime-promoted | Cross-genre claim is schema evidence, not live demo breadth. | Human review before promotion. |
| Runtime bridge still exists | Some demo paths still compile through legacy host. | Accept during sprint; clean later. |
