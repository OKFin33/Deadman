# Deadman Backend Adapter Mapping v0.1 Goal Spec

> Status: ready for `/goal` execution  
> Repo: `/Users/okfin3/project/GitHub/OKFin33/OSeria-Alter`  
> Product: Branch 3 / Deadman / `要是我来`  
> Date: 2026-05-24

## Goal Prompt

Paste this into the target execution thread:

```text
/goal
Execute the contract in /Users/okfin3/project/GitHub/OKFin33/OSeria-Alter/docs/goal_spec/Deadman_Backend_Adapter_Mapping_v0.1.md.

Build Deadman's backend adapter mapping layer from the existing promoted v0.1 runtime moment packs to the v0.3 typed judgment-adapter input contract. The goal is to prove that the current 5 reviewed Huangnian moments can become schema-shaped v0.3 adapter inputs without letting an LLM infer missing typed subkeys from loose prose. Add a fail-closed mapper, tests, and docs. Do not connect any LLM, ASR, image-generation, or external provider. Do not redesign frontend UI. Do not promote Yunmiao or Lihun to runtime. Do not add MP4/MOV, raw provider outputs, API keys, local .env files, or unreviewed candidate facts as runtime truth.

Before editing, read docs/Backend_Judgment_Adapter_Interface_v0.1.md, docs/Moment_Causality_Pack_v0.3_Draft.md, docs/Typed_Subkeys_Patch_Report_v0.1.md, docs/Visual_Result_Interface_Prep_v0.1.md, backend/judgment.py, backend/pack_store.py, and data/dramas/huangnian/moments.v0.1.json.
```

## Why This Goal Exists

Deadman now has:

```text
promoted runtime packs: moment_causality_pack.v0.1
minimum computable contract: moment_causality_pack.v0.3.draft
adapter boundary: deadman_judgment_adapter_input.v0.1
```

But the backend still judges directly against the old promoted pack shape.

Product consequence: if the next step connects an LLM directly to v0.1 moment
fields, the model will re-infer stake type, proof state, capability limits,
watch-flow boundaries, and visual proof policy from loose prose. That loses the
red-team patch.

This goal adds the bridge:

```text
existing promoted v0.1 moment pack
  -> fail-closed v0.3 typed moment view
  -> deadman_judgment_adapter_input.v0.1
```

It does not replace the deterministic judgment engine yet. It prepares the
engine boundary so a later CABRuntime SDK integration has a strict input.

## Current Inputs

Read these tracked files:

```text
backend/models.py
backend/judgment.py
backend/pack_store.py
backend/tests/test_judgment_api.py
data/dramas/huangnian/context.v0.1.json
data/dramas/huangnian/moments.v0.1.json
data/schemas/moment_causality_pack.v0.3.draft.json
data/schemas/deadman_judgment_adapter_input.v0.1.json
data/schemas/visual_result_plan.v0.1.json
docs/Backend_Judgment_Adapter_Interface_v0.1.md
docs/Moment_Causality_Pack_v0.3_Draft.md
docs/Visual_Result_Interface_Prep_v0.1.md
```

Important current facts:

- `backend/judgment.py` currently consumes v0.1 fields directly.
- `data/dramas/huangnian/moments.v0.1.json` contains 5 reviewed runtime
  moments.
- v0.3 typed schemas are contracts, not runtime pack truth yet.
- `score_axes` is producer/evaluation metadata and must not become
  viewer-facing evidence.
- `provider_policy` must be top-level visible in both `visual_result_policy`
  and `visual_result_plan`.

## Objective

Implement a backend-only mapping layer that can:

1. Convert each promoted Huangnian v0.1 moment into a v0.3 typed moment pack.
2. Wrap that typed moment pack into `deadman_judgment_adapter_input.v0.1`.
3. Fail closed when required source fields are absent instead of fabricating
   unsupported typed facts.
4. Preserve deterministic judgment behavior for current API responses.
5. Record exactly what is mapped, what is conservatively defaulted, and what
   remains future adapter work.

## Required Outputs

Code:

```text
backend/adapter_mapping.py
```

Tests:

```text
backend/tests/test_adapter_mapping.py
```

Docs:

```text
docs/Backend_Adapter_Mapping_v0.1.md
```

Updates:

```text
backend/README.md
backend/judgment.py
backend/tests/test_judgment_api.py
.agent/dev-log.md
```

Only update `models.py` if a small model addition materially clarifies the
mapping boundary. Do not perform a broad response-model migration in this goal.

## Non-Goals

Do not:

- call LLM providers;
- call ASR providers;
- call image-generation providers;
- change frontend UI;
- change the public `POST /api/deadman/judgment` response shape unless tests
  require a strictly additive debug field;
