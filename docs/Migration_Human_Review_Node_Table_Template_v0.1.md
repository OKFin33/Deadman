# Migration Human Review Node Table Template v0.1

> Product: Deadman / `要是我来`  
> Scope: Yunmiao and Lihun migration evidence  
> Status: v0.1 template; acceptable to revise during review  
> Date: 2026-05-25

## Purpose

This template is for reviewing migration-drama candidate nodes before any
runtime promotion.

Current rule:

```text
Yunmiao / Lihun candidates are schema and field evidence only.
They are not runtime truth until human-reviewed and explicitly promoted.
```

## Recommended Review Size

For each migration drama:

- review 6-10 candidate nodes;
- select 1-2 strong representative nodes;
- do not publish to runtime until product owner accepts the selected nodes.

## Review Table

Copy this table into a per-drama review doc.

| Field | Value |
| --- | --- |
| `review_id` |  |
| `drama_id` | `yunmiao` / `lihun` |
| `drama_title` |  |
| `episode_id` |  |
| `source_start_seconds` |  |
| `source_end_seconds` |  |
| `candidate_hook` |  |
| `scene_summary` |  |
| `user_impulse` |  |
| `why_this_is_a_good_moment` |  |
| `preset_action_a` |  |
| `preset_action_b` |  |
| `preset_action_c` |  |
| `expected_action_types` |  |
| `likely_verdict_range` |  |
| `required_core_fields` |  |
| `required_optional_modules` |  |
| `genre_constraints` |  |
| `information_asymmetry` |  |
| `proof_or_evidence_state` |  |
| `relationship_or_reputation_state` |  |
| `capability_or_power_rules` |  |
| `watch_flow_rationale` |  |
| `source_transcript_refs` |  |
| `source_keyframe_refs` |  |
| `asr_quality` | `good` / `usable` / `weak` / `bad` |
| `visual_evidence_quality` | `good` / `usable` / `weak` / `bad` |
| `review_status` | `reject` / `needs_more_evidence` / `schema_evidence_only` / `promotion_candidate` |
| `reviewer_notes` |  |

## Batch Table Format

For spreadsheet-style review:

| review_id | drama_id | ep | window | hook | user_impulse | mechanism | required_fields | optional_modules | evidence_quality | review_status | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |  |  |  |  |  |

## Review Criteria

Accept a candidate as `promotion_candidate` only if:

- the emotional impulse is obvious without extra explanation;
- the user action can change local consequence without needing a full alternate
  timeline;
- the result can stay within current scene or immediate aftermath;
- required fields are present in v0.3 terms;
- genre rules are explicit enough for judgment;
- evidence refs are publish-safe or can be summarized safely;
- the original plot can still be accepted after the interaction.

Reject or defer if:

- the scene depends on future episode knowledge not present in the window;
- the action requires omniscience or impossible powers;
- the result would need a full social graph or branch timeline;
- ASR/keyframe evidence is too weak to verify the scene;
- the hook is only funny but not causally judgeable.

## Drama-Specific Notes

### Yunmiao

Likely required modules:

- `capability_rules`;
- `information_asymmetry`;
- `audience_reputation_state`;
- `critical_stakes_state`.

Main risk:

```text
overpowered action destroys genre constraint and makes judgment meaningless
```

Review should preserve special power boundaries and hidden-strength logic.

### Lihun

Likely required modules:

- `relationship_state`;
- `proof_state`;
- `audience_reputation_state`;
- `information_asymmetry`.

Main risk:

```text
revenge action becomes pure爽 without credible social/legal cost
```

Review should preserve proof, witnesses, public reputation, and relationship
pressure.

## Promotion Gate

Before runtime promotion, create a reviewed artifact under:

```text
data/dramas/{drama_id}/evidence/
```

Promotion requires:

- product owner accepts the moment;
- source window is verified;
- pack fields are filled;
- adapter mapping can validate;
- no raw `tmp/...` dependency is required at runtime;
- no MP4/MOV file is committed.

Until then, the reviewed nodes may be used only for:

- field sufficiency evidence;
- migration report;
- technical documentation;
- future pack drafting.
