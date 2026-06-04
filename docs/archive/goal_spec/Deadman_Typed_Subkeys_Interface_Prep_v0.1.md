# Deadman Typed Subkeys and Interface Prep v0.1 Goal Spec

> Status: ready for `/goal` execution  
> Repo: `/Users/okfin3/project/GitHub/OKFin33/OSeria-Alter`  
> Product: Branch 3 / Deadman / `要是我来`  
> Date: 2026-05-24  

## Goal Prompt

Paste this into the target execution thread:

```text
/goal
Execute the contract in /Users/okfin3/project/GitHub/OKFin33/OSeria-Alter/docs/goal_spec/Deadman_Typed_Subkeys_Interface_Prep_v0.1.md.

Patch Deadman's v0.3 Moment Causality Pack draft so the red-team-required typed subkeys are explicit, and prepare backend judgment plus visual-result interfaces without integrating any real image-generation provider. The goal is schema/interface readiness, not runtime behavior change. Use the v0.3 minimum field set and v0.1 red-team findings as source of truth. Do not modify frontend UI or backend judgment logic unless a tiny compatibility test fixture is necessary. Do not call ASR, LLM, image-generation, or other providers. Do not add MP4/MOV, raw provider outputs, API keys, local .env files, or unreviewed candidate facts as runtime truth.

Before editing, read docs/Moment_Field_Minimum_Set_v0.3.md, docs/Field_Minimum_Red_Team_v0.1.md, and docs/Moment_Causality_Pack_v0.3_Draft.md.
```

## Why This Goal Exists

The v0.3 minimum field set passed red team only as:

```text
pass_with_required_patch
```

The 18 active fields are sufficient for P0 local consequence judgment, but the
red team found that several compressed fields cannot remain untyped prose blobs.
If the backend adapter or future LLM prompt consumes them as `{}` or arbitrary
natural language, the model will guess the missing distinctions.

Product consequence:

- `critical_stakes_state` without typed subkeys can confuse food scarcity,
  bodily injury, pregnancy risk, and reputation loss.
- `information_asymmetry` without typed subkeys can confuse who knows what and
  when revealing information helps or burns leverage.
- `capability_rules` without typed subkeys can turn hidden powers or systems
  into unconditional cheats.
- `visual_result_policy` without explicit truth/fallback rules lets generated
  images look like evidence.

This goal fixes those contract gaps before backend judgment adapter work.

## Current Inputs

Read these tracked docs:

```text
docs/Moment_Field_Minimum_Set_v0.3.md
docs/Field_Demand_Cluster_Report_v0.3.md
docs/Moment_Causality_Pack_v0.3_Draft.md
docs/Field_Minimum_Red_Team_v0.1.md
docs/Field_Minimum_Red_Team_Findings_v0.1.md
data/schemas/moment_causality_pack.v0.3.draft.json
data/evals/field_minimum_red_team.v0.1.json
```

Important red-team requirements:

| Field | Required subkeys |
|---|---|
| `critical_stakes_state` | `stake_type`, `stake_owner`, `time_pressure`, `scarcity_or_risk_level`, `irreversibility` |
| `information_asymmetry` | `hidden_fact`, `who_knows`, `who_would_learn`, `reveal_timing`, `leverage_change` |
| `capability_rules` | `capability_type`, `hard_limit`, `activation_cost`, `visibility_cost`, `known_to_actor`, `known_to_others` |
| `proof_state` | `proof_type`, `available_now`, `threshold`, `holder`, `risk_if_claimed_without_proof` |
| `audience_reputation_state` | `audience_scope`, `audience_alignment`, `status_at_stake`, `humiliation_vector` |
| `escalation_risk` | `risk_type`, `risk_source`, `immediacy`, `severity`, `mitigation` |
| `visual_result_policy` | explicit `truth_level`, fallback, and proof-blocking semantics |

## Objective

Produce a typed, adapter-ready contract:

```text
v0.3 minimum fields + red-team findings
  -> typed subkey patch for compressed fields
  -> stricter Moment Causality Pack v0.3 draft schema
  -> backend judgment adapter input/output interface schema
  -> visual result plan/request/response interface schema
  -> docs explaining what is now ready and what is intentionally not connected
```

This is not an LLM adapter implementation and not an image-generation spike.

## Required Outputs

Tracked docs:

```text
docs/Typed_Subkeys_Patch_Report_v0.1.md
docs/Backend_Judgment_Adapter_Interface_v0.1.md
docs/Visual_Result_Interface_Prep_v0.1.md
docs/Moment_Causality_Pack_v0.3_Draft.md
```

Tracked schemas:

```text
data/schemas/moment_causality_pack.v0.3.draft.json
data/schemas/deadman_judgment_adapter_input.v0.1.json
data/schemas/deadman_judgment_adapter_output.v0.1.json
data/schemas/visual_result_plan.v0.1.json
data/schemas/visual_result_request.v0.1.json
data/schemas/visual_result_response.v0.1.json
```

Optional tracked example fixtures:

```text
data/examples/typed_subkeys/huangnian_pack_example.v0.1.json
data/examples/typed_subkeys/yunmiao_pack_example.v0.1.json
data/examples/typed_subkeys/lihun_pack_example.v0.1.json
```

If examples are added, they must be clearly marked as schema examples, not
runtime-promoted packs.

## Non-Goals

Do not:

- call image-generation models;
- add image-generation provider credentials;
- call LLM providers;
- change backend judgment behavior;
- redesign frontend UI;
- promote 云渺 or 离婚 packs to runtime;
- add branch timeline, global inventory, full social graph, auto visual truth,
  or return-to-plot fields;
- make generated images evidence.

## Phase 1 - Patch Moment Pack Typed Subkeys

Update:

```text
docs/Moment_Causality_Pack_v0.3_Draft.md
data/schemas/moment_causality_pack.v0.3.draft.json
```

### Core causal field requirements

`critical_stakes_state` must support:

```json
{
  "stake_type": "resource|bodily_safety|pregnancy|reputation|relationship|legal|status|power|other",
  "stake_owner": "string",
  "time_pressure": "immediate|short_term|deferred|none|unknown",
  "scarcity_or_risk_level": "low|medium|high|unknown",
  "irreversibility": "reversible|costly|irreversible|unknown",
  "risk_if_action": "string",
  "risk_if_no_action": "string"
}
```

`escalation_risk` must support:

```json
{
  "risk_type": "social|physical|legal|resource|relationship|capability_exposure|watch_flow|other",
  "risk_source": "string",
  "immediacy": "immediate|short_term|deferred|unknown",
  "severity": "low|medium|high|critical|unknown",
  "mitigation": "string",
  "who_can_escalate": []
}
```

`watch_flow_rationale` must stay separate from `canon_baseline` and support:

```json
{
  "why_original_still_works": "string",
  "viewer_return_line": "string",
  "must_not_claim": [
    "future episodes follow this branch",
    "canon was wrong",
    "the branch continues automatically"
  ]
}
```

### Optional module requirements

`capability_rules` must support:

```json
{
  "capability_type": "system|hidden_power|status_power|knowledge|physical|social|none|other",
  "hard_limit": "string",
  "activation_cost": "string",
  "visibility_cost": "string",
  "known_to_actor": true,
  "known_to_others": false,
  "failure_mode_if_overused": "string"
}
```

`information_asymmetry` must support:

```json
{
  "hidden_fact": "string",
  "who_knows": [],
  "who_does_not_know": [],
  "who_would_learn": [],
  "reveal_timing": "now|later|avoid|unknown",
  "leverage_change": "gain|loss|mixed|none|unknown",
  "cost_of_reveal": "string"
}
```

`proof_state` must support:

```json
{
  "proof_type": "witness|record|object|medical|legal|business|visual_reference|none|other",
  "available_now": true,
  "threshold": "low|medium|high|unknown",
  "holder": "string",
  "risk_if_claimed_without_proof": "string",
  "evidence_refs": []
}
```

`audience_reputation_state` must support:

```json
{
  "audience_scope": "private|family|village|public|institutional|online|unknown",
  "audience_alignment": "supportive|hostile|mixed|neutral|unknown",
  "status_at_stake": "string",
  "humiliation_vector": "string",
  "likely_reaction": "string"
}
```

`relationship_state` may be patched if needed, but red team did not require a
high-severity typed-subkey patch. If touched, keep it small:

```json
{
  "relationship_type": "family|romantic|marriage|village|enemy|ally|institutional|unknown",
  "trust_level": "low|medium|high|broken|unknown",
  "dependency": "none|emotional|resource|safety|status|legal|unknown",
  "protection_priority": "string"
}
```

## Phase 2 - Patch Visual Result Policy

`visual_result_policy` must become explicit enough to support future image
generation without letting images become proof.

Required shape:

```json
{
  "result_media_mode": "preset_slot|realtime_generation|text_only|none",
  "truth_level": "illustrative_result|source_reference|reviewed_visual_evidence",
  "proof_eligibility": "never|producer_review_only",
  "must_not_be_used_as_proof": true,
  "fallback": "text_only|placeholder_slot|retry_later",
  "latency_budget_ms": 0,
  "visual_prompt_plan": {
    "prompt_source": "preset|judgment_result|none",
    "prompt_text": "",
    "negative_constraints": [
      "do not imply canon proof",
      "do not claim all characters witnessed this image",
      "avoid exact actor likeness unless licensed"
    ],
    "style_policy": "short_drama_result_card|neutral_illustration|none",
    "provider_policy": "not_connected|future_spike_required"
  }
}
```

Rules:

- `truth_level=illustrative_result` means the image is not evidence.
- `truth_level=source_reference` means it points to a source/keyframe but still
  cannot prove new generated consequences.
- `truth_level=reviewed_visual_evidence` is producer-side only and must not be
  used to claim generated branches are canon.
- `proof_eligibility` must default to `never` for generated result media.
- `fallback` must allow text-only output.

## Phase 3 - Backend Judgment Interface Prep