- promote Yunmiao or Lihun to runtime;
- mutate `data/dramas/huangnian/moments.v0.1.json`;
- generate or copy MP4/MOV files;
- add `.env` or provider keys;
- add continuous branch timeline semantics;
- expose `producer_only.score_axes` as viewer evidence.

## Adapter Ownership

Create:

```python
backend/adapter_mapping.py
```

Suggested public API:

```python
class AdapterMappingError(Exception):
    code: str
    message: str

def build_adapter_input(
    *,
    request_id: str,
    drama_pack: DramaPack,
    moment: dict[str, Any],
    request: JudgmentRequest,
) -> dict[str, Any]:
    ...

def build_typed_moment_pack(
    *,
    drama_pack: DramaPack,
    moment: dict[str, Any],
) -> dict[str, Any]:
    ...
```

Use plain dictionaries for now unless Pydantic models are already cheap and
localized. The source of truth is the JSON schema contract, not a new model tree.

`DeterministicJudgmentService.judge()` should invoke the mapper before producing
the current deterministic response. For now, it can use the mapped result only
for validation/debug/internal basis. Do not route user-visible text generation
through a new engine in this goal.

If mapping fails during the current public judgment endpoint, return a structured
backend error rather than silently falling back to old pack prose.

## Mapping Rules

### Top-level identity

| v0.1 source | v0.3 target |
| --- | --- |
| `moment_id` or `pack_id` | `pack_id` |
| fixed mapping constant | `schema_version="moment_causality_pack.v0.3.draft"` |
| `source_drama.drama_id` or pack drama id | `source_window.drama_id` |
| `source_drama.episode_id` | `source_window.episode_id` |
| `source_window.start_ms/end_ms` | `source_window.start_ms/end_ms` |

If `source_window.start_ms` or `source_window.end_ms` is missing, fail closed.

### Review and provenance

Map:

```text
review_state
provenance
source_refs
producer_review_fields.field_evidence_refs
source_window.transcript_refs
source_window.keyframe_refs
```

into `review_and_provenance`.

Do not include raw `tmp/...` paths in runtime-facing fields.

### Companion entry

Map:

```text
companion_surface.notice_marker
companion_surface.hook
companion_surface.viewer_impulse
interaction_window
```

into `companion_entry`.

### Action space

Map:

```text
action_space.action_type
action_space.default_options
action_space.custom_action_policy
```

into v0.3 `action_space`.

Preset action mapping should add stable preset ids in adapter input:

```text
preset_0, preset_1, preset_2
```

Do not rewrite the existing frontend option labels.

### Response contract

Map:

```text
outcome_response_contract.time_horizon
judgment_policy.must_not_claim
```

into:

```json
{
  "time_horizon": "current_scene_or_immediate_aftermath",
  "allow_future_branch_claims": false,
  "allow_canon_wrong_claims": false
}
```

If the source pack asks for a non-local time horizon, fail closed.

### Visual result policy

Map old `visual_result_policy` and `result_media` into the strict v0.3 shape:

```json
{
  "result_media_mode": "preset_slot|text_only|none",
  "truth_level": "illustrative_result",
  "proof_eligibility": "never",
  "must_not_be_used_as_proof": true,
  "fallback": "text_only|placeholder_slot",
  "latency_budget_ms": 0,
  "provider_policy": "not_connected",
  "visual_prompt_plan": {
    "prompt_source": "preset|judgment_result|none",
    "prompt_text": "",
    "negative_constraints": [
      "do not present generated images as evidence",
      "do not imply later episodes follow this branch"
    ],
    "style_policy": "short_drama_result_card|neutral_illustration|none",
    "provider_policy": "not_connected"
  }
}
```

For current placeholder media slots:

- preset options should map to `result_media_mode="preset_slot"`;
- custom actions should map to `result_media_mode="text_only"` or
  `plan_only` at adapter-output stage;
- generated image proof must remain blocked.

### Actor local state

Map:

```text
actor_context.pov_actor
actor_context.directly_affected_actors
actor_context.relationship_context
actor_context.local_emotional_pressure
```

into `actor_local_state`.

If `pov_actor` is missing, use `"主角"` and add a mapping warning.

### Critical stakes state

Map from `optional_modules` and `actor_context`.

Supported source modules:

```text
resource_scarcity
relationship_pressure
evidence_or_trap_logic
humiliation_reversal
village_or_public_reputation
system_or_hidden_power_rule
exposure_and_secrecy
```

Use conservative typed values:

```json
{
  "stake_type": "resource|relationship|reputation|power|status|other",
  "stake_owner": "string",
  "time_pressure": "immediate|short_term|deferred|none|unknown",
  "scarcity_or_risk_level": "low|medium|high|unknown",
  "irreversibility": "reversible|costly|irreversible|unknown",
  "risk_if_action": "string",
  "risk_if_no_action": "string"
}
```

Fail closed only if no module, actor context, canon baseline, or local
constraint can identify what is materially at stake. Otherwise prefer
`unknown` enum values plus a mapping warning over inventing precision.

### Local constraint state

Map:

```text
local_constraints.known_facts
local_constraints.unknown_or_hidden_facts
local_constraints.hard_constraints
local_constraints.risk_notes
context.core_constraints
context.judgment_guardrails
```

into `local_constraint_state`.

Do not copy `context.evidence_map` wholesale into the viewer-facing prompt; use
ids and concise claims only.

### Escalation risk

Map from:

```text
local_constraints.risk_notes
context.core_constraints
optional_modules.exposure_and_secrecy
optional_modules.village_or_public_reputation
optional_modules.system_or_hidden_power_rule
```

Required typed shape:

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

### Canon baseline

Map:

```text
canon_baseline.original_action
canon_baseline.original_rationale
canon_baseline.audience_tension
canon_baseline.original_plot_note
original_plot_note
```

into `canon_baseline`.

### Watch-flow rationale

Map:

```text
canon_baseline.original_plot_note
canon_baseline.original_rationale
outcome_response_contract.include_original_plot_note
judgment_policy.must_not_claim
```

into:

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

The adapter must preserve the product stance: Deadman gives a local consequence,
not a real alternate episode branch.

## Optional Module Mapping

Map optional modules only when the source has supporting evidence.

| v0.1 module | v0.3 optional module |
| --- | --- |
| `relationship_pressure` | `relationship_state` |
| `system_or_hidden_power_rule` | `capability_rules` |
| `exposure_and_secrecy` | `information_asymmetry`, maybe `capability_rules` |
| `evidence_or_trap_logic` | `proof_state`, `information_asymmetry` |
| `village_or_public_reputation` | `audience_reputation_state` |
| `humiliation_reversal` | `audience_reputation_state`, maybe `proof_state` |
| `resource_scarcity` | usually core `critical_stakes_state`, not a separate v0.3 module |

Do not create an optional module solely to make the schema look complete.

## Producer-only Handling

`score_axes` can be copied only under:

```text
moment_pack.producer_only.score_axes
adapter_input.debug.score_axes
```

It must not appear in viewer-facing prompt material or in fields named
`evidence`, `why_this_happens`, or `used_fields`.

Add a test for this.

## Adapter Input Shape

`build_adapter_input()` must return:

```json
{
  "request_id": "string",
  "drama_id": "huangnian",
  "moment_pack": {},
  "user_action": {
    "origin": "preset|custom",
    "action_type": "resource|relationship|proof|...",
    "text": "string",
    "preset_id": "preset_0|null"
  },
  "runtime_policy": {
    "time_horizon": "current_scene_or_immediate_aftermath",
    "allow_future_branch_claims": false,
    "allow_visual_as_proof": false,
    "output_language": "zh-CN",
    "hide_producer_only_fields_from_prompt": true
  },
  "requested_output": {
    "text_result": true,
    "visual_result": "preset_slot|plan_only|none"
  },
  "debug": {
    "mapping_version": "deadman_backend_adapter_mapping.v0.1",
    "source_schema_version": "moment_causality_pack.v0.1",
    "mapping_warnings": []
  }
}
```

The returned dict must conform structurally to
`deadman_judgment_adapter_input.v0.1.json`.

If full JSON Schema validation is easy with existing dependencies, add it. If
not, write a local structural validator for the contract fields that matter:

- required top-level adapter input fields;
- required v0.3 moment pack fields;
- required typed subkeys;
- visual provider policy at top level and prompt level;
- local runtime policy constants.

Do not add a large new dependency only for JSON Schema validation in this goal.

## Fail-Closed Rules

The mapper must fail closed when:

- `source_window.start_ms` or `source_window.end_ms` is missing;
- no `moment_id` or `pack_id` exists;
- no action options exist for a preset moment;
- `outcome_response_contract.time_horizon` contradicts local-only judgment;
- `visual_result_policy` cannot be made proof-blocking;
- `critical_stakes_state` has no grounded source for what is at stake;
- `watch_flow_rationale` cannot block future-branch claims;
- `score_axes` would leak into viewer-facing mapped fields.

Failure should use a small typed exception:

```python
AdapterMappingError(code="adapter_mapping_invalid", message="...")
```

