# Multi-Drama Field Induction Report v0.2

> Generated: 2026-05-24

## Summary

This pass upgrades Deadman from a one-drama `荒年` bridge to a source-based three-genre field induction set. The result is not final pack truth for 云渺 or 幸得相遇离婚时; it is schema evidence for the minimum fields a future LLM judgment adapter must consume.

## Per-Drama Results

| Drama | Candidates | Reviewed | Label counts | Candidate artifact | Review artifact |
|---|---:|---:|---|---|---|
| 荒年全村啃树皮，我有系统满仓肉 | 80 | 25 | `reject` 4, `keep` 11, `demo_candidate` 5, `pack_draft` 5 | `tmp/ars_huangnian_analysis/candidates/huangnian_candidates.v0.2.json` | `tmp/ars_huangnian_analysis/review/huangnian_candidates.reviewed.v0.1.json` |
| 云渺 | 67 | 20 | `keep` 12, `schema_evidence` 8 | `tmp/ars_yunmiao_analysis/candidates/yunmiao_candidates.v0.2.json` | `tmp/ars_yunmiao_analysis/review/yunmiao_candidates.reviewed.v0.2.json` |
| 幸得相遇离婚时 | 80 | 18 | `keep` 12, `schema_evidence` 6 | `tmp/ars_lihun_analysis/candidates/lihun_candidates.v0.2.json` | `tmp/ars_lihun_analysis/review/lihun_candidates.reviewed.v0.2.json` |

## v0.1 Fields That Survived

- `source_window`, `review_state`, `companion_surface.hook`, `viewer_impulse`, `actor_context`, `local_constraints`, `canon_baseline`, `action_space`, `judgment_policy`, `outcome_response_contract`, `watch_flow_fit`, `visual_result_policy`, and `producer_review_fields` survive as core.
- `resource_scarcity`, `exposure_and_secrecy`, `relationship_pressure`, `village_or_public_reputation`, `evidence_or_trap_logic`, `system_or_hidden_power_rule`, `humiliation_reversal`, and `survival_tradeoff` survive as optional modules.

## Renamed Or Split

- `system_or_hidden_power_rule` now remains a shared optional module, while 云渺-specific pressure is split into `hidden_power_rule` and `identity_reveal` GenreExtensions.
- Divorce/revenge pressure is not folded into generic `relationship_pressure`; it gets `betrayal_divorce_safety`, `status_reversal_bottom_card`, and `medical_or_pregnancy_risk` extensions.
- `visual_result_policy` now explicitly covers preset image slots and custom text-only fallback.

## Added For 云渺

- `hidden_power_rule`: power state, rule visibility, cost/cooldown, power cap.
- `identity_reveal`: reveal scope, leverage loss, misrecognition value.

## Added For 幸得相遇离婚时

- `betrayal_divorce_safety`: rupture cost, safety status, evidence needed.
- `status_reversal_bottom_card`: institutional leverage, bottom-card timing, future reversal value.
- `medical_or_pregnancy_risk`: rescue priority, evidence preservation, accountability delay.

## Safe To Feed Backend Immediately

- CoreEnvelope fields.
- Optional module names and coarse field pressure.
- Reviewed `荒年` demo packs.
- Migration candidates only as schema evidence, not final frontstage moments.

## Still Requires Human Review

- Any 云渺 / 离婚 candidate before runtime promotion.
- ASR-derived plot facts, named roles, quantities, injuries, pregnancy status, and visual claims.
- Original plot note wording, because it directly affects whether users accept returning to the main drama.

## Blockers / Provider Notes

- No blocking provider failure is encoded in this report if per-drama ASR summaries show successful outputs. Check ignored `tmp/ars_*_analysis/volc_asr/summary.json` for provider-level details.
- Raw provider responses remain under ignored `tmp/` paths.
