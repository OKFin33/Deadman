# Visual Result Interface Prep v0.1

> Product: Deadman / 要是我来  
> Scope: provider-neutral visual contract  
> Provider integration: not connected

## Boundary

This goal prepares image-related interfaces without connecting any image model.
The current product remains text-first with placeholder/preset media slots.

The reason is product risk, not implementation difficulty:

- realtime image generation may be too slow for a short-drama interaction loop;
- generated images can be mistaken for proof;
- actor likeness, safety, and style consistency need a separate eval before
  shipping.

## Schemas

Tracked schemas:

```text
data/schemas/visual_result_plan.v0.1.json
data/schemas/visual_result_request.v0.1.json
data/schemas/visual_result_response.v0.1.json
```

## visual_result_plan

Emitted by judgment. It decides whether the frontend should show a preset slot,
hold a future prompt plan, fall back to text, or show no visual result.

Required boundary fields:

- `truth_level`
- `proof_eligibility`
- `must_not_be_used_as_proof`
- `fallback`
- `latency_budget_ms`
- `provider_policy`
- `visual_prompt_plan.provider_policy`

Top-level `provider_policy` is currently `not_connected` or
`future_spike_required`. `visual_prompt_plan.provider_policy` mirrors that
boundary for prompt-specific handling and must not imply a connected provider.

## visual_result_request

Future visual service request. This is not used by runtime yet.

It includes:

- `mode`: `preset_slot`, `realtime_generation`, or `text_only`
- `truth_level`
- `prompt`
- `negative_constraints`
- `latency_budget_ms`
- `fallback`

Generated request prompts must not imply canon proof or exact actor likeness
unless licensing and review allow it.

## visual_result_response

Future visual service response. Generated media must remain illustrative unless
a producer-only review process marks it otherwise.

Required response semantics:

- `status=not_connected` is valid before provider integration;
- `proof_eligibility=never` is the generated-media default;
- `fallback_reason` must explain why text-only or placeholder output was used.

## Proof Boundary

Generated result images are never evidence for `proof_state`.

Keyframes/source references may help locate the moment, but they cannot prove
new generated consequences. The schema therefore keeps `visual_result_policy`
separate from `proof_state`.

## Future Provider Spike

A separate spike is required before realtime image generation ships:

- latency: P50/P90 under the interaction budget;
- quality: stable short-drama result-card style;
- safety: no unsafe content or unlicensed actor likeness;
- proof contamination: users do not read generated images as canon evidence;
- fallback: text-only remains acceptable when generation fails.
