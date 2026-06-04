# Field Minimum Red Team Findings v0.1

## FMRT-001 - Accepted fusions survive only if schemas require typed subkeys.

- Severity: `high`
- Affected fields: critical_stakes_state, information_asymmetry, capability_rules, escalation_risk
- Affected clusters: critical_stakes_tradeoff, visibility_and_timing, capability_bound_visibility, public_escalation
- Product consequence: Without typed subkeys, the backend can produce爽感 that ignores the exact kind of stake, reveal, ability limit, or backlash.
- Recommendation: Do not split these fields. Patch the v0.3 draft schema and adapter prompt with required typed subkeys.

## FMRT-002 - response_contract and watch_flow_rationale are non-removable boundary fields.

- Severity: `high`
- Affected fields: response_contract, watch_flow_rationale, canon_baseline
- Affected clusters: capability_bound_visibility, critical_stakes_tradeoff, critical_stakes_with_proof, proof_before_reversal, public_escalation, relationship_rupture, visibility_and_timing
- Product consequence: Cross-episode or meta actions will otherwise turn Deadman into a continuous branch simulator and make returning to the drama feel incoherent.
- Recommendation: Keep return_to_plot_fit excluded; enforce local consequence plus one-line watch-flow rationale in judgment output.

## FMRT-003 - visual_result_policy must explicitly block visual proof claims.

- Severity: `high`
- Affected fields: visual_result_policy, proof_state, review_and_provenance
- Affected clusters: capability_bound_visibility, critical_stakes_tradeoff, critical_stakes_with_proof, proof_before_reversal, public_escalation, relationship_rupture, visibility_and_timing
- Product consequence: Generated or placeholder result images could be read as evidence, making the consequence look canonically proven when it is only illustrative.
- Recommendation: Keep auto_visual_truth excluded and add truth_level/fallback fields before image generation is wired.

## FMRT-004 - score_axes should stay producer-only.

- Severity: `medium`
- Affected fields: score_axes
- Affected clusters: -
- Product consequence: Sending ranking scores into runtime judgment can bias the model toward candidate popularity instead of local causal credibility.
- Recommendation: Use score_axes for ARS ranking and QA only; backend adapter should not expose it to the viewer-facing judgment prompt.