Add schemas and docs for adapter input/output, but do not implement the
adapter unless the repo already has a natural place for passive schema
fixtures.

### Input schema

`deadman_judgment_adapter_input.v0.1.json` should represent:

```json
{
  "request_id": "string",
  "drama_id": "string",
  "moment_pack": {},
  "user_action": {
    "origin": "preset|custom",
    "action_type": "string",
    "text": "string",
    "preset_id": "string"
  },
  "runtime_policy": {
    "time_horizon": "current_scene_or_immediate_aftermath",
    "allow_future_branch_claims": false,
    "allow_visual_as_proof": false,
    "output_language": "zh-CN"
  },
  "requested_output": {
    "text_result": true,
    "visual_result": "preset_slot|plan_only|none"
  }
}
```

### Output schema

`deadman_judgment_adapter_output.v0.1.json` should represent:

```json
{
  "request_id": "string",
  "verdict": "credible_win|credible_costly_win|mixed|backfires|invalid_or_overpowered",
  "result_text": "string",
  "companion_reaction": "string",
  "why_this_happens": [],
  "watch_flow_rationale": "string",
  "used_fields": [],
  "blocked_claims": [],
  "visual_result_plan": {},
  "engine_metadata": {
    "mode": "deterministic|llm|hybrid",
    "schema_version": "string"
  }
}
```

Important:

- `score_axes` must not enter the viewer-facing prompt.
- `producer_only` fields may travel for debug/review, but adapter docs must
  say frontend ignores them.
- Adapter output must always include a local horizon and watch-flow rationale.

## Phase 4 - Visual Result Interface Prep

Add schemas and docs for image integration without connecting a provider.

`visual_result_plan.v0.1.json` describes what the judgment adapter emits.

`visual_result_request.v0.1.json` describes a future visual service request:

```json
{
  "request_id": "string",
  "moment_id": "string",
  "mode": "preset_slot|realtime_generation|text_only",
  "truth_level": "illustrative_result|source_reference|reviewed_visual_evidence",
  "prompt": "string",
  "negative_constraints": [],
  "latency_budget_ms": 0,
  "fallback": "text_only|placeholder_slot|retry_later"
}
```

`visual_result_response.v0.1.json` describes a future visual service response:

```json
{
  "request_id": "string",
  "status": "ready|fallback|failed|not_connected",
  "media_slot": {
    "slot_id": "string",
    "media_url": "string",
    "placeholder": true
  },
  "truth_level": "illustrative_result",
  "proof_eligibility": "never",
  "fallback_reason": "string"
}
```

Docs must clearly state:

- no provider is connected in this goal;
- provider spike comes later;
- latency, quality, actor likeness, safety, and proof-contamination need a
  separate eval before realtime image generation ships.

## Phase 5 - Compatibility And Examples

If adding examples, use existing `huangnian` promoted data and schema-evidence
nodes only as illustrative field examples. Do not promote new runtime packs.

Examples should validate against the updated schema where feasible.

## Verification

Required commands:

```bash
python3 -m py_compile tools/ars/*.py backend/*.py backend/tests/*.py
python3 -m unittest Deadman.backend.tests.test_judgment_api -v
cd frontend && npm test
cd Runtime/frontend && npm test
python3 -m json.tool data/schemas/moment_causality_pack.v0.3.draft.json >/dev/null
python3 -m json.tool data/schemas/deadman_judgment_adapter_input.v0.1.json >/dev/null
python3 -m json.tool data/schemas/deadman_judgment_adapter_output.v0.1.json >/dev/null
python3 -m json.tool data/schemas/visual_result_plan.v0.1.json >/dev/null
python3 -m json.tool data/schemas/visual_result_request.v0.1.json >/dev/null
python3 -m json.tool data/schemas/visual_result_response.v0.1.json >/dev/null
find Deadman Runtime/frontend docs/goal_spec -type f \( -iname '*.mp4' -o -iname '*.mov' -o -iname '.env' \) -print
rg -n --glob '!Runtime/frontend/dist/**' --glob '!frontend/dist/**' 'ark-[A-Za-z0-9-]{20,}|[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}' Deadman Runtime/frontend docs/goal_spec 2>/dev/null || true
find Deadman -type d -name __pycache__ -print
```

Expected:

- backend/frontend behavior remains unchanged;
- all JSON schemas parse;
- tests still pass;
- no media/env/secrets are added;
- generated `__pycache__` is removed before final report.

## Required Final Report

The execution agent final report must include:

- files changed;
- whether backend/frontend runtime behavior changed;
- typed subkeys added;
- visual interface boundary and non-goals;
- judgment adapter interface summary;
- whether examples were added and whether they are runtime-promoted;
- verification results;
- safety scan result;
- dev-log confirmation.

## Dev Log Requirement

Append one chronological entry to `.agent/dev-log.md` with `[Deadman]` prefix.

Required content:

- typed subkey patch executed;
- visual interface prepared without provider integration;
- backend judgment interface prepared without runtime behavior change;
- remaining provider/image spike debt.
