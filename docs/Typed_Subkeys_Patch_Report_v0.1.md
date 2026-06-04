# Typed Subkeys Patch Report v0.1

> Product: Deadman / 要是我来  
> Scope: schema/interface readiness  
> Runtime behavior change: none

## Why This Patch Was Required

Field Minimum Red Team v0.1 returned `pass_with_required_patch`. The v0.3
minimum field set was sufficient, but several compressed fields were still too
loose for backend judgment consumption.

Product consequence: if the adapter reads those fields as arbitrary prose, it
can produce爽感 that ignores the exact kind of stake, reveal timing, ability
limit, or backlash.

## Patched Fields

| Field | Patch |
| --- | --- |
| `critical_stakes_state` | Added typed stake, owner, time pressure, risk level, irreversibility, action/no-action risk. |
| `escalation_risk` | Added risk type/source, immediacy, severity, mitigation, and escalation actors. |
| `watch_flow_rationale` | Kept separate from `canon_baseline`; added original-still-works, viewer-return line, and blocked claims. |
| `capability_rules` | Added capability type, hard limit, activation cost, visibility cost, known-to flags, and overuse failure. |
| `information_asymmetry` | Added hidden fact, who knows/does not know/would learn, reveal timing, leverage change, and reveal cost. |
| `proof_state` | Added proof type, availability, threshold, holder, unsupported-claim risk, and evidence refs. |
| `audience_reputation_state` | Added audience scope/alignment, status at stake, humiliation vector, and likely reaction. |
| `relationship_state` | Added a small typed shape for relationship type, trust, dependency, and protection priority. |
| `visual_result_policy` | Added truth level, proof eligibility, explicit proof block, fallback, latency budget, top-level provider policy, and provider-neutral prompt plan. |

## Files Updated

- `data/schemas/moment_causality_pack.v0.3.draft.json`
- `docs/Moment_Causality_Pack_v0.3_Draft.md`

## Fields Still Excluded

The patch does not re-add `branch_timeline`, `global_inventory`,
`full_social_graph`, `auto_visual_truth`, or `return_to_plot_fit`.

Those exclusions are intentional. P0 only judges the current scene or immediate
aftermath; it does not claim the story actually branches.

## Adapter Consequence

The backend adapter can now consume one small field set with typed internals.
This keeps the field count low while preventing the model from inventing the
missing distinctions inside fused fields.

This patch does not connect an LLM, ASR, image model, or frontend UI.