When called from the public judgment endpoint, convert this into a structured
5xx or 422-style API error. Prefer 500 for broken promoted pack data and 422
for invalid user action payloads.

## Deterministic Judgment Integration

Patch `DeterministicJudgmentService.judge()` to build adapter input before it
returns the existing deterministic response.

Do not use the adapter input to change current Chinese result text yet.

Allowed internal uses:

- validate the promoted pack can be adapter-shaped;
- include a non-user-facing inference note such as
  `"Adapter mapping v0.1 validated typed input."`;
- add `debug` only if current response models/tests already have a suitable
  place and it does not affect frontend assumptions.

The public response should remain compatible with current frontend tests.

## Documentation Requirements

Create:

```text
docs/Backend_Adapter_Mapping_v0.1.md
```

It must explain:

- why v0.1 promoted packs are not enough for future LLM adapter prompts;
- mapping table from v0.1 fields to v0.3 typed fields;
- fail-closed policy;
- score_axes isolation;
- visual proof and provider-policy boundary;
- what this enables next.

Update:

```text
backend/README.md
```

Add a short section describing the adapter mapping layer and that the current
engine is still deterministic.

Append `.agent/dev-log.md` with a `[Deadman]` entry.

## Tests

Add tests in:

```text
backend/tests/test_adapter_mapping.py
```

Minimum tests:

1. All 5 promoted Huangnian moments map successfully.
2. Each mapped adapter input has:
   - `schema_version="moment_causality_pack.v0.3.draft"`;
   - required v0.3 top-level fields;
   - required typed subkeys for `critical_stakes_state`,
     `escalation_risk`, and `watch_flow_rationale`;
   - top-level `visual_result_policy.provider_policy`;
   - nested `visual_prompt_plan.provider_policy`;
   - runtime policy forbidding future branch claims and visual proof.
3. Preset action maps to stable `preset_id`.
4. Custom action maps with `preset_id=null` and does not create future branch
   claims.
5. Removing `source_window.start_ms` from a copied moment fails closed.
6. Removing `critical_stakes_state` source material from a copied moment fails
   closed or emits a tested explicit mapping error.
7. `score_axes` does not appear in viewer-facing mapped fields.
8. Public judgment API still returns the existing deterministic response shape.

Update existing judgment API tests only when needed to assert adapter validation
does not break current behavior.

## Verification Commands

Run:

```bash
python3 -m py_compile backend/*.py backend/tests/*.py
python3 -m unittest Deadman.backend.tests.test_adapter_mapping -v
python3 -m unittest Deadman.backend.tests.test_judgment_api -v
cd frontend && npm test
cd Runtime/frontend && npm test
```

Run schema parse checks:

```bash
python3 -m json.tool data/schemas/moment_causality_pack.v0.3.draft.json >/dev/null
python3 -m json.tool data/schemas/deadman_judgment_adapter_input.v0.1.json >/dev/null
python3 -m json.tool data/schemas/visual_result_plan.v0.1.json >/dev/null
```

Run safety checks:

```bash
find Deadman docs/goal_spec -type f \( -name '*.mp4' -o -name '*.mov' -o -name '*.m4v' -o -name '.env' -o -name '.env.*' \) -print
```

Expected: no output.

Clean Python cache after tests:

```bash
find Deadman -type d -name __pycache__ -prune -exec rm -rf {} +
```

## Acceptance Criteria

This goal is complete only if:

- `backend/adapter_mapping.py` exists and is covered by tests;
- all 5 current Huangnian promoted moments map to adapter inputs;
- mapper fails closed on broken required source fields;
- visual provider policy is visible at the top level and prompt level;
- score axes remain producer/debug only;
- no provider calls are added;
- existing judgment API behavior remains compatible;
- verification commands pass;
- `.agent/dev-log.md` has a `[Deadman]` entry.

## Expected Final Report

The execution agent should report:

- files changed;
- whether 5/5 Huangnian moments mapped;
- exact fail-closed tests added;
- whether public judgment response changed;
- verification command results;
- confirmation that no provider, media, env, or secret files were added;
- remaining debt before the formal CABRuntime SDK integration.

## Remaining Debt After This Goal

After this mapping layer exists, the next work should be one of:

1. Define and later wire the CABRuntime SDK integration that consumes the mapped
   input and returns `deadman_judgment_adapter_output.v0.1` or structured error.
2. Add a producer-side migration script that writes reviewed v0.3 packs directly
   instead of mapping from v0.1 at runtime.
3. Run the image/provider spike for latency, quality, actor-likeness safety,
   fallback behavior, and visual-proof contamination.

Do not collapse those into this goal.
